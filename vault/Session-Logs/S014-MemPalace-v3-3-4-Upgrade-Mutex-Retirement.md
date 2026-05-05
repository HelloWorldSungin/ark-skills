---
title: "Session 14: MemPalace v3.3.4 upgrade + palace-global mutex retirement (v1.23.1)"
type: session-log
tags:
  - session-log
  - S014
  - mempalace
  - claude-history-ingest
  - bugfix
  - infrastructure
  - upstream-watch
summary: "Shipped v1.23.1 — upgraded mempalace 3.3.2 → 3.3.4, retired palace-global mine mutex (Arkskill-010), cleared 5 circuit breakers, corrected CLAUDE.md T2 crash path docs."
session: "S014"
status: complete
date: 2026-05-05
prev: "[[S013-Gstack-v1-5-1-0-Integration-Wave1]]"
epic: "[[Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges]]"
source-tasks:
  - "[[Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges]]"
created: 2026-05-05
last-updated: 2026-05-05
---

# Session 14: MemPalace v3.3.4 upgrade + palace-global mutex retirement (v1.23.1)

## Objective

Investigate the recurring MemPalace crash, check whether upstream fix #976 had shipped, and execute the Arkskill-010 acceptance criteria: upgrade, retire the palace-global mine mutex, clear tripped circuit breakers, and correct stale documentation.

## Context

Arkskill-010 was created 2026-04-23 after root-causing the 38k-drawer palace corruption to concurrent cross-wing HNSW segment writes. v1.20.3 (commit `7e93411`) added a palace-global mutex (`~/.mempalace/palace/.ark-global-mine-mutex`) as a workaround. Upstream PR #976 (HNSW thread-safety) was merged 2026-04-25 to MemPalace `develop` branch but was NOT in a tagged release — v3.3.3 was cut 2026-04-24, one day before. We were monitoring for a release.

## Work Done

### Upstream Investigation

- Confirmed MemPalace v3.3.4 released 2026-05-01, shipping upstream #976 (HNSW `mine_palace_lock()` thread-safety fix).
- v3.3.5 pending: ships #1322 (`quarantine_stale_hnsw()` auto-repair on MCP startup + #1132 `_query` search segfault fix).

### Root Cause Analysis

Live crash trace from `~/.mempalace/hook_state/mine.log`:
```
File ".../chromadb/api/rust.py", line 541, in _upsert
    return self.bindings.upsert(...)
```
The crash is in **`_upsert` (mine path)**, not `_query` (search path) as previously documented in CLAUDE.md. Both originate from the same HNSW segment corruption from prior concurrent-writer races — different entry points to the same corrupted on-disk state.

Tripped wings (circuit breaker at 3+ failures):
- `-Users-sunginkim--superset-projects-ArkM1` (3)
- `-Users-sunginkim--superset-projects-DTD-debug` (3)
- `-Users-sunginkim--superset-projects-ark-skills` (3)
- `-Users-sunginkim--superset-worktrees-ark-skills-context-management` (3)
- `-Users-sunginkim-GIT-Crytography` (4)

### Fix Executed

1. **Upgraded mempalace**: `pipx upgrade mempalace` → 3.3.2 → 3.3.4.
2. **Cleared 5 circuit breakers**: reset fail_count files to 0 for all tripped wings.
3. **Retired palace-global mutex** from `skills/claude-history-ingest/hooks/ark-history-hook.sh`: removed 19-line `GLOBAL_LOCK` block (lines 118-136) + `rm -rf "$GLOBAL_LOCK"` from nohup background script.
4. **Corrected CLAUDE.md T2 note**: documented `_upsert` (mine) crash fixed in v3.3.4 alongside still-pending `_query` (search) crash (#1132, fix in v3.3.5). Added `requires v3.3.4+` to mine requirement.
5. **Updated Arkskill-010**: status `backlog` → `in-progress`; checked off #976-shipped and mutex-retirement acceptance criteria; documented hook strategy decision (keep custom hook — full transcript JSONL coverage; plugin's native auto-ingest captures only `mempalace_add_drawer` calls + PreCompact extraction).

### Shipped

Commit `72d64de` — v1.23.1 on master.

## Decisions Made

- **Keep custom Stop hook** (don't replace with plugin's native auto-ingest). Rationale: we mine full transcript JSONL into `claude-history-{project}` wing; the plugin's native auto-ingest only captures explicit `mempalace_add_drawer` calls and PreCompact extraction. Dropping the custom hook loses full transcript coverage. Decision documented in Arkskill-010.
- **Arkskill-010 status left as `in-progress`** (not `done`): smoke-test acceptance criterion (concurrent sessions hitting Stop simultaneously) has not been executed. Will mark done after confirming mines succeed across multiple wings post-upgrade.

## Open Questions

- **v3.3.5 watch**: #1132 (`_query` search segfault) and #1062 (`quarantine_stale_hnsw()` on MCP startup, would retire `/ark-health` Check 14d) are still pending. Watch for v3.3.5 release.
- **`mempalace-mcp` symlink warning**: `pipx upgrade` emitted a warning that `/Users/sunginkim/.local/bin/mempalace-mcp` points to itself (symlink loop), not the venv binary. Non-blocking for mine operations but should be investigated.

## Next Steps

1. Verify mines succeed post-upgrade: open sessions across a few projects, confirm no new fail_count increments after next Stop hook fires.
2. Once confirmed stable, update Arkskill-010 smoke-test criterion and mark task `done`.
3. Watch for MemPalace v3.3.5 (retire `/ark-health` Check 14d when #1062 ships).
4. Investigate `mempalace-mcp` symlink loop warning from pipx upgrade.
