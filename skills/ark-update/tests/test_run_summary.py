"""Tests: SKILL.md wrapper output format — migrate.py stdout summary shape.

The SKILL.md wrapper (Step 7) renders the run summary to the user.
These tests verify that migrate.py emits the expected stdout structure
that the SKILL.md wrapper can parse and render.

Summary format:
  ark-update run summary
  ======================
  clean — nothing to do (all ops idempotent, no pending migrations)
  -- OR --
  Phase 1 (destructive migrations): N applied, N failed
  Phase 2 (convergence): N applied, N drift-overwritten, N skipped, N failed
  [blank line]
  Drift events:          (only if drift_count > 0)
    drift: <op_id> (backup: <path>)
  [blank line]
  Failures:              (only if failures > 0)
    FAIL: <op_id> (<op_type>): <error>
"""
from __future__ import annotations

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


def test_summary_header_present(tmp_path: Path) -> None:
    """All runs must start with 'ark-update run summary' header."""
    _copy_fixture_pre("healthy-current", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert result.stdout.startswith("ark-update run summary\n"), (
        f"Expected header at start of stdout:\n{result.stdout!r}"
    )
    assert "======================" in result.stdout


def test_clean_summary_message(tmp_path: Path) -> None:
    """Idempotent run prints 'clean — nothing to do'."""
    _copy_fixture_pre("healthy-current", tmp_path)
    result = _run_engine(tmp_path)
    assert "clean — nothing to do" in result.stdout


def test_non_clean_summary_has_phase_lines(tmp_path: Path) -> None:
    """Non-clean run has both Phase 1 and Phase 2 summary lines."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "Phase 1 (destructive migrations):" in result.stdout
    assert "Phase 2 (convergence):" in result.stdout


def test_drift_summary_has_drift_events_section(tmp_path: Path) -> None:
    """Drift run prints 'Drift events:' section with backup paths."""
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "Drift events:" in result.stdout
    assert "drift:" in result.stdout
    assert "backup:" in result.stdout


def test_apply_count_in_summary(tmp_path: Path) -> None:
    """Summary Phase 2 line reports correct applied count."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    # pre-v1.11 applies 4 ops
    assert "4 applied" in result.stdout


def test_skip_count_in_summary(tmp_path: Path) -> None:
    """Summary Phase 2 line reports correct skipped count."""
    _copy_fixture_pre("pre-v1.12", tmp_path)
    result = _run_engine(tmp_path)
    # pre-v1.12: 1 skipped (setup-vault-symlink.sh already present)
    assert "1 skipped" in result.stdout


def test_drift_overwrite_count_in_summary(tmp_path: Path) -> None:
    """Drift run reports drift-overwritten count in Phase 2 summary line."""
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert "drift-overwritten" in result.stdout
    # Both omc-routing (content) and routing-rules (stale version) drift.
    assert "2 drift-overwritten" in result.stdout
