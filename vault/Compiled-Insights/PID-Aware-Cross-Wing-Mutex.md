---
title: "PID-Aware Cross-Wing Mutex"
type: compiled-insight
tags:
  - compiled-insight
  - pattern
  - infrastructure
  - concurrency
summary: "Shell mutex that embeds the holder PID so contenders can distinguish a live long-running lock from a stale one. Fixes the 'live mine wiped by age-only stale recovery' regression in age-only timestamp mutexes. Distinct from in-process fcntl.flock — this is for cross-process shell hook serialization with planned retirement when upstream concurrency lands."
source-sessions: []
source-tasks:
  - "[[Arkskill-010]]"
created: 2026-04-24
last-updated: 2026-04-24
---

# PID-Aware Cross-Wing Mutex

## Summary

Shell-level mutex for serializing cross-process workloads (separate Claude sessions, separate worktrees, separate ark-history-hook firings) against a shared resource — in this case the MemPalace ChromaDB palace. Distinct in shape and intent from [[Atomic-Chain-File-Mutation-Pattern]]: that one uses `fcntl.flock` inside a single Python helper for in-process coordination. This one is a shell `mkdir`-based lock with the holder's PID embedded so a contender can ask "is the holder still alive?" before reclaiming.

The v1.21.4 release replaced an age-only mutex (introduced in v1.21.1 as a 10-minute mtime check) with the PID-aware variant. The age-only version had a real failure mode: a legitimate `mempalace mine` that ran past 10 minutes could have its live lock wiped by a later session, reopening the exact HNSW write race v1.21.1 was meant to close. PID-awareness fixes that regression.

## The shape

```bash
acquire_lock() {
  local lockdir="$1"   # e.g. ~/.mempalace/palace/.ark-global-mine-mutex
  if mkdir "$lockdir" 2>/dev/null; then
    echo "$$" > "$lockdir/pid"
    return 0
  fi
  # Lock exists — is the holder still alive?
  local holder_pid
  holder_pid=$(cat "$lockdir/pid" 2>/dev/null)
  if [ -n "$holder_pid" ] && kill -0 "$holder_pid" 2>/dev/null; then
    return 1   # live holder; back off
  fi
  # Holder is dead OR PID file missing — try age-based recovery
  local age
  age=$(_mtime "$lockdir")
  local now
  now=$(date +%s)
  if [ $((now - age)) -gt 600 ]; then
    rm -rf "$lockdir"
    if mkdir "$lockdir" 2>/dev/null; then
      echo "$$" > "$lockdir/pid"
      return 0
    fi
  fi
  return 1
}
```

Two key properties:

1. **PID check before age check.** `kill -0 $pid` returns 0 if the process exists. Contenders honor live holders regardless of age. Age-based recovery only runs when the PID file is *missing* (lock dir created by a process that crashed before writing pid) or the PID is dead.

2. **Lock granularity.** v1.21.4 applied the helper to two locks: the per-wing lock (`$STATE_DIR/$WING.lock`, scoped to one project's mining) and the palace-global lock (`~/.mempalace/palace/.ark-global-mine-mutex`, scoped to the whole MemPalace ChromaDB). The cross-wing global one is the load-bearing fix for the HNSW write race; the per-wing one prevents the same wing's hook firing twice.

## Why not fcntl.flock here

The [[Atomic-Chain-File-Mutation-Pattern]]'s `fcntl.flock` is the right tool for *in-process* read-modify-write. Three reasons it doesn't fit here:

- **Cross-shell coordination.** The contenders are separate `bash` processes from separate Claude Code sessions; they don't share a Python interpreter. Wrapping every hook firing in a Python helper just to call `flock` adds startup cost.
- **No file to lock.** The protected resource is a SQLite + HNSW palace directory, not a single markdown file. Locking would require a sentinel file, which is what the `mkdir` lockdir already is.
- **OS releases flock on FD close.** That's a feature when the lock holder is one process — but `mempalace mine` shells out to subprocesses; if the parent shell's FD closes mid-mine the OS releases the lock while children are still writing. The mkdir+pid pattern survives this because lock release is explicit.

For a single-process atomic file write, use [[Atomic-Chain-File-Mutation-Pattern]]. For cross-shell mutual exclusion against a shared external resource, this is the shape.

## Portable `stat` for `_mtime`

The `_mtime()` helper hides a real cross-platform trap. The original v1.21.1 code used:

```bash
mtime=$(stat -f %m "$lockdir")  # BSD form
```

On macOS this returns the file mtime (correct). On GNU/Linux `-f` means *filesystem format info* — totally different output, silently mis-probed. v1.21.4 added a fallback:

```bash
_mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null
}
```

BSD form first because that's the dev-machine path; GNU form for downstream Linux users. **Any shell script that touches `stat` for mtime should carry this fallback** unless the script is gated to a single platform.

## Retirement plan (and why retirement matters)

The mutex is explicitly tagged as defense-in-depth, not the long-term answer. Once upstream MemPalace [#976](https://github.com/MemPalace/mempalace/pull/976) (HNSW thread-safety) lands, the cross-wing race closes at the chromadb layer and the ark-skills mutex becomes vestigial. Tracked as `Arkskill-010` — when #976 merges, the mutex retires.

This pattern itself — temporary serialization mechanism with a named retirement trigger — is worth pinning. It's how to ship a workaround without it ossifying. The CHANGELOG entry for v1.21.1 names the retire watchpoint inline ("Retire when upstream #976 lands"), which makes the cleanup discoverable from a `grep` rather than relying on memory.

## Evidence

- `CHANGELOG.md` v1.21.4: "the v1.21.1 mutex … used a 10-minute mtime check to recover stale locks — but a legitimate `mempalace mine` running past 10 minutes could have its live lock wiped by a later session, reopening the exact HNSW write race the release closes."
- `CHANGELOG.md` v1.21.4: "New `mtime()` / `_mtime()` helper tries BSD form first, falls back to GNU `stat -c %Y`."
- `CHANGELOG.md` v1.21.1: "Cross-wing mine mutex … Retire when upstream [#976](https://github.com/MemPalace/mempalace/pull/976) (HNSW thread-safety) lands."
- Commits `c521167` (v1.21.1 mutex introduce), `1a54608` (v1.21.4 PID-aware fix).
- Pre-push CCG (Codex + Gemini) tri-model review caught all four of the v1.21.4 fixes.

## Implications

- **Age-only timestamp mutexes are a regression vector.** If a legitimate workload can run longer than the staleness threshold, you'll wipe live locks and reopen the race. Always pair age-based recovery with a liveness check (PID, lockfile-on-named-pipe, etc.).
- **Don't use `stat -f` portably.** Prefer `stat -f %m … || stat -c %Y …` or the equivalent in whatever shell the script targets.
- **Tag every workaround mutex with its retirement trigger** (upstream PR number, version, condition) inline in the CHANGELOG and in the skill comment block. Otherwise temporary becomes permanent.
- **`mkdir`-as-lock survives crashes the way file-creation-with-O_EXCL does** — atomic, race-free, no lingering FDs. PID-file inside the dir is what makes liveness detection cheap.
- **Pre-push tri-model review (CCG)** caught all four v1.21.4 fixes. None were caught by single-model review or local test runs. This is consistent with [[Codex-Review-Non-Convergence]] — multiple independent reviewers find disjoint issue sets.
