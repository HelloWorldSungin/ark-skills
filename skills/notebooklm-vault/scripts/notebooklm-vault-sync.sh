#!/usr/bin/env bash
# notebooklm-vault-sync.sh — Incremental vault-to-NotebookLM sync
#
# Usage:
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh                # Incremental sync (new/changed only)
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --full         # Nuke and re-import everything (emergency recovery)
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --sessions-only  # Only session logs
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --file PATH    # Single file (relative to vault root)
#
# Expects to be run from the project root.
#
# Notebook-authoritative: each incremental run lists sources from NotebookLM, dedupes,
# and prunes orphans BEFORE syncing. sync-state.json is a hash cache only, not a
# source-of-truth for existence. This prevents ghost-registration accumulation when
# notebooklm-py's register -> upload -> stream pipeline fails partway through.
#
# Concurrency: per-vault flock — only one run per vault at a time.

set -euo pipefail

# --- Helpers (must be defined before any top-level usage) ---
die() { echo "ERROR: $*" >&2; exit 1; }

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Support both installed (.claude/skills/notebooklm-vault/scripts/) and
# standalone (skills/notebooklm-vault/scripts/) layouts.
if [[ "$SCRIPT_DIR" == */.claude/skills/* ]]; then
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
else
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
fi

# Prereqs needed for config parsing
command -v jq >/dev/null 2>&1 || die "jq not found. Install with: brew install jq"

# Config: check project's .notebooklm/ first, then vault's .notebooklm/
if [[ -f "$PROJECT_ROOT/.notebooklm/config.json" ]]; then
    CONFIG_FILE="$PROJECT_ROOT/.notebooklm/config.json"
else
    CONFIG_FILE="$PROJECT_ROOT/vault/.notebooklm/config.json"
fi
[[ -f "$CONFIG_FILE" ]] || die "Config not found. Check .notebooklm/config.json in project or vault."

# vault_root from config (relative to project root, or "." for standalone vaults)
VAULT_ROOT_REL=$(jq -r '.vault_root' "$CONFIG_FILE")
if [[ "$VAULT_ROOT_REL" == "." ]]; then
    # Standalone: config lives inside the vault; vault root is parent of .notebooklm/
    VAULT_ROOT="$(cd "$(dirname "$CONFIG_FILE")/.." && pwd)"
    VAULT_NOTEBOOKLM="$(dirname "$CONFIG_FILE")"
else
    VAULT_ROOT="$PROJECT_ROOT/$VAULT_ROOT_REL"
    VAULT_NOTEBOOKLM="$VAULT_ROOT/.notebooklm"
fi
SYNC_STATE_FILE="$VAULT_NOTEBOOKLM/sync-state.json"

# Excluded path segments (applied as "path contains /<excl>/ or ends with /<excl>")
EXCLUDES=(".obsidian" ".git" ".notebooklm" ".claude-plugin" "_Templates" "_Attachments" "TaskNotes" "_meta")

# Batched state management temp files
PENDING_UPDATES=""
PENDING_REMOVES=""

# Per-vault temp dirs / files
NOTEBOOK_SOURCES_DIR=""
VAULT_FILES=""

# Lock (set by acquire_lock)
LOCK_FILE=""

# Notebook keys loaded from config
declare -a NOTEBOOK_KEYS=()

# Sync counters
ADDED=0
UPDATED=0
UNCHANGED=0
DELETED=0
ERRORS=0

check_prereqs() {
    command -v notebooklm >/dev/null 2>&1 || die "notebooklm CLI not found. Install with: pipx install notebooklm-py"
    command -v jq >/dev/null 2>&1 || die "jq not found. Install with: brew install jq"
    [[ -f "$CONFIG_FILE" ]] || die "Config not found at $CONFIG_FILE. Run '/notebooklm-vault setup' first."
}

load_notebook_keys() {
    NOTEBOOK_KEYS=()
    while IFS= read -r key; do
        [[ -n "$key" ]] && NOTEBOOK_KEYS+=("$key")
    done < <(jq -r '.notebooks | keys[]' "$CONFIG_FILE")
    [[ ${#NOTEBOOK_KEYS[@]} -gt 0 ]] || die "No notebooks found in $CONFIG_FILE"
}

get_notebook_id() {
    local key="$1"
    local id
    id=$(jq -r ".notebooks.${key}.id // empty" "$CONFIG_FILE")
    [[ -n "$id" ]] || die "Notebook '${key}' has empty id in $CONFIG_FILE. Run '/notebooklm-vault setup' to create it."
    echo "$id"
}

init_sync_state() {
    if [[ ! -f "$SYNC_STATE_FILE" ]]; then
        mkdir -p "$(dirname "$SYNC_STATE_FILE")"
        echo '{"last_sync": null, "files": {}}' > "$SYNC_STATE_FILE"
        echo "NOTE: Bootstrapped empty sync state at $SYNC_STATE_FILE"
    fi
}

# --- Concurrency: per-vault lock (portable, mkdir-based) ---
# Multiple invocations for the same vault must serialize. A manual run and a
# /wiki-update triggered run can overlap; without this lock two concurrent
# sync_file() calls could race and produce fresh duplicates.
#
# Uses `mkdir` (atomic on POSIX filesystems) instead of `flock`, which is not
# installed on macOS by default. Stale-lock detection removes abandoned locks
# left behind by crashed/SIGKILL'd runs.
acquire_lock() {
    local vault_name
    vault_name=$(basename "$VAULT_ROOT")
    LOCK_FILE="/tmp/notebooklm-vault-sync.${vault_name}.lock"

    if mkdir "$LOCK_FILE" 2>/dev/null; then
        echo $$ > "$LOCK_FILE/pid"
        return 0
    fi

    # Lock exists — check for stale lock (holder process is gone)
    local stale_pid=""
    if [[ -f "$LOCK_FILE/pid" ]]; then
        stale_pid=$(cat "$LOCK_FILE/pid" 2>/dev/null | head -1 || true)
    fi

    if [[ -n "$stale_pid" ]] && ! kill -0 "$stale_pid" 2>/dev/null; then
        echo "WARN: removing stale lock from PID $stale_pid" >&2
        rm -rf "$LOCK_FILE"
        mkdir "$LOCK_FILE" 2>/dev/null || die "Could not acquire lock after stale cleanup: $LOCK_FILE"
        echo $$ > "$LOCK_FILE/pid"
        return 0
    fi

    die "Another sync is already running for vault: $vault_name (holder PID: ${stale_pid:-unknown}, lock: $LOCK_FILE)"
}

release_lock() {
    if [[ -n "${LOCK_FILE:-}" ]] && [[ -d "$LOCK_FILE" ]]; then
        # Only remove if we own it
        local holder_pid=""
        [[ -f "$LOCK_FILE/pid" ]] && holder_pid=$(cat "$LOCK_FILE/pid" 2>/dev/null | head -1 || true)
        if [[ "$holder_pid" == "$$" ]]; then
            rm -rf "$LOCK_FILE"
        fi
    fi
}

get_source_id() {
    local relpath="$1"
    jq -r ".files[\"${relpath}\"].source_id // empty" "$SYNC_STATE_FILE"
}

get_stored_hash() {
    local relpath="$1"
    jq -r ".files[\"${relpath}\"].hash // empty" "$SYNC_STATE_FILE"
}

get_file_hash() {
    md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | cut -d' ' -f1
}

# --- Batched state writes ---
# Mutations are queued during sync and flushed once at the end,
# reducing N jq+mktemp+mv cycles to a single jq call.
init_batch() {
    PENDING_UPDATES=$(mktemp)
    PENDING_REMOVES=$(mktemp)
    # Cleanup trap is installed once in main() and calls _cleanup_on_exit.
}

update_sync_state() {
    local relpath="$1" notebook="$2" source_id="$3" hash="$4"
    printf '%s\t%s\t%s\t%s\n' "$relpath" "$notebook" "$source_id" "$hash" >> "$PENDING_UPDATES"
}

remove_from_sync_state() {
    local relpath="$1"
    printf '%s\n' "$relpath" >> "$PENDING_REMOVES"
}

flush_sync_state() {
    [[ -n "${PENDING_UPDATES:-}" ]] || return 0
    [[ -f "${PENDING_UPDATES:-}" ]] || return 0
    [[ -n "${SYNC_STATE_FILE:-}" ]] || return 0
    [[ -f "${SYNC_STATE_FILE:-}" ]] || return 0

    local updates_json="[]"
    if [[ -s "$PENDING_UPDATES" ]]; then
        updates_json=$(jq -R -s '
            split("\n") | map(select(. != "")) | map(
                split("\t") | {p: .[0], n: .[1], s: .[2], h: .[3]}
            )
        ' < "$PENDING_UPDATES")
    fi

    local removes_json="[]"
    if [[ -s "$PENDING_REMOVES" ]]; then
        removes_json=$(jq -R -s 'split("\n") | map(select(. != ""))' < "$PENDING_REMOVES")
    fi

    local tmp
    tmp=$(mktemp)
    jq --argjson updates "$updates_json" \
       --argjson removes "$removes_json" \
       --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       'reduce ($removes[]) as $r (.; del(.files[$r])) |
        reduce ($updates[]) as $u (.; .files[$u.p] = {"notebook": $u.n, "source_id": $u.s, "hash": $u.h}) |
        .last_sync = $ts' \
       "$SYNC_STATE_FILE" > "$tmp" && mv "$tmp" "$SYNC_STATE_FILE"

    : > "$PENDING_UPDATES"
    : > "$PENDING_REMOVES"
}

# Trap handler — surface flush failures instead of silencing them, clean up temps,
# release the per-vault lock.
_cleanup_on_exit() {
    local rc=$?
    if [[ -n "${PENDING_UPDATES:-}" ]] && [[ -f "${PENDING_UPDATES:-}" ]] \
       && [[ -n "${SYNC_STATE_FILE:-}" ]] && [[ -f "${SYNC_STATE_FILE:-}" ]]; then
        if ! flush_sync_state; then
            echo "WARN: failed to flush sync state during cleanup" >&2
        fi
    fi
    [[ -n "${PENDING_UPDATES:-}" ]] && rm -f "$PENDING_UPDATES"
    [[ -n "${PENDING_REMOVES:-}" ]] && rm -f "$PENDING_REMOVES"
    [[ -n "${VAULT_FILES:-}" ]] && rm -f "$VAULT_FILES"
    [[ -n "${NOTEBOOK_SOURCES_DIR:-}" ]] && rm -rf "$NOTEBOOK_SOURCES_DIR"
    release_lock
    return $rc
}

# --- Routing ---
# Inferred from notebook keys in config.json:
#   Single key  -> all files route there
#   Multi-key   -> Infrastructure/* routes to "infra" if present, else first non-infra key
route_to_notebook() {
    local relpath="$1"

    if [[ ${#NOTEBOOK_KEYS[@]} -eq 1 ]]; then
        echo "${NOTEBOOK_KEYS[0]}"
        return
    fi

    if [[ "$relpath" == Infrastructure/* ]]; then
        for key in "${NOTEBOOK_KEYS[@]}"; do
            if [[ "$key" == "infra" ]]; then
                echo "infra"
                return
            fi
        done
    fi

    for key in "${NOTEBOOK_KEYS[@]}"; do
        if [[ "$key" != "infra" ]]; then
            echo "$key"
            return
        fi
    done

    echo "${NOTEBOOK_KEYS[0]}"
}

is_excluded() {
    local path="$1"
    for excl in "${EXCLUDES[@]}"; do
        if [[ "$path" == "$excl/"* ]] || [[ "$path" == *"/$excl/"* ]] || [[ "$path" == *"/$excl" ]]; then
            return 0
        fi
    done
    return 1
}

# --- Detect a standalone vault by structure ---
# A standalone vault has its metadata directories (_meta/, _Templates/, TaskNotes/)
# directly at the vault root, with no wrapping project subdirectory. This makes
# the layout self-describing: even if the project-level config writes
# vault_root: "vault" (centralized + standalone, written by /ark-onboard), the
# script can detect the layout from disk and scan correctly.
is_standalone_vault() {
    local root="$1"
    [[ -d "$root/_meta" ]] || [[ -d "$root/_Templates" ]] || [[ -d "$root/TaskNotes" ]]
}

# --- Determine scan base directory ---
# Standalone vault: scan VAULT_ROOT directly (root-level .md + all non-excluded subdirs).
#   Detected via vault_root: "." OR by structure (marker directories at root).
# Wrapped vault: scan the first non-excluded project subdirectory (e.g. vault/ArkNode-Poly/).
resolve_scan_base() {
    local mode="$1"
    local scan_base

    if [[ "$VAULT_ROOT_REL" == "." ]] || is_standalone_vault "$VAULT_ROOT"; then
        scan_base="$VAULT_ROOT"
    else
        # Wrapped: discover the project subdirectory
        local candidate name
        scan_base=""
        for candidate in "$VAULT_ROOT"/*/; do
            [[ -d "$candidate" ]] || continue
            name=$(basename "$candidate")
            local skip=false
            for excl in "${EXCLUDES[@]}"; do
                if [[ "$name" == "$excl" ]]; then
                    skip=true
                    break
                fi
            done
            if [[ "$skip" == "false" ]]; then
                scan_base="$VAULT_ROOT/$name"
                break
            fi
        done
        [[ -n "$scan_base" ]] || die "Wrapped vault at $VAULT_ROOT has no project subdirectory (all subdirs excluded)."
    fi

    if [[ "$mode" == "sessions-only" ]]; then
        scan_base="$scan_base/Session-Logs"
    fi

    echo "$scan_base"
}

# --- Build vault file list with collision detection ---
# Scans the vault per mode, produces a tab-separated file: title<TAB>relpath<TAB>nb_key.
# Fails loudly if two files share a basename within the same notebook.
build_vault_file_list() {
    local mode="$1"
    local scan_base
    scan_base=$(resolve_scan_base "$mode")
    [[ -d "$scan_base" ]] || die "Scan directory not found: $scan_base"

    VAULT_FILES=$(mktemp)

    while IFS= read -r filepath; do
        local relpath title nb_key
        relpath="${filepath#"$VAULT_ROOT"/}"
        if is_excluded "$relpath"; then continue; fi
        title=$(basename "$relpath")
        nb_key=$(route_to_notebook "$relpath")
        printf '%s\t%s\t%s\n' "$title" "$relpath" "$nb_key" >> "$VAULT_FILES"
    done < <(find -L "$scan_base" -name "*.md" -type f | sort)

    [[ -s "$VAULT_FILES" ]] || { echo "WARN: No files discovered in $scan_base"; return 0; }

    detect_basename_collisions
}

# --- Collision detection (fail-loud) ---
# NotebookLM titles file sources by basename only (hardcoded in add_file()).
# If two vault files share a basename AND route to the same notebook, they'd
# clobber each other. Fail loudly and require manual resolution.
detect_basename_collisions() {
    local collision_keys
    collision_keys=$(awk -F'\t' '{print $3 "|" $1}' "$VAULT_FILES" | sort | uniq -c | awk '$1 > 1 {$1=""; sub(/^ +/, ""); print}')
    [[ -z "$collision_keys" ]] && return 0

    echo "" >&2
    echo "FATAL: Filename collisions detected." >&2
    echo "NotebookLM identifies file sources by basename only. Two files with the" >&2
    echo "same basename in the same notebook would overwrite each other." >&2
    echo "" >&2

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        local nb_key title
        nb_key="${line%%|*}"
        title="${line#*|}"
        echo "  Notebook: $nb_key" >&2
        echo "  Title:    $title" >&2
        echo "  Conflicting paths:" >&2
        awk -F'\t' -v t="$title" -v n="$nb_key" '$1 == t && $3 == n { print "    - " $2 }' "$VAULT_FILES" >&2
        echo "" >&2
    done <<< "$collision_keys"

    echo "Resolve by renaming one of the files or moving one to an excluded directory." >&2
    die "Filename collisions prevent safe sync. Resolve before retrying."
}

# --- Nuke all sources from a notebook ---
# Used by --full mode to guarantee no orphaned duplicates survive.
nuke_notebook_sources() {
    local nb_id="$1" nb_label="$2"
    local source_ids count

    echo "  Deleting all sources from $nb_label notebook ($nb_id)..."
    source_ids=$(notebooklm source list --notebook "$nb_id" --json 2>/dev/null | jq -r '.sources[].id') || {
        echo "  WARN: Could not list sources for $nb_label"
        return 1
    }

    count=0
    for sid in $source_ids; do
        notebooklm source delete --notebook "$nb_id" --yes "$sid" >/dev/null 2>&1 || true
        count=$((count + 1))
    done
    echo "  Deleted $count sources from $nb_label notebook"
}

# --- Fetch source lists from NotebookLM (one RPC per notebook) ---
# Writes per-notebook caches to $NOTEBOOK_SOURCES_DIR/<key> with one line per
# source: title<TAB>id<TAB>status<TAB>created_at
fetch_notebook_sources() {
    NOTEBOOK_SOURCES_DIR=$(mktemp -d)

    local seen_keys=" "
    for key in "${NOTEBOOK_KEYS[@]}"; do
        [[ "$seen_keys" == *" $key "* ]] && continue
        seen_keys+="$key "

        local nb_id raw err_log
        nb_id=$(get_notebook_id "$key")
        # Capture stderr separately. Folding it into stdout (2>&1) breaks jq when
        # notebooklm-py prints runtime warnings (e.g. on empty notebooks it logs
        # "Sources data ... is not a list"), since the warning ends up at the
        # start of $raw and jq fails parsing.
        err_log=$(mktemp)
        if ! raw=$(notebooklm source list --notebook "$nb_id" --json 2>"$err_log"); then
            local err_msg
            err_msg=$(cat "$err_log")
            rm -f "$err_log"
            die "Failed to list sources for notebook '$key' ($nb_id): $err_msg"
        fi
        rm -f "$err_log"
        echo "$raw" | jq -r '.sources[] | [.title, .id, (.status // "UNKNOWN"), (.created_at // "")] | @tsv' \
            > "$NOTEBOOK_SOURCES_DIR/$key"
    done
}

# --- Dedupe + orphan prune + state reconciliation (per notebook) ---
# 1) For each title with >1 source: pick survivor by status rank
#    (READY > PROCESSING > ERROR > other), tie-break by oldest created_at.
#    Delete the rest.
# 2) Orphan prune: delete .md sources whose title doesn't match any vault file
#    routed to this notebook. Non-.md sources are preserved (manual PDFs, URLs).
# 3) Refresh the local cache file from NotebookLM if anything was mutated.
dedupe_and_heal_notebook() {
    local nb_key="$1"
    local nb_id sources_file
    nb_id=$(get_notebook_id "$nb_key")
    sources_file="$NOTEBOOK_SOURCES_DIR/$nb_key"

    [[ -s "$sources_file" ]] || { echo "Heal pass: $nb_key — notebook empty, skip"; return 0; }

    echo ""
    echo "Heal pass: $nb_key ($nb_id)"

    local initial_count
    initial_count=$(wc -l < "$sources_file" | tr -d ' ')
    echo "  Initial sources in notebook: $initial_count"

    local expected_file all_titles_file orphans_file
    expected_file=$(mktemp)
    all_titles_file=$(mktemp)
    orphans_file=$(mktemp)

    awk -F'\t' -v k="$nb_key" '$3 == k { print $1 }' "$VAULT_FILES" | sort -u > "$expected_file"
    awk -F'\t' '{print $1}' "$sources_file" | sort -u > "$all_titles_file"

    # --- Pass 1: Dedupe within title ---
    local deleted_count=0
    local duped_titles
    duped_titles=$(awk -F'\t' '{print $1}' "$sources_file" | sort | uniq -c | awk '$1 > 1 {$1=""; sub(/^ +/, ""); print}')

    if [[ -n "$duped_titles" ]]; then
        while IFS= read -r title; do
            [[ -z "$title" ]] && continue

            # Pick survivor: lowest status_rank, tie-break by oldest created_at.
            # status_rank: READY=0, PROCESSING=1, ERROR=2, other=3.
            local survivor_id
            survivor_id=$(awk -F'\t' -v t="$title" '
                $1 == t {
                    rank = 3
                    if ($3 == "READY") rank = 0
                    else if ($3 == "PROCESSING") rank = 1
                    else if ($3 == "ERROR") rank = 2
                    print rank "\t" $4 "\t" $2
                }
            ' "$sources_file" | LC_ALL=C sort -t $'\t' -k1,1n -k2,2 | head -1 | awk -F'\t' '{print $3}')

            [[ -z "$survivor_id" ]] && continue

            local dup_count
            dup_count=$(awk -F'\t' -v t="$title" '$1 == t' "$sources_file" | wc -l | tr -d ' ')
            echo "  DEDUPE: '$title' has $dup_count copies -> keep $survivor_id"

            while IFS= read -r del_id; do
                [[ -z "$del_id" ]] && continue
                if notebooklm source delete --notebook "$nb_id" --yes "$del_id" >/dev/null 2>&1; then
                    echo "    deleted: $del_id"
                    deleted_count=$((deleted_count + 1))
                else
                    echo "    WARN: failed to delete: $del_id"
                fi
                sleep 0.25
            done < <(awk -F'\t' -v t="$title" -v sid="$survivor_id" '$1 == t && $2 != sid {print $2}' "$sources_file")
        done <<< "$duped_titles"
    fi

    # --- Pass 2: Orphan prune ---
    # Only .md sources are considered orphans; non-.md sources (user-added PDFs,
    # URLs, etc.) are preserved.
    comm -23 "$all_titles_file" "$expected_file" | grep '\.md$' > "$orphans_file" || true

    local orphan_count
    orphan_count=$(wc -l < "$orphans_file" | tr -d ' ')

    if [[ "$orphan_count" -gt 0 ]]; then
        echo "  Orphan prune: $orphan_count .md titles not in vault"
        while IFS= read -r orphan_title; do
            [[ -z "$orphan_title" ]] && continue
            while IFS= read -r orphan_id; do
                [[ -z "$orphan_id" ]] && continue
                if notebooklm source delete --notebook "$nb_id" --yes "$orphan_id" >/dev/null 2>&1; then
                    echo "    ORPHAN-DELETED: '$orphan_title' ($orphan_id)"
                    deleted_count=$((deleted_count + 1))
                    DELETED=$((DELETED + 1))
                else
                    echo "    WARN: failed to delete orphan '$orphan_title' ($orphan_id)"
                fi
                sleep 0.25
            done < <(awk -F'\t' -v t="$orphan_title" '$1 == t {print $2}' "$sources_file")
        done < "$orphans_file"
    fi

    # --- Refresh local cache from NotebookLM if anything was mutated ---
    if [[ "$deleted_count" -gt 0 ]]; then
        local fresh err_log
        # Same stderr-vs-stdout discipline as fetch_notebook_sources: never fold
        # stderr into the JSON we hand to jq.
        err_log=$(mktemp)
        if fresh=$(notebooklm source list --notebook "$nb_id" --json 2>"$err_log"); then
            rm -f "$err_log"
            echo "$fresh" | jq -r '.sources[] | [.title, .id, (.status // "UNKNOWN"), (.created_at // "")] | @tsv' \
                > "$sources_file"
            local final_count
            final_count=$(wc -l < "$sources_file" | tr -d ' ')
            echo "  Heal complete: $initial_count -> $final_count sources ($deleted_count deleted)"
        else
            local err_msg
            err_msg=$(cat "$err_log")
            rm -f "$err_log"
            echo "  WARN: Could not refresh source list after heal: $err_msg"
        fi
    else
        echo "  Heal complete: no changes needed"
    fi

    rm -f "$expected_file" "$all_titles_file" "$orphans_file"
}

# --- Add with post-failure recovery ---
# notebooklm-py's add_file() does register -> start-upload -> stream. If any
# step after register fails, the server-side source is already registered.
# The CLI raises non-zero but never cleans up. Without this recovery path the
# script would retry on the next run and create another ghost -> duplicates.
#
# On failure (non-zero exit OR unparseable JSON), re-list the notebook and
# diff against the pre-add snapshot. If exactly one new source with this title
# appeared, claim it. If 0 (true step-1 failure) or >1 (concurrent add or
# unhealthy state), report error.
#
# Writes the resolved source ID to stdout, nothing to stdout on failure.
add_with_recovery() {
    local filepath="$1" nb_id="$2"
    local title result add_rc new_source_id
    title=$(basename "$filepath")

    local pre_tmp post_tmp new_ids_file
    pre_tmp=$(mktemp)
    post_tmp=$(mktemp)
    new_ids_file=$(mktemp)

    # Snapshot IDs with this title BEFORE the add. If the list call fails we
    # continue with an empty snapshot — the recovery count will simply detect
    # "new IDs" that include pre-existing ones, which is handled below.
    notebooklm source list --notebook "$nb_id" --json 2>/dev/null \
        | jq -r --arg t "$title" '.sources[] | select(.title == $t) | .id' 2>/dev/null \
        | LC_ALL=C sort > "$pre_tmp" || : > "$pre_tmp"

    # Attempt the add. Capture both stdout+stderr and rc without tripping -e.
    set +e
    result=$(notebooklm source add "$filepath" --type file --notebook "$nb_id" --json 2>&1)
    add_rc=$?
    set -e

    # Happy path
    if [[ "$add_rc" -eq 0 ]]; then
        new_source_id=$(echo "$result" | jq -r '.source.id // empty' 2>/dev/null || true)
        if [[ -n "$new_source_id" ]]; then
            rm -f "$pre_tmp" "$post_tmp" "$new_ids_file"
            printf '%s\n' "$new_source_id"
            return 0
        fi
    fi

    # Recovery path
    echo "    recovery: rc=$add_rc, re-listing to detect ghost registration" >&2
    notebooklm source list --notebook "$nb_id" --json 2>/dev/null \
        | jq -r --arg t "$title" '.sources[] | select(.title == $t) | .id' 2>/dev/null \
        | LC_ALL=C sort > "$post_tmp" || : > "$post_tmp"

    comm -23 "$post_tmp" "$pre_tmp" > "$new_ids_file" || true

    local new_count
    new_count=$(grep -c . "$new_ids_file" 2>/dev/null || true)
    new_count=${new_count:-0}

    if [[ "$new_count" -eq 1 ]]; then
        new_source_id=$(head -1 "$new_ids_file")
        echo "    RECOVERED ghost registration for '$title' -> $new_source_id" >&2
        rm -f "$pre_tmp" "$post_tmp" "$new_ids_file"
        printf '%s\n' "$new_source_id"
        return 0
    fi

    echo "    RECOVERY FAILED: rc=$add_rc, new_registrations=$new_count" >&2
    echo "    msg: $result" >&2
    rm -f "$pre_tmp" "$post_tmp" "$new_ids_file"
    return 1
}

# --- Sync a single file (notebook-authoritative) ---
# Uses the notebook source cache (built by fetch_notebook_sources + dedupe_and_heal_notebook)
# as the source of truth for existence. State is consulted only for hash caching.
sync_file() {
    local relpath="$1"
    local filepath="$VAULT_ROOT/$relpath"
    local title nb_key nb_id sources_file existing_id stored_hash current_hash new_id

    if [[ ! -f "$filepath" ]]; then
        echo "  SKIP (not found): $relpath"
        return 1
    fi

    title=$(basename "$relpath")
    nb_key=$(route_to_notebook "$relpath")
    nb_id=$(get_notebook_id "$nb_key")
    sources_file="$NOTEBOOK_SOURCES_DIR/$nb_key"
    current_hash=$(get_file_hash "$filepath")
    stored_hash=$(get_stored_hash "$relpath")

    # After dedupe, each title has at most one source. Look it up.
    existing_id=""
    if [[ -f "$sources_file" ]]; then
        existing_id=$(awk -F'\t' -v t="$title" '$1 == t {print $2; exit}' "$sources_file")
    fi

    if [[ -n "$existing_id" ]]; then
        # Source exists in notebook
        if [[ "$current_hash" == "$stored_hash" ]] || [[ -z "$stored_hash" ]]; then
            # Hash matches, OR state has no hash (bootstrap: source exists in
            # notebook but state was wiped/missing). Record the current hash
            # without re-uploading. If the file changed since the notebook copy,
            # the next run after this bootstrap will detect the hash mismatch.
            update_sync_state "$relpath" "$nb_key" "$existing_id" "$current_hash"
            UNCHANGED=$((UNCHANGED + 1))
            return 0
        fi

        # Changed — delete + re-add
        if ! notebooklm source delete --notebook "$nb_id" --yes "$existing_id" >/dev/null 2>&1; then
            echo "  WARN: pre-update delete failed for $relpath (existing: $existing_id)"
        fi
        if ! new_id=$(add_with_recovery "$filepath" "$nb_id"); then
            echo "  ERROR (update): $relpath"
            return 1
        fi
        update_sync_state "$relpath" "$nb_key" "$new_id" "$current_hash"
        # Refresh local cache: remove old row, add new row
        awk -F'\t' -v id="$existing_id" '$2 != id' "$sources_file" > "$sources_file.tmp" \
            && mv "$sources_file.tmp" "$sources_file"
        printf '%s\t%s\tPROCESSING\t%s\n' "$title" "$new_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$sources_file"
        echo "  UPDATED: $relpath -> $nb_key ($new_id)"
        UPDATED=$((UPDATED + 1))
        return 0
    fi

    # Not in notebook — add fresh
    if ! new_id=$(add_with_recovery "$filepath" "$nb_id"); then
        echo "  ERROR (add): $relpath"
        return 1
    fi
    update_sync_state "$relpath" "$nb_key" "$new_id" "$current_hash"
    printf '%s\t%s\tPROCESSING\t%s\n' "$title" "$new_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$sources_file"
    echo "  ADDED: $relpath -> $nb_key ($new_id)"
    ADDED=$((ADDED + 1))
}

# --- State-driven deletion pass ---
# Removes sources for vault files that no longer exist. Only removes state
# when remote deletion actually succeeds (or the source is already gone) —
# previous versions cleared state even on delete failure, leaking orphans.
state_deletion_pass() {
    local state_entries
    state_entries=$(jq -r '.files | to_entries[] | [.key, .value.notebook, .value.source_id] | @tsv' "$SYNC_STATE_FILE")
    [[ -z "$state_entries" ]] && return 0

    while IFS=$'\t' read -r relpath nb_key source_id; do
        [[ -z "$relpath" ]] && continue
        local filepath="$VAULT_ROOT/$relpath"
        [[ -f "$filepath" ]] && continue

        local nb_id
        nb_id=$(get_notebook_id "$nb_key")

        if [[ -z "$source_id" ]]; then
            remove_from_sync_state "$relpath"
            continue
        fi

        if notebooklm source delete --notebook "$nb_id" --yes "$source_id" >/dev/null 2>&1; then
            remove_from_sync_state "$relpath"
            DELETED=$((DELETED + 1))
            echo "  DELETED: $relpath (source: $source_id)"
            continue
        fi

        # Delete failed — maybe the source is already gone. Verify before
        # clearing state, otherwise we leak orphans permanently.
        local verify
        verify=$(notebooklm source list --notebook "$nb_id" --json 2>/dev/null \
                 | jq -r --arg id "$source_id" '.sources[] | select(.id == $id) | .id' 2>/dev/null || true)
        if [[ -z "$verify" ]]; then
            remove_from_sync_state "$relpath"
            DELETED=$((DELETED + 1))
            echo "  DELETED (already gone): $relpath"
        else
            echo "  WARN: deletion failed for orphan $relpath (source $source_id still exists)"
        fi
    done <<< "$state_entries"
}

# --- Main ---
main() {
    local mode="incremental"
    local single_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --full) mode="full"; shift ;;
            --sessions-only) mode="sessions-only"; shift ;;
            --file) single_file="$2"; shift 2 ;;
            *) die "Unknown argument: $1" ;;
        esac
    done

    check_prereqs
    load_notebook_keys

    # Install cleanup trap BEFORE any mktemp calls
    trap _cleanup_on_exit EXIT

    # Serialize per-vault runs
    acquire_lock

    init_sync_state
    init_batch

    echo "NotebookLM Vault Sync"
    echo "  Config: $CONFIG_FILE"
    echo "  Vault root: $VAULT_ROOT"
    echo "  Mode: $mode"
    echo "  Notebooks: ${NOTEBOOK_KEYS[*]}"
    for key in "${NOTEBOOK_KEYS[@]}"; do
        echo "    $key: $(get_notebook_id "$key")"
    done
    echo ""

    if [[ -n "$single_file" ]]; then
        # Single-file path: fetch the target notebook's source list so sync_file
        # can check existence. No dedupe/heal — dispatch-triggered runs stay fast.
        local nb_key nb_id
        nb_key=$(route_to_notebook "$single_file")
        nb_id=$(get_notebook_id "$nb_key")
        NOTEBOOK_SOURCES_DIR=$(mktemp -d)
        notebooklm source list --notebook "$nb_id" --json 2>/dev/null \
            | jq -r '.sources[] | [.title, .id, (.status // "UNKNOWN"), (.created_at // "")] | @tsv' \
            > "$NOTEBOOK_SOURCES_DIR/$nb_key"
        echo "Syncing single file: $single_file"
        sync_file "$single_file" || ERRORS=$((ERRORS + 1))
    else
        if [[ "$mode" == "full" ]]; then
            echo "Full sync: clearing all sources from targeted notebooks..."
            local seen_notebooks=" "
            for key in "${NOTEBOOK_KEYS[@]}"; do
                if [[ "$seen_notebooks" != *" $key "* ]]; then
                    seen_notebooks+="$key "
                    local nb_id
                    nb_id=$(get_notebook_id "$key")
                    nuke_notebook_sources "$nb_id" "$key"
                fi
            done

            # Reset sync state
            local tmp
            tmp=$(mktemp)
            jq '.files = {} | .last_sync = null' "$SYNC_STATE_FILE" > "$tmp" && mv "$tmp" "$SYNC_STATE_FILE"
            echo ""
        fi

        # Build vault file list (with collision detection)
        build_vault_file_list "$mode"

        # Fetch notebook source lists (one RPC per notebook)
        fetch_notebook_sources

        # Dedupe + orphan prune (skip for --full since we just nuked everything)
        if [[ "$mode" != "full" ]]; then
            for key in "${NOTEBOOK_KEYS[@]}"; do
                dedupe_and_heal_notebook "$key"
            done
            echo ""
        fi

        # Sync pass
        if [[ -s "$VAULT_FILES" ]]; then
            while IFS=$'\t' read -r _title relpath _nb_key; do
                [[ -z "$relpath" ]] && continue
                sync_file "$relpath" || ERRORS=$((ERRORS + 1))
            done < "$VAULT_FILES"
        fi

        # State-driven deletion pass (for files removed from the vault between runs).
        # Skipped in --full mode since state was just reset.
        if [[ "$mode" != "full" ]]; then
            echo ""
            echo "Checking for deleted vault files..."
            state_deletion_pass
        fi
    fi

    # flush happens in _cleanup_on_exit; exit code passes through
    echo ""
    echo "Sync complete:"
    echo "  Added:     $ADDED"
    echo "  Updated:   $UPDATED"
    echo "  Unchanged: $UNCHANGED"
    echo "  Deleted:   $DELETED"
    echo "  Errors:    $ERRORS"
}

main "$@"
