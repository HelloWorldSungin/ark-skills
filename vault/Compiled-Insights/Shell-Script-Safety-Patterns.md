---
title: "Shell Script Safety Patterns — Lessons from mine-vault.sh Review"
type: compiled-insight
tags:
  - compiled-insight
  - skill
summary: "Three shell scripting pitfalls caught by code review: TMPDIR env collision causes subprocess failures, pipefail+tail swallows errors, and missing EXIT traps leak temp dirs. All patterns apply to future bash scripts in skills/shared/."
source-sessions:
  - "[[S002-Vault-Retrieval-Tiers-Phase1]]"
source-tasks:
  - "[[Arkskill-001-vault-retrieval-tiers]]"
created: 2026-04-08
last-updated: 2026-04-08
---

# Shell Script Safety Patterns — Lessons from mine-vault.sh Review

## Summary

Code quality review of `skills/shared/mine-vault.sh` caught three bash scripting pitfalls that caused silent failures. All three were in the plan's verbatim script, passed spec review, and were only caught by the code quality reviewer. These patterns are generalizable to any bash script in the Ark skills ecosystem.

## Key Insights

### TMPDIR Is a POSIX Reserved Name

`TMPDIR` is a well-known POSIX/macOS environment variable that `mktemp`, Python's `tempfile`, and many tools read. Assigning `TMPDIR=$(mktemp -d)/vault-md-only` corrupts the variable for all subprocesses — `mempalace init` and `mempalace mine` would create their temp files under a path ending in `/vault-md-only`, which doesn't exist as a temp root. The fix: use `MINE_TMPDIR` (or any non-reserved name). Rule: never name script variables after well-known environment variables (`PATH`, `HOME`, `TMPDIR`, `LANG`, `SHELL`, etc.).

### pipefail + tail Swallows Exit Codes

With `set -o pipefail`, the exit status of a pipeline is the rightmost non-zero exit — but `tail` almost always exits 0. So `command_that_fails | tail -5` reports success even when `command_that_fails` crashed. The fix: capture output to a variable, check the exit code, then display:

```bash
OUTPUT=$(failing_command 2>&1) || {
    echo "ERROR: command failed:"
    echo "$OUTPUT"
    exit 1
}
echo "$OUTPUT" | tail -5
```

This pattern applies to any `printf ... | command ... | tail/head/grep` pipeline where the middle command's failure matters.

### EXIT Traps Prevent Temp Dir Leaks

If `set -e` kills the script mid-execution, any temp directory created earlier stays on disk. An EXIT trap runs regardless of how the script exits (success, error, signal):

```bash
MINE_TMPDIR=""
cleanup() {
    [ -n "${MINE_TMPDIR:-}" ] && [ -d "$(dirname "$MINE_TMPDIR")" ] && rm -rf "$(dirname "$MINE_TMPDIR")"
}
trap cleanup EXIT
```

Set the trap immediately after creating the temp dir. The explicit cleanup at the end of the script becomes redundant but harmless.

## Evidence

- mine-vault.sh code quality review (Session S002, commit 50ab675)
- TMPDIR collision: would cause mempalace subprocess failures on any system
- pipefail swallowing: `printf '\n\n\n\n\n' | mempalace init "$TMPDIR" 2>&1 | tail -5` — init failure invisible
- All three bugs were in the plan's verbatim script, not introduced by the implementer

## Implications

- Future bash scripts in `skills/shared/` should follow these patterns from the start
- Code quality review catches classes of bugs that spec compliance review cannot — spec review asks "did you build what was asked?" but not "is what was asked safe?"
- The plan's verbatim scripts should not be trusted as production-ready — they define requirements, not implementations
- Two-stage review (spec then quality) justified its cost on the first task
