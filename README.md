# Ark Skills Plugin

Claude Code plugin providing 16 shared skills to all ArkNode projects. Eliminates skill duplication across repos by centralizing skills with a context-discovery pattern that adapts to each project at runtime.

## Installation

```bash
# Add the marketplace
/plugin marketplace add HelloWorldSungin/ark-skills

# Install the plugin (user-scoped — available in all projects)
/plugin install ark-skills@ark-skills

# Verify skills are available
/wiki-status
```

### Prerequisites

**Required for all skills:** None — skills are instruction-only with no external dependencies by default.

**Optional — enhances vault retrieval (see Vault Retrieval Defaults in CLAUDE.md):**

| Dependency | Skills Enhanced | Install |
|------------|----------------|---------|
| [MemPalace](https://github.com/milla-jovovich/mempalace) | `/wiki-query` (T2), `/claude-history-ingest` | `pipx install "mempalace>=3.0.0,<4.0.0"` |
| [NotebookLM CLI](https://github.com/nichochar/notebooklm-cli) | `/wiki-query` (T1), `/notebooklm-vault` | `pipx install notebooklm-cli` + `notebooklm login` |
| [Obsidian CLI](https://help.obsidian.md/cli) | `/wiki-query` (T3), `/cross-linker` (Phase 2) | Requires Obsidian app running. Uses `obsidian:obsidian-cli` skill. |

**First-time MemPalace vault setup:**

```bash
# Index vault markdown files into MemPalace (one-time)
bash skills/shared/mine-vault.sh

# Install the conversation auto-indexing hook (per-project)
bash skills/claude-history-ingest/hooks/install-hook.sh
```

### Development Setup

```bash
# Clone with submodules (for contributing)
git clone --recurse-submodules git@github.com:HelloWorldSungin/ark-skills.git
```

## Available Skills

| Skill | Category | Description | Source |
|-------|----------|-------------|--------|
| `/ark-code-review` | Core | Multi-agent code review with fan-out architecture | Generalized |
| `/codebase-maintenance` | Core | Repo cleanup, vault sync, skill health | Generalized |
| `/notebooklm-vault` | Core | NotebookLM vault context and sync | Generalized |
| `/ark-tasknotes` | Task Automation | Agent-driven task creation via tasknotes MCP | New |
| `/wiki-query` | Vault Maintenance | Query vault knowledge with tiered retrieval | Adapted from obsidian-wiki |
| `/wiki-status` | Vault Maintenance | Vault statistics and insights | Adapted from obsidian-wiki |
| `/wiki-update` | Vault Maintenance | Sync project knowledge into vault | Adapted from obsidian-wiki |
| `/wiki-lint` | Vault Maintenance | Audit vault health (links, frontmatter, tags) | Adapted from obsidian-wiki |
| `/wiki-setup` | Vault Maintenance | Initialize new Ark vault with standard structure | Adapted from obsidian-wiki |
| `/wiki-ingest` | Vault Maintenance | Distill documents into vault pages | Adapted from obsidian-wiki |
| `/tag-taxonomy` | Vault Maintenance | Validate and normalize tags against taxonomy | Adapted from obsidian-wiki |
| `/cross-linker` | Vault Maintenance | Discover and add missing wikilinks | Adapted from obsidian-wiki |
| `/claude-history-ingest` | Vault Maintenance | Mine Claude conversations into compiled vault insights via MemPalace | Adapted from obsidian-wiki |
| `/data-ingest` | Vault Maintenance | Process logs, transcripts, exports into vault pages | Adapted from obsidian-wiki |
| `/ark-workflow` | Core | Task triage and skill chain orchestration (planned — no SKILL.md yet) | Planned |
| `/ark-onboard` | Onboarding | Interactive setup wizard — greenfield, migration, repair | New |
| `/ark-health` | Onboarding | Diagnostic check for Ark ecosystem health | New |

## Skill Documentation

### Core Skills

**`/ark-code-review`** — Fans out to parallel agents (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) and aggregates findings. Modes: `--quick`, `--thorough`, `--full`, `--epic TASK-ID`, `--plan SLUG`, `--pr N`. Requires: project name, task prefix, vault path, TaskNotes path from CLAUDE.md.

**`/codebase-maintenance`** — Three workflows: code cleanup (dead code, stale scripts), vault sync (map code changes to vault docs), and skill sync (heal drifted skill references). Routes via argument: `code`, `vault`, `skills`, `full`.

**`/notebooklm-vault`** — Bridges the Obsidian vault with Google NotebookLM for persistent cross-session memory. Sub-commands: `setup`, `ask`, `session-continue`, `bootstrap`, `session-handoff`, `audio`, `report`, `conflict-check`, `status`.

### Task Automation

**`/ark-tasknotes`** — Creates TaskNote tickets during development workflows. Uses tasknotes MCP when Obsidian is running, falls back to direct markdown write. Manages task IDs via counter file, syncs to Linear via linear-updater.

### Vault Maintenance

`/wiki-query` supports **multi-backend retrieval** (Phase 1) via the Vault Retrieval Defaults in CLAUDE.md:
- **T1 (NotebookLM):** Pre-synthesized answers for factual lookups (~500 tokens)
- **T2 (MemPalace):** Deep context and synthesis from vault pages + conversation history (~2,500 tokens)
- **T3 (Obsidian-CLI):** Full-text search across all vault files (~119 tokens + selective reads)
- **T4 (index.md scan):** Zero-dependency fallback using the existing 3-step index/summary/full-read pattern (~2,100 tokens)

Other vault skills continue to use the T4 (index.md scan) pattern. Multi-backend support for additional skills is planned for Phase 2.

Key operations: `/wiki-lint` audits vault health (broken links, missing frontmatter, stale index, tag violations). `/wiki-update` syncs project knowledge and regenerates `index.md`. `/tag-taxonomy` enforces consistent tagging against `_meta/taxonomy.md`. `/cross-linker` discovers and adds missing wikilinks.

**`/claude-history-ingest`** — Mines Claude Code conversation history into compiled vault insights using MemPalace (ChromaDB). Two-layer pipeline: a Stop hook auto-indexes sessions (zero LLM tokens), and a compile pass synthesizes insights via semantic search (~10K tokens vs 100-200K previously). Three modes: `index`, `compile`, `full` (default). Requires `pip install mempalace`.

### Onboarding

**`/ark-onboard`** — Interactive setup wizard and single entry point for new Ark projects. Detects project state (greenfield, non-Ark vault, partial Ark, healthy) and guides setup through Quick, Standard, or Full tiers. Absorbs `/wiki-setup` functionality. Handles vault creation, CLAUDE.md configuration, Obsidian plugin setup, TaskNotes MCP, MemPalace, history hook, and NotebookLM.

**`/ark-health`** — Diagnostic check that runs 19 checks across plugins, project configuration, vault structure, and integrations. Produces a scored scorecard with actionable fix and upgrade instructions. No auto-fix — always points to `/ark-onboard` for remediation.

## Context-Discovery Pattern

Every skill uses **context-discovery** — no skill contains hardcoded project names, vault paths, or task prefixes. When invoked, each skill:

1. Reads the project's `CLAUDE.md` in the current working directory
2. If it's a monorepo hub, follows the link to the active sub-project's CLAUDE.md
3. Extracts: project name, task prefix, vault root, project docs path, TaskNotes path, deployment targets, NotebookLM config

See `CLAUDE.md` in this repo for the full discovery procedure and field reference.

**Exemption:** `/ark-onboard` and `/ark-health` are exempt from context-discovery — they must work when CLAUDE.md is missing, broken, or incomplete.

## Architecture

```
ark-skills (Claude Code plugin)
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (ark-skills v1.1.0)
│   └── marketplace.json      # Repo-level plugin registry
└── skills/                   # 16 shared skills
      ↓ context-discovery
Project CLAUDE.md → vault path, task prefix, deployment targets
      ↓
Obsidian Vault → TaskNotes → linear-updater → Linear
               → NotebookLM sync
```

## New Project Onboarding

Run `/ark-onboard` for interactive guided setup. It detects your project state and walks you through the appropriate setup path.

For manual setup, see [docs/onboarding-guide.md](docs/onboarding-guide.md).

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifest (plugin.json, marketplace.json) |
| `skills/` | 16 shared skill definitions (SKILL.md files) |
| `docs/` | Design specs, plans, onboarding guide |
| `ArkNode-AI/` | Submodule: AI trading project (skill source for generalization) |
| `ArkNode-Poly/` | Submodule: Polymarket project (skill source for generalization) |
| `Arknode-AI-Obsidian-Vault/` | Submodule: AI vault repo |
| `Arknode-Poly-Obsidian-Vault/` | Submodule: Poly vault repo |
| `obsidian-wiki/` | Submodule: upstream wiki skill reference |
| `tasknotes/` | Submodule: Obsidian tasknotes plugin (MCP server) |
| `linear-updater/` | Submodule: TaskNotes-to-Linear sync service |

## Development

### Modifying Skills

1. Edit `skills/<skill-name>/SKILL.md`
2. Test by invoking the skill from a project
3. Verify no hardcoded references:
   ```bash
   grep -rn "ArkPoly\|ArkSignal\|trading-signal-ai\|CT100\|CT110\|CT120\|192\.168" skills/
   ```
4. Commit and push

### Verification Checks

```bash
# All 16 skills exist
find skills -name SKILL.md | wc -l  # → 16

# Zero hardcoded project references
grep -rn "ArkPoly\|ArkSignal\|trading-signal-ai\|arknode-poly" skills/

# Zero upstream wiki dependencies
grep -rn "\.env\|OBSIDIAN_VAULT_PATH\|manifest\.json" skills/

# All skills reference context-discovery
grep -rL "Project Discovery\|CLAUDE.md" skills/*/SKILL.md  # → empty
```

## Vault Artifacts

All Ark vaults include standard artifacts from the vault restructuring:

| Artifact | Path | Purpose |
|----------|------|---------|
| Vault schema | `_meta/vault-schema.md` | Self-documenting vault structure |
| Tag taxonomy | `_meta/taxonomy.md` | Canonical tag vocabulary |
| Index generator | `_meta/generate-index.py` | Regenerates `index.md` |
| Machine index | `index.md` | Flat catalog of all pages with summaries |
| Summaries | `summary:` frontmatter | <=200 char description on every page |

Skills leverage these artifacts for tiered retrieval, tag validation, and index management.
