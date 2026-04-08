---
name: wiki-setup
description: Initialize a new Ark project vault with standard structure and artifacts
---

# Wiki Setup

Initialize a new Obsidian vault for an Ark project with the standard folder structure, templates, metadata, and tooling.

## Prerequisites

- A git repo for the new vault
- A project name and task prefix (e.g., `ArkNewProject-`)

## Workflow

### Step 1: Get Project Info

Ask the user for:
- **Project name** — e.g., `my-new-project`
- **Task prefix** — e.g., `ArkNew-`
- **Vault path** — where to create the vault (default: current directory)

### Step 2: Create Directory Structure

```bash
mkdir -p {vault_path}/{_Templates,_Attachments,_meta,TaskNotes/{Tasks/{Epic,Story,Bug,Task},Archive/{Epic,Story,Bug,Enhancement},Templates,Views,meta}}
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

### Step 8: Generate Initial Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

### Step 9: Initialize Git and Commit

```bash
cd {vault_path}
git init
git add -A
git commit -m "feat: initialize {project_name} vault with Ark structure"
```

### Step 10: Remind User

Tell the user:
1. Add vault to the project's CLAUDE.md (vault path, task prefix, TaskNotes path)
2. Configure tasknotes MCP in `.claude/settings.json`
3. Add vault to linear-updater config (requires code change if third+ vault)
4. Set up NotebookLM sync if desired
