---
title: "MemPalace Integration Architecture"
type: compiled-insight
tags:
  - compiled-insight
  - plugin
  - infrastructure
summary: "claude-history-ingest wraps mempalace with custom hooks and three modes (index/compile/full) — NOT using mempalace's built-in hooks, which are too intrusive."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# MemPalace Integration Architecture

## Summary

The `/claude-history-ingest` skill was redesigned from a "read everything and cluster" approach to an orchestration layer over MemPalace's ChromaDB. The integration uses a custom Stop hook (not mempalace's built-in hooks), background mining to stay within Claude Code's 60-second hook timeout, and threshold-based auto-compile. Three modes separate zero-token indexing from LLM-powered synthesis.

## Key Insights

### Custom Hook, Not MemPalace's Built-In Hooks

The skill installs `~/.claude/hooks/ark-history-hook.sh` — a purpose-built Stop hook that does: index -> threshold check -> optional compile trigger. MemPalace's own `mempal_save_hook.sh` (which blocks the AI mid-conversation to force saves) was explicitly rejected as "too intrusive and designed for a different workflow." The PreCompact hook was also skipped — compile timing is controlled by the skill itself.

### Background Mining for Timeout Safety

`mempalace mine` on a large project can exceed Claude Code's 60-second hook timeout. The hook runs mining in the background (`nohup` + PID file), returns `{}` immediately, and checks the threshold on the *next* session end (by which time indexing has finished). Compile is deferred by one session — acceptable because it's not time-critical.

### Three-Mode Architecture

| Mode | Tokens | What It Does |
|------|--------|--------------|
| `index` | Zero | Mines project conversations into ChromaDB |
| `compile` | ~10K | Queries MemPalace, diffs against existing insights, writes new pages |
| `full` | ~10K | Index + compile in sequence |

The Stop hook only runs `index` automatically. `compile` is triggered either manually or when the hook detects enough new drawers have accumulated since last compile (default threshold: 50 drawers).

### Cross-Project Scoping Failure

An early version attempted to read memory files from all 15 projects and cluster them together. This produced garbage — mixing unrelated project context. The user interrupted mid-execution. The fix: scope everything to the current project's "wing" key (derived from `$PWD`). Each project gets its own wing in ChromaDB, and the compile step only queries within that wing.

### Wing Key Convention

The wing key is derived from the project path: `echo "$PWD" | sed 's|[/.]|-|g'`. For example, `/Users/sunginkim/.superset/projects/ark-skills` becomes `-Users-sunginkim--superset-projects-ark-skills`. This ensures each project's conversations are isolated in ChromaDB while remaining queryable by the compile step.

## Evidence

- Hook architecture design: conversation about custom vs. built-in hooks, background mining, timeout handling
- Cross-project scoping failure: "The skill attempted to read memory files from all 15 projects and cluster them together. This was too broad."
- Mode structure: SKILL.md at `skills/claude-history-ingest/SKILL.md`
- Codex review of the spec found 21 issues including: ARM64 segfault handling, async `&` fragility, canned searches causing recall loss

## Implications

- The hook + compile separation means indexing happens every session (cheap) while synthesis happens only when enough material accumulates (expensive but infrequent).
- If MemPalace breaks, vault compiled insights still exist as durable artifacts — the tool is complementary, not load-bearing.
- The wing-scoped design means adding a new project just means mining its directory — no config changes to the compile step.
- The "deferred by one session" tradeoff is worth the timeout safety — don't try to make indexing synchronous.
