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

### Centralized Vault Awareness

When the project's `vault` is a symlink (centralized-vault pattern), this skill:
- Reads `.notebooklm/config.json` from the project root first (expected `vault_root: "vault"`), falls back to `<vault>/.notebooklm/config.json` (expected `vault_root: "."`). Both resolve to the same directory.
- Locates `sync-state.json` exclusively inside the vault repo: `<vault>/.notebooklm/sync-state.json`. Never writes sync-state to the project repo.
- Bootstraps missing `sync-state.json` with empty state `{"last_sync": null, "files": {}}` on first sync.

Detect via `test -L vault`. When vault is NOT a symlink (embedded layout), sync-state remains in the project repo's `.notebooklm/` directory — backward compatible.

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

## Warmup Contract

Machine-readable subcontract consumed by `/ark-context-warmup`. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`. Calling convention: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` D6.

```yaml
warmup_contract:
  version: 1
  commands:
    - id: session-continue
      shell: 'notebooklm ask {{prompt}} --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id:
          from: config
          config_path: '.notebooklm/config.json'
          config_lookup_order: ['vault_root/.notebooklm/config.json', '.notebooklm/config.json']
          # Per D5 (plan §Decisions Pinned): if config.notebooks has exactly one entry,
          # use it. If it has >1 entry, config.default_for_warmup MUST be set —
          # otherwise the availability probe skips the lane with a remediation hint.
          # No silent fallback to "main". The executor resolves this via the lookup
          # rule, not a json_path fallback syntax.
          lookup: single_or_default_for_warmup
          json_path_template: 'notebooks.{key}.id'
          required: true
        prompt:
          from: template
          template_id: session_continue_prompt
      preconditions:
        - id: recent_session_with_shape
          script: scripts/session_shape_check.sh
          description: 'Exits 0 if latest session log <7 days old AND has Next Steps section AND resolvable epic link'
      output:
        format: json
        extract:
          where_we_left_off: '$.answer.sections.where_we_left_off'
          epic_progress: '$.answer.sections.epic_progress'
          immediate_next_steps: '$.answer.sections.immediate_next_steps'
          critical_context: '$.answer.sections.critical_context'
          citations: '$.citations'
        required_fields: [where_we_left_off, immediate_next_steps]
    - id: bootstrap
      shell: 'notebooklm ask {{prompt}} --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id:
          from: config
          config_path: '.notebooklm/config.json'
          config_lookup_order: ['vault_root/.notebooklm/config.json', '.notebooklm/config.json']
          # Per D5 (plan §Decisions Pinned): if config.notebooks has exactly one entry,
          # use it. If it has >1 entry, config.default_for_warmup MUST be set —
          # otherwise the availability probe skips the lane with a remediation hint.
          # No silent fallback to "main". The executor resolves this via the lookup
          # rule, not a json_path fallback syntax.
          lookup: single_or_default_for_warmup
          json_path_template: 'notebooks.{key}.id'
          required: true
        prompt:
          from: template
          template_id: bootstrap_prompt
      output:
        format: json
        extract:
          recent_sessions: '$.answer.sections.recent_sessions'
          current_state: '$.answer.sections.current_state'
          open_issues: '$.answer.sections.open_issues'
          citations: '$.citations'
        required_fields: [recent_sessions, current_state]
  prompt_templates:
    # Single-brace placeholders like {WARMUP_TASK_TEXT} and {WARMUP_PROJECT_NAME}
    # are interpolated by the executor from the environment at resolve time
    # (see executor._interpolate_template). Unknown placeholders pass through
    # literally so a typo surfaces as garbage in the backend response rather
    # than crashing the lane. Double-brace (`{{prompt}}`, `{{notebook_id}}`)
    # is a separate, later substitution applied against the `shell:` template
    # by substitute_shell_template — do not mix the two forms.
    session_continue_prompt: |
      What sessions are related to: {WARMUP_TASK_TEXT}? Include session numbers,
      outcomes, and any gotchas. Structure the answer with these exact headings:
      "Where We Left Off", "Epic Progress", "Immediate Next Steps", "Critical Context".
    bootstrap_prompt: |
      For the {WARMUP_PROJECT_NAME} project, provide: (1) the 5 most recent session
      logs with session number, date, objective, key outcomes, unresolved items;
      (2) the current project state — what is built, what is planned; (3) the top
      open issues, ongoing experiments, or blocked work items. Structure the answer
      with these exact headings: "Recent Sessions", "Current State", "Open Issues".
  selection_rules:
    # Per spec decision D5: no silent first-pick on multi-notebook configs.
    - rule: single_notebook
      when: 'config.notebooks has exactly one entry'
      action: 'use that notebook'
    - rule: explicit_default
      when: 'config.notebooks has >1 entry AND config.default_for_warmup is set'
      action: 'use config.notebooks[config.default_for_warmup]'
    - rule: ambiguous_multi_notebook
      when: 'config.notebooks has >1 entry AND config.default_for_warmup is NOT set'
      action: 'skip entire lane; log: "Multi-notebook NotebookLM config without default_for_warmup — lane skipped. Add default_for_warmup to .notebooklm/config.json pointing at the notebook key to use."'
```

## Important Notes

- **Always use `--notebook <id>` explicitly** — never rely on `notebooklm use` context, which can be overwritten by parallel agent sessions.
- **NotebookLM is the source of truth for existence, sync-state is a hash cache** (since plugin v1.9.0). Every incremental sync lists remote sources, dedupes by title, prunes orphans, and only then uploads new/changed files. Running the sync script locally is now safe — it self-heals any drift rather than creating duplicates.
- **Config is tracked, sync-state is in vault repo** — config stays in the project repo's `.notebooklm/config.json`. Sync state lives in the vault repo at `vault/.notebooklm/sync-state.json` and is shared across environments.
- **This skill complements the global `notebooklm` skill** — use this one for vault-specific operations, use the global one for general NotebookLM tasks.
- **Concurrent runs fail loudly.** A mkdir-based per-vault lock at `/tmp/notebooklm-vault-sync.<vault>.lock` serializes syncs. If two runs race, the second exits with `Another sync is already running`.

## Sync Behavior

The sync script (`scripts/notebooklm-vault-sync.sh`) has three operational modes:

| Mode | When to use | What it does |
|------|-------------|--------------|
| Incremental (default) | Normal runs, end-of-session, `/wiki-update` | Lists remote sources → dedupes & prunes orphans → uploads new/changed files. Self-heals any accumulated drift on every run. |
| `--sessions-only` | Quick refresh of just session logs | Same as incremental, scoped to `Session-Logs/` only. |
| `--file PATH` | Single-file sync (fast path) | Fetches target notebook's sources, syncs just that file. Skips dedupe/heal for speed. |
| `--full` | **Emergency recovery only** | Nukes all sources in the notebook and re-uploads. Use only if a notebook hits the 300-source cap or state has drifted beyond what incremental can heal. |

**Ghost-registration recovery (built in).** `notebooklm source add` is a 3-step pipeline (register → start-upload → stream). If step 2 or 3 fails, a ghost source remains on the server. The script snapshots per-title source IDs before each add; on failure, re-lists and claims the ghost instead of creating a duplicate on retry.

**Troubleshooting:**
- *"Another sync is already running"* — wait for the other run, or inspect `/tmp/notebooklm-vault-sync.<vault>.lock/pid`. Stale locks (from crashed runs) are detected and removed automatically on the next run.
- *"FATAL: Filename collisions detected"* — NotebookLM titles sources by basename only. Two vault files with the same basename routed to the same notebook would silently overwrite each other. Rename one or move it to an excluded directory.
- *Notebook hit 300-source cap* — run `--full` once to nuke + rebuild. Going forward, the dedupe pass prevents recurrence.
