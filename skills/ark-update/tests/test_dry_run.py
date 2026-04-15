"""Integration tests: --dry-run writes nothing and is deterministic.

--dry-run must:
  1. Write NOTHING to the project root (no file modifications, no .ark/ creation).
  2. Exit 0.
  3. Print JSON to stdout that is a valid PlanReport dict.
  4. Be deterministic: two --dry-run calls on the same input produce byte-identical JSON.
  5. Not create any .bak backup files.

Codex P2-5: per-op dry_run coverage is verified in test_op_*.py unit tests.
This file tests the engine-level --dry-run path.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent


def _run_dry(project_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "migrate.py"),
            "--project-root", str(project_root),
            "--skills-root", str(_SKILLS_ROOT),
            "--force",
            "--dry-run",
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


def _snapshot_dir(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file():
            snapshot[str(f.relative_to(root))] = f.read_bytes()
    return snapshot


FIXTURES = [
    "pre-v1.11",
    "pre-v1.12",
    "pre-v1.13",
    "fresh",
    "healthy-current",
    "drift-inside-markers",
    "drift-outside-markers",
]


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_dry_run_writes_nothing(fixture_name: str, tmp_path: Path) -> None:
    """--dry-run must not modify any file in the project root."""
    _copy_fixture_pre(fixture_name, tmp_path)
    snap_before = _snapshot_dir(tmp_path)

    result = _run_dry(tmp_path)
    assert result.returncode == 0, (
        f"--dry-run exited {result.returncode} for {fixture_name!r}:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    snap_after = _snapshot_dir(tmp_path)
    assert snap_before == snap_after, (
        f"--dry-run modified files for {fixture_name!r}:\n"
        + "\n".join(
            f"  {k}" for k in set(snap_before) ^ set(snap_after)
        )
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_dry_run_exits_zero(fixture_name: str, tmp_path: Path) -> None:
    """--dry-run must exit 0 for all valid fixtures."""
    _copy_fixture_pre(fixture_name, tmp_path)
    result = _run_dry(tmp_path)
    assert result.returncode == 0, (
        f"--dry-run non-zero exit for {fixture_name!r}:\n{result.stderr}"
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_dry_run_outputs_valid_json(fixture_name: str, tmp_path: Path) -> None:
    """--dry-run stdout must include a valid JSON PlanReport after the human-readable summary."""
    _copy_fixture_pre(fixture_name, tmp_path)
    result = _run_dry(tmp_path)
    assert result.returncode == 0

    # The last non-empty block of stdout is the JSON PlanReport.
    # migrate.py prints: human summary, blank line, JSON.
    lines = result.stdout.splitlines()
    # Find the start of the JSON block (first line that starts with '{')
    json_start = next((i for i, l in enumerate(lines) if l.strip().startswith("{")), None)
    assert json_start is not None, (
        f"No JSON found in --dry-run stdout for {fixture_name!r}:\n{result.stdout}"
    )
    json_text = "\n".join(lines[json_start:])
    try:
        plan = json.loads(json_text)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Invalid JSON in --dry-run output for {fixture_name!r}: {exc}\n{json_text}")

    # Verify required PlanReport keys.
    required_keys = {
        "phase_1_ops", "phase_2_ops",
        "would_apply_count", "would_skip_count",
        "would_overwrite_count", "would_fail_count",
    }
    missing = required_keys - set(plan.keys())
    assert not missing, (
        f"PlanReport missing keys for {fixture_name!r}: {sorted(missing)}"
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_dry_run_is_deterministic(fixture_name: str, tmp_path: Path) -> None:
    """Two --dry-run calls on the same fixture produce byte-identical JSON."""
    _copy_fixture_pre(fixture_name, tmp_path)

    r1 = _run_dry(tmp_path)
    r2 = _run_dry(tmp_path)

    assert r1.returncode == 0 and r2.returncode == 0

    # Extract JSON portions from both runs.
    def _extract_json(stdout: str) -> str:
        lines = stdout.splitlines()
        json_start = next(
            (i for i, l in enumerate(lines) if l.strip().startswith("{")), None
        )
        return "\n".join(lines[json_start:]) if json_start is not None else ""

    json1 = _extract_json(r1.stdout)
    json2 = _extract_json(r2.stdout)
    assert json1 == json2, (
        f"--dry-run non-deterministic for {fixture_name!r}"
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_dry_run_no_backups(fixture_name: str, tmp_path: Path) -> None:
    """--dry-run must not create any .bak backup files."""
    _copy_fixture_pre(fixture_name, tmp_path)
    _run_dry(tmp_path)
    bak_files = list(tmp_path.rglob("*.bak"))
    assert not bak_files, (
        f"--dry-run created backup files for {fixture_name!r}: {bak_files}"
    )
