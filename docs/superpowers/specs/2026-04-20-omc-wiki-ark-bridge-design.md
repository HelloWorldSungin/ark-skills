# OMC `/wiki` ↔ Ark `/wiki-*` Bridge — Design

**Status:** Draft
**Date:** 2026-04-20
**Author:** Sungin + Claude (brainstorming session)
**Depends on:** `docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md` (v1.17.0 context-budget probe)

## Problem

OMC's `/wiki` skill and Ark's `/wiki-*` skill family both implement the Karpathy LLM Wiki model, but target different lifecycles:

- **OMC `/wiki`** — per-working-directory scratchpad at `.omc/wiki/`, gitignored, tool-backed (`wiki_ingest`/`wiki_query`/`wiki_lint`), fast atomic adds, auto-capture stub at `SessionEnd`. Designed for in-session LLM use.
- **Ark `/wiki-*`** — per-project Obsidian vault (git-tracked), multi-tier retrieval (NotebookLM → MemPalace → Obsidian → index.md), strict frontmatter taxonomy, TaskNotes integration. Designed for durable cross-session, cross-human knowledge.

Without a bridge, knowledge written mid-session into OMC `.omc/wiki/` is stranded: gitignored, invisible to NotebookLM, inaccessible to future sessions on other machines. And the reverse gap: fresh sessions can't leverage the vault's rich context without a manual `/wiki-query` per topic.

Additional pain point: Claude Code session handoffs at ~25–30% context usage currently lose in-flight LLM-discovered knowledge that hasn't been written anywhere persistent.

## Goals

1. **Seed OMC from the vault on demand** — when the user asks warmup a question, populate `.omc/wiki/` with cited vault sources so mid-session `wiki_query` has something to retrieve.
2. **Capture handoffs** — write a bridge page to OMC when the v1.17.0 probe triggers compact/clear actions, preserving in-session state for the next session.
3. **Promote to the vault** — at end-of-session, promote durable OMC pages (architecture, decisions, patterns) into the Ark vault with proper Ark frontmatter, then delete the OMC source.
4. **No namespace collision** — keep Ark's `/wiki-*` skill names distinct from OMC's `/wiki`.

## Non-goals

- Real-time bidirectional sync between `.omc/wiki/` and the vault.
- Replacing OMC `/wiki` or Ark `/wiki-*`. Both remain first-class.
- Cross-project sharing of OMC pages (they stay per-worktree).
- Consolidating Ark's `/wiki-*` skills into an umbrella `/wiki` skill (rejected to avoid trigger collision with OMC).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Session Lifecycle                        │
└─────────────────────────────────────────────────────────────┘

  SESSION START
     │
     ├── /ark-context-warmup                           (Step 1)
     │     │
     │     ├─ no prompt → status brief only (read-only)
     │     └─ with prompt → fan out on cache miss
     │                      └─ write cited sources → .omc/wiki/
     │                         tag: source=warmup
     ▼
  IN-SESSION WORK
     │
     ├── LLM uses wiki_add / wiki_ingest                (existing OMC flow)
     │   to capture decisions, patterns, debugging notes
     ▼
  HANDOFF (v1.17.0 probe triggers at nudge=20% / strong=35%)
     │
     ├── User picks compact or clear                   (Step 2)
     │     └─ /wiki-handoff writes bridge page
     │        → .omc/wiki/session-bridge-{timestamp}.md
     │        tag: source=handoff
     │
     └── User picks subagent → NO bridge write (locked decision)
     ▼
  NEXT SESSION WARMUP
     │
     ├── Reads .omc/wiki/session-bridge-*.md <24h old  (Step 3)
     │   surfaces under "Prior Session Handoff" heading
     ▼
  SESSION END
     │
     └── /wiki-update                                   (Step 4)
         └─ Step 3.5: Promote OMC pages to vault
            filter stubs + confidence gate + dedup
            → delete OMC pages after successful write
```

## Component 1 — Warmup Seeds OMC

### Trigger semantics (Option E′)

| Invocation mode | OMC write? | Fanout? |
|---|---|---|
| `/ark-context-warmup` (no prompt, no chain) | **no** | no (status brief only) |
| `/ark-context-warmup` via `/ark-workflow` chain | **yes on cache miss** | yes on cache miss |
| `/ark-context-warmup "<prompt>"` standalone with prompt | **yes on cache miss** | yes on cache miss |
| `/ark-context-warmup --refresh` | **yes, force** | yes, force |

Cache key `chain_id + task_hash` already exists in v1.17.0 infrastructure. Topic shift → different hash → cache miss → fresh OMC write. Identical re-invocation within cache TTL → cache hit → OMC pages untouched (prior write still on disk).

### What gets written

On cache miss with prompt present, after NotebookLM/MemPalace/vault fan-out completes:

1. For each **NotebookLM source citation** returned with confidence=`high`: write an OMC page. File: `.omc/wiki/source-{slug}.md`.
2. For each **vault page** surfaced by T4 index scan with relevance rank in top 3: write an OMC page.
3. Skip pages whose content is <200 chars (unlikely to be useful mid-session).

OMC frontmatter translation:

```yaml
---
title: <from vault title>
tags: [<vault tags>, source-warmup]
created: <now>
updated: <now>
sources: [<vault-file-path>, <chain_id>]
links: []
category: <mapped from vault type — see table below>
confidence: <high|medium from retrieval rank>
schemaVersion: 1
---
```

Vault `type` → OMC `category` mapping:

| Vault `type` | OMC `category` |
|---|---|
| `architecture` | `architecture` |
| `decision-record` | `decision` |
| `pattern` | `pattern` |
| `compiled-insight` | `pattern` |
| `research` | `architecture` (closest fit) |
| `reference` / `guide` | `architecture` |
| session logs | **skip** (too chronological for OMC) |
| epic/story/bug/task | **skip** (project management, not knowledge) |

### Degradation

- If no prompt present → skip OMC writes (Option E′ rule).
- If `HAS_OMC=false` (no `.omc/` dir) → skip OMC writes silently.
- If NotebookLM + MemPalace + Obsidian + index all unavailable → warmup already exits silently per existing contract; no OMC writes.

## Component 2 — Handoff Bridge via v1.17.0 Probe

### Integration point

Hook into the existing `skills/ark-workflow/scripts/context_probe.py` menu-action handler. When the menu surfaces and the user picks an action:

| Menu action | Bridge write? |
|---|---|
| `compact` | **yes** — write before PreCompact hook fires |
| `clear` | **yes** — write before Claude Code `/clear` |
| `subagent` | **no** (locked decision) |

### New skill: `/wiki-handoff`

A new thin skill in `skills/wiki-handoff/SKILL.md`. Invoked by the probe menu action handler in `/ark-workflow`. Goals: stdlib-only, <1s wall time, single file write.

**Inputs** (from env / `.ark-workflow/current-chain.md`):
- `chain_id`, `task_text`, `scenario`, current step index
- Git diff stat since chain entry (what files were touched)

**Output**: writes one page to `.omc/wiki/session-bridge-{YYYY-MM-DD-HHMM}.md`:

```markdown
---
title: "Session Bridge — {task_summary}"
tags: [session-bridge, source-handoff, scenario-{scenario}]
created: <now>
updated: <now>
sources: [<chain_id>, <session_id>]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# Session Bridge — {task_summary}

## Task
{task_text}

## Scenario
{scenario} (step {step_index}/{step_count})

## What was done
- <git diff stat since chain entry, 1 line per file>
- <TODO: populated by LLM right before /wiki-handoff fires>

## Open threads
- <TODO: populated by LLM>

## Next steps
- <TODO: populated by LLM>

## Notes
- <free-form notes from conversation>
```

The TODO sections are populated by the LLM in the same turn that invokes `/wiki-handoff` — the LLM passes them as arguments. `/wiki-handoff` itself does not mine the conversation; it's a thin writer.

### Next-session consumption

Extend `skills/ark-context-warmup/SKILL.md` Step 1 (Task intake):

> **After task intake, check for session bridges.** List `.omc/wiki/session-bridge-*.md` with mtime <24h old. If the most recent bridge's `sources[]` overlaps with the current `chain_id` or its `task_text` shares ≥2 domain tags, read it and surface under a "Prior Session Handoff" heading in the Context Brief.

Degradation: if no bridges exist or all are >24h, skip silently.

## Component 3 — End-of-Session Promotion

### New step in `/wiki-update`: Step 3.5

Inserted between existing Step 3 (Update TaskNote Epic + Stories) and Step 4 (Extract Compiled Insights).

**Step 3.5: Promote OMC Wiki Pages**

1. **Discover.** If `.omc/wiki/index.md` exists, list all pages modified since the current session's start timestamp (from session log's `created:` field).
2. **Filter.** Drop pages matching any of:
   - `tags` contains `session-log` AND `auto-captured` (OMC's SessionEnd stubs — no real content)
   - `tags` contains `source-warmup` (re-derivable from the vault, no promotion value)
   - Filename matches `session-log-{date}-{id}.md` (belt + suspenders for stub detection)
   - `category: environment` (re-derivable from `project-memory.json`)
3. **Confidence gate.**
   - `confidence: high` → **auto-promote**
   - `confidence: medium` → surface in an interactive list; user picks `[y/N/edit]` per page
   - `confidence: low` (if present) → **skip** with log line
4. **Category → placement mapping:**

   | OMC `category` | Ark destination | Ark `type` |
   |---|---|---|
   | `architecture` | `{project_docs_path}/Architecture/` (fallback: `Compiled-Insights/`) | `architecture` |
   | `decision` | `{project_docs_path}/Architecture/` (fallback: `Compiled-Insights/`) | `decision-record` |
   | `pattern` | `{project_docs_path}/Compiled-Insights/` | `pattern` |
   | `debugging` | **fold inline** into current session log's "Issues & Discoveries" section; don't create a new page | — |
   | `session-log` (session-bridge pages only) | already captured by Step 2's session log merge | — |
   | `environment` | **skip** | — |

   "Fallback" path applies when the primary directory doesn't exist in the target vault layout.

5. **Frontmatter translation:**
   - `title` → `title`
   - `tags` → `tags` (normalize against `_meta/taxonomy.md` if present; warn on unknown tags but promote anyway)
   - `sources: [sessionId, ...]` → `source-sessions: ["[[S{NNN}-{slug}]]"]` (session slug from Step 2)
   - `category` → `type` (per table above)
   - Derive `summary:` by truncating first paragraph to ≤200 chars
   - Drop OMC-only fields: `confidence`, `schemaVersion`, `links`, `sources`
   - Preserve `created:` if present; set `last-updated: <today>`

6. **Dedup.** Check Ark `index.md` for existing page on same topic (title slug match OR tag overlap ≥2). If exists → merge body (append new content under `## Continuation — {date}`), bump `last-updated`. If new → create.

7. **Post-promotion disposition: delete.**
   After successful write + Ark-side index regen (Step 5 of `/wiki-update`), delete the OMC source page with `rm .omc/wiki/{slug}.md`. Locked decision: no archive folder.

8. **Report.**
   ```
   OMC Promotion Report
   ====================
   Auto-promoted (high confidence): N pages
   Flagged for review (medium): M pages
   Skipped (filtered): K pages
   Deleted from OMC: N pages
   ```

### Interaction with existing Step 4

Step 4 (Extract Compiled Insights) runs **after** Step 3.5. Its existing scan of `git diff` still applies — now augmented with promoted OMC pages that already carry `source-sessions:` references. If Step 4 finds the same insight the OMC page captured, it dedupes via the existing "search index.md + summaries" check in current Step 4.

## Data flow summary

```
.omc/wiki/               (OMC — per-worktree, gitignored)
  ├─ source-*.md         ← warmup populator (Component 1)
  ├─ {decisions,arch,patterns}.md
  │                      ← LLM wiki_add/wiki_ingest during session
  ├─ session-bridge-*.md ← handoff writer (Component 2)
  └─ index.md, log.md    ← OMC internal bookkeeping

     │
     │  /wiki-update Step 3.5 (Component 3)
     │  filter → gate → translate → dedup → write → DELETE
     ▼

vault/                   (Ark — per-project, git-tracked)
  ├─ Architecture/       ← promoted architecture + decisions
  ├─ Compiled-Insights/  ← promoted patterns + merged content
  ├─ Session-Logs/       ← session log + debugging fold-ins
  └─ index.md            ← regenerated by /wiki-update Step 5
```

## Edge cases

- **Worktree with no OMC init.** Component 1 skip (no writes). Component 2 skip (no probe, no handoff). Component 3 skip (no `.omc/wiki/` to discover). All silent no-ops.
- **OMC initialized mid-session.** Component 1 and 2 work going forward. Component 3 discovers all pages created since the OMC init timestamp.
- **Cross-worktree session continuation.** OMC is per-worktree; bridge pages do NOT transfer. This is by design — worktrees are branch-scoped, and bridge continuity within a worktree is the primary use case. Cross-worktree continuity goes through the vault via `/wiki-update`.
- **Shared/monorepo vault.** `{project_docs_path}` resolution from CLAUDE.md already handles this (existing Ark convention). Promoted pages land in the correct project subdirectory.
- **Unknown tags.** Step 3.5 point 5 warns on unknown tags but still promotes. Alternative considered: reject. Rejected because Ark's `taxonomy.md` is organic and rigid rejection would block legitimate new tags. The warning serves as a surface for taxonomy evolution.
- **Merge conflicts on bridge pages.** Bridges live in gitignored `.omc/wiki/`, so no git conflicts. Two parallel sessions writing bridges in the same worktree is unusual (sessions are typically serial within a CWD) but the timestamped filenames prevent overwrites.
- **Medium-confidence review happens mid-`/wiki-update`.** The interactive `[y/N/edit]` prompt blocks on user input. If `/wiki-update` is running in a non-interactive context (CI, automation), default to `N` (skip) for all medium-confidence pages. They stay in OMC for next manual run.

## Testing strategy

- **Unit**: frontmatter translation function (OMC → Ark) with fixture pairs.
- **Unit**: category → placement mapping table.
- **Unit**: stub filter regex + tag-based filter.
- **Integration**: fixture worktree with `.omc/wiki/` containing mixed stub, source-warmup, high-conf architecture, medium-conf pattern, debugging page. Run `/wiki-update` dry-run; assert promotion report matches expected.
- **Integration**: `/wiki-handoff` writes bridge; subsequent warmup reads it into Context Brief.
- **Integration**: warmup with prompt populates OMC on cache miss; re-run within cache TTL is no-op.
- **Smoke**: v1.17.0 probe at `strong` level, user picks `compact`, confirm bridge page created before compaction.

## Open questions (to resolve during implementation planning)

1. Should `/wiki-handoff` be invoked by the LLM directly (via Skill tool), or triggered from inside `context_probe.py`'s menu-action handler? Leaning: LLM-invoked, because the LLM has to write the "Open threads / Next steps" fields anyway.
2. Where exactly in `context_probe.py`'s flow does the bridge write hook in? Before `record-proceed`? After? (Needs inspection of `scripts/context_probe.py` beyond line 80.)
3. For medium-confidence pages in non-interactive `/wiki-update` runs, should the default be `skip` or `flag-file` (write a list to `.omc/wiki/.pending-review.md`)?
4. Do we want a `/wiki-update --dry-run` for Step 3.5 specifically, so users can preview the promotion plan before committing?

## Migration

No migration required. Feature is additive:
- Existing `/ark-context-warmup` runs without prompts continue working unchanged.
- Existing `/wiki-update` runs on worktrees without `.omc/wiki/` continue working unchanged (Step 3.5 is a silent no-op).
- No CLAUDE.md schema changes.
- No breaking changes to existing Ark skill triggers.

## Success criteria

1. Fresh session in worktree with prior handoff sees "Prior Session Handoff" in Context Brief automatically.
2. Running `/ark-context-warmup "how does X work"` populates 3–5 cited vault sources into `.omc/wiki/` on cache miss; second invocation is no-op within cache TTL.
3. Running `/wiki-update` after a session promotes high-confidence OMC pages into the vault, flags medium for review, deletes promoted sources, and leaves stubs + source-warmup pages untouched.
4. No trigger collision between Ark `/wiki-*` and OMC `/wiki` (verified by listing both in a session and triggering each).
5. v1.17.0 probe menu at `strong` level invokes `/wiki-handoff` before `compact`/`clear` executes.
