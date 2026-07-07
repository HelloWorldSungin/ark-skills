---
name: notebooklm-vault
description: Synthesized-recall backend for the OKF knowledge bundle at vault/, synced to Google NotebookLM. Use this skill whenever starting a fresh session and needing project history, when asking "what's the current project state", "has this been tried before", "why did we decide X", or when generating audio/reports from vault content. Triggers on bootstrap, vault context, conflict check, or any question about past decisions/research. Warm-start triggers for session-continue: "resume from last session", "continue where I left off", "warm start", "pick up where I left off". Do NOT use for writing to the vault — that is the /vault skill. Do NOT use for general NotebookLM operations unrelated to the vault — use the global notebooklm skill for those.
---

# NotebookLM Vault — Synthesized Project Recall

This skill bridges the OKF knowledge bundle at `vault/` with Google NotebookLM to give Claude Code synthesized recall over the project's institutional memory. The bundle contains durable knowledge only — research notes, architecture decisions, and reference pages. The active work record lives in GitHub issues and the bundle's `log.md` (session logs are retired). Reads are synthesized here; writes go through the `/vault` skill.

## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, vault root, project docs path
2. Read the notebook configuration from `.notebooklm/config.json`. Lookup order: project root first, then vault root (`vault/.notebooklm/config.json`). Monorepo layouts use the project-root config as the authoritative tracked source; standalone layouts use the vault-root config exclusively. Sync-state (`.notebooklm/sync-state.json`) lives inside the vault repo regardless of layout.
3. Determine notebook structure: single notebook (one key) or multi-notebook (trading + infra)
4. For navigation: use `python3 vault/_meta/okf/okf_cli.py {list,search}` to scan the OKF bundle by `description:` before reading full pages

## Architecture

A single NotebookLM notebook holds the vault content:

| Notebook | Vault Path | Content |
|----------|-----------|---------|
| **the notebook name from `.notebooklm/config.json`** | `{project_docs_path}/` | OKF knowledge bundle: research, decisions, reference pages, `log.md` |

**Note:** the frozen `TaskNotes/` and `Session-Logs/` legacy trees are NOT synced to NotebookLM — the active work record is GitHub issues + the bundle's `log.md`.

Config layout depends on whether the vault is monorepo or standalone:

- **Monorepo / wrapped:** `.notebooklm/config.json` lives in the project repo (tracked, authoritative) with `vault_root: "vault"`. The vault repo also carries its own `.notebooklm/config.json` with `vault_root: "."` for direct-mode sync from inside the vault.
- **Standalone:** only the vault-side `.notebooklm/config.json` (with `vault_root: "."`) exists. The project repo does NOT carry a `.notebooklm/config.json` — it would be redundant and historically caused the centralized-standalone scan-base bug.

Sync state always lives in `vault/.notebooklm/sync-state.json` (vault repo, tracked, shared across environments).

### Centralized Vault Awareness

When the project's `vault` is a symlink (centralized-vault pattern), this skill:
- Reads `.notebooklm/config.json` from the project root first (monorepo layouts: expected `vault_root: "vault"`), falls back to `<vault>/.notebooklm/config.json` (standalone layouts: expected `vault_root: "."`, AND the only config that exists). Both forms resolve to the same vault directory; the script's standalone-marker detection (`_meta/`, `_Templates/`, `TaskNotes/` at vault root) keeps scan-base resolution correct even if a stray `vault_root: "vault"` project config is left behind on a standalone vault.
- Locates `sync-state.json` exclusively inside the vault repo: `<vault>/.notebooklm/sync-state.json`. Never writes sync-state to the project repo.
- Bootstraps missing `sync-state.json` with empty state `{"last_sync": null, "files": {}}` on first sync.

Detect via `test -L vault`. When vault is NOT a symlink (embedded layout), sync-state remains in the project repo's `.notebooklm/` directory — backward compatible.

## Prerequisites

- `notebooklm` CLI installed globally via pipx (v0.3.3+)
- Authenticated: `notebooklm auth check --test`
- Google AI Pro plan (300 source limit per notebook)

## Vault Access — Use `okf_cli.py`

When reading or searching the bundle locally (outside NotebookLM), use the in-bundle OKF CLI over raw `Read`/`Glob`/`Grep`. It returns only the content you need and scans by `description:` cheaply.

```bash
python3 vault/_meta/okf/okf_cli.py list                 # Catalog all pages with descriptions
python3 vault/_meta/okf/okf_cli.py search "ensemble forecasting"   # Full-text search
python3 vault/_meta/okf/okf_cli.py read <page-path>     # Read a specific page
```

Fall back to raw `Read`/`Glob` only when you need to inspect non-markdown assets. Writing to the bundle is never this skill's job — use the `/vault` skill.

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
   PERSONA='You are a senior engineer reviewing the {project_name} project. Answer questions with specific dates, experiment results, and code references. When tracing decisions, cite the knowledge pages where they were recorded. Be thorough and precise.'
   notebooklm configure --notebook <notebook_id> --mode detailed --persona "$PERSONA" --response-length longer
   ```
4. Persist the notebook config. Detect layout first:
   - **Standalone vault** — vault root contains `_meta/`, `_Templates/`, or `TaskNotes/` directly (no wrapping project subdir).
   - **Monorepo / wrapped vault** — vault root contains a project subdirectory which contains those marker dirs.

   ```bash
   if [ -d vault/_meta ] || [ -d vault/_Templates ] || [ -d vault/TaskNotes ]; then
     LAYOUT=standalone
   else
     LAYOUT=monorepo
   fi
   ```

   **Standalone:** the vault-side config (`vault/.notebooklm/config.json`) is the only config. `/ark-onboard` Step 15 already wrote a stub there with `vault_root: "."`; fill in `notebooks.main.id` and persist the persona. Do NOT write a project-level config — for standalone it would be redundant at best and induce the centralized-standalone scan-base bug at worst (script lands on the first non-excluded subdirectory instead of the vault root). The sync script's marker-based standalone detection makes a stray project-level config harmless, but skipping it keeps the source of truth singular.

   **Monorepo:** write `.notebooklm/config.json` at the **project root** (tracked) — this is the authoritative config for monorepo layouts because it carries the wrapping `vault_root: "vault"` plus any project-docs-subdir routing.

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

### `session-continue` — Resume From Last Work

Targeted warm start that reads the most recent work record — the bundle's `log.md` tail plus the referenced GitHub epic — to pick up where the previous session left off. The GitHub epic is the plan and resume state (there are no session logs).

1. Read the tail of the OKF bundle's `log.md` for the most recent work-record lines. Each line carries an issue number, a one-line summary, and a link back to the GitHub comment permalink:
   ```bash
   tail -n 30 vault/log.md
   ```
2. Identify the active epic/issue from those lines (the most recent issue number, or the epic it references).
3. Read that GitHub issue and its comments — this is the authoritative record of progress, decisions, and next steps:
   ```bash
   gh issue view <n> --comments
   ```
   If it is a child issue, follow its "Part of #NNN" reference to the epic and read the epic body (its task-list children show what is done vs. remaining).
4. Query NotebookLM for related durable context (research, prior decisions):
   ```bash
   notebooklm ask "What prior work or decisions relate to: <summary of the epic's open items>? Include outcomes and any gotchas." --notebook <id> --json
   ```
5. Present a structured resume brief (all sections are required):

```markdown
## Resuming — Epic #<n> <Epic Title>

### Where We Left Off
[Latest progress from the issue comments + log.md tail — what was accomplished, current state]

### Epic Progress
[Children completed vs. remaining from the epic task-list, overall status]

### Immediate Next Steps
[Next steps from the latest issue comments + open children, ordered by priority]

### Critical Context
[Blockers, discovered-work issues, open questions from the issue thread]

### Related Prior Work
[Any relevant durable knowledge from the NotebookLM query]
```

6. If `log.md` is empty or no epic can be identified, fall back to `bootstrap`.

---

### `bootstrap` — Fresh Session Context Loader

Broad project overview for cold starts when `log.md` has no resolvable epic or when starting entirely new work.

1. Read `.notebooklm/config.json` for notebook ID.
2. Query the notebook with these questions (run in sequence):
   ```bash
   notebooklm ask "Summarize the most recent research findings and decisions, with dates and outcomes" --notebook <id> --json
   ```
   ```bash
   notebooklm ask "What is the current project state? What has been built so far and what is planned next?" --notebook <id> --json
   ```
   ```bash
   notebooklm ask "What are the top open questions, ongoing experiments, or unresolved decisions?" --notebook <id> --json
   ```
3. Format all answers into a structured context brief:

```markdown
## Project Context Brief

### Recent Findings & Decisions
[Most recent research findings and decisions with dates and outcomes]

### Current Project State
[What's built, what's planned, current development phase]

### Open Questions & Experiments
[Unresolved decisions, experiments in progress, open questions]
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
   Has this approach been tried before or does it contradict previous decisions: [user's approach]. Search the knowledge bundle for related experiments, failures, or architectural decisions. Be specific about outcomes and cite the pages.
   ```
3. Query the notebook:
   ```bash
   notebooklm ask "<query>" --notebook <id> --json
   ```
4. Present findings:
   - **Conflicts found** — with page references and what happened
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

## Local Retrieval (when not querying NotebookLM)

When reading the bundle directly:
1. **Catalog scan:** `python3 vault/_meta/okf/okf_cli.py list` to find relevant pages by `description:`
2. **Search:** `python3 vault/_meta/okf/okf_cli.py search "<terms>"` for full-text matches
3. **Full read:** `python3 vault/_meta/okf/okf_cli.py read <page-path>` for the top 3-5 candidates only
4. **Navigation context:** read `vault/_meta/vault-schema.md` to understand folder structure before exploring

## Notebook Querying

Read `.notebooklm/config.json` to determine notebook structure:
- **Single notebook:** Query the one configured notebook
- **Multiple notebooks:** Query each notebook, merge results, note which notebook each answer came from

## Important Notes

- **Always use `--notebook <id>` explicitly** — never rely on `notebooklm use` context, which can be overwritten by parallel agent sessions.
- **NotebookLM is the source of truth for existence, sync-state is a hash cache** (since plugin v1.9.0). Every incremental sync lists remote sources, dedupes by title, prunes orphans, and only then uploads new/changed files. Running the sync script locally is now safe — it self-heals any drift rather than creating duplicates.
- **Config is tracked, sync-state is in vault repo** — for monorepo layouts, config lives in the project repo's `.notebooklm/config.json`. For standalone layouts, config lives only in the vault repo's `.notebooklm/config.json`. Sync state always lives in the vault repo at `vault/.notebooklm/sync-state.json` and is shared across environments.
- **This skill complements the global `notebooklm` skill** — use this one for vault-specific operations, use the global one for general NotebookLM tasks.
- **Concurrent runs fail loudly.** A mkdir-based per-vault lock at `/tmp/notebooklm-vault-sync.<vault>.lock` serializes syncs. If two runs race, the second exits with `Another sync is already running`.

## Sync Behavior

The sync script (`scripts/notebooklm-vault-sync.sh`) has three operational modes:

| Mode | When to use | What it does |
|------|-------------|--------------|
| Incremental (default) | Normal runs, end-of-session, after `/vault` writes | Lists remote sources → dedupes & prunes orphans → uploads new/changed files. Self-heals any accumulated drift on every run. |
| `--file PATH` | Single-file sync (fast path) | Fetches target notebook's sources, syncs just that file. Skips dedupe/heal for speed. |
| `--full` | **Emergency recovery only** | Nukes all sources in the notebook and re-uploads. Use only if a notebook hits the 300-source cap or state has drifted beyond what incremental can heal. |

**Ghost-registration recovery (built in).** `notebooklm source add` is a 3-step pipeline (register → start-upload → stream). If step 2 or 3 fails, a ghost source remains on the server. The script snapshots per-title source IDs before each add; on failure, re-lists and claims the ghost instead of creating a duplicate on retry.

**Troubleshooting:**
- *"Another sync is already running"* — wait for the other run, or inspect `/tmp/notebooklm-vault-sync.<vault>.lock/pid`. Stale locks (from crashed runs) are detected and removed automatically on the next run.
- *"FATAL: Filename collisions detected"* — NotebookLM titles sources by basename only. Two vault files with the same basename routed to the same notebook would silently overwrite each other. Rename one or move it to an excluded directory.
- *Notebook hit 300-source cap* — run `--full` once to nuke + rebuild. Going forward, the dedupe pass prevents recurrence.
