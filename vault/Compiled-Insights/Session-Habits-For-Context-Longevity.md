---
title: "Session Habits for Context Longevity"
type: compiled-insight
tags:
  - compiled-insight
  - context-management
  - workflow
  - session-habits
  - ark-workflow
summary: "Three habits that shape context longevity across a skill chain: rewind-before-correction, new-task-means-new-session, compact-with-forward-brief. Landed in ark-workflow SKILL.md as a coaching block in v1.17.0; the Step 6.5 probe surfaces them contextually."
source-sessions:
  - "[[S011-Ark-Workflow-Context-Budget-Probe]]"
source-tasks:
  - "[[Arkskill-007-context-budget-probe]]"
created: 2026-04-17
last-updated: 2026-04-17
---

# Session Habits for Context Longevity

## Summary

Three practices that keep the parent session's context lean across a long
skill chain. Shipped in `/ark-workflow` v1.17.0 as a dedicated "Session
Habits" section between "When Things Change" and "Routing Rules Template",
and as a `### Session habits` subsection in `references/routing-template.md`
so downstream CLAUDE.md files inherit the coaching via `/ark-update`. The
context-budget probe introduced in the same release surfaces these habits
contextually at nudge/strong thresholds — but the habits matter between
probes too.

## The three habits

### 1. Rewind beats correction

When a step produces a wrong result, prefer `/rewind` (double-Esc) over
replying "that didn't work, try X." Rewind drops the failed attempt from
context. Correction stacks it. Over a 10-step chain with three
corrections, the difference between "stacked" and "rewound" can be 40-80k
tokens of detours that never contributed to the final output.

**When correction is better anyway:** when the failed attempt contains
information the next attempt needs (a surprising test result, a
discovered file path, a user preference the assistant learned). Rewind
erases that. Judgment call — but default to rewind.

### 2. New task, new session

When the current chain completes and the next task is unrelated, `/clear`
and start fresh. Grey area: closely-coupled follow-ups (e.g., documenting
a feature you just shipped) may reuse context — the just-shipped work is
load-bearing for the follow-up.

**Heuristic:** if the next task would be explained to a cold colleague
in under a paragraph, clearing is worth it. If the next task depends on
"the thing we just did" in ways that are hard to summarize, keep the
context.

### 3. `/compact` with a forward brief

When compacting mid-chain, steer the summary instead of accepting the
default. Example: `/compact focus on the auth refactor; drop the test
debugging`. The probe's mitigation menu pre-fills this template using
the current chain state — scenario, weight, completed steps, next step,
remaining steps — leaving a `<fill in>` slot for the key findings the
user wants to preserve.

**Why this matters:** a default `/compact` tries to summarize everything
equally. A directed `/compact` keeps the load-bearing work at full
resolution and collapses the disposable work aggressively. The
difference in post-compact reasoning quality is large.

## Why this is an insight, not just prose in a skill file

The three habits are discoverable only by reading
`skills/ark-workflow/SKILL.md` end-to-end (484 lines) or
`references/routing-template.md`. Vault retrieval against "how do I
keep context lean across a chain?" would otherwise miss them entirely.
Promoting to a compiled-insight page means any future query for
"session habits", "context longevity", "rewind vs correction",
"compact forward brief" surfaces the canonical three-line rule directly.

The probe in Step 6.5 is the mechanism; these three habits are the
heuristic. Both are needed — the probe fires only at thresholds, while
the habits guide every decision between them.

## References

- `skills/ark-workflow/SKILL.md` §"Session Habits" — canonical source
- `skills/ark-workflow/references/routing-template.md` §"Session habits" subsection
- `skills/ark-workflow/scripts/context_probe.py` — the probe that surfaces these at thresholds
- [[S011-Ark-Workflow-Context-Budget-Probe]] — ship session
- [[Arkskill-007-context-budget-probe]] — epic
