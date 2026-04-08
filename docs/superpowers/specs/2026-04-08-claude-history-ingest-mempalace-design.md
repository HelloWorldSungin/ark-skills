# Claude History Ingest + MemPalace Integration

**Date:** 2026-04-08
**Status:** Approved
**Skill:** `/claude-history-ingest`

## Problem

The current `/claude-history-ingest` skill reads raw JSONL transcripts from `~/.claude/projects/` directly into Claude's context window for clustering and distillation. A single session transcript can be 50-200K tokens. Multi-session ingestion routinely costs 100-200K tokens per invocation. This is unsustainable for regular use.

## Solution

Integrate [MemPalace](https://github.com/milla-jovovich/mempalace) (MIT, Python, ChromaDB) as the indexing and retrieval backend. The skill becomes a two-layer pipeline:

- **Layer 1 (auto-index):** A Stop hook runs `mempalace mine` after each session. Zero LLM tokens. Conversations are chunked and embedded into ChromaDB.
- **Layer 2 (auto-compile):** When enough new material accumulates, Claude synthesizes compiled insight pages by querying MemPalace search results (~5-10K tokens) instead of reading raw transcripts (~100-200K tokens).

Compiled insight pages in the Ark vault are preserved as durable knowledge artifacts.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Auto-Index (Stop hook, zero LLM tokens)       │
│                                                         │
│  Session ends → hook fires → mempalace mine             │
│  JSONL chunks → ChromaDB (wing=project, rooms=auto)     │
│  ~/.mempalace/palace/                                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ threshold met? (N new drawers)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Auto-Compile (triggered by Stop hook)         │
│                                                         │
│  mempalace_search per topic cluster → ~5K tokens        │
│  Claude synthesizes → Compiled Insight pages             │
│  Vault write + index regeneration + git commit          │
└─────────────────────────────────────────────────────────┘
```

## Layer 1: Auto-Index

### Trigger

A Stop hook fires at session end. It does NOT use mempalace's built-in `mempal_save_hook.sh` (which blocks the AI mid-conversation to force saves — too intrusive).

### Process

1. Derive the project's Claude directory: `PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')`
2. Check `~/.mempalace/hook_state/{project}_last_indexed` for what's already been mined
3. Run `mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos` with wing set to the project name
4. Update state file with new timestamp and drawer count

### Wing/Room Mapping

- **Wing** = full path-derived Claude directory name (e.g., `-Users-sunginkim--superset-projects-ark-skills`) as the ChromaDB key. The human-readable project name from CLAUDE.md (e.g., `ark-skills`) is used only in vault page output.
- **Rooms** = auto-detected by mempalace's `room_detector_local.py` (topics like `auth`, `deployment`, `refactoring`)
- **Halls** = mempalace defaults (`hall_facts`, `hall_events`, `hall_discoveries`, `hall_preferences`, `hall_advice`)

### Scope

- **Default:** only mines `~/.claude/projects/$PROJECT_DIR/` (current project)
- **`--scope all`:** iterates all directories under `~/.claude/projects/`, each becoming its own wing

### Performance

The hook runs `mempalace mine` in background (`&`) and returns `{}` immediately to avoid exceeding the 60s hook timeout. Because mining is async, the threshold check on any given session end uses the *previous* session's mining results. This means compile is always one session behind index — acceptable since it's not time-critical.

### State Files

```
~/.mempalace/hook_state/
├── ark-skills_last_indexed          # timestamp of last mine
├── ark-skills_drawer_count          # drawer count after last index
├── trading-signal-ai_last_indexed
└── compile_threshold.json           # per-project: {drawers_at_last_compile: N}
```

## Layer 2: Auto-Compile

### Trigger

After Layer 1's background mining completes (checked on the *next* session end), the hook checks:

```
new_drawers = current_drawer_count - drawers_at_last_compile
if new_drawers >= COMPILE_THRESHOLD:
    trigger compile
```

**Default threshold:** 50 new drawers (~3-5 active sessions). Configurable per project in `compile_threshold.json`.

When threshold is met, the hook returns `{"decision": "block", "reason": "...compile instructions..."}` which instructs Claude to run the compile pass before the session ends.

### Compile Process

1. **Read memory files directly** — `~/.claude/projects/{project}/memory/*.md`. Small, high-signal, read raw. No change from current skill.

2. **Query mempalace for topic clusters** — ~5-10 targeted semantic searches:
   - `mempalace_search("architecture decisions", wing="project-name", n_results=10)`
   - `mempalace_search("debugging lessons", wing="project-name", n_results=10)`
   - `mempalace_search("failed approaches", wing="project-name", n_results=10)`
   - `mempalace_search("performance discoveries", wing="project-name", n_results=10)`
   - `mempalace_search("workflow patterns", wing="project-name", n_results=10)`

3. **Diff against existing insights** — read existing compiled insight pages. Only generate new pages for clusters with genuinely new information.

4. **Write compiled insight pages** — same Ark frontmatter schema, same template, same vault location (`{vault_path}/{project_area}/Research/Compiled-Insights/`). `source-sessions:` populated from mempalace drawer metadata.

5. **Update index and commit** — `generate-index.py`, git add, commit, push.

### Token Budget

| Step | Tokens |
|------|--------|
| Memory files | ~1-2K |
| 5-10 search results | ~3-5K |
| Existing insight diffing | ~2-3K |
| Output generation | ~2-3K |
| **Total** | **~8-13K** |

vs. current: **~100-200K** (90-95% reduction)

## Skill Modes

The rewritten SKILL.md supports three modes:

| Mode | What it does | Token cost |
|------|-------------|------------|
| `index` | Force `mempalace mine` on current project (or all with `--scope all`) | 0 |
| `compile` | Force compile regardless of threshold | ~10K |
| `full` (default) | Index then compile | ~10K |

## Setup & Prerequisites

### One-Time Setup

1. **Install mempalace:**
   ```bash
   pip install mempalace
   ```

2. **Initialize the palace:**
   ```bash
   mempalace init ~/.claude/projects/$(echo "$PWD" | sed 's|/|-|g')
   ```

3. **Register the Stop hook** in `.claude/settings.local.json`:
   ```json
   {
     "hooks": {
       "Stop": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "bash ~/.claude/hooks/ark-history-hook.sh",
           "timeout": 60
         }]
       }]
     }
   }
   ```

4. **Optional — MCP server** for richer compile queries:
   ```bash
   claude mcp add mempalace -- python -m mempalace.mcp_server
   ```
   Compile falls back to `mempalace search` CLI if MCP is not connected.

### Detection

When the skill is invoked, it checks:
- `mempalace --version` — installed?
- `~/.mempalace/palace/` — initialized?
- `.claude/settings.local.json` — hook registered?

Missing prerequisites produce actionable error messages.

## New File: `~/.claude/hooks/ark-history-hook.sh`

A custom Stop hook script created during setup. Responsibilities:
- Read `session_id` and `transcript_path` from stdin JSON
- Run `mempalace mine` in background on the project's Claude directory
- Check drawer count against compile threshold
- Return `{"decision": "block", "reason": "..."}` if compile is needed, or `{}` otherwise
- Track state in `~/.mempalace/hook_state/`

## Edge Cases

### ChromaDB ARM64 segfault (mempalace #74)
Hook runs indexing in a subprocess. Crash = session ends normally, indexing retried next time. Vault artifacts never at risk.

### Duplicate indexing
`convo_miner.py` uses content hashing via `hashlib`. Already-indexed chunks are skipped. `mempalace_check_duplicate` MCP tool available for verification.

### Stale insights
Compile step diffs search results against existing insight pages. Overlapping or outdated content is skipped.

### Wing collision (global mode)
Uses full Claude project directory name (path-derived) as the wing identifier. Compile maps back to human-readable project name from CLAUDE.md.

### Hook timeout
`mempalace mine` runs in background. Returns `{}` immediately. Threshold check deferred to next session end.

### MCP server unavailable
Compile falls back to `mempalace search` CLI via bash. Functionally identical, slightly less structured output.

## What Changes vs. Current Skill

| Current | New |
|---------|-----|
| Reads raw JSONL in context (100-200K tokens) | mempalace indexes for free, search returns ~5K tokens |
| Manual invocation only | Auto-index on session end, auto-compile on threshold |
| Topic clustering in Claude's context | Semantic search queries replace clustering |
| Project-scoped only | Project-scoped by default, `--scope all` for global |
| No external dependencies | Requires `pip install mempalace` (ChromaDB) |

## What Stays the Same

- Compiled insight pages in `{vault_path}/{project_area}/Research/Compiled-Insights/`
- Ark frontmatter schema (`type: compiled-insight`, `source-sessions:`, `summary:`, etc.)
- Memory file reading (Step 2 — small, high-signal, read directly)
- Index regeneration via `generate-index.py`
- Git commit at end
- Project Discovery via CLAUDE.md
