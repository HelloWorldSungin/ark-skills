# Troubleshooting — When Things Change or Break

## Session Handoff

For medium and heavy tasks with a design phase:

- Spec and plan are committed to `docs/superpowers/specs/` on the current branch
- `handoff_marker` is set in `.ark-workflow/current-chain.md` frontmatter
- Tell the user: **"Design phase complete. Start a fresh Claude Code session and reference the spec at `docs/superpowers/specs/<filename>.md` to begin implementation."**

**Additional handoff points:**
- **Heavy Bugfix, step 2:** If investigation reveals architectural redesign is needed → `/checkpoint` findings, recommend fresh session with design phase
- **Heavy Hygiene, step 3:** If audit + investigation reveals systemic issues requiring rewrite → escalate to Heavy Greenfield, `/checkpoint`, fresh session
- **Heavy Migration, step 4:** After migration plan is committed → session break before implementation
- **Heavy Performance, step 5:** After optimization plan is committed → session break before implementation
- **Any scenario, mid-implementation:** If the user explicitly asks to pause, or if output quality has degraded (repeated errors, hallucinated file paths, forgotten context) → suggest `/checkpoint`. Do NOT rely on tool-call counts as a trigger — that's an unreliable proxy.
## When Things Go Wrong

If a step fails mid-workflow:

- **Failed QA:** fix bugs in the current session, re-run `/qa` to verify, re-run `/ark-code-review` if fixes are substantial
- **Failed deploy:** check CI logs for the failure. If test failure: fix and re-run `/ship`. If infra issue: investigate before retrying. Never force-merge past failing CI.
- **Review disagreement (`/ark-code-review` vs external advisor [`/ask codex` or `/ccg`]):** read both opinions — they see different things. If both flag the same area, it's almost certainly real. If they disagree, use your judgment. If `/ccg` itself reports Codex–Gemini disagreement, that's its own signal — weigh it alongside Ark's internal review. Document the resolution in the session log.
- **Flaky tests:** do not skip or retry blindly — `/investigate` the flake. If known and unrelated to your changes, note it and proceed. If new, treat as a bug.
- **Spec invalidated during implementation:** stop implementing, update the spec, re-run the design-phase external review (`/ask codex` for Medium, `/ccg` for Heavy) on the updated spec, resume from the updated spec (this is a re-triage moment)
- **Canary failure:** investigate the specific failure signal. If it's your change: rollback or hotfix (new light-class bug cycle). If pre-existing: document and proceed.
- **Vault tooling failure:** not blocking — don't let a `/wiki-update` failure hold up a ship. Note the failure, fix it in the next Knowledge Capture cycle.
- **Hygiene reveals bugs:** If `/codebase-maintenance` audit or `/investigate` uncovers bugs during a Hygiene workflow, re-triage the broken items as Bugfix (see Re-triage: Scenario shift). Fix bugs before continuing cleanup.
- **Migration breaks tests:** If a migration causes test failures, do NOT force the migration through. `/investigate` the failures — they may reveal undocumented dependencies. Fix or document before proceeding.
- **Batch item blocks other items:** If one item in a batch blocks others due to an unexpected dependency, re-order the execution plan. Flag the dependency to the user.
## Re-triage

If the task changes class mid-flight:

**Weight escalation:**
1. Stop at the current step
2. Re-classify using the triage table
3. Pick up the remaining phases from the new weight class
4. Don't restart — just add the phases you would have run

**Scenario shift:**
If investigation or implementation reveals the task is fundamentally a different scenario:
1. Stop at the current step
2. Document findings so far (session log or `/checkpoint`)
3. Re-classify into the correct scenario
4. If shifting to a scenario with a design phase (e.g., Bugfix → Greenfield), recommend a session break before starting the design phase
5. Pick up the new scenario's chain from the appropriate step

Examples:
- "Fix the login bug" → investigation reveals broken auth architecture → **pivot to Heavy Greenfield** (redesign)
- "Optimize the dashboard" → profiling reveals the data layer is fundamentally wrong → **pivot to Heavy Migration** (data layer rewrite)
- "Clean up dead code" → audit reveals half the module is broken → **pivot to Medium Bugfix** per broken item
