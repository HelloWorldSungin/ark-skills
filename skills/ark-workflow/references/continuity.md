# Continuity — Advanced Protocols

This file holds pay-per-use continuity protocols. The minimum Step 6.5 inline protocol (frontmatter template + basic after-each-step update) lives in main `SKILL.md`.

## Batch Triage Chain File Format

For batch output, write one section per group in the chain file:

~~~markdown
---
scenario: Batch
weight: mixed
batch: true
---

# Current Batch

## Group A (Light Bugfix, parallel)
### Item #2: Ghost pipeline runs
1. [ ] `/investigate`
...

### Item #5: MCP ClosedResourceError
1. [ ] `/investigate`
...

## Group B (Medium Bugfix, sequential)
### Item #3: Payload drop
1. [ ] `/investigate`
...
~~~

TodoWrite tasks are grouped with a parent task per group and sub-tasks per item step.

## Cross-Session Continuity

TodoWrite tasks are session-scoped and do NOT persist across sessions. Only `.ark-workflow/current-chain.md` persists on disk.

**1. Session start check (automatic):**
Every time a session starts in a project, the agent should check for `.ark-workflow/current-chain.md`. This applies whether or not `/ark-workflow` was explicitly invoked. The Routing Rules Template wires this up via CLAUDE.md so projects can enable it.

**2. Rehydrate TodoWrite tasks:**
When resuming a chain from the file, create new TodoWrite tasks for each unchecked step (`[ ]`). Mark the first unchecked step as `in_progress`. Completed steps (`[x]`) do not get recreated as tasks — they're history, not work.

## Handoff Markers

**Setting handoff_marker:**
The chain file distinguishes between "chain paused mid-work" (user closed Claude) and "intentional handoff" (medium+ design phase end-of-session marker). The handoff marker is recorded in the chain file frontmatter:

~~~yaml
handoff_marker: after-step-5
handoff_instructions: "Read spec at docs/superpowers/specs/2026-04-10-oauth-design.md"
~~~

**Resuming on a marked chain:**
On session start, if `handoff_marker` is set AND the marked step is `[x]` (completed), announce:
> "You're in Session 2 of a Heavy Greenfield. Design phase complete. Next: `/executing-plans` with the spec at [handoff_instructions path]."

## Stale Chain Detection

If the chain file is older than 7 days, flag it as potentially stale:
> "Found an ark-workflow chain from [age] ago. Is this still active, or should I archive it to `.ark-workflow/archive/`?"

Never auto-delete — always ask. The user may have been on vacation.

## Context Recovery After Compaction

If context compaction occurred mid-chain, the TodoWrite tasks survive but the rich chain context may be lost. The agent should re-read `.ark-workflow/current-chain.md` to refresh its understanding before continuing.

**Context recovery (catch-all):** At the start of any session in this project, if `.ark-workflow/current-chain.md` exists, the agent should read it and announce:
> "Found an in-progress `/ark-workflow` chain: [scenario]/[weight], step X of Y (`[next step]`). Continue from here?"

## Archive on Completion

On chain completion, move `.ark-workflow/current-chain.md` → `.ark-workflow/archive/YYYY-MM-DD-{scenario}.md`. Never delete — archives are workflow history. This rule also appears in abbreviated form inline in main Step 6.5.
