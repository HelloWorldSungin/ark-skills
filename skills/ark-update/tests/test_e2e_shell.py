"""End-to-end shell tests: subprocess.run migrate.py and assert exit code + stdout.

These tests exercise the full CLI entry point via subprocess, including:
  - --dry-run exits 0 and prints PlanReport JSON.
  - Normal run exits 0 and prints human summary.
  - Missing --project-root fails with usage error.
  - Missing --skills-root and no ARK_SKILLS_ROOT env var exits 1.
  - --help prints usage without error.
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
_MIGRATE_PY = str(_SCRIPTS_DIR / "migrate.py")


def _copy_fixture_pre(fixture_name: str, dest: Path) -> None:
    src = _FIXTURES_DIR / fixture_name
    for item in src.iterdir():
        if item.name == "expected-post":
            continue
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d)
        else:
            shutil.copy2(item, d)


# ---------------------------------------------------------------------------
# Basic shell invocations
# ---------------------------------------------------------------------------

def test_e2e_dry_run_exits_zero_with_json(tmp_path: Path) -> None:
    """subprocess: migrate.py --dry-run exits 0 and prints JSON PlanReport."""
    _copy_fixture_pre("healthy-current", tmp_path)
    result = subprocess.run(
        [sys.executable, _MIGRATE_PY,
         "--project-root", str(tmp_path),
         "--skills-root", str(_SKILLS_ROOT),
         "--force", "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"

    # Extract JSON from stdout.
    lines = result.stdout.splitlines()
    json_start = next((i for i, l in enumerate(lines) if l.strip().startswith("{")), None)
    assert json_start is not None, f"No JSON in stdout:\n{result.stdout}"
    plan = json.loads("\n".join(lines[json_start:]))
    assert "phase_1_ops" in plan
    assert "phase_2_ops" in plan
    assert "would_apply_count" in plan


def test_e2e_normal_run_exits_zero(tmp_path: Path) -> None:
    """subprocess: migrate.py normal run exits 0 with human summary."""
    _copy_fixture_pre("pre-v1.13", tmp_path)
    result = subprocess.run(
        [sys.executable, _MIGRATE_PY,
         "--project-root", str(tmp_path),
         "--skills-root", str(_SKILLS_ROOT),
         "--force"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    assert "ark-update run summary" in result.stdout


def test_e2e_missing_skills_root_exits_one(tmp_path: Path) -> None:
    """subprocess: no --skills-root and no ARK_SKILLS_ROOT → exit 1."""
    env = os.environ.copy()
    env.pop("ARK_SKILLS_ROOT", None)

    result = subprocess.run(
        [sys.executable, _MIGRATE_PY,
         "--project-root", str(tmp_path),
         "--force"],
        capture_output=True, text=True,
        env=env,
    )
    assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
    assert "ARK_SKILLS_ROOT" in result.stderr


def test_e2e_help_exits_zero() -> None:
    """subprocess: --help exits 0 and prints usage."""
    result = subprocess.run(
        [sys.executable, _MIGRATE_PY, "--help"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "migrate.py" in result.stdout or "usage" in result.stdout.lower()


def test_e2e_dirty_tree_exits_two(tmp_path: Path) -> None:
    """subprocess: dirty git repo exits 2 without --force."""
    # Init git repo, commit, then make dirty.
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    readme = tmp_path / "README.md"
    readme.write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    readme.write_text("dirty\n")

    result = subprocess.run(
        [sys.executable, _MIGRATE_PY,
         "--project-root", str(tmp_path),
         "--skills-root", str(_SKILLS_ROOT)],
        capture_output=True, text=True,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 for dirty tree, got {result.returncode}:\n{result.stderr}"
    )


def test_e2e_idempotent_run_clean(tmp_path: Path) -> None:
    """subprocess: second run on healthy-current reports clean."""
    _copy_fixture_pre("healthy-current", tmp_path)

    def run():
        return subprocess.run(
            [sys.executable, _MIGRATE_PY,
             "--project-root", str(tmp_path),
             "--skills-root", str(_SKILLS_ROOT),
             "--force"],
            capture_output=True, text=True,
        )

    r1 = run()
    assert r1.returncode == 0
    r2 = run()
    assert r2.returncode == 0
    assert "clean" in r2.stdout.lower(), f"2nd run not clean: {r2.stdout}"


def test_e2e_skills_root_via_env(tmp_path: Path) -> None:
    """subprocess: ARK_SKILLS_ROOT env var is respected when --skills-root absent."""
    _copy_fixture_pre("healthy-current", tmp_path)
    env = os.environ.copy()
    env["ARK_SKILLS_ROOT"] = str(_SKILLS_ROOT)

    result = subprocess.run(
        [sys.executable, _MIGRATE_PY,
         "--project-root", str(tmp_path),
         "--force"],
        capture_output=True, text=True,
        env=env,
    )
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr}"
    assert "ark-update run summary" in result.stdout
