#!/bin/bash
# mine-vault.sh — Index vault markdown files into MemPalace
#
# Usage: bash skills/shared/mine-vault.sh
#
# Reads CLAUDE.md for vault path, detects symlink vs real dir,
# filters to .md files only, and mines into the correct wing.
#
# Prerequisites: mempalace installed (pipx install mempalace)

set -euo pipefail

# === STEP 1: Find vault path ===
# Accept vault path as argument (for monorepo hub setups where context-discovery
# resolves through sub-project CLAUDEs — Claude does the discovery, passes the path).
# If no argument, extract from CLAUDE.md's Project Configuration table.
if [ -n "${1:-}" ] && [ -e "$1" ]; then
    VAULT_PATH="${1%/}"
    echo "Using vault path from argument: $VAULT_PATH"
else
    if [ ! -f "CLAUDE.md" ]; then
        echo "ERROR: No CLAUDE.md in current directory. Run from project root."
        echo "Usage: bash skills/shared/mine-vault.sh [vault_path]"
        exit 1
    fi

    # Extract vault path — find the backtick-enclosed value on the "Obsidian Vault" row
    VAULT_PATH=$(grep "Obsidian Vault" CLAUDE.md | grep -o '`[^`]*`' | head -1 | tr -d '`' | sed 's|/$||')

    # Fallback: check common locations
    if [ -z "$VAULT_PATH" ] || [ ! -e "$VAULT_PATH" ]; then
        for CANDIDATE in vault Vault obsidian; do
            if [ -e "$CANDIDATE" ]; then
                VAULT_PATH="$CANDIDATE"
                break
            fi
        done
    fi
fi

# Normalize: strip trailing slash, then make absolute so symlinks in
# the temp dir (STEP 4) resolve correctly regardless of CWD.
VAULT_PATH="${VAULT_PATH%/}"
[[ "$VAULT_PATH" = /* ]] || VAULT_PATH="$PWD/$VAULT_PATH"

if [ ! -e "$VAULT_PATH" ]; then
    echo "ERROR: Vault not found at '$VAULT_PATH'."
    echo "Usage: bash skills/shared/mine-vault.sh [vault_path]"
    echo "Or check CLAUDE.md's 'Obsidian Vault' row, or create a symlink:"
    echo "  ln -s /path/to/your/vault ./vault"
    exit 1
fi

# === STEP 2: Check mempalace is installed ===
if ! command -v mempalace &>/dev/null; then
    echo "ERROR: mempalace not found. Install it:"
    echo "  pipx install 'mempalace>=3.0.0,<4.0.0'"
    exit 1
fi

# === STEP 3: Detect vault type and derive wing ===
# MINE_VAULT_WING env var overrides auto-derivation. Useful for centralized vaults
# where the user wants vault content + history-hook drawers to land in the same
# wing (the hook always uses $PWD-based key, so passing
# MINE_VAULT_WING=$(echo "$PWD" | sed 's|[/.]|-|g') co-locates them).
if [ -L "$VAULT_PATH" ]; then
    CANONICAL=$(readlink -f "$VAULT_PATH")
    echo "Detected: shared vault (symlink → $CANONICAL)"
    DEFAULT_WING=$(echo "$CANONICAL" | sed 's|[/.]|-|g')
else
    echo "Detected: in-repo vault"
    DEFAULT_WING=$(echo "$PWD" | sed 's|[/.]|-|g')
fi
WING="${MINE_VAULT_WING:-$DEFAULT_WING}"
if [ -n "${MINE_VAULT_WING:-}" ]; then
    echo "Wing: $WING (from MINE_VAULT_WING)"
else
    echo "Wing: $WING"
fi

# === STEP 4: Create temp dir with .md files only ===
MINE_TMPDIR=$(mktemp -d)/vault-md-only
cleanup() { [ -n "${MINE_TMPDIR:-}" ] && [ -d "$(dirname "$MINE_TMPDIR")" ] && rm -rf "$(dirname "$MINE_TMPDIR")"; }
trap cleanup EXIT
echo "Filtering .md files (excluding .obsidian/, node_modules/, _Templates/)..."

find -L "$VAULT_PATH" -name "*.md" \
    -not -path "*/.obsidian/*" \
    -not -path "*/node_modules/*" \
    -not -path "*/_Templates/*" \
    | while IFS= read -r f; do
        REL="${f#$VAULT_PATH/}"
        DIR="$MINE_TMPDIR/$(dirname "$REL")"
        mkdir -p "$DIR"
        # cp (not ln -s): mempalace mine ignores symlinks, leading to "Files: 0"
        # despite a populated staging dir. Verified via dry-run on 2026-04-30.
        cp "$f" "$DIR/$(basename "$f")"
    done

FILE_COUNT=$(find -L "$MINE_TMPDIR" -name "*.md" | wc -l | tr -d ' ')
echo "Found $FILE_COUNT .md files"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "ERROR: No .md files found in $VAULT_PATH"
    exit 1
fi

# === STEP 5: Init mempalace (non-interactive) ===
echo "Initializing mempalace for temp directory..."
INIT_OUT=$(printf '\n\n\n\n\n' | mempalace init "$MINE_TMPDIR" 2>&1) || {
    echo "ERROR: mempalace init failed:"
    echo "$INIT_OUT"
    exit 1
}
echo "$INIT_OUT" | tail -5

# === STEP 6: Mine ===
echo "Mining $FILE_COUNT files into wing '$WING'..."
mempalace mine "$MINE_TMPDIR" --mode projects --wing="$WING"

# === STEP 7: Cleanup (handled by EXIT trap) ===

echo ""
echo "Done. Verify with: mempalace status"
