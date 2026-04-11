<workflow name="sync-vault">
<title>Obsidian Vault Sync</title>
<description>Analyze code changes on the current branch, map them to Obsidian vault documentation areas, and ensure relevant notes are up to date. Creates missing notes when new features or components lack documentation. Syncs changes to NotebookLM when done.</description>

<vault_layout>
Vault location: `vault/` (relative to project root)

```
vault/
├── 00-Home.md                          — Vault dashboard
├── 00-Onboarding.md                    — New developer/agent entry point
├── {project_docs_path}/
│   ├── 00-Project-Overview.md          — Project MOC
│   ├── Models/                         — Model documentation
│   ├── Strategies/                     — Trading strategy docs
│   ├── Research/                       — Research notes and analysis
│   │   └── 00-Research-Index.md
│   ├── Operations/                     — Deployment, monitoring, config
│   └── Session-Logs/                   — Build journal (Session-XXX.md)
│       └── 00-Session-Logs-Index.md    — Session index
├── TaskNotes/
│   ├── 00-Project-Management-Guide.md  — Setup & conventions
│   ├── meta/                           — Counter files for task IDs
│   └── Tasks/
│       ├── Epic/                       — Multi-sprint initiatives
│       ├── Story/                      — One-sprint features
│       ├── Task/                       — Standalone tasks
│       └── Bug/                        — Bug tickets
└── _Templates/                         — Note templates
```

If you discover that the vault structure has changed (new top-level directories, reorganized subdirectories, renamed paths), update this layout section in sync-vault.md so future runs have an accurate map.
</vault_layout>

<prerequisites>
BEFORE any vault work, do these steps in order:

1. **Invoke the `obsidian:obsidian-cli` skill** — This loads the CLI reference into your context. You need it for every vault read and search below.
2. **Test the CLI works** — Run `obsidian read file="00-Home"` to confirm Obsidian is reachable. If this fails (Obsidian not running or CLI not available), fall back to direct file reads with the Read tool and note the fallback in your output.

All vault reads in this workflow MUST use `obsidian read` / `obsidian search` commands, not direct file reads. Only fall back to direct reads if the CLI test above fails.

For writing notes, invoke the `obsidian:obsidian-markdown` skill to ensure proper frontmatter, wikilinks, and callouts.
</prerequisites>

<steps>
<step_1>
<title>Analyze Branch Changes</title>
<description>Understand what code changed on this branch to determine which vault areas need attention.</description>
<actions>
<action>Run `git log --oneline {base_branch}..HEAD` — list all commits on this branch</action>
<action>Run `git diff --stat {base_branch}..HEAD` — see which files changed and how much</action>
<action>Run `git diff --name-only {base_branch}..HEAD` — get clean list of changed files</action>
<action>Categorize changes by area: models, strategies, research, operations, scripts, source code, external repos</action>
</actions>
</step_1>

<step_2>
<title>Map Changes to Vault Areas</title>
<description>Each code area maps to specific vault documentation. Use this mapping to identify which vault notes need review.</description>
<mapping>
| Code Change Area | Vault Documentation Area |
|-----------------|-------------------------|
| `{source_path}/models/`, model configs | `{project_docs_path}/Models/` |
| `agents/`, agent handlers | `{project_docs_path}/00-Project-Overview.md` |
| `orchestrator/packages/core/src/`, invocation layer | `{project_docs_path}/00-Project-Overview.md` |
| `{source_path}/llm/`, LLM providers | `{project_docs_path}/00-Project-Overview.md` |
| Strategy configs, strategy code | `{project_docs_path}/Strategies/` |
| Research scripts, analysis code | `{project_docs_path}/Research/` |
| Deploy scripts, service configs, `systemd/` | `{project_docs_path}/Operations/` |
| `configs/agents.yaml`, `configs/teams.yaml` | `{project_docs_path}/Operations/` |
| External repo changes | `{project_docs_path}/00-Project-Overview.md` |
| `external-repo/tinyagi/` | `{project_docs_path}/00-Project-Overview.md`, `{project_docs_path}/Operations/Playbook-Guide.md` |
| CLAUDE.md changes | `{project_docs_path}/00-Project-Overview.md` |
| TaskNotes-related work | `TaskNotes/Tasks/` |
</mapping>
<action>For each changed code area, use `obsidian search` and `obsidian read` to check the corresponding vault notes</action>
</step_2>

<step_3>
<title>Check Vault Notes for Staleness</title>
<description>For each vault note identified in step 2, compare its content against the actual code state using obsidian-cli.</description>
<actions>
<action>Use `obsidian read file="<note>"` for each relevant vault note</action>
<action>Compare note content against code changes on the branch</action>
<action>Check `last-updated` frontmatter — flag notes that predate the branch changes</action>
<action>Verify specific details: file paths, function names, config values, URLs</action>
<action>Use `obsidian read file="00-Project-Overview"` — does it reflect current project state?</action>
<action>Use `obsidian read file="00-Session-Logs-Index"` — are recent sessions listed?</action>
</actions>
</step_3>

<step_4>
<title>Detect Missing Documentation</title>
<description>Identify code changes that introduce something new but lack vault documentation.</description>
<actions>
<action>New models or model versions → use `obsidian search query="<model-name>"` to check if a note exists</action>
<action>New strategies or strategy changes → check `{project_docs_path}/Strategies/`</action>
<action>New operational procedures → check `{project_docs_path}/Operations/`</action>
<action>Significant research findings → check `{project_docs_path}/Research/`</action>
<action>Check TaskNotes: find relevant epics/stories, update status if work is complete</action>
</actions>
</step_4>

<step_5>
<title>Verify Vault Layout</title>
<description>Check if the actual vault structure matches the layout documented above.</description>
<actions>
<action>Run `ls vault/` and compare against the documented layout</action>
<action>Check `ls {project_docs_path}/` for new subdirectories</action>
<action>If layout has changed, update the vault_layout section in this workflow file</action>
</actions>
</step_5>

<step_6>
<title>Check Session Logs (delegate to /wiki-update)</title>
<description>Session log creation and updates are owned by `/wiki-update`. This workflow no longer drafts session logs directly — it only notes whether one is needed so the sync plan can remind the user to run `/wiki-update` after sync.</description>
<actions>
<action>Check if the work on this branch warrants a session log (substantive changes, decisions made, experiments run).</action>
<action>If yes, note in the sync plan: "Run `/wiki-update` after vault sync — it will create/update the session log using the canonical merged schema, update linked TaskNote epic/stories, and extract compiled insights in one pass."</action>
<action>Do NOT draft session log content here. `/wiki-update` owns the create-vs-continuation decision, frontmatter schema, and TaskNote epic/story updates.</action>
</actions>
</step_6>

<step_7>
<title>Present Vault Sync Plan</title>
<description>Present findings to the user for review before making changes.</description>
<action>
Show the sync plan:

```
## Vault Sync Plan

### Branch Summary
- Branch: `branch-name`
- Commits: N commits since main
- Key changes: [brief summary]

### STALE (needs update)
| # | Note | Field/Section | Current Value | Should Be |
|---|------|--------------|---------------|-----------|

### MISSING (needs creation)
| # | Note Path | Template | Reason |
|---|-----------|----------|--------|

### TASKNOTES
| # | Task | Current Status | Suggested Status | Reason |
|---|------|---------------|-----------------|--------|

### SESSION LOG (delegated to /wiki-update)
| # | Needed | Reason |
|---|--------|--------|
<!-- If any row: remind user to run `/wiki-update` after this sync — it owns session log creation and TaskNote updates. Do not draft content here. -->

### LAYOUT CHANGES
| # | Change | Details |
|---|--------|---------|

### UP TO DATE (no action needed)
| # | Note | Last Verified |
|---|------|---------------|

### NOTEBOOKLM SYNC (final step)
After vault changes are applied, sync to NotebookLM via `/notebooklm-vault` skill.
```
</action>
</step_7>

<step_8>
<title>Execute Vault Sync</title>
<description>Apply changes using obsidian-markdown skill conventions.</description>
<actions>
<action>Invoke `obsidian:obsidian-markdown` skill before any vault writes</action>
<action>For STALE notes: Read → Edit stale fields → update `last-updated` frontmatter</action>
<action>For MISSING notes: Read matching template from `_Templates/` → populate with current data → write to correct path</action>
<action>For TASKNOTES: Update task status and add relevant notes</action>
<action>For SESSION LOGS: Do NOT draft a session log here. After this workflow finishes, run `/wiki-update` — it owns session log create/update, TaskNote epic/story sync, and compiled insight extraction.</action>
<action>For LAYOUT CHANGES: Update the vault_layout section in this workflow file</action>
<action>Add wikilinks from parent MOC notes to any newly created notes</action>
<action>Preserve existing wikilinks, callouts, and structure — only update drifted content</action>
</actions>
</step_8>

<step_9>
<title>Post-Sync Verification</title>
<actions>
<action>Use `obsidian read` to re-read modified notes and verify content is correct</action>
<action>Verify wikilinks in modified notes point to existing files</action>
<action>Confirm `last-updated` was set to today's date on all modified notes</action>
</actions>
</step_9>

<step_10>
<title>Vault Maintenance</title>
<description>After any vault changes, regenerate index and validate.</description>
<actions>
<action>Regenerate index: `cd {vault_path} && python3 _meta/generate-index.py`</action>
<action>Validate tags against `_meta/taxonomy.md`</action>
<action>Check for broken wikilinks (quick lint pass)</action>
<action>Commit vault changes: `cd {vault_path} && git add -A && git commit -m "chore: vault maintenance sync"`</action>
</actions>
</step_10>

<step_11>
<title>NotebookLM Sync</title>
<description>Sync vault changes to NotebookLM via the scheduled sync service.</description>
<actions>
<action>Inform the user: vault changes will be reflected in NotebookLM via the scheduled sync service</action>
<action>If immediate sync is needed, the user can run the sync script configured for this vault</action>
</actions>
</step_11>
</steps>

<success_criteria>
<criterion>Branch changes analyzed and mapped to vault documentation areas</criterion>
<criterion>Vault reads/searches performed via obsidian-cli (not direct file reads)</criterion>
<criterion>Stale vault notes identified and updated to reflect code changes</criterion>
<criterion>Missing documentation identified and created with proper templates</criterion>
<criterion>TaskNotes checked and updated if relevant</criterion>
<criterion>Session log status verified</criterion>
<criterion>Vault layout verified and updated if changed</criterion>
<criterion>All vault writes use obsidian-markdown conventions</criterion>
<criterion>Vault changes committed and pushed — scheduled sync will update NotebookLM</criterion>
</success_criteria>
</workflow>
