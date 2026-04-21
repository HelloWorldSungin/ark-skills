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


# --- Regression tests for review findings H5 / H6 ---

@pytest.mark.parametrize("bad", [
    "TO-DO",         # casing + hyphen variant
    "todo.",         # trailing punctuation
    "TODO!",         # trailing punctuation with bang
    "continuing",    # single filler token
    "tbd again",     # starts with filler token
    "wip wip wip",   # starts with filler prefix
    "todo todo todo todo",  # repetition fills MIN_LENGTH but low distinct-token count
])
def test_H6_harden_generic_bypasses_open_threads(tmp_path, bad):
    """H6: punctuation, casing, filler-prefix, and low-distinct-token bypasses
    must be rejected on open_threads."""
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--open-threads": bad}), cwd=tmp_path)
    assert r.returncode == 2, f"expected exit 2 for bypass {bad!r}; got {r.returncode}, stderr={r.stderr}"
    assert list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md")) == []


@pytest.mark.parametrize("bad", ["", "   ", "tbd", "continue", "wip"])
def test_H5_task_text_is_validated(tmp_path, bad):
    """H5: task_text must be validated too — not only open_threads + next_steps."""
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--task-text": bad}), cwd=tmp_path)
    assert r.returncode == 2, r.stderr
    assert list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md")) == []


@pytest.mark.parametrize("bad", ["tbd", "keep going", "todo todo todo"])
def test_H5_done_summary_validated_when_non_empty(tmp_path, bad):
    """H5: done_summary is optional (empty OK), but when provided must be substantive."""
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--done-summary": bad}), cwd=tmp_path)
    assert r.returncode == 2, r.stderr


def test_H5_done_summary_empty_is_allowed(tmp_path):
    """H5: empty done_summary is the documented default — must still accept."""
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--done-summary": ""}), cwd=tmp_path)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("bad", [
    "has spaces",          # space
    "slash/path",          # slash
    "colon:inside",        # colon
    "UPPER",               # uppercase letters
    "-leading-hyphen",     # must start alnum
    "x" * 33,              # too long (>32)
    "",                    # empty
])
def test_H5_scenario_sanitization(tmp_path, bad):
    """H5: scenario must be a DNS-like slug; reject unsafe values."""
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--scenario": bad}), cwd=tmp_path)
    assert r.returncode == 2, f"scenario {bad!r} should be rejected; got {r.returncode}"
    assert list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md")) == []


@pytest.mark.parametrize("ok", ["greenfield", "bugfix", "ship", "a", "a1-b2", "x" * 32])
def test_H5_scenario_accepts_valid_slugs(tmp_path, ok):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{"--scenario": ok}), cwd=tmp_path)
    assert r.returncode == 0, r.stderr
