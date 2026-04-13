# Ark Context Warm-Up — Design Spec

**Date:** 2026-04-12
**Scope:** New `/ark-context-warmup` skill + integration into every `/ark-workflow` chain.
**Status:** Approved (brainstorming phase)

## Problem

`/ark-workflow` emits a numbered skill chain but assumes the agent running the chain already has the project's recent and relevant context in session. In practice the agent often lacks it — especially at the start of a planning session (`/brainstorming`) or after a session handoff. The three tools that could supply this context (`/notebooklm-vault`, `/wiki-query`, `/ark-tasknotes`) are never invoked automatically. The agent proceeds half-blind, duplicating tracked work, missing past decisions, and forgetting where the previous session left off.

## Goal

Before any chain executes, automatically gather the most recent and relevant project context from the three available backends and present it to the agent as a single structured `## Context Brief`. Warm-up is:

- **Unconditional** — runs as step 0 of every chain, regardless of weight class.
- **Non-blocking** — every failure mode degrades gracefully. The chain never halts on warm-up failure.
- **Reusable** — exposed as a standalone skill, invokable outside any chain.
- **Efficient** — parallel fan-out, scenario-aware queries, 2-hour cache for intra-chain re-use.

## Non-Goals

- Not a NotebookLM sync operation. Sync staleness is `/ark-health`'s concern.
- Not a cross-project context tool. Scoped to the current project's vault.
- Not a contradiction resolver. If backends disagree, both signals surface; the agent reconciles.
- Not a gating mechanism. The warm-up informs, it does not block.

## Scope Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Which scenarios trigger warm-up | All scenarios `/ark-workflow` triages, every weight class | User prioritized "always have context"; no Light exemption |
| `/notebooklm-vault` sub-command | Smart pick: `session-continue` if latest session log <7 days old, else `bootstrap` | Matches resume-vs-cold-start decision humans already make |
| `/wiki-query` question formulation | Scenario-aware template (Greenfield/Bugfix/Migration/Performance/Hygiene each get tailored queries; Ship/Knowledge-Capture skip) | Highest signal per token spent; scenario is already known at warm-up time |
| `/ark-tasknotes` usage | Both `status` summary AND keyword search for tasks related to the user's prompt | Duplicate detection + in-flight collision detection in one pass |
| Implementation location | New standalone skill `/ark-context-warmup`, prepended as step 0 to every `chains/*.md` | Single source of truth for warm-up logic; reusable on demand; decouples triage from context fetching |
| Overall shape | Approach 2: parallel fan-out + synthesized `## Context Brief` with a `Flags` section | Fastest wall-clock; the Flags section is the high-value output |

## Architecture

### New skill

- **Path:** `skills/ark-context-warmup/SKILL.md`
- **Siblings:** lives alongside other Ark skills in this plugin repo
- **Internal structure:** single SKILL.md for orchestration; a small helpers script at `scripts/warmup-helpers.sh` (or `.py`) for unit-testable logic (smart-pick, scenario-to-query mapping, flag detection, cache freshness, synthesis)
- **Subdirs (required by the testing strategy):** `scripts/` for helpers + their tests, `fixtures/` for flag-regression test inputs

### Integration into chains

Every chain file (`greenfield.md`, `bugfix.md`, `ship.md`, `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`) gets a new step 0:

```
0. `/ark-context-warmup` — load recent + relevant project context
```

All existing numbered steps shift down by 1. For chains with session-handoff markers, the marker numbers referenced in comments also shift (e.g., `handoff_marker: after-step-5` → `after-step-6`). Chains affected by marker shifts: Greenfield Medium (handoff_marker: after-step-3 → after-step-4), Greenfield Heavy (after-step-5 → after-step-6), Migration Heavy (after-step-4 → after-step-5), Performance Heavy (after-step-5 → after-step-6).

### Role separation

- `/ark-workflow` triages and emits the chain. It does NOT invoke `/ark-context-warmup` itself — consistent with the existing "ark-workflow does not invoke downstream skills" policy. The chain is guidance; the agent runs the steps.
- `/ark-context-warmup` is self-contained. It does its own Project Discovery, availability checks, parallel fan-out, synthesis, and emits one `## Context Brief` to the session.

### Dependency direction

`/ark-context-warmup` depends on the three source skills' *outputs* but does NOT delegate to them via the Skill tool. Instead, it re-implements the minimum subset of their behavior inline (config reads, CLI calls, MCP queries). Reason: cross-skill invocation adds overhead and makes parallel fan-out harder; the actual work is a handful of shell commands cheap to duplicate. This follows the pattern of existing Ark skills that read configs directly rather than delegating.

## Components

### 1. Project Discovery + Task Prompt Intake

Follows the plugin's standard context-discovery pattern: reads CLAUDE.md, extracts `project_name`, `vault_root`, `project_docs_path`, `task_prefix`, NotebookLM config location.

Also captures the **user's pending task description** — the warm-up needs this to formulate task-aware queries:

- If invoked from an `/ark-workflow` chain, read `.ark-workflow/current-chain.md` for `scenario` and the captured task description.
- If invoked standalone, prompt the user: *"What are you about to work on? (one line)"*

### 2. Availability Probe

Three independent fast checks, all local (no network):

| Signal | Check |
|--------|-------|
| `HAS_NOTEBOOKLM` | `notebooklm` CLI on PATH **AND** `.notebooklm/config.json` exists at vault root or project root |
| `HAS_WIKI` | `{vault_path}/index.md` exists |
| `HAS_TASKNOTES` | `{tasknotes_path}/meta/{task_prefix}counter` exists |

Each missing signal is logged once with a remediation hint. If all three are unavailable, the skill reports `"No context backends available — proceeding without warm-up."` and exits cleanly.

### 3. Parallel Fan-Out

Dispatches three concurrent subagents via the `Agent` tool (`general-purpose` type). Each subagent is self-contained and returns a compact structured result. Subagent outputs stay within subagent contexts — only the synthesized brief lands in the parent session.

| Branch | Subagent responsibility | Expected output |
|--------|-------------------------|-----------------|
| A: NotebookLM | Glob session logs; if latest is <7 days old run `session-continue`, else `bootstrap` | Structured markdown brief |
| B: Wiki-query | Map scenario to query template; run `/wiki-query`; return answer + citations | Markdown with 1-3 relevant findings, or "No matches in vault" |
| C: TaskNotes | Run `status` summary; run keyword search (MCP or grep fallback); return both | Status summary + related-tasks list |

**Scenario-to-wiki-query mapping:**

| Scenario | Query template |
|----------|----------------|
| Greenfield | "Has anything like [task] been built before?" |
| Bugfix | "Have we seen bugs related to [task] before?" |
| Migration | "Past migration notes for [task]?" |
| Performance | "Past optimization work on [task]?" |
| Hygiene | "Related refactors or audits on [task]?" |
| Ship | skip (scenario has no design component) |
| Knowledge Capture | skip (scenario is already vault-focused) |

### 4. Synthesis

Main skill receives the three structured results and assembles one `## Context Brief`:

```
## Context Brief

### Where We Left Off
[from notebooklm session-continue OR "Fresh start — no recent session found"]

### Recent Project Activity
[from notebooklm bootstrap, or session-continue's epic progress]

### Vault Knowledge Relevant to This Task
[from wiki-query, or "Not queried — scenario: ship/knowledge-capture"]

### Related Tasks & In-flight Work
[from ark-tasknotes status + related search]

### Flags
[auto-derived warnings; see below]
```

### 5. Flags Generator

Scans results for warning patterns and adds them to `Flags`. This is the highest-value synthesis work.

| Flag | Trigger |
|------|---------|
| `DUPLICATE TASK` | TaskNotes related search found an open task whose title/summary has >50% keyword overlap with user's task description (overlap = shared content-word tokens / tokens-in-smaller-set, after stop-word removal and lowercasing). Exact tokenizer pinned during implementation. |
| `CONFLICTS WITH PAST DECISION` | NotebookLM result contains keywords "decided against", "tried and failed", or "rejected" in a sentence referencing a similar approach |
| `IN-FLIGHT WORK COLLISION` | TaskNotes status shows another in-progress task touching the same module/area |
| `STALE CONTEXT` | Last session log is >14 days old (warm-up surface is degraded) |
| `NO CONTEXT AVAILABLE` | All three backends unavailable or returned empty |

If no flags trigger, `Flags` reads `None`.

## Data Flow

```
[User invokes /ark-context-warmup, directly or as chain step 0]
  |
  v
[1] Project Discovery from CLAUDE.md
  |
  v
[2] Task description capture (chain frontmatter or user prompt)
  |
  v
[3] Availability probe (HAS_NOTEBOOKLM / HAS_WIKI / HAS_TASKNOTES)
    - If all false -> emit message + EXIT 0
  |
  v
[4] Parallel fan-out (Agent tool, general-purpose subagents)
    A: NotebookLM smart-pick branch
    B: Wiki-query scenario-aware branch (skipped for ship/knowledge-capture)
    C: TaskNotes status+search branch
  |
  v
[5] Fan-in: collect results (90s per-subagent timeout; partial results OK)
  |
  v
[6] Flags generator scans all three outputs
  |
  v
[7] Synthesizer assembles final Context Brief
    - Write cache: .ark-workflow/context-brief.md
    - Emit to session
  |
  v
[8] Hand back to chain flow
```

### Cross-session caching

The brief is written to `.ark-workflow/context-brief.md` (same directory as `current-chain.md`). If `/ark-context-warmup` is invoked again within the same chain and `context-brief.md` is <2 hours old AND the scenario matches, re-emit the cached brief instead of re-running. Cache is invalidated by:

- File age >2 hours
- Different scenario (cache is scenario-specific)
- Explicit `/ark-context-warmup --refresh` flag

This matters for multi-session chains (Greenfield Heavy has two sessions; both benefit from warm-up but the second shouldn't pay full cost within the 2-hour window).

### Token and latency budget

| Case | Wall-clock | Tokens to parent session |
|------|------------|--------------------------|
| All three available, cache miss | ~15-45s (parallel) | ~6-10k (Context Brief only) |
| All three unavailable | <2s | ~100 ("no backends" message) |
| Cache hit | <1s | ~6-10k (cached brief) |

Subagent raw outputs never land in the parent context — only the synthesized brief does.

## Error Handling

### Failure matrix

| Failure | Detection | Response |
|---------|-----------|----------|
| CLAUDE.md missing required field | Context-discovery | Emit field-missing message; EXIT 0 (don't block chain) |
| `.notebooklm/config.json` exists but CLI missing | Availability probe | Log skip + remediation hint (`pipx install notebooklm-cli`); skip branch |
| `notebooklm` CLI returns auth error | Subagent A stderr match | Log `"NotebookLM auth expired. Run: notebooklm auth login"`; skip branch |
| `notebooklm ask` times out or 5xx | Subagent A retries once with 15s backoff; second failure fatal | Log + skip branch |
| Session log glob empty | Subagent A | Fall through to `bootstrap` (not an error) |
| `index.md` missing | Availability probe | Log + remediation (`/wiki-update`); skip branch |
| Scenario is ship/knowledge-capture | Task intake | Silent skip for branch B; brief section says "Not queried — scenario: X" |
| Obsidian not running (MCP unavailable) | `tasknotes_health_check` fails | Fall back to markdown scan with `grep -rl` |
| TaskNotes counter missing | Availability probe | Log + remediation (`/wiki-setup`); skip branch |
| TaskNotes returns 100+ matches | Subagent C | Truncate to top 10 by match-score; note truncation count |
| Any subagent exceeds 90s timeout | Parent timer | Kill subagent; log; continue fan-in with partial results |
| Subagent returns malformed output | Synthesizer validation | Include raw under branch section with `[warm-up: unstructured output follows]` prefix; skip flag extraction for that branch |
| Synthesizer cache-write fails | Try/catch around file write | Emit brief to session anyway; log cache failure as non-fatal |
| `.ark-workflow/` not writable | File write | Skip cache write; emit `"Cache disabled — .ark-workflow/ not writable."` |
| User interrupts (Ctrl-C) | Signal | Kill subagents; skill exits; chain resumable with `--refresh` |
| All three backends unavailable | Availability probe | Emit `"No context backends available — proceeding without warm-up. Run /ark-health to diagnose."` EXIT 0 |

### Two guarantees

1. **Never blocks the chain.** Warm-up always exits cleanly (code 0) with a user-visible message. Chain step 1 proceeds regardless.
2. **Every skipped branch has a remediation hint.** No silent skips.

### Deliberately out of scope

- Stale NotebookLM sync detection (deferred to `/ark-health`).
- Cross-project context.
- Contradictory-signal resolution (surfaced, not resolved).
- Retry on partial success (report what succeeded).

## Testing

### 1. Unit tests (helpers)

Pure functions extracted to `scripts/warmup-helpers.{sh,py}`, tested with bats-core or pytest:

| Function | Test cases |
|----------|------------|
| `should_run_session_continue` | Latest <7d → `session-continue`; latest >7d → `bootstrap`; empty glob → `bootstrap`; malformed filename → skip-then-fall-through |
| `map_scenario_to_wiki_query` | Each scenario has its expected template; ship/knowledge-capture → None; unknown → generic fallback |
| `detect_duplicate_task` | >50% keyword overlap + open status → flag; no overlap → no flag; all stop-words → no flag; closed tasks ignored |
| `detect_conflict_keywords` | Triggers on "decided against", "tried and failed", "rejected"; known false-positive case documented |
| `is_cache_fresh` | <2hr + matching scenario → fresh; >2hr → stale; scenario mismatch → stale; missing → stale |
| `synthesize_brief` | All three present → full brief; one missing → "Not queried" section; malformed → raw with prefix |

Runs on every push via CI.

### 2. Integration tests (filesystem)

bats-core against throwaway temp projects:

| Scenario | Setup | Expected |
|----------|-------|----------|
| All backends available | Full CLAUDE.md + configs + stubbed `notebooklm` CLI | All three branches dispatch |
| Only vault available | Remove NotebookLM config + TaskNotes counter | Only wiki branch runs; skip hints logged |
| None available | Remove all three | "No context backends" message; EXIT 0 |
| Missing required CLAUDE.md field | Remove `project_docs_path` | Field-missing message; EXIT 0; no probe |
| `.ark-workflow/` not writable | `chmod -w` | Brief emitted; cache failure logged; no crash |

### 3. End-to-end smoke tests (manual, documented in `scripts/smoke-test.md`)

Run before every release tag:

1. Real Ark project, all three backends configured → run `/ark-context-warmup`; verify all five sections present; under 60s.
2. Invoke `/ark-workflow` with a sample bugfix prompt → verify resolved chain starts with `0. /ark-context-warmup`, remaining steps renumbered.
3. Run `/ark-context-warmup` twice within 5 min → second run hits cache, returns in <2s with identical output.
4. Run `/ark-context-warmup --refresh` → cache bypassed, full fan-out runs.

### 4. Flag-regression tests

Fixture library at `skills/ark-context-warmup/fixtures/`:

- `duplicate-task-hit.md` — should trigger `DUPLICATE TASK`
- `duplicate-task-miss.md` — closed task; should NOT trigger
- `conflict-decision.md` — should trigger `CONFLICTS WITH PAST DECISION`
- `conflict-false-positive.md` — "decided against" in unrelated context; documents known noise
- `stale-context.md` — 20+ day old session log
- `in-flight-collision.md` — in-progress task on same module

Each fixture pairs with an expected-flags assertion. Catches flag-logic regressions immediately.

### 5. Chain-file integrity test

CI grep on all `chains/*.md`:

- First numbered step must be `` 0. `/ark-context-warmup` ``
- Any `handoff_marker: after-step-N` values must match the updated step numbers

Prevents accidental unwinding of the prepend.

### What we don't test

- NotebookLM/Obsidian backend correctness (their skills' tests, not ours).
- Parallel subagent timing precision (we test completion-or-timeout, not wall-clock numbers).
- LLM-driven synthesis quality (synthesizer is deterministic template assembly, no LLM call).

## Open Questions

None remaining after brainstorming.

## Implementation Checklist (high-level; detailed plan to follow via `/writing-plans`)

1. Create `skills/ark-context-warmup/SKILL.md` with frontmatter + sub-command routing.
2. Add `scripts/warmup-helpers.{sh,py}` with the six unit-testable helper functions.
3. Add unit tests for helpers.
4. Implement availability probe.
5. Implement three subagent branches (NotebookLM smart-pick, wiki-query scenario-aware, tasknotes status+search).
6. Implement synthesizer + flags generator.
7. Implement caching layer with 2-hour TTL + `--refresh` flag.
8. Add integration tests.
9. Add flag-regression fixtures + tests.
10. Prepend `0. /ark-context-warmup` to all seven `chains/*.md` files; shift all step numbers and handoff markers.
11. Add chain-file integrity CI check.
12. Add a smoke-test runbook at `scripts/smoke-test.md`.
13. Update `skills/ark-workflow/SKILL.md` File Map if needed to mention the new first-step expectation.
14. Register `/ark-context-warmup` in `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json`.
15. Bump `VERSION` and add `CHANGELOG` entry per the project's "always bump version" convention.
16. Write the user-facing announcement explaining the new step 0 behavior.
