# helper.bash — shared setup for the ark-skill-healer bats suite.
#
# Every test sources this. It computes the skill/script roots relative to the
# test file location (no hardcoded absolute paths) and provides a hermetic
# temp SKILL_HEALER_STATE_DIR so tests NEVER touch the real
# .omc/skill-healer/state. Cleanup is automatic via teardown().

# Resolve paths from this helper's own location.
HELPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HELPER_DIR/.." && pwd)"
SCRIPTS_DIR="$SKILL_DIR/scripts"
REFERENCES_DIR="$SKILL_DIR/references"
FIXTURES_DIR="$HELPER_DIR/fixtures"
# REPO_ROOT mirrors the scripts' own resolution: scripts/../../../.. == repo root.
REPO_ROOT="$(cd "$SCRIPTS_DIR/../../../.." && pwd)"

INVENTORY_SH="$SCRIPTS_DIR/collect_inventory.sh"
UPSTREAM_SH="$SCRIPTS_DIR/collect_upstream.sh"
SEED_SH="$SCRIPTS_DIR/seed_workarounds.sh"
LIB_STATE_SH="$SCRIPTS_DIR/lib_state.sh"

# Create a private temp dir + hermetic state dir. Call from setup().
healer_setup_tmp() {
    HEALER_TMP="$(mktemp -d)"
    export SKILL_HEALER_STATE_DIR="$HEALER_TMP/state"
    mkdir -p "$SKILL_HEALER_STATE_DIR"
}

# Remove the temp dir + unset overrides. Call from teardown().
healer_teardown_tmp() {
    [ -n "${HEALER_TMP:-}" ] && rm -rf "$HEALER_TMP"
    unset SKILL_HEALER_STATE_DIR
    unset SKILL_HEALER_INVENTORY_SCRIPT
}

# bats' `run` merges stderr into $output. The collectors log guarded skips
# (e.g. "tier=release skipped: …") to stderr, which are NOT JSON. Strip any line
# that is not a JSON object before feeding $output to jq.
json_lines() {
    printf '%s\n' "$1" | grep '^{' || true
}

# jq filter helper: count upstream_delta records matching a jq predicate.
# usage: count_deltas "$output" '.quiet == false'
count_deltas() {
    json_lines "$1" \
        | jq -c "select(.kind==\"upstream_delta\" and ($2))" 2>/dev/null \
        | grep -c . || true
}
