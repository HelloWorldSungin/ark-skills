# Claude History Ingest + MemPalace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the token-heavy JSONL-reading workflow in `/claude-history-ingest` with a MemPalace-backed two-layer pipeline: auto-index via Stop hook (zero LLM tokens) and auto-compile via threshold-triggered semantic search (~10K tokens vs 100-200K).

**Architecture:** A bash Stop hook runs `mempalace mine` in the background after each session, indexing conversation chunks into ChromaDB. When enough new material accumulates, the hook blocks session exit and instructs Claude to compile insights by querying MemPalace search results instead of reading raw transcripts. Compiled insight pages in the Ark vault are preserved unchanged.

**Tech Stack:** mempalace (Python/ChromaDB), bash (Stop hook), Claude Code skills (SKILL.md)

**Spec:** `docs/superpowers/specs/2026-04-08-claude-history-ingest-mempalace-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `skills/claude-history-ingest/SKILL.md` | Rewrite | Skill instructions: setup detection, three modes (index/compile/full), compile workflow via mempalace search |
| `skills/claude-history-ingest/hooks/ark-history-hook.sh` | Create | Stop hook: incremental indexing, threshold check, compile block decision |
| `skills/claude-history-ingest/hooks/install-hook.sh` | Create | One-time setup: install mempalace, init palace, register hook in settings |

---

### Task 1: Install mempalace and verify CLI

**Files:**
- None (environment setup)

- [ ] **Step 1: Install mempalace via pip (pinned range)**

```bash
pip install "mempalace>=3.0.0,<4.0.0"
```

Expected: installs successfully, prints version info.

- [ ] **Step 2: Verify installation**

```bash
mempalace --version
```

Expected: prints version (e.g., `mempalace 3.0.x`).

- [ ] **Step 3: Initialize a test palace**

```bash
mempalace init ~/.claude/projects/$(echo "$PWD" | sed 's|/|-|g') --yes
```

Expected: creates `~/.mempalace/palace/` directory, detects rooms from the project structure.

- [ ] **Step 4: Verify palace exists**

```bash
ls ~/.mempalace/palace/
```

Expected: ChromaDB files present (e.g., `chroma.sqlite3`).

- [ ] **Step 5: Test mining a single JSONL file**

Find a transcript file and test incremental mining:

```bash
PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')
WING="$PROJECT_DIR"
TRANSCRIPT=$(ls -t ~/.claude/projects/$PROJECT_DIR/*.jsonl 2>/dev/null | head -1)
if [ -n "$TRANSCRIPT" ]; then
    mempalace mine "$TRANSCRIPT" --mode convos --wing "$WING"
else
    echo "No JSONL files found — mine the full directory instead"
    mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos --wing "$WING"
fi
```

Expected: prints mining progress, files indexed into ChromaDB.

- [ ] **Step 6: Verify search works**

```bash
mempalace search "skill" --wing "$(echo "$PWD" | sed 's|/|-|g')"
```

Expected: returns verbatim conversation chunks with wing/room metadata.

- [ ] **Step 7: Commit nothing** (no code changes, just environment verification)

---

### Task 2: Write the Stop hook script

**Files:**
- Create: `skills/claude-history-ingest/hooks/ark-history-hook.sh`

- [ ] **Step 1: Create the hooks directory**

```bash
mkdir -p skills/claude-history-ingest/hooks
```

- [ ] **Step 2: Write the hook script**

Create `skills/claude-history-ingest/hooks/ark-history-hook.sh`:

```bash
#!/bin/bash
# ark-history-hook.sh — Auto-index Claude sessions into MemPalace
#
# Stop hook for Claude Code. After each session:
# 1. Mines the session transcript into ChromaDB (background, zero LLM tokens)
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
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null)
TRANSCRIPT_PATH="${TRANSCRIPT_PATH/#\~/$HOME}"

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
WING=$(echo "$PWD" | sed 's|/|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$WING"

# === CIRCUIT BREAKER ===
FAIL_FILE="$STATE_DIR/${WING}_fail_count"
FAIL_COUNT=0
if [ -f "$FAIL_FILE" ]; then
    FAIL_COUNT=$(cat "$FAIL_FILE" 2>/dev/null || echo 0)
fi
if [ "$FAIL_COUNT" -ge "$FAIL_COUNT_MAX" ]; then
    echo "[ark-history-hook] Auto-indexing disabled after $FAIL_COUNT_MAX consecutive failures. Delete $FAIL_FILE to re-enable." >> "$STATE_DIR/mine.log"
    echo "{}"
    exit 0
fi

# === LAYER 1: INDEX (background, zero LLM tokens) ===
LOCK="$STATE_DIR/${WING}.lock"
if mkdir "$LOCK" 2>/dev/null; then
    # Determine what to mine: transcript file (incremental) or full directory (fallback)
    if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
        MINE_TARGET="$TRANSCRIPT_PATH"
    elif [ -d "$CLAUDE_PROJECT" ]; then
        MINE_TARGET="$CLAUDE_PROJECT"
    else
        rmdir "$LOCK" 2>/dev/null
        echo "{}"
        exit 0
    fi

    nohup bash -c "
        if mempalace mine \"$MINE_TARGET\" --mode convos --wing \"$WING\" 2>>\"$STATE_DIR/mine.log\"; then
            echo 0 > \"$FAIL_FILE\"
            date +%s > \"$STATE_DIR/${WING}_last_indexed\"
            # Count drawers for THIS wing only (not global total)
            mempalace status --json 2>/dev/null | python3 -c \"import sys,json; print(json.load(sys.stdin).get('wings',{}).get('$WING',0))\" > \"$STATE_DIR/${WING}_drawer_count\" 2>/dev/null
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
if [ ! -f "$DONE_MARKER" ]; then
    # No completed mining yet — skip threshold check
    echo "{}"
    exit 0
fi

DRAWER_COUNT_FILE="$STATE_DIR/${WING}_drawer_count"
THRESHOLD_FILE="$STATE_DIR/compile_threshold.json"

CURRENT_DRAWERS=0
if [ -f "$DRAWER_COUNT_FILE" ]; then
    CURRENT_DRAWERS=$(cat "$DRAWER_COUNT_FILE" 2>/dev/null || echo 0)
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
    # Remove done marker so we don't re-trigger until next mining completes
    rm -f "$DONE_MARKER"

    cat << HOOKJSON
{
  "decision": "block",
  "reason": "AUTO-COMPILE checkpoint. Run /claude-history-ingest compile to synthesize new insights from the ${NEW_DRAWERS} new conversation chunks indexed since last compile. Use mempalace_search or 'mempalace search' CLI to query topics, diff against existing vault insights, and write only genuinely new compiled insight pages. Stage only the new files (not git add -A). The wing key for this project is: ${WING}. IMPORTANT: After compile, you MUST run Step 7 (Update Compile Threshold State) to prevent re-triggering."
}
HOOKJSON
else
    echo "{}"
fi
```

- [ ] **Step 3: Make it executable**

```bash
chmod +x skills/claude-history-ingest/hooks/ark-history-hook.sh
```

- [ ] **Step 4: Verify the script parses correctly**

```bash
echo '{"session_id":"test-123","transcript_path":"","stop_hook_active":false}' | bash skills/claude-history-ingest/hooks/ark-history-hook.sh
```

Expected: prints `{}` (no transcript, no prior mining results, so nothing to compile).

- [ ] **Step 5: Test the infinite-loop guard**

```bash
echo '{"session_id":"test-123","transcript_path":"","stop_hook_active":true}' | bash skills/claude-history-ingest/hooks/ark-history-hook.sh
```

Expected: prints `{}` immediately (loop prevention).

- [ ] **Step 6: Commit**

```bash
git add skills/claude-history-ingest/hooks/ark-history-hook.sh
git commit -m "feat: add Stop hook for auto-indexing sessions into MemPalace"
```

---

### Task 3: Write the setup/install helper script

**Files:**
- Create: `skills/claude-history-ingest/hooks/install-hook.sh`

- [ ] **Step 1: Write the install script**

Create `skills/claude-history-ingest/hooks/install-hook.sh`:

```bash
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
    pip install "mempalace>=3.0.0,<4.0.0"
else
    echo -e "${GREEN}[OK]${NC} mempalace found: $(mempalace --version 2>/dev/null || echo 'installed')"
fi

# --- Step 3: Initialize palace ---
PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$PROJECT_DIR"

if [ ! -d "$HOME/.mempalace/palace" ] || [ ! -f "$HOME/.mempalace/palace/chroma.sqlite3" ]; then
    if [ -d "$CLAUDE_PROJECT" ]; then
        echo -e "${YELLOW}Initializing palace for: $CLAUDE_PROJECT${NC}"
        mempalace init "$CLAUDE_PROJECT" --yes
    else
        echo -e "${YELLOW}Initializing palace with current directory...${NC}"
        mempalace init "$PWD" --yes
    fi
else
    echo -e "${GREEN}[OK]${NC} Palace already initialized at ~/.mempalace/palace/"
fi

# --- Step 4: Copy hook to ~/.claude/hooks/ ---
HOOK_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ark-history-hook.sh"
HOOK_DST="$HOME/.claude/hooks/ark-history-hook.sh"

mkdir -p "$HOME/.claude/hooks"

if [ -f "$HOOK_DST" ]; then
    echo -e "${GREEN}[OK]${NC} Hook already installed at $HOOK_DST"
else
    cp "$HOOK_SRC" "$HOOK_DST"
    chmod +x "$HOOK_DST"
    echo -e "${GREEN}[OK]${NC} Hook installed to $HOOK_DST"
fi

# --- Step 5: Register hook in settings ---
# Try global settings first, fall back to local
SETTINGS="$HOME/.claude/settings.json"
if [ ! -f "$SETTINGS" ]; then
    SETTINGS="$HOME/.claude/settings.local.json"
fi

if [ -f "$SETTINGS" ] && grep -q "ark-history-hook" "$SETTINGS" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Hook already registered in $SETTINGS"
else
    echo -e "${YELLOW}Registering hook in $SETTINGS...${NC}"
    python3 -c "
import json, os
path = '$SETTINGS'
data = {}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
hooks = data.setdefault('hooks', {})
stop_hooks = hooks.setdefault('Stop', [])
entry = {
    'hooks': [{
        'type': 'command',
        'command': 'bash $HOOK_DST',
        'timeout': 60
    }]
}
stop_hooks.append(entry)
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print('Hook registered.')
"
    echo -e "${GREEN}[OK]${NC} Hook registered in $SETTINGS"
fi

# --- Step 6: Create state directory ---
mkdir -p "$HOME/.mempalace/hook_state"
echo -e "${GREEN}[OK]${NC} State directory ready at ~/.mempalace/hook_state/"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo "  - Run '/claude-history-ingest index' to do an initial index"
echo "  - The Stop hook will auto-index future sessions"
echo "  - After ~50 new conversation chunks, auto-compile will trigger"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x skills/claude-history-ingest/hooks/install-hook.sh
```

- [ ] **Step 3: Dry-run the script to verify it parses**

```bash
bash -n skills/claude-history-ingest/hooks/install-hook.sh
```

Expected: no output (no syntax errors).

- [ ] **Step 4: Commit**

```bash
git add skills/claude-history-ingest/hooks/install-hook.sh
git commit -m "feat: add install script for MemPalace hook setup"
```

---

### Task 4: Rewrite the SKILL.md

**Files:**
- Rewrite: `skills/claude-history-ingest/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md**

```bash
cat skills/claude-history-ingest/SKILL.md
```

Confirm you have the full current content before replacing it.

- [ ] **Step 2: Write the new SKILL.md**

Replace the entire contents of `skills/claude-history-ingest/SKILL.md` with:

```markdown
---
name: claude-history-ingest
description: Mine Claude Code conversation history and memory files into compiled vault insights
---

# Claude History Ingest

Extract knowledge from the **current project's** Claude Code conversation history using MemPalace for indexing and retrieval, then distill into compiled insight pages in the project's vault.

## Prerequisites Check

Before doing anything else, verify the setup:

\`\`\`bash
# 1. Is mempalace installed?
mempalace --version

# 2. Is the palace initialized?
ls ~/.mempalace/palace/ 2>/dev/null

# 3. Is the hook installed?
ls ~/.claude/hooks/ark-history-hook.sh 2>/dev/null
\`\`\`

If anything is missing, run the installer:

\`\`\`bash
bash skills/claude-history-ingest/hooks/install-hook.sh
\`\`\`

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/_meta/taxonomy.md` for valid tags (compiled insights must use tags from this list)
4. Read `{vault_path}/_Templates/Compiled-Insight-Template.md` for output format
5. Derive the wing key: `WING=$(echo "$PWD" | sed 's|/|-|g')`

## Modes

This skill supports three modes. Default is `full`.

### Mode: `index`

Zero LLM tokens. Indexes conversations into MemPalace's ChromaDB.

\`\`\`bash
PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')
WING="$PROJECT_DIR"
mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos --wing "$WING"
\`\`\`

For global scope (all projects):

\`\`\`bash
for DIR in ~/.claude/projects/*/; do
    WING=$(basename "$DIR")
    mempalace mine "$DIR" --mode convos --wing "$WING"
done
\`\`\`

After indexing, verify with:

\`\`\`bash
mempalace status
\`\`\`

### Mode: `compile`

~10K LLM tokens. Queries MemPalace search results and writes compiled insight pages.

#### Step 1: Read Memory Files

Read the project's memory files directly (small, high-signal):

\`\`\`bash
PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$PROJECT_DIR"
ls "$CLAUDE_PROJECT/memory/" 2>/dev/null
\`\`\`

Read each `.md` file in `{CLAUDE_PROJECT}/memory/`. Parse YAML frontmatter. Prioritize by type:
- `type: user` — knowledge about the developer
- `type: feedback` — workflow preferences and corrections
- `type: project` — project decisions and context
- `type: reference` — external resource pointers

#### Step 2: Dynamic Topic Discovery

Query MemPalace for the rooms it detected in this project's wing.

Via MCP (preferred): `mempalace_list_rooms(wing=WING)`

Via CLI fallback — parse room names from status output:

\`\`\`bash
WING=$(echo "$PWD" | sed 's|/|-|g')
mempalace status --json 2>/dev/null | python3 -c "import sys,json; [print(r) for r in json.load(sys.stdin).get('rooms',{}).keys()]"
\`\`\`

Combine discovered room names with baseline queries:
- `"architecture decisions"`
- `"debugging lessons"`
- `"failed approaches"`
- `"workflow patterns"`
- `"performance discoveries"`

#### Step 3: Query MemPalace for Each Topic

For each topic from Step 2, run a semantic search:

\`\`\`bash
WING=$(echo "$PWD" | sed 's|/|-|g')
mempalace search "architecture decisions" --wing "$WING"
mempalace search "debugging lessons" --wing "$WING"
# ... one per topic
\`\`\`

Or via MCP: `mempalace_search(query, wing=WING, n_results=10)` for each topic.

Collect all returned chunks. Deduplicate by content (same chunk may appear in multiple searches).

#### Step 4: Diff Against Existing Insights

Read the drawer tracking file to know which drawers have already been compiled:

\`\`\`bash
STATE_DIR="$HOME/.mempalace/hook_state"
WING=$(echo "$PWD" | sed 's|/|-|g')
cat "$STATE_DIR/${WING}_compiled_drawers.json" 2>/dev/null || echo '{"compiled_ids":[]}'
\`\`\`

Read existing compiled insight pages in `vault/Compiled-Insights/`:

\`\`\`bash
ls vault/Compiled-Insights/*.md 2>/dev/null
\`\`\`

For each page, read the title and Summary section. For each search result from Step 3, check:
1. Is the drawer ID (from mempalace metadata) already in `compiled_drawers.json`? If yes, skip.
2. Does the content overlap significantly with an existing insight page's Summary? If yes, skip.

Only generate new pages for clusters that surface genuinely new, uncompiled information.

After writing new insight pages, update the tracking file:

\`\`\`bash
# Append newly compiled drawer IDs to the tracking file
python3 -c "
import json, os
path = '$STATE_DIR/${WING}_compiled_drawers.json'
data = {'compiled_ids': []}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
# NEW_IDS is the list of drawer IDs used in this compile pass
data['compiled_ids'].extend(NEW_IDS)
data['compiled_ids'] = list(set(data['compiled_ids']))  # dedupe
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
"
\`\`\`

(Replace `NEW_IDS` with the actual list of drawer IDs from the search results used in this compile.)

#### Step 5: Write Compiled Insight Pages

For each new cluster, create a page in `vault/Compiled-Insights/` (this is the actual path in this repo — NOT `Research/Compiled-Insights/` as the old skill said):

Use the template from `vault/_Templates/Compiled-Insight-Template.md`:

\`\`\`yaml
---
title: "{Insight Title}"
type: compiled-insight
tags:
  - compiled-insight
  - {domain-tag from vault/_meta/taxonomy.md — e.g., skill, plugin, vault, infrastructure}
summary: "{<=200 char finding summary}"
source-sessions: []
source-tasks: []
created: {today}
last-updated: {today}
---
\`\`\`

Write:
- **Summary** — one-paragraph synthesis
- **Key Insights** — specific findings with sub-headings
- **Evidence** — verbatim quotes from MemPalace search results
- **Implications** — what to do differently based on this knowledge

#### Step 6: Update Index and Commit

\`\`\`bash
cd {vault_path}
python3 _meta/generate-index.py
\`\`\`

Stage only the new/modified files (not `git add -A`):

\`\`\`bash
git add vault/Compiled-Insights/{new-files}.md vault/index.md
git commit -m "docs: ingest Claude history — {N} compiled insights created"
git push
\`\`\`

#### Step 7: Update Compile Threshold State

After a successful compile, update the threshold state so the auto-compile hook knows the new baseline:

\`\`\`bash
WING=$(echo "$PWD" | sed 's|/|-|g')
STATE_DIR="$HOME/.mempalace/hook_state"
# Get per-wing drawer count (not global total)
CURRENT=$(mempalace status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('wings',{}).get('$(echo "$PWD" | sed "s|/|-|g")',0))" 2>/dev/null || cat "$STATE_DIR/${WING}_drawer_count" 2>/dev/null || echo 0)
python3 -c "
import json, os, fcntl
path = '$STATE_DIR/compile_threshold.json'
data = {}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
data['$WING'] = {'drawers_at_last_compile': $CURRENT}
# Atomic write via temp file
tmp = path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
print(f'Updated compile threshold: $WING = $CURRENT drawers')
"
\`\`\`

### Mode: `full` (default)

Runs `index` synchronously, then `compile`. Always compiles regardless of threshold (manual invocation, threshold gating only applies to auto-compile via the Stop hook).

## Auto-Indexing

The Stop hook at `~/.claude/hooks/ark-history-hook.sh` handles auto-indexing. It:
- Mines each session's transcript into ChromaDB after the session ends (zero LLM tokens)
- Checks if enough new drawers have accumulated since the last compile
- If threshold met (default: 50 drawers), blocks session exit and asks Claude to run compile

The hook source lives in this skill at `skills/claude-history-ingest/hooks/ark-history-hook.sh`.
To reinstall after updates: `bash skills/claude-history-ingest/hooks/install-hook.sh`
```

- [ ] **Step 3: Verify the SKILL.md has valid YAML frontmatter**

```bash
head -4 skills/claude-history-ingest/SKILL.md
```

Expected:
```
---
name: claude-history-ingest
description: Mine Claude Code conversation history and memory files into compiled vault insights
---
```

- [ ] **Step 4: Commit**

```bash
git add skills/claude-history-ingest/SKILL.md
git commit -m "feat: rewrite claude-history-ingest to use MemPalace backend

Two-layer pipeline: auto-index via Stop hook (zero LLM tokens)
and compile via semantic search (~10K tokens vs 100-200K).
Three modes: index, compile, full (default)."
```

---

### Task 5: End-to-end manual test

**Files:**
- None (validation only)

- [ ] **Step 1: Run the install script**

```bash
bash skills/claude-history-ingest/hooks/install-hook.sh
```

Expected: all checks pass, hook installed.

- [ ] **Step 2: Run index mode**

Invoke the skill in index mode:

```bash
PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')
WING="$PROJECT_DIR"
mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos --wing "$WING"
```

Expected: conversations indexed, `mempalace status` shows drawers.

- [ ] **Step 3: Verify search returns results**

```bash
WING=$(echo "$PWD" | sed 's|/|-|g')
mempalace search "skill" --wing "$WING"
mempalace search "vault" --wing "$WING"
```

Expected: verbatim conversation chunks with relevance scores.

- [ ] **Step 4: Run compile mode via the skill**

Invoke `/claude-history-ingest compile` (or run the skill manually). Verify:
- Memory files are read from `~/.claude/projects/{project}/memory/`
- MemPalace searches return results for each topic
- Existing insight pages are compared against new results
- New compiled insight pages are written to `vault/Compiled-Insights/`
- Only new files are staged (not `git add -A`)
- Commit message follows the pattern `docs: ingest Claude history — N compiled insights created`

- [ ] **Step 5: Verify the hook end-to-end**

Test the hook manually with simulated input:

```bash
echo '{"session_id":"test-e2e","transcript_path":"","stop_hook_active":false}' | bash ~/.claude/hooks/ark-history-hook.sh
```

Expected: `{}` (no threshold met on first run).

- [ ] **Step 6: Verify the threshold state was updated**

```bash
cat ~/.mempalace/hook_state/compile_threshold.json
```

Expected: JSON with the wing key and `drawers_at_last_compile` count matching the compile that just ran.

- [ ] **Step 7: Commit if any test artifacts need cleanup**

If the test created any vault pages, verify they look correct and commit:

```bash
git add vault/Compiled-Insights/ vault/index.md
git commit -m "docs: ingest Claude history — N compiled insights created"
```

---

### Task 6: Update plugin metadata and documentation

**Files:**
- Modify: `CLAUDE.md` (add mempalace dependency note)
- Modify: `CHANGELOG.md` (add versioned entry matching existing format)
- Modify: `.claude-plugin/plugin.json` (bump version)
- Modify: `VERSION` (bump version)

- [ ] **Step 1: Update CLAUDE.md skill description**

In `CLAUDE.md` line 88, replace the existing skill entry:

Old:
```markdown
- `/claude-history-ingest` — Mine Claude conversations into compiled insights
```

New:
```markdown
- `/claude-history-ingest` — Mine Claude conversations into compiled vault insights via MemPalace (requires `pip install mempalace`)
```

- [ ] **Step 2: Bump version**

Read `VERSION` and `.claude-plugin/plugin.json` for the current version. Bump the minor version (e.g., `1.0.2` -> `1.1.0`).

Update `VERSION`:
```
1.1.0
```

Update `.claude-plugin/plugin.json` line 3:
```json
"version": "1.1.0",
```

- [ ] **Step 3: Update CHANGELOG.md**

Add a versioned entry at the top (after the header), matching the existing format:

```markdown
## [1.1.0] - 2026-04-08

### Changed
- `claude-history-ingest` skill rewritten to use MemPalace (ChromaDB) for indexing and retrieval.
  Auto-indexes sessions via Stop hook (zero LLM tokens). Compiles insights via semantic search
  (~10K tokens vs 100-200K previously). Three modes: index, compile, full.
  Requires `pip install mempalace`.

### Added
- `skills/claude-history-ingest/hooks/ark-history-hook.sh` — Stop hook for auto-indexing
- `skills/claude-history-ingest/hooks/install-hook.sh` — One-time setup helper
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md CHANGELOG.md VERSION .claude-plugin/plugin.json
git commit -m "chore: bump to 1.1.0 — MemPalace integration for claude-history-ingest"
```
