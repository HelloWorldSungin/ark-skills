---
name: notebooklm-vault
description: Persistent context and memory layer backed by the Obsidian vault synced to Google NotebookLM. Use this skill whenever starting a fresh session and needing project history, when asking "what happened in session X", "what's the current project state", "has this been tried before", or when generating audio/reports from vault content. Triggers on bootstrap, vault context, session history, conflict check, or any question about past decisions/experiments. Warm-start triggers for session-continue: "resume from last session", "continue where I left off", "warm start", "pick up where I left off". Do NOT trigger on phrases containing "session log", "wrap up", "hand off", or "end session" — those belong to /wiki-update. Do NOT use for general NotebookLM operations unrelated to the vault — use the global notebooklm skill for those.
---

# NotebookLM Vault — Persistent Project Memory

This skill bridges the Obsidian vault with Google NotebookLM to give Claude Code persistent memory across sessions. The vault contains session logs, architecture decisions, research notes, and strategy documentation — the project's institutional memory.

## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, vault root, project docs path
2. Read the **project repo's** `.notebooklm/config.json` for notebook configuration (this is the tracked, authoritative source). The vault repo holds `.notebooklm/sync-state.json` (runtime state, not config).
3. Determine notebook structure: single notebook (one key) or multi-notebook (trading + infra)
4. For tiered retrieval: read vault's `index.md` and use `summary:` fields to scan before reading full pages

## Architecture

A single NotebookLM notebook holds the vault content:

| Notebook | Vault Path | Content |
|----------|-----------|---------|
| **the notebook name from `.notebooklm/config.json`** | `{project_docs_path}/` | Session logs, strategies, models, research, operations |

**Note:** TaskNotes (`{tasknotes_path}/`) are NOT synced to NotebookLM. They are managed locally in Obsidian only.

Config lives in `.notebooklm/config.json` (project repo, tracked). Sync state lives in `vault/.notebooklm/sync-state.json` (vault repo, tracked, shared across environments). The vault also has its own `.notebooklm/config.json` with `vault_root: "."`.

## Prerequisites

- `notebooklm` CLI installed globally via pipx (v0.3.3+)
- Authenticated: `notebooklm auth check --test`
- Google AI Pro plan (300 source limit per notebook)
- Obsidian running locally (required for `obsidian` CLI commands)

## Vault Access — Use `obsidian` CLI

When reading or searching vault files, prefer the `obsidian` CLI (from the `obsidian:obsidian-cli` skill) over raw `Read`/`Glob`/`Grep` tools. The CLI returns only the content you need and costs significantly fewer tokens on large files like session logs.

**Reading notes** — use wikilink-style name resolution (no path or extension needed):
```bash
obsidian read file="Session-001"                    # Read a session log
obsidian read file="{task_prefix}001-research-pipeline"  # Read a TaskNote epic
```

**Searching the vault** — much cheaper than Grep across hundreds of files:
```bash
obsidian search query="ensemble forecasting" limit=10     # Full-text search
```
Note: `obsidian search` is plain-text only — it does NOT support property-based operators like `task-type:epic`. To find epics, search for keywords that appear in epic files.

**Reading/setting frontmatter properties** — avoids parsing YAML manually:
```bash
obsidian property:read name="epic" file="Session-001"
obsidian property:set name="status" value="in-progress" file="{task_prefix}001-research-pipeline" silent
```

**Finding backlinks** — discover what references a note:
```bash
obsidian backlinks file="{task_prefix}001-research-pipeline"  # Find stories linking to epic
```

**Listing tasks** — find TaskNotes by status:
```bash
obsidian tasks query="status:in-progress project:{project_name}"
```

Fall back to raw `Read`/`Glob` only when Obsidian is not running or when you need to write/create files (use the `obsidian:obsidian-markdown` skill for creating vault files).

## Sub-Commands

Route on `$ARGUMENTS`. If no argument is provided, show available sub-commands.

---

### `setup` — One-Time Initialization

Creates the notebook, configures persona, bulk imports all vault .md files, and saves config.

1. Verify auth: `notebooklm auth check --test`
2. Create notebook:
   ```bash
   notebooklm create "the notebook name from `.notebooklm/config.json`" --json
   ```
   Parse the `id` from JSON output.
3. Configure the notebook:
   ```bash
   PERSONA='You are a senior engineer reviewing the {project_name} project. Answer questions with specific session numbers, dates, experiment results, and code references. When tracing decisions, cite the session logs where they were made. Be thorough and precise.'
   notebooklm configure --notebook <notebook_id> --mode detailed --persona "$PERSONA" --response-length longer
   ```
4. Write `.notebooklm/config.json`:
   ```json
   {
     "notebooks": {
       "main": { "id": "<notebook_id>", "title": "the notebook name from `.notebooklm/config.json`" }
     },
     "persona": "<the persona string>",
     "mode": "detailed",
     "response_length": "longer",
     "vault_root": "vault"
   }
   ```
5. Run full sync to import all files:
   ```bash
   bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh --full
   ```
6. Report results: notebook ID, source count, any errors.

---

### `ask "question"` — Notebook Query

Queries the notebook and returns answers with source citations.

1. Read `.notebooklm/config.json` for notebook ID.
2. Query:
   ```bash
   notebooklm ask "question" --notebook <id> --json
   ```
3. Present the answer with source citations.

---

### `session-continue` — Resume From Last Session

Targeted warm start that reads the most recent session log and its linked epic to pick up where the previous session left off.

1. Find the most recent session log. Use Glob on `{project_docs_path}/Session-Logs/S*.md` (Ark convention: files are named `S{NNN}-{slug}.md`, not `Session-{NNN}.md`), then sort results by the numeric session number (not by mtime). Read the highest-numbered session via `obsidian` CLI:
   ```bash
   obsidian read file="S<NNN>-<slug>"
   ```
2. Extract the `epic` frontmatter field efficiently:
   ```bash
   obsidian property:read name="epic" file="S<NNN>-<slug>"
   ```
   Also extract the following sections from the content returned by the read: **Next Steps**, **Open Questions**, **Decisions Made**, and **Work Done**. These are the sections written by `/wiki-update` 1.8.0+. For older logs (pre-1.8.0) that use **Results** / **Issues & Discoveries** section names, fall back to those.
3. Identify the related epic:
   - If the session log has an `epic` frontmatter field, use that directly.
   - **Fallback for older session logs without `epic` field:** Infer the epic from the session's tags and content.
4. If an epic is identified, read it and find related stories using `obsidian` CLI:
   ```bash
   obsidian read file="<epic-id>-<slug>"
   obsidian backlinks file="<epic-id>-<slug>"   # finds stories that link to the epic
   ```
5. Query NotebookLM for related context:
   ```bash
   notebooklm ask "What sessions are related to: <summary of next steps from session log>? Include session numbers, outcomes, and any gotchas." --notebook <id> --json
   ```
6. Present a structured resume brief (all sections are required):

```markdown
## Resuming from Session <NNN>

### Where We Left Off
[Status from session log — what was accomplished, current state]

### Epic Progress — <Epic Title> (<epic-id>)
[Stories completed vs. remaining, overall epic status]

### Immediate Next Steps
[Next steps from session log + outstanding stories, ordered by priority]

### Critical Context
[Issues/discoveries from session log, blockers from stories]

### Related Prior Work
[Any relevant sessions from NotebookLM query]
```

7. If no session log exists, or no epic can be identified, fall back to `bootstrap`.

---

### `bootstrap` — Fresh Session Context Loader

Broad project overview for cold starts when no recent session log has a linked epic or when starting entirely new work.

1. Read `.notebooklm/config.json` for notebook ID.
2. Query the notebook with these questions (run in sequence):
   ```bash
   notebooklm ask "List the 5 most recent session logs with: session number, date, objective, key outcomes, and unresolved items" --notebook <id> --json
   ```
   ```bash
   notebooklm ask "What is the current project state? What has been built so far and what is planned next?" --notebook <id> --json
   ```
   ```bash
   notebooklm ask "What are the top open issues, ongoing experiments, or blocked work items?" --notebook <id> --json
   ```
3. Format all answers into a structured context brief:

```markdown
## Session Context Brief

### Recent Sessions
[5 most recent sessions with numbers, dates, objectives, outcomes, unresolved items]

### Current Project State
[What's built, what's planned, current development phase]

### Open Issues & Experiments
[Active work items, blocked items, experiments in progress]
```

---

### `audio "description"` — Generate Podcast Deep-Dive

Generates a podcast-style audio overview from vault sources.

1. Read config for notebook ID.
2. Generate:
   ```bash
   notebooklm generate audio "description" --notebook <id> --format deep-dive --json
   ```
3. Parse `artifact_id` from output.
4. Spawn a background agent to wait and download:
   ```
   notebooklm artifact wait <artifact_id> -n <notebook_id> --timeout 1200
   notebooklm download audio ./outputs/<descriptive-name>.mp3 -a <artifact_id> -n <notebook_id>
   ```
5. Tell the user generation is in progress and they'll be notified when complete.

---

### `report` — Generate Briefing Document

Generates a briefing doc summarizing recent changes from the notebook.

1. Read config.
2. Generate:
   ```bash
   notebooklm generate report --notebook <id> --format briefing-doc --json
   ```
3. Parse artifact ID, wait for completion, download:
   ```bash
   notebooklm download report ./outputs/vault-briefing.md -a <artifact_id> -n <id>
   ```

---

### `conflict-check "approach"` — Decision Conflict Detection

Checks if a proposed approach contradicts past decisions recorded in the vault.

1. Read config for notebook ID.
2. Formulate the query:
   ```
   Has this approach been tried before or does it contradict previous decisions: [user's approach]. Search all session logs for related experiments, failures, or architectural decisions. Be specific about session numbers and outcomes.
   ```
3. Query the notebook:
   ```bash
   notebooklm ask "<query>" --notebook <id> --json
   ```
4. Present findings:
   - **Conflicts found** — with session references and what happened
   - **Related history** — similar experiments or decisions
   - **Recommendation** — proceed, modify approach, or reconsider

---

### `status` — Show Sync Status

Displays notebook ID, source count, and last sync timestamp.

1. Read `.notebooklm/config.json` for notebook ID.
2. Query source count:
   ```bash
   notebooklm source list --notebook <id> --json
   ```
3. Read `vault/.notebooklm/sync-state.json` for last sync timestamp.
4. Display:
   ```
   Notebook: <id> — N sources
   Last sync: 2026-03-24T12:00:00Z
   Vault root: vault
   ```

---

## Tiered Retrieval (Post-Restructuring)

When querying vault knowledge:
1. **Tier 1 — Index scan:** Read `index.md` to find relevant pages by category and summary
2. **Tier 2 — Summary scan:** Read `summary:` frontmatter of candidate pages (cheap, <=200 chars each)
3. **Tier 3 — Full read:** Only open full page content for the top 3-5 most relevant candidates
4. **Navigation context:** Read `_meta/vault-schema.md` to understand folder structure before exploring

## Notebook Querying

Read `.notebooklm/config.json` to determine notebook structure:
- **Single notebook:** Query the one configured notebook
- **Multiple notebooks:** Query each notebook, merge results, note which notebook each answer came from

## Important Notes

- **Always use `--notebook <id>` explicitly** — never rely on `notebooklm use` context, which can be overwritten by parallel agent sessions.
- **The sync script is the source of truth** for file->source mapping. Don't manually add sources outside of it.
- **Config is tracked, sync-state is in vault repo** — config stays in the project repo's `.notebooklm/config.json`. Sync state lives in the vault repo at `vault/.notebooklm/sync-state.json` and is shared across environments.
- **This skill complements the global `notebooklm` skill** — use this one for vault-specific operations, use the global one for general NotebookLM tasks.
- **Periodic sync is owned by the scheduled sync service.** Do not run the sync script locally except during `setup` (one-time `--full` bootstrap). Local runs diverge `sync-state.json` and cause duplicate sources hitting the 300-source-per-notebook cap.
