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

**Exemption:** `/ark-onboard` and `/ark-health` are exempt from context-discovery — they must work when CLAUDE.md is missing, broken, or incomplete.

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
| **Project docs path** | `vault/` (standalone layout — same as vault root) |
| **Session Logs** | `vault/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `Arkskill-`, project: `ark-skills` |

## Available Skills

### Workflow Orchestration
- `/ark-workflow` — Task triage and skill chain orchestration (entry point for all non-trivial work)
- `/ark-context-warmup` — Automatic context loader. Runs as step 0 of every /ark-workflow chain; queries NotebookLM + vault + TaskNotes for recent + relevant context. Also invokable standalone.

### Core (generalized from existing)
- `/ark-code-review` — Multi-agent code review with fan-out architecture
- `/codebase-maintenance` — Repo cleanup, vault sync, skill health
- `/notebooklm-vault` — NotebookLM vault context and sync (bootstrap, ask, session-continue, conflict-check). End-of-session handoff lives in `/wiki-update`.

### Task Automation
- `/ark-tasknotes` — Agent-driven task creation and status via tasknotes MCP. Use `status` subcommand for task overview and triage recommendations.

### Onboarding
- `/ark-onboard` — Interactive setup wizard (greenfield, migration, repair). Absorbs `/wiki-setup`.
- `/ark-health` — Diagnostic check for Ark ecosystem health (19 checks, scored scorecard)

### Vault Maintenance (adapted from obsidian-wiki)
- `/wiki-query` — Query vault knowledge with tiered retrieval
- `/wiki-lint` — Audit vault health (links, frontmatter, tags, index)
- `/wiki-status` — Vault statistics and insights
- `/wiki-update` — End-of-session workflow: create/update session log, update TaskNote epic/stories, extract compiled insights, regenerate index
- `/wiki-setup` — Initialize new Ark vault with standard structure
- `/wiki-ingest` — Distill documents into vault pages
- `/tag-taxonomy` — Validate and normalize tags against taxonomy
- `/cross-linker` — Discover and add missing wikilinks
- `/claude-history-ingest` — Mine Claude conversations into compiled vault insights via MemPalace (requires `pip install mempalace`)
- `/data-ingest` — Process logs, transcripts, exports into vault pages

## Vault Retrieval Defaults

Four retrieval backends, ordered by richness. Check availability in order.
Use the first available backend appropriate for the query type.

| Tier | Backend | Best For | Token Cost |
|------|---------|----------|------------|
| T1 | NotebookLM | Factual lookups, pre-synthesized answers | ~500 |
| T2 | MemPalace | Deep context, synthesis, experiential recall | ~2,500 |
| T3 | Obsidian-CLI (via `obsidian:obsidian-cli` skill) | Full-text search, inline mentions | ~119 + reads |
| T4 | index.md scan | Structured browse, page discovery, zero-dep fallback | ~2,100 |

### Availability Checks

- **T1:** `notebooklm` CLI authenticated + config exists at `{vault_path}/.notebooklm/config.json` OR `.notebooklm/config.json` in project root
- **T2:** `mempalace` installed + project-specific wing exists in `mempalace status`
- **T3:** Obsidian app running. Always invoke via `obsidian:obsidian-cli` skill.
- **T4:** `{vault_path}/index.md` exists. Always available.

### Failure Messaging

When a preferred tier is unavailable, log before falling back:
- "T1 not available — NotebookLM config not found at {vault_path}/.notebooklm/config.json or .notebooklm/config.json. Falling back to T4."
- "T2 not available — MemPalace wing '{wing}' not found. Run `bash skills/shared/mine-vault.sh` to index. Falling back to T4."
- "T3 not available — Obsidian not responsive. Falling back to T4."

### Query Routing

- "What is X?" / "What did we decide?" → T1 → T4
- "Why did we decide X?" / "Show the reasoning" → T2 → T4
- "What did we try when debugging X?" → T2
- "How does X relate to Y?" → T2 → T4
- "What don't we know about X?" → T2 → T1 → T4
- "Find all mentions of X" → T3 → T4
- "What pages exist about X?" → T4
