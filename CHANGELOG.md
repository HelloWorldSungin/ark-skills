# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-04-08

### Added
- Multi-backend vault retrieval tiers for `/wiki-query`: T1 (NotebookLM), T2 (MemPalace),
  T3 (Obsidian-CLI), T4 (index.md scan). Routes queries by type with automatic fallback.
- `skills/shared/mine-vault.sh` — one-time helper to index vault .md files into MemPalace.
  Accepts vault path argument, detects symlink vs real dir, derives wing name.
- Vault Retrieval Defaults section in CLAUDE.md: tier table, availability checks,
  failure messaging, and 7-rule query routing guide.
- Optional dependency table in README (MemPalace, NotebookLM CLI, Obsidian CLI).

### Changed
- `wiki-query` SKILL.md rewritten: query classification (factual, synthesis, gap, search,
  browse), tier availability check, per-type routing, T4 fallback guard, CONVO_WING for
  shared vaults. Old Tier 1/2/3 renamed to Step 3a/3b/3c within T4.
- README Vault Maintenance section updated for multi-backend language scoped to wiki-query (Phase 1).

## [1.1.2] - 2026-04-08

### Fixed
- SKILL.md index mode now explicitly states to mine the project root directory only,
  preventing errors from attempting to mine subdirectories like `memory/`

## [1.1.1] - 2026-04-08

### Fixed
- Stop hook now registers in per-project `.claude/settings.json` instead of global settings.
  The hook only fires in projects that explicitly run the installer.

## [1.1.0] - 2026-04-08

### Changed
- `claude-history-ingest` skill rewritten to use MemPalace (ChromaDB) for indexing and retrieval.
  Auto-indexes sessions via Stop hook (zero LLM tokens). Compiles insights via semantic search
  (~10K tokens vs 100-200K previously). Three modes: index, compile, full.
  Requires `pip install mempalace`.

### Added
- `skills/claude-history-ingest/hooks/ark-history-hook.sh` — Stop hook for auto-indexing
- `skills/claude-history-ingest/hooks/install-hook.sh` — One-time setup helper

### Fixed
- Path encoding now matches Claude Code's convention (replaces both `/` and `.` with `-`)
- Installer updates existing hook to latest version instead of silently skipping

## [1.0.2.0] - 2026-04-08

### Changed
- `claude-history-ingest` skill now scopes to current project's Claude directory instead of scanning all projects

## [1.0.1.0] - 2026-04-08

### Added
- Ark vault for this repo (`vault/`) with standard structure, templates, metadata, and task tracking
- Obsidian configuration with TaskNotes (v4.5.1) and Obsidian Git plugins pre-installed
- NotebookLM config template (`.notebooklm/config.json`) with placeholder notebook ID
- Project Configuration section in CLAUDE.md for context-discovery

### Changed
- wiki-setup skill now includes Obsidian plugin installation (Steps 8-9), NotebookLM config (Step 10), and expanded post-setup checklist
- Onboarding guide rewritten with full CLAUDE.md template, three layout examples (standalone, separate repo, monorepo), plugin documentation, and NotebookLM config reference

## [1.0.0.0] - 2026-04-08

### Added
- Claude Code plugin manifest (`.claude-plugin/plugin.json`, `marketplace.json`) for installation via `/plugin marketplace add`
- 14 shared skills: ark-code-review, ark-tasknotes, codebase-maintenance, notebooklm-vault, wiki-query, wiki-status, wiki-update, wiki-lint, wiki-setup, wiki-ingest, tag-taxonomy, cross-linker, claude-history-ingest, data-ingest
- Context-discovery pattern: all skills read project CLAUDE.md at runtime instead of hardcoding paths
- Vault restructure artifacts (summary frontmatter, index.md, vault-schema, tag-taxonomy) in both AI and Poly vault submodules
- NotebookLM vault sync script with incremental change detection
- Onboarding guide for new projects
- Comprehensive README with installation instructions and skill reference

### Fixed
- Shell script function ordering: `die()` and `jq` prereq check moved before first usage in vault sync script
