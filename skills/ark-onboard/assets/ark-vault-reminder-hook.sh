#!/usr/bin/env bash
# ark-vault-reminder-hook.sh — gentle Stop hook: once per session, suggest /vault distillation.
#
# Installed by /ark-onboard into a downstream project's .claude/hooks/ and registered under
# hooks.Stop in .claude/settings.json. It is SUGGESTION-ONLY:
#   - never writes to the vault, never runs git, never modifies project files
#   - never blocks the stop (exit 0, no "decision" field) — the session ends normally
#   - fires at most once per session (Stop fires on every turn-end; a session_id-keyed
#     marker keeps it from bannering every turn)
#
# Contract: a Stop hook that prints {"systemMessage": "..."} on exit 0 shows a non-blocking
# banner to the user. See the Claude Code hooks docs.
set -euo pipefail

# session_id (from the Stop payload on stdin) keys the once-per-session marker. python3 is a
# hard ark requirement (/ark-health Check 8, Critical); default only guards a malformed payload.
sid="$(python3 -c 'import json, sys
try:
    print(json.load(sys.stdin).get("session_id") or "nosession")
except Exception:
    print("nosession")')"

marker="${TMPDIR:-/tmp}/ark-vault-reminder-${sid}"
if [ -f "$marker" ]; then
    exit 0
fi
: > "$marker"

printf '%s\n' '{"systemMessage":"🗄️  Session wrapping up — if you learned something durable, run /vault to distill it into the OKF vault (durable knowledge only; not session logs or tasks)."}'
