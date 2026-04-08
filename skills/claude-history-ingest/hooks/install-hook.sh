#!/bin/bash
# install-hook.sh — One-time setup for claude-history-ingest + MemPalace
#
# Checks prerequisites, installs mempalace, initializes palace, registers hook.
# Safe to run multiple times (idempotent).

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== claude-history-ingest + MemPalace Setup ==="
echo ""

# --- Step 1: Check Python ---
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}ERROR: python3 not found. Install Python 3.10+ first.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} python3 found: $(python3 --version)"

# --- Step 2: Install mempalace ---
if ! command -v mempalace &>/dev/null; then
    echo -e "${YELLOW}Installing mempalace...${NC}"
    if command -v pipx &>/dev/null; then
        if ! pipx install "mempalace>=3.0.0,<4.0.0"; then
            echo -e "${RED}ERROR: pipx install failed. Try manually: pipx install mempalace${NC}"
            exit 1
        fi
        # Ensure pipx bin dir is on PATH for this session
        export PATH="$HOME/.local/bin:$PATH"
    elif pip3 install --user "mempalace>=3.0.0,<4.0.0" 2>/dev/null; then
        true
    else
        echo -e "${RED}ERROR: Could not install mempalace. Try: pipx install mempalace${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}[OK]${NC} mempalace found: $(command -v mempalace 2>/dev/null || echo 'installed (restart shell to update PATH)')"

# --- Step 3: Initialize palace ---
# Claude Code encodes project paths by replacing both / and . with -
PROJECT_DIR=$(echo "$PWD" | sed 's|[/.]|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$PROJECT_DIR"

if [ ! -f "$HOME/.mempalace/palace/chroma.sqlite3" ]; then
    TARGET="$CLAUDE_PROJECT"
    if [ ! -d "$TARGET" ]; then
        TARGET="$PWD"
    fi
    echo -e "${YELLOW}Initializing palace for: $TARGET${NC}"
    # init --yes only auto-accepts entities, not rooms — pipe empty line for room acceptance
    echo "" | mempalace init "$TARGET" --yes
else
    echo -e "${GREEN}[OK]${NC} Palace already initialized at ~/.mempalace/palace/"
fi

# --- Step 4: Copy hook to ~/.claude/hooks/ ---
HOOK_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ark-history-hook.sh"
HOOK_DST="$HOME/.claude/hooks/ark-history-hook.sh"

mkdir -p "$HOME/.claude/hooks"

if [ -f "$HOOK_DST" ] && cmp -s "$HOOK_SRC" "$HOOK_DST"; then
    echo -e "${GREEN}[OK]${NC} Hook up to date at $HOOK_DST"
else
    [ -f "$HOOK_DST" ] && ACTION="updated" || ACTION="installed"
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    echo -e "${GREEN}[OK]${NC} Hook $ACTION at $HOOK_DST"
fi

# --- Step 5: Register hook in project-local settings ---
# Use .claude/settings.json in the current project (per-project scope, not global)
# This ensures the hook only fires in projects that explicitly opt in
PROJ_SETTINGS="$PWD/.claude/settings.json"
mkdir -p "$PWD/.claude"

if [ -f "$PROJ_SETTINGS" ] && grep -q "ark-history-hook" "$PROJ_SETTINGS" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Hook already registered in $PROJ_SETTINGS (project-local)"
else
    echo -e "${YELLOW}Registering hook in $PROJ_SETTINGS (project-local)...${NC}"
    SETTINGS_PATH="$PROJ_SETTINGS" HOOK_CMD="bash $HOOK_DST" python3 -c "
import json, os, sys
path = os.environ['SETTINGS_PATH']
hook_cmd = os.environ['HOOK_CMD']
data = {}
if os.path.exists(path):
    with open(path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f'ERROR: {path} is not valid JSON: {e}', file=sys.stderr)
            sys.exit(1)
hooks = data.setdefault('hooks', {})
stop_hooks = hooks.setdefault('Stop', [])
entry = {
    'hooks': [{
        'type': 'command',
        'command': hook_cmd,
        'timeout': 60
    }]
}
stop_hooks.append(entry)
tmp = path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
print('Hook registered.')
"
    echo -e "${GREEN}[OK]${NC} Hook registered in $PROJ_SETTINGS (project-local)"
fi

# --- Step 6: Create state directory ---
mkdir -p "$HOME/.mempalace/hook_state"
echo -e "${GREEN}[OK]${NC} State directory ready at ~/.mempalace/hook_state/"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo "  - Run '/claude-history-ingest index' to do an initial index"
echo "  - The Stop hook will auto-index future sessions"
echo "  - After ~50 new conversation chunks, auto-compile will trigger"
