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

# === PORTABLE HELPERS ===
# Age-only stale-lock recovery allowed a legitimate long-running mine to be
# whacked by a later session. acquire_lock() writes the holder PID into the
# lock dir; contenders check `kill -0 $pid` first, fall back to age only when
# the PID file is missing. Also unifies stat across BSD (macOS) and GNU (Linux).
mtime() {
    stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0
}

# acquire_lock <lock_dir> <stale_age_seconds> — returns 0 on acquire, 1 on contended.
# Semantics:
#   - PID file present + alive  → contended (return 1)
#   - PID file present + dead   → stale, reclaim regardless of age
#   - PID file missing + fresh  → contended (new lock still being initialized)
#   - PID file missing + stale  → age-based reclaim
acquire_lock() {
    local lock="$1" stale_age="$2" holder age
    if [ -d "$lock" ]; then
        holder=$(cat "$lock/pid" 2>/dev/null || true)
        if [ -n "$holder" ]; then
            if kill -0 "$holder" 2>/dev/null; then
                return 1  # holder alive — contended
            fi
            # Holder dead — reclaim immediately, age irrelevant
            rm -rf "$lock" 2>/dev/null || true
        else
            age=$(( $(date +%s) - $(mtime "$lock") ))
            if [ "$age" -gt "$stale_age" ]; then
                rm -rf "$lock" 2>/dev/null || true
            else
                return 1  # no PID evidence + too new to clear
            fi
        fi
    fi
    mkdir "$lock" 2>/dev/null || return 1
    echo $$ > "$lock/pid"
    return 0
}

release_lock() {
    rm -rf "$1" 2>/dev/null || true
}

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
if acquire_lock "$LOCK" 300; then
    # mine only accepts directories, not single files — dedup is file-level so this is still incremental
    if [ -d "$CLAUDE_PROJECT" ]; then
        MINE_TARGET="$CLAUDE_PROJECT"
    else
        release_lock "$LOCK"
        echo "{}"
        exit 0
    fi

    # Palace-global mutex: prevents cross-wing mine races on the shared HNSW segment.
    # mempalace 3.3.2 ships:
    #   - #1023 PID-file guard for `mempalace hook run` auto-ingest (doesn't apply here — we call `mempalace mine` directly)
    #   - #784 per-source-file locks in the miner (prevents duplicate drawer inserts, not HNSW segment contention)
    # Neither protects against two `mempalace mine` processes for DIFFERENT wings writing
    # the same HNSW segment at the same time — still the root cause of upstream #1092.
    # Status as of 2026-04-30: upstream #976 (HNSW thread-safety, root-cause fix) MERGED
    # to `develop` 2026-04-25 but NOT yet in a release tag — v3.3.3 was cut 2026-04-24,
    # one day before the merge. #991 (`hnsw:num_threads=1`) closed without merge,
    # superseded by #976. #1062 (`quarantine_stale_hnsw()` on MCP startup) still open.
    # Retire this mutex once a tagged release includes #976.
    GLOBAL_LOCK="$HOME/.mempalace/palace/.ark-global-mine-mutex"
    mkdir -p "$HOME/.mempalace/palace" 2>/dev/null
    if ! acquire_lock "$GLOBAL_LOCK" 600; then
        echo "[$(date '+%H:%M:%S')] ark-history-hook: another wing's mine is active on this palace (pid $(cat "$GLOBAL_LOCK/pid" 2>/dev/null || echo '?')) — skipping this session's mine" >> "$STATE_DIR/mine.log"
        release_lock "$LOCK"
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
        rm -rf \"$LOCK\" 2>/dev/null
        rm -rf \"$GLOBAL_LOCK\" 2>/dev/null
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
  "reason": "AUTO-COMPILE checkpoint: ${NEW_DRAWERS} new conversation chunks indexed since last compile. DELEGATE this work to a subagent — do NOT run /claude-history-ingest compile inline (the mempalace searches and vault writes would pollute the main context window). Spawn one Task tool call (subagent_type: general-purpose) with this exact prompt: 'Run /claude-history-ingest compile mode end-to-end for wing ${WING} in cwd ${PWD}. Follow Steps 1-7 of the claude-history-ingest skill SKILL.md: read project memory files under \\$HOME/.claude/projects/${WING}/memory/, derive topics via mempalace status + baseline list, query mempalace search --wing=${WING} --results 10 per topic, diff against existing vault/Compiled-Insights/*.md (skip overlap), write new pages using vault/_Templates/Compiled-Insight-Template.md, regenerate the index via the vault _meta/generate-index.py, commit only the new + index files (no git add -A), and CRITICALLY execute Step 7 to update \\$HOME/.mempalace/hook_state/compile_threshold.json with the current drawer count for wing ${WING} — skipping Step 7 will re-trigger this hook every session. Return only a 2-line summary: N insight pages created, threshold updated to X drawers.' After the subagent returns, relay only its summary to the user — do not re-run any of its steps in the main context."
}
HOOKJSON
else
    # Threshold not met — restore done marker for next session's check
    mv "$CLAIMED_MARKER" "$DONE_MARKER" 2>/dev/null
    echo "{}"
fi
