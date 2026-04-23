# /ark-code-review — Report Format Templates

Per-mode report templates. Loaded on-demand by `SKILL.md` § Step 3 (Aggregate and present). Each template is a rendering skeleton — fill placeholders from aggregated findings and deduplicate across agent sources before emitting.

All modes share: dedup findings by `(file, line, description)`; sort by severity; each entry tagged with `Found by: <agent>`.

---

## Default mode

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

---

## `--full` mode

Combines `--thorough` (all 5 agents) with `--epic` (vault context). Adds Epic Alignment, Story Coverage, Silent Failure Audit, Gaps & Risks, and a Merge Readiness verdict.

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

---

## `--epic` mode

Like `--full` but without the Silent Failure Audit (only 2 agents: code-architect-epic-variant + code-reviewer).

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

---

## `--plan` mode

Plan-completion-first: Plan Completion table drives the narrative; Spec Conformance audits adherence to design docs; Scope Drift catches code outside the plan.

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

---

## `--pr N` additions

Use Default mode template plus PR header and the GitHub offer in Step 4 (Follow-up).

```
**PR:** #N — <title>
**URL:** <url>
**Branch:** <headRefName> → <baseRefName>
```

Post-report offers unique to `--pr` mode live in `SKILL.md` § Step 4.

---

## `--quick` mode

Minimal. No subagent dispatch; do the review inline.

```markdown
# Quick Review

**Files reviewed:** N
**Issues:** X high, Y medium

## Findings
- [file:line] Description (severity)

## Verdict
[LOOKS GOOD / FIX: <one-liner>]
```

Do not offer follow-up actions in `--quick` mode. The report stands alone.
