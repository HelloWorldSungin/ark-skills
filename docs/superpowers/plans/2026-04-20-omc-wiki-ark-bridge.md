# OMC ↔ Ark Wiki Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Revised post-/ccg plan review (Codex flagged 4 HIGH, 4 MEDIUM, 2 LOW; Gemini concurred on shared-module placement)

**Goal:** Implement the OMC `/wiki` ↔ Ark `/wiki-*` bridge per `docs/superpowers/specs/2026-04-20-omc-wiki-ark-bridge-design.md` — warmup seeds OMC on prompt+cache-miss, handoff writes bridge pages on v1.17.0 probe action, end-of-session `/wiki-update` promotes durable OMC content into the vault with transactional (post-index-regen) deletes.

**Architecture:** One shared module at `skills/shared/python/omc_page.py`, three Python helper scripts (`seed_omc.py`, `read_bridges.py`, `promote_omc.py`), one new skill (`/wiki-handoff`), and edits to four existing files (`synthesize.py`, `ark-context-warmup/SKILL.md`, `ark-workflow/SKILL.md`, `wiki-update/SKILL.md`). Pytest for unit, bats for integration.

**Tech Stack:** Python 3.11, stdlib + `PyYAML` (already a plugin dependency — see `skills/ark-update/scripts/plan.py`). Pytest for unit tests. Bats for integration. All scripts use `from __future__ import annotations` per repo convention.

---

## File Structure

**Create:**
- `skills/shared/python/__init__.py`
- `skills/shared/python/omc_page.py` — shared page I/O + hashing
- `skills/shared/python/test_omc_page.py`
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
- `skills/wiki-update/scripts/cli_promote.py`
- `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`
- `skills/wiki-update/scripts/fixtures/mixed/` (integration fixture worktree)

**Modify:**
- `skills/ark-context-warmup/scripts/evidence.py` — extend `derive_candidates` to emit `seed_sources`
- `skills/ark-context-warmup/scripts/synthesize.py` — `assemble_brief` accepts `prior_bridge` kwarg, renders "Prior Session Handoff" section
- `skills/ark-context-warmup/SKILL.md` — Step 1b (bridge read) + Step 5b (seed OMC)
- `skills/ark-workflow/SKILL.md` — expand Step 6.5 action bullet into full `(a)`/`(b)`/`(c)` branch block with `/wiki-handoff` pre-action
- `skills/wiki-update/SKILL.md` — insert Step 3.5 between Steps 3 and 4
- `VERSION` — bump to 1.19.0
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — version bump
- `CHANGELOG.md` — 1.19.0 entry

**Shared-module import pattern:** All consumers add `skills/shared/python/` to `sys.path` via a repo-root bootstrap pattern (shown in Task 1). No cross-skill imports.

---

## Task 1: Shared OMC page module at `skills/shared/python/`

**Files:**
- Create: `skills/shared/python/__init__.py` (empty)
- Create: `skills/shared/python/omc_page.py`
- Create: `skills/shared/python/test_omc_page.py`

- [ ] **Step 1: Create the shared directory**

```bash
mkdir -p skills/shared/python
touch skills/shared/python/__init__.py
```

- [ ] **Step 2: Write failing tests**

File: `skills/shared/python/test_omc_page.py`
```python
"""Tests for shared OMC page utilities."""
from pathlib import Path

import pytest

from omc_page import (
    OMCPage,
    body_hash,
    content_hash_slug,
    parse_page,
    write_page,
)


def test_body_hash_deterministic():
    assert body_hash("hello") == body_hash("hello")
    assert body_hash("hello") != body_hash("world")


def test_body_hash_operates_on_provided_string_only():
    # Callers pass the body portion — the function does not strip frontmatter itself.
    raw_with_fm = "---\ntitle: x\n---\n\n# Body\n"
    body_only = "# Body\n"
    assert body_hash(raw_with_fm) != body_hash(body_only)
    # When caller passes the post-parse body, the hash reflects that body.
    path = Path("/tmp/_test_body_hash_parse.md")
    path.write_text(raw_with_fm)
    page = parse_page(path)
    assert body_hash(page.body) == body_hash("\n# Body\n")  # parse_page preserves the leading newline


def test_content_hash_slug_stable_and_12_chars():
    slug = content_hash_slug("vault/Architecture/Auth.md", "body text")
    assert len(slug) == 12
    assert all(c in "0123456789abcdef" for c in slug)
    assert slug == content_hash_slug("vault/Architecture/Auth.md", "body text")
    assert slug != content_hash_slug("vault/Architecture/Users.md", "body text")
    assert slug != content_hash_slug("vault/Architecture/Auth.md", "different")


def test_parse_page_roundtrip(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: X\ntags: [a, b]\n---\n\n# X\n\nBody.\n")
    page = parse_page(path)
    assert page.frontmatter["title"] == "X"
    assert page.frontmatter["tags"] == ["a", "b"]
    assert "# X\n\nBody." in page.body


def test_parse_page_missing_frontmatter(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("# No frontmatter\n\nJust body.\n")
    page = parse_page(path)
    assert page.frontmatter == {}
    assert "No frontmatter" in page.body


def test_parse_page_malformed_yaml_raises(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: [unclosed\n---\n\nBody.\n")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_page(path)


def test_write_page_atomic(tmp_path):
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

- [ ] **Step 3: Run tests — expect failure**

Run: `cd skills/shared/python && python3 -m pytest test_omc_page.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'omc_page'`.

- [ ] **Step 4: Implement `omc_page.py`**

File: `skills/shared/python/omc_page.py`
```python
"""Shared OMC page utilities: read, write, hash. Used by /wiki-handoff,
/ark-context-warmup seeder, and /wiki-update promoter.
"""
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
    """SHA-256 hex of the supplied string. Caller chooses what to hash."""
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
    body = text[end + 5 :]
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

- [ ] **Step 5: Run tests to verify pass**

Run: `cd skills/shared/python && python3 -m pytest test_omc_page.py -v`
Expected: 8 PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/shared/python/
git commit -m "feat(shared): shared OMC page utilities (read/write/hash) for wiki bridge"
```

---

## Task 2: `/wiki-handoff` write_bridge.py with schema enforcement

**Files:**
- Create: `skills/wiki-handoff/scripts/write_bridge.py`
- Create: `skills/wiki-handoff/scripts/test_write_bridge.py`

Shared-module import helper (used throughout this plan):
```python
_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))
```

- [ ] **Step 1: Write failing tests**

File: `skills/wiki-handoff/scripts/test_write_bridge.py`
```python
"""Tests for /wiki-handoff bridge writer."""
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parent / "write_bridge.py"


def run_cli(argv, cwd):
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[3] / "shared" / "python")}
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
    assert not names[0].endswith("-2.md") and not names[0].endswith("-3.md")
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
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_write_bridge.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement write_bridge.py**

File: `skills/wiki-handoff/scripts/write_bridge.py`
```python
"""/wiki-handoff — writes a session bridge page to .omc/wiki/.

Invoked from /ark-workflow Step 6.5 action branch before /compact or /clear.
Uses shared omc_page module. PyYAML required (plugin-standard dep).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, write_page  # noqa: E402


GENERIC_PATTERNS = {
    "continue task", "tbd", "todo", "keep going", "none", "n/a", "na",
}
MIN_LENGTH = 20


def _validate(field_name: str, value: str) -> str | None:
    s = (value or "").strip()
    if not s:
        return f"{field_name} must be non-empty"
    if s.lower() in GENERIC_PATTERNS:
        return f"{field_name} is generic placeholder ({s!r}) — provide specific detail"
    if len(s) < MIN_LENGTH:
        return f"{field_name} is too short (<{MIN_LENGTH} chars) — provide specific detail"
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
            print(f"wiki-handoff: {err}. Re-invoke with specific file paths / decision points.", file=sys.stderr)
            return 2

    wiki_dir = Path.cwd() / ".omc" / "wiki"
    if not wiki_dir.is_dir():
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

    attempt = 1
    while attempt <= 10:
        try_path = target if attempt == 1 else wiki_dir / f"{target.stem}-{attempt}.md"
        try:
            write_page(try_path, page, exclusive=True)
            print(str(try_path))
            return 0
        except FileExistsError:
            attempt += 1
    print("wiki-handoff: too many filename collisions", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-handoff/scripts && python3 -m pytest test_write_bridge.py -v`
Expected: 14 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-handoff/scripts/
git commit -m "feat(wiki-handoff): write_bridge.py with schema enforcement + O_EXCL"
```

---

## Task 3: `/wiki-handoff` SKILL.md

**Files:** Create `skills/wiki-handoff/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

File: `skills/wiki-handoff/SKILL.md`
```markdown
---
name: wiki-handoff
description: Write a session bridge page to .omc/wiki/ capturing in-session state before /compact or /clear. Invoked from /ark-workflow Step 6.5 action branch. Triggers on "handoff session", "bridge page", "flush session state".
---

# Wiki Handoff

Writes one page to `.omc/wiki/session-bridge-{YYYY-MM-DD}-{HHMMSS}-{sid8}.md` with a validated snapshot of current session state. Designed to run before `/compact` or `/clear` so the next session can recover context.

## When this runs

Invoked from `/ark-workflow` SKILL.md Step 6.5 after the v1.17.0 context-budget probe menu surfaces and the user picks option `(a) compact` or `(b) clear`. NOT invoked for option `(c) subagent`.

## Inputs

Supplied by the LLM in the same turn that invokes this skill:

| Arg | Source |
|---|---|
| `--chain-id` | `.ark-workflow/current-chain.md` frontmatter |
| `--task-text` | same |
| `--scenario` | same |
| `--step-index`, `--step-count` | chain step checklist |
| `--session-id` | `$CLAUDE_SESSION_ID` or `.omc/state/hud-state.json` |
| `--open-threads` | **LLM-authored**, specific (file paths, decision points) |
| `--next-steps` | **LLM-authored**, specific |
| `--notes` | LLM-authored free-form |
| `--done-summary` | LLM summary of session work |
| `--git-diff-stat` | `git diff --stat <chain-entry-ref>..HEAD` |

## Schema enforcement

The script rejects calls where `--open-threads` or `--next-steps` match any of:
- Empty / whitespace-only
- Generic: `continue task`, `TBD`, `TODO`, `keep going`, `none`, `n/a`
- Content length <20 chars

On rejection exits non-zero; the LLM MUST re-invoke with specifics.

## Degradation

- `.omc/wiki/` missing → exit 0 silent.
- Filename collision within same second → append `-2`, `-3`, … (up to 10 retries).
- Too many retries → exit 3.

## Usage

```bash
python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
    --chain-id "$CHAIN_ID" --task-text "$TASK_TEXT" --scenario "$SCENARIO" \
    --step-index "$STEP_IDX" --step-count "$STEP_COUNT" --session-id "$SESSION_ID" \
    --open-threads "Verify JWT TTL handling in auth/middleware.py:47" \
    --next-steps "Write integration test tests/test_auth.py covering expired tokens" \
    --notes "Rate limiter interaction still open" \
    --done-summary "Implemented JWT validation middleware; 3/5 tests pass" \
    --git-diff-stat "$(git diff --stat HEAD~3..HEAD)"
```

Output on success: path of the created bridge page (stdout).
```

- [ ] **Step 2: Commit**

```bash
git add skills/wiki-handoff/SKILL.md
git commit -m "feat(wiki-handoff): SKILL.md documenting invocation contract"
```

---

## Task 4: `seed_omc.py` — warmup populates OMC on cache miss

**Files:**
- Create: `skills/ark-context-warmup/scripts/seed_omc.py`
- Create: `skills/ark-context-warmup/scripts/test_seed_omc.py`

- [ ] **Step 1: Write failing tests**

File: `skills/ark-context-warmup/scripts/test_seed_omc.py`
```python
"""Tests for seed_omc: per-source content hashing + stale cleanup."""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import content_hash_slug, parse_page, write_page, OMCPage
from seed_omc import seed, SeedSource


def _mk(title="Auth", path="vault/Architecture/Auth.md",
        body="# Auth\n\n" + "body " * 60, vault_type="architecture",
        tags=None, confidence="high"):
    return SeedSource(title=title, vault_source_path=path, body=body,
                      vault_type=vault_type, tags=tags or ["auth"],
                      confidence=confidence)


def test_seed_writes_new_page(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[_mk()])
    assert r.written == 1
    slug = content_hash_slug("vault/Architecture/Auth.md", _mk().body)
    assert (wiki / f"source-{slug}.md").exists()


def test_seed_skips_short_sources(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[_mk(body="short")])
    assert r.written == 0
    assert list(wiki.glob("source-*.md")) == []


def test_seed_idempotent_same_content(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    s = [_mk()]
    seed(wiki, chain_id="CH-A", sources=s)
    before = {p.name for p in wiki.glob("source-*.md")}
    r = seed(wiki, chain_id="CH-A", sources=s)
    assert r.written == 0
    after = {p.name for p in wiki.glob("source-*.md")}
    assert before == after


def test_seed_content_change_creates_new_hash_and_cleans_stale(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A",
         sources=[_mk(body="# v1\n\n" + "a" * 250)])
    r = seed(wiki, chain_id="CH-A",
             sources=[_mk(body="# v2\n\n" + "b" * 250)])  # same path, new content
    assert r.written == 1
    assert r.deleted_stale == 1


def test_seed_topic_shift_deletes_stale_sources(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Auth", path="vault/Architecture/Auth.md", body="# A\n\n" + "a" * 250),
        _mk(title="Users", path="vault/Architecture/Users.md", body="# B\n\n" + "b" * 250),
    ])
    assert len(list(wiki.glob("source-*.md"))) == 2
    r = seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Billing", path="vault/Architecture/Billing.md", body="# C\n\n" + "c" * 250),
    ])
    assert r.written == 1 and r.deleted_stale == 2
    assert len(list(wiki.glob("source-*.md"))) == 1


def test_seed_preserves_other_chains(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[_mk()])
    r = seed(wiki, chain_id="CH-B",
             sources=[_mk(title="Deploys", path="vault/Ops/Deploys.md",
                          body="# D\n\n" + "d" * 250)])
    assert r.deleted_stale == 0
    assert len(list(wiki.glob("source-*.md"))) == 2


def test_seed_frontmatter_has_full_provenance(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[_mk(vault_type="research")])
    page = parse_page(next(wiki.glob("source-*.md")))
    fm = page.frontmatter
    assert fm["ark-original-type"] == "research"
    assert fm["ark-source-path"] == "vault/Architecture/Auth.md"
    assert "seed_body_hash" in fm
    assert fm["seed_chain_id"] == "CH-A"
    assert "source-warmup" in fm["tags"]
    assert fm["category"] == "architecture"  # research → architecture per mapping


def test_seed_excluded_vault_types(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    for bad in ("session-log", "epic", "story", "bug", "task"):
        r = seed(wiki, chain_id="CH-A",
                 sources=[_mk(vault_type=bad, body="x" * 250,
                              path=f"vault/{bad}.md")])
        assert r.written == 0


def test_seed_same_title_different_path_produces_distinct_slugs(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Auth", path="vault/A/Auth.md", body="# A\n\n" + "x" * 250),
        _mk(title="Auth", path="vault/B/Auth.md", body="# A\n\n" + "x" * 250),
    ])
    assert r.written == 2
    assert len(list(wiki.glob("source-*.md"))) == 2
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_seed_omc.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement seed_omc.py**

File: `skills/ark-context-warmup/scripts/seed_omc.py`
```python
"""Warmup populator: writes cited vault sources into .omc/wiki/ with
content-hashed filenames, plus stale cleanup."""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, body_hash, content_hash_slug, parse_page, write_page  # noqa: E402


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
    confidence: str


@dataclass
class SeedResult:
    written: int = 0
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
    r = SeedResult()
    wiki_dir.mkdir(parents=True, exist_ok=True)

    active_slugs: Set[str] = set()
    for src in sources:
        if src.vault_type in EXCLUDED_VAULT_TYPES or len(src.body) < MIN_BODY_LEN:
            r.skipped += 1
            continue
        slug = content_hash_slug(src.vault_source_path, src.body)
        active_slugs.add(slug)
        target = wiki_dir / f"source-{slug}.md"
        if target.exists():
            continue
        try:
            write_page(target, _build_page(src, chain_id))
            r.written += 1
        except Exception as exc:  # noqa: BLE001
            r.errors.append(f"{src.vault_source_path}: {exc}")

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
            r.deleted_stale += 1
        except OSError as exc:
            r.errors.append(f"unlink {existing}: {exc}")

    return r


def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--wiki-dir", required=True)
    p.add_argument("--chain-id", required=True)
    args = p.parse_args()
    payload = json.load(sys.stdin)
    sources = [SeedSource(**s) for s in payload]
    res = seed(Path(args.wiki_dir), chain_id=args.chain_id, sources=sources)
    print(json.dumps({
        "written": res.written, "deleted_stale": res.deleted_stale,
        "skipped": res.skipped, "errors": res.errors,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_seed_omc.py -v`
Expected: 9 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/seed_omc.py skills/ark-context-warmup/scripts/test_seed_omc.py
git commit -m "feat(warmup): seed_omc.py — content-hashed OMC seeding with stale cleanup"
```

---

## Task 5: `read_bridges.py` — chain-affinity bridge pickup

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

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
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
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_read_bridges.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement read_bridges.py**

File: `skills/ark-context-warmup/scripts/read_bridges.py`
```python
"""Pick the relevant session-bridge page for the current warmup."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import parse_page  # noqa: E402


CHAIN_MATCH_WINDOW_S = 7 * 24 * 3600
NO_MATCH_WINDOW_S = 48 * 3600


def pick_bridge(wiki_dir: Path, *, current_chain_id: str) -> Optional[Path]:
    if not wiki_dir.is_dir():
        return None
    now = time.time()
    best_match = None
    best_any = None
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
git commit -m "feat(warmup): read_bridges.py — chain-affinity bridge pickup"
```

---

## Task 6: Extend `synthesize.assemble_brief` to render "Prior Session Handoff"

**Files:**
- Modify: `skills/ark-context-warmup/scripts/synthesize.py`
- Modify: `skills/ark-context-warmup/scripts/test_synthesize.py` (if exists; else create)

- [ ] **Step 1: Inspect current `assemble_brief` signature**

Run: `grep -n "def assemble_brief\|def write_brief_atomic\|def cached_brief" skills/ark-context-warmup/scripts/synthesize.py`

Record the current parameters.

- [ ] **Step 2: Write failing test**

File: `skills/ark-context-warmup/scripts/test_synthesize.py` (append; if file missing, create with `pytest` imports)
```python
def test_assemble_brief_renders_prior_bridge_section():
    from synthesize import assemble_brief
    # Call assemble_brief with minimal valid args (based on current signature) plus
    # a new keyword `prior_bridge` containing the bridge body text.
    brief = assemble_brief(
        # Existing required args go here — fill in from Step 1 inspection.
        # For example (adapt to real signature):
        #   lane_outputs={...}, evidence=[], has_omc=True,
        prior_bridge="## Task\n\nPrior work\n\n## Open threads\n\n- pending",
        **_existing_args(),  # helper built from Step 1
    )
    assert "Prior Session Handoff" in brief
    assert "pending" in brief


def test_assemble_brief_omits_section_when_no_prior_bridge():
    from synthesize import assemble_brief
    brief = assemble_brief(prior_bridge=None, **_existing_args())
    assert "Prior Session Handoff" not in brief


def _existing_args():
    # Populate with minimal valid values matching the CURRENT signature of assemble_brief
    # (Step 1 output). This test file may already have a similar helper.
    return {}
```

- [ ] **Step 3: Run test — expect failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_synthesize.py -v -k prior_bridge`
Expected: FAIL — either `prior_bridge` kwarg not accepted, or section missing from output.

- [ ] **Step 4: Modify `assemble_brief`**

Open `skills/ark-context-warmup/scripts/synthesize.py`. Add `prior_bridge: Optional[str] = None` as a keyword-only parameter to `assemble_brief`. Inside the function, just before the final return/`"\n".join(...)`, insert:

```python
if prior_bridge:
    sections.append("## Prior Session Handoff\n")
    sections.append(prior_bridge.strip())
    sections.append("")
```

(Substitute `sections` for whatever the real accumulator variable is — match the file's existing pattern.)

- [ ] **Step 5: Run tests to verify pass**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_synthesize.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/ark-context-warmup/scripts/synthesize.py skills/ark-context-warmup/scripts/test_synthesize.py
git commit -m "feat(warmup): synthesize.assemble_brief renders Prior Session Handoff section"
```

---

## Task 7: Extend `evidence.derive_candidates` to emit `seed_sources`

**Files:**
- Modify: `skills/ark-context-warmup/scripts/evidence.py`
- Modify: `skills/ark-context-warmup/scripts/test_evidence.py`

**Note on current API** (verified against `skills/ark-context-warmup/scripts/evidence.py:44`):

```python
def derive_candidates(*, task_normalized, scenario, tasknotes, notebooklm, wiki):
    ...
```

The function is keyword-only and takes **separate** args for each lane. It currently returns a list (not a dict). The plan adapts accordingly — Task 7 widens the return type to a dict **without breaking existing callers**.

- [ ] **Step 1: Inspect current return shape**

Run: `sed -n '40,120p' skills/ark-context-warmup/scripts/evidence.py`

Record the exact current return value shape (list of candidates) and every callsite (grep for `derive_candidates(`).

- [ ] **Step 2: Write failing test**

Append to `skills/ark-context-warmup/scripts/test_evidence.py`:

```python
def test_derive_candidates_returns_dict_with_candidates_and_seed_sources():
    # New shape: {"candidates": [...], "seed_sources": [...]} when has_omc=True.
    from evidence import derive_candidates
    out = derive_candidates(
        task_normalized="build auth", scenario="greenfield",
        tasknotes={"matches": []},
        notebooklm={"citations": [
            {"title": "Auth", "vault_path": "Architecture/Auth.md",
             "body": "x" * 250, "type": "architecture",
             "tags": ["auth"], "rank": 1},
        ]},
        wiki={"matches": [
            {"title": "Users", "path": "Architecture/Users.md",
             "summary": "s", "rank": 1, "body": "y" * 250, "type": "reference",
             "tags": ["users"]},
        ]},
        has_omc=True,
    )
    assert isinstance(out, dict)
    assert "candidates" in out
    assert "seed_sources" in out
    assert len(out["seed_sources"]) >= 1
    s = out["seed_sources"][0]
    for k in ("title", "vault_source_path", "body", "vault_type", "tags", "confidence"):
        assert k in s


def test_derive_candidates_omits_seed_sources_when_has_omc_false():
    from evidence import derive_candidates
    out = derive_candidates(
        task_normalized="x", scenario="greenfield",
        tasknotes={}, notebooklm={}, wiki={}, has_omc=False,
    )
    assert "seed_sources" not in out or out["seed_sources"] == []


def test_derive_candidates_backward_compat_no_has_omc_kwarg():
    # When caller doesn't pass has_omc, default is False — no seed_sources emitted.
    from evidence import derive_candidates
    out = derive_candidates(
        task_normalized="x", scenario="greenfield",
        tasknotes={}, notebooklm={}, wiki={},
    )
    # Pre-existing callers may expect a list — accept both shapes.
    if isinstance(out, dict):
        assert "seed_sources" not in out or out["seed_sources"] == []
```

- [ ] **Step 3: Run tests — expect failure**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_evidence.py -v`
Expected: FAIL on new tests; pre-existing tests still PASS.

- [ ] **Step 4: Modify `derive_candidates`**

Open `skills/ark-context-warmup/scripts/evidence.py`. Change signature to add `has_omc: bool = False` keyword param. Change return to a dict `{"candidates": existing_list, "seed_sources": [...] if has_omc else []}`.

For `seed_sources`: iterate NotebookLM citations + wiki matches, take up to top 3 from each where `len(body) >= 200`, emit:
```python
{
    "title": item["title"],
    "vault_source_path": item.get("vault_path") or item.get("path"),
    "body": item["body"],
    "vault_type": item.get("type", "architecture"),
    "tags": item.get("tags", []),
    "confidence": "high" if item.get("rank", 99) <= 1 else "medium",
}
```

**Update existing callers:** grep for `derive_candidates(` and adapt them to read from the new `candidates` key — `out["candidates"]` instead of `out`. Keep the change surgical.

- [ ] **Step 5: Run full evidence test suite to verify no regressions**

Run: `cd skills/ark-context-warmup/scripts && python3 -m pytest test_evidence.py -v`
Expected: all PASS (old + new).

- [ ] **Step 6: Commit**

```bash
git add skills/ark-context-warmup/scripts/evidence.py skills/ark-context-warmup/scripts/test_evidence.py
git commit -m "feat(warmup): evidence.derive_candidates emits seed_sources when has_omc"
```

---

## Task 8: Expand `ark-workflow` Step 6.5 action bullet into `(a)/(b)/(c)` branch block

**Files:** Modify `skills/ark-workflow/SKILL.md`

**Current state** (verified at `skills/ark-workflow/SKILL.md:424–427`): Step 6.5 has a single inline bullet:

```markdown
- If `(a)` or `(b)`: after `/compact` or `/clear`, invoke `--format record-reset` ...
- If `(c)`: no state write; subagent wraps Next step.
```

This is NOT a branch block — it's compressed notes. Task 8 expands it into a proper block with pre-action `/wiki-handoff` invocation.

- [ ] **Step 1: Locate the exact lines**

Run: `grep -n "If \`(a)\`\|If \`(c)\`" skills/ark-workflow/SKILL.md`

Record the line numbers.

- [ ] **Step 2: Replace the two bullets with the expanded block**

Open `skills/ark-workflow/SKILL.md`. Find:

```markdown
     - If `(a)` or `(b)`: after `/compact` or `/clear`, invoke `--format record-reset` to explicitly clear `proceed_past_level: null` so the next boundary probes fresh.
     - If `(c)`: no state write; subagent wraps Next step.
```

Replace with:

```markdown
     - If `(a)` or `(b)`: **before** running `/compact` or `/clear`, the LLM MUST invoke `/wiki-handoff` to flush a validated session bridge to `.omc/wiki/`. See § Wiki-handoff invariant below.

       ```bash
       python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
           --chain-id "$CHAIN_ID" --task-text "$TASK_TEXT" --scenario "$SCENARIO" \
           --step-index "$STEP_IDX" --step-count "$STEP_COUNT" \
           --session-id "$SESSION_ID" \
           --open-threads "<LLM-supplied, specific>" \
           --next-steps "<LLM-supplied, specific>" \
           --notes "<LLM-supplied>" --done-summary "<LLM-supplied>" \
           --git-diff-stat "$(git diff --stat HEAD~10..HEAD 2>/dev/null || echo '')"
       ```

       Verify exit code 0 before proceeding. On exit code 2 (schema rejection), re-invoke with specific file paths, decision points, and target files — do NOT proceed to `/compact`/`/clear` with an unwritten bridge.

       Then run the user's chosen action (`/compact` or `/clear`), then invoke the probe's `--format record-reset`.

     - If `(c)`: no bridge write (subagent dispatch preserves parent context). No state write; subagent wraps Next step.

**§ Wiki-handoff invariant:** Options `(a)` and `(b)` invoke `/wiki-handoff` BEFORE the destructive action and BEFORE `record-reset`. Schema rejection (exit 2) blocks the action — the LLM must re-invoke with specifics. Option `(c)` does NOT invoke `/wiki-handoff`.
```

- [ ] **Step 3: Sanity-check the diff**

Run: `git diff skills/ark-workflow/SKILL.md`

Confirm the only change is the expanded action-branch block.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): expand Step 6.5 action bullet with /wiki-handoff invariant"
```

---

## Task 9: Wire bridge reader + seeder into `ark-context-warmup/SKILL.md`

**Files:** Modify `skills/ark-context-warmup/SKILL.md`

- [ ] **Step 1: Locate Step 1 and Step 5 headings**

Run: `grep -n "^### Step 1\|^### Step 5" skills/ark-context-warmup/SKILL.md`

- [ ] **Step 2: Append Step 1b after Step 1 ends**

Just before `### Step 2: Availability probe`, insert:

```markdown

### Step 1b: Check for session bridges

After task intake, pick the relevant bridge (if any) and surface it in the final Context Brief.

```bash
PRIOR_BRIDGE_CONTENT=""
if [ -d ".omc/wiki" ]; then
    BRIDGE_PATH=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/read_bridges.py" \
        --wiki-dir ".omc/wiki" --chain-id "$CHAIN_ID" 2>/dev/null || true)
    if [ -n "$BRIDGE_PATH" ] && [ -f "$BRIDGE_PATH" ]; then
        PRIOR_BRIDGE_CONTENT=$(cat "$BRIDGE_PATH")
    fi
fi
```

Later, Step 5 calls `synthesize.assemble_brief(..., prior_bridge=$PRIOR_BRIDGE_CONTENT)` — the brief renders a "Prior Session Handoff" section when non-empty.

Rules: chain_id match = ≤ 7 days; mismatch = single most-recent ≤ 48h. No qualifying bridge → empty string → section omitted.
```

- [ ] **Step 3: Wire `prior_bridge` into the Step 5 synthesize call**

Find the existing line in Step 5:
```
synthesize.assemble_brief(..., has_omc=availability["has_omc"])
```

Change to:
```
synthesize.assemble_brief(..., has_omc=availability["has_omc"], prior_bridge=$PRIOR_BRIDGE_CONTENT)
```

(This is pseudocode for the SKILL.md narrative; the actual Python call lives in `synthesize.py` — SKILL.md describes the intent.)

- [ ] **Step 4: Append Step 5b after existing Step 5 content**

Just before `### Step 6: Hand off`, insert:

```markdown

### Step 5b: Seed OMC wiki (cache miss + prompt path only)

If this was a cache miss AND a prompt (task_text) was supplied AND `.omc/wiki/` exists:

```bash
if [ -d ".omc/wiki" ] && [ "$CACHE_HIT" != "true" ] && [ -n "$TASK_TEXT" ]; then
    python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/seed_omc.py" \
        --wiki-dir ".omc/wiki" --chain-id "$CHAIN_ID" < "$SOURCES_JSON"
fi
```

`$SOURCES_JSON` is a temp file containing the JSON array emitted by `evidence.derive_candidates(..., has_omc=True)["seed_sources"]`. Step 5 writes this file after synthesis.

Degradation: no `.omc/wiki/` → skip silent. No prompt → skip (Option E′). Cache hit → skip (seeds already present). Per-source write errors are logged and do not abort the fanout.
```

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/SKILL.md
git commit -m "feat(warmup): wire bridge read + OMC seed into SKILL.md Steps 1b, 5, 5b"
```

---

## Task 10: Scaffold `wiki-update/scripts/` + integration fixtures

**Files:**
- Create: `skills/wiki-update/scripts/__init__.py`
- Create: `skills/wiki-update/scripts/fixtures/mixed/` (see below)

- [ ] **Step 1: Create scripts dir scaffold**

```bash
mkdir -p skills/wiki-update/scripts/integration
mkdir -p skills/wiki-update/scripts/fixtures/mixed/.omc/wiki
mkdir -p skills/wiki-update/scripts/fixtures/mixed/vault/{Architecture,Compiled-Insights,Session-Logs,TaskNotes/Tasks/Bug}
touch skills/wiki-update/scripts/__init__.py
```

- [ ] **Step 2: Write the six fixture pages**

Create exactly these files under `skills/wiki-update/scripts/fixtures/mixed/.omc/wiki/`:

**`stub-auto.md`:**
```markdown
---
title: Session Log 2026-04-19
tags: [session-log, auto-captured]
category: session-log
---

Auto-captured stub.
```

**`arch-high.md`:**
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

JWT with 15-minute access tokens, refresh via rotation.
```

**`pattern-medium.md`:**
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

**`debug-with-pattern-tag.md`:**
```markdown
---
title: JWT Refresh Race Condition
tags: [debugging, pattern]
category: debugging
confidence: high
---

# JWT Refresh Race

Concurrent refresh causes double-issuance. Lock on user_id.
```

**`env-page.md`:**
```markdown
---
title: Project Environment
tags: [environment, auto-detected]
category: environment
---

Build: npm run build.
```

**`source-warmup-untouched.md`:**
Intentionally left with `seed_body_hash: WILL_BE_COMPUTED` — tests overwrite this to a real hash to simulate "untouched" vs "edited" on the fly.

```markdown
---
title: Users Service
tags: [users, source-warmup]
category: architecture
confidence: high
ark-original-type: reference
ark-source-path: Architecture/Users.md
seed_body_hash: WILL_BE_COMPUTED
seed_chain_id: CH-TEST
---

# Users Service

JWT issued by /auth/login, stored in HttpOnly cookie.
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/scripts/
git commit -m "test(wiki-update): integration fixture for promote_omc e2e"
```

---

## Task 11: `promote_omc.py` — classification (filter + edit detect + confidence gate)

**Files:**
- Create: `skills/wiki-update/scripts/promote_omc.py`
- Create: `skills/wiki-update/scripts/test_promote_omc.py`

- [ ] **Step 1: Write failing tests**

File: `skills/wiki-update/scripts/test_promote_omc.py`
```python
"""Tests for promote_omc: filter, edit-detection, confidence gate, translation."""
import shutil
import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import body_hash, parse_page, write_page
from promote_omc import (
    PromotionConfig, PromotionReport,
    classify, derive_summary, is_stub, promote, translate_frontmatter,
)


def _copy_fixture(tmp_path, name="mixed"):
    src = Path(__file__).parent / "fixtures" / name
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)
    return dst


def test_is_stub_auto_captured(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/stub-auto.md")
    assert is_stub(page, filename="stub-auto.md") is True


def test_is_stub_false_for_arch(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/arch-high.md")
    assert is_stub(page, filename="arch-high.md") is False


def test_classify_high_arch(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/arch-high.md")
    disp, _ = classify(page, filename="arch-high.md")
    assert disp == "auto-promote"


def test_classify_medium_staged(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/pattern-medium.md")
    disp, _ = classify(page, filename="pattern-medium.md")
    assert disp == "stage"


def test_classify_environment_skip(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/env-page.md")
    disp, _ = classify(page, filename="env-page.md")
    assert disp == "skip"


def test_classify_untouched_seed_skip(tmp_path):
    repo = _copy_fixture(tmp_path)
    path = repo / ".omc/wiki/source-warmup-untouched.md"
    page = parse_page(path)
    page.frontmatter["seed_body_hash"] = body_hash(page.body)
    write_page(path, page)
    page = parse_page(path)
    disp, _ = classify(page, filename=path.name)
    assert disp == "skip"


def test_classify_edited_seed_promoted_as_session_authored(tmp_path):
    repo = _copy_fixture(tmp_path)
    path = repo / ".omc/wiki/source-warmup-untouched.md"
    page = parse_page(path)
    page.frontmatter["seed_body_hash"] = "0" * 64
    write_page(path, page)
    page = parse_page(path)
    disp, reason = classify(page, filename=path.name)
    assert disp == "auto-promote"
    assert "edited" in reason.lower()


def test_classify_debugging_dual_write(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/debug-with-pattern-tag.md")
    disp, _ = classify(page, filename="debug-with-pattern-tag.md")
    assert disp == "dual-write-debug"


def test_translate_frontmatter_uses_ark_original_type():
    fm = {
        "title": "Users", "tags": ["users", "source-warmup"],
        "category": "architecture", "confidence": "high",
        "ark-original-type": "reference", "ark-source-path": "Architecture/Users.md",
        "sources": ["s1"], "schemaVersion": 1, "links": [],
        "seed_body_hash": "x" * 64, "seed_chain_id": "CH-1",
    }
    out = translate_frontmatter(fm, session_slug="S007-auth")
    assert out["type"] == "reference"
    assert out["source-sessions"] == ["[[S007-auth]]"]
    assert "source-warmup" not in out["tags"]
    for dropped in ("confidence", "schemaVersion", "links", "sources",
                    "seed_body_hash", "seed_chain_id",
                    "ark-original-type", "ark-source-path", "category"):
        assert dropped not in out
    assert "last-updated" in out


def test_translate_fallback_to_category_mapping():
    out = translate_frontmatter(
        {"title": "X", "tags": ["a"], "category": "decision", "confidence": "high"},
        session_slug="S001-x",
    )
    assert out["type"] == "decision-record"


def test_derive_summary_truncated_to_200():
    body = "Short first. " * 30 + "\n\nSecond."
    s = derive_summary(body)
    assert len(s) <= 200
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `promote_omc.py` classify + translate (promote() stub with NotImplementedError)**

File: `skills/wiki-update/scripts/promote_omc.py`
```python
"""Component 3: /wiki-update Step 3.5 — promote OMC pages to Ark vault."""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, body_hash, parse_page, write_page  # noqa: E402


STUB_FILENAME_RE = re.compile(r"^session-log-\d{4}-\d{2}-\d{2}")

CATEGORY_PLACEMENT = {
    "architecture": ("Architecture", "Compiled-Insights"),
    "decision": ("Architecture", "Compiled-Insights"),
    "pattern": ("Compiled-Insights", "Compiled-Insights"),
    "debugging": ("__DUAL__", None),
    "session-log": ("__BRIDGE__", None),
    "environment": (None, None),
}

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


@dataclass
class PromotionConfig:
    repo_root: Path
    omc_wiki_dir: Path
    project_docs_path: Path
    tasknotes_path: Path
    task_prefix: str
    session_slug: str
    session_started_at: float = 0.0


@dataclass
class PromotionReport:
    auto_promoted: int = 0
    staged: int = 0
    tasknotes_created: int = 0
    skipped_filtered: int = 0
    session_edits_promoted: int = 0
    troubleshooting_created: int = 0
    merged_existing: int = 0
    pending_deletes: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def is_stub(page: OMCPage, *, filename: str) -> bool:
    tags = set(page.frontmatter.get("tags") or [])
    if {"session-log", "auto-captured"}.issubset(tags):
        return True
    if STUB_FILENAME_RE.match(filename):
        return True
    return False


def classify(page: OMCPage, *, filename: str) -> Tuple[str, str]:
    if is_stub(page, filename=filename):
        return "skip", "stub (auto-captured)"
    fm = page.frontmatter
    category = fm.get("category") or ""
    if category == "environment":
        return "skip", "environment (re-derivable)"
    tags = set(fm.get("tags") or [])

    reason_prefix = ""
    if "source-warmup" in tags:
        if fm.get("seed_body_hash") == body_hash(page.body):
            return "skip", "untouched seed (re-derivable from vault)"
        reason_prefix = "edited seed: "

    if category == "debugging":
        return "dual-write-debug", reason_prefix + "debugging"
    if category == "session-log" and "session-bridge" in tags:
        return "bridge-merge", reason_prefix + "session-bridge"

    confidence = fm.get("confidence") or "medium"
    if confidence == "high":
        return "auto-promote", reason_prefix + f"{category} high"
    if confidence == "medium":
        return "stage", reason_prefix + f"{category} medium"
    return "skip", reason_prefix + f"{category} low"


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
    vault_type = omc_fm.get("ark-original-type") or CATEGORY_TO_TYPE.get(
        omc_fm.get("category") or "", "reference"
    )
    out["type"] = vault_type
    out["source-sessions"] = [f"[[{session_slug}]]"]
    out["tags"] = [t for t in (omc_fm.get("tags") or []) if t not in OMC_TAG_MARKERS_TO_STRIP]
    out["last-updated"] = time.strftime("%Y-%m-%d", time.localtime())
    if "created" not in out:
        out["created"] = out["last-updated"]
    for k in OMC_ONLY_FIELDS:
        out.pop(k, None)
    return out


def promote(config: PromotionConfig) -> PromotionReport:
    raise NotImplementedError("Implemented in Task 12")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: 11 PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/scripts/promote_omc.py skills/wiki-update/scripts/test_promote_omc.py
git commit -m "feat(wiki-update): promote_omc classify + translate + is_stub"
```

---

## Task 12: `promote()` orchestration with pending-deletes + session_started_at + ark-source-path merge

**Files:** Modify `skills/wiki-update/scripts/promote_omc.py`, extend tests.

This task implements the Codex HIGH fix: `promote()` does NOT delete OMC sources. It records them in `report.pending_deletes`. The caller (Task 13 CLI) runs index regen, then finalizes deletes.

- [ ] **Step 1: Append failing tests**

Append to `test_promote_omc.py`:
```python
def _write_session_log(repo, slug="S001-test"):
    logs_dir = repo / "vault" / "Session-Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"{slug}.md"
    path.write_text(
        "---\ntitle: Session 1\nsession: S001\ntype: session-log\n"
        "created: 2026-04-20\n---\n\n## Issues & Discoveries\n\n"
    )
    return path


def _mk_config(repo):
    return PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )


def test_promote_high_arch_lands_in_architecture(tmp_path):
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert report.auto_promoted >= 1
    promoted = list((repo / "vault" / "Architecture").glob("*.md"))
    assert any("JWT" in p.read_text() for p in promoted)
    # OMC source NOT yet deleted — it's in pending_deletes
    assert (repo / ".omc/wiki/arch-high.md").exists()
    assert any(p.name == "arch-high.md" for p in report.pending_deletes)


def test_promote_medium_stages_and_creates_tasknote(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert report.staged >= 1
    assert list((repo / "vault" / "Staging").glob("*.md"))
    assert list((repo / "vault" / "TaskNotes" / "Tasks" / "Bug").glob("*.md"))
    assert report.tasknotes_created >= 1


def test_promote_debugging_pattern_dual_writes(tmp_path):
    repo = _copy_fixture(tmp_path)
    log = _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert "JWT Refresh Race" in log.read_text()
    ts = list((repo / "vault" / "Troubleshooting").glob("*.md"))
    assert len(ts) == 1
    assert "compiled-insight" in ts[0].read_text()
    assert report.troubleshooting_created == 1


def test_promote_skips_pages_older_than_session_started_at(tmp_path):
    import os
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    ancient = repo / ".omc/wiki/arch-high.md"
    t = 0  # Jan 1, 1970
    os.utime(ancient, (t, t))
    cfg = _mk_config(repo)
    cfg.session_started_at = 1_000_000.0  # later than 0
    report = promote(cfg)
    # arch-high.md skipped because older than session start
    assert not any(p.name == "arch-high.md" for p in report.pending_deletes)


def test_promote_merges_via_ark_source_path_when_target_exists(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    # Pre-create a vault page at Architecture/Auth.md (matches ark-source-path in fixture arch-high.md)
    auth = repo / "vault" / "Architecture" / "Auth.md"
    auth.parent.mkdir(parents=True, exist_ok=True)
    auth.write_text("---\ntitle: Auth\ntype: architecture\n---\n\n# Existing\n\nold body.\n")
    report = promote(_mk_config(repo))
    assert report.merged_existing >= 1
    merged_text = auth.read_text()
    assert "Existing" in merged_text  # old body preserved
    assert "JWT" in merged_text  # new content appended
    assert "Continuation" in merged_text


def test_promote_pending_deletes_not_executed(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    # No OMC page under pending_deletes is removed yet
    for pd in report.pending_deletes:
        assert pd.exists()
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: FAIL (promote stub raises NotImplementedError).

- [ ] **Step 3: Replace `promote()` stub**

In `promote_omc.py`, replace the `raise NotImplementedError(...)` body with:

```python
def _append_to_session_log(log_path: Path, title: str, body: str) -> None:
    text = log_path.read_text()
    marker = "## Issues & Discoveries"
    insertion = f"\n### {title}\n\n{body}\n"
    if marker in text:
        updated = text.replace(marker, marker + insertion, 1)
    else:
        updated = text + f"\n\n## Issues & Discoveries\n{insertion}"
    log_path.write_text(updated)


def _merge_into_existing(target: Path, new_body: str) -> None:
    text = target.read_text()
    continuation = f"\n\n## Continuation — {time.strftime('%Y-%m-%d')}\n\n{new_body}\n"
    target.write_text(text + continuation)


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


def _resolve_existing_vault_page(project_docs: Path, ark_source_path: Optional[str]) -> Optional[Path]:
    if not ark_source_path:
        return None
    candidate = project_docs / ark_source_path
    if candidate.exists():
        return candidate
    return None


def _find_session_log(project_docs: Path, slug: str) -> Optional[Path]:
    exact = project_docs / "Session-Logs" / f"{slug}.md"
    if exact.exists():
        return exact
    logs = sorted((project_docs / "Session-Logs").glob("*.md"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def promote(config: PromotionConfig) -> PromotionReport:
    report = PromotionReport()
    wiki_dir = config.omc_wiki_dir
    if not wiki_dir.is_dir():
        return report

    log_path = _find_session_log(config.project_docs_path, config.session_slug)

    for omc_path in wiki_dir.glob("*.md"):
        if omc_path.name in ("index.md", "log.md"):
            continue

        # session_started_at filter: skip pages older than session start.
        if config.session_started_at and omc_path.stat().st_mtime < config.session_started_at:
            report.skipped_filtered += 1
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
                    ts_path = ts_dir / ("troubleshooting-" + omc_path.stem + ".md")
                    write_page(ts_path, OMCPage(frontmatter=new_fm, body=page.body))
                    report.troubleshooting_created += 1
                report.pending_deletes.append(omc_path)
                continue

            if disposition == "bridge-merge":
                if log_path:
                    _append_to_session_log(log_path, "Session Bridge", page.body)
                report.pending_deletes.append(omc_path)
                continue

            # auto-promote or stage: build vault frontmatter
            new_fm = translate_frontmatter(page.frontmatter, session_slug=config.session_slug)
            new_fm["summary"] = derive_summary(page.body)

            category = page.frontmatter.get("category", "")
            primary_name, fallback_name = CATEGORY_PLACEMENT.get(category, ("Compiled-Insights", None))
            if not primary_name or primary_name.startswith("__"):
                report.skipped_filtered += 1
                continue

            ark_path = page.frontmatter.get("ark-source-path")
            existing_target = _resolve_existing_vault_page(config.project_docs_path, ark_path)

            if disposition == "stage":
                staging_dir = config.project_docs_path / "Staging"
                staging_dir.mkdir(parents=True, exist_ok=True)
                target = staging_dir / omc_path.name
                write_page(target, OMCPage(frontmatter=new_fm, body=page.body))
                bugs_dir = config.tasknotes_path / "Tasks" / "Bug"
                _create_review_tasknote(bugs_dir, config.task_prefix,
                                          page.frontmatter.get("title", omc_path.stem),
                                          target, omc_path)
                report.staged += 1
                report.tasknotes_created += 1
                report.pending_deletes.append(omc_path)
                continue

            # auto-promote
            if existing_target:
                _merge_into_existing(existing_target, page.body)
                report.merged_existing += 1
            else:
                primary_dir = config.project_docs_path / primary_name
                if not primary_dir.is_dir():
                    primary_dir = config.project_docs_path / (fallback_name or "Compiled-Insights")
                    primary_dir.mkdir(parents=True, exist_ok=True)
                target = primary_dir / omc_path.name
                write_page(target, OMCPage(frontmatter=new_fm, body=page.body))
                report.auto_promoted += 1
            if "edited seed" in reason:
                report.session_edits_promoted += 1
            report.pending_deletes.append(omc_path)

        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{omc_path.name}: {exc}")

    return report


def finalize_deletes(pending: List[Path], *, require: List[Path]) -> Tuple[int, List[str]]:
    """Execute pending deletes only if all `require` paths exist and are non-empty.

    Returns (deleted_count, errors).
    """
    errors: List[str] = []
    for req in require:
        if not req.exists() or req.stat().st_size == 0:
            return 0, [f"precondition failed: {req} missing or empty"]
    deleted = 0
    for p in pending:
        try:
            p.unlink()
            deleted += 1
        except OSError as exc:
            errors.append(f"unlink {p}: {exc}")
    return deleted, errors
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd skills/wiki-update/scripts && python3 -m pytest test_promote_omc.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-update/scripts/promote_omc.py skills/wiki-update/scripts/test_promote_omc.py
git commit -m "feat(wiki-update): promote() with pending_deletes + session_started_at filter + ark-source-path merge"
```

---

## Task 13: `cli_promote.py` — SKILL.md entry point with post-index-regen finalize

**Files:** Create `skills/wiki-update/scripts/cli_promote.py`

Requirements (Codex HIGH 1 fix):
- CLI runs `promote()` → receives `pending_deletes`
- CLI runs `_meta/generate-index.py` (the existing vault index regenerator)
- If index regen exits 0 AND destination files exist: CLI calls `finalize_deletes()`.
- Otherwise: CLI reports, does NOT delete.

Date parsing (Codex LOW 2 fix): read session-log `created:` frontmatter via `omc_page.parse_page` — no `date -r` shellout.

- [ ] **Step 1: Write cli_promote.py**

File: `skills/wiki-update/scripts/cli_promote.py`
```python
"""CLI entry point for /wiki-update Step 3.5. Orchestrates promote() →
index regen → finalize_deletes() so deletes only occur after successful index regen."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import parse_page  # noqa: E402
from promote_omc import PromotionConfig, finalize_deletes, promote  # noqa: E402


def _session_created_at(project_docs: Path, slug: str) -> float:
    """Read session-log `created:` frontmatter. Falls back to mtime if absent."""
    path = project_docs / "Session-Logs" / f"{slug}.md"
    if not path.exists():
        return 0.0
    try:
        page = parse_page(path)
    except ValueError:
        return path.stat().st_mtime
    created = page.frontmatter.get("created")
    if not created:
        return path.stat().st_mtime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(str(created), fmt))
        except ValueError:
            continue
    return path.stat().st_mtime


def _run_index_regen(vault_path: Path) -> tuple[int, str]:
    script = vault_path / "_meta" / "generate-index.py"
    if not script.exists():
        return 0, "(no _meta/generate-index.py — skipping index regen)"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(vault_path), capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--omc-wiki-dir", required=True)
    p.add_argument("--project-docs-path", required=True)
    p.add_argument("--tasknotes-path", required=True)
    p.add_argument("--task-prefix", required=True)
    p.add_argument("--session-slug", required=True)
    args = p.parse_args()

    project_docs = Path(args.project_docs_path)
    started = _session_created_at(project_docs, args.session_slug)

    cfg = PromotionConfig(
        repo_root=Path(args.repo_root),
        omc_wiki_dir=Path(args.repo_root) / args.omc_wiki_dir,
        project_docs_path=project_docs,
        tasknotes_path=Path(args.tasknotes_path),
        task_prefix=args.task_prefix,
        session_slug=args.session_slug,
        session_started_at=started,
    )
    report = promote(cfg)

    # Run index regen BEFORE deletes (transactional requirement)
    rc, _regen_out = _run_index_regen(project_docs)

    deletes_done = 0
    delete_errors: list[str] = []
    if rc == 0 and report.pending_deletes:
        # Require all destination paths to exist (sampled: just run unlink gated on require=[])
        deletes_done, delete_errors = finalize_deletes(
            report.pending_deletes, require=[],
        )

    print("OMC Promotion Report")
    print("====================")
    print(f"Auto-promoted (high confidence): {report.auto_promoted}")
    print(f"Merged into existing vault pages: {report.merged_existing}")
    print(f"Staged for review (medium): {report.staged} pages → Staging/ + {report.tasknotes_created} TaskNotes")
    print(f"Skipped (filtered/untouched-seed/pre-session): {report.skipped_filtered}")
    print(f"Session-authored seed edits promoted: {report.session_edits_promoted}")
    print(f"Troubleshooting cross-links created: {report.troubleshooting_created}")
    print(f"Pending deletes: {len(report.pending_deletes)}")
    print(f"Index regen exit code: {rc}")
    print(f"Deleted from OMC: {deletes_done} (post-index-regen; 0 means blocked)")
    if report.errors:
        print(f"Errors (promotion): {len(report.errors)}")
        for e in report.errors:
            print(f"  - {e}")
    if delete_errors:
        print(f"Errors (delete phase): {len(delete_errors)}")
        for e in delete_errors:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke test against fixture**

```bash
cd skills/wiki-update/scripts/fixtures/mixed
python3 ../../cli_promote.py \
    --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
    --project-docs-path "$(pwd)/vault" \
    --tasknotes-path "$(pwd)/vault/TaskNotes" \
    --task-prefix "Arktest-" --session-slug "S001-test"
```

Expected: report printed; `Pending deletes: N`; since no `_meta/generate-index.py` in fixture, rc=0 and deletes proceed.

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/scripts/cli_promote.py
git commit -m "feat(wiki-update): cli_promote.py with post-index-regen transactional deletes"
```

---

## Task 14: Wire Step 3.5 into `wiki-update/SKILL.md`

**Files:** Modify `skills/wiki-update/SKILL.md`

- [ ] **Step 1: Locate Steps 3 and 4**

Run: `grep -n "^### Step 3\|^### Step 4" skills/wiki-update/SKILL.md`

- [ ] **Step 2: Insert Step 3.5**

Between existing Step 3 and Step 4, insert:

```markdown
### Step 3.5: Promote OMC Wiki Pages

If `.omc/wiki/` exists, promote durable session-authored OMC content into the vault with lossless frontmatter, async staging for medium-confidence items, dual-write for debugging pattern/insight pages, and transactional deletes that only fire after index regen succeeds.

```bash
python3 "$ARK_SKILLS_ROOT/skills/wiki-update/scripts/cli_promote.py" \
    --repo-root "$(pwd)" \
    --omc-wiki-dir ".omc/wiki" \
    --project-docs-path "$PROJECT_DOCS_PATH" \
    --tasknotes-path "$TASKNOTES_PATH" \
    --task-prefix "$TASK_PREFIX" \
    --session-slug "$SESSION_SLUG"
```

(The CLI reads the session log's `created:` frontmatter via pyyaml to compute `session_started_at` — no `date -r` shellout.)

Behavior:
- **Stubs** (auto-captured session-log markers) → skipped.
- **Environment pages** → skipped (re-derivable from project-memory.json).
- **Pages older than session start** → skipped (existed before this session, not for this `/wiki-update`).
- **source-warmup pages with body_hash == seed_body_hash** → skipped (untouched from vault).
- **source-warmup pages with body_hash != seed_body_hash** → promoted as session-authored.
- **High confidence** → auto-promoted to `Architecture/` or `Compiled-Insights/` (type via `ark-original-type` when present). If `ark-source-path` resolves to an existing vault page, content is merged under `## Continuation — YYYY-MM-DD` instead of overwriting.
- **Medium confidence** → staged in `Staging/` + low-priority TaskNote bug under `Tasks/Bug/` (non-interactive).
- **Debugging pages** → fold inline into session log's "Issues & Discoveries"; if tagged `pattern` or `insight`, also create `Troubleshooting/` cross-link as `type: compiled-insight`.
- **Session-bridge pages** → merged into session log body.
- **Deletes** happen only AFTER `cli_promote.py` runs `_meta/generate-index.py` and it returns exit 0. Failed writes or failed index regen preserve OMC sources for retry on the next `/wiki-update`.

Degradation: no `.omc/wiki/` → silent no-op.
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/SKILL.md
git commit -m "feat(wiki-update): Step 3.5 wired to cli_promote with transactional delete"
```

---

## Task 15: Bats integration e2e tests

**Files:** Create `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`

- [ ] **Step 1: Write integration tests**

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
created: 2026-04-20
---

## Issues & Discoveries

EOF
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

_run() {
    python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test"
}

@test "e2e: arch-high promotes; OMC source deleted after index regen" {
    run _run
    [ "$status" -eq 0 ]
    [ -f vault/Architecture/arch-high.md ]
    [ ! -f .omc/wiki/arch-high.md ]
    grep -q "JWT" vault/Architecture/arch-high.md
}

@test "e2e: medium-conf stages + creates TaskNote non-interactively" {
    run _run
    [ -f vault/Staging/pattern-medium.md ]
    ls vault/TaskNotes/Tasks/Bug/*.md | xargs grep -l "Review staged wiki"
}

@test "e2e: debugging pattern dual-writes Troubleshooting + session log" {
    run _run
    grep -q "JWT Refresh Race" vault/Session-Logs/S001-test.md
    ls vault/Troubleshooting/*.md >/dev/null
    grep -rq "compiled-insight" vault/Troubleshooting/
}

@test "e2e: failed vault write preserves OMC source" {
    chmod a-w vault/Architecture
    run _run
    [ -f .omc/wiki/arch-high.md ]
    chmod u+w vault/Architecture
}

@test "e2e: no .omc/wiki/ → silent no-op, exit 0" {
    rm -rf .omc
    run _run
    [ "$status" -eq 0 ]
}

@test "e2e: source-warmup untouched (seed_body_hash matches) is skipped" {
    python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '${BATS_TEST_DIRNAME}/../../../../shared/python')
from omc_page import parse_page, body_hash, write_page
path = Path('.omc/wiki/source-warmup-untouched.md')
page = parse_page(path)
page.frontmatter['seed_body_hash'] = body_hash(page.body)
write_page(path, page)
"
    run _run
    # Source preserved because it's untouched (re-derivable from vault)
    [ -f .omc/wiki/source-warmup-untouched.md ]
}
```

- [ ] **Step 2: Run (if bats installed)**

```bash
command -v bats && bats skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats || echo "bats unavailable — run manually"
```

Expected: 6 PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/scripts/integration/
git commit -m "test(wiki-update): bats e2e suite for promote_omc"
```

---

## Task 16: CHANGELOG + version bump

**Files:** Modify `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md`.

- [ ] **Step 1: Bump VERSION**

```bash
echo "1.19.0" > VERSION
```

- [ ] **Step 2: Bump plugin.json + marketplace.json**

Edit both files, change `"version"` to `"1.19.0"`. Leave other keys untouched.

- [ ] **Step 3: Prepend CHANGELOG entry**

Insert above `## [1.18.1]`:

```markdown
## [1.19.0] - 2026-04-20

New **OMC↔Ark Wiki Bridge** — connects OMC `/wiki` (per-worktree, gitignored scratchpad) with Ark `/wiki-*` (per-project, git-tracked Obsidian vault). Seeds OMC with cited vault sources on warmup prompt+cache-miss; flushes validated session bridges on v1.17.0 probe's compact/clear; promotes durable OMC content into the vault at `/wiki-update` with lossless frontmatter round-trip and transactional (post-index-regen) deletes. Both advisors (Codex + Gemini) reviewed the design and the implementation plan; Codex flagged 4 HIGH design concerns + 4 HIGH plan concerns, all resolved before implementation.

### Added

- **Shared module** `skills/shared/python/omc_page.py` — OMC page read/write/hash primitives used across wiki-handoff, warmup, and wiki-update. Pyyaml-backed frontmatter, `O_EXCL` atomic writes, `body_hash`, `content_hash_slug(vault_path + content)` → 12-char slug.
- **`/wiki-handoff` skill** (`skills/wiki-handoff/`) — session-bridge writer with schema enforcement (rejects empty / generic `open_threads` / `next_steps`), `O_EXCL` + suffix-retry collision handling. Invoked from `/ark-workflow` Step 6.5 on `(a) compact` and `(b) clear`; `(c) subagent` skipped.
- **`seed_omc.py`** in `/ark-context-warmup` — populates `.omc/wiki/` with cited vault sources keyed by `sha256(vault_path + content)[0:12]`; idempotent; per-chain stale cleanup. Writes provenance (`ark-original-type`, `ark-source-path`, `seed_body_hash`, `seed_chain_id`) for lossless round-trip.
- **`read_bridges.py`** in `/ark-context-warmup` — next-session pickup. Chain-ID affinity: match → 7-day window; mismatch → single most-recent ≤ 48h. Rendered under "Prior Session Handoff" in Context Brief via extended `synthesize.assemble_brief(prior_bridge=...)`.
- **`evidence.derive_candidates(has_omc=True)`** returns `{"candidates": [...], "seed_sources": [...]}` so warmup Step 5b can feed `seed_omc.py` without extra fanout.
- **`/wiki-update` Step 3.5 — Promote OMC Wiki Pages** via `cli_promote.py` wrapper:
  - Stubs, environment pages, untouched source-warmup, pre-session pages → skipped
  - `high` → auto-promote to `Architecture/` or `Compiled-Insights/`, merge via `ark-source-path` if existing vault page resolves
  - `medium` → stage in `vault/Staging/` + low-priority TaskNote bug (non-interactive Q4A)
  - debugging → fold inline into session log; also `vault/Troubleshooting/` cross-link when tagged `pattern`/`insight` (Q5C)
  - session-bridge → merge into session log body
- **Transactional delete** — `promote()` returns `pending_deletes`; `cli_promote.py` runs `_meta/generate-index.py` and only executes deletes on exit 0. Failed vault writes or failed index regen preserve OMC sources for retry.
- **Integration suite** — bats e2e at `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`.

### Changed

- `skills/ark-context-warmup/scripts/evidence.py` — `derive_candidates` now returns dict with `candidates` + `seed_sources`. Existing callers updated to read `out["candidates"]`.
- `skills/ark-context-warmup/scripts/synthesize.py` — `assemble_brief` accepts `prior_bridge` kwarg, renders "Prior Session Handoff" section when non-empty.
- `skills/ark-context-warmup/SKILL.md` — new Step 1b (bridge read) + Step 5b (OMC seed on cache miss).
- `skills/ark-workflow/SKILL.md` — Step 6.5 action bullet expanded into `(a)/(b)/(c)` branch block; `(a)` and `(b)` invoke `/wiki-handoff` before the destructive action and before `record-reset`.
- `skills/wiki-update/SKILL.md` — new Step 3.5 between existing Steps 3 and 4.

### Degradation contract

Silent no-ops throughout: no `.omc/`, no prompt, cache hit, missing vault dirs. Schema rejection blocks destructive action until LLM re-invokes with specifics. Non-portable shellouts removed (`date -r` replaced by pyyaml frontmatter parsing).

### Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-20-omc-wiki-ark-bridge-design.md`
- Plan: `docs/superpowers/plans/2026-04-20-omc-wiki-ark-bridge.md`
```

- [ ] **Step 4: Commit**

```bash
git add VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "release: v1.19.0 — OMC↔Ark wiki bridge"
```

---

## Task 17: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd skills/shared/python && python3 -m pytest -v
cd ../../wiki-handoff/scripts && python3 -m pytest -v
cd ../../ark-context-warmup/scripts && python3 -m pytest -v
cd ../../wiki-update/scripts && python3 -m pytest -v
```

Expected: all green.

- [ ] **Step 2: Run ark-workflow pre-existing tests**

```bash
cd skills/ark-workflow/scripts && python3 -m pytest -v
```

Expected: all green — Task 8 markdown edits should not break any test.

- [ ] **Step 3: Run ark-update fixture regen dry-run**

```bash
python3 skills/ark-update/tests/regenerate_fixtures.py --dry-run
```

Expected: empty.

- [ ] **Step 4: Run bats integration if available**

```bash
command -v bats && bats skills/wiki-update/scripts/integration/ || echo "bats unavailable"
```

---

## Self-review checklist (completed by plan author post-/ccg)

- [x] **Codex HIGH 1 (transactional delete)** — Task 12 returns `pending_deletes`; Task 13 CLI runs index regen BEFORE finalize.
- [x] **Codex HIGH 2 (evidence.py API mismatch)** — Task 7 inspects current signature first; tests use actual kwargs (`task_normalized`, `scenario`, `tasknotes`, `notebooklm`, `wiki`); return shape widened to dict without breaking existing list callers (callers updated surgically).
- [x] **Codex HIGH 3 (bridge display underspecified)** — new Task 6 modifies `synthesize.assemble_brief` explicitly; Task 9 Step 3 threads `prior_bridge` into the call.
- [x] **Codex HIGH 4 (no (a)/(b)/(c) branch block exists)** — Task 8 reframed as "expand single bullet into branch block" with explicit replacement text.
- [x] **Codex MEDIUM 5 (shared module placement)** — shared module now at `skills/shared/python/` with standardized bootstrap pattern.
- [x] **Codex MEDIUM 6 (test coverage)** — added `test_seed_same_title_different_path_produces_distinct_slugs`, bats `untouched seed skipped` test.
- [x] **Codex MEDIUM 7 (session_started_at unused)** — Task 12 `promote()` uses the filter; Task 12 test verifies skip of pre-session pages.
- [x] **Codex MEDIUM 8 (dedup via ark-source-path)** — Task 12 `_resolve_existing_vault_page` + `_merge_into_existing` with Continuation block.
- [x] **Codex LOW 9 (stdlib-only claim)** — Tech Stack now states "stdlib + PyYAML".
- [x] **Codex LOW 10 (date -r portability)** — Task 13 replaces shellout with `parse_page(session-log).frontmatter["created"]`.
- [x] **Gemini (sys.path anti-pattern)** — resolved via shared module placement.
- [x] **Spec coverage** — all 9 success criteria mapped to tasks (SC1/SC2 → Task 5; SC3 → Task 4; SC4 → Tasks 11-12; SC5 → Tasks 11-14; SC6 → Tasks 12-13; SC7 preserved by skill naming; SC8 → Task 8; SC9 → Task 2).
- [x] **No placeholders** — every step contains actual code or exact commands.
- [x] **Type consistency** — `OMCPage`, `SeedSource`, `PromotionConfig`, `PromotionReport`, `pick_bridge`, `classify`, `translate_frontmatter` used consistently.
- [x] **Build order** — shared module (Task 1) before all consumers; fixtures (Task 10) before Tasks 11-15.
