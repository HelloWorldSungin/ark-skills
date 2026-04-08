# Ark Skills Plugin

Claude Code plugin providing 14 shared skills to all ArkNode projects. Eliminates skill duplication across repos by centralizing skills with a context-discovery pattern that adapts to each project at runtime.

## Installation

```bash
# Add the marketplace
/plugin marketplace add HelloWorldSungin/ark-skills

# Install the plugin (user-scoped — available in all projects)
/plugin install ark-skills@ark-skills

# Verify skills are available
/wiki-status
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
| `/claude-history-ingest` | Vault Maintenance | Mine Claude conversations into compiled insights | Adapted from obsidian-wiki |
| `/data-ingest` | Vault Maintenance | Process logs, transcripts, exports into vault pages | Adapted from obsidian-wiki |

## Skill Documentation

### Core Skills

**`/ark-code-review`** — Fans out to parallel agents (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) and aggregates findings. Modes: `--quick`, `--thorough`, `--full`, `--epic TASK-ID`, `--plan SLUG`, `--pr N`. Requires: project name, task prefix, vault path, TaskNotes path from CLAUDE.md.

**`/codebase-maintenance`** — Three workflows: code cleanup (dead code, stale scripts), vault sync (map code changes to vault docs), and skill sync (heal drifted skill references). Routes via argument: `code`, `vault`, `skills`, `full`.

**`/notebooklm-vault`** — Bridges the Obsidian vault with Google NotebookLM for persistent cross-session memory. Sub-commands: `setup`, `ask`, `session-continue`, `bootstrap`, `session-handoff`, `audio`, `report`, `conflict-check`, `status`.

### Task Automation

**`/ark-tasknotes`** — Creates TaskNote tickets during development workflows. Uses tasknotes MCP when Obsidian is running, falls back to direct markdown write. Manages task IDs via counter file, syncs to Linear via linear-updater.

### Vault Maintenance

All 10 vault skills use the **tiered retrieval** pattern:
1. **Tier 1 — Index scan:** Read `index.md` for page catalog with summaries
2. **Tier 2 — Summary scan:** Read `summary:` frontmatter (<=200 chars each)
3. **Tier 3 — Full read:** Only open top 3-5 candidates

Key operations: `/wiki-lint` audits vault health (broken links, missing frontmatter, stale index, tag violations). `/wiki-update` syncs project knowledge and regenerates `index.md`. `/tag-taxonomy` enforces consistent tagging against `_meta/taxonomy.md`. `/cross-linker` discovers and adds missing wikilinks.

## Context-Discovery Pattern

Every skill uses **context-discovery** — no skill contains hardcoded project names, vault paths, or task prefixes. When invoked, each skill:

1. Reads the project's `CLAUDE.md` in the current working directory
2. If it's a monorepo hub, follows the link to the active sub-project's CLAUDE.md
3. Extracts: project name, task prefix, vault root, project docs path, TaskNotes path, deployment targets, NotebookLM config

See `CLAUDE.md` in this repo for the full discovery procedure and field reference.

## Architecture

```
ark-skills (Claude Code plugin)
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (ark-skills v1.0.0)
│   └── marketplace.json      # Repo-level plugin registry
└── skills/                   # 14 shared skills
      ↓ context-discovery
Project CLAUDE.md → vault path, task prefix, deployment targets
      ↓
Obsidian Vault → TaskNotes → linear-updater → Linear
               → NotebookLM sync
```

## New Project Onboarding

See [docs/onboarding-guide.md](docs/onboarding-guide.md) for step-by-step instructions to add a new project to the Ark ecosystem with shared skills, vault, and Linear sync.

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifest (plugin.json, marketplace.json) |
| `skills/` | 14 shared skill definitions (SKILL.md files) |
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
# All 14 skills exist
find skills -name SKILL.md | wc -l  # → 14

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
