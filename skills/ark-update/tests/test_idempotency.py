"""Integration tests: idempotency — second run on every fixture must be fully zero-write.

Codex P1-2 invariant: if Phase 1 had zero pending migrations AND Phase 2 ops all
returned ``skipped_idempotent``, the engine must NOT append to migrations-applied.jsonl
and must NOT rewrite .ark/plugin-version.

"Fully zero-write" means:
  - No files outside .ark/ are modified.
  - .ark/migrations-applied.jsonl is NOT appended to (byte-identical before/after).
  - .ark/plugin-version is NOT rewritten (byte-identical before/after).
  - Engine stdout says "clean — nothing to do".
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
    """Run migrate.py with --force (skip git dirty check)."""
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


def _snapshot_dir(root: Path) -> dict[str, bytes]:
    """Return {rel_path_str: file_bytes} for all files under root."""
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
def test_second_run_is_zero_write(fixture_name: str, tmp_path: Path) -> None:
    """Run engine twice; second run must be fully zero-write (codex P1-2).

    Steps:
      1. Copy fixture pre-state.
      2. Run engine (first run — may apply ops, write .ark/ state).
      3. Snapshot all files.
      4. Run engine again (second run — must be clean).
      5. Snapshot all files again.
      6. Assert byte-identical snapshots.
      7. Assert second-run stdout contains "clean — nothing to do".
    """
    _copy_fixture_pre(fixture_name, tmp_path)

    # First run — converge.
    r1 = _run_engine(tmp_path)
    assert r1.returncode == 0, (
        f"First run failed for {fixture_name!r}:\n{r1.stdout}\n{r1.stderr}"
    )

    # Snapshot after first run.
    snap_after_1 = _snapshot_dir(tmp_path)

    # Second run — must be idempotent.
    r2 = _run_engine(tmp_path)
    assert r2.returncode == 0, (
        f"Second run failed for {fixture_name!r}:\n{r2.stdout}\n{r2.stderr}"
    )

    # Assert stdout says clean.
    assert "clean" in r2.stdout.lower(), (
        f"Second run for {fixture_name!r} did not report clean:\n{r2.stdout}"
    )

    # Snapshot after second run — must be byte-identical.
    snap_after_2 = _snapshot_dir(tmp_path)

    diffs: list[str] = []
    all_keys = set(snap_after_1) | set(snap_after_2)
    for key in sorted(all_keys):
        b1 = snap_after_1.get(key)
        b2 = snap_after_2.get(key)
        if b1 is None:
            diffs.append(f"NEW after 2nd run: {key}")
        elif b2 is None:
            diffs.append(f"DELETED after 2nd run: {key}")
        elif b1 != b2:
            diffs.append(f"MODIFIED after 2nd run: {key} ({len(b1)} → {len(b2)} bytes)")

    assert not diffs, (
        f"Second run was NOT zero-write for {fixture_name!r} (codex P1-2):\n"
        + "\n".join(f"  {d}" for d in diffs)
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_second_run_does_not_append_log(fixture_name: str, tmp_path: Path) -> None:
    """Second run must NOT append to migrations-applied.jsonl (P1-2 invariant)."""
    _copy_fixture_pre(fixture_name, tmp_path)

    # First run.
    r1 = _run_engine(tmp_path)
    assert r1.returncode == 0, f"First run failed: {r1.stdout}\n{r1.stderr}"

    log_path = tmp_path / ".ark" / "migrations-applied.jsonl"
    log_before = log_path.read_bytes() if log_path.exists() else b""

    # Second run.
    r2 = _run_engine(tmp_path)
    assert r2.returncode == 0, f"Second run failed: {r2.stdout}\n{r2.stderr}"

    log_after = log_path.read_bytes() if log_path.exists() else b""

    assert log_before == log_after, (
        f"migrations-applied.jsonl was modified on second run for {fixture_name!r} "
        f"(codex P1-2). Before: {len(log_before)} bytes, after: {len(log_after)} bytes."
    )
