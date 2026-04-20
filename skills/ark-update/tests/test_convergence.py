"""Integration tests: run each fixture through the engine and diff result vs expected-post/.

Each test copies the fixture pre-state to a temp directory, runs migrate.py,
then compares every file in expected-post/ byte-exact against the actual output.

Gate-flag wiring note (Step 7, commit a9958c8):
  Gate-flag resolution IS wired in migrate.py (_read_gate_flags / _iter_target_profile_entries).
  These convergence tests intentionally run with ARK_HAS_OMC and ARK_CENTRALIZED_VAULT
  UNSET so the engine falls back to backward-compat (unconditional-apply) mode.
  As a result, expected-post/ for ALL fixtures includes both the omc-routing managed
  region AND scripts/setup-vault-symlink.sh — this preserves full coverage of the
  unconditional code path.

  Gate-specific behaviour (skip paths) is covered by test_gate_flags.py, which runs
  the engine with explicit env-var overrides and asserts inline (not against expected-post/).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent  # worktree root / skills root


def _run_engine(project_root: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Run migrate.py on *project_root* with --force (skip git dirty check)."""
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "migrate.py"),
        "--project-root", str(project_root),
        "--skills-root", str(_SKILLS_ROOT),
        "--force",
    ]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True)


def _copy_fixture_pre(fixture_name: str, dest: Path) -> None:
    """Copy pre-state of a fixture (excluding expected-post/) to *dest*."""
    src = _FIXTURES_DIR / fixture_name
    for item in src.iterdir():
        if item.name == "expected-post":
            continue
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d)
        else:
            shutil.copy2(item, d)


def _assert_convergence(fixture_name: str, project_root: Path) -> None:
    """Assert every file in expected-post/ matches the engine output byte-exact.

    Files in .ark/ are excluded (run state, not fixture content).
    Extra files in project_root that aren't in expected-post/ are flagged as
    unexpected additions (excluding .ark/).
    """
    ep = _FIXTURES_DIR / fixture_name / "expected-post"

    missing: list[str] = []
    diffs: list[str] = []
    extra: list[str] = []

    for ep_file in sorted(ep.rglob("*")):
        if not ep_file.is_file():
            continue
        rel = ep_file.relative_to(ep)
        actual = project_root / rel
        if not actual.exists():
            missing.append(str(rel))
            continue
        expected_bytes = ep_file.read_bytes()
        actual_bytes = actual.read_bytes()
        if expected_bytes != actual_bytes:
            diffs.append(
                f"{rel}: expected {len(expected_bytes)} bytes, got {len(actual_bytes)} bytes"
            )

    for actual_file in sorted(project_root.rglob("*")):
        if not actual_file.is_file():
            continue
        rel = actual_file.relative_to(project_root)
        parts = rel.parts
        if parts[0] in (".ark",):
            continue
        ep_file = ep / rel
        if not ep_file.exists():
            extra.append(str(rel))

    errors: list[str] = []
    if missing:
        errors.append("Missing files in output:\n  " + "\n  ".join(missing))
    if diffs:
        errors.append("Byte-mismatch:\n  " + "\n  ".join(diffs))
    if extra:
        errors.append("Unexpected extra files in output:\n  " + "\n  ".join(extra))

    assert not errors, f"Fixture {fixture_name!r} convergence failed:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Parametrised convergence tests
# ---------------------------------------------------------------------------

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
def test_convergence_byte_exact(fixture_name: str, tmp_path: Path) -> None:
    """Run engine on fixture pre-state; assert expected-post/ byte-exact match."""
    _copy_fixture_pre(fixture_name, tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0, (
        f"Engine exited {result.returncode} for {fixture_name!r}:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    _assert_convergence(fixture_name, tmp_path)


def test_convergence_pre_v1_11_applies_four_ops(tmp_path: Path) -> None:
    """pre-v1.11: engine must apply exactly 4 ops (omc-routing, routing-rules, gitignore, setup-vault-symlink)."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    # Summary line: "4 applied"
    assert "4 applied" in result.stdout, f"Expected 4 applied, got:\n{result.stdout}"


def test_convergence_pre_v1_12_skips_existing_script(tmp_path: Path) -> None:
    """pre-v1.12: setup-vault-symlink.sh already present → must be skipped_idempotent."""
    _copy_fixture_pre("pre-v1.12", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "3 applied" in result.stdout, f"Expected 3 applied:\n{result.stdout}"
    assert "1 skipped" in result.stdout, f"Expected 1 skipped:\n{result.stdout}"


def test_convergence_pre_v1_13_converges_existing(tmp_path: Path) -> None:
    """pre-v1.13: omc-routing missing, routing-rules stale (v1.12.0),
    setup-vault-symlink.sh already present.

    Expected breakdown against current target-profile:
    - omc-routing            → applied (inserted)
    - .ark-workflow/ ignore  → applied (appended)
    - routing-rules          → drift-overwritten (marker version 1.12.0 < target 1.17.0)
    - setup-vault-symlink.sh → skipped (already present)
    """
    _copy_fixture_pre("pre-v1.13", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "2 applied" in result.stdout, f"Expected 2 applied:\n{result.stdout}"
    assert "1 drift-overwritten" in result.stdout, f"Expected 1 drift-overwritten:\n{result.stdout}"
    assert "1 skipped" in result.stdout, f"Expected 1 skipped:\n{result.stdout}"


def test_convergence_fresh_creates_all(tmp_path: Path) -> None:
    """fresh: empty project; engine must create all 4 managed artifacts."""
    _copy_fixture_pre("fresh", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "4 applied" in result.stdout, f"Expected 4 applied:\n{result.stdout}"
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "scripts" / "setup-vault-symlink.sh").exists()


def test_convergence_drift_inside_markers_overwrites_and_backs_up(tmp_path: Path) -> None:
    """drift-inside-markers: engine must report drift-overwritten and create backups."""
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "drift-overwritten" in result.stdout, (
        f"Expected drift-overwritten in summary:\n{result.stdout}"
    )
    # At least one backup file must exist
    backups = list((tmp_path / ".ark" / "backups").glob("*.bak"))
    assert backups, "Expected at least one .bak backup file in .ark/backups/"


def test_convergence_drift_outside_markers_zero_touch(tmp_path: Path) -> None:
    """drift-outside-markers: content outside markers must be preserved byte-exact."""
    _copy_fixture_pre("drift-outside-markers", tmp_path)
    claude_before = (tmp_path / "CLAUDE.md").read_bytes()
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "clean" in result.stdout.lower(), (
        f"Expected clean run (all idempotent) for drift-outside-markers:\n{result.stdout}"
    )
    claude_after = (tmp_path / "CLAUDE.md").read_bytes()
    assert claude_before == claude_after, (
        "CLAUDE.md was modified on drift-outside-markers fixture — zero-touch violated"
    )
