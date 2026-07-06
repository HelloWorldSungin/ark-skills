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
| **Task Management** | GitHub Issues via `gh` CLI — labels: triage (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`), type (`epic`, `story`, `task`), priority (`P1`/`P2`/`P3`), components (`consultant`, `conventions`, `vault`, `onboarding`); see `docs/agents/issue-tracker.md` for the full convention (`gh issue create/view/list/edit/comment/close` crib) |

## Agent skills

### Issue tracker

GitHub Issues via the `gh` CLI (`HelloWorldSungin/ark-skills`); external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical mattpocock triage roles map 1:1 onto this repo's own label names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) — no remapping. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root, created lazily by `/domain-modeling` when needed (neither exists yet). See `docs/agents/domain.md`.

## Available Skills

### Workflow Orchestration
- `/ark-workflow` — Task triage and skill chain orchestration (entry point for all non-trivial work)
- `/ark-context-warmup` — Automatic context loader. Runs as step 0 of every /ark-workflow chain; queries NotebookLM + vault + TaskNotes for recent + relevant context. Also invokable standalone.
- `/wiki-handoff` — Write a session bridge page to `.omc/wiki/` before `/compact` or `/clear`; invoked from `/ark-workflow` Step 6.5 action branch.

### Core (generalized from existing)
- `/ark-code-review` — Multi-agent code review with fan-out architecture
- `/codebase-maintenance` — Repo cleanup, vault sync, skill health
- `/notebooklm-vault` — NotebookLM vault context and sync (bootstrap, ask, session-continue, conflict-check). End-of-session handoff lives in `/wiki-update`.

### Code-Structural Retrieval
- `/graph-map` — Install/drive graphify to map the repo into a knowledge graph, quarantine the Obsidian export in `vault/generated/graphify/`, and register a code-structural query backend. Modes: setup / update / status / query.

### Task Automation
- `/ark-tasknotes` — Agent-driven task creation and status via tasknotes MCP. Use `status` subcommand for task overview and triage recommendations.

### Onboarding
- `/ark-onboard` — Interactive setup wizard (greenfield, migration, repair). Absorbs `/wiki-setup`.
- `/ark-health` — Diagnostic check for Ark ecosystem health (22 checks, scored scorecard)
- `/ark-update` — Version-driven migration framework. Converges downstream projects to the current ark-skills target profile by replaying additive conventions and any pending destructive migrations. Distinct from `/ark-onboard` repair (failure-driven).

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
| T2 | MemPalace | Deep context, synthesis, experiential recall (MCP tools for reads; CLI for ingest) | ~2,500 |
| T3 | Obsidian-CLI (via `obsidian:obsidian-cli` skill) | Full-text search, inline mentions | ~119 + reads |
| T4 | index.md scan | Structured browse, page discovery, zero-dep fallback | ~2,100 |

### Availability Checks

- **T1:** `notebooklm` CLI authenticated + config exists at `{vault_path}/.notebooklm/config.json` OR `.notebooklm/config.json` in project root
- **T2:** MemPalace MCP server reachable (`mcp__mempalace__*` tools available) for reads; `mempalace` CLI installed for ingest (`mempalace mine`, requires **v3.3.5+**; floor-pin **>=3.3.6** for the #1457 fix — PyPI latest 3.4.1, 2026-06-15). The HNSW-corruption crash class — `_query` ([#1132](https://github.com/MemPalace/mempalace/issues/1132)) and `_upsert` ([#976](https://github.com/MemPalace/mempalace/pull/976)) — is closed in v3.3.5 via [#1322](https://github.com/MemPalace/mempalace/pull/1322) (wires `quarantine_stale_hnsw` into the chromadb client open path). v3.3.5 also ships [`mempalace repair --mode from-sqlite`](https://github.com/MemPalace/mempalace/pull/1310) for recovering already-corrupt palaces (reads `(id, document, metadata)` directly from `chroma.sqlite3` without opening chromadb against the corrupt palace). **Resolved (v3.3.6):** the zero-byte `link_lists.bin` SIGSEGV gap ([#1457](https://github.com/MemPalace/mempalace/issues/1457)) — where the v3.3.5 quarantine gate treated a 0-byte `link_lists.bin` as benign — is **fixed in v3.3.6** (PR [#1461](https://github.com/MemPalace/mempalace/pull/1461), published to PyPI 2026-06-06; release notes: "#1452, #1461, fixes #1457"). On installs **>=3.3.6** the manual segment `mv` workaround is no longer needed; it remains a fallback only for installs still pinned below 3.3.6. `mempalace status` hits SQLite's 32k-variable limit on palaces past ~32k drawers ([#802](https://github.com/MemPalace/mempalace/issues/802), open). If MCP is unreachable, skip T2 entirely.
- **T3:** Obsidian app running. Always invoke via `obsidian:obsidian-cli` skill.
- **T4:** `{vault_path}/index.md` exists. Always available.

### Failure Messaging

When a preferred tier is unavailable, log before falling back:
- "T1 not available — NotebookLM config not found at {vault_path}/.notebooklm/config.json or .notebooklm/config.json. Falling back to T4."
- "T2 not available — MemPalace MCP server unreachable. CLI search/mine require v3.3.5+ (#1132/#976 closed via #1322); #1457 zero-byte link_lists SIGSEGV fix shipped in v3.3.6 (#1461; PyPI 2026-06-06) — manual segment `mv` repair only needed on installs pinned below 3.3.6 (floor-pin >=3.3.6; latest 3.4.1). Skipping T2. Falling back to T3/T4."
- "T2 wing missing — MemPalace wing '{wing}' not indexed. Run `bash skills/shared/mine-vault.sh` via MCP (CLI mine still works). Falling back to T4."
- "T3 not available — Obsidian not responsive. Falling back to T4."

### Query Routing

- "What is X?" / "What did we decide?" → T1 → T4
- "Why did we decide X?" / "Show the reasoning" → T2 → T4
- "What did we try when debugging X?" → T2
- "How does X relate to Y?" → T2 → T4
- "What don't we know about X?" → T2 → T1 → T4
- "Find all mentions of X" → T3 → T4
- "What pages exist about X?" → T4

### Code-Structural Retrieval

For code-structure questions, use the graphify graph (availability: `graphify-out/graph.json` exists):
- "What calls X / what does X depend on?" → **Graph** (`graphify query`) → `rg`/LSP/source
- "Show the structure/flow of X" → **Graph** → source
- "Why was X built this way?" → **T2** (MemPalace), not the graph

Failure: "Code-structural graph not available — run /graph-map setup. Falling back to rg/LSP/source."

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
