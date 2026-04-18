"""Tests for the menu-rendering helper inside context_probe.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_probe as cp  # noqa: E402

CHAIN_FIXTURES = SCRIPTS_DIR / "fixtures" / "chain-files"


class TestMidChainRender:
    def test_render_includes_completed_next_remaining(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge",
            pct=28,
            tokens=200_000,
            chain_text=chain_text,
        )
        assert "Context at 28%" in menu
        assert "(~200k)" in menu
        assert "/ark-context-warmup" in menu  # completed
        assert "/investigate" in menu  # completed
        assert "/ark-code-review" in menu  # next
        assert "/ship" in menu  # remaining
        assert "Resuming bugfix chain (medium)" in menu

    def test_render_strong_level_escalates(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="strong",
            pct=42,
            tokens=420_000,
            chain_text=chain_text,
        )
        assert "Context at 42%" in menu
        assert "attention-rot zone" in menu

    def test_render_offers_three_options(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=28, tokens=200_000, chain_text=chain_text,
        )
        assert "(a) /compact focus on the forward brief" in menu
        assert "(b) /clear" in menu
        assert "(c) Delegate Next step to a subagent" in menu
        assert "[a/b/c/proceed]" in menu

    def test_tokens_unavailable_renders_unknown(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=28, tokens=None, chain_text=chain_text,
        )
        assert "Context at 28%" in menu
        # When tokens unknown, the parenthetical is omitted (no ~k suffix)
        assert "(~" not in menu


class TestEntryRender:
    def test_zero_completed_uses_entry_template(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=24, tokens=240_000, chain_text=chain_text,
        )
        assert "before chain has started" in menu
        assert "Starting greenfield chain (heavy)" in menu
        assert "/ark-context-warmup" in menu  # in plan list
        assert "/executing-plans" in menu  # in plan list
        # No Completed/Remaining lines in entry rendering
        assert "Completed:" not in menu
        assert "Remaining:" not in menu
        assert "Plan:" in menu

    def test_entry_option_a_unavailable(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=24, tokens=240_000, chain_text=chain_text,
        )
        assert "(a) /compact — unavailable" in menu
        assert "Which option? [b/c/proceed]" in menu  # constrained answer set

    def test_entry_strong_escalates(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="strong", pct=42, tokens=420_000, chain_text=chain_text,
        )
        assert "attention-rot zone" in menu
        assert "(b)/(c) is strongly recommended" in menu
