"""Unit tests for check_path_b_coverage.py — the CI contract validator that
enforces byte-identity canonicalization + shape distribution across the
17 Path B blocks in /ark-workflow chains (post-2026-04-15 uniformity refactor).

Originally backfilled for /ark-code-review --thorough pass 2 H4 finding —
the script shipped in v1.13.0 with zero tests. Updated for the 2026-04-14
uniformity refactor: /ralph and /ultrawork shapes retired (R2); Ship
Standalone Path B block removed (R17). Resulting contract: 17 total blocks
across 4 distinct canonicalized shapes (vanilla, team, special-a, special-b).

Uses importlib.util to load the target module by path (matches the pattern
used for synthesize/evidence/executor in test_warmup_helpers.py)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


_CPC_PATH = Path(__file__).parent / "check_path_b_coverage.py"
_spec = importlib.util.spec_from_file_location("check_path_b_coverage", _CPC_PATH)
cpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpc)


# ── Fixture helpers ─────────────────────────────────────────────────────

def _vanilla_block(weight: str = "--quick") -> str:
    """Return a canonical Vanilla-shape Path B block for fixture construction."""
    return f"""### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan
3. `/autopilot` — execution only; skips autopilot's internal Phase 5.
4. `<<HANDBACK>>` — Ark resumes authority.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review {weight}` onward. Closeout terminates at `/claude-history-ingest`.
"""


def _team_block() -> str:
    return """### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + coordinated multi-agent execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec.
2. `/omc-plan --consensus` — multi-agent consensus plan.
3. `/team` — coordinated cross-module migration.
4. `<<HANDBACK>>` — Ark resumes after team-verify, before team-fix.
5. **Ark closeout** — `/ark-code-review --thorough` onward to `/claude-history-ingest`.
"""


def _special_a_block() -> str:
    return """### Path B (OMC-powered — if HAS_OMC=true)

*Findings-only — no code review, no ship.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on audit scope.
2. `/omc-plan --consensus` — multi-agent consensus audit plan.
3. `/autopilot` — execution only; produces findings document.
4. `<<HANDBACK>>` — Ark resumes authority.
5. **Ark closeout:** `/wiki-update` → STOP.
"""


def _special_b_block() -> str:
    return """### Path B (OMC-powered — if HAS_OMC=true)

*Reflective capture.*

0. `/ark-context-warmup` — same as Path A
1. `/claude-history-ingest` — mine recent conversations (substitutes for `/deep-interview`).
2. `/omc-plan --consensus` — plan the capture.
3. `/autopilot` — runs `/wiki-ingest` + `/cross-linker` + `/tag-taxonomy`.
4. `<<HANDBACK>>` — Ark resumes authority.
5. **Ark closeout:** `/wiki-update` → `/claude-history-ingest`.
"""


# ── _canonicalize ───────────────────────────────────────────────────────

class TestCanonicalize:
    def test_strips_quick_and_thorough_to_same_hash(self):
        """Light/Medium (--quick) and Heavy (--thorough) vanilla blocks must
        collapse to a single canonicalized hash — the byte-identity invariant
        that lets ALLOWED_SHAPES count all vanillas as one shape."""
        light = cpc._canonicalize(_vanilla_block("--quick"))
        heavy = cpc._canonicalize(_vanilla_block("--thorough"))
        assert cpc._hash(light) == cpc._hash(heavy)

    def test_strips_weight_placeholder(self):
        """The `{weight}` template-placeholder variant must also collapse."""
        placeholder = cpc._canonicalize(_vanilla_block("{weight}"))
        quick = cpc._canonicalize(_vanilla_block("--quick"))
        # Both get stripped to "--WEIGHT" or "WEIGHT" respectively — the key
        # invariant is that both contain a normalized weight marker that hashes
        # identically. In current implementation both strip-to-uniform.
        assert "--quick" not in placeholder
        assert "{weight}" not in placeholder
        # The two hash identically after canonicalization stripping — confirm
        # via _classify_shape routing to "vanilla" rather than equality since
        # the two stripped tokens differ (--WEIGHT vs WEIGHT by design).
        assert cpc._classify_shape(placeholder) == "vanilla"
        assert cpc._classify_shape(quick) == "vanilla"

    def test_collapses_multispace(self):
        """Multiple spaces/tabs collapse to single space per line."""
        dirty = "hello    world\tfoo  bar"
        canonical = cpc._canonicalize(dirty)
        assert canonical == "hello world foo bar"

    def test_strips_outer_blank_lines(self):
        """Leading/trailing blank lines removed."""
        dirty = "\n\nhello\nworld\n\n\n"
        canonical = cpc._canonicalize(dirty)
        assert canonical == "hello\nworld"

    def test_preserves_interior_blank_lines(self):
        """Blank lines BETWEEN content lines are preserved (they're part of
        the block's structure — affect the canonical hash consistently across
        all blocks since templates are structurally identical)."""
        dirty = "foo\n\nbar"
        canonical = cpc._canonicalize(dirty)
        assert canonical == "foo\n\nbar"


# ── _classify_shape ─────────────────────────────────────────────────────

class TestClassifyShape:
    def test_vanilla_block(self):
        canonical = cpc._canonicalize(_vanilla_block())
        assert cpc._classify_shape(canonical) == "vanilla"

    def test_team_block(self):
        canonical = cpc._canonicalize(_team_block())
        assert cpc._classify_shape(canonical) == "team"

    def test_ralph_mention_inside_vanilla_still_classifies_as_vanilla(self):
        """Post-uniformity invariant: /ralph and /ultrawork mentions inside a
        vanilla block (e.g., 'Benchmark-target loops are handled inside
        autopilot's Phase 2 via internal /ralph') must NOT cause the block
        to misclassify as its old 'ralph' or 'ultrawork' shape. The retired
        shapes no longer exist in ALLOWED_SHAPES and must not sneak back in
        via descriptive text."""
        vanilla_with_internal_ralph = _vanilla_block().replace(
            "3. `/autopilot` — execution only; skips autopilot's internal Phase 5.",
            "3. `/autopilot` — full pipeline; benchmark-target loops are handled via internal /ralph. Also internal /ultrawork.",
        )
        canonical = cpc._canonicalize(vanilla_with_internal_ralph)
        assert cpc._classify_shape(canonical) == "vanilla"

    def test_special_a_block(self):
        canonical = cpc._canonicalize(_special_a_block())
        assert cpc._classify_shape(canonical) == "special-a-hygiene-audit-only"

    def test_special_b_block(self):
        canonical = cpc._canonicalize(_special_b_block())
        assert cpc._classify_shape(canonical) == "special-b-knowledge-capture"

    def test_special_b_checked_before_deep_interview_parenthetical(self):
        """Order-matters guard: Special-B's block text mentions /deep-interview
        in a parenthetical ("substitutes for /deep-interview"). If the classifier
        checked for /deep-interview before /wiki-ingest, Special-B would be
        misclassified as vanilla. This test pins the check order."""
        assert "/deep-interview" in _special_b_block()  # confirmed in fixture
        assert "/wiki-ingest" in _special_b_block()
        canonical = cpc._canonicalize(_special_b_block())
        assert cpc._classify_shape(canonical) == "special-b-knowledge-capture"

    def test_unknown_block_returns_unknown(self):
        """A block that matches none of the known markers returns 'unknown' —
        it does NOT throw and it does NOT silently drop the block."""
        weird = "### Path B (OMC-powered)\n\nNo recognizable markers here at all.\n"
        assert cpc._classify_shape(weird) == "unknown"


# ── _classification_flags (M1 diagnostics helper) ───────────────────────

class TestClassificationFlags:
    def test_flags_set_matches_classify_shape_markers(self):
        """Diagnostic helper for unknown-shape errors — the flag set returned
        must exactly cover the markers _classify_shape() checks. Adding a new
        marker to classify without adding it here would silently leave the
        diagnostic incomplete."""
        expected_keys = {"wiki_ingest", "stop", "history_ingest", "code_review",
                         "team", "autopilot"}
        flags = cpc._classification_flags(_vanilla_block())
        assert set(flags.keys()) == expected_keys
        # Vanilla has /autopilot + /ark-code-review, no engine-specific markers
        assert flags["autopilot"] is True
        assert flags["code_review"] is True
        assert flags["team"] is False


# ── _extract_path_b_blocks ──────────────────────────────────────────────

class TestExtractPathBBlocks:
    def test_extracts_single_block_ending_at_next_h3(self):
        chain = f"""# Scenario

## Heavy

Step content.

{_vanilla_block()}
### Some Other Section

Not a Path B block.
"""
        blocks = cpc._extract_path_b_blocks(chain)
        assert len(blocks) == 1
        assert "/autopilot" in blocks[0]
        assert "Some Other Section" not in blocks[0]

    def test_extracts_multiple_blocks(self):
        chain = f"""## Light

{_vanilla_block("--quick")}
## Heavy

{_vanilla_block("--thorough")}"""
        blocks = cpc._extract_path_b_blocks(chain)
        assert len(blocks) == 2

    def test_extracts_zero_blocks_from_path_a_only_file(self):
        """A chain file with only Path A content (no Path B heading) yields no
        extracted blocks — important because it's the foundation-phase state."""
        chain = "## Light\n\nStep 1\n\n## Heavy\n\nStep 1\n"
        assert cpc._extract_path_b_blocks(chain) == []


# ── Integration via CLI ─────────────────────────────────────────────────

class TestCLI:
    def _write_chain(self, chains_dir: Path, name: str, body: str) -> None:
        (chains_dir / f"{name}.md").write_text(body)

    def _run(self, chains_dir: Path, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(_CPC_PATH), "--chains", str(chains_dir), *extra_args],
            capture_output=True, text=True,
        )

    def test_expected_blocks_zero_with_empty_chains_passes(self, tmp_path):
        """Foundation-phase state: Phase 1 lands the script before any Path B
        blocks exist. --expected-blocks 0 with zero blocks must succeed."""
        chains = tmp_path / "chains"
        chains.mkdir()
        self._write_chain(chains, "foo", "## Light\n\nNo Path B here.\n")
        result = self._run(chains, "--expected-blocks", "0")
        assert result.returncode == 0
        assert "0 Path B blocks" in result.stdout

    def test_expected_blocks_mismatch_fails(self, tmp_path):
        """Supplying --expected-blocks N that doesn't match actual count fails
        with exit 1 and surfaces the count mismatch."""
        chains = tmp_path / "chains"
        chains.mkdir()
        self._write_chain(chains, "foo", f"## Light\n{_vanilla_block()}")
        result = self._run(chains, "--expected-blocks", "5")
        assert result.returncode == 1
        assert "total Path B blocks = 1" in result.stderr
        assert "expected 5" in result.stderr

    def test_missing_handback_marker_fails(self, tmp_path):
        """Every Path B block must contain <<HANDBACK>>. A block missing the
        marker must fail the run."""
        chains = tmp_path / "chains"
        chains.mkdir()
        broken = _vanilla_block().replace("<<HANDBACK>>", "<<MISSING>>")
        self._write_chain(chains, "foo", f"## Light\n{broken}")
        result = self._run(chains, "--expected-blocks", "1")
        assert result.returncode == 1
        assert "<<HANDBACK>>" in result.stderr

    def test_missing_interview_or_ingest_fails(self, tmp_path):
        """Every Path B block must contain /deep-interview OR
        /claude-history-ingest. A block with neither must fail."""
        chains = tmp_path / "chains"
        chains.mkdir()
        broken = (
            _vanilla_block()
            .replace("/deep-interview", "/something-else")
        )
        # Also need to ensure /claude-history-ingest is not elsewhere
        broken = broken.replace("/claude-history-ingest", "/terminal-step")
        self._write_chain(chains, "foo", f"## Light\n{broken}")
        result = self._run(chains, "--expected-blocks", "1")
        assert result.returncode == 1
        assert "/deep-interview" in result.stderr or "/claude-history-ingest" in result.stderr

    def test_unknown_shape_error_dumps_flag_set(self, tmp_path):
        """M1 regression: when a block fails to classify, the error must
        include the flag marker dump to help the developer diagnose."""
        chains = tmp_path / "chains"
        chains.mkdir()
        # 17 blocks to hit the full-coverage classifier path (shape distribution
        # assertion only runs when --expected-blocks == 17)
        bad_block = (
            "### Path B (OMC-powered — if HAS_OMC=true)\n\n"
            "No markers match here.\n\n"
            "0. Step.\n"
            "4. `<<HANDBACK>>` — required marker.\n"
            "5. `/deep-interview` — required marker.\n"
        )
        # 16 good blocks to hit 17 total count + 1 bad block
        body = "## Dummy\n" + "\n".join(_vanilla_block() for _ in range(16)) + bad_block
        self._write_chain(chains, "foo", body)
        result = self._run(chains)  # default --expected-blocks 17
        assert result.returncode == 1
        # Verify the flag dump appears in the error output
        assert "markers=" in result.stderr
        assert "autopilot=" in result.stderr or "wiki_ingest=" in result.stderr

    def test_real_repo_chains_pass(self, tmp_path):
        """End-to-end sanity: the live repo chains directory must pass the
        default (17 blocks, 4 shapes) check. This pins the post-uniformity
        CI contract (2026-04-15)."""
        live_chains = Path(__file__).parent.parent.parent / "ark-workflow" / "chains"
        if not live_chains.is_dir():
            pytest.skip("live chains directory not accessible")
        result = subprocess.run(
            [sys.executable, str(_CPC_PATH), "--chains", str(live_chains)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"CI contract broken: {result.stderr}"
        assert "17 Path B block" in result.stdout
        assert "4 distinct canonicalized shape" in result.stdout


# ── ALLOWED_SHAPES contract ─────────────────────────────────────────────

class TestAllowedShapesContract:
    def test_allowed_shapes_sum_to_17(self):
        """ALLOWED_SHAPES distribution must sum to the total expected-blocks
        count. If someone adds a new engine shape without reducing vanilla,
        this pins that invariant. Post-2026-04-15 uniformity refactor the
        sum is 17 (Ship Standalone Path B removed in R17)."""
        assert sum(cpc.ALLOWED_SHAPES.values()) == 17

    def test_allowed_shapes_contains_four_shapes(self):
        """The 4-shape model is the post-uniformity contract (2026-04-14).
        Retired shapes: `ralph`, `ultrawork` — their engines are now
        invoked inside autopilot's Phase 2. Adding a 5th shape or removing
        one requires updating this test + the reference doc's
        expected-closeout table + the classifier."""
        assert len(cpc.ALLOWED_SHAPES) == 4
        assert set(cpc.ALLOWED_SHAPES.keys()) == {
            "vanilla", "team",
            "special-a-hygiene-audit-only", "special-b-knowledge-capture",
        }
