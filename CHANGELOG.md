# Changelog

All notable changes to this project will be documented in this file.

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
