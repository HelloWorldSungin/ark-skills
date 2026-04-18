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
