---
title: "Shell Script Safety Patterns — Lessons from mine-vault.sh Review"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - bash
summary: "Four shell scripting pitfalls caught by code review: TMPDIR env collision, pipefail+tail swallowing, missing EXIT traps, and unquoted-tilde parameter stripping. All patterns survived spec review in plans and were only caught by code quality review."
source-sessions:
  - "[[S002-Vault-Retrieval-Tiers-Phase1]]"
  - "[[S005-Ark-Onboard-Centralized-Vault]]"
source-tasks:
  - "[[Arkskill-001-vault-retrieval-tiers]]"
created: 2026-04-08
last-updated: 2026-04-12
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

### Unquoted Tilde in Parameter-Stripping Patterns

Bash performs tilde expansion on the unquoted `~/` in the pattern position of `${var#pattern}` **before** parameter substitution runs. So `${USER_PATH#~/}` with `USER_PATH="~/Vaults/test"` doesn't strip the literal `~/` — the pattern becomes `/Users/sunginkim/` which doesn't match `~/Vaults/test`, so the expansion returns the string unchanged.

```bash
$ USER_PATH="~/Vaults/test"
$ echo "${USER_PATH#~/}"        # broken — returns "~/Vaults/test"
$ echo "${USER_PATH#'~/'}"      # correct — returns "Vaults/test"
$ echo "${USER_PATH:2}"         # also correct — skip 2 chars
```

This bug was in `/ark-onboard`'s approved spec (codex round-4 PASS, revision 4) and propagated through two task bodies before the cross-task code reviewer caught it. Users who typed `~/Vaults/myproject` at the wizard prompt would have gotten `VAULT_TARGET="$HOME/~/Vaults/myproject"` written to the tracked setup script — a broken path the symlink creation would silently fail on. Fix landed in commit `ab62949` via `${USER_PATH#'~/'}`.

Rule: **always quote the tilde inside `${var#pattern}` and `${var%pattern}` patterns**. Bash's tilde-expansion-before-pattern-match behavior is a well-known footgun that spec review cannot catch (codex doesn't execute code; approvals reflect "matches the spec," not "the spec is correct bash").

## Evidence

- mine-vault.sh code quality review (Session S002, commit 50ab675)
- TMPDIR collision: would cause mempalace subprocess failures on any system
- pipefail swallowing: `printf '\n\n\n\n\n' | mempalace init "$TMPDIR" 2>&1 | tail -5` — init failure invisible
- ark-onboard tilde-expansion bug (Session S005, commit ab62949) — survived codex round-4 PASS in the approved spec
- All four bugs were in plan-verbatim scripts, not introduced by implementers

## Implications

- Future bash scripts in `skills/shared/` and inline wizard bash blocks should follow these patterns from the start
- Code quality review catches classes of bugs that spec compliance review cannot — spec review asks "did you build what was asked?" but not "is what was asked safe?"
- Codex-approved specs still contain executable bugs. "Approved by external model" is not the same as "behaviorally verified." Always execute representative test cases on shipping code.
- Per-task review is necessary but not sufficient for multi-task features. A final cross-task code review pass surfaces issues per-task reviewers miss (stale cross-references, dual-write config gaps, verbatim-inherited bugs).
- The plan's verbatim scripts should not be trusted as production-ready — they define requirements, not implementations
- Two-stage review (spec then quality) has justified its cost on every multi-task feature where it's been applied
