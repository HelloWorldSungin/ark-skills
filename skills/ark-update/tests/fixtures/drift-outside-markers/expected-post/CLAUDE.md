<!-- ark:begin id=omc-routing version=1.13.0 -->
## Skill routing — OMC integration

This section is managed by `/ark-update`. Do not hand-edit content between the ark markers.

### When OMC is available

When `HAS_OMC=true` (i.e., `command -v omc` succeeds and `ARK_SKIP_OMC` is not set),
`/ark-workflow` Step 6 renders a 3-button choice after triage:

```
[Accept Path B]   [Use Path A]   [Show me both]
```

**Path A (Ark-native):** step-by-step, user-in-the-loop, discrete skills at every decision
point. Always available. Default when OMC is not detected.

**Path B (OMC-powered):** front-loaded judgment + consensus plan + autonomous execution +
Ark closeout. Recommended when any of these signals fires:
- Prompt contains an OMC keyword (`autopilot`, `ralph`, `ulw`, `deep interview`, etc.)
- Triaged weight class is Heavy
- Task touches ≥3 independent modules
- User explicitly requests hands-off execution

**Emergency rollback:** `ARK_SKIP_OMC=true /ark-workflow "<prompt>"` forces Path A
regardless of OMC detection. Intended for incident response.

### Install OMC

OMC not detected? Install it to unlock Path B chains:

  See INSTALL_HINT_URL for installation instructions.
  (Constant defined in `skills/ark-workflow/references/omc-integration.md` § Section 0.)

After installation, re-run `/ark-workflow` — OMC detection is automatic.

### Path B routing table

| Variant | OMC engine | Handback boundary |
|---------|-----------|-------------------|
| Greenfield / Bugfix / Hygiene / Ship / Migration (non-Heavy) | `/autopilot` | After Phase 4; Phase 5 (docs/ship) skipped |
| Greenfield Heavy (multi-module) | `/ultrawork` | After last parallel lane completes |
| Bugfix Heavy / Performance Medium+Heavy | `/ralph` | After loop-to-verified exits with success |
| Migration Heavy | `/team` | After `team-verify`, before `team-fix` |

After `<<HANDBACK>>`, Ark resumes from the variant's Path A closeout step.
See `skills/ark-workflow/references/omc-integration.md` § Section 4 for the full
variant-inherited handback contract and expected-closeout table.
<!-- ark:end id=omc-routing -->
<!-- ark:begin id=routing-rules version=1.12.0 -->
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

## User Extra Section

This user content lives outside managed regions.
The engine must not touch it.
