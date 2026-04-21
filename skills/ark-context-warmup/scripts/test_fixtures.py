"""Fixture-driven regression tests for evidence candidates."""
import importlib.util
from pathlib import Path

import yaml

HERE = Path(__file__).parent
FIXTURES_DIR = HERE.parent / "fixtures"

_spec = importlib.util.spec_from_file_location("evidence", HERE / "evidence.py")
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)


def _load_fixture(name: str) -> dict:
    return yaml.safe_load((FIXTURES_DIR / name).read_text())


def _run(fixture: dict) -> list:
    inp = fixture["input"]
    # Preserve None values; only use defaults if key is missing entirely
    wiki = inp.get("wiki", {"matches": []})
    notebooklm = inp.get("notebooklm", {"citations": [], "bootstrap": "", "session_continue": ""})
    return evidence.derive_candidates(
        task_normalized=inp["task_normalized"],
        scenario=inp["scenario"],
        tasknotes=inp.get("tasknotes"),
        notebooklm=notebooklm,
        wiki=wiki,
    )["candidates"]


def _match(candidate: dict, expected: dict) -> bool:
    for k, v in expected.items():
        if candidate.get(k) != v:
            return False
    return True


def _fixture_ids():
    return [p.name for p in sorted(FIXTURES_DIR.glob("*.yaml"))]


import pytest

@pytest.mark.parametrize("fixture_name", _fixture_ids())
def test_fixture(fixture_name: str):
    f = _load_fixture(fixture_name)
    got = _run(f)
    expected = f["expected"]["candidates"]
    for e in expected:
        assert any(_match(g, e) for g in got), (
            f"fixture {fixture_name}: expected candidate {e} not found; got: {got}"
        )
    if f["expected"].get("exact"):
        non_degraded = [g for g in got if g.get("type") != "Degraded coverage"]
        assert len(non_degraded) == len(expected), (
            f"fixture {fixture_name}: extra candidates; got {non_degraded}"
        )
