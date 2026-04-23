# /ark-code-review — Agent Prompt Templates

Prompt bodies for the parallel agents invoked by `/ark-code-review`. Loaded on-demand by `SKILL.md` § Step 2. Substitute `<FILE_LIST>`, `<DIFF>`, `<REVIEW_CONTEXT_DOC>`, `<PLAN_SPEC_CONTEXT_DOC>`, `<TEST_FILES>` per the call site.

Pass/fail semantics and agent routing tables live in `SKILL.md`. This file is prompt-only.

---

## Agent 1 — Code Reviewer (default + all modes)

```
subagent_type: feature-dev:code-reviewer
prompt: |
  Review these changes for bugs, logic errors, security vulnerabilities,
  and code quality issues. Only report findings with confidence >= 80.

  Changed files: <FILE_LIST>
  Diff: <DIFF>

  Focus on correctness and security. Skip style issues (linters handle those).
```

## Agent 2 — Code Architect (default + all modes)

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

## Agent 3 — Test Coverage Checker (default + thorough)

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

## Agent 4 — Silent Failure Hunter (--thorough only)

```
subagent_type: code-simplifier:code-simplifier
prompt: |
  Audit error handling in these changed files for silent failures.
  Check for: broad catch blocks, missing error logging, swallowed exceptions,
  inappropriate fallback behavior, optional chaining hiding errors.

  Changed files: <FILE_LIST>
```

## Agent 5 — Test Analyzer (--thorough only)

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

---

## Mode variants

### Code Architect variant (`--epic` mode)

Use instead of Agent 2 default when `--epic` mode is active.

```
subagent_type: feature-dev:code-architect
prompt: |
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

### Code Reviewer variant (`--epic` mode)

Use instead of Agent 1 default when `--epic` mode is active. Shorter than the default because the epic context provides the framing.

```
subagent_type: feature-dev:code-reviewer
prompt: |
  Review code quality of these changes. Confidence >= 80 only.

  Changed files: <FILE_LIST>
  Diff: <DIFF>
```

### Plan Conformance Reviewer (`--plan` mode)

Use instead of Agent 2 default when `--plan` mode is active.

```
subagent_type: feature-dev:code-architect
prompt: |
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

### Code Reviewer variant (`--plan` mode)

Use instead of Agent 1 default when `--plan` mode is active.

```
subagent_type: feature-dev:code-reviewer
prompt: |
  Review code quality of these changes. Confidence >= 80 only.

  Additional context: these changes implement the plan described below.
  Pay special attention to whether the implementation matches the code
  snippets prescribed in the spec (if any diverge, flag it).

  Changed files: <FILE_LIST>
  Diff: <DIFF>
```
