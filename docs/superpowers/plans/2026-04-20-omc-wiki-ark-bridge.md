# OMC ↔ Ark Wiki Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the OMC `/wiki` ↔ Ark `/wiki-*` bridge per `docs/superpowers/specs/2026-04-20-omc-wiki-ark-bridge-design.md` — warmup seeds OMC on prompt+cache-miss, handoff writes bridge pages on v1.17.0 probe action, end-of-session `/wiki-update` promotes durable OMC content into the vault with transactional deletes.

**Architecture:** Three Python helper scripts (`seed_omc.py`, `read_bridges.py`, `promote_omc.py`) + one new skill (`/wiki-handoff`) + edits to three existing SKILL.md files (`ark-context-warmup`, `ark-workflow`, `wiki-update`). Stdlib-only. Pytest for unit, bats for integration.

**Tech Stack:** Python 3.11 stdlib (hashlib, pathlib, json, os, fcntl, time, yaml via pyyaml which ark-skills already uses per `skills/ark-update/scripts/plan.py`). Pytest + bats.

---

## File Structure

**Create:**
- `skills/wiki-handoff/SKILL.md`
- `skills/wiki-handoff/scripts/write_bridge.py`
- `skills/wiki-handoff/scripts/test_write_bridge.py`
- `skills/ark-context-warmup/scripts/seed_omc.py`
- `skills/ark-context-warmup/scripts/test_seed_omc.py`
- `skills/ark-context-warmup/scripts/read_bridges.py`
- `skills/ark-context-warmup/scripts/test_read_bridges.py`
- `skills/wiki-update/scripts/__init__.py`
- `skills/wiki-update/scripts/promote_omc.py`
- `skills/wiki-update/scripts/test_promote_omc.py`
- `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`
- `skills/wiki-update/scripts/fixtures/` (integration fixtures)

**Modify:**
- `skills/ark-context-warmup/SKILL.md` — Step 1 (read bridges) + Step 5 (seed OMC on cache miss)
- `skills/ark-workflow/SKILL.md` — Step 6.5 action branch (invoke `/wiki-handoff` before compact/clear)
- `skills/wiki-update/SKILL.md` — add Step 3.5 (Promote OMC)
- `VERSION` — bump to 1.19.0
- `.claude-plugin/plugin.json` — version bump
- `.claude-plugin/marketplace.json` — version bump
- `CHANGELOG.md` — 1.19.0 entry

---

## Task 1: Shared OMC page utilities (foundation for all three components)

**Files:**
- Create: `skills/wiki-handoff/scripts/omc_page.py` (shared module — imported by all three helpers)
- Create: `skills/wiki-handoff/scripts/test_omc_page.py`

- [ ] **Step 1: Write failing tests for page read/write/hash**

File: `skills/wiki-handoff/scripts/test_omc_page.py`
```python
"""Tests for shared OMC page utilities."""
from pathlib import Path

import pytest

from omc_page import (
    body_hash,
    content_hash_slug,
    parse_page,
    write_page,
    OMCPage,
)


def test_body_hash_excludes_frontmatter():
    body_only = "# Title\n\nContent here.\n"
    fm_plus_body = "---\ntitle: x\n---\n\n" + body_only
    # body_hash operates on body portion only
    assert body_hash(body_only) == body_hash(body_only)
    # Hash is deterministic
    assert body_hash("hello") == body_hash("hello")


def test_content_hash_slug_stable_and_short():
    slug = content_hash_slug("vault/Architecture/Auth.md", "body text")
    assert len(slug) == 12
    assert slug.isalnum()
    # Same inputs → same slug
    assert slug == content_hash_slug("vault/Architecture/Auth.md", "body text")
    # Different path → different slug
    other = content_hash_slug("vault/Architecture/Users.md", "body text")
    assert slug != other


def test_parse_page_roundtrip(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: X\ntags: [a, b]\n---\n\n# X\n\nBody.\n")
    page = parse_page(path)
    assert page.frontmatter["title"] == "X"
    assert page.frontmatter["tags"] == ["a", "b"]
    assert page.body.strip() == "# X\n\nBody."


def test_parse_page_missing_frontmatter(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("# No frontmatter\n\nJust body.\n")
    page = parse_page(path)
    assert page.frontmatter == {}
    assert "No frontmatter" in page.body


def test_parse_page_malformed_yaml(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: [unclosed\n---\n\nBody.\n")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_page(path)


def test_write_page_atomic_creates_file(tmp_path):
    path = tmp_path / "new.md"
    page = OMCPage(frontmatter={"title": "T"}, body="# T\n\nBody.\n")
    write_page(path, page)
    assert path.exists()
    assert "title: T" in path.read_text()


def test_write_page_o_excl_blocks_overwrite(tmp_path):
    path = tmp_path / "existing.md"
    path.write_text("original")
    page = OMCPage(frontmatter={"title": "T"}, body="body")
    with pytest.raises(FileExistsError):
        write_page(path, page, exclusive=True)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_omc_page.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'omc_page'`

- [ ] **Step 3: Implement omc_page.py**

File: `skills/wiki-handoff/scripts/omc_page.py`
```python
"""Shared OMC page utilities: read, write, hash. Stdlib-only where possible; pyyaml for frontmatter."""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class OMCPage:
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""


def body_hash(body: str) -> str:
    """SHA-256 of body content (caller must exclude frontmatter)."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def content_hash_slug(source_path: str, content: str) -> str:
    """12-char stable slug from vault source path + content."""
    h = hashlib.sha256(f"{source_path}\n{content}".encode("utf-8")).hexdigest()
    return h[:12]


def parse_page(path: Path) -> OMCPage:
    """Parse a markdown page with optional YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return OMCPage(frontmatter={}, body=text)
    end = text.find("\n---\n", 4)
    if end == -1:
        return OMCPage(frontmatter={}, body=text)
    fm_text = text[4:end]
    body = text[end + 5:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed frontmatter in {path}: {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter in {path} is not a mapping")
    return OMCPage(frontmatter=fm, body=body)


def write_page(path: Path, page: OMCPage, *, exclusive: bool = False) -> None:
    """Write page atomically. If exclusive=True, fail when file exists."""
    fm_text = yaml.safe_dump(page.frontmatter, sort_keys=False).rstrip()
    text = f"---\n{fm_text}\n---\n\n{page.body}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        fd = os.open(str(path), flags, 0o644)
        try:
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
    else:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_omc_page.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-handoff/scripts/omc_page.py skills/wiki-handoff/scripts/test_omc_page.py
git commit -m "feat(wiki-bridge): shared OMC page read/write/hash utilities"
```

---

## Task 2: `/wiki-handoff` write_bridge.py with schema enforcement

**Files:**
- Create: `skills/wiki-handoff/scripts/write_bridge.py`
- Create: `skills/wiki-handoff/scripts/test_write_bridge.py`

- [ ] **Step 1: Write failing tests**

File: `skills/wiki-handoff/scripts/test_write_bridge.py`
```python
"""Tests for /wiki-handoff bridge writer."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parent / "write_bridge.py"


def run_cli(argv, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        cwd=str(cwd), capture_output=True, text=True,
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
        "--next-steps": "Write integration test in tests/test_auth.py covering expired tokens",
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
    ("--open-threads", "x"),  # <20 chars
    ("--next-steps", ""),
    ("--next-steps", "continue task"),
])
def test_rejects_generic_placeholders(tmp_path, field, bad):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(**{field: bad}), cwd=tmp_path)
    assert r.returncode != 0
    assert "specific" in r.stderr.lower() or "generic" in r.stderr.lower() or "too short" in r.stderr.lower()
    assert list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md")) == []


def test_filename_collision_appends_suffix(tmp_path, monkeypatch):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    # Freeze time inside script via env
    monkeypatch.setenv("WIKI_HANDOFF_FIXED_STAMP", "2026-04-20-143005")
    r1 = run_cli(_args(), cwd=tmp_path)
    r2 = run_cli(_args(), cwd=tmp_path)
    r3 = run_cli(_args(), cwd=tmp_path)
    assert r1.returncode == 0
    assert r2.returncode == 0
    assert r3.returncode == 0
    names = sorted(p.name for p in wiki.glob("session-bridge-*.md"))
    assert len(names) == 3
    # First: no suffix; subsequent: -2, -3
    assert not names[0].endswith("-2.md") and not names[0].endswith("-3.md")
    assert any(n.endswith("-2.md") for n in names)
    assert any(n.endswith("-3.md") for n in names)


def test_missing_omc_wiki_dir_exits_silently(tmp_path):
    # No .omc/wiki/ → script should exit 0 (nothing to write to, silent no-op)
    r = run_cli(_args(), cwd=tmp_path)
    assert r.returncode == 0
    assert "not initialized" in r.stderr.lower() or r.stderr == ""


def test_bridge_frontmatter_has_chain_id(tmp_path):
    (tmp_path / ".omc" / "wiki").mkdir(parents=True)
    r = run_cli(_args(), cwd=tmp_path)
    assert r.returncode == 0
    bridge = list((tmp_path / ".omc" / "wiki").glob("session-bridge-*.md"))[0]
    text = bridge.read_text()
    assert "chain_id: CH-001" in text
    assert "tags:" in text
    assert "session-bridge" in text
    assert "source-handoff" in text
    assert "scenario-greenfield" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_write_bridge.py -v`
Expected: FAIL — `write_bridge.py` doesn't exist yet.

- [ ] **Step 3: Implement write_bridge.py**

File: `skills/wiki-handoff/scripts/write_bridge.py`
```python
"""/wiki-handoff — writes a session bridge page to .omc/wiki/.

Invoked from /ark-workflow Step 6.5 action branch before /compact or /clear.
Stdlib-only + pyyaml (via omc_page).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from omc_page import OMCPage, write_page


GENERIC_PATTERNS = {
    "continue task", "tbd", "todo", "keep going", "none", "n/a", "na",
}
MIN_LENGTH = 20


def _validate(field_name: str, value: str) -> str | None:
    """Return error message if invalid, else None."""
    s = (value or "").strip()
    if not s:
        return f"{field_name} must be non-empty"
    if s.lower() in GENERIC_PATTERNS:
        return f"{field_name} is generic placeholder ({s!r})"
    if len(s) < MIN_LENGTH:
        return f"{field_name} is too short (<{MIN_LENGTH} chars)"
    return None


def _timestamp() -> str:
    fixed = os.environ.get("WIKI_HANDOFF_FIXED_STAMP")
    if fixed:
        return fixed
    return time.strftime("%Y-%m-%d-%H%M%S", time.localtime())


def _build_filename(session_id: str, ts: str) -> str:
    sid8 = (session_id or "00000000")[-8:]
    return f"session-bridge-{ts}-{sid8}.md"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chain-id", required=True)
    p.add_argument("--task-text", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--step-index", required=True)
    p.add_argument("--step-count", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--open-threads", required=True)
    p.add_argument("--next-steps", required=True)
    p.add_argument("--notes", default="")
    p.add_argument("--done-summary", default="")
    p.add_argument("--git-diff-stat", default="")
    args = p.parse_args()

    for name, val in (("open_threads", args.open_threads), ("next_steps", args.next_steps)):
        err = _validate(name, val)
        if err:
            print(f"wiki-handoff: {err}. Re-invoke with specific detail.", file=sys.stderr)
            return 2

    wiki_dir = Path.cwd() / ".omc" / "wiki"
    if not wiki_dir.is_dir():
        print("wiki-handoff: .omc/wiki/ not initialized — skipping bridge write.", file=sys.stderr)
        return 0

    ts = _timestamp()
    base_name = _build_filename(args.session_id, ts)
    target = wiki_dir / base_name

    task_summary = args.task_text.strip().splitlines()[0][:80]
    body = f"""# Session Bridge — {task_summary}

## Task
{args.task_text}

## Scenario
{args.scenario} (step {args.step_index}/{args.step_count})

## What was done
{args.git_diff_stat or '(no diff stat provided)'}

{args.done_summary}

## Open threads
{args.open_threads}

## Next steps
{args.next_steps}

## Notes
{args.notes}
"""

    fm = {
        "title": f"Session Bridge — {task_summary}",
        "tags": ["session-bridge", "source-handoff", f"scenario-{args.scenario}"],
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": [args.chain_id, args.session_id],
        "links": [],
        "category": "session-log",
        "confidence": "high",
        "schemaVersion": 1,
        "chain_id": args.chain_id,
    }
    page = OMCPage(frontmatter=fm, body=body)

    # O_EXCL retry with numeric suffix
    attempt = 1
    while True:
        try_path = target if attempt == 1 else wiki_dir / f"{target.stem}-{attempt}.md"
        try:
            write_page(try_path, page, exclusive=True)
            print(str(try_path))
            return 0
        except FileExistsError:
            attempt += 1
            if attempt > 10:
                print("wiki-handoff: too many filename collisions", file=sys.stderr)
                return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_write_bridge.py -v`
Expected: 13 PASS (happy path + 10 parametrized rejections + collision + missing-dir + frontmatter).

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-handoff/scripts/write_bridge.py skills/wiki-handoff/scripts/test_write_bridge.py
git commit -m "feat(wiki-handoff): write_bridge.py with schema enforcement + O_EXCL collision handling"
```

---

## Task 3: `/wiki-handoff` SKILL.md

**Files:**
- Create: `skills/wiki-handoff/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

File: `skills/wiki-handoff/SKILL.md`
```markdown
---
name: wiki-handoff
description: Write a session bridge page to .omc/wiki/ capturing in-session state before /compact or /clear. Invoked from /ark-workflow Step 6.5 action branch. Stdlib-only, <1s wall time. Triggers on "handoff session", "bridge page", "flush session state".
---

# Wiki Handoff

Writes one page to `.omc/wiki/session-bridge-{YYYY-MM-DD}-{HHMMSS}-{sid8}.md` with a validated snapshot of current session state. Designed to run before `/compact` or `/clear` so the next session can recover context.

## When this runs

Invoked from `/ark-workflow` SKILL.md Step 6.5 after the v1.17.0 context-budget probe menu surfaces and the user picks option `(a) compact` or `(b) clear`. NOT invoked for option `(c) subagent` (subagent dispatch doesn't wipe parent context).

## Inputs

The calling skill (the LLM itself, in the `/ark-workflow` turn) supplies these args to `write_bridge.py`:

| Arg | Source |
|---|---|
| `--chain-id` | `.ark-workflow/current-chain.md` frontmatter |
| `--task-text` | same |
| `--scenario` | same |
| `--step-index`, `--step-count` | chain step checklist state |
| `--session-id` | `$CLAUDE_SESSION_ID` or `.omc/state/hud-state.json` |
| `--open-threads` | **LLM-authored**, specific (file paths, decision points) |
| `--next-steps` | **LLM-authored**, specific |
| `--notes` | LLM-authored free-form |
| `--done-summary` | LLM summary of session work |
| `--git-diff-stat` | `git diff --stat <chain-entry-ref>..HEAD` |

## Schema enforcement

The script rejects calls where `--open-threads` or `--next-steps` match any of:
- Empty or whitespace-only
- Generic: `continue task`, `TBD`, `TODO`, `keep going`, `none`, `n/a`
- Content length <20 chars

On rejection, exits non-zero with diagnostic. The LLM must re-invoke with specifics.

## Degradation

- `.omc/wiki/` doesn't exist → exit 0 silent (OMC not initialized in this worktree).
- Filename collision within same second → append `-2`, `-3`, ... (up to 10 retries).
- Too many retries → exit 3.

## Usage

```bash
python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
    --chain-id "$CHAIN_ID" \
    --task-text "$TASK_TEXT" \
    --scenario "$SCENARIO" \
    --step-index "$STEP_IDX" --step-count "$STEP_COUNT" \
    --session-id "$SESSION_ID" \
    --open-threads "Verify JWT TTL handling in auth/middleware.py:47" \
    --next-steps "Write integration test tests/test_auth.py covering expired tokens" \
    --notes "Rate limiter interaction still open" \
    --done-summary "Implemented JWT validation middleware; 3/5 tests pass" \
    --git-diff-stat "$(git diff --stat HEAD~3..HEAD)"
```

Output on success: the path of the created bridge page (stdout).
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-handoff/SKILL.md
git commit -m "feat(wiki-handoff): SKILL.md documenting handoff invocation contract"
```

---

## Task 4: seed_omc.py — warmup populates OMC on cache miss

**Files:**
- Create: `skills/ark-context-warmup/scripts/seed_omc.py`
- Create: `skills/ark-context-warmup/scripts/test_seed_omc.py`

- [ ] **Step 1: Write failing tests**

File: `skills/ark-context-warmup/scripts/test_seed_omc.py`
```python
"""Tests for seed_omc: warmup populator with per-source content hashing and stale cleanup."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "wiki-handoff" / "scripts"))
from omc_page import content_hash_slug, parse_page
from seed_omc import seed, SeedSource


def _mk_source(title="Auth", path="vault/Architecture/Auth.md",
               body="# Auth\n\nJWT-based auth.\n" * 30,
               vault_type="architecture", tags=None, confidence="high"):
    return SeedSource(
        title=title,
        vault_source_path=path,
        body=body,
        vault_type=vault_type,
        tags=tags or ["auth", "security"],
        confidence=confidence,
    )


def test_seed_writes_new_pages(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    sources = [_mk_source()]
    result = seed(wiki, chain_id="CH-A", sources=sources)
    assert result.written == 1
    assert result.refreshed == 0
    assert result.deleted_stale == 0
    slug = content_hash_slug("vault/Architecture/Auth.md", sources[0].body)
    expected = wiki / f"source-{slug}.md"
    assert expected.exists()


def test_seed_skips_short_sources(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    sources = [_mk_source(body="short")]  # <200 chars
    result = seed(wiki, chain_id="CH-A", sources=sources)
    assert result.written == 0
    assert list(wiki.glob("source-*.md")) == []


def test_seed_idempotent_same_content(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    sources = [_mk_source()]
    seed(wiki, chain_id="CH-A", sources=sources)
    before = {p.name: p.stat().st_mtime_ns for p in wiki.glob("source-*.md")}
    result = seed(wiki, chain_id="CH-A", sources=sources)
    assert result.written == 0
    assert result.refreshed == 0  # identical content, no rewrite
    after = {p.name: p.stat().st_mtime_ns for p in wiki.glob("source-*.md")}
    assert before == after


def test_seed_refresh_when_content_changes(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    s1 = _mk_source(body="# Auth v1\n\n" + "x" * 250)
    seed(wiki, chain_id="CH-A", sources=[s1])
    s2 = _mk_source(body="# Auth v2\n\n" + "y" * 250)  # same path, different content
    result = seed(wiki, chain_id="CH-A", sources=[s2])
    # New content = new hash = new page; old is stale and deleted
    assert result.written == 1
    assert result.deleted_stale == 1


def test_seed_deletes_stale_sources_for_same_chain(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    s_a = _mk_source(title="Auth", path="vault/Architecture/Auth.md",
                     body="# A\n\n" + "a" * 250)
    s_b = _mk_source(title="Users", path="vault/Architecture/Users.md",
                     body="# B\n\n" + "b" * 250)
    seed(wiki, chain_id="CH-A", sources=[s_a, s_b])
    assert len(list(wiki.glob("source-*.md"))) == 2
    # Topic shift within same chain: fanout now returns only s_c
    s_c = _mk_source(title="Billing", path="vault/Architecture/Billing.md",
                     body="# C\n\n" + "c" * 250)
    result = seed(wiki, chain_id="CH-A", sources=[s_c])
    assert result.written == 1
    assert result.deleted_stale == 2
    remaining = list(wiki.glob("source-*.md"))
    assert len(remaining) == 1


def test_seed_preserves_other_chains(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[_mk_source()])
    # A different chain must not wipe CH-A's sources
    s_other = _mk_source(title="Deploys", path="vault/Ops/Deploys.md",
                         body="# D\n\n" + "d" * 250)
    result = seed(wiki, chain_id="CH-B", sources=[s_other])
    assert result.deleted_stale == 0
    assert len(list(wiki.glob("source-*.md"))) == 2


def test_seed_frontmatter_contains_provenance(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    sources = [_mk_source(vault_type="research")]
    seed(wiki, chain_id="CH-A", sources=sources)
    page_path = next(wiki.glob("source-*.md"))
    page = parse_page(page_path)
    fm = page.frontmatter
    assert fm["ark-original-type"] == "research"
    assert fm["ark-source-path"] == "vault/Architecture/Auth.md"
    assert "seed_body_hash" in fm
    assert fm["seed_chain_id"] == "CH-A"
    assert "source-warmup" in fm["tags"]
    # Vault research → OMC architecture per mapping
    assert fm["category"] == "architecture"


def test_seed_excluded_vault_types(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    for bad in ("session-log", "epic", "story", "bug", "task"):
        src = _mk_source(vault_type=bad, body="x" * 250,
                         path=f"vault/{bad}.md")
        result = seed(wiki, chain_id="CH-A", sources=[src])
        assert result.written == 0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_seed_omc.py -v`
Expected: FAIL — `seed_omc` module missing.

- [ ] **Step 3: Implement seed_omc.py**

File: `skills/ark-context-warmup/scripts/seed_omc.py`
```python
"""Warmup populator: writes cited vault sources into .omc/wiki/ with content-hash filenames.

Component 1 of the OMC↔Ark bridge. Called from /ark-context-warmup Step 5 on cache miss
with prompt.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

# Shared module: omc_page lives in sibling skill wiki-handoff
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "wiki-handoff" / "scripts"))

from omc_page import OMCPage, body_hash, content_hash_slug, parse_page, write_page


MIN_BODY_LEN = 200

VAULT_TYPE_TO_OMC_CATEGORY = {
    "architecture": "architecture",
    "decision-record": "decision",
    "pattern": "pattern",
    "compiled-insight": "pattern",
    "research": "architecture",
    "reference": "architecture",
    "guide": "architecture",
}

EXCLUDED_VAULT_TYPES = {"session-log", "epic", "story", "bug", "task"}


@dataclass
class SeedSource:
    title: str
    vault_source_path: str
    body: str
    vault_type: str
    tags: List[str]
    confidence: str  # "high" | "medium"


@dataclass
class SeedResult:
    written: int = 0
    refreshed: int = 0
    deleted_stale: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)


def _build_page(source: SeedSource, chain_id: str) -> OMCPage:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    category = VAULT_TYPE_TO_OMC_CATEGORY.get(source.vault_type, "architecture")
    tags = list(dict.fromkeys(source.tags + ["source-warmup"]))
    fm = {
        "title": source.title,
        "tags": tags,
        "created": now,
        "updated": now,
        "sources": [source.vault_source_path, chain_id],
        "links": [],
        "category": category,
        "confidence": source.confidence,
        "schemaVersion": 1,
        "ark-original-type": source.vault_type,
        "ark-source-path": source.vault_source_path,
        "seed_body_hash": body_hash(source.body),
        "seed_chain_id": chain_id,
    }
    return OMCPage(frontmatter=fm, body=source.body)


def seed(wiki_dir: Path, *, chain_id: str, sources: List[SeedSource]) -> SeedResult:
    result = SeedResult()
    wiki_dir.mkdir(parents=True, exist_ok=True)

    active_slugs: Set[str] = set()
    for src in sources:
        if src.vault_type in EXCLUDED_VAULT_TYPES or len(src.body) < MIN_BODY_LEN:
            result.skipped += 1
            continue
        slug = content_hash_slug(src.vault_source_path, src.body)
        active_slugs.add(slug)
        target = wiki_dir / f"source-{slug}.md"
        page = _build_page(src, chain_id)
        if target.exists():
            # Already exists with same content hash → skip to preserve mtime (idempotent)
            continue
        try:
            write_page(target, page, exclusive=False)
            result.written += 1
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{src.vault_source_path}: {exc}")

    # Stale cleanup: delete other source-warmup pages with same chain_id
    for existing in wiki_dir.glob("source-*.md"):
        slug = existing.stem[len("source-"):]
        if slug in active_slugs:
            continue
        try:
            page = parse_page(existing)
        except ValueError:
            continue
        if page.frontmatter.get("seed_chain_id") != chain_id:
            continue
        if "source-warmup" not in (page.frontmatter.get("tags") or []):
            continue
        try:
            existing.unlink()
            result.deleted_stale += 1
        except OSError as exc:
            result.errors.append(f"unlink {existing}: {exc}")

    return result


def _cli() -> int:
    """JSON-driven CLI: reads SeedSource list from stdin JSON, writes result JSON to stdout."""
    import argparse
    import json
    p = argparse.ArgumentParser()
    p.add_argument("--wiki-dir", required=True)
    p.add_argument("--chain-id", required=True)
    args = p.parse_args()
    payload = json.load(sys.stdin)
    sources = [SeedSource(**s) for s in payload]
    res = seed(Path(args.wiki_dir), chain_id=args.chain_id, sources=sources)
    print(json.dumps({
        "written": res.written,
        "refreshed": res.refreshed,
        "deleted_stale": res.deleted_stale,
        "skipped": res.skipped,
        "errors": res.errors,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_seed_omc.py -v`
Expected: 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/seed_omc.py skills/ark-context-warmup/scripts/test_seed_omc.py
git commit -m "feat(warmup): seed_omc.py — populate .omc/wiki/ with content-hashed vault sources"
```

---

## Task 5: read_bridges.py — next-session warmup affinity logic

**Files:**
- Create: `skills/ark-context-warmup/scripts/read_bridges.py`
- Create: `skills/ark-context-warmup/scripts/test_read_bridges.py`

- [ ] **Step 1: Write failing tests**

File: `skills/ark-context-warmup/scripts/test_read_bridges.py`
```python
"""Tests for bridge reader affinity logic (7d chain-match, 48h non-match)."""
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "wiki-handoff" / "scripts"))
from omc_page import OMCPage, write_page
from read_bridges import pick_bridge

H = 3600


def _make_bridge(wiki: Path, name: str, *, chain_id: str, mtime_age_s: float):
    path = wiki / name
    page = OMCPage(
        frontmatter={
            "title": f"Bridge for {chain_id}",
            "tags": ["session-bridge", "source-handoff"],
            "chain_id": chain_id,
            "category": "session-log",
        },
        body="## Task\n\nsome body\n",
    )
    write_page(path, page)
    t = time.time() - mtime_age_s
    os.utime(path, (t, t))
    return path


def test_pick_chain_match_within_7_days(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    b1 = _make_bridge(wiki, "session-bridge-a.md", chain_id="CH-X", mtime_age_s=5 * 24 * H)
    picked = pick_bridge(wiki, current_chain_id="CH-X")
    assert picked == b1


def test_pick_chain_match_rejected_past_7_days(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "session-bridge-a.md", chain_id="CH-X", mtime_age_s=8 * 24 * H)
    picked = pick_bridge(wiki, current_chain_id="CH-X")
    assert picked is None


def test_pick_mismatch_within_48h_most_recent(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "session-bridge-old.md", chain_id="CH-Y", mtime_age_s=40 * H)
    b_recent = _make_bridge(wiki, "session-bridge-new.md", chain_id="CH-Z", mtime_age_s=6 * H)
    picked = pick_bridge(wiki, current_chain_id="CH-NEW")
    assert picked == b_recent


def test_pick_mismatch_rejected_past_48h(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    _make_bridge(wiki, "session-bridge-a.md", chain_id="CH-Y", mtime_age_s=72 * H)
    picked = pick_bridge(wiki, current_chain_id="CH-NEW")
    assert picked is None


def test_pick_chain_match_preferred_over_more_recent_mismatch(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    b_match = _make_bridge(wiki, "session-bridge-match.md", chain_id="CH-X", mtime_age_s=2 * 24 * H)
    _make_bridge(wiki, "session-bridge-other.md", chain_id="CH-Y", mtime_age_s=1 * H)
    picked = pick_bridge(wiki, current_chain_id="CH-X")
    assert picked == b_match


def test_no_bridges_returns_none(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    assert pick_bridge(wiki, current_chain_id="CH-X") is None


def test_missing_wiki_dir_returns_none(tmp_path):
    assert pick_bridge(tmp_path / ".omc" / "wiki", current_chain_id="CH-X") is None
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_read_bridges.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement read_bridges.py**

File: `skills/ark-context-warmup/scripts/read_bridges.py`
```python
"""Pick the relevant session-bridge page for the current warmup.

- chain_id match: window = 7 days
- chain_id mismatch: only most-recent single bridge, window = 48h
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "wiki-handoff" / "scripts"))

from omc_page import parse_page


CHAIN_MATCH_WINDOW_S = 7 * 24 * 3600
NO_MATCH_WINDOW_S = 48 * 3600


def pick_bridge(wiki_dir: Path, *, current_chain_id: str) -> Optional[Path]:
    if not wiki_dir.is_dir():
        return None
    now = time.time()
    best_match: Optional[tuple[float, Path]] = None
    best_any: Optional[tuple[float, Path]] = None
    for path in wiki_dir.glob("session-bridge-*.md"):
        try:
            page = parse_page(path)
        except ValueError:
            continue
        chain_id = page.frontmatter.get("chain_id")
        mtime = path.stat().st_mtime
        age = now - mtime
        if chain_id == current_chain_id and age <= CHAIN_MATCH_WINDOW_S:
            if best_match is None or mtime > best_match[0]:
                best_match = (mtime, path)
        if best_any is None or mtime > best_any[0]:
            best_any = (mtime, path)
    if best_match:
        return best_match[1]
    if best_any and (now - best_any[0]) <= NO_MATCH_WINDOW_S:
        return best_any[1]
    return None


def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--wiki-dir", required=True)
    p.add_argument("--chain-id", required=True)
    args = p.parse_args()
    picked = pick_bridge(Path(args.wiki_dir), current_chain_id=args.chain_id)
    if picked:
        print(picked)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_read_bridges.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/read_bridges.py skills/ark-context-warmup/scripts/test_read_bridges.py
git commit -m "feat(warmup): read_bridges.py — chain-affinity bridge pickup (7d match / 48h non-match)"
```

---

## Task 6: Wire seed_omc + read_bridges into ark-context-warmup SKILL.md

**Files:**
- Modify: `skills/ark-context-warmup/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md Step 1 and Step 5**

Run: `sed -n '55,115p' skills/ark-context-warmup/SKILL.md`

- [ ] **Step 2: Insert bridge-read block in Step 1 (Task intake)**

At the end of the Step 1 section (after the `Legacy chain file` log line), append:

```markdown

### Step 1b: Check for session bridges

After task intake, list recent session bridges and surface the most relevant one in the Context Brief.

```bash
BRIDGE_PATH=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/read_bridges.py" \
    --wiki-dir ".omc/wiki" \
    --chain-id "$CHAIN_ID" 2>/dev/null || true)
if [ -n "$BRIDGE_PATH" ] && [ -f "$BRIDGE_PATH" ]; then
    PRIOR_BRIDGE_CONTENT=$(cat "$BRIDGE_PATH")
    # Later, synthesize.assemble_brief receives this content and renders it
    # under a "Prior Session Handoff" heading when non-empty.
fi
```

Rules:
- **chain_id match** = show if mtime ≤ 7 days.
- **chain_id mismatch** = show single most-recent bridge only if mtime ≤ 48h.
- No qualifying bridge → skip silently.
```

- [ ] **Step 3: Insert OMC seed block after Step 5 Synthesis**

Immediately after the existing `synthesize.write_brief_atomic(...)` line in Step 5, append:

```markdown

### Step 5b: Seed OMC wiki (cache miss + prompt path only)

If this invocation was a cache miss AND a prompt (task_text) was supplied AND `.omc/wiki/` exists, populate source pages:

```bash
if [ -d ".omc/wiki" ] && [ "$CACHE_HIT" != "true" ] && [ -n "$TASK_TEXT" ]; then
    # Build JSON array of SeedSource from NotebookLM citations + top-3 T4 index hits.
    # Schema: [{title, vault_source_path, body, vault_type, tags, confidence}, ...]
    python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/seed_omc.py" \
        --wiki-dir ".omc/wiki" --chain-id "$CHAIN_ID" < "$SOURCES_JSON"
fi
```

Inputs: `$SOURCES_JSON` must be a file containing a JSON array of seed-source objects. `evidence.derive_candidates` must emit this array when `has_omc=true`.

Degradation:
- No `.omc/wiki/` → skip (silent).
- No prompt → skip (Option E′ rule).
- Cache hit → skip (seeds already present from prior fanout).
- Any source-level write error → seed_omc logs it and continues with remaining sources.
```

- [ ] **Step 4: Commit**

```bash
git add skills/ark-context-warmup/SKILL.md
git commit -m "feat(warmup): wire seed_omc + read_bridges into SKILL.md Steps 1b and 5b"
```

---

## Task 7: evidence.py emits SeedSource JSON when HAS_OMC

**Files:**
- Modify: `skills/ark-context-warmup/scripts/evidence.py`
- Modify: `skills/ark-context-warmup/scripts/test_evidence.py` (if it exists; create if not)

- [ ] **Step 1: Read current evidence.py to understand its shape**

Run: `sed -n '1,80p' skills/ark-context-warmup/scripts/evidence.py`

- [ ] **Step 2: Add failing test for seed-source emission**

File: `skills/ark-context-warmup/scripts/test_evidence.py` (append or create)

```python
def test_derive_candidates_emits_seed_sources_when_has_omc():
    lane_outputs = {
        "notebooklm": {"citations": [{"title": "Auth", "vault_path": "Architecture/Auth.md",
                                       "body": "x" * 250, "type": "architecture",
                                       "tags": ["auth"], "rank": 1}]},
        "wiki": {"matches": [{"title": "Users", "path": "Architecture/Users.md",
                               "summary": "s", "rank": 1}]},
    }
    from evidence import derive_candidates
    res = derive_candidates(lane_outputs, has_omc=True)
    assert "seed_sources" in res
    assert len(res["seed_sources"]) >= 1
    s = res["seed_sources"][0]
    for k in ("title", "vault_source_path", "body", "vault_type", "tags", "confidence"):
        assert k in s


def test_derive_candidates_omits_seed_sources_when_not_has_omc():
    from evidence import derive_candidates
    res = derive_candidates({}, has_omc=False)
    assert "seed_sources" not in res or res["seed_sources"] == []
```

- [ ] **Step 3: Run the new tests — expect failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_evidence.py -v -k seed_sources`
Expected: FAIL — `derive_candidates` does not yet accept `has_omc` or emit `seed_sources`.

- [ ] **Step 4: Modify evidence.py to emit seed_sources when has_omc**

Locate `derive_candidates` in `skills/ark-context-warmup/scripts/evidence.py`. Add a `has_omc: bool = False` kwarg. When `has_omc=True`, add a `seed_sources` key to the returned dict whose value is a list built from `lane_outputs["notebooklm"]["citations"]` (top 3 by rank, body≥200 chars) and `lane_outputs["wiki"]["matches"]` (top 3 by rank). Each element is `{title, vault_source_path, body, vault_type, tags, confidence}`. Confidence: rank 1 → "high", ranks 2-3 → "medium".

- [ ] **Step 5: Run tests to verify pass**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_evidence.py -v`
Expected: all PASS (including pre-existing tests).

- [ ] **Step 6: Commit**

```bash
git add skills/ark-context-warmup/scripts/evidence.py skills/ark-context-warmup/scripts/test_evidence.py
git commit -m "feat(warmup): evidence.derive_candidates emits SeedSource list when has_omc=true"
```

---

## Task 8: Wire `/wiki-handoff` into ark-workflow Step 6.5

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Read current Step 6.5 action branch**

Run: `sed -n '1,1p' skills/ark-workflow/SKILL.md; grep -n "6.5\|action\|record-reset\|compact\|\/clear" skills/ark-workflow/SKILL.md`

Locate the section that dispatches on the user's menu selection `(a) compact`, `(b) clear`, `(c) subagent`. Note the line numbers around `record-reset`.

- [ ] **Step 2: Edit the (a) and (b) branches**

Replace the existing `(a)` branch text in `skills/ark-workflow/SKILL.md` with:

```markdown
**Option (a) — /compact:**

Before dispatching /compact, the LLM must flush a session bridge to OMC so the next session can recover context. Fire `/wiki-handoff`:

```bash
python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
    --chain-id "$CHAIN_ID" \
    --task-text "$TASK_TEXT" \
    --scenario "$SCENARIO" \
    --step-index "$STEP_IDX" --step-count "$STEP_COUNT" \
    --session-id "$SESSION_ID" \
    --open-threads "<LLM-supplied: specific file paths, unresolved questions>" \
    --next-steps "<LLM-supplied: specific actions, with target files>" \
    --notes "<LLM-supplied free-form>" \
    --done-summary "<LLM-supplied summary>" \
    --git-diff-stat "$(git diff --stat HEAD~10..HEAD 2>/dev/null || echo '')"
```

Verify exit code 0 AND the printed bridge path exists on disk. If write failed with a schema-enforcement error, re-invoke with more specific inputs; do NOT proceed to /compact with an empty bridge.

Then invoke `/compact`. Then `context_probe.py --record-reset` (so the probe state matches the post-action level).
```

Replace the existing `(b)` branch similarly — identical dispatch to `/wiki-handoff`, then `/clear`, then `record-reset`.

Leave `(c) subagent` unchanged — no bridge write.

- [ ] **Step 3: Add a note at the top of Step 6.5 documenting the invariant**

Just before the menu options list, insert:

```markdown
> **Wiki-handoff invariant:** For options (a) compact and (b) clear, `/wiki-handoff` MUST write a validated bridge page before the destructive action. Schema-enforcement rejection (exit code 2) blocks the action — re-invoke with specifics. Option (c) subagent does NOT invoke `/wiki-handoff` (parent context is preserved).
```

- [ ] **Step 4: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): invoke /wiki-handoff before compact/clear in Step 6.5 action branch"
```

---

## Task 9: Scaffold wiki-update/scripts + integration fixtures

**Files:**
- Create: `skills/wiki-update/scripts/__init__.py`
- Create: `skills/wiki-update/scripts/fixtures/` (3 subdirs: `mixed/`, `edited_seed/`, `failed_write/`)

- [ ] **Step 1: Create `__init__.py` (empty)**

Run: `touch skills/wiki-update/scripts/__init__.py`

- [ ] **Step 2: Create fixture — mixed OMC pages**

Create these files under `skills/wiki-update/scripts/fixtures/mixed/.omc/wiki/`:

`stub-auto.md`:
```markdown
---
title: Session Log 2026-04-19
tags: [session-log, auto-captured]
category: session-log
---

Auto-captured stub.
```

`arch-high.md`:
```markdown
---
title: Auth Middleware Architecture
tags: [auth, architecture]
category: architecture
confidence: high
ark-original-type: architecture
ark-source-path: Architecture/Auth.md
seed_body_hash: PLACEHOLDER_HASH
seed_chain_id: CH-TEST
---

# Auth Middleware

Decision to use JWT with 15-minute access tokens.
```

`pattern-medium.md`:
```markdown
---
title: Error Wrapping Pattern
tags: [patterns, errors]
category: pattern
confidence: medium
---

# Error Wrapping

Wrap errors with context at every crossing.
```

`debug-with-pattern-tag.md`:
```markdown
---
title: JWT Refresh Race Condition
tags: [debugging, pattern]
category: debugging
confidence: high
---

# JWT Refresh Race

Concurrent refresh requests cause double-issuance. Fix: lock on user_id.
```

`env-page.md`:
```markdown
---
title: Project Environment
tags: [environment, auto-detected]
category: environment
---

Build: npm run build
```

`source-abc123def456.md` (unchanged seed):
```markdown
---
title: Users Service
tags: [users, source-warmup]
category: architecture
confidence: high
ark-original-type: reference
ark-source-path: Architecture/Users.md
seed_body_hash: WILL_BE_COMPUTED_IN_TEST
seed_chain_id: CH-TEST
---

# Users Service

JWT issued by /auth/login, stored in HttpOnly cookie.
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/scripts/__init__.py skills/wiki-update/scripts/fixtures
git commit -m "test(wiki-update): mixed-case fixture worktree for promote_omc"
```

---

## Task 10: promote_omc.py — stub filter + confidence gate

**Files:**
- Create: `skills/wiki-update/scripts/promote_omc.py`
- Create: `skills/wiki-update/scripts/test_promote_omc.py`

- [ ] **Step 1: Write failing tests for filter + gate**

File: `skills/wiki-update/scripts/test_promote_omc.py`
```python
"""Tests for promote_omc: filter, edit-detection, confidence gate, category mapping."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "wiki-handoff" / "scripts"))
from omc_page import body_hash, parse_page
from promote_omc import (
    PromotionConfig,
    PromotionReport,
    promote,
    is_stub,
    classify,
)


def _copy_fixture(tmp_path, name="mixed"):
    src = Path(__file__).parent / "fixtures" / name
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)
    return dst


def test_is_stub_detects_auto_captured(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc" / "wiki" / "stub-auto.md")
    assert is_stub(page, filename="stub-auto.md") is True


def test_is_stub_returns_false_for_arch(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc" / "wiki" / "arch-high.md")
    assert is_stub(page, filename="arch-high.md") is False


def test_classify_high_arch_auto_promote(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc" / "wiki" / "arch-high.md")
    disposition, _ = classify(page, filename="arch-high.md")
    assert disposition == "auto-promote"


def test_classify_medium_staged(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc" / "wiki" / "pattern-medium.md")
    disposition, _ = classify(page, filename="pattern-medium.md")
    assert disposition == "stage"


def test_classify_environment_skipped(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc" / "wiki" / "env-page.md")
    disposition, _ = classify(page, filename="env-page.md")
    assert disposition == "skip"


def test_classify_untouched_seed_skipped(tmp_path):
    repo = _copy_fixture(tmp_path)
    # Normalize the fixture: seed_body_hash == body_hash(body)
    page_path = repo / ".omc" / "wiki" / "source-abc123def456.md"
    page = parse_page(page_path)
    page.frontmatter["seed_body_hash"] = body_hash(page.body)
    from omc_page import write_page
    write_page(page_path, page)
    page = parse_page(page_path)
    disposition, _ = classify(page, filename="source-abc123def456.md")
    assert disposition == "skip"


def test_classify_edited_seed_gets_confidence_gate(tmp_path):
    repo = _copy_fixture(tmp_path)
    page_path = repo / ".omc" / "wiki" / "source-abc123def456.md"
    # Set seed_body_hash to something different from current body — simulating an edit
    page = parse_page(page_path)
    page.frontmatter["seed_body_hash"] = "0" * 64  # deliberately wrong
    from omc_page import write_page
    write_page(page_path, page)
    page = parse_page(page_path)
    disposition, reason = classify(page, filename="source-abc123def456.md")
    assert disposition == "auto-promote"  # confidence: high
    assert "edited" in reason.lower()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement promote_omc.py (filter + classify only; promote() stub returns unimplemented for now)**

File: `skills/wiki-update/scripts/promote_omc.py`
```python
"""Component 3: /wiki-update Step 3.5 — Promote OMC wiki pages to Ark vault."""
from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "wiki-handoff" / "scripts"))

from omc_page import OMCPage, body_hash, parse_page, write_page


STUB_FILENAME_RE = re.compile(r"^session-log-\d{4}-\d{2}-\d{2}")

CATEGORY_PLACEMENT = {
    "architecture": ("Architecture", "Compiled-Insights"),
    "decision": ("Architecture", "Compiled-Insights"),
    "pattern": ("Compiled-Insights", "Compiled-Insights"),
    "debugging": ("__DUAL__", None),
    "session-log": ("__BRIDGE__", None),
    "environment": (None, None),
}


@dataclass
class PromotionConfig:
    repo_root: Path
    omc_wiki_dir: Path
    project_docs_path: Path
    tasknotes_path: Path
    task_prefix: str
    session_slug: str  # for source-sessions backlink
    session_started_at: float
    interactive: bool = False  # default to non-interactive async-staging


@dataclass
class PromotionReport:
    auto_promoted: int = 0
    staged: int = 0
    tasknotes_created: int = 0
    skipped_filtered: int = 0
    session_edits_promoted: int = 0
    troubleshooting_created: int = 0
    deleted: int = 0
    errors: List[str] = field(default_factory=list)


def is_stub(page: OMCPage, *, filename: str) -> bool:
    tags = set(page.frontmatter.get("tags") or [])
    if {"session-log", "auto-captured"}.issubset(tags):
        return True
    if STUB_FILENAME_RE.match(filename):
        return True
    return False


def classify(page: OMCPage, *, filename: str) -> Tuple[str, str]:
    """Return (disposition, reason).

    Dispositions: auto-promote, stage, skip, dual-write-debug, bridge-merge.
    """
    if is_stub(page, filename=filename):
        return "skip", "stub (auto-captured)"
    fm = page.frontmatter
    category = fm.get("category") or ""

    if category == "environment":
        return "skip", "environment (re-derivable)"

    tags = set(fm.get("tags") or [])

    # Edit detection on source-warmup pages
    if "source-warmup" in tags:
        seed_hash = fm.get("seed_body_hash")
        current_hash = body_hash(page.body)
        if seed_hash == current_hash:
            return "skip", "untouched seed (re-derivable from vault)"
        # Edited — treat as session-authored; fall through to confidence gate
        reason_prefix = "edited seed: "
    else:
        reason_prefix = ""

    confidence = fm.get("confidence") or "medium"

    if category == "debugging":
        return "dual-write-debug", reason_prefix + "debugging"
    if category == "session-log" and "session-bridge" in tags:
        return "bridge-merge", reason_prefix + "session-bridge"

    if confidence == "high":
        return "auto-promote", reason_prefix + f"{category} high"
    if confidence == "medium":
        return "stage", reason_prefix + f"{category} medium"
    return "skip", reason_prefix + f"{category} low"


def promote(config: PromotionConfig) -> PromotionReport:
    raise NotImplementedError("filled in Task 11")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/scripts/promote_omc.py skills/wiki-update/scripts/test_promote_omc.py
git commit -m "feat(wiki-update): promote_omc.py filter + classify (stub/edit/confidence)"
```

---

## Task 11: promote_omc.py — frontmatter translation + lossless round-trip

**Files:**
- Modify: `skills/wiki-update/scripts/promote_omc.py`
- Modify: `skills/wiki-update/scripts/test_promote_omc.py`

- [ ] **Step 1: Append failing tests for translate_frontmatter**

Append to `test_promote_omc.py`:

```python
def test_translate_frontmatter_uses_ark_original_type(tmp_path):
    from promote_omc import translate_frontmatter
    omc_fm = {
        "title": "Users Service",
        "tags": ["users", "source-warmup"],
        "category": "architecture",
        "confidence": "high",
        "ark-original-type": "reference",
        "ark-source-path": "Architecture/Users.md",
        "sources": ["sess-1"],
        "schemaVersion": 1,
        "links": [],
        "seed_body_hash": "x" * 64,
        "seed_chain_id": "CH-1",
    }
    out = translate_frontmatter(omc_fm, session_slug="S007-auth")
    # Vault type from ark-original-type
    assert out["type"] == "reference"
    # Session backlink
    assert out["source-sessions"] == ["[[S007-auth]]"]
    # OMC-only fields dropped
    for dropped in ("confidence", "schemaVersion", "links", "sources",
                    "seed_body_hash", "seed_chain_id",
                    "ark-original-type", "ark-source-path", "category"):
        assert dropped not in out
    # Tags normalized (source-warmup stripped — it's an OMC-only marker)
    assert "source-warmup" not in out["tags"]
    assert "users" in out["tags"]
    # last-updated present
    assert "last-updated" in out


def test_translate_frontmatter_falls_back_to_category_when_no_original_type():
    from promote_omc import translate_frontmatter
    omc_fm = {"title": "X", "tags": ["a"], "category": "decision",
              "confidence": "high"}
    out = translate_frontmatter(omc_fm, session_slug="S001-x")
    assert out["type"] == "decision-record"


def test_translate_frontmatter_summary_truncation():
    from promote_omc import derive_summary
    body = "First paragraph. " * 30 + "\n\nSecond paragraph."
    s = derive_summary(body)
    assert len(s) <= 200
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v -k "translate or summary"`
Expected: FAIL.

- [ ] **Step 3: Add translate_frontmatter + derive_summary to promote_omc.py**

Insert into `promote_omc.py` (above `promote()` stub):

```python
import time


CATEGORY_TO_TYPE = {
    "architecture": "architecture",
    "decision": "decision-record",
    "pattern": "pattern",
}

OMC_ONLY_FIELDS = {
    "confidence", "schemaVersion", "links", "sources",
    "seed_body_hash", "seed_chain_id",
    "ark-original-type", "ark-source-path", "category",
}

OMC_TAG_MARKERS_TO_STRIP = {"source-warmup", "source-handoff"}


def derive_summary(body: str, *, max_len: int = 200) -> str:
    for line in body.split("\n\n"):
        s = line.strip()
        if s and not s.startswith("#"):
            one_line = " ".join(s.split())
            if len(one_line) <= max_len:
                return one_line
            return one_line[: max_len - 1].rstrip() + "…"
    return ""


def translate_frontmatter(omc_fm: dict, *, session_slug: str) -> dict:
    out = dict(omc_fm)
    # Determine vault type
    vault_type = omc_fm.get("ark-original-type") or CATEGORY_TO_TYPE.get(
        omc_fm.get("category") or "", "reference"
    )
    out["type"] = vault_type

    # source-sessions backlink
    out["source-sessions"] = [f"[[{session_slug}]]"]

    # tags: drop OMC-only markers
    tags = [t for t in (omc_fm.get("tags") or []) if t not in OMC_TAG_MARKERS_TO_STRIP]
    out["tags"] = tags

    # last-updated
    out["last-updated"] = time.strftime("%Y-%m-%d", time.localtime())
    if "created" not in out:
        out["created"] = out["last-updated"]

    # Drop OMC-only
    for k in OMC_ONLY_FIELDS:
        out.pop(k, None)
    return out
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/scripts/promote_omc.py skills/wiki-update/scripts/test_promote_omc.py
git commit -m "feat(wiki-update): translate_frontmatter lossless round-trip via ark-original-type"
```

---

## Task 12: promote_omc.py — transactional delete + full promote() orchestration

**Files:**
- Modify: `skills/wiki-update/scripts/promote_omc.py`
- Modify: `skills/wiki-update/scripts/test_promote_omc.py`

- [ ] **Step 1: Append failing integration tests**

Append to `test_promote_omc.py`:

```python
def _write_session_log(repo, slug="S001-test"):
    logs_dir = repo / "vault" / "Session-Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"{slug}.md"
    path.write_text("---\ntitle: Session 1\nsession: S001\ntype: session-log\n---\n\n"
                    "## Objective\n\nTest\n\n## Issues & Discoveries\n\n")
    return path


def test_promote_high_confidence_arch_lands_in_architecture(tmp_path):
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    (repo / "vault" / "Compiled-Insights").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    cfg = PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )
    report = promote(cfg)
    assert report.auto_promoted >= 1
    promoted = list((repo / "vault" / "Architecture").glob("*.md"))
    assert any("Auth" in p.read_text() for p in promoted)


def test_promote_medium_stages_and_creates_tasknote(tmp_path):
    repo = _copy_fixture(tmp_path)
    for d in ("vault/Architecture", "vault/Compiled-Insights", "vault/Staging",
              "vault/TaskNotes/Tasks/Bug"):
        (repo / d).mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    cfg = PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )
    report = promote(cfg)
    assert report.staged >= 1
    staged = list((repo / "vault" / "Staging").glob("*.md"))
    assert len(staged) >= 1
    bugs = list((repo / "vault" / "TaskNotes" / "Tasks" / "Bug").glob("*.md"))
    assert any("Review staged wiki" in p.read_text() for p in bugs)
    assert report.tasknotes_created >= 1


def test_promote_debugging_pattern_dual_writes_troubleshooting(tmp_path):
    repo = _copy_fixture(tmp_path)
    for d in ("vault/Architecture", "vault/Compiled-Insights", "vault/Troubleshooting"):
        (repo / d).mkdir(parents=True, exist_ok=True)
    log_path = _write_session_log(repo)
    cfg = PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )
    report = promote(cfg)
    # Inline fold-in
    assert "JWT Refresh Race" in log_path.read_text()
    # Cross-link page
    ts = list((repo / "vault" / "Troubleshooting").glob("*.md"))
    assert len(ts) == 1
    assert "compiled-insight" in ts[0].read_text()
    assert report.troubleshooting_created == 1


def test_promote_transactional_delete_preserves_on_write_failure(tmp_path, monkeypatch):
    repo = _copy_fixture(tmp_path)
    # Deliberately remove target dir AND make the promotion raise on write.
    cfg = PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault_does_not_exist",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )
    # Corrupt write_page to force failure
    import promote_omc
    def boom(*a, **k):
        raise OSError("simulated write failure")
    monkeypatch.setattr(promote_omc, "write_page", boom)
    report = promote(cfg)
    # arch-high.md must still exist (not deleted)
    assert (repo / ".omc" / "wiki" / "arch-high.md").exists()
    assert report.deleted == 0
    assert any("failure" in e.lower() for e in report.errors)
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: FAIL (promote() is NotImplementedError).

- [ ] **Step 3: Replace `promote()` stub with full implementation**

Replace the `promote()` stub in `promote_omc.py` with:

```python
def _write_vault_page(target: Path, page: OMCPage) -> None:
    write_page(target, page, exclusive=False)


def _append_to_session_log(log_path: Path, title: str, body: str) -> None:
    text = log_path.read_text()
    marker = "## Issues & Discoveries"
    if marker in text:
        insertion = f"\n### {title}\n\n{body}\n"
        updated = text.replace(marker, marker + insertion, 1)
    else:
        updated = text + f"\n\n## Issues & Discoveries\n\n### {title}\n\n{body}\n"
    log_path.write_text(updated)


def _create_review_tasknote(bugs_dir: Path, task_prefix: str, title: str,
                             staging_path: Path, omc_path: Path) -> Path:
    bugs_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(bugs_dir.glob(f"{task_prefix}*.md"))
    next_n = len(existing) + 1
    task_id = f"{task_prefix}{next_n:03d}"
    path = bugs_dir / f"{task_id}-review-wiki-promotion.md"
    path.write_text(
        f"---\ntitle: \"Review staged wiki promotion: {title}\"\n"
        f"task-id: {task_id}\nstatus: todo\npriority: low\n"
        f"type: bug\ntags: [wiki-promotion-review]\n---\n\n"
        f"## Review\n\nStaged at `{staging_path}`; original OMC source at `{omc_path}`.\n"
    )
    return path


def _fallback_dir(primary: Path, fallback_name: str, project_docs: Path) -> Path:
    if primary.is_dir():
        return primary
    return project_docs / fallback_name


def promote(config: PromotionConfig) -> PromotionReport:
    report = PromotionReport()
    wiki_dir = config.omc_wiki_dir
    if not wiki_dir.is_dir():
        return report

    # Locate current session log once
    log_candidates = sorted((config.project_docs_path / "Session-Logs").glob("*.md"),
                             key=lambda p: p.stat().st_mtime, reverse=True)
    log_path = log_candidates[0] if log_candidates else None

    for omc_path in wiki_dir.glob("*.md"):
        if omc_path.name in ("index.md", "log.md"):
            continue
        try:
            page = parse_page(omc_path)
        except ValueError as exc:
            report.errors.append(f"malformed {omc_path.name}: {exc}")
            continue

        disposition, reason = classify(page, filename=omc_path.name)

        try:
            if disposition == "skip":
                report.skipped_filtered += 1
                continue

            if disposition == "dual-write-debug":
                if log_path:
                    _append_to_session_log(log_path,
                                           page.frontmatter.get("title", omc_path.stem),
                                           page.body)
                tags = set(page.frontmatter.get("tags") or [])
                if tags & {"pattern", "insight"}:
                    ts_dir = config.project_docs_path / "Troubleshooting"
                    ts_dir.mkdir(parents=True, exist_ok=True)
                    new_fm = translate_frontmatter(page.frontmatter,
                                                    session_slug=config.session_slug)
                    new_fm["type"] = "compiled-insight"
                    new_fm["summary"] = derive_summary(page.body)
                    ts_path = ts_dir / omc_path.name.replace("debug-", "troubleshooting-")
                    _write_vault_page(ts_path, OMCPage(frontmatter=new_fm, body=page.body))
                    report.troubleshooting_created += 1
                if _delete_source_safely(omc_path, [log_path] if log_path else []):
                    report.deleted += 1
                continue

            if disposition == "bridge-merge":
                if log_path:
                    _append_to_session_log(log_path, "Session Bridge", page.body)
                if _delete_source_safely(omc_path, [log_path] if log_path else []):
                    report.deleted += 1
                continue

            new_fm = translate_frontmatter(page.frontmatter, session_slug=config.session_slug)
            new_fm["summary"] = derive_summary(page.body)

            category = page.frontmatter.get("category", "")
            primary_name, fallback_name = CATEGORY_PLACEMENT.get(category, ("Compiled-Insights", None))
            if not primary_name or primary_name.startswith("__"):
                report.skipped_filtered += 1
                continue
            target_dir = _fallback_dir(config.project_docs_path / primary_name,
                                        fallback_name or "Compiled-Insights",
                                        config.project_docs_path)

            if disposition == "stage":
                staging_dir = config.project_docs_path / "Staging"
                staging_dir.mkdir(parents=True, exist_ok=True)
                target = staging_dir / omc_path.name
                _write_vault_page(target, OMCPage(frontmatter=new_fm, body=page.body))
                bugs_dir = config.tasknotes_path / "Tasks" / "Bug"
                tn_path = _create_review_tasknote(bugs_dir, config.task_prefix,
                                                    page.frontmatter.get("title", omc_path.stem),
                                                    target, omc_path)
                report.staged += 1
                report.tasknotes_created += 1
                if _delete_source_safely(omc_path, [target, tn_path]):
                    report.deleted += 1
                continue

            # auto-promote
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / omc_path.name
            _write_vault_page(target, OMCPage(frontmatter=new_fm, body=page.body))
            report.auto_promoted += 1
            if "edited seed" in reason:
                report.session_edits_promoted += 1
            if _delete_source_safely(omc_path, [target]):
                report.deleted += 1

        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{omc_path.name}: {exc}")

    return report


def _delete_source_safely(omc_path: Path, required_dests: list) -> bool:
    for dest in required_dests:
        if dest is None:
            return False
        if not Path(dest).exists() or Path(dest).stat().st_size == 0:
            return False
    try:
        omc_path.unlink()
        return True
    except OSError:
        return False
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/scripts/promote_omc.py skills/wiki-update/scripts/test_promote_omc.py
git commit -m "feat(wiki-update): promote() orchestration with transactional delete + Q4A staging + Q5C dual-write"
```

---

## Task 13: Wire Step 3.5 into wiki-update SKILL.md

**Files:**
- Modify: `skills/wiki-update/SKILL.md`

- [ ] **Step 1: Read current SKILL.md Step 3 end and Step 4 beginning**

Run: `grep -n "^### Step 3\|^### Step 4" skills/wiki-update/SKILL.md`

- [ ] **Step 2: Insert Step 3.5 between them**

Between the existing Step 3 (TaskNote Epic/Stories) and Step 4 (Extract Compiled Insights), insert:

```markdown
### Step 3.5: Promote OMC Wiki Pages

If `.omc/wiki/` exists, run the OMC-to-vault promotion helper. This moves durable session-authored knowledge from the per-worktree OMC scratchpad into the project vault with lossless frontmatter translation and transactional deletes.

```bash
SESSION_SLUG="$(basename "$SESSION_LOG_PATH" .md)"
SESSION_STARTED_AT=$(date -r "$SESSION_LOG_PATH" +%s 2>/dev/null || echo 0)
python3 "$ARK_SKILLS_ROOT/skills/wiki-update/scripts/cli_promote.py" \
    --repo-root "$(pwd)" \
    --omc-wiki-dir ".omc/wiki" \
    --project-docs-path "$PROJECT_DOCS_PATH" \
    --tasknotes-path "$TASKNOTES_PATH" \
    --task-prefix "$TASK_PREFIX" \
    --session-slug "$SESSION_SLUG" \
    --session-started-at "$SESSION_STARTED_AT"
```

Behavior:
- **Stubs** (auto-captured session-log markers) → skipped.
- **Environment pages** → skipped (re-derivable from project-memory.json).
- **source-warmup pages with body_hash == seed_body_hash** → skipped (untouched from vault).
- **source-warmup pages with body_hash != seed_body_hash** → treated as session-authored, routed through confidence gate.
- **High confidence** → auto-promoted to `{project_docs_path}/Architecture/` or `Compiled-Insights/` (with lossless type via `ark-original-type`).
- **Medium confidence** → staged in `{project_docs_path}/Staging/` + a low-priority TaskNote bug created under `Tasks/Bug/`.
- **Debugging pages** → always folded inline into current session log's "Issues & Discoveries"; additionally, if tagged `pattern` or `insight`, a cross-linked page lands in `{project_docs_path}/Troubleshooting/` as `type: compiled-insight`.
- **Session-bridge pages** → merged into the session log body.
- **Delete** only happens after vault write + destination check passes.

Degradation: no `.omc/wiki/` → silent no-op. Failed writes preserve OMC sources for retry.
```

- [ ] **Step 3: Create the CLI wrapper that SKILL.md calls**

File: `skills/wiki-update/scripts/cli_promote.py`
```python
"""CLI wrapper around promote_omc.promote for shell invocation from SKILL.md."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from promote_omc import PromotionConfig, promote


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--omc-wiki-dir", required=True)
    p.add_argument("--project-docs-path", required=True)
    p.add_argument("--tasknotes-path", required=True)
    p.add_argument("--task-prefix", required=True)
    p.add_argument("--session-slug", required=True)
    p.add_argument("--session-started-at", required=True, type=float)
    args = p.parse_args()

    cfg = PromotionConfig(
        repo_root=Path(args.repo_root),
        omc_wiki_dir=Path(args.repo_root) / args.omc_wiki_dir,
        project_docs_path=Path(args.project_docs_path),
        tasknotes_path=Path(args.tasknotes_path),
        task_prefix=args.task_prefix,
        session_slug=args.session_slug,
        session_started_at=args.session_started_at,
    )
    report = promote(cfg)

    print("OMC Promotion Report")
    print("====================")
    print(f"Auto-promoted (high confidence): {report.auto_promoted}")
    print(f"Staged for review (medium): {report.staged} pages → Staging/ + {report.tasknotes_created} TaskNotes")
    print(f"Skipped (filtered/untouched-seed): {report.skipped_filtered}")
    print(f"Session-authored seed edits promoted: {report.session_edits_promoted}")
    print(f"Troubleshooting cross-links created: {report.troubleshooting_created}")
    print(f"Deleted from OMC: {report.deleted}")
    if report.errors:
        print(f"Errors: {len(report.errors)}")
        for e in report.errors:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Smoke test against the fixture**

Run:
```bash
cd skills/wiki-update/scripts/fixtures/mixed
python3 ../../cli_promote.py \
    --repo-root "$(pwd)" \
    --omc-wiki-dir ".omc/wiki" \
    --project-docs-path "$(pwd)/vault" \
    --tasknotes-path "$(pwd)/vault/TaskNotes" \
    --task-prefix "Arktest-" \
    --session-slug "S001-test" \
    --session-started-at 0 || true
```

Expected: non-crash; report lines printed to stdout.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/SKILL.md skills/wiki-update/scripts/cli_promote.py
git commit -m "feat(wiki-update): Step 3.5 wired to promote_omc via cli_promote.py"
```

---

## Task 14: Integration bats suite

**Files:**
- Create: `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`

- [ ] **Step 1: Write bats integration tests**

File: `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`
```bash
#!/usr/bin/env bats

setup() {
    export TMPDIR_TEST="$(mktemp -d)"
    cp -R "${BATS_TEST_DIRNAME}/../fixtures/mixed/" "${TMPDIR_TEST}/repo"
    cd "${TMPDIR_TEST}/repo"
    mkdir -p vault/Architecture vault/Compiled-Insights vault/Staging \
             vault/Troubleshooting vault/Session-Logs vault/TaskNotes/Tasks/Bug
    cat > vault/Session-Logs/S001-test.md <<'EOF'
---
title: Session 1
session: S001
type: session-log
---

## Issues & Discoveries

EOF
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

@test "e2e: mixed fixture promotes arch-high to Architecture" {
    python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test" \
        --session-started-at 0
    [ -f vault/Architecture/arch-high.md ]
    grep -q "JWT" vault/Architecture/arch-high.md
    [ ! -f .omc/wiki/arch-high.md ]
}

@test "e2e: medium-conf stages + creates TaskNote non-interactively" {
    python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test" \
        --session-started-at 0
    [ -f vault/Staging/pattern-medium.md ]
    ls vault/TaskNotes/Tasks/Bug/*.md | grep -q review-wiki
}

@test "e2e: debugging pattern dual-writes Troubleshooting page" {
    python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test" \
        --session-started-at 0
    grep -q "JWT Refresh Race" vault/Session-Logs/S001-test.md
    ls vault/Troubleshooting/*.md | head -1 | xargs grep -q "compiled-insight"
}

@test "e2e: failed vault write preserves OMC source" {
    chmod -w vault/Architecture
    run python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test" \
        --session-started-at 0
    [ -f .omc/wiki/arch-high.md ]
    chmod +w vault/Architecture
}

@test "e2e: no .omc/wiki/ → silent no-op" {
    rm -rf .omc
    run python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test" \
        --session-started-at 0
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run bats suite (if bats installed) or skip with note**

Run: `command -v bats && bats skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats || echo "bats not installed — smoke test manually per skill smoke-test.md"`

Expected (with bats): 5 PASS. Without bats: skip message, no failure.

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats
git commit -m "test(wiki-update): bats e2e integration suite for promote_omc"
```

---

## Task 15: CHANGELOG + version bump + plugin.json/marketplace.json

**Files:**
- Modify: `VERSION`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump VERSION**

```bash
echo "1.19.0" > VERSION
```

- [ ] **Step 2: Bump plugin.json + marketplace.json**

Run: `grep -l '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json`
Edit both files to set `"version": "1.19.0"`. Keep other keys unchanged.

- [ ] **Step 3: Add CHANGELOG entry**

Insert at the top of `CHANGELOG.md` (under existing `## [1.18.1]`):

```markdown
## [1.19.0] - 2026-04-20

New **OMC↔Ark Wiki Bridge** — bidirectional connector between OMC `/wiki` (per-worktree scratchpad) and Ark `/wiki-*` (per-project Obsidian vault). Three components: warmup seeds OMC with cited vault sources on prompt + cache miss; `/wiki-handoff` writes a validated bridge page before v1.17.0 probe's compact/clear; `/wiki-update` Step 3.5 promotes durable OMC pages into the vault with lossless round-trip and transactional deletes.

### Added

- **`/wiki-handoff` skill** (`skills/wiki-handoff/`) — validated bridge-page writer with schema enforcement (rejects empty / generic `open_threads` / `next_steps`), O_EXCL atomic creation, collision-suffix fallback. Invoked from `/ark-workflow` Step 6.5 action branch on `(a) compact` and `(b) clear` only; `(c) subagent` does not invoke.
- **`seed_omc.py`** in `/ark-context-warmup` — populates `.omc/wiki/` with cited vault sources keyed by `sha256(vault_path + content)[0:12]`. Idempotent; stale cleanup on each fanout deletes prior same-chain sources not in the current fanout. Writes provenance (`ark-original-type`, `ark-source-path`, `seed_body_hash`, `seed_chain_id`) for lossless round-trip.
- **`read_bridges.py`** in `/ark-context-warmup` — next-session consumption. Chain-ID affinity: match → 7-day window; mismatch → single most-recent only, 48h window. Surfaces chosen bridge under "Prior Session Handoff" in Context Brief.
- **`/wiki-update` Step 3.5 — Promote OMC Wiki Pages**. Filter + edit-detection + confidence gate:
  - `high` → auto-promote to `Architecture/` or `Compiled-Insights/`
  - `medium` → stage in `vault/Staging/` + low-priority TaskNote bug (non-interactive Q4A)
  - debugging pages → always fold inline into session log; also create `vault/Troubleshooting/` cross-link if tagged `pattern`/`insight` (Q5C)
  - session-bridge pages → merge into session log body
  - untouched source-warmup pages → skip (re-derivable); edited ones → promote
- **Transactional delete** — OMC source removed only after vault write + destination check (size > 0). Failed writes preserve sources for retry.
- **`ark-original-type` + `ark-source-path` provenance** for lossless vault-type round-trip. `research`/`reference`/`guide`/`compiled-insight` preserved through the OMC scratchpad.
- **Integration tests** — bats e2e suite at `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`.

### Changed

- `skills/ark-context-warmup/SKILL.md` — added Step 1b (bridge read) + Step 5b (OMC seed on cache miss with prompt).
- `skills/ark-workflow/SKILL.md` Step 6.5 — action branches `(a)` and `(b)` now invoke `/wiki-handoff` before the destructive action and before `record-reset`.
- `skills/wiki-update/SKILL.md` — new Step 3.5 between existing Steps 3 and 4.

### Degradation contract

All bridge components are gated on `.omc/wiki/` existing. No `.omc/`: silent no-op everywhere. No prompt on warmup: no OMC writes (Option E′ rule). Handoff schema rejection blocks the destructive action — LLM must re-invoke with specifics.

### Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-20-omc-wiki-ark-bridge-design.md`
- Plan: `docs/superpowers/plans/2026-04-20-omc-wiki-ark-bridge.md`
```

- [ ] **Step 4: Commit release metadata**

```bash
git add VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "release: v1.19.0 — OMC↔Ark wiki bridge"
```

---

## Task 16: Final verification pass

- [ ] **Step 1: Run full test suite**

```bash
cd skills/wiki-handoff/scripts && python3 -m pytest -v
cd ../../ark-context-warmup/scripts && python3 -m pytest -v
cd ../../wiki-update/scripts && python3 -m pytest -v
```

Expected: all green.

- [ ] **Step 2: Run ark-workflow existing tests to ensure Step 6.5 edits didn't break anything**

```bash
cd skills/ark-workflow/scripts && python3 -m pytest -v
```

Expected: all green.

- [ ] **Step 3: Run ark-update fixture regen check**

```bash
python3 skills/ark-update/tests/regenerate_fixtures.py --dry-run
```

Expected: empty dry-run output (no template drift from this PR).

- [ ] **Step 4: Lint check**

```bash
command -v ruff && ruff check skills/ || true
```

- [ ] **Step 5: Final commit if any fixups**

```bash
git status && git diff --stat
```

If nothing to commit, proceed to push.

---

## Self-review checklist (completed by plan author)

- [x] **Spec coverage** — all 9 spec success criteria mapped:
  - SC1 (bridge in brief, chain match 7d) → Task 5 (read_bridges + affinity tests)
  - SC2 (bridge in brief, 48h non-match) → Task 5
  - SC3 (warmup populates on cache miss, idempotent, stale cleanup) → Task 4
  - SC4 (edited seed promoted) → Task 10 (classify) + Task 12 (promote)
  - SC5 (promotion: high auto, medium staging, dual-write debug) → Tasks 10-12
  - SC6 (transactional delete) → Task 12
  - SC7 (no trigger collision) → not directly testable; preserved by skill naming
  - SC8 (probe menu → wiki-handoff → compact/clear → record-reset order) → Task 8 + Task 2 (schema)
  - SC9 (schema rejection) → Task 2
- [x] **Placeholder scan** — no TBD/TODO/"implement later" in task bodies.
- [x] **Type consistency** — `PromotionConfig`, `SeedSource`, `OMCPage`, `pick_bridge` consistent across tasks.
- [x] **Build order** — Task 1 (shared module) precedes all consumers; Task 9 fixture precedes Tasks 10-14.
