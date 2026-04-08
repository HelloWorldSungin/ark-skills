---
name: claude-history-ingest
description: Mine Claude Code conversation history and memory files into compiled vault insights
---

# Claude History Ingest

Extract knowledge from the **current project's** Claude Code conversation history using MemPalace for indexing and retrieval, then distill into compiled insight pages in the project's vault.

## Prerequisites Check

Before doing anything else, verify the setup:

```bash
# 1. Is mempalace installed?
command -v mempalace

# 2. Is the palace initialized?
ls ~/.mempalace/palace/chroma.sqlite3 2>/dev/null

# 3. Is the hook installed?
ls ~/.claude/hooks/ark-history-hook.sh 2>/dev/null
```

If anything is missing, run the installer:

```bash
bash skills/claude-history-ingest/hooks/install-hook.sh
```

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/_meta/taxonomy.md` for valid tags (compiled insights must use tags from this list)
4. Read `{vault_path}/_Templates/Compiled-Insight-Template.md` for output format
5. Derive the wing key: `WING=$(echo "$PWD" | sed 's|[/.]|-|g')`

## Modes

This skill supports three modes. Default is `full`.

### Mode: `index`

Zero LLM tokens. Indexes conversations into MemPalace's ChromaDB.

```bash
PROJECT_DIR=$(echo "$PWD" | sed 's|[/.]|-|g')
WING="$PROJECT_DIR"
mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos --wing="$WING"
```

For global scope (all projects):

```bash
for DIR in ~/.claude/projects/*/; do
    WING=$(basename "$DIR")
    mempalace mine "$DIR" --mode convos --wing="$WING"
done
```

After indexing, verify with:

```bash
mempalace status
```

### Mode: `compile`

~10K LLM tokens. Queries MemPalace search results and writes compiled insight pages.

#### Step 1: Read Memory Files

Read the project's memory files directly (small, high-signal):

```bash
PROJECT_DIR=$(echo "$PWD" | sed 's|[/.]|-|g')
CLAUDE_PROJECT="$HOME/.claude/projects/$PROJECT_DIR"
ls "$CLAUDE_PROJECT/memory/" 2>/dev/null
```

Read each `.md` file in `{CLAUDE_PROJECT}/memory/`. Parse YAML frontmatter. Prioritize by type:
- `type: user` — knowledge about the developer
- `type: feedback` — workflow preferences and corrections
- `type: project` — project decisions and context
- `type: reference` — external resource pointers

#### Step 2: Dynamic Topic Discovery

Query MemPalace for the rooms it detected in this project's wing.

Parse room names from status output:

```bash
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
mempalace status 2>/dev/null | awk -v wing="$WING" '
    /WING:/ { found=($2 == wing) }
    found && /ROOM:/ { print $2 }
'
```

Combine discovered room names with baseline queries:
- `"architecture decisions"`
- `"debugging lessons"`
- `"failed approaches"`
- `"workflow patterns"`
- `"performance discoveries"`

#### Step 3: Query MemPalace for Each Topic

For each topic from Step 2, run a semantic search:

```bash
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
mempalace search "architecture decisions" --wing="$WING" --results 10
mempalace search "debugging lessons" --wing="$WING" --results 10
# ... one per topic
```

Collect all returned chunks. Deduplicate by content (same chunk may appear in multiple searches).

#### Step 4: Diff Against Existing Insights

Read existing compiled insight pages in `vault/Compiled-Insights/`:

```bash
ls vault/Compiled-Insights/*.md 2>/dev/null
```

For each page, read the title and Summary section. For each search result from Step 3, check:
1. Does the content overlap significantly with an existing insight page's Summary? If yes, skip.

Only generate new pages for clusters that surface genuinely new, uncompiled information.

#### Step 5: Write Compiled Insight Pages

For each new cluster, create a page in `vault/Compiled-Insights/`:

Use the template from `vault/_Templates/Compiled-Insight-Template.md`:

```yaml
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
```

Write:
- **Summary** — one-paragraph synthesis
- **Key Insights** — specific findings with sub-headings
- **Evidence** — verbatim quotes from MemPalace search results
- **Implications** — what to do differently based on this knowledge

#### Step 6: Update Index and Commit

Regenerate the vault index from the repo root:

```bash
python3 {vault_path}/_meta/generate-index.py
```

Stage only the new/modified files from the repo root (not `git add -A`):

```bash
git add {vault_path}/Compiled-Insights/{new-files}.md {vault_path}/index.md
git commit -m "docs: ingest Claude history — {N} compiled insights created"
```

#### Step 7: Update Compile Threshold State

After a successful compile, update the threshold state so the auto-compile hook knows the new baseline:

```bash
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
STATE_DIR="$HOME/.mempalace/hook_state"
# Parse drawer count from text status output
CURRENT=$(mempalace status 2>/dev/null | awk -v wing="$WING" '
    BEGIN { total=0 }
    /WING:/ { found=($2 == wing) }
    found && /ROOM:/ { for(i=1;i<=NF;i++) if($i=="drawers") total+=$(i-1) }
    END { print total }
')
CURRENT=${CURRENT:-0}
python3 -c "
import json, os
path = '$STATE_DIR/compile_threshold.json'
data = {}
if os.path.exists(path):
    with open(path) as f:
        data = json.load(f)
data['$WING'] = {'drawers_at_last_compile': $CURRENT}
tmp = path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(data, f, indent=2)
os.replace(tmp, path)
print(f'Updated compile threshold: $WING = $CURRENT drawers')
"
```

### Mode: `full` (default)

First run all `index` steps above, then run all `compile` steps above. Always compiles regardless of threshold (manual invocation — threshold gating only applies to auto-compile via the Stop hook).

## Auto-Indexing

The Stop hook at `~/.claude/hooks/ark-history-hook.sh` handles auto-indexing. It:
- Mines the project directory into ChromaDB after the session ends (zero LLM tokens)
- Checks if enough new drawers have accumulated since the last compile
- If threshold met (default: 50 drawers), blocks session exit and asks Claude to run compile

The hook source lives in this skill at `skills/claude-history-ingest/hooks/ark-history-hook.sh`.
To reinstall after updates: `bash skills/claude-history-ingest/hooks/install-hook.sh`
