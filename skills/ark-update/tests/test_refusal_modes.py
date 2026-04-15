"""Integration tests: refusal modes — engine refuses cleanly with correct exit code.

Refusal scenarios tested:
  1. Dirty working tree (uncommitted changes) → exit 2.
  2. Malformed migrations-applied.jsonl (invalid JSON) → exit 4.
  3. Mismatched marker id in CLAUDE.md → MarkerIntegrityError, exit 1.
  4. .ark/ directory gitignored (contains '.ark/' line in .gitignore) → exit 1, message.
  5. Malformed CLAUDE.md (unclosed marker) → MarkerIntegrityError, exit 1.
  6. Path traversal in target-profile (would need a patched profile) is tested
     in test_paths.py; not re-tested here.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent


def _run_engine(
    project_root: Path,
    extra_args: list[str] | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "migrate.py"),
        "--project-root", str(project_root),
        "--skills-root", str(_SKILLS_ROOT),
    ]
    if extra_args:
        cmd.extend(extra_args)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=run_env)


# ---------------------------------------------------------------------------
# 1. Dirty working tree → exit 2
# ---------------------------------------------------------------------------

def test_dirty_tree_refuses(tmp_path: Path) -> None:
    """Engine exits 2 when working tree has uncommitted changes (git repo)."""
    # Init a git repo with one committed file, then make it dirty.
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty-message"],
        cwd=tmp_path, capture_output=True,
    )
    # Now make it dirty (modify tracked file).
    readme.write_text("hello dirty\n")

    result = _run_engine(tmp_path)  # no --force
    assert result.returncode == 2, (
        f"Expected exit 2 for dirty tree, got {result.returncode}:\n{result.stderr}"
    )
    assert "uncommitted" in result.stderr.lower(), (
        f"Expected 'uncommitted' in stderr: {result.stderr}"
    )


def test_force_bypasses_dirty_check(tmp_path: Path) -> None:
    """--force lets the engine run on a dirty tree."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path, capture_output=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("dirty\n")
    # Don't commit — fully dirty.

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 0, (
        f"--force should bypass dirty check, got {result.returncode}:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 2. Malformed migrations-applied.jsonl → exit 4
# ---------------------------------------------------------------------------

def test_malformed_jsonl_refuses(tmp_path: Path) -> None:
    """Engine exits 4 when migrations-applied.jsonl contains invalid JSON."""
    ark_dir = tmp_path / ".ark"
    ark_dir.mkdir()
    log_path = ark_dir / "migrations-applied.jsonl"
    log_path.write_text("this is not json\n", encoding="utf-8")

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 4, (
        f"Expected exit 4 for malformed jsonl, got {result.returncode}:\n{result.stderr}"
    )
    assert "malformed" in result.stderr.lower() or "repair" in result.stderr.lower(), (
        f"Expected 'malformed' or 'repair' in stderr: {result.stderr}"
    )


def test_malformed_jsonl_missing_field_refuses(tmp_path: Path) -> None:
    """Engine exits 4 when jsonl entry is valid JSON but missing required fields."""
    ark_dir = tmp_path / ".ark"
    ark_dir.mkdir()
    log_path = ark_dir / "migrations-applied.jsonl"
    # Valid JSON but missing required 'ops_ran', 'failed_ops', etc.
    log_path.write_text(
        json.dumps({"version": "1.0.0", "applied_at": "2026-01-01T00:00:00Z"}) + "\n",
        encoding="utf-8",
    )

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 4, (
        f"Expected exit 4 for incomplete log entry, got {result.returncode}:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 3. Mismatched marker id in CLAUDE.md → exit 1
# ---------------------------------------------------------------------------

def test_mismatched_marker_id_refuses(tmp_path: Path) -> None:
    """Engine exits 1 when CLAUDE.md has mismatched begin/end marker ids."""
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        "# Project\n"
        "<!-- ark:begin id=foo version=1.0.0 -->\n"
        "some content\n"
        "<!-- ark:end id=bar -->\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 1, (
        f"Expected exit 1 for mismatched marker id, got {result.returncode}:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# 4. .ark/ gitignored → exit 1
# ---------------------------------------------------------------------------

def test_ark_dir_gitignored_refuses(tmp_path: Path) -> None:
    """Engine exits 1 when .ark/ is listed in .gitignore."""
    (tmp_path / "CLAUDE.md").write_text("# Project\n")
    (tmp_path / ".gitignore").write_text(".ark/\n*.pyc\n")

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 1, (
        f"Expected exit 1 for .ark/ gitignored, got {result.returncode}:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Message must mention .ark/ gitignored
    combined = result.stdout + result.stderr
    assert ".ark" in combined, (
        f"Expected '.ark' mentioned in output: stdout={result.stdout!r} stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# 5. Unclosed marker (malformed CLAUDE.md structure) → exit 1
# ---------------------------------------------------------------------------

def test_unclosed_marker_refuses(tmp_path: Path) -> None:
    """Engine exits 1 when CLAUDE.md has an unclosed ark:begin marker."""
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(
        "# Project\n"
        "<!-- ark:begin id=routing-rules version=1.12.0 -->\n"
        "some content\n"
        "# No closing marker — malformed\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    result = _run_engine(tmp_path, extra_args=["--force"])
    assert result.returncode == 1, (
        f"Expected exit 1 for unclosed marker, got {result.returncode}:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
