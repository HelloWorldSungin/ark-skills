---
name: wiki-handoff
description: Write a session bridge page to .omc/wiki/ capturing in-session state before /compact or /clear. Invoked from /ark-workflow Step 6.5 action branch. Triggers on "handoff session", "bridge page", "flush session state".
---

# Wiki Handoff

Writes one page to `.omc/wiki/session-bridge-{YYYY-MM-DD}-{HHMMSS}-{sid8}.md` with a validated snapshot of current session state, then **recommends `/compact` vs `/clear`** based on chain progress and emits the exact slash command + follow-up prompt to paste. Designed to run before `/compact` or `/clear` so the next session can recover context.

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

## Recommendation rule

After a successful write the script appends a recommendation block to stdout. The decision uses chain progress already captured in `--step-index` / `--step-count`:

| Condition | Recommendation | Reason printed |
|---|---|---|
| `step_index < step_count` (chain mid-flight) | `/compact` | "chain in progress, step {i}/{n} — keep summary continuity" |
| `step_index >= step_count` (chain complete) | `/clear` | "chain complete ({n}/{n}) — next task likely unrelated" |
| Non-numeric or `step_count == 0` | `/compact` | "indeterminate chain state — defaulting to compact (safer)" |

The block contains the slash command to run (with a pre-filled `focus on …` argument for `/compact`) and the prompt to paste after the destructive action settles. The follow-up prompt always points back at the bridge file so the resumed session can recover context with one read.

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

## Output

On success the script prints to stdout:

1. Line 1: absolute path of the created bridge page (preserved for backward compat — callers that capture the first line still work).
2. Blank line.
3. `═══ HANDOFF RECOMMENDATION: /compact ═══` or `═══ HANDOFF RECOMMENDATION: /clear ═══`.
4. `Reason: …` — one-line rationale per the recommendation rule above.
5. `→ Run this slash command:` followed by the command on the next line (indented 3 spaces). For `/compact`, includes a pre-filled `focus on …` argument; for `/clear`, the bare `/clear`.
6. `→ After /compact settles, paste this prompt:` (or `After /clear completes, …`) followed by the resume prompt on the next line.

Example (`/compact` case):

```
.omc/wiki/session-bridge-2026-05-01-143005-abcdef01.md

═══ HANDOFF RECOMMENDATION: /compact ═══
Reason: chain in progress, step 2/5 — keep summary continuity.

→ Run this slash command:
   /compact focus on continuing the greenfield chain (step 2/5); see .omc/wiki/session-bridge-2026-05-01-143005-abcdef01.md for specifics

→ After /compact settles, paste this prompt:
   Read .omc/wiki/session-bridge-2026-05-01-143005-abcdef01.md and continue from its "Next steps" section. Resume at step 3/5 of scenario "greenfield".
```

On non-zero exit (schema rejection, collision limit, I/O), nothing is printed to stdout — the caller must NOT proceed to `/compact` or `/clear`.
