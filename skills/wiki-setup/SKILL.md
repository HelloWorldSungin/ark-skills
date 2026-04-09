---
name: wiki-setup
description: Initialize a new Ark project vault with standard structure and artifacts
---

# Wiki Setup

Initialize a new Obsidian vault for an Ark project with the standard folder structure, templates, metadata, and tooling.

## Prerequisites

- A git repo for the new vault
- A project name and task prefix (e.g., `ArkNewProject-`)
- An existing Ark vault to copy Obsidian plugin binaries from (optional — if not available, user installs plugins manually from Obsidian)

## Workflow

### Step 1: Get Project Info

Ask the user for:
- **Project name** — e.g., `my-new-project`
- **Task prefix** — e.g., `ArkNew-`
- **Vault path** — where to create the vault (default: current directory)

### Step 2: Create Directory Structure

```bash
mkdir -p {vault_path}/{_Templates,_Attachments,_meta,.obsidian/plugins/{tasknotes,obsidian-git},TaskNotes/{Tasks/{Epic,Story,Bug,Task},Archive/{Epic,Story,Bug,Enhancement},Templates,Views,meta}}
```

### Step 3: Create 00-Home.md

Write `{vault_path}/00-Home.md`:
```yaml
---
title: "{Project Name} Knowledge Base"
type: moc
tags:
  - home
  - dashboard
summary: "Navigation hub for {Project Name}: links to project areas and key resources."
created: {today}
last-updated: {today}
---
```

With navigation links to key sections.

### Step 4: Create Templates

Create these templates in `{vault_path}/_Templates/`:
- `Session-Template.md` — session log with `prev:`, `epic:`, `session:` frontmatter
- `Compiled-Insight-Template.md` — for synthesized knowledge with `source-sessions:`, `source-tasks:`
- `Bug-Template.md` — bug report with `task-id:`, `status:`, `priority:`, `component:`
- `Task-Template.md` — generic task
- `Research-Template.md` — research findings
- `Service-Template.md` — service/infrastructure documentation

Use the templates from existing Ark vaults as reference for exact format.

### Step 5: Create Metadata Files

**`_meta/vault-schema.md`:**
Document the vault's folder structure, frontmatter conventions, and navigation patterns. Model after the existing vault schemas.

**`_meta/taxonomy.md`:**
Initialize with structural tags (`session-log`, `task`, `compiled-insight`, `home`, `moc`) and project-specific domain tags. Leave room for organic growth.

**`_meta/generate-index.py`:**
Copy from an existing vault:
```bash
cp {reference_vault}/_meta/generate-index.py {vault_path}/_meta/generate-index.py
```

### Step 6: Create Task Counter

Write `{vault_path}/TaskNotes/meta/{task_prefix}counter` with content `1`.

### Step 7: Create Project Management Guide

Write `{vault_path}/TaskNotes/00-Project-Management-Guide.md` documenting:
- Task ID format: `{task_prefix}NNN`
- Counter file location
- Status values: backlog, todo, in-progress, done
- Task types: epic, story, bug, task

### Step 8: Set Up Obsidian Configuration

Create `{vault_path}/.gitignore`:
```
# Obsidian — ignore transient state, track plugins and core config
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/graph.json
.obsidian/themes/

# Plugin data.json files may contain credentials — gitignore them
.obsidian/plugins/*/data.json
```

Create `{vault_path}/.obsidian/app.json`:
```json
{ "alwaysUpdateLinks": true }
```

Create `{vault_path}/.obsidian/appearance.json`:
```json
{}
```

Create `{vault_path}/.obsidian/community-plugins.json`:
```json
["tasknotes", "obsidian-git"]
```

Create `{vault_path}/.obsidian/core-plugins.json` — copy from an existing Ark vault to match standard core plugin settings.

### Step 9: Install TaskNotes and Obsidian Git Plugins

Ask the user if they have an existing Ark vault to copy plugin binaries from.

**If a reference vault is available**, copy the plugin files (NOT `data.json` — that's gitignored and project-specific):

```bash
# TaskNotes plugin
cp {reference_vault}/.obsidian/plugins/tasknotes/main.js {vault_path}/.obsidian/plugins/tasknotes/
cp {reference_vault}/.obsidian/plugins/tasknotes/manifest.json {vault_path}/.obsidian/plugins/tasknotes/
cp {reference_vault}/.obsidian/plugins/tasknotes/styles.css {vault_path}/.obsidian/plugins/tasknotes/

# Obsidian Git plugin
cp {reference_vault}/.obsidian/plugins/obsidian-git/main.js {vault_path}/.obsidian/plugins/obsidian-git/
cp {reference_vault}/.obsidian/plugins/obsidian-git/manifest.json {vault_path}/.obsidian/plugins/obsidian-git/
cp {reference_vault}/.obsidian/plugins/obsidian-git/styles.css {vault_path}/.obsidian/plugins/obsidian-git/
cp {reference_vault}/.obsidian/plugins/obsidian-git/obsidian_askpass.sh {vault_path}/.obsidian/plugins/obsidian-git/
```

**If no reference vault is available**, tell the user to install both plugins manually from Obsidian's Community Plugins browser after opening the vault.

Then generate the TaskNotes `data.json` with project-specific paths. The key fields to set:
- `tasksFolder`: `"TaskNotes/Tasks"`
- `archiveFolder`: `"TaskNotes/Archive"`
- `taskTag`: `"task"`
- `enableAPI`: `true` — starts the HTTP API server for external integrations
- `apiPort`: `8080` — use a unique port per vault if running multiple Obsidian instances (e.g., 8080, 8081, 8082)
- `enableMCP`: `true` — exposes TaskNotes tools via MCP at `/mcp` endpoint (requires `enableAPI`)
- `commandFileMapping`: point all views to `TaskNotes/Views/`

Copy the full `data.json` structure from an existing vault and adjust folder paths. The `data.json` is gitignored so it stays local to each developer's machine.

**Reference vault for copying:** `~/.superset/vaults/ArkNode-AI` has a known-good config with API + MCP enabled on port 8088.

### Step 10: Create NotebookLM Config

Create `{vault_path}/.notebooklm/config.json` with a template config:

```json
{
  "notebooks": {
    "main": { "id": "", "title": "{Project Name}" }
  },
  "persona": "You are a senior engineer reviewing the {project_name} project. Answer questions with specific references. Be thorough and precise.",
  "mode": "detailed",
  "response_length": "longer",
  "vault_root": "."
}
```

The `notebooks.main.id` is left empty — the user fills it in after creating a notebook in NotebookLM. The `persona` should be customized to describe the project's domain.

Add `.notebooklm/sync-state.json` to `{vault_path}/.gitignore` — it's runtime state generated by the sync process and should not be tracked.

### Step 11: Generate Initial Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

### Step 12: Initialize Git and Commit

```bash
cd {vault_path}
git init
git add -A
git commit -m "feat: initialize {project_name} vault with Ark structure"
```

### Step 13: Remind User

Tell the user:
1. Add vault to the project's CLAUDE.md (vault path, task prefix, TaskNotes path) — see `docs/onboarding-guide.md` for template
2. Configure tasknotes MCP in `.claude/settings.json`
3. Open the vault in Obsidian and enable the TaskNotes and Obsidian Git plugins
4. Add vault to linear-updater config (requires code change if third+ vault)
5. Fill in the NotebookLM notebook ID in `.notebooklm/config.json` after creating the notebook
6. Run `/notebooklm-vault setup` to bootstrap the notebook with vault content
