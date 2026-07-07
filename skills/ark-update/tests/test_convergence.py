"""Integration tests: run each fixture through the engine and diff result vs expected-post/.

Each test copies the fixture pre-state to a temp directory, runs migrate.py,
then compares every file in expected-post/ byte-exact against the actual output.

Gate-flag wiring note (Step 7, commit a9958c8):
  Gate-flag resolution IS wired in migrate.py (_read_gate_flags / _iter_target_profile_entries).
  These convergence tests intentionally run with ARK_HAS_OMC and ARK_CENTRALIZED_VAULT
  UNSET so the engine falls back to backward-compat (unconditional-apply) mode.

  Gate-specific behaviour (skip paths) is covered by test_gate_flags.py, which runs
  the engine with explicit env-var overrides and asserts inline (not against expected-post/).

v2.0.0 NOTE: target-profile.yaml v2 declares ``managed_regions: []`` and
``ensured_gitignore: []`` — the v1 CLAUDE.md routing/omc-routing managed regions
and the .ark-workflow/ gitignore entry were retired in the v2.0.0 restructure (see
target-profile.yaml's v2.0.0 NOTE). The only remaining convergence-relevant entry is
the ``setup-vault-symlink`` ensured_files op. expected-post/ fixtures were
regenerated accordingly via ``tests/regenerate_fixtures.py --apply`` — CLAUDE.md
and .gitignore are no longer touched by the engine at all (they pass through
byte-identical to the fixture's pre-state, or don't exist post-run if they didn't
exist pre-run, as for the ``fresh`` fixture).
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


def test_convergence_pre_v1_11_applies_one_op(tmp_path: Path) -> None:
    """pre-v1.11: engine must apply exactly 1 op (setup-vault-symlink; the only
    surviving convergence entry in v2 — see module docstring's v2.0.0 NOTE)."""
    _copy_fixture_pre("pre-v1.11", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    # Summary line: "1 applied"
    assert "1 applied" in result.stdout, f"Expected 1 applied, got:\n{result.stdout}"


def test_convergence_pre_v1_12_skips_existing_script(tmp_path: Path) -> None:
    """pre-v1.12: setup-vault-symlink.sh already present → all ops idempotent → clean run."""
    _copy_fixture_pre("pre-v1.12", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "clean" in result.stdout.lower(), f"Expected a clean run:\n{result.stdout}"


def test_convergence_pre_v1_13_converges_existing(tmp_path: Path) -> None:
    """pre-v1.13: setup-vault-symlink.sh already present → all ops idempotent → clean run.

    (In v1 this fixture also exercised omc-routing/routing-rules convergence;
    those managed regions are retired in v2 — see module docstring's v2.0.0 NOTE.)
    """
    _copy_fixture_pre("pre-v1.13", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "clean" in result.stdout.lower(), f"Expected a clean run:\n{result.stdout}"


def test_convergence_fresh_creates_symlink_script(tmp_path: Path) -> None:
    """fresh: empty project; engine must create the one surviving managed artifact."""
    _copy_fixture_pre("fresh", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "1 applied" in result.stdout, f"Expected 1 applied:\n{result.stdout}"
    assert (tmp_path / "scripts" / "setup-vault-symlink.sh").exists()


# v2.0.0 NOTE: test_convergence_drift_inside_markers_overwrites_and_backs_up was
# removed here. It asserted drift/backup behavior of the retired omc-routing /
# routing-rules managed regions. The only remaining op (create_file_from_template,
# used for setup-vault-symlink) never drifts by design — its _detect_drift_impl
# always returns has_drift=False (once a file exists, the engine never overwrites
# or re-stamps it; see ops/create_file_from_template.py). drift-inside-markers now
# produces a clean run with no backups, same as any fixture where the script
# already exists. See the ark-update engine-v2 follow-up issue for restoring
# drift/backup coverage once the okf-conversion / gh-issues-adoption ops land.


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
