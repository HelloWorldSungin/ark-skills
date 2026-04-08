---
title: "Ecosystem Architecture Map"
type: compiled-insight
tags:
  - compiled-insight
  - infrastructure
  - plugin
summary: "The Ark ecosystem connects 7 repos via shared skills plugin, Obsidian vaults synced to NotebookLM, Linear via linear-updater, and Proxmox homelab infrastructure."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Ecosystem Architecture Map

## Summary

The Ark ecosystem spans two active AI/ML projects (ArkNode-AI and ArkNode-Poly), each with their own Obsidian vault, NotebookLM sync, and Linear project. The ark-skills repo provides shared tooling as a Claude Code plugin. The original 7 submodules have been removed in favor of independent repo management. Understanding this topology is essential for any cross-project work.

## Key Insights

### Two Active Projects, One Shared Tooling Layer

| Project | Domain | Task Prefix | Key Characteristics |
|---------|--------|------------|---------------------|
| **ArkNode-AI / trading-signal-ai** | ML trading signals (XGBoost/Platt calibration) | `ArkSignal-` | 321-file vault, 103 session logs, Proxmox homelab (CT100/CT110/CT120) |
| **ArkNode-Poly** | AI-powered prediction market trading (Polymarket) | `ArkPoly-` | 181-file vault, 24 session logs, multi-agent orchestration pipeline |

### Related Repositories (formerly submodules, now independent)

| Repo | Purpose |
|------|---------|
| ArkNode-AI | ML infra homelab, trading-signal-ai at `projects/trading-signal-ai/` |
| ArkNode-Poly | Polymarket prediction market trading |
| Arknode-AI-Obsidian-Vault | 321-file vault, task prefix `ArkSignal-` (standalone at `~/.superset/vaults/ArkNode-AI/`) |
| Arknode-Poly-Obsidian-Vault | 181-file vault, task prefix `ArkPoly-` (standalone at `~/.superset/vaults/ArkNode-Poly/`) |
| linear-updater | Polls vaults, syncs TaskNotes to Linear (5-min interval) |
| tasknotes | Obsidian plugin with MCP server at `/mcp` endpoint |
| obsidian-wiki | 13 skills for vault maintenance (Karpathy llm-wiki pattern) — upstream reference only |

### Obsidian Plugin Config Pattern

- **Plugin binaries** (`main.js`, `styles.css`, `manifest.json`) are committed to git so new clones get working plugins immediately
- **`data.json` files** are gitignored because they contain credentials (e.g., LiveSync) and project-specific paths
- **`core-plugins.json`** is tracked — controls which built-in Obsidian plugins are enabled
- **NotebookLM split**: `config.json` (notebook ID, persona) is tracked; `sync-state.json` (runtime state) is gitignored

### Integration Data Flow

```
Claude Code + ark-skills plugin
    ↓ (MCP or direct write)
Obsidian vault (TaskNotes/*.md)
    ↓ (5-min poll)
linear-updater → Linear
    ↓ (sync)
NotebookLM (indexed vault content)
```

### Infrastructure (ArkNode-AI)

| Container | Role | IP |
|-----------|------|----|
| CT100 | Production | 192.168.68.84 |
| CT110 | Research (4x RTX 5060 Ti) | 192.168.68.110 |
| CT120 | PostgreSQL | 192.168.68.120 |

### Known Scaling Limitation

`linear-updater/src/config.ts` is hardcoded for exactly 2 vaults (`VAULT_AI_PATH` and `VAULT_POLY_PATH`). Adding a third project requires refactoring `loadConfig()` to read a dynamic vault list. This is documented in the design spec Phase 5.

### Config Locations

- **NotebookLM config**: Each project repo's `.notebooklm/config.json` (tracked, authoritative)
- **Vault symlinks**: `vault/` → `~/.superset/vaults/{Project}/`
- **Sub-project CLAUDE.md**: Declares task prefix, vault path, project config (follow from hub CLAUDE.md)
- **NotebookLM notebook IDs**: AI trading: `01d771dd-5b99-4212-b99f-6b2e2abcdbe3`, AI infra: `8377f401-4be5-40f6-a8c8-1711ad946db5`

## Evidence

- Memory: `reference_ecosystem.md`, `user_profile.md`
- Design spec §5: New project onboarding requirements
- Design spec §3: TaskNotes MCP architecture and per-project routing

## Implications

- Any cross-project tool must handle per-project config via context-discovery, not hardcoded constants.
- Adding new projects requires: CLAUDE.md config, plugin install, MCP setup, and linear-updater refactor (for the 3rd+ project).
- SSH access to HelloWorldSungin GitHub org and CT110 are prerequisites for full ecosystem access.
- The 5-minute linear-updater poll cycle means task changes are not immediately reflected in Linear.
