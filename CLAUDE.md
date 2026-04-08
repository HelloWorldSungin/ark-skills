# Ark Skills Plugin

Shared skills for all ArkNode projects. This repo is registered as a Claude Code plugin — all skills in `skills/` are user-scoped and available to every project.

## Context-Discovery Pattern

Every skill in this plugin uses **context-discovery** to find project-specific values at runtime. No skill contains hardcoded project names, vault paths, or task prefixes.

### How It Works

When a skill says "Run Project Discovery," follow this procedure:

1. Read the `CLAUDE.md` in the current working directory
2. If it's a monorepo hub (contains a "Projects" table linking to sub-project CLAUDEs), follow the link for the active project based on your current working directory
3. Extract these fields from the most specific CLAUDE.md:

| Field | Where to Find | Example |
|-------|--------------|---------|
| Project name | Header or table | `trading-signal-ai` |
| Task prefix | "Task Management" row, includes trailing dash | `ArkSignal-` |
| Vault root | Parent of project docs and TaskNotes | `vault/` |
| Project docs path | "Obsidian Vault" row — project-specific content | `vault/Trading-Signal-AI/` |
| TaskNotes path | "Task Management" row — sibling of project docs, NOT nested under it | `vault/TaskNotes/` |
| Counter file | `{tasknotes_path}/meta/{task_prefix}counter` — prefix includes dash | `vault/TaskNotes/meta/ArkSignal-counter` |
| Deployment targets | Infrastructure section | CT100, CT110, CT120 (if defined) |
| NotebookLM config | `.notebooklm/config.json` in **project repo** (tracked config) | notebook keys, persona |

**Path layout:** `vault/` is the root containing BOTH `vault/{ProjectDocs}/` and `vault/TaskNotes/` as siblings:
```
vault/                          # {vault_root}
├── Trading-Signal-AI/          # {project_docs_path} — project knowledge
│   ├── Session-Logs/
│   ├── Research/
│   └── ...
└── TaskNotes/                  # {tasknotes_path} — task tracking (sibling, NOT nested)
    ├── Tasks/
    ├── Archive/
    └── meta/ArkSignal-counter
```

**Counter file convention:** Task prefix always includes the trailing dash (e.g., `ArkSignal-`). Counter filename is `{task_prefix}counter` → `ArkSignal-counter`. No double dash.

4. If a required field is missing, tell the user: "CLAUDE.md is missing [field]. Add it before running this skill."

### Vault Artifacts (Post-Restructuring)

All Ark vaults have these standard artifacts from the vault restructuring:

| Artifact | Path | Purpose |
|----------|------|---------|
| Vault schema | `_meta/vault-schema.md` | Self-documenting vault structure |
| Tag taxonomy | `_meta/taxonomy.md` | Canonical tag vocabulary |
| Index generator | `_meta/generate-index.py` | Regenerates `index.md` |
| Machine index | `index.md` | Flat catalog of all pages with summaries |
| Summaries | `summary:` frontmatter | <=200 char description on every page |

### Ark Frontmatter Schema

Ark vaults use `type:` (not `category:`), `source-sessions:` and `source-tasks:` (not `sources:`). They do NOT use `provenance:` markers. See each vault's `_meta/vault-schema.md` for the complete frontmatter spec.

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/` |
| **Session Logs** | `vault/Session-Logs/` (when created) |
| **Task Management** | `vault/TaskNotes/` — prefix: `Arkskill-`, project: `ark-skills` |

## Available Skills

### Core (generalized from existing)
- `/ark-code-review` — Multi-agent code review with fan-out architecture
- `/codebase-maintenance` — Repo cleanup, vault sync, skill health
- `/notebooklm-vault` — NotebookLM vault context and sync

### Task Automation
- `/ark-tasknotes` — Agent-driven task creation via tasknotes MCP

### Vault Maintenance (adapted from obsidian-wiki)
- `/wiki-query` — Query vault knowledge with tiered retrieval
- `/wiki-lint` — Audit vault health (links, frontmatter, tags, index)
- `/wiki-status` — Vault statistics and insights
- `/wiki-update` — Sync project knowledge into vault, regenerate index
- `/wiki-setup` — Initialize new Ark vault with standard structure
- `/wiki-ingest` — Distill documents into vault pages
- `/tag-taxonomy` — Validate and normalize tags against taxonomy
- `/cross-linker` — Discover and add missing wikilinks
- `/claude-history-ingest` — Mine Claude conversations into compiled insights
- `/data-ingest` — Process logs, transcripts, exports into vault pages
