---
name: wiki-handoff
description: Write a session bridge page to .omc/wiki/ capturing in-session state before /compact or /clear. Invoked from /ark-workflow Step 6.5 action branch. Triggers on "handoff session", "bridge page", "flush session state".
---

# Wiki Handoff

Writes one page to `.omc/wiki/session-bridge-{YYYY-MM-DD}-{HHMMSS}-{sid8}.md` with a validated snapshot of current session state. Designed to run before `/compact` or `/clear` so the next session can recover context.

## When this runs

Invoked from `/ark-workflow` SKILL.md Step 6.5 after the v1.17.0 context-budget probe menu surfaces and the user picks option `(a) compact` or `(b) clear`. NOT invoked for option `(c) subagent`.

## Inputs

Supplied by the LLM in the same turn that invokes this skill:

| Arg | Source |
|---|---|
| `--chain-id` | `.ark-workflow/current-chain.md` frontmatter |
| `--task-text` | same |
| `--scenario` | same |
| `--step-index`, `--step-count` | chain step checklist |
| `--session-id` | `$CLAUDE_SESSION_ID` or `.omc/state/hud-state.json` |
| `--open-threads` | **LLM-authored**, specific (file paths, decision points) |
| `--next-steps` | **LLM-authored**, specific |
| `--notes` | LLM-authored free-form |
| `--done-summary` | LLM summary of session work |
| `--git-diff-stat` | `git diff --stat <chain-entry-ref>..HEAD` |

## Schema enforcement

The script rejects calls where `--open-threads` or `--next-steps` match any of:
- Empty / whitespace-only
- Generic: `continue task`, `TBD`, `TODO`, `keep going`, `none`, `n/a`
- Content length <20 chars

On rejection exits non-zero; the LLM MUST re-invoke with specifics.

## Degradation

- `.omc/wiki/` missing → exit 0 silent.
- Filename collision within same second → append `-2`, `-3`, … (up to 10 retries).
- Too many retries → exit 3.

## Usage

```bash
python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
    --chain-id "$CHAIN_ID" --task-text "$TASK_TEXT" --scenario "$SCENARIO" \
    --step-index "$STEP_IDX" --step-count "$STEP_COUNT" --session-id "$SESSION_ID" \
    --open-threads "Verify JWT TTL handling in auth/middleware.py:47" \
    --next-steps "Write integration test tests/test_auth.py covering expired tokens" \
    --notes "Rate limiter interaction still open" \
    --done-summary "Implemented JWT validation middleware; 3/5 tests pass" \
    --git-diff-stat "$(git diff --stat HEAD~3..HEAD)"
```

Output on success: path of the created bridge page (stdout).
