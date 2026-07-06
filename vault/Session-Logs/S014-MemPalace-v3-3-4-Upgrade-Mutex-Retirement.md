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
description: "Shipped v1.23.1 — upgraded mempalace 3.3.2 → 3.3.4, retired palace-global mine mutex (Arkskill-010), repaired 294GB HNSW bloat, smoke-tested #976, synced live hook. Arkskill-010 closed."
session: "S014"
status: complete
date: 2026-05-05
prev: "[[S013-Gstack-v1-5-1-0-Integration-Wave1]]"
epic: "[[Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges]]"
source-tasks:
  - "[[Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges]]"
created: 2026-05-05
last-updated: 2026-05-05
timestamp: 2026-05-05T00:00:00Z
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

---

## Continuation — 2026-05-05 — Palace HNSW repair, smoke test, live hook sync

### Objective

Execute the open Next Steps from the morning session: confirm mines actually succeed post-upgrade, run the missing concurrent-mine smoke test, close Arkskill-010, and sweep all projects on the macbook for any stale fix-application surfaces.

### Work Done

#### Discovered: v3.3.4 alone did not stop crashes — HNSW segment was still on-disk corrupt

Verifying mines post-upgrade revealed `_upsert` was still segfaulting. Investigation traced this to **on-disk HNSW corruption left over from pre-v3.3.4 races**: segment `347d1275-b2dc-4332-868a-09596239e39f/link_lists.bin` had bloated to **294GB** (~14,000× normal — should be ~20MB for 21,392 vectors). The upstream #976 fix prevents *new* corruption but does not repair existing on-disk state. New compiled insight: [MemPalace-HNSW-Bloat-Repair](../Compiled-Insights/MemPalace-HNSW-Bloat-Repair.md).

#### `mempalace repair` self-defeating without manual segment move

`mempalace repair --mode legacy --backup --yes` exited with code 0 and produced zero output — *appearing* to succeed silently. Real story: chromadb segfaults on `col.count()` (line 689 of `cli.py:cmd_repair`) when loading the bloated segment. Exit was actually 139, but the `tee` pipeline used to capture output masked it as 0. **The repair tool needs chromadb to be openable, and chromadb cannot open the bloated segment.**

Fix sequence:
1. `mv ~/.mempalace/palace/347d1275-b2dc-4332-868a-09596239e39f ~/.mempalace/palace/347d1275-b2dc-4332-868a-09596239e39f.bak` (instant same-FS rename — directory contained the 294GB `link_lists.bin`)
2. ChromaDB then opened the collection with a fresh empty HNSW segment
3. `col.get()` extracted all 21,392 drawers from the metadata segment in `chroma.sqlite3` (the SQLite-segment ground truth was untouched)
4. `repair --mode legacy --backup --yes` rebuilt the HNSW from the metadata, re-filing all 21,392 drawers in ~2 minutes
5. Disk filled to 100% mid-repair from extraction working set; user manually `rm -rf`'d the `.bak` to reclaim the 294GB before retry succeeded

Final state: `du -sh ~/.mempalace/palace/*` — 200K + 172K + 200K HNSW segments, 240MB chroma.sqlite3 (up from 144MB after the rebuild). Backup at `~/.mempalace/palace.backup` (137MB), since deleted by user.

#### Verified mines work end-to-end

Manual `mempalace mine ~/.claude/projects/-Users-sunginkim--superset-projects-ark-skills --mode convos --wing=...` filed 7,138 new drawers across 116 conversation files, exit 0, no segfault. The original bug is closed.

Argparse trap: the wing key starts with `-` so `--wing -Users...` is misread as a flag. Use `--wing=-Users...` (equals form) — applies to any shell invocation of `mempalace mine`, not just our hook.

#### Smoke test — Arkskill-010 final acceptance criterion

Built `/tmp/mempalace-smoke-test.sh` and ran it. Launched 4 concurrent `mempalace mine` processes against 4 different wings:
- `-Users-sunginkim-GIT-ArkNode-AI-projects-trading-signal-ai-scripts`
- `-Users-sunginkim-GIT4-ArkNode-Poly`
- `-Users-sunginkim--superset-worktrees-ArkNode-Poly-x-research`
- `-Users-sunginkim-GIT-pytest-presentation`

All started simultaneously via `&`, all targeting the same shared palace.

Results:
| Metric | Before | After | Verdict |
|---|---|---|---|
| HNSW segment sizes | 172K + 200K + 200K | **172K + 200K + 200K** | ✅ Zero bloat from 4 concurrent writes |
| `embeddings_queue` rows | 28,860 | **29,177** | ✅ Monotonic +317, no data loss |
| Process exit codes | — | **0, 0, 0, 0** | ✅ No segfaults |
| Repair-status | — | normal flush-lag UNKNOWN | ✅ Not DIVERGED |
| Elapsed | — | 22s for 4 parallel mines | ✅ Lock not over-serializing |

**This is the exact race that produced the 294GB bloat pre-v3.3.4.** Same workload now runs cleanly. PR #976 verified working in production.

#### Live hook drift — discovered and fixed

Audit found one stale fix-application surface: `~/.claude/hooks/ark-history-hook.sh` was 11K (May 1 / v1.23.0 era) and still contained the retired `ark-global-mine-mutex` block. The plugin marketplace cache only contains versions ≤1.23.0 (v1.23.1 pushed but cache hadn't refreshed). Fixed by `cp` from the repo source-of-truth → live hook is now 9.4K, `has_retired_mutex: 0`. This was system-wide drift, not per-project.

Audited all 9 projects in `~/.superset/projects/` and 6 vaults in `~/.superset/vaults/`:
- ✅ No per-project `ark-history-hook.sh` copies (ArkNode-Poly's `.claude/hooks/` only has codex-prelint + ruff-lint, unrelated)
- ✅ No version pins in any project's CLAUDE.md
- ✅ No leftover `.ark-global-mine-mutex` lockdirs anywhere on disk
- ✅ No per-project `.mempalace` state directories
- ✅ All circuit breakers clean across all wings

#### Arkskill-010 closed

All 4 acceptance criteria now `[x]`. Status bumped `in-progress` → `done`. Smoke-test result and script path captured inline in the criterion text.

### Decisions Made

- **Repair playbook for HNSW bloat: manual segment move, not `mempalace repair` alone.** When `_upsert`/`_query` segfaults persist after upgrading to v3.3.4+, the fix is to `mv` the bloated VECTOR segment directory aside (instant same-FS rename, fully reversible), then run `mempalace repair --mode legacy --backup --yes` so chromadb can open the collection on a fresh empty HNSW and rebuild from the metadata segment in `chroma.sqlite3`.
- **Trust the SQLite metadata segment as ground truth.** The 21,392 drawers and 330 closets in `chroma.sqlite3` survive HNSW bloat because they live in different chromadb segments. Repair extracts via `col.get()` (metadata path), not `col.query()` (HNSW path that segfaults).
- **Capture true exit codes, never trust `tee`.** `mempalace repair … | tee log; echo $?` reports `tee`'s exit, not the upstream process's. Use `> log 2>&1; echo $?` instead — caught a 139 that looked like a 0 for over an hour.
- **Sync live hook from repo source whenever plugin-marketplace cache lags.** `cp ~/.superset/projects/ark-skills/skills/claude-history-ingest/hooks/ark-history-hook.sh ~/.claude/hooks/ark-history-hook.sh` is forward-compatible — when the marketplace eventually pulls v1.23.1, the auto-install path overwrites with identical content.

### Issues & Discoveries

- **Tee masks segfault exit codes** — fundamental gotcha for any shell invocation of mempalace (or any chromadb-backed tool). Documented in [MemPalace-HNSW-Bloat-Repair](../Compiled-Insights/MemPalace-HNSW-Bloat-Repair.md).
- **`mempalace repair-status` cannot detect physical file bloat** — only compares SQLite vs HNSW *counts*. A 294GB `link_lists.bin` for 21K vectors reports "OK / within tolerance" even though the file is unusable.
- **Plugin marketplace cache lag** — caches `1.22.1`–`1.23.0` of ark-skills exist locally, but `1.23.1` is missing despite being pushed and tagged. The live hook is whatever `/claude-history-ingest` last installed; it does not auto-update from the cache. This is a fix-application visibility risk — version pinned in `VERSION`/`plugin.json` is decoupled from what's actually executing in `~/.claude/hooks/`.
- **Argparse vs `-`-prefixed wing keys** — universal trap for any shell-invoked mempalace command on machines using path-derived wing keys.

### Updated Next Steps

1. **Watch for MemPalace v3.3.5** — ships #1132 (`_query` search segfault fix) and #1062 (`quarantine_stale_hnsw()` on MCP startup, retires `/ark-health` Check 14d).
2. **Watch for plugin marketplace cache to pick up v1.23.1** — at that point the live-hook sync we did is no longer needed; future installs/upgrades will deliver the mutex-retired hook automatically.
3. **Investigate `mempalace-mcp` symlink loop warning** from pipx upgrade (still open from morning session, non-blocking).
4. **Consider adding a `/ark-health` check** for live-hook drift: compare `~/.claude/hooks/ark-history-hook.sh` content hash against the most recent plugin-cache version. Would have caught this drift instantly.
