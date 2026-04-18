# Routing Rules Template

Copy the block below into a project's CLAUDE.md to auto-trigger /ark-workflow and enable cross-session chain resume in that project.

---

`````markdown
## Skill routing — Ark Workflow

**Session start — check for in-progress chain:**
At the start of every session in this project, check for `.ark-workflow/current-chain.md`.
If it exists with unchecked steps, read it and announce to the user:

  "Found an in-progress ark-workflow chain:
  - Scenario: [scenario]/[weight]
  - Progress: step X of Y complete
  - Next: [next skill]
  Continue from here, or archive as stale?"

If the user continues, rehydrate TodoWrite tasks from the unchecked items and resume
from the next pending step. If the chain has a `handoff_marker` set and it's checked,
announce the session transition and run the handoff instructions.

**New task triage:**
When starting any non-trivial task (and no in-progress chain exists), invoke
`/ark-workflow` first to triage and get the skill chain. Pattern triggers:

- "build", "create", "add feature", "new component" → /ark-workflow (greenfield)
- "fix", "bug", "broken", "error", "investigate" → /ark-workflow (bugfix)
- "ship", "deploy", "push", "PR", "merge" → /ark-workflow (ship)
- "document", "vault", "catch up", "knowledge" → /ark-workflow (knowledge capture)
- "cleanup", "refactor", "audit", "hygiene", "dead code" → /ark-workflow (hygiene)
- "upgrade", "migrate", "bump", "version" → /ark-workflow (migration)
- "slow", "optimize", "latency", "benchmark" → /ark-workflow (performance)

For trivial tasks (single obvious change, no ambiguity), skip triage and work directly.

**After each step in a running chain:**
1. Check off the step in `.ark-workflow/current-chain.md` (change `[ ]` to `[x]`)
2. Append any notes to the Notes section of the chain file
3. Update the corresponding TodoWrite task to `completed`
4. Announce: `Next: [next skill] — [purpose]`
5. Mark the next task as `in_progress`
6. If the chain is complete, move the file to `.ark-workflow/archive/YYYY-MM-DD-[scenario].md`

### Session habits

Three habits keep context healthy across long chains:

- **Rewind beats correction.** When a step produces a wrong result, prefer
  `/rewind` (double-Esc) over replying "that didn't work, try X." Rewind drops
  the failed attempt from context; correction stacks it.
- **New task, new session.** When the current chain completes and the next
  task is unrelated, `/clear` and start fresh.
- **`/compact` with a forward brief.** When compacting mid-chain, steer the
  summary: `/compact focus on the auth refactor; drop the test debugging`.
  `/ark-workflow`'s step-boundary probe pre-fills this template from chain
  state when context crosses the nudge or strong threshold.
`````

---

To add routing to a new project, copy the block above into the project's CLAUDE.md. The `/ark-workflow` skill is already available globally via the ark-skills plugin.
