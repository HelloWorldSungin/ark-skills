"""Tests for /wiki-handoff bridge writer."""
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parent / "write_bridge.py"


def run_cli(argv, cwd):
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[2] / "shared" / "python")}
    import os
    env = {**os.environ, **env}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=str(cwd), capture_output=True, text=True, env=env,
    )


def _args(**over):
    base = {
        "--chain-id": "CH-001",
        "--task-text": "Build auth middleware for the Kart service",
        "--scenario": "greenfield",
        "--step-index": "2",
        "--step-count": "5",
        "--session-id": "abcdef01234567890abcdef",
        "--open-threads": "Verify JWT TTL handling in auth/middleware.py:47",
        "--next-steps": "Write integration test tests/test_auth.py covering expired tokens",
        "--notes": "Rate limiter interaction still open",
        "--done-summary": "Implemented JWT validation middleware; 3/5 tests pass",
    }
    base.update(over)
    argv = []
    for k, v in base.items():
        argv.extend([k, v])
    return argv


def test_happy_path_writes_bridge(tmp_path):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    bridges = list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md"))
    assert len(bridges) == 1
    content = bridges[0].read_text()
    assert "Build auth middleware" in content
    assert "JWT TTL" in content
    assert "chain_id: CH-001" in content


@pytest.mark.parametrize("field,bad", [
    ("--open-threads", ""),
    ("--open-threads", "   "),
    ("--open-threads", "continue task"),
    ("--open-threads", "TBD"),
    ("--open-threads", "TODO"),
    ("--open-threads", "keep going"),
    ("--open-threads", "none"),
    ("--open-threads", "x"),
    ("--next-steps", ""),
    ("--next-steps", "continue task"),
])
def test_rejects_generic_placeholders(tmp_path, field, bad):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{field: bad}), cwd=tmp_path)
    assert r.returncode != 0
    assert any(w in r.stderr.lower() for w in ("specific", "generic", "too short", "non-empty"))
    assert list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md")) == []


def test_filename_collision_appends_suffix(tmp_path, monkeypatch):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    monkeypatch.setenv("WIKI_HANDOFF_FIXED_STAMP", "2026-04-20-143005")
    r1 = run_cli(_args(), cwd=tmp_path)
    r2 = run_cli(_args(), cwd=tmp_path)
    r3 = run_cli(_args(), cwd=tmp_path)
    assert r1.returncode == 0 and r2.returncode == 0 and r3.returncode == 0
    names = sorted(p.name for p in wiki.glob("session-bridge-*.md"))
    assert len(names) == 3
    # Exactly one file lacks a -N suffix; the other two have -2 and -3
    unsuffixed = [n for n in names if not (n.endswith("-2.md") or n.endswith("-3.md"))]
    assert len(unsuffixed) == 1
    assert any(n.endswith("-2.md") for n in names)
    assert any(n.endswith("-3.md") for n in names)


def test_missing_omc_wiki_dir_exits_silently(tmp_path):
    r = run_cli(_args(), cwd=tmp_path)
    assert r.returncode == 0


def test_bridge_frontmatter_has_chain_id_and_tags(tmp_path):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    bridge = list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md"))[0]
    text = bridge.read_text()
    assert "chain_id: CH-001" in text
    assert "session-bridge" in text
    assert "source-handoff" in text
    assert "scenario-greenfield" in text
