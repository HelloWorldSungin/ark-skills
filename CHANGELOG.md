# Changelog

All notable changes to this project will be documented in this file.

## [1.7.0] - 2026-04-10

### Changed
- **ark-workflow**: Progressive-disclosure split of the monolithic router
  - Main `SKILL.md`: 858 → 270 lines (68.5%)
  - Common-path context load (router + one chain file): 858 → ~313 lines avg (63.5%); worst case (Greenfield) 858 → 334 lines (61.1%); best case (Ship) 858 → 280 lines (67.4%)
  - Chain variants moved to `chains/{scenario}.md` (7 files: greenfield, bugfix, ship, knowledge-capture, hygiene, migration, performance)
  - Pay-per-use content moved to `references/{batch-triage,continuity,troubleshooting,routing-template}.md`
  - Behavioral parity: all 22 v2 gaps preserved, all 19 chain variants preserved, 10 `/test-driven-development` references preserved in chains/ (2 baseline references at SKILL.md L282 and L751 were intentionally dropped by Phase 3 — slimmed Step 6.5 and removed example block), 0 `/TDD` references
  - File count in `skills/ark-workflow/`: 1 → 12
  - Total repo footprint: 858 → 833 lines (−25 net — the progressive-disclosure split is a net shrink on disk AND a major context-load win)
  - Dropped the Condition Resolution "Example resolved output" block (14 lines, illustrative only)

## [1.6.0] - 2026-04-09

### Changed
- **ark-workflow**: Major rewrite of the task triage skill addressing 22 gaps (12 initial + 10 from Codex review)
  - Expanded from 5 to 7 scenarios: added Migration and Performance as first-class scenarios
  - Replaced factor-matrix triage with risk-primary + decision-density escalation (Heavy risk stays Heavy; architecture decisions escalate Light → Heavy)
  - Added Batch Triage for multi-item prompts with root cause consolidation, dependency heuristics, and per-group execution plans
  - Added Continuity mechanism: TodoWrite tasks + `.ark-workflow/current-chain.md` state file for in-session and cross-session chain tracking, with handoff markers, stale-chain detection, and context recovery after compaction
  - Added Hygiene Audit-Only variant for assessment-only requests (no implementation/ship forced)
  - Split security routing into Audit and Hardening paths, with `/cso` dedup rule (`/cso` runs exactly once per chain)
  - Added `/investigate` as conditional step in Hygiene chains for bug-like items
  - Added session handoff guidance for Heavy Bugfix, Hygiene, Migration, and Performance
  - Added scenario-shift re-triage handling with pivot examples
  - Fixed `/TDD` naming to `/test-driven-development` across all chains
  - Rewrote Routing Rules Template with session-resume block and new-task triggers for 7 scenarios

### Fixed
- ark-workflow: removed unreliable "10 tool calls since last file read" handoff trigger (output quality signals replace it)
- ark-workflow: Knowledge Capture now has Light/Full split instead of one-size-fits-all chain

## [1.5.0] - 2026-04-09

### Added
- `/ark-tasknotes status` subcommand — task overview dashboard with opinionated triage
  recommendations. Shows status counts, active work, stale/blocked items, velocity pulse,
  recently completed tasks, and a prioritized "what to work on next" work plan.
  Uses MCP tools when Obsidian is running, falls back to direct markdown reads.
- Skill restructured with Modes section (Create and Status) for extensibility.

## [1.4.2] - 2026-04-09

### Fixed
- `/ark-onboard` and `/ark-health`: TaskNotes MCP config now uses built-in HTTP transport
  (`type: http`, `url: http://localhost:{apiPort}/mcp`) instead of nonexistent `tasknotes-mcp`
  npm package. Removed `enableAPI` from TaskNotes `data.json` template (not a real setting).

## [1.4.1] - 2026-04-09

### Changed
- `/ark-onboard` Step 11 now downloads Obsidian plugin binaries (TaskNotes, Obsidian Git)
  directly from GitHub releases via the community-plugins.json registry. Falls back to
  reference vault copy, then manual GUI install as last resort.
- `/ark-onboard` Step 12 generates full `data.json` configs for both plugins — TaskNotes
  gets Ark-specific folder paths, custom statuses, field mappings, and Bases view bindings;
  Obsidian Git gets auto-save/pull/push intervals and merge strategy. No GUI configuration
  required.
- Repair path check 12 fix updated to use GitHub download instead of manual install.

## [1.4.0] - 2026-04-08

### Added
- `/ark-onboard` — interactive setup wizard for new Ark projects. Handles greenfield,
  non-Ark vault migration, partial repair, and health reporting. Absorbs `/wiki-setup`
  as the recommended entry point. Supports Quick, Standard, and Full setup tiers.
- `/ark-health` — diagnostic check for Ark ecosystem health. Runs 19 checks across
  plugins, CLAUDE.md fields, vault structure, and integrations. Produces a scored
  scorecard with actionable fix instructions.

## [1.3.0] - 2026-04-08

### Added
- `/ark-workflow` skill — task triage and skill chain orchestration. Entry point for all
  non-trivial work. Detects scenario (greenfield, bugfix, ship, knowledge capture, hygiene),
  classifies weight (light/medium/heavy) with risk as primary signal, and outputs the
  optimal ordered skill chain with project-specific conditions resolved.
- Routing rules template for project CLAUDE.md auto-triggering

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
