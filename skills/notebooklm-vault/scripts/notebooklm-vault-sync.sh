#!/usr/bin/env bash
# notebooklm-vault-sync.sh — Incremental vault-to-NotebookLM sync
#
# Usage:
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh              # Incremental sync (new/changed only)
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --full        # Re-import everything
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --sessions-only  # Only session logs
#   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --file PATH      # Single file (relative to vault root)
#
# Expects to be run from the project root.

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

# Sync state: always in the vault's .notebooklm/
VAULT_ROOT=$(jq -r '.vault_root' "$CONFIG_FILE")
if [[ "$VAULT_ROOT" == "." ]]; then
    VAULT_NOTEBOOKLM="$(dirname "$CONFIG_FILE")"
else
    VAULT_NOTEBOOKLM="$PROJECT_ROOT/$VAULT_ROOT/.notebooklm"
fi
SYNC_STATE_FILE="$VAULT_NOTEBOOKLM/sync-state.json"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"

# Excluded directories (relative patterns)
EXCLUDES=(".obsidian" ".git" "_Templates" "_Attachments" ".claude-plugin")

# Batched state management temp files
PENDING_UPDATES=""
PENDING_REMOVES=""

check_prereqs() {
    command -v notebooklm >/dev/null 2>&1 || die "notebooklm CLI not found. Install with: pipx install notebooklm-py"
    command -v jq >/dev/null 2>&1 || die "jq not found. Install with: brew install jq"
    [[ -f "$CONFIG_FILE" ]] || die "Config not found at $CONFIG_FILE. Run '/notebooklm-vault setup' first."
}

get_notebook_id() {
    local key="$1"
    jq -r ".notebooks.${key}.id" "$CONFIG_FILE"
}

get_vault_root() {
    local rel
    rel=$(jq -r '.vault_root' "$CONFIG_FILE")
    if [[ "$rel" == "." ]]; then
        # Config is inside the vault — vault root is one level up from .notebooklm/
        echo "$(cd "$(dirname "$CONFIG_FILE")/.." && pwd)"
    else
        echo "$(cd "$PROJECT_ROOT/$rel" && pwd)"
    fi
}

init_sync_state() {
    if [[ ! -f "$SYNC_STATE_FILE" ]]; then
        mkdir -p "$(dirname "$SYNC_STATE_FILE")"
        echo '{"last_sync": null, "files": {}}' > "$SYNC_STATE_FILE"
        echo "NOTE: Bootstrapped empty sync state at $SYNC_STATE_FILE"
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
# reducing ~N jq+mktemp+mv cycles to a single jq call.

init_batch() {
    PENDING_UPDATES=$(mktemp)
    PENDING_REMOVES=$(mktemp)
    trap 'flush_sync_state 2>/dev/null; rm -f "$PENDING_UPDATES" "$PENDING_REMOVES"' EXIT
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

    # Build updates JSON array from TSV
    local updates_json="[]"
    if [[ -s "$PENDING_UPDATES" ]]; then
        updates_json=$(jq -R -s '
            split("\n") | map(select(. != "")) | map(
                split("\t") | {p: .[0], n: .[1], s: .[2], h: .[3]}
            )
        ' < "$PENDING_UPDATES")
    fi

    # Build removes JSON array
    local removes_json="[]"
    if [[ -s "$PENDING_REMOVES" ]]; then
        removes_json=$(jq -R -s 'split("\n") | map(select(. != ""))' < "$PENDING_REMOVES")
    fi

    # Apply all mutations + update timestamp in one jq call
    local tmp
    tmp=$(mktemp)
    jq --argjson updates "$updates_json" \
       --argjson removes "$removes_json" \
       --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       'reduce ($removes[]) as $r (.; del(.files[$r])) |
        reduce ($updates[]) as $u (.; .files[$u.p] = {"notebook": $u.n, "source_id": $u.s, "hash": $u.h}) |
        .last_sync = $ts' \
       "$SYNC_STATE_FILE" > "$tmp" && mv "$tmp" "$SYNC_STATE_FILE"

    # Clear pending files
    : > "$PENDING_UPDATES"
    : > "$PENDING_REMOVES"
}

route_to_notebook() {
    # Single notebook for this project
    echo "main"
}

is_excluded() {
    local path="$1"
    for excl in "${EXCLUDES[@]}"; do
        if [[ "$path" == *"/$excl/"* ]] || [[ "$path" == *"/$excl" ]]; then
            return 0
        fi
    done
    return 1
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
        notebooklm source delete --notebook "$nb_id" --yes "$sid" 2>/dev/null || true
        count=$((count + 1))
    done
    echo "  Deleted $count sources from $nb_label notebook"
}

# --- Sync a single file ---
sync_file() {
    local vault_root="$1" relpath="$2"
    local filepath="$vault_root/$relpath"
    local nb_key source_id stored_hash current_hash nb_id result new_source_id

    if [[ ! -f "$filepath" ]]; then
        echo "  SKIP (not found): $relpath"
        return 1
    fi

    nb_key=$(route_to_notebook "$relpath")
    nb_id=$(get_notebook_id "$nb_key")
    source_id=$(get_source_id "$relpath")
    stored_hash=$(get_stored_hash "$relpath")
    current_hash=$(get_file_hash "$filepath")

    if [[ -z "$source_id" ]]; then
        # New file — add it
        result=$(notebooklm source add "$filepath" --type file --notebook "$nb_id" --json 2>&1) || {
            echo "  ERROR (add): $relpath — $result"
            return 1
        }
        new_source_id=$(echo "$result" | jq -r '.source.id // empty')
        if [[ -z "$new_source_id" ]]; then
            echo "  ERROR (parse): $relpath — no source_id in: $result"
            return 1
        fi
        update_sync_state "$relpath" "$nb_key" "$new_source_id" "$current_hash"
        echo "  ADDED: $relpath → $nb_key ($new_source_id)"
        ADDED=$((ADDED + 1))
    elif [[ "$current_hash" != "$stored_hash" ]]; then
        # Changed file — delete old, re-add
        notebooklm source delete --notebook "$nb_id" --yes "$source_id" 2>/dev/null || true
        result=$(notebooklm source add "$filepath" --type file --notebook "$nb_id" --json 2>&1) || {
            echo "  ERROR (update): $relpath — $result"
            return 1
        }
        new_source_id=$(echo "$result" | jq -r '.source.id // empty')
        if [[ -z "$new_source_id" ]]; then
            echo "  ERROR (parse): $relpath — no source_id in: $result"
            return 1
        fi
        update_sync_state "$relpath" "$nb_key" "$new_source_id" "$current_hash"
        echo "  UPDATED: $relpath → $nb_key ($new_source_id)"
        UPDATED=$((UPDATED + 1))
    else
        UNCHANGED=$((UNCHANGED + 1))
    fi
}

# --- Main ---
main() {
    check_prereqs
    init_sync_state
    init_batch

    local vault_root mode single_file
    vault_root=$(get_vault_root)
    mode="incremental"
    single_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --full) mode="full"; shift ;;
            --sessions-only) mode="sessions-only"; shift ;;
            --file) single_file="$2"; shift 2 ;;
            *) die "Unknown argument: $1" ;;
        esac
    done

    ADDED=0
    UPDATED=0
    UNCHANGED=0
    ERRORS=0

    echo "NotebookLM Vault Sync"
    echo "  Vault root: $vault_root"
    echo "  Mode: $mode"
    echo "  Notebook: $(get_notebook_id main)"
    echo ""

    if [[ -n "$single_file" ]]; then
        echo "Syncing single file: $single_file"
        sync_file "$vault_root" "$single_file" || ERRORS=$((ERRORS + 1))
    else
        # Determine which directories to scan
        local dirs=()
        case "$mode" in
            sessions-only)
                # Discover project docs path from config vault_root
                local project_dir
                project_dir=$(ls -d "$vault_root"/*/ 2>/dev/null | grep -v TaskNotes | grep -v _Templates | grep -v _Attachments | grep -v _meta | grep -v .obsidian | head -1)
                project_dir="${project_dir#$vault_root/}"
                project_dir="${project_dir%/}"
                dirs=("${project_dir}/Session-Logs")
                ;;
            *)
                # Scan all non-system directories
                local project_dir
                project_dir=$(ls -d "$vault_root"/*/ 2>/dev/null | grep -v TaskNotes | grep -v _Templates | grep -v _Attachments | grep -v _meta | grep -v .obsidian | head -1)
                project_dir="${project_dir#$vault_root/}"
                project_dir="${project_dir%/}"
                dirs=("${project_dir}")
                ;;
        esac

        # Full mode: nuke all sources from the notebook FIRST,
        # then reset sync state. This prevents orphaned duplicates
        # that accumulate when sync state gets out of sync with
        # the actual NotebookLM sources.
        if [[ "$mode" == "full" ]]; then
            echo "Full sync: clearing all sources from notebook..."
            local nb_id
            nb_id=$(get_notebook_id "main")
            nuke_notebook_sources "$nb_id" "main"

            # Reset sync state for all files
            local tmp
            tmp=$(mktemp)
            jq '.files = {} | .last_sync = null' "$SYNC_STATE_FILE" > "$tmp" && mv "$tmp" "$SYNC_STATE_FILE"
            echo ""
        fi

        for dir in "${dirs[@]}"; do
            local scan_dir="$vault_root/$dir"
            [[ -d "$scan_dir" ]] || { echo "WARN: Directory not found: $scan_dir"; continue; }

            echo "Scanning: $dir/"
            while IFS= read -r filepath; do
                # Get path relative to vault root
                local relpath="${filepath#$vault_root/}"

                # Check exclusions
                if is_excluded "$relpath"; then
                    continue
                fi

                sync_file "$vault_root" "$relpath" || ERRORS=$((ERRORS + 1))
            done < <(find "$scan_dir" -name "*.md" -type f | sort)
        done
    fi

    # --- Deletion pass: remove orphaned sources ---
    DELETED=0
    if [[ "$mode" != "full" ]] && [[ -z "$single_file" ]]; then
        echo ""
        echo "Checking for deleted vault files..."
        while IFS=$'\t' read -r relpath nb_key source_id; do
            local filepath="$vault_root/$relpath"
            if [[ ! -f "$filepath" ]]; then
                local nb_id
                nb_id=$(get_notebook_id "$nb_key")
                if [[ -n "$source_id" ]]; then
                    notebooklm source delete --notebook "$nb_id" --yes "$source_id" 2>/dev/null || true
                fi
                remove_from_sync_state "$relpath"
                echo "  DELETED: $relpath (source: ${source_id:-unknown})"
                DELETED=$((DELETED + 1))
            fi
        done < <(jq -r '.files | to_entries[] | [.key, .value.notebook, .value.source_id] | @tsv' "$SYNC_STATE_FILE")
    fi

    # Flush all batched state mutations to disk
    flush_sync_state

    echo ""
    echo "Sync complete:"
    echo "  Added:     $ADDED"
    echo "  Updated:   $UPDATED"
    echo "  Unchanged: $UNCHANGED"
    echo "  Deleted:   $DELETED"
    echo "  Errors:    $ERRORS"
}

main "$@"
