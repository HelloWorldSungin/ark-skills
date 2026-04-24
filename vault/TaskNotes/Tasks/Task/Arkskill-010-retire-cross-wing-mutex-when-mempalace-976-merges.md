---
title: "Retire cross-wing mutex + revisit hook strategy when MemPalace #976 merges"
tags:
  - task
  - upstream-watch
  - mempalace
task-id: "Arkskill-010"
task-type: "task"
status: backlog
priority: "low"
project: "ark-skills"
work-type: "infrastructure"
component: "claude-history-ingest"
urgency: "normal"
created: "2026-04-23"
summary: "Watch MemPalace #976 (HNSW thread-safety). When merged, retire palace-global mutex and revisit dropping our custom Stop-hook in favor of the plugin's native auto-ingest."
---

# Retire cross-wing mutex + revisit hook strategy when MemPalace #976 merges

## Description

Track the merge of upstream MemPalace [#976](https://github.com/MemPalace/mempalace/pull/976) (HNSW thread-safety + PreCompact deadlock fix). Once it lands and is shipped in a release, the cross-wing concurrent-writer race that produced our 38k-drawer palace corruption is closed at the chromadb layer.

Two follow-on actions become possible:

1. **Retire the palace-global mutex** in `skills/claude-history-ingest/hooks/ark-history-hook.sh` (the `~/.mempalace/palace/.ark-global-mine-mutex` mkdir lock added in v1.20.3).
2. **Revisit the hook strategy.** Today we keep our custom Stop-hook AND the plugin's native auto-ingest (or one of the two, depending on whether the user picks Check 14c state A or B). After #976, the question is whether we can drop our custom hook entirely and let the plugin's native auto-ingest handle conversation history mining. That's a feature decision, not just a safety one — the two hooks store different things (we mine the full transcript JSONL into `claude-history-{project}` wing; the plugin's auto-ingest captures explicit `mempalace_add_drawer` calls + PreCompact extraction). Doing the swap means accepting that loss-of-coverage tradeoff.

## Related upstream PRs to also watch

- [#991](https://github.com/MemPalace/mempalace/pull/991) — `hnsw:num_threads=1` defense-in-depth. If it lands, lower our pin urgency.
- [#1062](https://github.com/MemPalace/mempalace/pull/1062) — auto `quarantine_stale_hnsw()` on MCP startup. When merged, retire `/ark-health` Check 14d (the palace read sanity probe + drift recovery hint).

## Acceptance criteria

- [ ] #976 confirmed merged + shipped in a tagged MemPalace release
- [ ] Smoke-test the new release with multiple concurrent Claude Code sessions hitting Stop simultaneously (the exact race that caused the 38k corruption)
- [ ] Decision documented: keep custom hook, drop custom hook, or hybrid
- [ ] If retiring mutex: PR removes the mkdir block from `skills/claude-history-ingest/hooks/ark-history-hook.sh` lines 77-100ish, bumps version, updates CHANGELOG, updates `/ark-health` Check 14c retirement note

## Background

- v1.20.3 (commit `7e93411`) added the palace-global mutex after root-causing the corruption to cross-wing HNSW segment drift, NOT the chromadb 1.5.7-vs-1.5.8 ABI bugs we initially blamed.
- mempalace 3.3.2 ships [#1023](https://github.com/MemPalace/mempalace/pull/1023) (PID guard for hook runner) + [#784](https://github.com/MemPalace/mempalace/pull/784) (per-source-file `mine_lock`) + [#1000](https://github.com/MemPalace/mempalace/pull/1000) (quarantine helper, not wired to startup yet) — none of which cover the cross-wing race.
- v1.21.1 (commit `c521167`, currently on branch `reconcile-1.21.1`, not yet pushed) consolidates the v1.20.x story onto origin's v1.21.0 Shrink-to-Core slim.

## Related

- [[Arkskill-009]] (if exists)
- Vault: `Session-Logs/2026-04-23-mempalace-corruption-recovery.md` (when written)
