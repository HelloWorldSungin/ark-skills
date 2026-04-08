---
name: codebase-maintenance
description: Multi-step codebase maintenance that audits code, syncs Obsidian vault documentation, and heals Claude Code skills. This skill contains the specialized workflows, checklists, plan templates, and vault-mapping logic needed to do these tasks correctly — do not attempt them without it. MUST be consulted whenever the user mentions any of these: cleanup, maintenance, dead code, stale scripts, stale files, vault sync, vault up to date, sync vault, documentation drift, docs out of date, what needs documenting, skill drift, heal skills, sync skills, update skills, are my skills accurate, check skill paths, full pass before merge, pre-merge sweep, tidy the repo, clean up the repo, or any request to verify that code changes are properly reflected in Obsidian vault documentation or Claude Code skills. Also triggers when the user asks about documentation coverage for recent commits, wants to find orphaned files, or is preparing to merge a branch and wants everything checked. Do NOT use for: creating individual Obsidian notes (use obsidian-markdown). This skill is different from notebooklm-vault — use notebooklm-vault for reading vault history and session context, use this skill for ensuring vault docs match code changes.
---

<objective>
Three primary goals:
1. **Repo cleanup** — Find and remove dead code, stale scripts, and untracked files.
2. **Vault sync** — Ensure code changes on the current branch have matching Obsidian vault documentation. Update stale notes, create missing ones, and check TaskNotes for relevant tasks. Uses obsidian-cli for efficient vault reads/searches.
3. **Skill sync** — Check all project-level Claude Code skills for references that have drifted due to code changes on the branch. Update stale skills so they stay accurate.

## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, vault path, deployment targets (if any), code scan paths
2. If CLAUDE.md defines deployment targets, include infrastructure audit steps
3. If CLAUDE.md defines a monitoring dashboard, include dashboard sync steps

All documentation lives in the Obsidian vault (discovered from CLAUDE.md). The vault is the source of truth. Vault changes must be committed and pushed in the vault repo, not the project repo. Destructive operations (code cleanup) require user approval via planning mode. Vault sync and skill sync present plans for review but don't require plan mode.
</objective>

<quick_start>
1. User selects scope (code, vault, skills, or full)
2. Skill routes to the appropriate workflow
3. Workflow analyzes branch changes and current state
4. Plan presented for user review
5. Changes execute, followed by verification
</quick_start>

<routing>
Parse `$ARGUMENTS` to determine workflow. If no argument provided, use AskUserQuestion to let user choose.

| Argument | Workflow File | Description |
|----------|--------------|-------------|
| `code` | `workflows/cleanup-code.md` | Dead code, stale scripts, untracked files |
| `vault` | `workflows/sync-vault.md` | Sync Obsidian vault with code changes on current branch |
| `skills` | `workflows/sync-skills.md` | Update project skills that drifted due to code changes |
| `full` | `workflows/full-cleanup.md` | All categories combined — MUST complete all 3 phases |

If argument is empty or unrecognized, ask user:
```
Which maintenance scope?
- code: Dead code, stale scripts, untracked files
- vault: Sync Obsidian vault with code changes on current branch
- skills: Update project skills drifted by code changes
- full: All categories (code + vault + skills)
```

When `full` is selected: Read `workflows/full-cleanup.md` COMPLETELY before starting. The workflow requires creating a TaskCreate checklist and completing ALL phases.
</routing>

<context_gathering>
Before running any workflow, gather current project state:

1. **Branch changes** — `git log --oneline {base_branch}..HEAD` to see all commits on this branch. This is the primary input for vault sync.
2. **Branch diff** — `git diff --stat {base_branch}..HEAD` for a high-level view of what files changed
3. **Recent main history** — `git log --oneline -10 master` for overall project direction
4. **Vault state** — Scan `{project_docs_path}/` for current documentation landscape
5. **TaskNotes** — Check `vault/TaskNotes/Tasks/` for in-progress tasks related to the changes
</context_gathering>

<shared_principles>
These apply to ALL workflows:

1. **Planning mode for destructive operations** — Enter planning mode before deleting files or removing code (code cleanup). Vault sync and skill sync present plans for review but don't require plan mode.

2. **Never delete without justification** — Every file flagged for deletion must have a reason (orphaned, superseded, references removed feature).

3. **Vault is the source of truth for docs** — All documentation lives at `vault/`. Key areas:
   - `{project_docs_path}/` — Project docs (models, strategies, operations, research)
   - `{project_docs_path}/Session-Logs/` — Build journal / session history
   - `TaskNotes/` — Project management (Epic/Story/Task/Bug)

4. **Use obsidian-cli for vault reads** — Before any vault work, invoke the `obsidian:obsidian-cli` skill first and test with `obsidian read file="00-Home"`. Then use `obsidian read` and `obsidian search` for all vault reads/searches. Only fall back to direct reads if the CLI test fails. Use `obsidian:obsidian-markdown` skill conventions for all vault writes.

5. **Git untracked audit** — `git status` untracked files, categorize as: commit, .gitignore, or delete.
</shared_principles>

<cleanup_plan_format>
Present cleanup plans in this format:

```
## Cleanup Plan: {scope}

### DELETE (requires approval)
| # | File | Reason |
|---|------|--------|
| 1 | path/to/file.py | Orphaned — no callers after refactor |

### UPDATE
| # | File | Action |
|---|------|--------|
| 1 | CLAUDE.md | Update current status section |

### KEEP (no action needed)
| # | File | Reason |
|---|------|--------|
| 1 | path/to/important.py | Still referenced by research pipeline |

### Git Untracked
| # | File | Action |
|---|------|--------|
| 1 | scripts/new_script.py | Commit |
| 2 | temp_debug.py | Delete |

### Vault Sync
| # | Note | Action | Reason |
|---|------|--------|--------|
| 1 | Operations/Deployment-Guide.md | UPDATE | Config paths changed |
| 2 | Models/New-Model.md | CREATE | New model added on branch |

### Skill Sync
| # | Skill | File | Issue | Fix |
|---|-------|------|-------|-----|
| 1 | notebooklm-vault | SKILL.md | Old vault path | Update to new path |
```
</cleanup_plan_format>

<post_cleanup>
After cleanup execution completes:

1. **Run tests** — If tests exist, run them to verify nothing broke
2. **Commit changes** — Summarize what was cleaned up in the commit message
3. **Vault verification** — Re-read modified vault notes to verify frontmatter is valid YAML and wikilinks resolve
</post_cleanup>

<references>
- Cleanup checklist: `references/cleanup-checklist.md`
</references>

<success_criteria>
<criterion>Correct workflow selected based on argument or user choice</criterion>
<criterion>Planning mode activated before destructive operations (code cleanup)</criterion>
<criterion>Branch changes analyzed to identify documentation and skill gaps</criterion>
<criterion>Vault notes updated to reflect code changes on the branch</criterion>
<criterion>Project skills checked and updated for drifted references</criterion>
<criterion>Vault changes synced to NotebookLM</criterion>
<criterion>Post-cleanup: tests run if available, changes committed</criterion>
</success_criteria>
