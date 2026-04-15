"""Unit tests for check_chain_drift.py — the CI lint added in R4 of the
2026-04-15 uniformity refactor that detects recurrence of specific
documentation drift patterns surfaced in the audit.

Design:
  - TestBannedPatterns: one test per banned rule; creates a minimal
    markdown fixture under a tmp_path mimicking the target globs, runs
    the lint, asserts exit 1 + stderr includes the reason.
  - TestLegitimateContent: confirms that legitimate descriptive mentions
    of /ralph or /ultrawork INSIDE a vanilla step-3 line do not trigger
    Pattern 4 (the step-3 engine anchor regex).
  - TestRealRepoFilesPass: runs the script against the real repo and
    asserts exit 0 — this pins the post-R4 contract.

Follows the importlib.util loading pattern used in test_check_path_b_coverage.py."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


_CCD_PATH = Path(__file__).parent / "check_chain_drift.py"
_spec = importlib.util.spec_from_file_location("check_chain_drift", _CCD_PATH)
ccd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccd)


# ── Fixture helpers ─────────────────────────────────────────────────────

def _make_fake_repo(tmp_path: Path, *, chain_content: str = "", ref_content: str = "") -> Path:
    """Create the skills/ark-workflow/{chains,references}/ directory layout
    under tmp_path with the provided markdown bodies. Returns tmp_path so
    it can be passed as --root."""
    chains = tmp_path / "skills" / "ark-workflow" / "chains"
    refs = tmp_path / "skills" / "ark-workflow" / "references"
    chains.mkdir(parents=True, exist_ok=True)
    refs.mkdir(parents=True, exist_ok=True)
    if chain_content:
        (chains / "fixture.md").write_text(chain_content)
    if ref_content:
        (refs / "omc-integration.md").write_text(ref_content)
    return tmp_path


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_CCD_PATH), "--root", str(root)],
        capture_output=True, text=True,
    )


# ── TestBannedPatterns ──────────────────────────────────────────────────

class TestBannedPatterns:
    def test_detects_omc_execution_only(self, tmp_path):
        """Pattern 1: literal OMC_EXECUTION_ONLY anywhere in scope."""
        root = _make_fake_repo(
            tmp_path,
            chain_content="# Test\n\nExport OMC_EXECUTION_ONLY=1 then run.\n",
        )
        result = _run(root)
        assert result.returncode == 1
        assert "OMC_EXECUTION_ONLY" in result.stderr
        assert "retired in R1" in result.stderr

    def test_detects_omc_execution_only_in_reference(self, tmp_path):
        """Same pattern in omc-integration.md also trips."""
        root = _make_fake_repo(
            tmp_path,
            ref_content="# Ref\n\nOld note: `OMC_EXECUTION_ONLY` handling.\n",
        )
        result = _run(root)
        assert result.returncode == 1
        assert "OMC_EXECUTION_ONLY" in result.stderr

    def test_detects_phase_5_docs_ship(self, tmp_path):
        """Pattern 2: stale 'Phase 5 (docs/ship)' claim about autopilot."""
        root = _make_fake_repo(
            tmp_path,
            chain_content="# Test\n\nSkips Phase 5 (docs/ship) — wrong.\n",
        )
        result = _run(root)
        assert result.returncode == 1
        assert "Phase 5" in result.stderr
        assert "Cleanup" in result.stderr

    def test_detects_internal_phase_4_execution(self, tmp_path):
        """Pattern 3: stale 'internal Phase 4 (execution)' phase claim."""
        root = _make_fake_repo(
            tmp_path,
            chain_content="# Test\n\nAfter internal Phase 4 (execution) completes.\n",
        )
        result = _run(root)
        assert result.returncode == 1
        assert "Phase 4" in result.stderr
        assert "Validation" in result.stderr

    def test_detects_ralph_as_step_3_engine(self, tmp_path):
        """Pattern 4: /ralph as chain step-3 engine (the anchored regex)."""
        root = _make_fake_repo(
            tmp_path,
            chain_content=(
                "# Test\n\n"
                "### Path B (OMC-powered — if HAS_OMC=true)\n\n"
                "3. `/ralph` — loop-to-verified against benchmark.\n"
            ),
        )
        result = _run(root)
        assert result.returncode == 1
        assert "/ralph" in result.stderr or "ultrawork" in result.stderr
        assert "uniformity" in result.stderr.lower() or "R2" in result.stderr

    def test_detects_ultrawork_as_step_3_engine(self, tmp_path):
        """Pattern 4 complement: /ultrawork as chain step-3 engine."""
        root = _make_fake_repo(
            tmp_path,
            chain_content=(
                "# Test\n\n"
                "### Path B (OMC-powered — if HAS_OMC=true)\n\n"
                "3. `/ultrawork` — parallel lanes.\n"
            ),
        )
        result = _run(root)
        assert result.returncode == 1
        assert "/ultrawork" in result.stderr or "/ralph" in result.stderr

    def test_reports_multiple_violations(self, tmp_path):
        """If multiple banned patterns are present, all are reported."""
        root = _make_fake_repo(
            tmp_path,
            chain_content=(
                "# Test\n\n"
                "OMC_EXECUTION_ONLY=1 env var.\n\n"
                "3. `/ralph` — loop-to-verified.\n"
            ),
        )
        result = _run(root)
        assert result.returncode == 1
        # Both violations surfaced.
        assert "OMC_EXECUTION_ONLY" in result.stderr
        assert "/ralph" in result.stderr or "/ultrawork" in result.stderr


# ── TestLegitimateContent ───────────────────────────────────────────────

class TestLegitimateContent:
    def test_internal_ralph_mention_inside_vanilla_step_3_does_not_trip(self, tmp_path):
        """Descriptive mentions of /ralph or /ultrawork INSIDE a vanilla
        step-3 line (engine is /autopilot) must not match Pattern 4.
        This is the critical false-positive guard — the uniformity
        refactor deliberately keeps these mentions to explain what
        /autopilot's Phase 2 does internally."""
        root = _make_fake_repo(
            tmp_path,
            chain_content=(
                "# Test\n\n"
                "### Path B (OMC-powered — if HAS_OMC=true)\n\n"
                "3. `/autopilot` — full pipeline; benchmark-target loops are "
                "handled inside autopilot's Phase 2 via internal /ralph. Also "
                "internal /ultrawork parallelism.\n"
                "4. `<<HANDBACK>>`\n"
                "5. Ark closeout.\n"
            ),
        )
        result = _run(root)
        assert result.returncode == 0, f"False positive: {result.stderr}"
        assert "zero banned patterns" in result.stdout

    def test_legitimate_section_4_2_pointer_to_team_does_not_trip(self, tmp_path):
        """After R1 renumbering, § Section 4.2 is /team handback. Legitimate
        pointers to §4.2 (not pointing at the deleted /ralph content) must
        not trip the lint."""
        root = _make_fake_repo(
            tmp_path,
            chain_content=(
                "# Test\n\n"
                "3. `/team` — coordinated cross-module migration. See "
                "`references/omc-integration.md` § Section 4.2 for the "
                "handback boundary.\n"
            ),
        )
        result = _run(root)
        assert result.returncode == 0, f"False positive: {result.stderr}"

    def test_empty_target_files_still_pass(self, tmp_path):
        """Files with no content pass — the lint is only for detecting
        banned patterns, not enforcing minimum content."""
        root = _make_fake_repo(tmp_path, chain_content="# Empty chain\n")
        result = _run(root)
        assert result.returncode == 0

    def test_no_target_files_fails(self, tmp_path):
        """If --root points at a directory with no scannable files, the
        script fails with a clear error (not silent success)."""
        # Don't create the skills/ tree.
        result = _run(tmp_path)
        assert result.returncode == 1
        assert "No target files found" in result.stderr


# ── TestRealRepoFilesPass ───────────────────────────────────────────────

class TestRealRepoFilesPass:
    def test_live_repo_passes_drift_lint(self):
        """End-to-end: the ark-skills repo must pass the drift lint at
        current HEAD. This is the CI contract that R4 institutes."""
        # The test file lives at skills/ark-context-warmup/scripts/; the
        # repo root is three parents up.
        repo_root = Path(__file__).parent.parent.parent.parent
        target_chains = repo_root / "skills" / "ark-workflow" / "chains"
        if not target_chains.is_dir():
            pytest.skip("live repo structure not accessible from this location")
        result = subprocess.run(
            [sys.executable, str(_CCD_PATH), "--root", str(repo_root)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"R4 contract broken — chain drift detected at HEAD:\n{result.stderr}"
        )
        assert "zero banned patterns" in result.stdout


# ── TestCollectFiles ────────────────────────────────────────────────────

class TestCollectFiles:
    def test_collects_all_chain_files(self, tmp_path):
        """_collect_files must pick up every *.md under chains/ plus the
        single omc-integration.md reference."""
        root = _make_fake_repo(
            tmp_path,
            chain_content="# A\n",
        )
        # Add a second chain file manually.
        (root / "skills" / "ark-workflow" / "chains" / "another.md").write_text("# B\n")
        # And the reference.
        (root / "skills" / "ark-workflow" / "references" / "omc-integration.md").write_text("# Ref\n")

        files = ccd._collect_files(root)
        names = sorted(f.name for f in files)
        assert "fixture.md" in names
        assert "another.md" in names
        assert "omc-integration.md" in names

    def test_ignores_non_scope_files(self, tmp_path):
        """Files outside skills/ark-workflow/chains/ and
        references/omc-integration.md must be ignored."""
        root = _make_fake_repo(tmp_path, chain_content="# In scope\n")
        # Drop a file outside scope containing banned content.
        (root / "skills" / "ark-workflow" / "references" / "troubleshooting.md").write_text(
            "OMC_EXECUTION_ONLY should not trigger from this file.\n"
        )
        files = ccd._collect_files(root)
        names = [f.name for f in files]
        assert "troubleshooting.md" not in names
        # And the lint pass (because troubleshooting.md isn't scanned).
        result = _run(root)
        assert result.returncode == 0
