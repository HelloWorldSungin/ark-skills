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

1. Read `session_id` and `transcript_path` from the hook's stdin JSON
2. Derive the project's Claude directory: `PROJECT_DIR=$(echo "$PWD" | sed 's|/|-|g')`
3. Derive the wing key: `WING=$PROJECT_DIR`
4. **Incremental mining:** if `transcript_path` is provided and the file exists, mine only that file: `mempalace mine "$TRANSCRIPT_PATH" --mode convos --wing "$WING"`. This is the precise incremental signal — one session's JSONL, not the entire project directory.
5. **Fallback:** if `transcript_path` is missing or empty, mine the full directory: `mempalace mine ~/.claude/projects/$PROJECT_DIR/ --mode convos --wing "$WING"`. This handles first-run and catch-up scenarios.
6. Update state files with new timestamp and drawer count

### Wing/Room Mapping

- **Wing** = full path-derived Claude directory name (e.g., `-Users-sunginkim--superset-projects-ark-skills`) as the ChromaDB key. The human-readable project name from CLAUDE.md (e.g., `ark-skills`) is used only in vault page output.
- **Rooms** = auto-detected by mempalace's `room_detector_local.py` (topics like `auth`, `deployment`, `refactoring`)
- **Halls** = mempalace defaults (`hall_facts`, `hall_events`, `hall_discoveries`, `hall_preferences`, `hall_advice`)

### Scope

- **Default:** only mines `~/.claude/projects/$PROJECT_DIR/` (current project)
- **`--scope all`:** iterates all directories under `~/.claude/projects/`, each becoming its own wing

### Performance

The hook spawns `mempalace mine` via `nohup` so it survives shell exit:

```bash
LOCK="$STATE_DIR/${WING}.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "{}"  # another index is running, skip
    exit 0
fi
nohup bash -c "
    mempalace mine \"$CLAUDE_PROJECT\" --mode convos 2>>\"$STATE_DIR/mine.log\"
    date +%s > \"$STATE_DIR/${WING}_last_indexed\"
    mempalace status --json | python3 -c \"import sys,json; print(json.load(sys.stdin)['total_drawers'])\" > \"$STATE_DIR/${WING}_drawer_count\"
    touch \"$STATE_DIR/${WING}_done\"
    rmdir \"$LOCK\"
" &>/dev/null &
echo "{}"  # return immediately
```

Key properties:
- **Lock directory** prevents concurrent indexing (two terminals ending at once)
- **`nohup`** survives hook shell exit
- **Completion marker** (`{wing}_done`) signals the next session that results are ready
- **Threshold check** on any given session end uses the *previous* session's mining results. Compile is always one session behind index — acceptable since it's not time-critical.

### State Files

Wing keys are the path-derived directory names (matching the ChromaDB wing). Human-readable project names are only used in vault page output.

```
~/.mempalace/hook_state/
├── -Users-sunginkim--superset-projects-ark-skills_last_indexed
├── -Users-sunginkim--superset-projects-ark-skills_drawer_count
├── -Users-sunginkim--superset-projects-trading-signal-ai_last_indexed
└── compile_threshold.json           # per-project keyed by wing: {drawers_at_last_compile: N}
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

**Important: the hook never writes to the vault or runs git.** It only returns the block decision. Claude receives the compile instructions, runs the search queries, writes insight pages, and controls what gets staged and committed. This keeps git operations under Claude's judgment (e.g., checking for dirty worktree, avoiding `git add -A` in favor of specific file adds, handling auth failures gracefully).

### Compile Process

1. **Read memory files directly** — `~/.claude/projects/{project}/memory/*.md`. Small, high-signal, read raw. No change from current skill.

2. **Dynamic topic discovery** — query `mempalace_list_rooms(wing=WING)` to get the actual room names mempalace detected (e.g., `auth-migration`, `ci-pipeline`, `graphql-switch`). Combine these with a baseline set of general queries (`"architecture decisions"`, `"debugging lessons"`, `"failed approaches"`). This prevents recall loss from relying only on pre-defined search terms — any topic mempalace detected gets searched.

3. **Query mempalace for each topic** — run semantic searches using the path-derived wing key, one per topic from step 2:
   - `mempalace_search("architecture decisions", wing="-Users-sunginkim--superset-projects-ark-skills", n_results=10)`
   - `mempalace_search("auth-migration", wing="-Users-sunginkim--superset-projects-ark-skills", n_results=10)`
   - `mempalace_search("ci-pipeline", wing="-Users-sunginkim--superset-projects-ark-skills", n_results=10)`
   - (one search per discovered room + baseline topics)

4. **Diff against existing insights** — read existing compiled insight pages. Only generate new pages for clusters with genuinely new information.

5. **Write compiled insight pages** — same Ark frontmatter schema, same template, same vault location (`{vault_path}/{project_area}/Research/Compiled-Insights/`). `source-sessions:` populated from mempalace drawer metadata.

6. **Update index and commit** — `generate-index.py`, then stage only the new/modified insight pages and index.md (not `git add -A`), commit, push.

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
| `full` (default) | Index synchronously, then compile regardless of threshold | ~10K |

Note: `full` mode always compiles (it's a manual invocation, so threshold gating doesn't apply). Auto-compile via the Stop hook is the only path that respects the threshold — it fires only when enough new drawers have accumulated.

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
- Read `session_id`, `transcript_path`, and `stop_hook_active` from stdin JSON
- If `stop_hook_active` is true, return `{}` (prevents infinite block loop)
- Acquire lock directory; skip if another index is running
- Run `mempalace mine` via `nohup` on the session's transcript file (incremental) or full project directory (fallback)
- Check drawer count against compile threshold (using previous session's results)
- Return `{"decision": "block", "reason": "...compile instructions..."}` if threshold met, or `{}` otherwise
- **Never** writes to the vault, runs git, or modifies project files — only returns the block decision
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

## Implementation Concerns (from Codex review)

These are valid concerns to address during implementation, documented here for tracking:

- **Version pinning:** Pin `mempalace` to a tested version range. ChromaDB version drift (#257) is a known risk. Use a virtualenv or document the interpreter requirement.
- **Privacy/retention:** Add a `.mempalace-ignore` pattern (similar to `.gitignore`) so users can exclude sensitive session files from indexing. Document the delete/reset path (`mempalace` CLI or direct ChromaDB deletion).
- **ARM64 circuit breaker:** Track consecutive failures in state. After 3 consecutive segfaults, disable auto-indexing and log a warning instead of retrying forever.
- **Deterministic diffing:** During compile, use mempalace drawer IDs (content hashes) as stable identifiers. Track which drawer IDs have been compiled into which insight pages via a `compiled_drawers.json` state file.
- **CLI vs MCP parity:** Document exactly which metadata fields are available in each mode. If `source-sessions:` can't be reliably extracted from CLI output, make MCP a hard requirement for compile (not optional).

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
