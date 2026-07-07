<!-- ark:begin id=omc-routing version=1.13.0 -->
## Skill routing — OMC integration

User hand-edited this block — DRIFT.
<!-- ark:end id=omc-routing -->
<!-- ark:begin id=routing-rules version=1.11.0 -->
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
`````

---

To add routing to a new project, copy the block above into the project's CLAUDE.md. The `/ark-workflow` skill is already available globally via the ark-skills plugin.
<!-- ark:end id=routing-rules -->
<!-- ark:begin id=vault-awareness version=2.2.0 -->
## Vault Awareness

This project's durable knowledge lives in an OKF vault. Treat it as both an input and an
output of your work — not an afterthought.

- **Before** non-trivial or brownfield work, consult the vault first — "has this been
  built, decided, or tried before?" Read paths: `/notebooklm-vault` (synthesized recall)
  or `python3 vault/_meta/okf/okf_cli.py search` (navigation / full-text).
- **At the end of a session**, distill durable insights back with `/vault` — research
  findings, decisions and their rationale, reference pages. Durable knowledge only: not
  session logs, not task tracking (those live in GitHub Issues + `log.md`).

Neither step is automatic; they are your responsibility. Skipping the pre-work read risks
rebuilding something that already exists; skipping the distill loses what you learned.
<!-- ark:end id=vault-awareness -->
