# New Project Onboarding Guide

How to add a new project to the Ark ecosystem with shared skills, vault, and Linear sync.

## Prerequisites

- SSH key with access to the HelloWorldSungin GitHub org
- SSH key on CT110 for vault sync and linear-updater deployment
- Linear API key for the target team
- Google NotebookLM access (for notebook sync)
- Obsidian installed with tasknotes plugin

## Overview

Adding a new project requires four things:

1. **Vault** — An Obsidian vault with Ark standard structure
2. **CLAUDE.md** — Project config that skills read via context-discovery
3. **Plugin** — ark-skills installed so all 14 shared skills are available
4. **Integrations** — TaskNotes MCP, Linear sync, NotebookLM (optional)

## Step 1: Install the Plugin

Add `ark-skills` as a Claude Code plugin. All 14 shared skills become available.

```bash
# Add the marketplace
/plugin marketplace add HelloWorldSungin/ark-skills

# Install the plugin (user-scoped — available in all projects)
/plugin install ark-skills@ark-skills

# Verify skills are available
/wiki-status
```

## Step 2: Create the Vault

Run the `/wiki-setup` skill from this plugin. It will prompt you for:

- **Project name** — e.g., `my-new-project`
- **Task prefix** — e.g., `MyProject-` (always include trailing dash)
- **Vault path** — where to create the vault (default: `./vault/` in your project repo)

The skill also asks if you have an existing Ark vault to copy plugin binaries from. If so, it copies the TaskNotes and Obsidian Git plugins. If not, you'll install them manually from Obsidian's Community Plugins browser after opening the vault.

The skill creates:

```
vault/
├── .gitignore                  # Ignores workspace.json, plugin data.json, sync-state.json
├── .notebooklm/                # NotebookLM sync configuration
│   └── config.json             # Notebook ID, persona, mode (tracked; fill in ID after creating notebook)
├── .obsidian/                  # Obsidian configuration (tracked in git)
│   ├── app.json
│   ├── appearance.json
│   ├── community-plugins.json  # Enables tasknotes + obsidian-git
│   ├── core-plugins.json
│   └── plugins/
│       ├── tasknotes/          # TaskNotes plugin (main.js, manifest.json, styles.css)
│       └── obsidian-git/       # Obsidian Git plugin
├── 00-Home.md                  # Navigation hub (MOC)
├── index.md                    # Machine-generated catalog
├── _Templates/                 # 6 page templates
│   ├── Session-Template.md
│   ├── Compiled-Insight-Template.md
│   ├── Bug-Template.md
│   ├── Task-Template.md
│   ├── Research-Template.md
│   └── Service-Template.md
├── _Attachments/               # Images, files
├── _meta/                      # Vault metadata and tooling
│   ├── vault-schema.md         # Self-documenting structure
│   ├── taxonomy.md             # Canonical tag vocabulary
│   └── generate-index.py       # Index regeneration script
└── TaskNotes/                  # Task tracking
    ├── 00-Project-Management-Guide.md
    ├── Tasks/{Epic,Story,Bug,Task}/
    ├── Archive/{Epic,Story,Bug,Enhancement}/
    ├── Templates/
    ├── Views/
    └── meta/
        └── {TaskPrefix}counter # Next task ID (starts at 1)
```

### Vault layout variants

**Standalone project** — vault lives inside the project repo:

```
my-project/
├── CLAUDE.md
├── src/
└── vault/           # vault root = vault/
    ├── 00-Home.md
    ├── TaskNotes/
    └── ...
```

**Separate vault repo** — vault is its own Git repo, symlinked or referenced:

```
my-project/
├── CLAUDE.md
└── vault/                    # vault root
    ├── My-Project/           # project docs path (symlink or subdir)
    │   ├── Session-Logs/
    │   └── Research/
    └── TaskNotes/            # sibling of project docs, NOT nested
```

**Monorepo hub** — parent repo with a Projects table linking to sub-project CLAUDEs:

```
monorepo/
├── CLAUDE.md                 # contains Projects table
├── project-a/
│   └── CLAUDE.md             # project-specific config
├── project-b/
│   └── CLAUDE.md
└── vault/                    # shared vault root
    ├── Project-A/
    ├── Project-B/
    └── TaskNotes/
```

### Obsidian plugins included

The vault setup installs two community plugins:

| Plugin | Purpose | Source |
|--------|---------|--------|
| **TaskNotes** | Note-based task management with calendar, pomodoro, time-tracking | [callumalpass/tasknotes](https://github.com/callumalpass/tasknotes) |
| **Obsidian Git** | Automatic vault backup and sync via git | [Vinzent03/obsidian-git](https://github.com/Vinzent03/obsidian-git) |

Plugin binaries (`main.js`, `manifest.json`, `styles.css`) are tracked in git. Plugin settings (`data.json`) are **gitignored** because they may contain credentials and are machine-specific.

After opening the vault in Obsidian for the first time:
1. Go to Settings > Community Plugins
2. Verify both plugins appear and are enabled
3. Configure TaskNotes: set `tasksFolder` to `TaskNotes/Tasks` and `archiveFolder` to `TaskNotes/Archive` (the `/wiki-setup` skill generates a `data.json` with these defaults)
4. Configure Obsidian Git: set your preferred backup interval

### Updating plugins

When a plugin releases a new version, update it in any one vault via Obsidian's UI, then copy the updated `main.js`, `manifest.json`, and `styles.css` to other vaults. Or let Obsidian auto-update each vault independently.

## Step 3: Configure CLAUDE.md

This is the most critical step. Every skill uses **context-discovery** to read your project's CLAUDE.md at runtime. Without the right fields, skills will fail.

### Required fields

The context-discovery pattern extracts these fields from your CLAUDE.md:

| Field | Where Skills Look | Required? |
|-------|-------------------|-----------|
| Project name | Header or "Project Configuration" table | Yes |
| Obsidian Vault path | "Obsidian Vault" row in config table | Yes |
| Task prefix | "Task Management" row — includes trailing dash | Yes |
| TaskNotes path | "Task Management" row | Yes |
| Session Logs path | "Session Logs" row | Recommended |
| Deployment targets | Infrastructure table | Optional |
| NotebookLM config | `.notebooklm/config.json` in project repo | Optional |

### Derived fields (skills compute these automatically)

| Field | Derivation |
|-------|------------|
| Vault root | Parent of project docs and TaskNotes |
| Counter file | `{tasknotes_path}/meta/{task_prefix}counter` |

### Full CLAUDE.md template

Copy this template and fill in the bracketed values:

```markdown
# {Project Name}

{Brief description of the project.}

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/` |
| **Session Logs** | `vault/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `{TaskPrefix}-`, project: `{project-name}` |

## Development

{Project-specific development instructions, build commands, test commands, etc.}

## Infrastructure

| Host | Role |
|------|------|
| {host} | {role} |

{Only include this section if you have deployment targets.}
```

### Standalone project example (minimal)

```markdown
# My Side Project

Personal experiment with LLM-powered code generation.

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/` |
| **Session Logs** | `vault/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `MySide-`, project: `my-side-project` |
```

### Full project example (with infrastructure and NotebookLM)

```markdown
# Trading Signal AI

ML-powered trading signal generation and backtesting platform.

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/Trading-Signal-AI/` |
| **Session Logs** | `vault/Trading-Signal-AI/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `ArkSignal-`, project: `trading-signal-ai` |

## Development

- **Language:** Python 3.11+ with Poetry
- **Test:** `poetry run pytest`
- **Lint:** `poetry run ruff check .`
- **Type check:** `poetry run mypy .`

## Infrastructure

| Host | Role |
|------|------|
| CT100 | Production — signal generation |
| CT110 | Vault sync, linear-updater, NotebookLM sync |
| CT120 | Staging — backtesting |
```

### Monorepo hub example

The parent repo's CLAUDE.md has a Projects table. Each sub-project has its own CLAUDE.md.

**Parent CLAUDE.md:**

```markdown
# ArkNode Monorepo

## Projects

| Project | CLAUDE.md | Vault |
|---------|-----------|-------|
| Trading Signal AI | `trading-signal-ai/CLAUDE.md` | `vault/Trading-Signal-AI/` |
| Polymarket | `arknode-poly/CLAUDE.md` | `vault/ArkNode-Poly/` |
```

**Sub-project CLAUDE.md (`trading-signal-ai/CLAUDE.md`):**

```markdown
# Trading Signal AI

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `../vault/Trading-Signal-AI/` |
| **Session Logs** | `../vault/Trading-Signal-AI/Session-Logs/` |
| **Task Management** | `../vault/TaskNotes/` — prefix: `ArkSignal-`, project: `trading-signal-ai` |
```

### Key conventions

- **Task prefix always includes trailing dash** — e.g., `ArkSignal-`, not `ArkSignal`
- **Counter filename** is `{task_prefix}counter` — e.g., `ArkSignal-counter` (no double dash)
- **TaskNotes is a sibling of project docs**, never nested under them
- Use `type:` not `category:` in frontmatter
- Use `source-sessions:` and `source-tasks:` not `sources:`
- Do NOT use `provenance:` markers

## Step 4: Configure TaskNotes MCP

TaskNotes MCP lets skills create task tickets directly from Claude Code.

### In Obsidian

1. Install the tasknotes plugin
2. Enable `enableAPI: true` in tasknotes plugin settings
3. Enable `enableMCP: true`
4. Set `apiPort` (default 8080; use a unique port if running multiple vaults)

### In your project's `.claude/settings.json`

```json
{
  "mcpServers": {
    "tasknotes": {
      "type": "url",
      "url": "http://localhost:{port}/mcp"
    }
  }
}
```

### Without Obsidian

If Obsidian isn't running, `/ark-tasknotes` falls back to writing task markdown files directly to `TaskNotes/Tasks/`. The MCP integration is optional but recommended for richer task creation.

## Step 5: Add Vault to linear-updater

The linear-updater syncs TaskNotes to Linear automatically.

1. Add your vault to the `VAULTS` env var on CT110:
   ```
   VAULTS=ai:/path/ai,poly:/path/poly,newproject:/path/new
   ```
2. Restart linear-updater on CT110
3. Verify sync: create a test task, wait 5 minutes, check Linear

## Step 6: Set Up NotebookLM Sync (Optional)

NotebookLM provides persistent cross-session memory for vault knowledge. The `/wiki-setup` skill already creates a template `.notebooklm/config.json` in the vault with placeholder values.

### Config structure

```json
{
  "notebooks": {
    "main": { "id": "", "title": "Your Project Name" }
  },
  "persona": "You are a senior engineer reviewing the {project} project. Answer questions with specific references. Be thorough and precise.",
  "mode": "detailed",
  "response_length": "longer",
  "vault_root": "."
}
```

| Field | Description | Created by setup? |
|-------|-------------|-------------------|
| `notebooks.main.id` | NotebookLM notebook ID | No — fill in after creating notebook |
| `notebooks.main.title` | Display name | Yes |
| `persona` | System prompt for NotebookLM responses | Yes (generic — customize for your domain) |
| `mode` | Response detail level (`detailed` or `concise`) | Yes |
| `response_length` | Response length (`longer` or `shorter`) | Yes |
| `vault_root` | Root path for vault file resolution | Yes (`.` = vault directory) |

The `sync-state.json` file is auto-generated at runtime by the sync process and is gitignored.

### To activate

1. Create a notebook in [NotebookLM](https://notebooklm.google.com/)
2. Copy its ID from the URL and paste into `config.json` → `notebooks.main.id`
3. Customize the `persona` field for your project's domain
4. Run `/notebooklm-vault setup` to bootstrap the notebook with vault content
5. Add sync timer on CT110 (copy existing timer, update paths)

## Step 7: Verify Everything

### Run baseline lint

```bash
# From your project directory (with vault set up)
/wiki-lint
```

This checks for broken links, missing frontmatter, stale index, and tag violations.

### Manual checklist

- [ ] Vault created with standard structure (`/wiki-setup`)
- [ ] CLAUDE.md has all required fields (vault path, task prefix, TaskNotes path)
- [ ] Plugin installed, all skills available (`/wiki-status`)
- [ ] Task counter file exists and contains `1`
- [ ] `index.md` generated (`python3 vault/_meta/generate-index.py`)
- [ ] `/wiki-lint` passes clean
- [ ] TaskNotes MCP reachable (if using Obsidian)
- [ ] linear-updater picks up vault changes (if using Linear)
- [ ] NotebookLM sync running (if using NotebookLM)

## Troubleshooting

### "CLAUDE.md is missing [field]"

A skill couldn't find a required field. Check that your CLAUDE.md has the "Project Configuration" table with all required rows. Field names must match exactly — `**Obsidian Vault**`, `**Task Management**`, etc.

### Skills don't see the vault

Verify the vault path in CLAUDE.md is relative to the project root and the directory actually exists. Run `ls vault/` to confirm.

### Task counter not incrementing

Check that `vault/TaskNotes/meta/{TaskPrefix}counter` exists and contains a single integer. The file must end with a newline.

### Index generation fails

Run from the vault root: `cd vault && python3 _meta/generate-index.py`. Check that Python 3.10+ is available. The script only scans `.md` files outside of `_Templates/`, `_Attachments/`, and `_meta/`.
