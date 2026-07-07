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


def test_apply_count_in_summary(tmp_path: Path) -> None:
    """Summary Phase 2 line reports correct applied count."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    # v2.2.0: two convergence ops apply on pre-v1.11 — setup-vault-symlink
    # (ensured_files) and the vault-awareness managed region (epic #41).
    assert "2 applied" in result.stdout


# v2.0.0 NOTE: test_drift_summary_has_drift_events_section,
# test_skip_count_in_summary, and test_drift_overwrite_count_in_summary were
# removed here. They asserted behavior of the retired v1 managed_regions ops
# (omc-routing, routing-rules): drift/backup reporting, and a mixed
# applied+skipped run (3 routing ops applying alongside 1 already-present
# vault-symlink script skipping). target-profile.yaml v2 declares
# ``managed_regions: []`` — the only remaining op (create_file_from_template,
# used for setup-vault-symlink) never drifts by design (see its
# ``_detect_drift_impl``, which always returns ``has_drift=False``), and with
# a single gated op there is no longer a fixture that produces a genuine
# mixed apply/skip run — it's binary skip-all-or-apply-all for that one op.
# See the ark-update engine-v2 follow-up issue (docs/agents/issue-tracker.md
# conventions) for restoring this coverage once the okf-conversion /
# gh-issues-adoption migration ops are implemented.
