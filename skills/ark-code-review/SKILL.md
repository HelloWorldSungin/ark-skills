---
name: ark-code-review
description: Comprehensive multi-agent code review that orchestrates Claude Code agents (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) into a unified review. Includes an epic review mode that pulls Obsidian TaskNotes epics, stories, and session logs to cross-reference planned work against actual code changes. Also includes a plan review mode that cross-references code against implementation plans and design specs. Includes a full review mode (--full) that combines thorough code analysis with auto-detected epic context. Use this skill whenever the user mentions "code review", "review my changes", "review before deploy", "check my code", "ark review", "/ark-code-review", "pre-deploy review", "review this branch", "review these files", "review this epic", "does the code match the plan", "review against plan", "review against spec", "check plan completion", "did I implement the plan", "full review", "complete review", "review everything", or any request to get feedback on code quality. Also triggers on "what did I break", "is this safe to deploy", "sanity check", or "second opinion on this code". Do NOT use for: PR reviews on GitHub (use code-review:code-review directly), codebase maintenance/cleanup (use codebase-maintenance), or general questions about the codebase.
---

# Ark Code Review

Multi-agent code review that fans out to specialized reviewers, then aggregates findings into a single actionable report. Designed for pre-merge review of branch changes.

## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, task prefix, vault path, TaskNotes path
2. Read the vault's `_meta/vault-schema.md` to understand the vault structure
3. Detect the base branch: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'` (fallback to `master`)
4. Use discovered values throughout — never hardcode project names or paths

## Quick Reference

```
/ark-code-review                              # Default: review current branch vs {base_branch}
/ark-code-review --quick                      # Fast: code-reviewer only
/ark-code-review --thorough                   # Full: all agents including error/test analysis
/ark-code-review --full                       # Thorough + auto-detect epic from branch name
/ark-code-review --epic {task_prefix}001           # Review epic + stories + sessions vs code
/ark-code-review --plan some-feature-slug     # Review code against plan + spec docs
/ark-code-review --pr 123                     # Review a GitHub PR
/ark-code-review src/foo.py bar.py            # Review specific files only
```

## How It Works

The skill fans out to parallel agents, then aggregates findings into a single report.

### Agents (parallel)

Spawn these as parallel subagents scoped to the changed files:

| Agent | Type | What It Checks |
|-------|------|----------------|
| `feature-dev:code-reviewer` | Agent | Bugs, logic errors, security vulnerabilities, CLAUDE.md compliance. Confidence >= 80 filter. |
| `feature-dev:code-architect` | Agent | Architecture consistency, pattern violations, integration risks. Checks changes against established project conventions. |
| **Test Coverage Checker** | Agent (Explore) | Maps changed source files to test files, flags missing/stale tests. |

In `--thorough` mode, also spawn:

| Agent | Type | What It Checks |
|-------|------|----------------|
| **Silent Failure Hunter** | Agent | Silent failures, broad catch blocks, missing error logging, swallowed exceptions. |
| **Test Analyzer** | Agent | Deep test analysis: untested error paths, missing edge cases, negative test gaps. |

### Aggregate & Report

After all agents complete, produce a unified report. Deduplicate findings that overlap between agents (prefer the more specific finding). Sort by severity.

## Execution Steps

Follow these steps exactly:

### Step 1: Determine scope

```bash
# Get the diff to review
git diff {base_branch}...HEAD --stat          # overview
git diff {base_branch}...HEAD --name-only     # changed files list
git diff {base_branch}...HEAD                 # full diff
```

If the user provided specific files, scope all agents to those files only.
If `--pr N` was passed, use `gh pr diff N` instead.

### Step 2: Fan out agents

Spawn these agents **in parallel** using the Agent tool. Pass each agent the list of changed files and the diff.

**Agent 1 — Code Reviewer:**
```
subagent_type: feature-dev:code-reviewer
prompt: |
  Review these changes for bugs, logic errors, security vulnerabilities,
  and code quality issues. Only report findings with confidence >= 80.

  Changed files: <FILE_LIST>
  Diff: <DIFF>

  Focus on correctness and security. Skip style issues (linters handle those).
```

**Agent 2 — Code Architect:**
```
subagent_type: feature-dev:code-architect
prompt: |
  Review these changes for architecture consistency. Check whether changes
  follow existing project patterns, module boundaries, and abstractions.
  Flag integration risks or pattern violations.

  Changed files: <FILE_LIST>
  Diff: <DIFF>

  Reference existing patterns with file:line. Be specific about what
  convention is violated and what the correct pattern looks like.
```

**Agent 3 — Test Coverage Checker (default + thorough):**
```
subagent_type: Explore
prompt: |
  Analyze test coverage for the changed source files on this branch.

  Changed files: <FILE_LIST>

  For each changed source file, do the following:

  1. MAP to test file — Discover the project's test structure by scanning for:
     - `tests/` directory structure
     - Test runner config (pytest.ini, jest.config.*, vitest.config.*)
     - Test naming patterns used in the project (e.g., test_*.py, *.test.ts, *.spec.ts)
     Check multiple naming conventions.

  2. CHECK existence — Does the corresponding test file exist?

  3. CHECK staleness — If the test file exists, read both the changed source and the test.
     Flag if:
     - New public functions/classes were added to the source but have no test
     - Existing function signatures changed (params added/removed) but tests weren't updated
     - New code branches (if/else, try/except) with no corresponding test path
     - Business logic changes (calculations, thresholds, filters) without regression tests

  4. CATEGORIZE each finding:
     - MISSING_TEST_FILE: Changed source file has no test file at all
     - MISSING_FUNCTION_TEST: New or changed public function has no test
     - STALE_TEST: Test exists but doesn't cover the new behavior
     - ADEQUATE: Test file exists and appears to cover the changes (briefly note why)

  5. SKIP these (don't need tests):
     - Config files (*.yaml, *.json, *.toml)
     - __init__.py with only imports
     - Templates, static assets, CSS/JS
     - Documentation, README, CLAUDE.md
     - Type stubs, pure dataclass definitions with no logic

  Output a structured list:
  For each changed source file:
    - Source: <path>
    - Test: <path or "NONE">
    - Status: MISSING_TEST_FILE | MISSING_FUNCTION_TEST | STALE_TEST | ADEQUATE | SKIP
    - Details: <what's missing or why it's adequate>
    - Suggested test: <brief description of what test to write, if applicable>
```

**Agent 4 — Silent Failure Hunter (--thorough only):**
```
subagent_type: code-simplifier:code-simplifier
prompt: |
  Audit error handling in these changed files for silent failures.
  Check for: broad catch blocks, missing error logging, swallowed exceptions,
  inappropriate fallback behavior, optional chaining hiding errors.

  Changed files: <FILE_LIST>
```

**Agent 5 — Test Analyzer (--thorough only):**
```
prompt: |
  Analyze test coverage for these changes. Identify:
  - Untested error handling paths
  - Missing edge cases
  - Critical business logic without tests
  - Missing negative test cases

  Changed files: <FILE_LIST>
  Corresponding test files: <TEST_FILES>
```

### Step 3: Aggregate and present

Produce the final report in this format:

```markdown
# Ark Code Review Report

**Branch:** <branch> vs {base_branch}
**Files changed:** N
**Reviewers:** code-reviewer, code-architect, test-coverage-checker [, silent-failure-hunter, test-analyzer]

## Critical (must fix before merge)
- [file:line] Description — Found by: <agent>

## High (should fix)
- [file:line] Description — Found by: <agent>

## Medium (consider fixing)
- [file:line] Description — Found by: <agent>

## Test Coverage
| Source File | Test File | Status | Details |
|-------------|-----------|--------|---------|
| src/foo.py | tests/test_foo.py | ADEQUATE | Covers new bar() method |
| src/bar.py | NONE | MISSING_TEST_FILE | New module with 3 public functions — needs unit tests |
| src/baz.py | tests/test_baz.py | STALE_TEST | process() gained a new param `strict` but tests don't exercise it |

**Coverage verdict:** [ALL COVERED / N files need tests / WRITE TESTS BEFORE MERGE]

## Architecture Notes
- Description — Found by: code-architect

## Simplification Opportunities
- [file:line] Description (suggestion only, not auto-applied)

## Summary
X critical, Y high, Z medium issues found. N files need test coverage.
[Merge recommendation: SAFE / FIX FIRST / WRITE TESTS / NEEDS DISCUSSION]
```

### Step 4: Offer follow-up (MANDATORY — do not skip this step)

After presenting the report, you MUST offer follow-up actions.

For **all modes** (except --quick):
- "Want me to fix the critical/high issues?"
- "Want me to write/update the missing tests?" (if test coverage checker found gaps)
- "Want me to run `/simplify` on the suggestions?"

For **--pr N** mode (in addition to the above):
- "Want me to post these findings as comments on PR #N?" (via `gh pr comment`)
- "Want me to request changes on the PR?" (via `gh pr review --request-changes`)
- "Or just leave the review here locally?"

For **--full** mode:
- "Want me to fix the critical/high issues?"
- "Want me to write/update the missing tests?" (if test coverage checker found gaps)
- "Want me to update the epic/story statuses in the vault?"
- "Want me to run `/simplify` on the suggestions?"

For **--epic** mode:
- "Want me to update the epic/story statuses in the vault?"
- "Want me to fix the code quality issues?"

For **--plan** mode:
- "Want me to fix the code quality issues?"
- "Want me to implement the incomplete tasks?" (if tasks remain unchecked)
- "Want me to update the plan checkboxes to reflect current status?"

## Mode-Specific Behavior

### `--quick` mode

**Goal: finish in under 60 seconds with a short, actionable report.**

1. **Scope down aggressively.** Do NOT review the full branch diff. Instead:
   - If the user mentions specific files or "the changes I just made", scope to only those files.
   - Otherwise, use `git diff --name-only` (unstaged) or `git diff --cached --name-only` (staged) to find only the *most recent* uncommitted changes. If nothing is uncommitted, use the last commit only (`git diff HEAD~1 --name-only`).
   - Never review more than ~10 files in quick mode. If the scope is larger, tell the user to use default mode instead.

2. **Skip code-architect and test coverage checker** — no architecture or test coverage review.

3. **Run only `feature-dev:code-reviewer`** scoped to the narrowed file list. Do NOT spawn a subagent — do the review inline to save overhead.

4. **Produce a minimal report** — no Architecture Notes, no Simplification Opportunities section. Just:

```markdown
# Quick Review

**Files reviewed:** N
**Issues:** X high, Y medium

## Findings
- [file:line] Description (severity)

## Verdict
[LOOKS GOOD / FIX: <one-liner>]
```

5. **Do not offer follow-up actions.** The quick report stands alone.

### `--thorough` mode
Run all agents (including silent-failure-hunter and test-analyzer). Use for significant changes, new features, or pre-merge reviews.

### `--full` mode

Combines `--thorough` (all 5 code analysis agents) with `--epic` (vault context cross-referencing), auto-detecting the epic from the current branch name.

#### Step 0: Auto-detect epic from branch name

```
1. Get current branch: git branch --show-current
2. Strip prefix (feature/, improve/, epic/, fix/, bugfix/) → branch_slug
3. Lowercase branch_slug, tokenize by splitting on "-"
4. For each epic file in {tasknotes_path}/Tasks/Epic/*.md:
   a. Strip task-id prefix (e.g., "{task_prefix}043-") → epic_slug
   b. Lowercase epic_slug, tokenize by splitting on "-"
   c. Score = |branch_tokens ∩ epic_tokens| / |branch_tokens ∪ epic_tokens|
5. Pick the best match:
   - If best score ≥ 0.6 and no tie → use that epic
   - If tie or best score < 0.6 → fall back to step 0b
```

**Step 0b: Fallback — in-progress epics**

If branch matching fails:
```
1. Search {tasknotes_path}/Tasks/Epic/*.md for frontmatter "status: in-progress"
2. If 1 match → use it
3. If 0 matches → warn "No epic found, falling back to --thorough only"
4. If 2+ matches → present the list, ask user to pick
```

#### Steps 1-4: Combined thorough + epic

Once the epic is resolved:

1. **Gather vault context** — same as `--epic` mode (Step 1: read epic, stories, sessions via obsidian-cli)
2. **Determine scope** — same as default mode (git diff {base_branch}...HEAD)
3. **Fan out all agents in parallel:**

| # | Agent | Source | Notes |
|---|-------|--------|-------|
| 1 | Code Reviewer (`feature-dev:code-reviewer`) | default | Confidence ≥80 |
| 2 | Code Architect (`feature-dev:code-architect`) | `--epic` | Gets epic context doc + diff; checks epic alignment AND architecture |
| 3 | Test Coverage Checker (Explore) | default | Maps source → test files |
| 4 | Silent Failure Hunter | `--thorough` | Audits error handling |
| 5 | Test Analyzer | `--thorough` | Deep test gap analysis |

4. **Produce combined report** — uses the Epic Review Report format with additional thorough-mode sections:

```markdown
# Full Review Report

**Epic:** <TASK-ID> — <title> (auto-detected from branch)
**Branch:** <branch> vs {base_branch}
**Files changed:** N
**Stories:** N total (X done, Y in-progress, Z not started)
**Reviewers:** code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer

## Epic Alignment
- [PASS/GAP] Goal 1: <assessment>
- [PASS/GAP] Goal 2: <assessment>

## Story Coverage
| Story | Status | Code Changes? | Assessment |
|-------|--------|---------------|------------|
| <id>  | done   | Yes (3 files) | Fully implemented |
| <id>  | in-progress | Partial | Missing error handling |
| <id>  | backlog | No | Not started — blocks merge? |

## Critical (must fix before merge)
- [file:line] Description — Found by: <agent>

## High (should fix)
- [file:line] Description — Found by: <agent>

## Medium (consider fixing)
- [file:line] Description — Found by: <agent>

## Silent Failure Audit
- [file:line] Description — Found by: silent-failure-hunter

## Test Coverage
| Source File | Test File | Status | Details |
|-------------|-----------|--------|---------|
...

**Coverage verdict:** [ALL COVERED / N files need tests / WRITE TESTS BEFORE MERGE]

## Gaps & Risks
- Story X has no corresponding code
- Code in module Y doesn't map to any story (scope creep?)
- Session-### noted risk Z — not addressed in code

## Architecture Notes
- Description — Found by: code-architect

## Recommendations
1. ...
2. ...

## Merge Readiness
[READY / BLOCKED BY: <story-ids or issues> / NEEDS DISCUSSION]
```

### `--epic TASK-ID` mode

Reviews an Obsidian TaskNotes epic against the actual code on the branch. This is the most context-rich review mode — it pulls the full planning context from the vault and cross-references it against what was actually implemented.

#### Step 1: Gather vault context (via obsidian-cli)

Use the `obsidian:obsidian-cli` skill to efficiently query the vault instead of reading raw files.

```
1. Find and read the epic:
   obsidian read file="<TASK-ID>-*"
   -> Extract: title, status, priority, goals, child story wikilinks

2. Find child stories using backlinks:
   obsidian backlinks file="<TASK-ID>-*"
   -> This finds all stories whose `projects` frontmatter references the epic

3. For each child story, read properties:
   obsidian property:read name="status" file="<story-id>-*"
   -> Extract: task-id, title, status, session, completion criteria

4. Collect session references from:
   - Epic's `session` property
   - Each story's `session` property
   - Deduplicate session IDs

5. For each referenced session log:
   obsidian read file="Session-###"
   -> Extract: objective, key accomplishments, next steps
```

#### Step 2: Build the review context document

Assemble a structured summary:

```markdown
## Epic: <TASK-ID> — <title>
Status: <status> | Priority: <priority>
Goals:
<goals from epic body>

## Stories
### <story-id> — <title> [status]
Description: <from story body>
Completion criteria: <checkboxes>

### <story-id> — <title> [status]
...

## Session History
### Session-###: <title>
Key accomplishments: <summary>
Next steps: <from session>

## Branch Changes
<git diff {base_branch}...HEAD --stat>
<changed files list>
```

#### Step 3: Fan out reviewers

Run in parallel:

**Agent 1 — Code Architect** (`feature-dev:code-architect`):
```
Review whether the code changes on this branch correctly implement the epic's
goals and stories. Check for:
- Missing stories that have no corresponding code changes
- Code changes that don't map to any story (scope creep)
- Architecture decisions that contradict the epic's stated goals
- Integration risks between stories

Epic context:
<REVIEW_CONTEXT_DOC>

Branch diff:
<DIFF>
```

**Agent 2 — Code Reviewer** (`feature-dev:code-reviewer`):
```
Review code quality of these changes. Confidence >= 80 only.
Changed files: <FILE_LIST>
Diff: <DIFF>
```

#### Step 4: Epic review report

```markdown
# Epic Review Report

**Epic:** <TASK-ID> — <title>
**Branch:** <branch> vs {base_branch}
**Stories:** N total (X done, Y in-progress, Z not started)

## Epic Alignment
- [PASS/GAP] Goal 1: <assessment>
- [PASS/GAP] Goal 2: <assessment>

## Story Coverage
| Story | Status | Code Changes? | Assessment |
|-------|--------|---------------|------------|
| <id>  | done   | Yes (3 files) | Fully implemented |
| <id>  | in-progress | Partial | Missing error handling |
| <id>  | backlog | No | Not started — blocks merge? |

## Code Quality Issues
- [file:line] Description — Found by: <agent>

## Gaps & Risks
- Story X has no corresponding code
- Code in module Y doesn't map to any story (scope creep?)
- Session-### noted risk Z — not addressed in code

## Recommendations
1. ...
2. ...

## Merge Readiness
[READY / BLOCKED BY: <story-ids> / NEEDS DISCUSSION]
```

### `--plan SLUG` mode

Reviews code changes against an implementation plan and its companion design spec. This is the in-repo counterpart to `--epic` — while epics live in the Obsidian vault and track high-level goals/stories, plans and specs are detailed implementation blueprints with exact file paths, code snippets, and step-by-step tasks.

Use this when you want to verify that the code on the branch actually matches what was planned — catching missed tasks, spec deviations, and scope drift.

#### Step 1: Discover plan and spec files

The argument can be a full filename, a slug (with or without date prefix), or a partial match:

```
/ark-code-review --plan research-pipeline
/ark-code-review --plan 2026-03-24-research-pipeline
/ark-code-review --plan pipeline       # partial match
```

Discovery logic:
1. Search for plan files matching `*{SLUG}*.md` in likely locations (project root, docs/, plans/)
2. If multiple matches, pick the most recent by date prefix. If ambiguous, ask the user.
3. For the matched plan, check for a companion spec/design file with `-design` or `-spec` suffix.
4. If the spec file doesn't exist, proceed with plan-only review (warn the user).

#### Step 2: Parse plan and spec

Read both documents and extract structured context:

**From the plan:**
- Goal statement (top of document)
- Chunks and tasks (## Chunk N / ### Task N headers)
- Individual steps with checkbox status (`- [ ]` unchecked, `- [x]` checked)
- File paths mentioned in each task
- Commit messages (from `git commit -m` lines in steps)

**From the spec:**
- Problem statement and solution overview
- Design decisions table
- Architecture (before/after data flow)
- Component descriptions with file paths and code snippets
- Performance targets
- Testing requirements

#### Step 3: Fan out reviewers

Run in parallel:

**Agent 1 — Plan Conformance Reviewer** (`feature-dev:code-architect`):
```
Review whether the code changes on this branch correctly implement the
plan and spec. Cross-reference each planned task against actual code changes.

For each task in the plan, determine:
- IMPLEMENTED: Code changes match the task's requirements
- PARTIAL: Some aspects implemented, others missing
- NOT_IMPLEMENTED: No corresponding code changes found
- DEVIATED: Code exists but differs from the spec's prescribed approach

Also check for:
- Scope creep: Code changes that don't map to any planned task
- Spec deviations: Architecture/approach differs from what the spec describes
- Missing design decisions: Spec prescribed a specific choice but code uses something else

Plan + Spec context:
<PLAN_SPEC_CONTEXT_DOC>

Branch diff:
<DIFF>
```

**Agent 2 — Code Reviewer** (`feature-dev:code-reviewer`):
```
Review code quality of these changes. Confidence >= 80 only.

Additional context: these changes implement the plan described below.
Pay special attention to whether the implementation matches the code
snippets prescribed in the spec (if any diverge, flag it).

Changed files: <FILE_LIST>
Diff: <DIFF>
```

**Agent 3 — Test Coverage Checker** (same Explore agent as default mode).

#### Step 4: Plan review report

```markdown
# Plan Review Report

**Plan:** <filename>
**Spec:** <filename or "none">
**Branch:** <branch> vs {base_branch}
**Tasks:** N total (X implemented, Y partial, Z not started)

## Plan Completion
| Chunk | Task | Steps | Status | Assessment |
|-------|------|-------|--------|------------|
| 1: Foundation | Task 1: Add path constant | 3/3 | IMPLEMENTED | All steps complete, matches spec |
| 1: Foundation | Task 2: Fix data manager | 4/5 | PARTIAL | Step 5 (commit) pending |
| 2: Pipeline | Task 3: Create pipeline | 5/6 | IMPLEMENTED | Code matches spec snippets |

**Completion: X/N tasks done (Y%)**

## Spec Conformance
- [PASS] Component 1: Matches spec architecture
- [DEVIATION] Component 2: Uses different approach than spec prescribes
- [GAP] Testing: Spec requires specific test — not implemented

## Code Quality Issues
- [file:line] Description — Found by: code-reviewer

## Scope Drift
- Code in <file> doesn't map to any planned task (new? scope creep?)
- Plan Task N references <file> but no changes were made to it

## Test Coverage
| Source File | Test File | Status | Details |
|-------------|-----------|--------|---------|
...

## Recommendations
1. ...
2. ...

## Merge Readiness
[READY / BLOCKED BY: incomplete tasks / NEEDS DISCUSSION]
Plan completion must be >= 80% for merge recommendation.
```

### `--pr N` mode

1. Use `gh pr diff N` for the diff (not `git diff`).
2. Also run `gh pr view N --json title,url,headRefName,baseRefName` to get PR metadata for the report header.
3. Run full default review (all default agents in parallel).
4. In the report header, include the PR number, title, and URL.
5. **After the report, you MUST offer to post findings as PR comments:**
   - "Want me to post these findings as inline comments on PR #N?" (via `gh pr review N --comment --body "..."`)
   - "Want me to request changes on the PR?" (via `gh pr review N --request-changes --body "..."`)
   - "Or just leave the review here locally?"

## Post-Review Actions

**If the project's CLAUDE.md defines deployment targets:**
- Check deployed commit drift on each target
- Verify service health endpoints
- Run staging smoke tests

**If no deployment targets are defined:** Skip deployment checks.

## Important Notes

- **Linters handle style** — All agents skip formatting/style issues since linters catch those automatically.
- **Confidence threshold** — `feature-dev:code-reviewer` uses >= 80 confidence. Other agents should also avoid low-confidence findings.
- **Large diffs** — If >4000 lines, consider splitting the review by directory or module rather than reviewing everything at once.
- **Don't auto-fix** — This skill is advisory. Present findings and let the user decide what to fix.
