# OMC `/wiki` ↔ Ark `/wiki-*` Bridge — Design

**Status:** Draft (revised post-/ccg review)
**Date:** 2026-04-20
**Author:** Sungin + Claude (brainstorming session); revised after Codex + Gemini review
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
3. **Promote to the vault** — at end-of-session, promote durable OMC pages (architecture, decisions, patterns) into the Ark vault with proper Ark frontmatter, then delete the OMC source under transactional rules.
4. **No namespace collision** — keep Ark's `/wiki-*` skill names distinct from OMC's `/wiki`.
5. **Preserve in-session edits** — seeded pages that are edited mid-session must not be silently lost.

## Non-goals

- Real-time bidirectional sync between `.omc/wiki/` and the vault.
- Replacing OMC `/wiki` or Ark `/wiki-*`. Both remain first-class.
- Cross-project sharing of OMC pages (they stay per-worktree).
- Consolidating Ark's `/wiki-*` skills into an umbrella `/wiki` skill (rejected to avoid trigger collision with OMC).
- Modifying OMC's `wiki_query` to transparently search the Ark vault (the "Virtual Overlay" alternative is a separate future effort — see Appendix A).

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
     │                      ├─ compute per-source content hashes
     │                      ├─ write new source pages with seed_body_hash
     │                      ├─ refresh changed sources
     │                      └─ delete stale sources for this chain
     ▼
  IN-SESSION WORK
     │
     ├── LLM uses wiki_add / wiki_ingest                (existing OMC flow)
     │   to capture decisions, patterns, debugging notes
     │
     ├── LLM may edit source-warmup pages in place
     │   (body_hash will diverge from seed_body_hash)
     ▼
  HANDOFF (v1.17.0 probe triggers at nudge=20% / strong=35%)
     │
     ├── User picks (a) compact OR (b) clear            (Step 2)
     │     └─ ark-workflow SKILL.md action branch runs
     │        /wiki-handoff BEFORE executing compact/clear,
     │        and BEFORE record-reset.
     │     └─ Bridge page: .omc/wiki/session-bridge-{date}-{time}-{sid8}.md
     │
     └── User picks (c) subagent → NO bridge write (locked decision)
     ▼
  NEXT SESSION WARMUP
     │
     ├── Reads session-bridge-*.md by affinity rules    (Step 3)
     │   - chain_id match: window = 7 days
     │   - chain_id mismatch: only most-recent bridge AND <48h
     │   Surfaces under "Prior Session Handoff" in Context Brief
     ▼
  SESSION END
     │
     └── /wiki-update                                   (Step 4)
         └─ Step 3.5: Promote OMC pages to vault
            ├─ filter stubs
            ├─ preserve edited source-warmup (body_hash changed)
            ├─ high-confidence → direct vault promote
            ├─ medium-confidence → vault/Staging/ + TaskNote
            ├─ debugging → inline in session log; if tagged
            │              pattern/insight, ALSO create
            │              cross-linked Troubleshooting page
            ├─ round-trip via ark-original-type + ark-source-path
            └─ transactional delete (only after vault write + index OK)
```

## Component 1 — Warmup Seeds OMC

### Trigger semantics (Option E′)

| Invocation mode | OMC write? | Fanout? |
|---|---|---|
| `/ark-context-warmup` (no prompt, no chain) | **no** | no (status brief only) |
| `/ark-context-warmup` via `/ark-workflow` chain | **yes on cache miss** | yes on cache miss |
| `/ark-context-warmup "<prompt>"` standalone with prompt | **yes on cache miss** | yes on cache miss |
| `/ark-context-warmup --refresh` | **yes, force** | yes, force |

Cache key for the Context Brief remains `chain_id + task_hash` (unchanged). Per-source OMC writes use a **separate dedup layer** — see below.

### What gets written

On cache miss with prompt present, after NotebookLM/MemPalace/vault fan-out completes:

1. For each **NotebookLM source citation** returned with relevance in top 3: compute per-source key `H = sha256(vault_source_path + source_content)`. Write/refresh an OMC page with filename `.omc/wiki/source-{H[0:12]}.md`.
2. For each **vault page** surfaced by T4 index scan in top 3: same per-source key rule.
3. Skip sources whose content is <200 chars (unlikely to be useful mid-session).
4. **Stale cleanup.** After writing/refreshing, list all `source-warmup` pages where frontmatter `chain_id` matches current chain. Any page whose content-hash key `H` is NOT in the current fanout's key set is stale → delete.

Rationale (Codex HIGH 2 fix): `chain_id + task_hash` only dedups the Context Brief. Per-source pages need their own key tied to the source content itself, so topic drift *within* a chain refreshes OMC correctly, and name collisions across unrelated sources are impossible.

### OMC frontmatter (seeded pages)

```yaml
---
title: <from vault title>
tags: [<vault tags>, source-warmup]
created: <now>
updated: <now>
sources: [<vault-source-path>, <chain_id>]
links: []
category: <mapped from vault type — see table below>
confidence: <high|medium from retrieval rank>
schemaVersion: 1
# Provenance for lossless promotion and edit detection (Codex HIGH 3, MEDIUM 4)
ark-original-type: <original vault type — research|reference|guide|compiled-insight|etc>
ark-source-path: <absolute path inside vault, e.g. Architecture/Auth.md>
seed_body_hash: <sha256 of body content at seed time>
seed_chain_id: <chain_id that produced this seed>
---
```

The `seed_body_hash` is computed over the markdown body (frontmatter excluded) at write time. Promotion re-computes it and compares — see Component 3.

### Vault `type` → OMC `category` mapping (seed direction)

| Vault `type` | OMC `category` | Notes |
|---|---|---|
| `architecture` | `architecture` | lossless |
| `decision-record` | `decision` | lossless |
| `pattern` | `pattern` | lossless |
| `compiled-insight` | `pattern` | preserve original via `ark-original-type` |
| `research` | `architecture` | preserve original via `ark-original-type` |
| `reference` / `guide` | `architecture` | preserve original via `ark-original-type` |
| session logs | **skip** | too chronological for OMC |
| epic/story/bug/task | **skip** | project management, not knowledge |

### Degradation

- No prompt present → skip OMC writes (Option E′ rule).
- `HAS_OMC=false` (no `.omc/` dir) → skip OMC writes silently.
- All retrieval backends unavailable → warmup already exits silently per existing contract; no OMC writes.
- Failed write on one source → log, continue with remaining sources (don't abort whole fanout).

## Component 2 — Handoff Bridge via v1.17.0 Probe

### Integration point (Codex HIGH 1 fix)

`context_probe.py` is a **state machine only** — it renders menus and mutates `proceed_past_level` suppression state. The action handling lives in **`skills/ark-workflow/SKILL.md` Step 6.5** after `$MENU` is displayed and the user selects an option.

`/wiki-handoff` fires inside that SKILL.md action branch:

```
After user selects (a) compact or (b) clear:
  1. Invoke /wiki-handoff (LLM populates TODO fields inline)
  2. Verify bridge page written (filesystem check)
  3. Invoke /compact or /clear as the user requested
  4. Invoke context_probe.py --record-reset
```

Order matters:
- Bridge write **before** compact/clear (otherwise in-session context is gone).
- Bridge write **before** `record-reset` (so we don't reset state if the bridge write fails — allows retry).
- Subagent branch (option c): no bridge write (locked decision).

### New skill: `/wiki-handoff`

A new skill in `skills/wiki-handoff/SKILL.md`. Invoked by the LLM directly (via Skill tool) from the `/ark-workflow` Step 6.5 action branch. Stdlib-only; single file write; <1s wall time.

**Inputs** (from env / chain file, plus LLM-provided fields):
- `chain_id`, `task_text`, `scenario`, current step index (from `.ark-workflow/current-chain.md`)
- Git diff stat since chain entry (what files were touched)
- `open_threads`, `next_steps`, `notes` — **LLM-supplied as arguments**

**Schema enforcement (Gemini 6 fix).** The skill rejects the call if `open_threads` or `next_steps` match any of:
- Empty string or whitespace-only
- Generic placeholders: `"continue task"`, `"TBD"`, `"TODO"`, `"keep going"`, `"none"`
- Content length <20 chars total

On rejection, print: `"wiki-handoff: open_threads must be specific (file paths, decision points, unresolved questions). Re-invoke with detail."` and exit non-zero.

**Filename** (Codex LOW/MEDIUM 7 fix): `.omc/wiki/session-bridge-{YYYY-MM-DD}-{HHMMSS}-{session_id[-8:]}.md`. Atomic create via `O_CREAT | O_EXCL`. On collision (unlikely but possible): append `-2`, `-3`, etc.

**Bridge page content:**

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
chain_id: <chain_id>
---

# Session Bridge — {task_summary}

## Task
{task_text}

## Scenario
{scenario} (step {step_index}/{step_count})

## What was done
- <git diff stat since chain entry, 1 line per file>
- <LLM-supplied "done" summary>

## Open threads
- <LLM-supplied, validated non-generic>

## Next steps
- <LLM-supplied, validated non-generic>

## Notes
- <LLM-supplied free-form notes>
```

### Next-session consumption (Gemini 3 fix)

Extend `skills/ark-context-warmup/SKILL.md` Step 1 (Task intake):

> **After task intake, check for session bridges.** List `.omc/wiki/session-bridge-*.md`. For each, read frontmatter `chain_id`.
>
> - **chain_id match** with current chain: show the most recent bridge if its mtime is ≤ **7 days** old.
> - **chain_id mismatch**: show the **single most-recent** bridge only if its mtime is ≤ **48 hours** old.
>
> Surface the chosen bridge under "Prior Session Handoff" heading in the Context Brief. If no bridge qualifies, skip silently.

Rationale: 24h was too narrow (fails over weekends / context switching). Chain-ID affinity preserves relevant continuity up to a week; non-matching bridges get a short grace period only.

## Component 3 — End-of-Session Promotion

### New step in `/wiki-update`: Step 3.5

Inserted between existing Step 3 (Update TaskNote Epic + Stories) and Step 4 (Extract Compiled Insights).

**Step 3.5: Promote OMC Wiki Pages**

1. **Discover.** If `.omc/wiki/index.md` (or just `.omc/wiki/`) exists, list all pages modified since the current session's start timestamp (from session log's `created:` field). If no index.md but pages exist, process the pages directly and log: `"OMC index.md missing — processing pages directly"`.

2. **Filter stubs.** Drop pages matching any of:
   - `tags` contains both `session-log` AND `auto-captured` (OMC's SessionEnd stubs)
   - Filename matches `session-log-{date}-{id}.md`
   - `category: environment` (re-derivable from `project-memory.json`)

3. **Edit-detection gate for `source-warmup` pages (Codex HIGH 3 fix).**
   For each page tagged `source-warmup`:
   - Compute current `body_hash = sha256(body)` (excluding frontmatter).
   - If `body_hash == seed_body_hash` → skip (untouched, re-derivable from vault).
   - If `body_hash != seed_body_hash` → **treat as session-authored**; route through confidence gate (step 4). Log: `"Modified seed page {slug}: promoting as session-authored"`.

4. **Confidence gate.**
   - `confidence: high` → **auto-promote** (step 5).
   - `confidence: medium` (Q4 A — async staging, not interactive):
     - Write to `{project_docs_path}/Staging/` instead of final destination.
     - Create a TaskNote bug at `{tasknotes_path}/Tasks/Bug/` titled `"Review staged wiki promotion: {title}"` with `priority: low` and body linking both the staging page and the OMC source.
     - Log `"Staged: {slug} → {project_docs_path}/Staging/"`.
   - `confidence: low` → skip with log line.

5. **Category → placement mapping:**

   | OMC `category` | Ark destination | Ark `type` (from `ark-original-type` if present) |
   |---|---|---|
   | `architecture` | `{project_docs_path}/Architecture/` (fallback: `Compiled-Insights/`) | `ark-original-type` ∈ {architecture, research, reference, guide} |
   | `decision` | `{project_docs_path}/Architecture/` (fallback: `Compiled-Insights/`) | `decision-record` |
   | `pattern` | `{project_docs_path}/Compiled-Insights/` | `ark-original-type` if present else `pattern` |
   | `debugging` | **dual write** (Q5 C, see 5a below) | — |
   | `session-log` (session-bridge pages only) | merged into Step 2 session log body | — |
   | `environment` | **skip** | — |

   "Fallback" applies when the primary directory doesn't exist.

5a. **Debugging dual-write (Q5 C):**
   - **Always**: append debugging page content to the current session log's "Issues & Discoveries" section (existing behavior).
   - **Additionally**, if the debugging page's `tags` include `pattern` OR `insight`: create a cross-linked page at `{project_docs_path}/Troubleshooting/{slug}.md` with `type: compiled-insight`, tags preserved, backlink to the session log, and link back from the session log's inline entry. Purpose: valuable debugging wisdom is discoverable outside chronological logs.

6. **Frontmatter translation (Codex MEDIUM 4 — lossless round-trip):**
   - `title` → `title`
   - `tags` → `tags` (normalize against `_meta/taxonomy.md` if present; warn on unknown tags but promote anyway)
   - `sources: [sessionId, ...]` → `source-sessions: ["[[S{NNN}-{slug}]]"]` (session slug from Step 2)
   - `category` → `type` via `ark-original-type` if present (lossless round-trip); otherwise via the table in step 5.
   - If `ark-source-path` is set and the target path already exists in vault → merge into existing page (lossless path preservation).
   - Derive `summary:` by truncating first paragraph to ≤200 chars.
   - Drop OMC-only fields: `confidence`, `schemaVersion`, `links`, `sources`, `seed_body_hash`, `seed_chain_id`, `ark-original-type`, `ark-source-path` (provenance consumed, no longer needed).
   - Preserve `created:` if present; set `last-updated: <today>`.

7. **Dedup.** Check Ark `index.md` for existing page on same topic (use `ark-source-path` if present — authoritative; else title slug match OR tag overlap ≥2). If exists → merge body (append new content under `## Continuation — {date}`), bump `last-updated`. If new → create.

8. **Transactional delete (Codex MEDIUM 5 fix).**
   Only delete OMC source pages after **all** of:
   - Vault write returned success
   - `/wiki-update` Step 5 (index regen) returned exit code 0
   - Destination page exists on disk with non-zero size

   Use `os.unlink` with pre-check (not `rm -f`); on failure, log `"OMC page {slug} preserved — vault write/index regen failed"` and leave the page in place for the next `/wiki-update` run. Never silently swallow unlink errors.

9. **Report.**
   ```
   OMC Promotion Report
   ====================
   Auto-promoted (high confidence): N pages
   Staged for review (medium): M pages → Staging/ + N TaskNotes created
   Skipped (filtered/untouched-seed): K pages
   Session-authored seed edits promoted: J pages
   Troubleshooting cross-links created: T pages
   Deleted from OMC: N pages (transactional, only on success)
   Errors: E (pages preserved for next run)
   ```

### Interaction with existing Step 4

Step 4 (Extract Compiled Insights) runs **after** Step 3.5. Its existing scan of `git diff` still applies — now augmented with promoted OMC pages that carry `source-sessions:` references. Dedup relies on the existing "search index.md + summaries" check.

## Data flow summary

```
.omc/wiki/               (OMC — per-worktree, gitignored)
  ├─ source-{hash12}.md  ← warmup populator (Component 1)
  │                        keyed by content hash, auto-refresh
  ├─ {decisions,arch,patterns}.md
  │                      ← LLM wiki_add/wiki_ingest during session
  ├─ session-bridge-{date}-{time}-{sid8}.md
  │                      ← handoff writer (Component 2)
  └─ index.md, log.md    ← OMC internal bookkeeping

     │
     │  /wiki-update Step 3.5 (Component 3)
     │  filter → edit-detect → confidence-gate → translate → dedup
     │   → write → verify → transactional delete
     ▼

vault/                   (Ark — per-project, git-tracked)
  ├─ Architecture/       ← promoted architecture + decisions
  ├─ Compiled-Insights/  ← promoted patterns + merged content
  ├─ Session-Logs/       ← session log + debugging fold-ins
  ├─ Troubleshooting/    ← pattern/insight-tagged debugging (Q5 C)
  ├─ Staging/            ← medium-confidence holding area (Q4 A)
  └─ index.md            ← regenerated by /wiki-update Step 5
```

## Edge cases

- **Worktree with no OMC init.** Component 1/2/3 all silent no-ops. No writes, no errors.
- **OMC initialized mid-session.** Component 1 and 2 work going forward. Component 3 discovers all pages created since the OMC init timestamp.
- **Cross-worktree session continuation (Codex MEDIUM — risk acknowledged).** OMC is per-worktree; bridge pages do NOT transfer. Users switching worktrees between handoff and resume lose continuity. **Mitigation**: `/wiki-update` at end-of-session promotes the most recent bridge page to the vault session log as a "Session Bridge" subsection. That way cross-worktree continuity flows through the vault. Bridges that never survive to `/wiki-update` are worktree-local by design.
- **Shared/monorepo vault.** `{project_docs_path}` resolution from CLAUDE.md already handles this (existing Ark convention). Promoted pages land in the correct project subdirectory.
- **Unknown tags.** Warn but promote. Ark's taxonomy is organic; rigid rejection would block legitimate new tags.
- **Merge conflicts on bridge pages.** Bridges live in gitignored `.omc/wiki/` — no git conflicts. Timestamped filenames with second resolution + session-id suffix prevent within-worktree overwrites.
- **Source-slug collision.** Eliminated by content-hash-keyed filenames (Component 1).
- **Source content changed under same title.** New content-hash → new filename → both pages coexist until stale cleanup deletes the older one on next fanout.
- **Cache hit with missing OMC seed.** Cache hit doesn't write. If OMC was cleared between runs, seeds are gone but brief is still served. Mitigation: on cache hit, verify expected seed files exist; if missing, invalidate cache entry and re-fan-out.
- **Non-interactive `/wiki-update` (CI, automation).** Q4 A async staging is fully non-interactive — no user prompts. Staging + TaskNote creation works in any context.
- **Failed vault write during promotion.** Transactional delete gate keeps OMC source in place. Next `/wiki-update` retries.
- **Failed index regen.** Same as above — deletion blocked, OMC preserved.
- **Malformed YAML frontmatter on OMC page.** Filter step logs and skips; page stays in OMC with a diagnostic line in the promotion report.
- **Concurrent warmups in the same worktree.** Unusual (warmup is step 0 of a chain, chains are serial) but possible. File-level atomic writes handle it; stale-cleanup may delete a sibling warmup's source briefly. Acceptable — next fanout restores.

## Testing strategy

- **Unit**: frontmatter translation function (OMC → Ark, with and without `ark-original-type`) with fixture pairs.
- **Unit**: category → placement mapping table (all branches).
- **Unit**: stub filter regex + tag-based filter.
- **Unit**: `seed_body_hash` edit detection (identical, whitespace-only change, substantive edit).
- **Unit**: content-hash-keyed filename generation + collision handling.
- **Unit**: `/wiki-handoff` schema enforcement (rejects empty/generic/short inputs, accepts specific ones).
- **Unit**: bridge window affinity logic (match 7d, mismatch 48h, various mtime inputs).
- **Integration**: fixture worktree with `.omc/wiki/` containing mixed stub, source-warmup (untouched), source-warmup (edited), high-conf architecture, medium-conf pattern, debugging page (pattern-tagged) — run `/wiki-update` dry-run; assert promotion report matches expected.
- **Integration**: `/wiki-handoff` writes bridge; subsequent warmup reads it into Context Brief (chain-match + chain-mismatch windows).
- **Integration**: warmup with prompt populates OMC on cache miss; re-run within cache TTL is no-op; source content change triggers stale cleanup.
- **Integration**: concurrent warmups in same worktree — no torn files.
- **Integration**: bridge filename collision within same second — `O_EXCL` prevents overwrite.
- **Integration**: failed vault write during Step 3.5 — OMC source NOT deleted.
- **Integration**: failed index regen — OMC source NOT deleted.
- **Integration**: missing `.omc/wiki/index.md` with pages present — processes pages directly, logs warning.
- **Integration**: symlinked / shared vault writes — promotion lands in correct `{project_docs_path}`.
- **Integration**: non-interactive `/wiki-update` — medium-confidence pages go to Staging + TaskNotes created, no prompts.
- **Integration**: malformed YAML frontmatter on OMC page — skipped with diagnostic.
- **Integration**: cross-worktree continuation — bridge promoted to vault session log at end-of-session; next session in different worktree finds it via T1/T4.
- **Smoke**: v1.17.0 probe at `strong` level, user picks `compact`, confirm bridge page created before compaction; `record-reset` fires after bridge write confirmed.

## Open questions (to resolve during implementation planning)

1. Where exactly does `/wiki-handoff` hook into `skills/ark-workflow/SKILL.md` Step 6.5? (Needs inspection of the file's current action-branch shape.) Confirmed location: after user picks (a)/(b), before `/compact`/`/clear` dispatch, before `record-reset`.
2. Should staging page naming use the same slug as the eventual final page, or a `staging-` prefix? Leaning: same slug — user moves it, renaming is a hassle.
3. TaskNote priority for staged-review: `low` (current proposal) or `medium`?
4. Should we add a `/wiki-update --dry-run` for Step 3.5 specifically, so users preview promotion plans before committing?

## Migration

Feature is additive:
- Existing `/ark-context-warmup` runs without prompts continue working unchanged.
- Existing `/wiki-update` runs on worktrees without `.omc/wiki/` continue working unchanged (Step 3.5 is silent no-op).
- No CLAUDE.md schema changes.
- No breaking changes to existing Ark skill triggers.
- New directories (`Staging/`, `Troubleshooting/`) are created lazily — no pre-existing-vault migration required.

## Success criteria

1. Fresh session in worktree with prior handoff (same chain_id, <7d old) sees "Prior Session Handoff" in Context Brief automatically.
2. Fresh session with no matching chain but a recent bridge (<48h) sees the most recent bridge once, in the Context Brief.
3. Running `/ark-context-warmup "how does X work"` populates 3–5 cited vault sources into `.omc/wiki/` on cache miss; second invocation is no-op within cache TTL; topic shift refreshes per-source pages without stale residue.
4. Editing a source-warmup page mid-session, then running `/wiki-update`, results in the edited content being promoted (not silently filtered).
5. Running `/wiki-update` after a session auto-promotes high-confidence OMC pages into the vault, stages medium-confidence pages into `Staging/` with review TaskNotes, leaves stubs + untouched seed pages alone, creates Troubleshooting cross-links for pattern-tagged debugging, and deletes successfully promoted sources.
6. Failed vault write or failed index regen leaves all OMC pages intact for a retry.
7. No trigger collision between Ark `/wiki-*` and OMC `/wiki`.
8. v1.17.0 probe menu at `strong` level: user picks compact or clear → `/wiki-handoff` fires before the action; user picks subagent → no bridge write; `record-reset` fires only after bridge confirmed.
9. Schema enforcement: `/wiki-handoff` rejects generic "continue task" / empty "Open threads" and prompts for specifics.

## Appendix A — Rejected alternatives (and why)

- **Always-seed warmup (Gemini 1).** Would populate OMC even when user just wants a status check. Rejected: pays a fanout cost on every orientation-style warmup; user can always re-invoke with a prompt if they decide to work. Trade-off accepted.
- **`/ark-wiki` umbrella skill (Gemini 4).** Collides at the trigger level with OMC `/wiki` ("wiki lint" would match both). Rejected to preserve namespace separation.
- **Virtual Overlay — `wiki_query` transparently searches vault (Gemini 7 steel-man).** Attractive (zero duplication) but requires modifying OMC's TypeScript tools. Out of scope for this spec. Logged as potential future direction; does not block this design.
- **Interactive `[y/N/edit]` medium-confidence gate (original proposal).** Replaced by Q4 A async staging + TaskNote. Interactive gates break non-interactive runs and create session-end friction.
- **Debugging folder only (Gemini 5).** Would lose session-log chronological context. Q5 C dual-write keeps both discoverability *and* timeline.
