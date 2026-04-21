"""Tests for bridge reader affinity logic (7d chain-match, 48h non-match)."""
import os
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, write_page
from read_bridges import pick_bridge

H = 3600


def _make_bridge(wiki: Path, name: str, *, chain_id: str, age_s: float):
    path = wiki / name
    write_page(path, OMCPage(
        frontmatter={"title": f"B {chain_id}", "tags": ["session-bridge"],
                     "chain_id": chain_id, "category": "session-log"},
        body="body",
    ))
    t = time.time() - age_s
    os.utime(path, (t, t))
    return path


def test_chain_match_within_7_days(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    b = _make_bridge(wiki, "a.md", chain_id="CH-X", age_s=5 * 24 * H)
    assert pick_bridge(wiki, current_chain_id="CH-X") == b


def test_chain_match_rejected_past_7_days(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "a.md", chain_id="CH-X", age_s=8 * 24 * H)
    assert pick_bridge(wiki, current_chain_id="CH-X") is None


def test_mismatch_within_48h_most_recent(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "old.md", chain_id="CH-Y", age_s=40 * H)
    r = _make_bridge(wiki, "new.md", chain_id="CH-Z", age_s=6 * H)
    assert pick_bridge(wiki, current_chain_id="CH-NEW") == r


def test_mismatch_rejected_past_48h(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "a.md", chain_id="CH-Y", age_s=72 * H)
    assert pick_bridge(wiki, current_chain_id="CH-NEW") is None


def test_chain_match_preferred_over_recent_mismatch(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    m = _make_bridge(wiki, "match.md", chain_id="CH-X", age_s=2 * 24 * H)
    _make_bridge(wiki, "other.md", chain_id="CH-Y", age_s=1 * H)
    assert pick_bridge(wiki, current_chain_id="CH-X") == m


def test_no_bridges(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    assert pick_bridge(wiki, current_chain_id="CH-X") is None


def test_missing_dir(tmp_path):
    assert pick_bridge(tmp_path / ".omc" / "wiki", current_chain_id="CH-X") is None
