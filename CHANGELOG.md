# Changelog

All notable changes to this project will be documented in this file.

## [1.6.0] - 2026-04-10

### Changed
- **`/wiki-update` is now the single end-of-session workflow.** Previously a
  5-step knowledge-sync-and-index skill, it now runs a 6-step flow that creates
  or updates the session log, updates linked TaskNote epic/stories, extracts
  compiled insights from the session log content, regenerates `index.md`, and
  commits. Includes skip detection for ad-hoc docs syncs (preserves backward
  compat for narrow invocations with no git changes since the last session log).
- Session log frontmatter schema merged: `vault/_Templates/Session-Template.md`
  now uses `title` (with session number), `type: session-log`, `summary`,
  `session` (with `S` prefix), `status`, `date`, `prev`, `epic`, `source-tasks`,
  `created`, `last-updated`. The template's prior `title: "Session: {TITLE}"`
  (missing the session number) is fixed. `vault/_meta/vault-schema.md` type-specific
  fields row updated to document `date` and `status`.
- `skills/ark-workflow/SKILL.md` — the Medium and Heavy Hygiene chains previously
  ended with `/wiki-update (if vault) + session log`. The `+ session log` suffix
  is dropped because session log creation is now implicit in `/wiki-update`.
- `CLAUDE.md` (plugin) — `/wiki-update` and `/notebooklm-vault` skill descriptions
  updated to reflect the new split of responsibility.

### Removed
- **`/notebooklm-vault session-handoff` sub-command removed.** Its session log
  write, TaskNote epic/stories update, and sync-notify logic moved into
  `/wiki-update` (Step 2 + Step 3). `/notebooklm-vault` is now focused purely on
  NotebookLM query/sync concerns: `setup`, `ask`, `session-continue`, `bootstrap`,
  `audio`, `report`, `conflict-check`, `status`. The skill description and README
  sub-command list were updated accordingly. Any existing invocation using
  `wrap up`, `end session`, `hand off`, or `session log` triggers now routes to
  `/wiki-update`. Schema mismatch between the old session-handoff writes and the
  Session-Template (latent bug — old format omitted `title` and `summary`, which
  the vault index generator treats as canonical) is resolved by the merged schema.

### Known Issues (deferred)
- Existing session logs in `vault/Session-Logs/` lack the new `date` and `status`
  fields. They still parse cleanly against `_meta/generate-index.py` (defaults
  via `.get()`), so no migration is strictly required. A follow-up PR should
  backfill them and resolve the pre-existing `S002` collision
  (`S002-Ark-Workflow-Skill.md` vs `S002-Vault-Retrieval-Tiers-Phase1.md` both
  use session number 2; one should be renumbered to `S003`).

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
