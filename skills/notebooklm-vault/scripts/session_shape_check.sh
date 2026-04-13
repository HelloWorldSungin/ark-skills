#!/usr/bin/env bash
# Precondition for notebooklm-vault's session-continue command.
# Exit 0: latest session log exists, is <7 days old (by file mtime), has "## Next Steps"
#         heading, and has a non-empty "epic:" frontmatter field (link resolution is done
#         later by notebooklm-vault's session-continue logic itself, not by this probe).
# Exit 1: any above check fails → warm-up should use bootstrap instead.
#
# Reads env vars (set by warm-up per D6):
#   WARMUP_PROJECT_DOCS_PATH — absolute path to project docs (parent of Session-Logs/)

set -uo pipefail

if [ -z "${WARMUP_PROJECT_DOCS_PATH:-}" ]; then
    echo "session_shape_check: WARMUP_PROJECT_DOCS_PATH not set" >&2
    exit 1
fi

LOGS_DIR="$WARMUP_PROJECT_DOCS_PATH/Session-Logs"
if [ ! -d "$LOGS_DIR" ]; then
    echo "session_shape_check: no Session-Logs directory at $LOGS_DIR" >&2
    exit 1
fi

# Find highest-numbered S*.md (per notebooklm-vault convention)
LATEST=$(find "$LOGS_DIR" -maxdepth 1 -type f -name 'S*.md' 2>/dev/null \
    | awk -F/ '{print $NF}' \
    | sort -V \
    | tail -1)

if [ -z "$LATEST" ]; then
    echo "session_shape_check: no session logs found" >&2
    exit 1
fi

LATEST_PATH="$LOGS_DIR/$LATEST"

# Age check: <7 days old
if [ "$(date +%s)" -gt 0 ]; then
    AGE_SECONDS=$(( $(date +%s) - $(stat -f %m "$LATEST_PATH" 2>/dev/null || stat -c %Y "$LATEST_PATH" 2>/dev/null) ))
    if [ "$AGE_SECONDS" -gt $((7 * 86400)) ]; then
        echo "session_shape_check: latest log $LATEST is older than 7 days (${AGE_SECONDS}s)" >&2
        exit 1
    fi
fi

# Shape check: has "Next Steps" heading
if ! grep -qE '^##[[:space:]]+Next Steps' "$LATEST_PATH"; then
    echo "session_shape_check: $LATEST missing '## Next Steps' heading" >&2
    exit 1
fi

# Shape check: has epic frontmatter field with non-empty value
# Minimal YAML-frontmatter parse: first --- ... --- block, look for "epic:" line
EPIC_VALUE=$(awk '
    /^---$/ { if (in_fm) exit; in_fm=1; next }
    in_fm && /^epic:/ { sub(/^epic:[[:space:]]*/, ""); print; exit }
' "$LATEST_PATH" | tr -d '"' | tr -d "'" | xargs)

if [ -z "$EPIC_VALUE" ]; then
    echo "session_shape_check: $LATEST has no 'epic:' frontmatter field" >&2
    exit 1
fi

exit 0
