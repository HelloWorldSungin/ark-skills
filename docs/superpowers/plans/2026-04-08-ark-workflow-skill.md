# Ark Workflow Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `/ark-workflow`, a new skill that triages tasks into weight classes and outputs the optimal skill chain per scenario.

**Architecture:** Single SKILL.md file following the Ark context-discovery pattern. The skill is an interactive orchestrator — it asks questions to detect scenario and weight class, resolves project-specific conditions (vault, UI, standard docs), then outputs an ordered skill chain. No code, no state, no downstream invocation.

**Tech Stack:** Markdown (SKILL.md), bash (project discovery commands), YAML (frontmatter)

---

### Task 1: Create the SKILL.md frontmatter and Project Discovery section

**Files:**
- Create: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p skills/ark-workflow
```

- [ ] **Step 2: Write the frontmatter and Project Discovery section**

Create `skills/ark-workflow/SKILL.md` with this content:

```markdown
---
name: ark-workflow
description: Task triage and skill chain orchestration. Use when starting any non-trivial task to determine the optimal workflow. Triggers on "build", "create", "fix", "bug", "ship", "deploy", "document", "cleanup", "refactor", "audit", "new feature", "investigate". Do NOT use for trivial single-file changes with no ambiguity.
---

# Ark Workflow

Triage any task into a weight class (light / medium / heavy), detect the scenario, and output the optimal skill chain. This is the entry point for all non-trivial work across Ark projects.

## Project Discovery

1. Read the current project's CLAUDE.md to find:
   - Project name
   - Vault path (if configured)
   - Task prefix (if configured)
2. Detect project characteristics:

\`\`\`bash
# Has UI? Check for frontend indicators
ls package.json tsconfig.json 2>/dev/null && grep -l "react\|vue\|svelte\|next\|angular" package.json 2>/dev/null && echo "HAS_UI=true" || echo "HAS_UI=false"

# Has standard docs outside docs/superpowers/?
HAS_DOCS=false
for f in README.md ARCHITECTURE.md CONTRIBUTING.md; do
  [ -f "$f" ] && HAS_DOCS=true && break
done
# Exclude docs/superpowers/ from consideration
echo "HAS_STANDARD_DOCS=$HAS_DOCS"

# Has vault?
HAS_VAULT=false
VAULT_PATH=""
# Read from CLAUDE.md Project Configuration table
grep -A1 "Obsidian Vault" CLAUDE.md 2>/dev/null | grep -oP '`[^`]+`' | tr -d '`' | while read p; do
  [ -d "$p" ] && echo "HAS_VAULT=true" && echo "VAULT_PATH=$p"
done
[ "$HAS_VAULT" = "false" ] && echo "HAS_VAULT=false"

# Has CI/CD?
HAS_CI=false
[ -d ".github/workflows" ] || [ -f ".gitlab-ci.yml" ] || [ -f "Dockerfile" ] && HAS_CI=true
echo "HAS_CI=$HAS_CI"
\`\`\`

3. Store these values for condition resolution in later steps.
```

- [ ] **Step 3: Verify the file was created**

```bash
head -20 skills/ark-workflow/SKILL.md
```

Expected: frontmatter with name `ark-workflow` and the Project Discovery section.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add SKILL.md with frontmatter and project discovery"
```

---

### Task 2: Add the Scenario Detection section

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the Scenario Detection section**

Add after the Project Discovery section:

```markdown
## Scenario Detection

Identify which scenario applies based on the user's request. Ask if ambiguous.

| Scenario | Trigger Patterns | Description |
|----------|-----------------|-------------|
| **Greenfield** | "build", "create", "add feature", "new component", "implement" | Building something new from scratch |
| **Bugfix** | "fix", "bug", "broken", "error", "investigate", "not working", "crash" | Something's broken, find and fix it |
| **Ship** | "ship", "deploy", "push", "PR", "merge", "release", "cherry-pick" | Getting code reviewed, merged, deployed |
| **Knowledge Capture** | "document", "vault", "catch up", "knowledge", "wiki", "update docs" | Catch up the vault with what's happened |
| **Hygiene** | "cleanup", "refactor", "audit", "hygiene", "dead code", "maintenance", "security audit" | Cleanup, refactor, security audit |

If the user's request matches multiple scenarios (e.g., "fix this bug and ship it"), use the primary scenario (bugfix) — the ship phase is included in the bugfix workflow.

If no pattern matches clearly, ask:

> What kind of task is this?
> A) Greenfield — building something new
> B) Bugfix — something's broken
> C) Ship — getting code out the door
> D) Knowledge Capture — documenting what happened
> E) Hygiene — cleanup, refactor, audit
```

- [ ] **Step 2: Verify the section was appended**

```bash
grep -c "Scenario Detection" skills/ark-workflow/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add scenario detection section"
```

---

### Task 3: Add the Triage System section

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the Triage System section**

Add after Scenario Detection:

```markdown
## Triage

Classify the task as **light**, **medium**, or **heavy**. **Risk is the primary signal** — a one-file auth change is heavy regardless of file count.

| Factor | Light | Medium | Heavy |
|--------|-------|--------|-------|
| **Risk** | Low (internal, non-breaking) | Moderate (API changes, schema) | High (infra, auth, data migration, secrets, permissions) |
| **Decision density** | Obvious fix | Some trade-offs | Architecture choices |
| **Files touched** | 1-3 | 4-10 | 10+ |
| **Duration** | < 30 min | 30 min - few hours | Half day+ |
| **Has UI?** | No | Maybe | Yes, user-facing changes |

If unsure, ask:

> How would you classify this task?
> A) Light — quick fix, 1-3 files, low risk
> B) Medium — some trade-offs, moderate scope
> C) Heavy — architecture decisions, high risk, or large scope

**Re-triage rule:** If a task reveals more complexity mid-flight (e.g., a "light" bug turns out to involve auth), escalate to the appropriate class and pick up the remaining phases from there. Don't restart — just add the phases you would have run.
```

- [ ] **Step 2: Verify**

```bash
grep -c "## Triage" skills/ark-workflow/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add triage system section"
```

---

### Task 4: Add the Skill Chain Generator — Greenfield scenario

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the Skill Chains header and Greenfield chain**

Add after Triage:

```markdown
## Skill Chains

Based on the scenario and weight class, present the resolved skill chain below. Replace conditions with project-specific values from Project Discovery (e.g., replace "(if UI)" with "skipping — no UI detected" or "including — UI detected").

---

### Greenfield Feature

**Light** (rare for greenfield):

1. Implement directly
2. `/ship` → `/land-and-deploy`
3. `/wiki-update`
4. `/cso` (if security-relevant)
5. `/canary` (if deploy risk)

**Medium:**

*Session 1 — Design:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. Commit spec → **end session, start fresh for implementation**

*Session 2 — Implementation:*
4. Read spec from `docs/superpowers/specs/`
5. `/executing-plans` with `/TDD` per step
6. `/ark-code-review --quick` → `/simplify`
7. `/qa` (if UI)
8. `/cso` (if security-relevant)
9. `/ship` → `/land-and-deploy`
10. `/canary` (if deploy risk)

*Document:*
11. `/wiki-update`
12. `/wiki-ingest` (if new component needs its own vault page)
13. `/cross-linker`
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
16. `/wiki-update`
17. `/wiki-ingest` (if new component needs its own vault page)
18. `/cross-linker`
19. `/document-release` (if standard docs exist)
20. Session log
21. `/claude-history-ingest`
```

- [ ] **Step 2: Verify**

```bash
grep -c "### Greenfield Feature" skills/ark-workflow/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add greenfield skill chain"
```

---

### Task 5: Add the Skill Chain Generator — Bugfix scenario

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the Bugfix chain**

Add after the Greenfield section:

```markdown
---

### Bug Investigation & Fix

**Light:**

1. `/investigate` — root cause analysis
2. Fix directly
3. `/ship` → `/land-and-deploy`
4. `/cso` (if security-relevant)
5. `/canary` (if deploy risk)
6. `/wiki-update`
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
10. `/wiki-update`
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
10. `/wiki-update`
11. `/wiki-ingest` (if the fix introduces a new concept)
12. `/cross-linker`
13. Session log
14. `/claude-history-ingest`
```

- [ ] **Step 2: Verify**

```bash
grep -c "### Bug Investigation" skills/ark-workflow/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add bugfix skill chain"
```

---

### Task 6: Add the Skill Chain Generator — Ship, Knowledge Capture, Hygiene scenarios

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the remaining three scenario chains**

Add after the Bugfix section:

```markdown
---

### Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update`

---

### Knowledge Capture

*Catch up the vault with what's happened. No weight class needed.*

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
3. `/ship` → `/land-and-deploy`
4. `/cso` (if security-relevant)
5. `/canary` (if deploy risk)
6. `/wiki-update`

**Medium:**

1. `/codebase-maintenance` — audit
2. `/cso` (if security-relevant)
3. `/TDD` — tests before restructuring
4. Implement cleanup
5. `/ark-code-review --quick` → `/simplify`
6. `/ship` → `/land-and-deploy`
7. `/canary` (if deploy risk)
8. `/wiki-update` + session log

**Heavy:**

1. `/codebase-maintenance` — audit
2. `/cso` — infrastructure, dependency, secrets audit
3. `/TDD` — tests before restructuring
4. Implement cleanup
5. `/ark-code-review --thorough` + `/codex` → `/simplify`
6. `/ship` → `/land-and-deploy`
7. `/canary` (if deploy risk)
8. `/wiki-update` + session log
9. `/claude-history-ingest`
```

- [ ] **Step 2: Verify all five scenarios are present**

```bash
grep -c "^### " skills/ark-workflow/SKILL.md
```

Expected: `5` (Greenfield, Bug Investigation, Shipping, Knowledge Capture, Codebase Hygiene)

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add ship, knowledge capture, hygiene skill chains"
```

---

### Task 7: Add Condition Resolution, Session Handoff, and Failure Reference sections

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the Condition Resolution section**

Add after all skill chains:

```markdown
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

If a step fails mid-workflow, refer to the failure handling guide in the design spec at `docs/superpowers/specs/2026-04-08-optimal-workflow-design.md` under "When Things Go Wrong". Key principles:

- **Failed QA:** fix bugs, re-run `/qa`, re-run review if fixes are substantial
- **Failed deploy:** check CI logs, fix and re-run `/ship`, never force-merge
- **Review disagreement:** read both opinions, use your judgment, document resolution
- **Flaky tests:** investigate the flake, don't skip blindly
- **Spec invalidated:** stop implementing, update spec, re-run `/codex` review
- **Canary failure:** investigate, rollback or hotfix if your change, document if pre-existing
- **Vault failure:** not blocking — note it, fix in next Knowledge Capture cycle

## Re-triage

If the task changes class mid-flight (a "light" bug that turns out to involve auth, a "medium" feature that needs architecture decisions):

1. Stop at the current step
2. Re-classify using the triage table
3. Pick up the remaining phases from the new weight class
4. Don't restart — just add the phases you would have run
```

- [ ] **Step 2: Verify the new sections**

```bash
grep -c "^## " skills/ark-workflow/SKILL.md
```

Expected: `9` (Project Discovery, Scenario Detection, Triage, Skill Chains, Condition Resolution, Session Handoff, When Things Go Wrong, Re-triage, Routing Rules Template — added in Task 9)

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add condition resolution, session handoff, failure reference"
```

---

### Task 8: Update CLAUDE.md to register the new skill

**Files:**
- Modify: `CLAUDE.md:69-89` (Available Skills section)

- [ ] **Step 1: Add ark-workflow to the Available Skills section**

In the "Available Skills" section of `CLAUDE.md`, add a new subsection before "Core":

```markdown
### Workflow Orchestration
- `/ark-workflow` — Task triage and skill chain orchestration (entry point for all non-trivial work)
```

- [ ] **Step 2: Verify**

```bash
grep "ark-workflow" CLAUDE.md
```

Expected: line containing the new skill entry.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: register /ark-workflow in Available Skills"
```

---

### Task 9: Add CLAUDE.md routing rules template to the skill

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Append the routing rules template section**

Add at the end of the SKILL.md:

```markdown
## Routing Rules Template

Projects can add this block to their CLAUDE.md to auto-trigger `/ark-workflow`:

\`\`\`markdown
## Skill routing — Ark Workflow

When starting any non-trivial task, invoke `/ark-workflow` first to triage and get the
skill chain. Pattern triggers:

- "build", "create", "add feature", "new component" → /ark-workflow (greenfield)
- "fix", "bug", "broken", "error", "investigate" → /ark-workflow (bugfix)
- "ship", "deploy", "push", "PR", "merge" → /ark-workflow (ship)
- "document", "vault", "catch up", "knowledge" → /ark-workflow (knowledge capture)
- "cleanup", "refactor", "audit", "hygiene", "dead code" → /ark-workflow (hygiene)

For trivial tasks (single obvious change, no ambiguity), skip triage and work directly.
\`\`\`

To add routing to a new project, copy the block above into the project's CLAUDE.md. The `/ark-workflow` skill is already available globally via the ark-skills plugin.
```

- [ ] **Step 2: Verify**

```bash
grep -c "Routing Rules Template" skills/ark-workflow/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): add routing rules template for project CLAUDE.md"
```

---

### Task 10: Version bump and changelog

**Files:**
- Modify: `VERSION`
- Modify: `CHANGELOG.md`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Bump VERSION to 1.2.0**

Write `1.2.0` to `VERSION` (this is a new feature, minor bump).

- [ ] **Step 2: Update plugin.json version**

Change `"version": "1.1.2"` to `"version": "1.2.0"` in `.claude-plugin/plugin.json`.

- [ ] **Step 3: Add "workflow" keyword to plugin.json**

Add `"workflow"` to the keywords array in `.claude-plugin/plugin.json`.

- [ ] **Step 4: Update marketplace.json version**

Change `"version": "1.1.2"` to `"version": "1.2.0"` in `.claude-plugin/marketplace.json`.

- [ ] **Step 5: Prepend changelog entry**

Add at the top of CHANGELOG.md, after the `# Changelog` header:

```markdown
## [1.2.0] - 2026-04-08

### Added
- `/ark-workflow` skill — task triage and skill chain orchestration. Entry point for all
  non-trivial work. Detects scenario (greenfield, bugfix, ship, knowledge capture, hygiene),
  classifies weight (light/medium/heavy) with risk as primary signal, and outputs the
  optimal ordered skill chain with project-specific conditions resolved.
- Routing rules template for project CLAUDE.md auto-triggering
- Workflow design spec at `docs/superpowers/specs/2026-04-08-optimal-workflow-design.md`
```

- [ ] **Step 6: Verify all version files match**

```bash
cat VERSION
grep '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json
```

Expected: all show `1.2.0`.

- [ ] **Step 7: Commit**

```bash
git add VERSION CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump to 1.2.0 — add /ark-workflow skill"
```

---

### Task 11: End-to-end verification

**Files:** None (read-only verification)

- [ ] **Step 1: Verify skill directory structure**

```bash
ls -la skills/ark-workflow/
```

Expected: `SKILL.md` present.

- [ ] **Step 2: Verify skill content completeness**

```bash
grep "^## " skills/ark-workflow/SKILL.md
```

Expected sections: Project Discovery, Scenario Detection, Triage, Skill Chains, Condition Resolution, Session Handoff, When Things Go Wrong, Re-triage, Routing Rules Template.

- [ ] **Step 3: Verify all five scenario chains are present**

```bash
grep "^### " skills/ark-workflow/SKILL.md
```

Expected: Greenfield Feature, Bug Investigation & Fix, Shipping & Deploying, Knowledge Capture, Codebase Hygiene.

- [ ] **Step 4: Verify CLAUDE.md registration**

```bash
grep "ark-workflow" CLAUDE.md
```

Expected: skill listed in Available Skills.

- [ ] **Step 5: Verify version consistency**

```bash
cat VERSION && grep '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json
```

Expected: all show `1.2.0`.

- [ ] **Step 6: Verify all changes are committed**

```bash
git status
git log --oneline -8
```

Expected: clean working tree, commits for tasks 1-10.
