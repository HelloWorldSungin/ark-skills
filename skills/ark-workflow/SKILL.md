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
Check early exits — if the user's request is clearly Knowledge Capture AND `HAS_VAULT=false`, stop and tell the user to run `/wiki-setup` first.

### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table. If the prompt describes multiple distinct tasks (see Batch Triage trigger), read `references/batch-triage.md` and follow that algorithm instead of Steps 3-6. For security requests, use the two-path security routing (audit vs hardening). If ambiguous, ask the disambiguation question.

### Step 3: Classify Weight
Classify using risk-primary triage with decision-density escalation. Ship skips this step. Knowledge Capture uses Light/Full split. Hygiene Audit-Only has no weight class.

### Step 4: Look Up Skill Chain
Read `chains/{scenario}.md` (e.g., `chains/bugfix.md`). Each chain file contains sections for the applicable weight variants — Light/Medium/Heavy, or Light/Full for Knowledge Capture, or Audit-Only/Light/Medium/Heavy for Hygiene. Select the section matching your triaged weight class.

**Filename mapping:** `greenfield.md`, `bugfix.md`, `ship.md` (standalone — no weight class), `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`.

If security hardening triggered mandatory early `/cso`, apply the Dedup rule documented at the bottom of `chains/hygiene.md`.

### Step 5: Resolve Conditions
Walk through the chain and resolve every conditional using Condition Resolution definitions:
- `(if UI)` → check `HAS_UI`. If false, output "Skipping `/qa` — no UI detected"
- `(if vault)` → check `HAS_VAULT`. If false, skip the step silently
- `(if standard docs exist)` → check `HAS_STANDARD_DOCS`. If false, output "Skipping `/document-release` — no standard docs found"
- `(if security-relevant)` → evaluate against the security triggers in Condition Resolution
- `(if deploy risk)` → evaluate against the deploy risk triggers in Condition Resolution
- `(if any item involves broken/unexpected behavior)` → evaluate against the investigation triggers in Condition Resolution

### Step 6: Present the Resolved Chain
Output the numbered skill chain with all conditions resolved. Include the session handoff marker if applicable.

### Step 6.5: Activate Continuity
- Create TodoWrite tasks for each step in the resolved chain
- Write `.ark-workflow/current-chain.md` at project root with this frontmatter:

  ---
  scenario: {scenario}
  weight: {weight}
  batch: false
  created: {ISO-8601 timestamp}
  handoff_marker: null
  handoff_instructions: null
  ---
  # Current Chain: {scenario}-{weight}
  ## Steps
  [numbered checklist of chain steps, each as `- [ ]`]
  ## Notes

- Add `.ark-workflow/` to `.gitignore` if not already present
- After each step: check off the step in the file (`[ ]` → `[x]`), update the TodoWrite task to `completed`, announce `Next: [skill] — [purpose]`, mark next task `in_progress`
- For batch-mode chain file format, cross-session resume, `handoff_marker` semantics, stale-chain detection, and compaction recovery: see `references/continuity.md`

### Step 7: Hand Off
The skill is done. The user or Claude follows the chain, invoking each skill in order. `/ark-workflow` does not invoke downstream skills itself. After each step, the agent updates the chain file + task and announces the next step.

## Condition Resolution

When presenting a skill chain, resolve all conditions using Project Discovery values. Present the chain with conditions already evaluated.

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

**Investigation triggers (for `/investigate` in Hygiene):**
- Broken functionality, silent failures, unexpected errors, crashes, or data loss — even when framed as "tech debt" or "cleanup"
- If the root cause isn't obvious from reading the code, investigate before fixing

**UI triggers (for `/qa`, `/design-review`):**
- Project has frontend dependencies (react, vue, svelte, next, angular, @remix, solid-js) AND the current task touches UI-facing code

**Standard docs trigger (for `/document-release`):**
- Project has README.md, ARCHITECTURE.md, CONTRIBUTING.md, or CHANGELOG.md outside of `docs/superpowers/`

## When Things Change

- **Mid-flight re-triage** (weight escalation or scenario shift): stop at the current step, reclassify using the Triage section above, pick up the remaining phases from the new class. For scenario-shift pivot examples, see `references/troubleshooting.md`.
- **Design-phase session handoffs**: chain files specify inline `handoff_marker` values where applicable. For per-scenario handoff points and guidance on when to break sessions mid-implementation, see `references/troubleshooting.md`.
- **Step failure or unexpected state**: see `references/troubleshooting.md` for per-failure guidance (failed QA, failed deploy, review disagreement, flaky tests, spec invalidation, canary failure, vault tooling failure, hygiene reveals bugs, migration breaks tests, batch item blocks others).

## Routing Rules Template

See `references/routing-template.md` for the copy-paste block to add to project CLAUDE.md files. (Not loaded at runtime — this is human-only documentation.)

## File Map

**Chain files (`chains/`)** — loaded once per triage after scenario detection:
- `chains/greenfield.md`, `chains/bugfix.md`, `chains/ship.md`, `chains/knowledge-capture.md`, `chains/hygiene.md`, `chains/migration.md`, `chains/performance.md`

**References (`references/`)** — loaded only when their trigger fires:
- `batch-triage.md` — multi-item algorithm (trigger: Step 2 multi-item detection)
- `continuity.md` — batch/resume/handoff/stale/compaction protocols (trigger: pay-per-use branches of Step 6.5)
- `troubleshooting.md` — re-triage, handoff details, failure recovery (trigger: mid-flight events)
- `routing-template.md` — CLAUDE.md copy-paste block (trigger: never runtime)
