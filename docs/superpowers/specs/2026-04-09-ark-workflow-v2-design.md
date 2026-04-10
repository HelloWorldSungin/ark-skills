# Ark Workflow v2 — Design Spec

**Date:** 2026-04-09
**Scope:** Clean rewrite of `skills/ark-workflow/SKILL.md`
**File to modify:** `skills/ark-workflow/SKILL.md` (single file, full rewrite)

## Problem

The current `/ark-workflow` skill has 12 identified gaps that cause incorrect or incomplete triage for real-world usage patterns. The most impactful: multi-item batches (3-5 numbered items) get a single chain instead of per-item triage, and bug-like items in Hygiene batches skip root cause investigation.

## Gaps Addressed

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | Multi-item batch handling missing | Critical | New "Batch Triage" section |
| 2 | `/TDD` naming mismatch (should be `/test-driven-development`) | Critical | Rename all 7 occurrences |
| 3 | Missing `/investigate` in Hygiene chains | High | Add conditional step |
| 4 | Scenario gaps (migrations, performance, security hardening) | High | Add Migration + Performance scenarios |
| 5 | No session handoff for non-Greenfield Heavy | High | Expand Session Handoff section |
| 6 | Triage conflict resolution — no tiebreaker | High | Risk-primary with decision-density escalation |
| 7 | Re-triage only covers weight, not scenario shifts | High | Expand Re-triage section |
| 8 | Knowledge Capture has no weight classes | Medium | Light/Full split |
| 9 | Condition definitions vague/incomplete | Medium | Precise trigger lists |
| 10 | ~~Useful skills unreferenced~~ | ~~Medium~~ | **Deferred** — not included in this rewrite. `/health` doesn't exist in this plugin (`/ark-health` does, but serves a different purpose). `/careful`/`/guard` are gstack safety skills — reserved for a follow-up iteration with explicit placement. |
| 11 | Conditions evaluated post-triage | Low | Short-circuit early exits |
| 12 | Security hardening routing unclear | High | Add Security Audit as audit-only Hygiene variant |

## Design Decisions (User-Approved + Codex Review)

1. **Batch model:** Per-item triage with root-cause consolidation — scan for shared root causes first, then triage remaining items independently, then group by dependencies
2. **Scenario expansion:** Add Migration and Performance as first-class scenarios (7 total). Security hardening splits into two routes: "security audit" (findings-only, new Hygiene-Audit variant) and "security hardening" (Hygiene with mandatory early `/cso`, dedup later steps)
3. **Knowledge Capture:** Light/Full split (not three weight classes)
4. **Triage tiebreaker:** Risk sets the floor; decision density can escalate but never downgrade. A 1-file auth change is Heavy (risk). A 20-file redesign with architecture decisions is Heavy (decision density). A 20-file trivial rename is Light (low risk, low decision density).

## Approach

Clean rewrite of `skill.md`. Same overall structure with all 12 gaps integrated from the start.

**Risk assessment:** This skill is the router for non-trivial work across Ark projects. A bad rewrite affects downstream scenario detection, weight classification, and skill chain output for every task. The change is lower risk than a code rewrite (no compilation, no runtime), but the smoke tests in the Verification section are **required** — not optional — before declaring the rewrite complete. Preserves all working parts (Project Discovery, existing chains that are correct).

---

## Spec: New Skill Structure

### Frontmatter

Update the `description` field to include new trigger patterns:

```yaml
---
name: ark-workflow
description: >-
  Task triage and skill chain orchestration. Use when starting any non-trivial
  task to determine the optimal workflow. Triggers on "build", "create", "fix",
  "bug", "ship", "deploy", "document", "cleanup", "refactor", "audit",
  "upgrade", "migrate", "slow", "optimize", "benchmark", "new feature",
  "investigate". Do NOT use for trivial single-file changes with no ambiguity.
---
```

### Section 1: Header + Purpose

No change. Keep the one-liner: "Triage any task into a weight class, detect the scenario, and output the optimal skill chain."

### Section 2: Project Discovery

**No structural changes.** Keep the exact same context-discovery pattern and bash detection script.

**One addition:** After step 7 (HAS_VAULT check), add early exits:

```markdown
8. **Early exits** — check prerequisites before proceeding:
   - If the user's request is clearly Knowledge Capture AND `HAS_VAULT=false`:
     stop and tell them to run `/wiki-setup` first. Do not proceed to triage.
```

### Section 3: Scenario Detection (5 → 7 scenarios)

New table:

| Scenario | Trigger Patterns | Description |
|----------|-----------------|-------------|
| **Greenfield** | "build", "create", "add feature", "new component", "implement" | Building something new from scratch |
| **Bugfix** | "fix", "bug", "broken", "error", "investigate", "not working", "crash" | Something's broken, find and fix it |
| **Ship** | "ship", "deploy", "push", "PR", "merge", "release", "cherry-pick" | Getting code reviewed, merged, deployed |
| **Knowledge Capture** | "document", "vault", "catch up", "knowledge", "wiki", "update docs" | Catch up the vault with what's happened |
| **Hygiene** | "cleanup", "refactor", "audit", "hygiene", "dead code", "maintenance" | Cleanup, refactor, code quality |
| **Migration** | "upgrade", "migrate", "bump major", "framework upgrade", "version bump" | Upgrading dependencies, frameworks, or platform versions |
| **Performance** | "slow", "optimize", "latency", "benchmark", "profile", "performance" | Improving speed, reducing resource usage |

**Security routing — two distinct paths:**

1. **Security audit / review** (assessment only, no code changes expected): "security audit", "security review", "audit our X", "review the security of Y" → route to **Hygiene: Audit-Only** variant (new). Ends with findings report, no implementation or ship steps.

2. **Security hardening** (remediation expected): "harden", "fix security", "improve auth security", "address vulnerabilities" → route to **Hygiene** (Light/Medium/Heavy) with `/cso` as **mandatory step 1**.

   **Resolution rule — how mandatory early `/cso` is wired into the chain:**
   - Look up the standard Hygiene chain for the triaged weight (Light/Medium/Heavy)
   - **Prepend** `/cso` as the new step 1. All original steps shift down by 1.
   - **Dedup**: remove any later `/cso` step from the chain (whether unconditional like Hygiene Heavy's step 4 or conditional like "if security-relevant"). `/cso` runs exactly once per chain execution.
   - Present the resolved chain to the user with the `/cso` at step 1 and a note: "Security hardening detected — `/cso` promoted to step 1; later `/cso` deduped."

If the user's intent is ambiguous between audit and hardening, ask:
> Are you asking for an audit (findings only) or hardening (findings + fixes + ship)?

**Multi-scenario resolution:** Keep existing rule (use primary scenario). Add: "If the prompt contains multiple numbered/bulleted items that span different scenarios, use Batch Triage instead."

**Updated disambiguation prompt:**

> What kind of task is this?
> A) Greenfield — building something new
> B) Bugfix — something's broken
> C) Ship — getting code out the door
> D) Knowledge Capture — documenting what happened
> E) Hygiene — cleanup, refactor, audit
> F) Migration — upgrading dependencies or platforms
> G) Performance — optimizing speed or resources

### Section 4: Triage (risk-primary with escalation)

**Rule:** Risk sets the floor. Decision density can escalate but never downgrade. File count and duration are informational context only.

**Step 1 — Classify by risk:**

| Risk | Floor Class | Signals |
|------|-------------|---------|
| **Low** | Light | Internal changes, non-breaking, no auth/data/infra touch points |
| **Moderate** | Medium | API surface changes, schema modifications, external integration changes |
| **High** | Heavy | Auth/permissions, data migrations, infrastructure, secrets, breaking changes to shared interfaces |

**Step 2 — Escalate by decision density:**

| Decision density | Effect |
|------------------|--------|
| Obvious fix, clear path | No change — stay at risk floor |
| Some trade-offs to consider | Escalate Light → Medium (if currently Light) |
| Architecture decisions required | Escalate to Heavy (regardless of current floor) |

**Rule:** Escalation only increases the class. A Heavy risk stays Heavy even if the fix is obvious. A Light risk with architecture decisions becomes Heavy.

**Examples:**

| Task | Risk | Decision Density | Result |
|------|------|------------------|--------|
| Rename 20 test utility functions | Low | Obvious | **Light** (low risk, no decisions) |
| Fix one auth validation function | High | Obvious | **Heavy** (risk floor) |
| Redesign internal caching layer (20 files) | Low | Architecture | **Heavy** (escalated by decision density) |
| Add logging to 15 modules | Low | Obvious | **Light** (low risk, no decisions) |
| Add feature flag infrastructure | High | Trade-offs | **Heavy** (risk floor) |
| Refactor state management across modules | Low | Trade-offs | **Medium** (escalated from Light) |

**Context signals** (informational, not classification inputs — show to user for transparency):

| Signal | Description |
|--------|-------------|
| File count | 1-3 (small), 4-10 (moderate), 10+ (large) |
| Duration estimate | Quick (<30min), moderate (hours), extended (half-day+) |

**Disambiguation prompts:**

If risk is unclear:
> How risky is this task?
> A) Low risk — internal, non-breaking, no auth/data/infra
> B) Moderate risk — API changes, schema changes, external integrations
> C) High risk — auth, data migration, infra, secrets, permissions

If decision density is unclear:
> How many trade-offs or architecture decisions does this involve?
> A) Obvious — clear path, no real choices
> B) Some trade-offs — a few decisions to make
> C) Architecture decisions — multiple significant choices, design work needed

**Scenarios that skip triage:**
- Ship — no weight class needed
- Knowledge Capture — uses Light/Full split (see below), not the risk+density triage

**Knowledge Capture classification:** Light if syncing recent changes or updating a few pages. Full if catching up after extended period, rebuilding tags, or ingesting external documents.

### Section 5: Batch Triage (new section)

**Trigger:** Activated when the user's prompt describes multiple distinct executable tasks. This includes:
- Numbered lists ("1. Fix X, 2. Fix Y")
- Bulleted lists
- Prose with multiple distinct requests ("fix the auth bug and also clean up the dead code")
- Tech debt/cleanup batches

**Not a batch:** Requirement lists, acceptance criteria, or nested sub-steps within a single task. If the "items" describe one logical unit of work (e.g., "add dark mode: toggle component, theme provider, CSS vars"), treat as a single task, not a batch. When uncertain, ask:
> Are these separate tasks to triage individually, or one task with multiple sub-steps?

**Algorithm:**

**Step 0 — Root cause consolidation (new):**
Before per-item triage, scan the items for shared root causes. If multiple items appear to be symptoms of one underlying issue, tell the user:

> Items #X, #Y, and #Z look like symptoms of a shared root cause. Would you like to consolidate them into a single investigation, or triage them separately?

Only consolidate if the user confirms. Do not auto-consolidate — the user's framing matters.

**Step 1 — Per-item scenario + weight classification:**

For each remaining item:
1. Determine scenario (from the 7-scenario table)
2. Classify weight:
   - Ship items: **no weight class** (use standalone Ship chain)
   - Knowledge Capture items: **Light or Full** (per Knowledge Capture rules)
   - All other scenarios: **Light/Medium/Heavy** (per risk-primary triage)
3. Present as a summary table

**Step 2 — Dependency detection (heuristic):**

Based on item descriptions and project knowledge, flag possible dependencies:
- Items that describe the same component/file/module (possible shared code)
- Items where one describes output/state that another consumes (logical dependency)
- Items with different risk levels touching the same area (risk isolation — don't ship together)

**Important:** This is heuristic based on item descriptions, not code analysis. Tell the user when flagging: "I think #X depends on #Y because they both touch the auth middleware — confirm before ordering." Ask for confirmation on uncertain dependencies before committing to an execution order.

**Step 3 — Grouping:**

Organize items into execution groups:
- **Parallel groups:** Independent items with the same scenario + weight class
- **Sequential chains:** Items with confirmed dependencies (A before B)
- **Separate session recommended:** Heavy items when the rest of the batch is Light — suggest the user split into separate sessions

**Step 4 — Per-group chains:**

For each group, look up the skill chain:
- Ship items → Ship chain (unchanged)
- Knowledge Capture items → Knowledge Capture Light or Full
- Scenario-and-weight items → matching scenario chain

Present the full execution plan.

**Example output format:**

```
## Batch Triage

| # | Item | Scenario | Weight | Notes |
|---|------|----------|--------|-------|
| 1 | Transaction isolation | Bugfix | Medium | Touches DB client |
| 2 | Ghost pipeline runs | Bugfix | Light | Orchestrator startup |
| 3 | Payload drop | Bugfix | Medium | Invoke endpoint |
| 4 | Retry storms | Bugfix | Heavy | Process lifecycle |
| 5 | MCP ClosedResourceError | Bugfix | Light | Graceful shutdown |
| 6 | Update README | Knowledge Capture | Light | - |
| 7 | Cherry-pick hotfix | Ship | - | Standalone ship |

**Root cause scan:** No shared root causes detected.

**Possible dependencies (please confirm):**
- #4 may depend on #1 (both touch process/DB lifecycle)
- #6 is independent

**Execution plan:**
- Group A (parallel): #2, #5 — Light Bugfix chain
- Group B (sequential): #3 — Medium Bugfix chain
- Group C (pending dep confirmation): #1 → #4 — Heavy Bugfix
- Standalone: #7 — Ship chain
- Standalone: #6 — Knowledge Capture Light

**Session recommendation:** Groups A+B and standalones in this session. Group C in a fresh session if Heavy (architecture work may require design phase).
```

### Section 5.5: Continuity — Task Tracking + Chain State File (new)

**Problem:** `/ark-workflow` outputs a chain and exits. Subsequent skills run independently. Without tracking, the agent loses position across context compaction or session breaks, and the user has no in-session reminder of the next step.

**Solution:** Hybrid continuity — TodoWrite tasks for interactive reminders + chain state file for durability.

**What `/ark-workflow` does at the end of Step 6 (Present the Resolved Chain):**

1. **Create TodoWrite tasks** for each step in the chain (or each group in a batch). Each task has:
   - `subject`: The skill name (e.g., `/investigate — root cause analysis`)
   - `description`: The step's purpose + any inline conditions
   - First task marked `in_progress`, all others `pending`

2. **Write chain state file** to `.ark-workflow/current-chain.md` at the project root:

```markdown
---
scenario: Bugfix
weight: Heavy
batch: false
created: 2026-04-10T03:00:00Z
discovery:
  HAS_UI: false
  HAS_VAULT: true
  HAS_STANDARD_DOCS: true
  HAS_CI: true
---

# Current Chain: Bugfix-Heavy

## Steps

1. [ ] `/investigate` — root cause analysis
2. [ ] Re-triage if deeper than expected
3. [ ] `/test-driven-development` — failing test
4. [ ] Fix
5. [ ] `/ark-code-review --thorough` + `/codex` → `/simplify`
6. [ ] `/qa` — skipped (no UI)
7. [ ] `/cso` — skipped (not security-relevant)
8. [ ] `/ship` → `/land-and-deploy`
9. [ ] `/canary` (if deploy risk)
10. [ ] `/wiki-update`
11. [ ] `/wiki-ingest` (if new concept)
12. [ ] `/cross-linker`
13. [ ] Session log
14. [ ] `/claude-history-ingest`

## Notes

(Agent appends notes as steps complete — root cause findings, test names, PR URL, etc.)
```

3. **Add a `.gitignore` entry** for `.ark-workflow/` so chain state doesn't pollute the repo (the user's ongoing work, not code).

4. **Append this reminder to the chain output presented to the user:**

> **Continuity:**
> - Tasks created in TodoWrite for each step
> - Chain state saved to `.ark-workflow/current-chain.md`
> - After completing each step, the agent will announce `Next: [skill]` and update the task + chain file
> - If context is lost, read the chain file to resume

5. **Instruction to the agent (embedded in the chain output):**

> **After completing each step in this chain:**
> 1. Check off the step in `.ark-workflow/current-chain.md` (change `[ ]` to `[x]`) and append any notes
> 2. Update the corresponding TodoWrite task to `completed`
> 3. Announce to the user: `Next: [next skill name] — [one-line purpose]`
> 4. Mark the next task as `in_progress`
> 5. If the chain is complete, **archive** `.ark-workflow/current-chain.md` to `.ark-workflow/archive/YYYY-MM-DD-[scenario].md` (do NOT delete — archives are the workflow history) and tell the user the workflow is done

**Batch Triage mode:** For batch output, write one section per group in the chain file:

```markdown
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
```

Tasks in TodoWrite are grouped with a parent task per group and sub-tasks per item step.

**Cross-session continuity (new sessions picking up an in-progress chain):**

TodoWrite tasks are session-scoped and do NOT persist across sessions. Only `.ark-workflow/current-chain.md` persists on disk. To make cross-session continuity work:

**1. Session start check (automatic):**
Every time a session starts in a project, the agent should check for `.ark-workflow/current-chain.md`. This applies whether or not `/ark-workflow` was explicitly invoked. Add to the Routing Rules Template (Section 12) so projects can wire this up via their CLAUDE.md:

```markdown
## Ark Workflow — session resume

At the start of every session in this project, check for `.ark-workflow/current-chain.md`.
If it exists and contains unchecked steps, read it and announce:

"Found an in-progress ark-workflow chain:
- Scenario: [scenario]/[weight]
- Progress: step X of Y complete
- Next: [next skill name]
- Started: [timestamp from frontmatter]

Continue from here? (Or archive this chain if it's stale / abandoned.)"

Then rehydrate TodoWrite tasks from the unchecked items in the file.
```

**2. Rehydrate TodoWrite tasks:**
When resuming a chain from the file, create new TodoWrite tasks for each unchecked step (`[ ]`). Mark the first unchecked step as `in_progress`. Completed steps (`[x]`) do not get recreated as tasks — they're history, not work.

**3. Handle intentional session handoffs:**
The chain file distinguishes between "chain paused mid-work" (user closed Claude) and "intentional handoff" (medium+ design phase end-of-session marker). The handoff marker is recorded in the chain file:

```markdown
---
scenario: Greenfield
weight: Heavy
batch: false
created: 2026-04-10T03:00:00Z
handoff_marker: after-step-5   # set when the chain hits a design→implementation break
handoff_instructions: "Read spec at docs/superpowers/specs/2026-04-10-oauth-design.md"
---
```

On session start, if `handoff_marker` is set AND the marked step is `[x]` (completed), announce:
> "You're in Session 2 of a Heavy Greenfield. Design phase complete. Next: `/executing-plans` with the spec at [handoff_instructions path]."

**4. Stale chain detection:**
If the chain file is older than 7 days, flag it as potentially stale:
> "Found an ark-workflow chain from [age] ago. Is this still active, or should I archive it to `.ark-workflow/archive/`?"

Never auto-delete — always ask. The user may have been on vacation.

**5. Context recovery (in-session, after compaction):**
If context compaction occurred mid-chain, the TodoWrite tasks survive but the rich chain context may be lost. The agent should re-read `.ark-workflow/current-chain.md` to refresh its understanding before continuing.

**Context recovery (catch-all):** At the start of any session in this project, if `.ark-workflow/current-chain.md` exists, the agent should read it and announce:
> "Found an in-progress `/ark-workflow` chain: [scenario]/[weight], step X of Y (`[next step]`). Continue from here?"

### Section 6: Workflow Steps (updated)

```markdown
### Step 1: Run Project Discovery
Execute the Project Discovery section. Record: HAS_UI, HAS_VAULT, HAS_STANDARD_DOCS, HAS_CI.
Check early exits — if Knowledge Capture + no vault, stop here.

### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table.
If the prompt describes multiple distinct tasks (see Batch Triage trigger), go to Batch Triage instead of steps 3-6.
For security requests, use the two-path security routing (audit vs hardening).
If ambiguous, ask the disambiguation question.

### Step 3: Classify Weight
Classify using risk-primary triage with decision-density escalation.
Ship skips this step.
Knowledge Capture uses Light/Full split.
Hygiene audit-only uses the Audit-Only variant (no weight class).

### Step 4: Look Up Skill Chain
Find the matching chain using scenario + weight class.
If security hardening triggered mandatory early /cso, apply the dedup rule.

### Step 5: Resolve Conditions
Walk through the chain and resolve every conditional using Condition Resolution definitions.

### Step 6: Present the Resolved Chain
Output the numbered skill chain with all conditions resolved.
Include session handoff markers where applicable.

### Step 6.5: Activate Continuity (new)
- Create TodoWrite tasks for each step in the chain
- Write `.ark-workflow/current-chain.md` with the full chain state
- Add `.ark-workflow/` to `.gitignore` if not already present
- Embed the "after each step" reminder instructions in the output

### Step 7: Hand Off
The skill is done. The user or Claude follows the chain.
/ark-workflow does not invoke downstream skills itself.
After each step, the agent updates the chain file + task and announces the next step.
```

### Section 7: Skill Chains

#### Greenfield Feature

**Light** — unchanged except `/TDD` → `/test-driven-development`:

1. Implement directly
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

**Medium** — `/TDD` renamed:

*Session 1 — Design:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. Commit spec → **end session, start fresh for implementation**

*Session 2 — Implementation:*
4. Read spec from `docs/superpowers/specs/`
5. `/test-driven-development` — write tests first, implement against them
6. `/ark-code-review --quick` → `/simplify`
7. `/qa` (if UI)
8. `/cso` (if security-relevant)
9. `/ship` → `/land-and-deploy`
10. `/canary` (if deploy risk)

*Document:*
11. `/wiki-update` (if vault)
12. `/wiki-ingest` (if vault + new component needs its own page)
13. `/cross-linker` (if vault)
14. `/document-release` (if standard docs exist)
15. Session log

**Heavy** — `/TDD` renamed:

*Session 1 — Design & Planning:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. `/writing-plans` — break into phased implementation plan
4. `/codex` — review the plan
5. Commit spec + plan → **end session, start fresh for implementation**

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/test-driven-development` per step
8. `/subagent-driven-development` — parallelize independent modules
9. `/checkpoint` (optional — if pausing mid-implementation)
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
11. `/qa` (if UI)
12. `/design-review` (if UI)
13. `/cso` (if security-relevant)
14. `/ship` → `/land-and-deploy`
15. `/canary` (if deploy risk)

*Document:*
16. `/wiki-update` (if vault)
17. `/wiki-ingest` (if vault + new component needs its own page)
18. `/cross-linker` (if vault)
19. `/document-release` (if standard docs exist)
20. Session log
21. `/claude-history-ingest`

#### Bug Investigation & Fix

**Light** — unchanged except naming:

1. `/investigate` — root cause analysis
2. Fix directly
3. `/cso` (if security-relevant)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)
7. Session log (only if surprising root cause)

**Medium** — `/TDD` renamed:

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected
3. `/test-driven-development` — write a failing test that reproduces the bug
4. Fix
5. `/ark-code-review --quick` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

**Heavy** — `/TDD` renamed + session handoff added:

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected. **If investigation reveals architectural redesign is needed: `/checkpoint` findings, end session, start fresh with a design phase (pivot to Heavy Greenfield from step 1).**
3. `/test-driven-development` — write a failing test that reproduces the bug
4. Fix (structured, may require `/executing-plans`)
5. `/ark-code-review --thorough` + `/codex` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/wiki-ingest` (if vault + fix introduces a new concept)
12. `/cross-linker` (if vault)
13. Session log
14. `/claude-history-ingest`

#### Shipping & Deploying

Unchanged:

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

#### Knowledge Capture (Light/Full split — new)

Requires vault — if `HAS_VAULT=false`, tell the user to run `/wiki-setup` first. (This should already be caught by the early exit in Project Discovery.)

**Light** (syncing recent changes, updating a few pages):

1. `/wiki-update` — sync recent changes
2. `/cross-linker` (if vault)

**Full** (catching up after extended period, rebuilding tags, ingesting external docs):

1. `/wiki-status` — vault statistics
2. `/wiki-lint` — broken links, missing frontmatter, tag violations
3. `/wiki-update` — sync recent changes
4. `/wiki-ingest` — distill external documents if needed
5. `/cross-linker` — discover missing wikilinks
6. `/tag-taxonomy` — normalize tags
7. `/claude-history-ingest` — mine recent sessions
8. Session log

#### Codebase Hygiene (updated — `/investigate` added, `/TDD` renamed, Audit-Only added)

**Audit-Only** (new — for "audit", "review", "assess" requests with no remediation expected):

1. `/codebase-maintenance` — audit (or `/cso` if security audit)
2. Present findings report to the user
3. `/wiki-update` (if vault — to record findings)
4. **STOP** — do not implement, do not ship. Ask user: "Findings above. Do you want to create tickets via `/ark-tasknotes`, or proceed with fixes (I'll re-triage as Hygiene Light/Medium/Heavy)?"

**Light:**

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. Implement cleanup
4. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

**Medium:**

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
4. `/test-driven-development` — tests before restructuring
5. Implement cleanup
6. `/ark-code-review --quick` → `/simplify`
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault) + session log

**Heavy:**

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. **If audit + investigation reveals systemic issues requiring rewrite: escalate to Heavy Greenfield. `/checkpoint` findings, end session, start fresh with design phase.**
4. `/cso` — infrastructure, dependency, secrets audit (this IS the mandatory `/cso` run — no duplicate later)
5. `/test-driven-development` — tests before restructuring
6. Implement cleanup
7. `/ark-code-review --thorough` + `/codex` → `/simplify`
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault) + session log
11. `/claude-history-ingest`

**Dedup rule:** If security hardening triggers mandatory early `/cso` (before the chain starts), skip the conditional `/cso` inside the chain. `/cso` runs exactly once per chain execution.

#### Migration (new scenario)

**Light** (patch/minor version bumps, non-breaking dependency updates):

1. Read migration/upgrade guide for the dependency
2. Implement upgrade
3. Run tests — verify nothing broke
4. `/cso` (if security-relevant — major bumps, known CVEs)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

**Medium** (major version bumps, API changes required):

1. `/investigate` — audit current usage of the thing being migrated
2. Read migration guide, identify breaking changes
3. `/test-driven-development` — write tests for new API surface before migrating
4. Implement migration
5. `/ark-code-review --quick` → `/simplify`
6. `/cso` (if security-relevant)
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault)
10. Session log

**Heavy** (framework migrations, platform changes, database migrations):

*Session 1 — Planning:*
1. `/investigate` — audit all usage, map blast radius
2. `/brainstorming` — migration strategy (big bang vs incremental, feature flags, rollback plan)
3. `/codex` — review the migration plan
4. Commit migration plan → **end session, start fresh for implementation**

*Session 2 — Implementation:*
5. Read migration plan
6. `/test-driven-development` — tests for new platform/framework before migrating
7. Implement migration in stages (per the plan)
8. `/ark-code-review --thorough` + `/codex` → `/simplify`
9. `/cso` (if security-relevant)
10. `/ship` → `/land-and-deploy`
11. `/canary` — **mandatory for Heavy migrations** (not conditional)

*Document:*
12. `/wiki-update` (if vault)
13. `/wiki-ingest` (if vault + migration introduces new architecture concepts)
14. `/cross-linker` (if vault)
15. `/document-release` (if standard docs exist)
16. Session log
17. `/claude-history-ingest`

#### Performance (new scenario)

**Light** (single hotspot fix, obvious optimization):

1. `/investigate` — profile and identify the bottleneck
2. Fix the hotspot
3. Verify improvement (before/after timing or metric)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)

**Medium** (multiple hotspots, caching layer, query optimization):

1. `/investigate` — profile and identify bottlenecks
2. `/benchmark` — establish baseline metrics (if available)
3. `/test-driven-development` — write performance regression tests
4. Implement optimizations
5. `/benchmark` — verify improvement against baseline
6. `/ark-code-review --quick` → `/simplify`
7. `/cso` (if security-relevant — e.g., caching introduces data exposure)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

**Heavy** (architecture-level optimization, data layer redesign):

*Session 1 — Analysis & Planning:*
1. `/investigate` — deep profiling, identify systemic bottlenecks
2. `/benchmark` — comprehensive baseline
3. `/brainstorming` — optimization strategy (caching architecture, query redesign, etc.)
4. `/codex` — review the optimization plan
5. Commit plan → **end session, start fresh for implementation**

*Session 2 — Implementation:*
6. Read optimization plan
7. `/test-driven-development` — performance regression tests
8. Implement optimizations in stages
9. `/benchmark` — verify improvement per stage
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
11. `/cso` (if security-relevant)
12. `/ship` → `/land-and-deploy`
13. `/canary` — **mandatory for Heavy performance changes** (not conditional)

*Document:*
14. `/wiki-update` (if vault)
15. `/wiki-ingest` (if vault + optimization introduces new architecture)
16. `/cross-linker` (if vault)
17. Session log
18. `/claude-history-ingest`

### Section 8: Condition Resolution (tightened)

**Security-relevant triggers (for `/cso`):**
- Auth/permissions changes (both read AND write paths)
- Secrets handling (creation, rotation, storage, access patterns)
- Dependency upgrades: major/breaking version bumps, packages with known CVEs, packages adding native modules
- Data exposure: new PII access, new data flows, storage changes, new data processing
- Infrastructure changes: networking, DNS, tunnels, systemd units, container configs
- External API integrations: adding OR removing
- New internal APIs that other services will call

**Deploy risk triggers (for `/canary`):**
- All security-relevant triggers above
- Database schema changes (even non-breaking — adding nullable columns, indices)
- Cache invalidation changes
- Feature flag rollouts
- Config changes affecting production
- Changes to request handling or middleware ordering

**Investigation triggers (for `/investigate` in Hygiene) — NEW:**
- Broken functionality, silent failures, unexpected errors, crashes, or data loss — even when framed as "tech debt" or "cleanup"
- If the root cause isn't obvious from reading the code, investigate before fixing

**UI triggers (for `/qa`, `/design-review`):**
- Project has frontend dependencies (react, vue, svelte, next, angular, @remix, solid-js) AND the current task touches UI-facing code

**Standard docs trigger (for `/document-release`):**
- Project has README.md, ARCHITECTURE.md, CONTRIBUTING.md, or CHANGELOG.md outside of `docs/superpowers/`

### Section 9: Session Handoff (expanded)

For medium and heavy tasks with a design phase:
- Spec and plan are committed to `docs/superpowers/specs/` on the current branch
- Tell the user: **"Design phase complete. Start a fresh Claude Code session and reference the spec at `docs/superpowers/specs/<filename>.md` to begin implementation."**

**Additional handoff points (new):**
- **Heavy Bugfix, step 2:** If investigation reveals architectural redesign is needed → `/checkpoint` findings, recommend fresh session with design phase
- **Heavy Hygiene, step 3:** If audit + investigation reveals systemic issues requiring rewrite → escalate to Heavy Greenfield, `/checkpoint`, fresh session
- **Heavy Migration, step 4:** After migration plan is committed → session break before implementation
- **Heavy Performance, step 5:** After optimization plan is committed → session break before implementation
- **Any scenario, mid-implementation:** If the user explicitly asks to pause, or if output quality has degraded (repeated errors, hallucinated file paths, forgotten context) → suggest `/checkpoint`. Do NOT rely on tool-call counts as a trigger — that's an unreliable proxy.

### Section 10: Re-triage (expanded — weight AND scenario shifts)

If the task changes class mid-flight:

**Weight escalation** (existing — unchanged):
1. Stop at the current step
2. Re-classify using the triage table
3. Pick up the remaining phases from the new weight class
4. Don't restart — just add the phases you would have run

**Scenario shift** (new):
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

### Section 11: When Things Go Wrong

Keep all existing entries. Add:

- **Hygiene reveals bugs:** If `/codebase-maintenance` audit or `/investigate` uncovers bugs during a Hygiene workflow, re-triage the broken items as Bugfix (see Re-triage: Scenario shift). Fix bugs before continuing cleanup.
- **Migration breaks tests:** If a migration causes test failures, do NOT force the migration through. `/investigate` the failures — they may reveal undocumented dependencies. Fix or document before proceeding.
- **Batch item blocks other items:** If one item in a batch blocks others due to an unexpected dependency, re-order the execution plan. Flag the dependency to the user.

### Section 12: Routing Rules Template (updated for 7 scenarios + resume)

```markdown
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
6. If the chain is complete, move the file to `.ark-workflow/archive/[date]-[scenario].md`
```

---

## Verification

After implementing the rewrite:

1. **Structural check:** Read the new `skill.md` end-to-end. Verify every section header from this spec exists.
2. **Naming check:** `grep -c '/TDD' skills/ark-workflow/SKILL.md` should return 0. All instances should be `/test-driven-development`.
3. **Scenario count:** Verify 7 scenarios in the detection table.
4. **Chain count:** Verify chains exist for: Greenfield (L/M/H = 3), Bugfix (L/M/H = 3), Ship (1), Knowledge Capture (Light/Full = 2), Hygiene (Audit-Only/L/M/H = 4), Migration (L/M/H = 3), Performance (L/M/H = 3) = **19 chains total**.
5. **Batch Triage section:** Verify it exists with the 4-step algorithm and example output.
6. **Condition Resolution:** Verify "Investigation triggers" is listed as a new condition type.
7. **Session Handoff:** Verify Heavy Bugfix, Heavy Hygiene, Heavy Migration, and Heavy Performance all have explicit handoff guidance.
8. **Re-triage:** Verify both weight escalation and scenario shift are documented with examples.
9. **Security dedup:** Verify the `/cso` dedup rule is documented in both the security routing section and the Hygiene chain dedup rule.
10. **Risk+density triage:** Verify the triage table shows risk as floor + decision density as escalation (not risk-only). Verify the example table includes the "20-file trivial rename = Light" and "20-file internal redesign = Heavy" cases.
11. **Continuity mechanism:** Verify Section 5.5 exists with TodoWrite tasks, chain state file spec, gitignore instruction, and the after-each-step reminder protocol. Verify Step 6.5 is added to Workflow Steps.
12. **Cross-session continuity:** Verify Section 5.5 covers session-start check, TodoWrite rehydration, handoff markers, stale chain detection (>7 days), and context recovery after compaction.
13. **Routing Rules Template:** Verify the template includes both session-resume block AND new-task triage triggers, plus the "after each step" protocol.
14. **Smoke test:** Mentally run the three original user prompts (Session A/B/C) through the new skill and verify they produce correct triage. Also run a "security audit" and "security hardening" prompt to verify the two-path routing works.
15. **Cross-session smoke test:** Simulate ending a session mid-Heavy-Greenfield (step 4 of 21), opening a new session, and verify the agent reads the chain file and rehydrates tasks from step 5.

### Smoke Test: Session A (Data & Orchestrator)

Expected batch triage output:
| # | Item | Scenario | Risk | Class |
|---|------|----------|------|-------|
| 1 | Transaction isolation | Bugfix | Moderate | Medium |
| 2 | Ghost pipeline runs | Bugfix | Low | Light |
| 3 | Payload drop (ArkPoly-119) | Bugfix | Moderate | Medium |
| 4 | Retry storms (ArkPoly-120) | Bugfix | High | Heavy |
| 5 | MCP ClosedResourceError (ArkPoly-121) | Bugfix | Low | Light |

All correctly classified as Bugfix (not Hygiene), with per-item weight classes.

### Smoke Test: Session B (Dashboard & Infra)

Expected:
| # | Item | Scenario | Risk | Class |
|---|------|----------|------|-------|
| 1 | File permissions (root/strategist) | Bugfix | High | Heavy |
| 2 | SSE tunnel gap | Bugfix | Moderate | Medium |
| 3 | Dashboard blocking calls | Performance | Low | Light |

Mixed scenarios correctly detected. Item 3 routes to Performance, not Hygiene.

### Smoke Test: Session C (CI & Cleanup)

Expected:
| # | Item | Scenario | Weight | Notes |
|---|------|----------|--------|-------|
| 1 | Deploy script TS build (ArkPoly-129) | Bugfix | Medium | Broken behavior |
| 2 | ESLint no-explicit-any cleanup | Hygiene | Light | Pure cleanup |

Mixed scenarios. Item 1 is a Bugfix (broken behavior), item 2 is pure Hygiene.

### Smoke Test: Security Audit

Prompt: "Run a security audit on our auth module."

Expected:
- Scenario detection: security routing → **Hygiene: Audit-Only**
- Chain: `/cso` → findings report → `/wiki-update` → STOP (no implementation, no ship)
- `/cso` runs once (dedup rule not needed, no duplicate later steps)

### Smoke Test: Security Hardening

Prompt: "Harden our auth module against session hijacking."

Expected:
- Scenario detection: security routing → **Hygiene (Heavy)** with mandatory early `/cso`
- Weight class: Heavy (auth = high risk + architecture decisions likely)
- Chain: `/cso` (mandatory, step 1) → `/codebase-maintenance` → `/investigate` → ~~`/cso`~~ (deduped) → `/test-driven-development` → implement → thorough review → ship → canary → vault
- `/cso` runs exactly once

### Smoke Test: Decision-Density Escalation

Prompt: "Redesign the internal caching layer — rewrite how we cache DB query results across the orchestrator."

Expected:
- Scenario: Hygiene (refactor) — OR Greenfield if user explicitly says "redesign"
- Risk: Low (internal only, no auth/data/infra)
- Decision density: Architecture (rewriting a whole layer)
- Weight: **Heavy** (escalated by decision density from Light floor)
- Chain: Heavy Hygiene OR Heavy Greenfield

This verifies that the triage doesn't under-weight architecture work just because risk is low.
