"""Tests: engine emits structured log to migrations-applied.jsonl.

Verifies that after a non-clean run:
  - .ark/migrations-applied.jsonl exists and is valid JSONL.
  - Each line is a valid JSON object with the required schema fields.
  - phase field is "convergence" for Phase 2 entries.
  - ops_ran is an integer >= 0.
  - result is "clean" or "partial".
  - applied_at is a UTC ISO-8601 string ending in 'Z'.

Also verifies that a clean (idempotent) run does NOT append to the log (P1-2).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent


def _run_engine(project_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "migrate.py"),
            "--project-root", str(project_root),
            "--skills-root", str(_SKILLS_ROOT),
            "--force",
        ],
        capture_output=True,
        text=True,
    )


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


_ISO_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

REQUIRED_LOG_FIELDS = {"version", "applied_at", "ops_ran", "ops_skipped", "failed_ops", "result", "phase"}


def test_non_clean_run_writes_jsonl(tmp_path: Path) -> None:
    """A non-clean run (pre-v1.11) writes at least one JSONL log entry."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0

    log_path = tmp_path / ".ark" / "migrations-applied.jsonl"
    assert log_path.exists(), "migrations-applied.jsonl must exist after a non-clean run"

    entries = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    assert entries, "Expected at least one log entry"


def test_log_entry_schema(tmp_path: Path) -> None:
    """Each log entry must have all required fields with correct types."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    _run_engine(tmp_path)

    log_path = tmp_path / ".ark" / "migrations-applied.jsonl"
    assert log_path.exists()

    for i, raw_line in enumerate(log_path.read_text().splitlines()):
        if not raw_line.strip():
            continue
        entry = json.loads(raw_line)

        missing = REQUIRED_LOG_FIELDS - set(entry.keys())
        assert not missing, f"Log entry {i} missing fields: {missing}"

        assert isinstance(entry["ops_ran"], int), f"ops_ran must be int in entry {i}"
        assert isinstance(entry["ops_skipped"], int), f"ops_skipped must be int in entry {i}"
        assert isinstance(entry["failed_ops"], list), f"failed_ops must be list in entry {i}"
        assert entry["result"] in ("clean", "partial"), (
            f"result must be 'clean' or 'partial' in entry {i}: {entry['result']!r}"
        )
        assert entry["phase"] in ("destructive", "convergence"), (
            f"phase must be 'destructive' or 'convergence' in entry {i}: {entry['phase']!r}"
        )
        assert _ISO_Z_RE.match(entry["applied_at"]), (
            f"applied_at must be ISO-8601 UTC in entry {i}: {entry['applied_at']!r}"
        )


def test_convergence_phase_logged(tmp_path: Path) -> None:
    """After Phase 2 convergence, log must have a 'convergence' phase entry."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    _run_engine(tmp_path)

    log_path = tmp_path / ".ark" / "migrations-applied.jsonl"
    assert log_path.exists()

    entries = [json.loads(l) for l in log_path.read_text().splitlines() if l.strip()]
    conv_entries = [e for e in entries if e.get("phase") == "convergence"]
    assert conv_entries, "Expected at least one 'convergence' phase log entry"
    assert conv_entries[-1]["ops_ran"] > 0, "Expected ops_ran > 0 for convergence entry"


def test_clean_run_does_not_append_log(tmp_path: Path) -> None:
    """A fully idempotent run must NOT append to the log (codex P1-2)."""
    _copy_fixture_pre("healthy-current", tmp_path)

    # First run (should be clean immediately).
    _run_engine(tmp_path)

    log_path = tmp_path / ".ark" / "migrations-applied.jsonl"
    log_before = log_path.read_bytes() if log_path.exists() else b""

    # Second run — must not append.
    _run_engine(tmp_path)

    log_after = log_path.read_bytes() if log_path.exists() else b""
    assert log_before == log_after, (
        f"Log was appended on clean (idempotent) run (codex P1-2). "
        f"Before {len(log_before)} bytes, after {len(log_after)} bytes."
    )


def test_plugin_version_pointer_written(tmp_path: Path) -> None:
    """After a non-clean run, .ark/plugin-version must be written."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    _run_engine(tmp_path)

    pointer = tmp_path / ".ark" / "plugin-version"
    assert pointer.exists(), ".ark/plugin-version must exist after non-clean run"
    version = pointer.read_text().strip()
    assert version, "plugin-version must not be empty"
    # Should be a semver-ish string.
    assert "." in version, f"plugin-version should be semver-like: {version!r}"
