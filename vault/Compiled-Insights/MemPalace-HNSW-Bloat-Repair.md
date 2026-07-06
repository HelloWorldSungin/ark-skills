---
title: "MemPalace HNSW Bloat Repair"
type: compiled-insight
tags:
  - compiled-insight
  - infrastructure
  - mempalace
  - debugging
description: "When `_upsert`/`_query` segfaults persist after upgrading mempalace, the on-disk HNSW segment is bloated and must be manually moved aside before `mempalace repair` can run. v3.3.4 prevents future bloat but doesn't repair existing on-disk corruption."
source-sessions:
  - "[[S014-MemPalace-v3-3-4-Upgrade-Mutex-Retirement]]"
source-tasks:
  - "[[Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges]]"
created: 2026-05-05
last-updated: 2026-05-05
timestamp: 2026-05-05T00:00:00Z
---

# MemPalace HNSW Bloat Repair

## Summary

If `mempalace mine` (or `search`) crashes with `chromadb/api/rust.py:_upsert` (or `:_query`) segfault even after upgrading to MemPalace v3.3.4+, the segfault is no longer a *new* race — it's the on-disk HNSW segment from past races, still corrupt. The upstream #976 fix (`mine_palace_lock()`) prevents future races but does not retroactively repair bloated `link_lists.bin` files. Repair requires manually moving the corrupted VECTOR segment directory aside so chromadb can open the collection on a fresh empty HNSW, then `mempalace repair --mode legacy` rebuilds from the metadata segment in `chroma.sqlite3`.

This page documents the diagnosis steps, the non-obvious failure modes (silent repair, `tee`-masked segfault), and the precise fix sequence.

## Root Cause Recap

ChromaDB stores each collection across two segment types:
- **VECTOR / hnsw-local-persisted** — HNSW graph index on disk as `link_lists.bin`, `data_level0.bin`, `header.bin`, etc.
- **METADATA / sqlite** — drawer text/metadata inside `chroma.sqlite3` (the SQLite database file at the palace root).

Pre-v3.3.4, MemPalace had no thread-safety lock on HNSW writes. When multiple Claude Code Stop hooks fired across different wings simultaneously, all four-five concurrent `mempalace mine` processes wrote to the same HNSW. The graph connectivity file (`link_lists.bin`) accumulated orphan and duplicate edges without bound. Observed bloat factor: **~14,000×** normal size — `link_lists.bin` for ~21,000 vectors should be ~20MB; ours grew to **294GB**.

The bloat is graph-level corruption, not data-level: the metadata segment (`chroma.sqlite3`) remained intact with all 21,392 drawers.

## Why `mempalace repair` alone does not work

`mempalace repair --mode legacy --backup --yes` calls `col.count()` at line 689 of `mempalace/cli.py:cmd_repair` to read the drawer count. `col.count()` opens the collection's HNSW segment via the chromadb Rust extension. On a 294GB `link_lists.bin`, this segfaults — exit code 139, no output.

Two compounding visibility problems:

1. **Pipeline `tee` masks the real exit code.** `mempalace repair … | tee log; echo $?` reports `tee`'s exit (0), not the upstream process's (139). The repair *appears* to succeed silently. Always capture exit code with redirection: `> log 2>&1; echo $?`.

2. **`mempalace repair-status` cannot detect physical file bloat.** It only compares SQLite vs HNSW *counts*. A 294GB `link_lists.bin` for 21K vectors reports `OK / within tolerance` even though the file is unusable. Always pair `repair-status` with `du -sh ~/.mempalace/palace/*` when diagnosing crashes.

## The Repair Procedure

### 1. Identify the bloated VECTOR segment

```bash
sqlite3 ~/.mempalace/palace/chroma.sqlite3 \
  "SELECT c.name, s.id, s.type, s.scope FROM collections c JOIN segments s ON c.id=s.collection ORDER BY c.name, s.type;"
```

Cross-reference against `du -sh ~/.mempalace/palace/*` — the segment directory in tens-of-GB range is the bloated one. The `mempalace_drawers` collection's VECTOR segment is the typical culprit (it carries the bulk of conversation drawers).

### 2. Move (do not delete) the corrupted segment directory

```bash
mv ~/.mempalace/palace/{seg-uuid} ~/.mempalace/palace/{seg-uuid}.bak
```

Same-FS rename — instant, fully reversible. **Do NOT `rm -rf` yet** — keep the `.bak` until repair confirms success.

### 3. Reserve disk headroom

The repair extracts all drawers to memory + temp working space. On a 21K-drawer palace, plan for **~1-2GB transient working set**. If the `.bak` is sitting on a near-full disk, the repair will fail with ENOSPC mid-extraction. Either delete the `.bak` first (only after confirming the SQLite metadata segment is intact via `mempalace repair-status`) or move it to a different volume.

### 4. Run repair

```bash
mempalace repair --mode legacy --backup --yes > /tmp/mempalace-repair.log 2>&1
echo "EXIT: $?"
```

`--backup` copies `chroma.sqlite3` (the ground truth) to `~/.mempalace/palace.backup` before mutating. `--yes` skips the interactive confirmation (the prompt has no TTY in non-interactive contexts and silently bails without it).

Expected output:
```
=======================================================
  MemPalace Repair
=======================================================
  Drawers found: 21392
  Extracting drawers...
  Extracted 21392 drawers
  Backing up to /Users/.../palace.backup...
  Rebuilding collection...
  Re-filed 5000/21392 drawers...
  Re-filed 10000/21392 drawers...
  ...
  Repair complete. 21392 drawers rebuilt.
=======================================================
```

### 5. Verify

```bash
mempalace repair-status                                     # should now report flush-lag UNKNOWN, not DIVERGED
du -sh ~/.mempalace/palace/*                                # all VECTOR segments back in 100K-1MB range
mempalace mine ~/.claude/projects/{some-wing} --mode convos --wing={wing-key}   # exit 0, no segfault
```

The new VECTOR segment will have a fresh UUID (chromadb regenerates the segment ID on rebuild). Do not be alarmed when `347d1275-...` becomes `28bdd9c7-...` — it is the same logical segment, recreated.

### 6. Reclaim the bloat

Once repair has completed, mining works, and you've kept the palace open for a session or two without recurrence:

```bash
rm -rf ~/.mempalace/palace/{seg-uuid}.bak
rm -rf ~/.mempalace/palace.backup    # optional — keep until you're confident
```

## Cross-Process Argparse Trap

Wing keys derived from project paths begin with `-` (e.g., `-Users-sunginkim--superset-projects-ark-skills`). `mempalace mine … --wing -Users-…` is misread as a new flag and fails with:

```
mempalace mine: error: argument --wing: expected one argument
```

Use the equals form: `--wing=-Users-…`. This applies to any shell invocation — our hook handles it correctly (passes via `WING="$1"` positional), but ad-hoc CLI use must use `=`.

## Smoke Test Verification

After repair, verify the upstream lock works by simulating the original cross-wing race. See [PID-Aware-Cross-Wing-Mutex](PID-Aware-Cross-Wing-Mutex.md) § Retired (2026-05-05) for the smoke-test methodology — 4 concurrent `mempalace mine` against 4 different wings produces zero HNSW bloat and zero segfaults on v3.3.4+.

## Implications

- **Upgrading mempalace alone is insufficient when there is pre-existing bloat.** Always pair version upgrades with a `du -sh ~/.mempalace/palace/*` audit. If any VECTOR segment is in tens-of-GB range, the upgrade will not stop crashes — repair must run too.
- **`tee` is unsafe for capturing exit codes from chromadb-backed tools.** Anywhere we pipe mempalace output for logging, we must capture exit via `> file 2>&1; echo $?` or `${PIPESTATUS[0]}` instead. This gotcha is general to any subprocess that can segfault inside a Rust extension — bash does not propagate pipe-segment exit codes by default.
- **Trust the SQLite metadata segment as ground truth.** No matter how badly the HNSW index corrupts, the actual drawer text is in `chroma.sqlite3`. Backups should prioritize the SQLite file; HNSW segments can always be rebuilt from it.
- **Tag every workaround mutex with its retirement trigger.** [PID-Aware-Cross-Wing-Mutex](PID-Aware-Cross-Wing-Mutex.md) applies — but the corollary here is: when the trigger lands, *also* schedule a sweep for any state the mutex was protecting against. The mutex retirement closed the door on *new* bloat; it did not clean up *old* bloat. Two separate fixes for two separate concerns.
- **Plugin cache lag introduces fix-application visibility risk.** Even after the source-of-truth hook is committed and pushed, the live `~/.claude/hooks/ark-history-hook.sh` may stay stale until the marketplace cache picks up the new version and `/claude-history-ingest` re-runs install. If urgent, manually `cp` the repo source-of-truth over the live hook — same content, forward-compatible with the eventual auto-install.

## Evidence

- `vault/Session-Logs/S014-MemPalace-v3-3-4-Upgrade-Mutex-Retirement.md` § Continuation — full trace.
- `mempalace/cli.py` lines 679-694 (`cmd_repair` opens chromadb at `col.count()`).
- `mempalace/repair.py` line 358 (`rebuild_index` ChromaBackend instantiation).
- Smoke test script: `/tmp/mempalace-smoke-test.sh` (4 concurrent mines, before/after disk + count diff).
- Repair log captured at `/tmp/mempalace-repair.log`: 21,392 drawers rebuilt in ~2 minutes.
- Disk reclaimed: 294GB → 200K HNSW segments (14,000× factor inverted).
