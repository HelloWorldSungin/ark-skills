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

ark-skills is two co-equal cores: a **workflow consultant** that plans and routes each task, and a **conventions layer** that converges projects onto shared OKF knowledge + GitHub-Issues conventions.

### Workflow consultant
- `/ark-consult` — Stateless workflow consultant; the planning phase for any non-trivial task. Triages, asks ≤2 clarifying questions, recommends exactly ONE execution ecosystem (gstack / superpowers / mattpocock / oh-my-claudecode) from a routing matrix, files a GitHub epic as the plan of record, and hands off. Replaces the retired chain-orchestration skill and its chains. The epic is the only state; resume = `gh issue view <epic>`.

### Conventions layer
- `/vault` — Write-side OKF knowledge ops for the bundle at `vault/`: end-of-session insight distillation, document ingestion, `log.md` append, index regen. Durable knowledge only — no session logs, no task tracking. Reading is script-based (`okf_cli.py`) or NotebookLM.
- `/notebooklm-vault` — Synthesized-recall backend: syncs the OKF bundle to NotebookLM and answers factual/historical queries (bootstrap, ask, session-continue, conflict-check).
- `/ark-onboard` — Interactive setup wizard: initializes the OKF bundle, bootstraps GitHub Issue labels, points at mattpocock setup, and writes CLAUDE.md rows.
- `/ark-health` — Diagnostic check for the v2 invariants (OKF lint clean, `okf_version` present, labels present, `docs/agents/` config, mattpocock configured, exactly 6 skills, no frozen-tracker writes, NotebookLM reachable).
- `/ark-update` — Version-driven migration framework: converges downstream projects onto the current target profile (OKF conversion + GitHub-Issues adoption). Execution is per-project and deferred.

## Vault Retrieval Defaults

Two read paths for the OKF bundle. Querying the vault is read-side only — no skill wraps it (write-side is `/vault`).

| Path | Backend | Best For |
|------|---------|----------|
| Synthesized recall | NotebookLM (`/notebooklm-vault`) | "What is X?", "What did we decide?", "Has this been tried?" — pre-synthesized answers over the OKF bundle |
| Navigation / full-text | `python3 vault/_meta/okf/okf_cli.py {list,search,read}` | Page discovery, full-text search, reading specific pages |

### Availability

- **NotebookLM:** `notebooklm` CLI authenticated + config at `{vault_path}/.notebooklm/config.json` or `.notebooklm/config.json` in project root. If unavailable, fall back to `okf_cli.py`.
- **okf_cli.py:** always available when the OKF bundle exists (`vault/_meta/okf/okf_cli.py`). Zero-dependency fallback.

### Query Routing

- "What is X?" / "What did we decide?" / "Has this been tried?" → NotebookLM → `okf_cli.py search`
- "Find all mentions of X" / "What pages exist about X?" → `okf_cli.py search` / `okf_cli.py list`
- Write-side (distill, ingest, update the vault) → `/vault`

Failure: "NotebookLM not available — config not found at {vault_path}/.notebooklm/config.json or .notebooklm/config.json. Falling back to okf_cli.py."

### Code-Structural Retrieval

For code-structure questions (what calls X, dependencies/impact, the shape of a flow), use the graphify graph directly — see the **graphify** section below. No ark skill wraps it.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
