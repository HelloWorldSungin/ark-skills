# New Project Onboarding Guide

How to add a new project to the Ark ecosystem with shared skills, vault, and Linear sync.

## Prerequisites

- SSH key with access to the HelloWorldSungin GitHub org
- SSH key on CT110 for vault sync and linear-updater deployment
- Linear API key for the target team
- Google NotebookLM access (for notebook sync)
- Obsidian installed with tasknotes plugin

## Step 1: Create Obsidian Vault

Run the `/wiki-setup` skill from this plugin. It will:
1. Create the standard Ark vault structure
2. Initialize TaskNotes with your task prefix
3. Create metadata files (_meta/vault-schema.md, taxonomy.md, generate-index.py)
4. Generate initial index.md

## Step 2: Install This Plugin

Add `create-ark-skills` as a Claude Code plugin. All 14 shared skills become available.

```bash
# In Claude Code settings, add this repo as a plugin
```

## Step 3: Configure Project CLAUDE.md

Add these fields to your project's CLAUDE.md:

```markdown
| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/{Project-Name}/` (symlink to vault repo) |
| **Session Logs** | `vault/{Project-Name}/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `{YourPrefix}-`, project: `{project-name}` |
```

## Step 4: Configure TaskNotes MCP

In Obsidian:
1. Enable `enableAPI: true` in tasknotes plugin settings
2. Enable `enableMCP: true`
3. Set `apiPort` (default 8080; use a unique port if running multiple vaults)

In your project's `.claude/settings.json`:
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

## Step 5: Add Vault to linear-updater

The linear-updater supports dynamic vault configuration via the `VAULTS` env var:
1. Add your vault to the `VAULTS` env var: `VAULTS=ai:/path/ai,poly:/path/poly,newproject:/path/new`
2. Restart linear-updater on CT110
3. Verify sync: create a test task, wait 5 minutes, check Linear

## Step 6: Set Up NotebookLM Sync

1. Create `.notebooklm/config.json` in your project repo:
```json
{
  "notebooks": {
    "main": {
      "name": "Your Notebook Name",
      "id": "notebook-id-from-notebooklm"
    }
  },
  "persona": "expert",
  "mode": "detailed",
  "response_length": "longer"
}
```

2. Add sync timer on CT110 (copy existing timer, update paths)

## Step 7: Run Baseline Lint

Invoke `/wiki-lint` to verify vault structure is healthy.

## Verification Checklist

- [ ] Vault created with standard structure
- [ ] Plugin installed, skills available
- [ ] CLAUDE.md has vault path, task prefix, TaskNotes path
- [ ] TaskNotes MCP reachable (run `tasknotes_health_check`)
- [ ] linear-updater picks up vault changes
- [ ] NotebookLM sync running
- [ ] wiki-lint passes clean
