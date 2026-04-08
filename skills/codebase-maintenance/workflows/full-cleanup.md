<workflow name="full-cleanup">
<title>Full Codebase Maintenance</title>
<description>Comprehensive maintenance: code/script cleanup, Obsidian vault sync, and skill healing. Combines all specialized workflows into one pass with mandatory progress tracking.</description>

<critical_rule>
YOU MUST COMPLETE ALL 3 PHASES. Do not skip any phase. Do not stop after gathering context or writing a session log. The whole point of "full" maintenance is that ALL categories get checked and ALL changes get made. If you only do one thing, you have failed.

The 3 phases are: (1) Code Cleanup, (2) Vault Sync, (3) Skill Sync.
A session log is NOT a substitute for vault sync. Vault sync means checking every vault note that maps to branch code changes and updating stale content.
</critical_rule>

<prerequisites>
BEFORE starting, do ALL of these (they are not optional):

1. **Create the progress checklist** — Use TaskCreate to create one task per phase below. This is mandatory because it prevents you from losing track of where you are:
   - "Phase 0: Gather project context (git log, git diff, vault survey)"
   - "Phase 1: Code and script cleanup (dead code, untracked files)"
   - "Phase 2: Vault sync (map code→vault, check staleness, update/create notes)"
   - "Phase 3: Skill sync (audit affected skills, fix drifted references)"
   - "Phase 4: Present plan and execute approved changes"
   - "Phase 5: Post-cleanup verification and NotebookLM sync"

2. **Test obsidian-cli** — Invoke the `obsidian:obsidian-cli` skill and run `obsidian read file="00-Home"`. All vault reads MUST use `obsidian read` / `obsidian search`. Only fall back to direct reads if this test fails.
</prerequisites>

<phase_0>
<title>Phase 0: Gather Project Context</title>
<description>Collect authoritative project state before scanning. Mark the Phase 0 task as in_progress, then completed when done.</description>
<actions>
<action>Run `git log --oneline {base_branch}..HEAD` to see all branch commits</action>
<action>Run `git diff --stat {base_branch}..HEAD` for a high-level view of changed files</action>
<action>Run `git diff --name-only {base_branch}..HEAD` for clean list of changed files</action>
<action>Run `git log --oneline -10 master` for recent project direction</action>
<action>Use `obsidian search` to survey current vault documentation state</action>
<action>Check `vault/TaskNotes/Tasks/` for in-progress tasks</action>
</actions>
<checkpoint>
You MUST output a "Branch Change Summary" to the user showing: branch name, number of commits, key changed files grouped by area. This summary is the input for all subsequent phases. If you skip this, the rest of the workflow has no foundation.
</checkpoint>
</phase_0>

<phase_1>
<title>Phase 1: Code and Script Cleanup</title>
<description>Mark Phase 1 task as in_progress. Execute the code cleanup workflow. Enter planning mode for destructive operations.</description>
<actions>
<action>Enter planning mode</action>
<action>Glob all scripts — list them</action>
<action>Dead code detection — find scripts and source functions with no callers</action>
<action>Git untracked audit — run `git status` and categorize as commit, .gitignore, or delete</action>
</actions>
<checkpoint>
You MUST output a "Code Cleanup Findings" section listing: dead scripts found, untracked files. Even if everything is clean, say "No issues found" explicitly. Then mark Phase 1 task as completed.
</checkpoint>
</phase_1>

<phase_2>
<title>Phase 2: Vault Sync</title>
<description>Mark Phase 2 task as in_progress. This is the most important phase — it ensures vault documentation matches code reality. A session log alone is NOT sufficient. You must check every vault note that corresponds to code changes on the branch.</description>

<what_vault_sync_means>
Vault sync is NOT just writing a session log. It means:
1. Looking at every file changed on the branch (from Phase 0)
2. Mapping each changed file to the vault note that documents it (using the mapping table below)
3. Reading each mapped vault note via `obsidian read`
4. Comparing the note's content against the actual code — checking file paths, function names, config values, architecture descriptions
5. Updating any stale content in vault notes
6. Creating new vault notes for features that have no documentation
7. Updating TaskNotes status for relevant epics/stories
8. THEN also checking if a session log is needed
</what_vault_sync_means>

<mapping>
| Code Change Area | Vault Documentation Area |
|-----------------|-------------------------|
| `{source_path}/models/`, model configs | `{project_docs_path}/Models/` |
| `agents/`, agent handlers | `{project_docs_path}/00-Project-Overview.md` |
| `orchestrator/packages/core/src/`, invocation layer | `{project_docs_path}/00-Project-Overview.md` |
| `{source_path}/llm/`, LLM providers | `{project_docs_path}/00-Project-Overview.md` |
| Strategy configs, strategy code | `{project_docs_path}/Strategies/` |
| Research scripts, analysis | `{project_docs_path}/Research/` |
| Deploy scripts, service configs, `systemd/` | `{project_docs_path}/Operations/` |
| `configs/agents.yaml`, `configs/teams.yaml` | `{project_docs_path}/Operations/` |
| External repo changes | `{project_docs_path}/00-Project-Overview.md` |
| `external-repo/tinyagi/` | `{project_docs_path}/00-Project-Overview.md`, `{project_docs_path}/Operations/Playbook-Guide.md` |
| CLAUDE.md changes | `{project_docs_path}/00-Project-Overview.md` |
| TaskNotes-related work | `TaskNotes/Tasks/` |
</mapping>

<actions>
<action>For each code change area from Phase 0, identify the corresponding vault notes using the mapping table</action>
<action>Use `obsidian read file="<note>"` for EACH relevant vault note — actually read them, don't skip</action>
<action>Compare note content against current code state — flag stale paths, configs, descriptions</action>
<action>Use `obsidian search query="<keyword>" limit=10` to find notes you might have missed</action>
<action>Check `obsidian read file="00-Project-Overview"` — does it reflect current project state?</action>
<action>Check TaskNotes: find relevant epics/stories, update status if work is complete</action>
<action>Check if a new session log is needed for branch work</action>
<action>Detect missing documentation — new features without vault notes</action>
</actions>
<checkpoint>
You MUST output a "Vault Sync Findings" section with these subsections:
- **STALE NOTES** — vault notes with outdated content (note name, what's wrong, what it should say)
- **MISSING NOTES** — new features lacking documentation
- **TASKNOTES** — task status updates needed
- **SESSION LOG** — whether a new session log is needed
- **UP TO DATE** — vault notes that were checked and are fine

If you output zero items in STALE NOTES, explain WHY — which notes did you actually read and verify? List them. Then mark Phase 2 task as completed.
</checkpoint>
</phase_2>

<phase_3>
<title>Phase 3: Skill Sync</title>
<description>Mark Phase 3 task as in_progress. Check all project-level Claude Code skills for references that drifted due to branch code changes.</description>
<actions>
<action>Map branch changes to potentially affected skills (use the mapping in sync-skills.md)</action>
<action>Read each affected skill's SKILL.md and workflow files</action>
<action>Extract concrete references: file paths, function names, URLs, config keys</action>
<action>Verify each reference still exists and is accurate in the current codebase</action>
<action>Check if new branch functionality should be mentioned in existing skills</action>
</actions>
<checkpoint>
You MUST output a "Skill Sync Findings" section listing: which skills were checked, which have stale references, and what needs fixing. Even if all skills are up to date, list which ones you verified. Then mark Phase 3 task as completed.
</checkpoint>
</phase_3>

<phase_4>
<title>Phase 4: Present Plan and Execute</title>
<description>Mark Phase 4 task as in_progress. Combine ALL findings from Phases 1-3 into one comprehensive plan, present it, then execute approved changes.</description>
<actions>
<action>Combine all findings into one plan using the standard format from SKILL.md</action>
<action>Present the full plan to the user for approval</action>
<action>After approval, execute changes:
  - Code deletions (if approved)
  - Vault updates — invoke `obsidian:obsidian-markdown` skill, then use Edit tool for vault writes
  - Skill updates — minimal targeted edits to fix drifted references
</action>
</actions>
<checkpoint>
Mark Phase 4 task as completed after executing all approved changes.
</checkpoint>
</phase_4>

<phase_5>
<title>Phase 5: Post-Cleanup Verification</title>
<description>Mark Phase 5 task as in_progress. Verify all changes, run tests, and sync to NotebookLM.</description>
<actions>
<action>Use `obsidian read` to verify modified vault notes render correctly</action>
<action>Re-read modified skills to verify edits</action>
<action>Run tests if available to verify nothing broke</action>
<action>Sync vault changes to NotebookLM:
```bash
bash .claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh
```
</action>
<action>Report final summary: what was cleaned, updated, created, and synced</action>
</actions>
<checkpoint>
Mark Phase 5 task as completed. Output a final "Maintenance Complete" summary showing what was done in each phase.
</checkpoint>
</phase_5>
</workflow>
