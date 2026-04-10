---
name: ark-workflow
description: Task triage and skill chain orchestration. Use when starting any non-trivial task to determine the optimal workflow. Triggers on "build", "create", "fix", "bug", "ship", "deploy", "document", "cleanup", "refactor", "audit", "upgrade", "migrate", "slow", "optimize", "benchmark", "new feature", "investigate". Do NOT use for trivial single-file changes with no ambiguity.
---

# Ark Workflow

Triage any task into a weight class (light / medium / heavy), detect the scenario, and output the optimal skill chain. This is the entry point for all non-trivial work across Ark projects.

## Project Discovery

Follow the context-discovery pattern documented in this plugin's CLAUDE.md:

1. Read the `CLAUDE.md` in the current working directory
2. If it's a monorepo hub (contains a "Projects" table linking to sub-project CLAUDEs), follow the link for the active project based on your current working directory
3. Extract from the most specific CLAUDE.md:
   - Project name (from header or table)
   - Vault root (parent of project docs and TaskNotes)
   - Project docs path (from "Obsidian Vault" row)
   - TaskNotes path (from "Task Management" row)
4. If a required field is missing, note it — vault skills will be skipped for projects without vault configuration

5. Detect project characteristics:

```bash
# Has UI? Check for frontend indicators (any one is sufficient)
HAS_UI=false
if [ -f "package.json" ]; then
  grep -qE "react|vue|svelte|next|angular|@remix|solid-js" package.json 2>/dev/null && HAS_UI=true
fi
[ -f "tsconfig.json" ] && grep -q "jsx\|tsx" tsconfig.json 2>/dev/null && HAS_UI=true
echo "HAS_UI=$HAS_UI"

# Has standard docs outside docs/superpowers/?
HAS_STANDARD_DOCS=false
for f in README.md ARCHITECTURE.md CONTRIBUTING.md CHANGELOG.md; do
  [ -f "$f" ] && HAS_STANDARD_DOCS=true && break
done
echo "HAS_STANDARD_DOCS=$HAS_STANDARD_DOCS"

# Has vault? (extracted from CLAUDE.md in step 3 above)
# If vault root was found and directory exists: HAS_VAULT=true
# If no vault configured or directory missing: HAS_VAULT=false
echo "HAS_VAULT=$HAS_VAULT"

# Has CI/CD?
HAS_CI=false
[ -d ".github/workflows" ] || [ -f ".gitlab-ci.yml" ] || [ -f "Dockerfile" ] && HAS_CI=true
echo "HAS_CI=$HAS_CI"
```

6. Store these values for condition resolution in later steps.
7. If `HAS_VAULT=false`, tell the user: "No vault configured for this project. Vault skills (`/wiki-update`, `/wiki-ingest`, `/cross-linker`, `/wiki-lint`, etc.) will be skipped. Run `/wiki-setup` to initialize a vault if needed."

8. **Early exits** — check prerequisites before proceeding to triage:
   - If the user's request is clearly Knowledge Capture (matches "document", "vault", "catch up", "knowledge", "wiki") AND `HAS_VAULT=false`: stop and tell the user to run `/wiki-setup` first. Do not proceed to Step 2 (Scenario Detection).

## Scenario Detection

Identify which scenario applies based on the user's request. Ask if ambiguous.

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

1. **Security audit / review** (assessment only, no code changes expected): "security audit", "security review", "audit our X", "review the security of Y" → route to **Hygiene: Audit-Only** variant. Ends with findings report, no implementation or ship steps.

2. **Security hardening** (remediation expected): "harden", "fix security", "improve auth security", "address vulnerabilities" → route to **Hygiene** (Light/Medium/Heavy) with `/cso` as **mandatory step 1**.

   **How to wire the mandatory early `/cso` into the chain output (resolution rule):**
   a. Look up the standard Hygiene chain for the triaged weight (Light/Medium/Heavy)
   b. **Prepend** `/cso` as the new step 1. All original steps shift down by 1.
   c. **Dedup**: remove any later `/cso` step from the chain (whether unconditional like Hygiene Heavy's "step 4" or conditional like Hygiene Light's "if security-relevant"). `/cso` runs exactly once per chain execution.
   d. Present the resolved chain to the user with the `/cso` at step 1 and a note: "Security hardening detected — `/cso` promoted to step 1; later `/cso` deduped."

If the user's intent is ambiguous between audit and hardening, ask:
> Are you asking for an audit (findings only) or hardening (findings + fixes + ship)?

**Multi-scenario resolution:** If the user's request matches multiple scenarios (e.g., "fix this bug and ship it"), use the primary scenario (bugfix) — the ship phase is included in the bugfix workflow. If the prompt describes multiple distinct tasks (numbered, bulleted, or in prose), use Batch Triage instead (see below).

If no pattern matches clearly, ask:

> What kind of task is this?
> A) Greenfield — building something new
> B) Bugfix — something's broken
> C) Ship — getting code out the door
> D) Knowledge Capture — documenting what happened
> E) Hygiene — cleanup, refactor, audit
> F) Migration — upgrading dependencies or platforms
> G) Performance — optimizing speed or resources

## Triage

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
| Rename 20 test utility functions | Low | Obvious | **Light** |
| Fix one auth validation function | High | Obvious | **Heavy** (risk floor) |
| Redesign internal caching layer (20 files) | Low | Architecture | **Heavy** (escalated) |
| Add logging to 15 modules | Low | Obvious | **Light** |
| Add feature flag infrastructure | High | Trade-offs | **Heavy** (risk floor) |
| Refactor state management across modules | Low | Trade-offs | **Medium** (escalated) |

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

**Scenarios that skip the full triage:**
- Ship — no weight class needed
- Knowledge Capture — uses Light/Full split
- Hygiene Audit-Only — no weight class (it's always findings-only)

**Knowledge Capture classification:** Light if syncing recent changes or updating a few pages. Full if catching up after extended period, rebuilding tags, or ingesting external documents.

**Re-triage rule:** If a task reveals more complexity mid-flight (e.g., a "light" bug turns out to involve auth, or an investigation reveals architecture decisions are required), escalate to the appropriate class and pick up the remaining phases from there. Don't restart — just add the phases you would have run. If the scenario itself changes (e.g., Bugfix → Greenfield redesign), see the Re-triage section below for scenario shift handling.

## Workflow

This is the concrete algorithm. Follow these steps in order:

### Step 1: Run Project Discovery
Execute the Project Discovery section above. Record: `HAS_UI`, `HAS_VAULT`, `HAS_STANDARD_DOCS`, `HAS_CI`.

### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table. If ambiguous, ask the multiple-choice question.

### Step 3: Classify Weight
For scenarios that use weight classes (Greenfield, Bugfix, Hygiene), classify using the Triage table. Ship and Knowledge Capture skip this step.

### Step 4: Look Up Skill Chain
Find the matching chain in the Skill Chains section below using scenario + weight class.

### Step 5: Resolve Conditions
Walk through the chain and resolve every conditional:
- `(if UI)` → check `HAS_UI`. If false, output "Skipping `/qa` — no UI detected"
- `(if vault)` → check `HAS_VAULT`. If false, skip the step silently (vault skills are optional)
- `(if standard docs exist)` → check `HAS_STANDARD_DOCS`. If false, output "Skipping `/document-release` — no standard docs found"
- `(if security-relevant)` → evaluate against the security triggers listed in Condition Resolution
- `(if deploy risk)` → evaluate against the deploy risk triggers listed in Condition Resolution

### Step 6: Present the Resolved Chain
Output the numbered skill chain with all conditions resolved. Include the session handoff marker if applicable (medium+ design phase).

### Step 7: Hand Off
The skill is done. The user or Claude follows the chain, invoking each skill in order. `/ark-workflow` does not invoke downstream skills itself.

## Skill Chains

Based on the scenario and weight class, present the resolved skill chain below. Replace conditions with project-specific values from Project Discovery (e.g., replace "(if UI)" with "skipping — no UI detected" or "including — UI detected").

---

### Greenfield Feature

**Light** (rare for greenfield):

1. Implement directly
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

**Medium:**

*Session 1 — Design:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. Commit spec → **end session, start fresh for implementation**

*Session 2 — Implementation:*
4. Read spec from `docs/superpowers/specs/`
5. `/TDD` — write tests first, implement against them
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

**Heavy:**

*Session 1 — Design & Planning:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. `/writing-plans` — break into phased implementation plan
4. `/codex` — review the plan
5. Commit spec + plan → **end session, start fresh for implementation**

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/TDD` per step
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

---

### Bug Investigation & Fix

**Light:**

1. `/investigate` — root cause analysis
2. Fix directly
3. `/cso` (if security-relevant)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)
7. Session log (only if surprising root cause)

**Medium:**

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected
3. `/TDD` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix
5. `/ark-code-review --quick` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

**Heavy:**

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected
3. `/TDD` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
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

---

### Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

---

### Knowledge Capture

*Catch up the vault with what's happened. No weight class needed. Requires vault — if `HAS_VAULT=false`, tell the user to run `/wiki-setup` first.*

1. `/wiki-status` — vault statistics
2. `/wiki-lint` — broken links, missing frontmatter, tag violations
3. `/wiki-update` — sync recent changes
4. `/wiki-ingest` — distill external documents if needed
5. `/cross-linker` — discover missing wikilinks
6. `/tag-taxonomy` — normalize tags
7. `/claude-history-ingest` — mine recent sessions
8. Session log

---

### Codebase Hygiene

**Light:**

1. `/codebase-maintenance` — audit
2. Implement cleanup
3. `/cso` (if security-relevant)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)

**Medium:**

1. `/codebase-maintenance` — audit
2. `/cso` (if security-relevant)
3. `/TDD` — tests before restructuring
4. Implement cleanup
5. `/ark-code-review --quick` → `/simplify`
6. `/ship` → `/land-and-deploy`
7. `/canary` (if deploy risk)
8. `/wiki-update` (if vault) + session log

**Heavy:**

1. `/codebase-maintenance` — audit
2. `/cso` — infrastructure, dependency, secrets audit
3. `/TDD` — tests before restructuring
4. Implement cleanup
5. `/ark-code-review --thorough` + `/codex` → `/simplify`
6. `/ship` → `/land-and-deploy`
7. `/canary` (if deploy risk)
8. `/wiki-update` (if vault) + session log
9. `/claude-history-ingest`

---

## Condition Resolution

When presenting a skill chain, resolve all conditions using Project Discovery values. Present the chain with conditions already evaluated:

**Security-relevant triggers (for `/cso`):**
auth/permissions changes, secrets handling, dependency upgrades, data exposure risks, infrastructure changes, new external API integrations.

**Deploy risk triggers (for `/canary`):**
config changes affecting production, infra changes, auth/permissions changes, data migrations, dependency upgrades with breaking changes.

**UI triggers (for `/qa`, `/design-review`):**
Project has frontend dependencies (react, vue, svelte, next, angular) AND the current task touches UI-facing code.

**Standard docs trigger (for `/document-release`):**
Project has README.md, ARCHITECTURE.md, CONTRIBUTING.md, or CHANGELOG.md outside of `docs/superpowers/`.

**Example resolved output:**

> **Your skill chain (Greenfield, Medium):**
> 1. `/brainstorming` — explore intent, write spec
> 2. `/codex` — review spec
> 3. Commit spec → **start fresh session**
> 4. `/executing-plans` with `/TDD` per step
> 5. `/ark-code-review --quick` → `/simplify`
> 6. Skipping `/qa` — no UI detected
> 7. Skipping `/cso` — no security-relevant changes
> 8. `/ship` → `/land-and-deploy`
> 9. Skipping `/canary` — no deploy risk
> 10. `/wiki-update`
> 11. `/wiki-ingest` — if new component needs a vault page
> 12. `/cross-linker`
> 13. Skipping `/document-release` — no standard docs found
> 14. Session log

## Session Handoff

For medium and heavy tasks with a design phase:

- Spec and plan are committed to `docs/superpowers/specs/` on the current branch
- Tell the user: **"Design phase complete. Start a fresh Claude Code session and reference the spec at `docs/superpowers/specs/<filename>.md` to begin implementation."**
- If heavy and pausing mid-implementation: suggest `/checkpoint` to save working state

## When Things Go Wrong

If a step fails mid-workflow:

- **Failed QA:** fix bugs in the current session, re-run `/qa` to verify, re-run `/ark-code-review` if fixes are substantial
- **Failed deploy:** check CI logs for the failure. If test failure: fix and re-run `/ship`. If infra issue: investigate before retrying. Never force-merge past failing CI.
- **Review disagreement (`/ark-code-review` vs `/codex`):** read both opinions — they see different things. If both flag the same area, it's almost certainly real. If they disagree, use your judgment. Document the resolution in the session log.
- **Flaky tests:** do not skip or retry blindly — `/investigate` the flake. If known and unrelated to your changes, note it and proceed. If new, treat as a bug.
- **Spec invalidated during implementation:** stop implementing, update the spec, re-run `/codex` review on the updated spec, resume from the updated spec (this is a re-triage moment)
- **Canary failure:** investigate the specific failure signal. If it's your change: rollback or hotfix (new light-class bug cycle). If pre-existing: document and proceed.
- **Vault tooling failure:** not blocking — don't let a `/wiki-update` failure hold up a ship. Note the failure, fix it in the next Knowledge Capture cycle.

## Re-triage

If the task changes class mid-flight (a "light" bug that turns out to involve auth, a "medium" feature that needs architecture decisions):

1. Stop at the current step
2. Re-classify using the triage table
3. Pick up the remaining phases from the new weight class
4. Don't restart — just add the phases you would have run

## Routing Rules Template

Projects can add this block to their CLAUDE.md to auto-trigger `/ark-workflow`:

`````markdown
## Skill routing — Ark Workflow

When starting any non-trivial task, invoke `/ark-workflow` first to triage and get the
skill chain. Pattern triggers:

- "build", "create", "add feature", "new component" → /ark-workflow (greenfield)
- "fix", "bug", "broken", "error", "investigate" → /ark-workflow (bugfix)
- "ship", "deploy", "push", "PR", "merge" → /ark-workflow (ship)
- "document", "vault", "catch up", "knowledge" → /ark-workflow (knowledge capture)
- "cleanup", "refactor", "audit", "hygiene", "dead code" → /ark-workflow (hygiene)

For trivial tasks (single obvious change, no ambiguity), skip triage and work directly.
`````

To add routing to a new project, copy the block above into the project's CLAUDE.md. The `/ark-workflow` skill is already available globally via the ark-skills plugin.
