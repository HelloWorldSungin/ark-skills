"""Tests for context_probe.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_probe as cp  # noqa: E402

FIXTURES = SCRIPTS_DIR / "fixtures" / "context-probe"


class TestProbeLevels:
    def test_ok_fresh(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        assert result["level"] == "ok"
        assert result["pct"] == 5

    def test_ok_warm_just_below_nudge(self):
        result = cp.probe(FIXTURES / "ok-warm.json")
        assert result["level"] == "ok"
        assert result["pct"] == 19

    def test_nudge_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "nudge-low.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 20

    def test_nudge_mid(self):
        result = cp.probe(FIXTURES / "nudge-mid.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28

    def test_nudge_high_just_below_strong(self):
        result = cp.probe(FIXTURES / "nudge-high.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 34

    def test_strong_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "strong-low.json")
        assert result["level"] == "strong"
        assert result["pct"] == 35

    def test_strong_high(self):
        result = cp.probe(FIXTURES / "strong-high.json")
        assert result["level"] == "strong"
        assert result["pct"] == 72

    def test_over_100_clamped(self):
        result = cp.probe(FIXTURES / "over-100.json")
        assert result["level"] == "strong"
        assert result["pct"] == 100  # clamped

    def test_threshold_overrides(self):
        # Custom thresholds: 10/25 instead of 20/35.
        result = cp.probe(FIXTURES / "nudge-mid.json", nudge_pct=10, strong_pct=25)
        assert result["level"] == "strong"  # 28 >= 25 with custom strong


class TestProbeTokens:
    def test_tokens_summed_when_all_subfields_present(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        # 6 + 100 + 1000 + 50000 = 51106
        assert result["tokens"] == 51106
        assert result["warnings"] == []

    def test_tokens_unavailable_when_current_usage_missing(self):
        result = cp.probe(FIXTURES / "missing-current-usage.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]

    def test_tokens_unavailable_when_subfield_non_integer(self):
        result = cp.probe(FIXTURES / "non-integer-token.json")
        assert result["level"] == "nudge"
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]
