#!/bin/bash
# ark-history-hook.sh — Auto-index Claude sessions into MemPalace
#
# Stop hook for Claude Code. After each session:
# 1. Mines the session transcript directory into ChromaDB (background, zero LLM tokens)
# 2. Checks if enough new material has accumulated for a compile pass
# 3. If threshold met, blocks session exit so Claude can compile insights
#
# Install: copy to ~/.claude/hooks/ and register in settings.json
# This hook NEVER writes to the vault, runs git, or modifies project files.

set -euo pipefail

# === CONFIGURATION ===
COMPILE_THRESHOLD=50  # New drawers before triggering compile
STATE_DIR="$HOME/.mempalace/hook_state"
FAIL_COUNT_MAX=3      # Circuit breaker: disable after N consecutive failures

mkdir -p "$STATE_DIR"

# === READ HOOK INPUT ===
INPUT=$(cat)

SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null)
SESSION_ID=$(echo "$SESSION_ID" | tr -cd 'a-zA-Z0-9_-')
[ -z "$SESSION_ID" ] && SESSION_ID="unknown"

STOP_HOOK_ACTIVE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stop_hook_active', False))" 2>/dev/null)

# === INFINITE LOOP PREVENTION ===
if [ "$STOP_HOOK_ACTIVE" = "True" ] || [ "$STOP_HOOK_ACTIVE" = "true" ]; then
    echo "{}"
    exit 0
fi

# === CHECK MEMPALACE IS INSTALLED ===
if ! command -v mempalace &>/dev/null; then
    echo "{}"
    exit 0
fi

# === DERIVE WING KEY ===
# Claude Code encodes project paths by replacing both / and . with -
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$WING"

# === CIRCUIT BREAKER ===
FAIL_FILE="$STATE_DIR/${WING}_fail_count"
FAIL_COUNT=0
if [ -f "$FAIL_FILE" ]; then
    FAIL_COUNT=$(cat "$FAIL_FILE" 2>/dev/null | grep -E '^[0-9]+$' | head -1 || echo 0)
    FAIL_COUNT=${FAIL_COUNT:-0}
fi
if [ "$FAIL_COUNT" -ge "$FAIL_COUNT_MAX" ]; then
    echo "[ark-history-hook] Auto-indexing disabled after $FAIL_COUNT_MAX consecutive failures. Delete $FAIL_FILE to re-enable." >> "$STATE_DIR/mine.log"
    echo "{}"
    exit 0
fi

# === LAYER 1: INDEX (background, zero LLM tokens) ===
LOCK="$STATE_DIR/${WING}.lock"
# Stale lock recovery: if lock is older than 5 minutes, assume the process died
if [ -d "$LOCK" ]; then
    LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK" 2>/dev/null || echo 0) ))
    [ "$LOCK_AGE" -gt 300 ] && rmdir "$LOCK" 2>/dev/null
fi
if mkdir "$LOCK" 2>/dev/null; then
    # mine only accepts directories, not single files — dedup is file-level so this is still incremental
    if [ -d "$CLAUDE_PROJECT" ]; then
        MINE_TARGET="$CLAUDE_PROJECT"
    else
        rmdir "$LOCK" 2>/dev/null
        echo "{}"
        exit 0
    fi

    nohup bash -c "
        if mempalace mine \"$MINE_TARGET\" --mode convos --wing=\"$WING\" 2>>\"$STATE_DIR/mine.log\"; then
            echo 0 > \"$FAIL_FILE\"
            date +%s > \"$STATE_DIR/${WING}_last_indexed\"
            # Parse drawer count from text status output (no --json flag available)
            # Status format: '  WING: wingname' followed by '    ROOM: name    N drawers'
            # Sum all room drawer counts for this wing
            mempalace status 2>/dev/null | awk -v wing=\"$WING\" '
                BEGIN { found=0; total=0 }
                /WING:/ { found=(\$2 == wing) }
                found && /ROOM:/ { for(i=1;i<=NF;i++) if(\$i==\"drawers\") total+=\$(i-1) }
                END { print total }
            ' > \"$STATE_DIR/${WING}_drawer_count\" 2>/dev/null
            touch \"$STATE_DIR/${WING}_done\"
        else
            PREV=\$(cat \"$FAIL_FILE\" 2>/dev/null || echo 0)
            echo \$((PREV + 1)) > \"$FAIL_FILE\"
        fi
        rmdir \"$LOCK\" 2>/dev/null
    " &>/dev/null &
fi

# === LAYER 2: COMPILE THRESHOLD CHECK ===
# Uses PREVIOUS session's mining results (current mining is still in background)
DONE_MARKER="$STATE_DIR/${WING}_done"
CLAIMED_MARKER="$STATE_DIR/${WING}_done_claimed_$$"
# Atomically claim the done marker to prevent double-trigger from concurrent sessions
if ! mv "$DONE_MARKER" "$CLAIMED_MARKER" 2>/dev/null; then
    # No completed mining yet or another session already claimed it
    echo "{}"
    exit 0
fi

DRAWER_COUNT_FILE="$STATE_DIR/${WING}_drawer_count"
THRESHOLD_FILE="$STATE_DIR/compile_threshold.json"

CURRENT_DRAWERS=0
if [ -f "$DRAWER_COUNT_FILE" ]; then
    CURRENT_DRAWERS=$(cat "$DRAWER_COUNT_FILE" 2>/dev/null | grep -E '^[0-9]+$' | head -1 || echo 0)
    CURRENT_DRAWERS=${CURRENT_DRAWERS:-0}
fi

LAST_COMPILE_DRAWERS=0
if [ -f "$THRESHOLD_FILE" ]; then
    LAST_COMPILE_DRAWERS=$(python3 -c "
import sys,json
try:
    data = json.load(open('$THRESHOLD_FILE'))
    print(data.get('$WING', {}).get('drawers_at_last_compile', 0))
except:
    print(0)
" 2>/dev/null)
fi

NEW_DRAWERS=$((CURRENT_DRAWERS - LAST_COMPILE_DRAWERS))

echo "[$(date '+%H:%M:%S')] Session $SESSION_ID: $CURRENT_DRAWERS total drawers, $NEW_DRAWERS new since last compile" >> "$STATE_DIR/mine.log"

if [ "$NEW_DRAWERS" -ge "$COMPILE_THRESHOLD" ] && [ "$CURRENT_DRAWERS" -gt 0 ]; then
    # Claimed marker already removed from original location by mv above
    rm -f "$CLAIMED_MARKER"

    cat << HOOKJSON
{
  "decision": "block",
  "reason": "AUTO-COMPILE checkpoint. Run /claude-history-ingest compile to synthesize new insights from the ${NEW_DRAWERS} new conversation chunks indexed since last compile. Use mempalace search CLI (with --wing=\"${WING}\" syntax) to query topics, diff against existing vault insights, and write only genuinely new compiled insight pages. Stage only the new files (not git add -A). The wing key for this project is: ${WING}. IMPORTANT: After compile, you MUST run Step 7 (Update Compile Threshold State) to prevent re-triggering."
}
HOOKJSON
else
    # Threshold not met — restore done marker for next session's check
    mv "$CLAIMED_MARKER" "$DONE_MARKER" 2>/dev/null
    echo "{}"
fi
