---
name: ark-workflow
description: Task triage and skill chain orchestration. Use when starting any non-trivial task to determine the optimal workflow. Triggers on "build", "create", "fix", "bug", "ship", "deploy", "document", "cleanup", "refactor", "audit", "new feature", "investigate". Do NOT use for trivial single-file changes with no ambiguity.
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
