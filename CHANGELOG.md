# Changelog

All notable changes to this project will be documented in this file.

## [1.10.1] - 2026-04-12

### Corrected

v1.10.0's framing overstated the hook-registration problem. Correction:

- **Claude Code merges hook arrays from global `~/.claude/settings.json` and project-local
  `.claude/settings.json`** — it does NOT shadow. The Stop hook registered in `~/.claude/settings.json`
  was firing for `ArkNode-AI/projects/trading-signal-ai`, `ArkNode-Poly`, and `ark-skills` the
  entire time, despite each project's local `settings.json` containing only `PostToolUse`.
  Evidence: `~/.mempalace/hook_state/mine.log` showed hundreds of hook fires per day for all
  three wings — including fires that happened **before** v1.10.0's `install-hook.sh` runs
  added the project-local registration.
- **The project-local hook installs in v1.10.0 were cosmetic, not functional.** The three
  projects already had the hook firing via the global registration. The installs added
  redundant entries that don't change observable behavior.
- **What v1.10.0 DID correctly fix:** the `threshold-lock` WARN in `/ark-health` Check 16
  caught Poly's real bug — `compile_threshold.json` baseline stuck at 4319 == current, so
  `new_drawers = 0` forever, and auto-compile never fired. That WARN is still valuable and
  unchanged.
- **Why Poly's baseline got stuck** (root cause, previously unexplained in v1.10.0):
  `mempalace mine` dedupes by filename. Claude Code session transcripts are monotonically
  appended (session_id is the filename, content grows over the session lifecycle). Modified
  transcripts get skipped by mine as "already filed", so the drawer count doesn't grow when
  sessions are continued rather than newly started. Poly had mostly continuation sessions,
  so the 4319 baseline went stale. Filed [mempalace#645](https://github.com/MemPalace/mempalace/issues/645#issuecomment-4233459673)
  with the Claude Code repro (existing issue — author already filed a markdown-vault variant).

### Changed

- `/ark-onboard` repair mode: the Check 16 reclassification remains, but the "missing
  project-local registration" scenario is now understood as cosmetic in most cases (hook
  fires via global). The reclassification is still useful for the narrower case where
  neither global nor project-local has the hook — rare but real.
- `/wiki-update` auto-trigger documentation: unchanged. Still accurate.

### What to know going forward

1. If `/ark-health` Check 16 WARNs on `threshold-lock`, that's a **real** bug — the auto-compile
   will never fire until the baseline moves. Fix: run `/claude-history-ingest compile` to
   re-anchor, or lower the baseline manually.
2. If Check 16 FAILs on "hook registered" but mempalace is firing (check `mine.log`),
   investigate whether you actually need project-local registration. Usually the global
   registration is sufficient.
3. Long-running Claude sessions don't add drawers via `mempalace mine` until new session
   files are created. Start fresh sessions periodically, or wait for `mempalace --refresh`
   (tracked upstream at [#645](https://github.com/MemPalace/mempalace/issues/645)).

## [1.10.0] - 2026-04-12

### Fixed
- **MemPalace auto-hook now detects silent-failure modes in `/ark-health` Check 16.**
  The hook was installed globally (`~/.claude/settings.json`) but project-local
  `.claude/settings.json` files shadow the global for that project, so projects
  like `ArkNode-AI/projects/trading-signal-ai` and `ArkNode-Poly` were silently
  running without session auto-indexing or the 50-drawer auto-compile trigger.
  Check 16 previously only verified that the hook was registered; it now catches
  three additional drift modes as WARNs:
  - **Wing-mismatch** — `mempalace status` has no wing matching the PWD-derived key.
  - **Threshold-staleness** — `new_drawers >= 200` (way past the 50-threshold) but no compile has fired.
  - **Threshold-lock** — `current_drawers == drawers_at_last_compile` and baseline > 500 (stuck state).
  Wing-match uses `grep -Fxq --` to avoid treating wing keys (which start with `-`) as flag arguments.

### Changed
- **`/ark-onboard` repair mode reclassifies Check 16 as Standard failure** when
  mempalace + vault wing are present but the hook is unregistered — this is the
  missing-glue case, and it's now auto-fixed in Step 3 rather than being hidden
  under "Available upgrades". Added a new **Step 3b: Warnings (interactive review)**
  that presents Check 16's three WARN sub-conditions with fix-now / skip / explain
  options (threshold-lock and wing-mismatch need human judgment, so they are
  never auto-applied).
- **`/wiki-update`** now documents its relationship to the 50-drawer auto-compile
  trigger — clarifies that `compile_threshold.json` is owned by `/claude-history-ingest compile`,
  and that manual `/wiki-update` runs after a compile do not affect the next auto-fire.

### Context
Discovered while debugging why `ArkNode-AI/trading-signal-ai` and `ArkNode-Poly`
were not firing the 50-conversation auto-hook despite the global hook being
installed. Root cause: project-local `settings.json` shadows global, and neither
project registered the Stop hook. Both projects were fixed by running
`install-hook.sh` from each CWD; ark-health/ark-onboard were hardened so this
silent-failure class is detected and repair-able going forward.

## [1.9.0] - 2026-04-12

### Fixed
- **`/notebooklm-vault` sync no longer accumulates ghost source registrations.**
  `notebooklm-py`'s `add_file()` is a 3-step pipeline (register → start-upload →
  stream); if step 2 or 3 fails, a ghost source is registered on the server but
  not tracked locally, so the next run re-registers it. This caused
  `linear-updater`'s notebooks to hit the 300-source cap with ~332 duplicates
  between them. The same bug class applied to the plugin's
  `skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh` (verified by direct
  code reading). Ported the fix from `linear-updater`:
  - **Notebook-authoritative existence.** Each incremental run lists remote
    sources once per notebook and builds a title→id map; existence is checked
    against the remote, not against local state. `sync-state.json` is now a
    hash cache only.
  - **Dedupe-and-heal pass on every incremental run.** Groups sources by title;
    keeps survivor (READY > PROCESSING > ERROR, tiebreak oldest `created_at`),
    deletes the rest. Orphan-prunes `.md` titles not present in the vault
    (preserves non-`.md` sources like manually-added PDFs).
  - **Ghost registration recovery.** Snapshots per-title source IDs before each
    `notebooklm source add`. On any failure, re-lists and diffs against the
    snapshot; if exactly one new source appeared, claims it instead of retrying
    (which would create a duplicate).
  - **Collision detection (fail-loud).** Two vault files with the same basename
    routed to the same notebook would silently overwrite each other (NotebookLM
    titles by basename only). Script now fails with a clear error listing the
    conflicting paths.
  - **State-delete verification.** The state-driven deletion pass now verifies
    a source is actually gone (re-list check) before clearing local state on
    delete failure, preventing orphan leaks.
  - **Per-vault concurrency lock.** `mkdir`-based lock at
    `/tmp/notebooklm-vault-sync.<vault>.lock` serializes concurrent runs. Stale
    locks from crashed runs are detected via PID and removed automatically.
    Portable (no `flock` dependency — works on macOS out of the box).
  - **Cleanup trap surfaces flush failures** instead of silencing them.
- Latent exclusion bug: `TaskNotes/` and `_meta/` now included in the default
  excludes list for standalone vaults (previously only filtered for wrapped
  vaults via subdir discovery). TaskNotes were never meant to sync to NotebookLM.
- Empty notebook id in `.notebooklm/config.json` now fails with a clear
  "Run '/notebooklm-vault setup'" message instead of an opaque
  `notebooklm source list` error.

### Changed
- `/notebooklm-vault` SKILL.md: new `## Sync Behavior` section documenting the
  four modes (incremental, `--sessions-only`, `--file`, `--full`), ghost
  recovery, and troubleshooting. Updated the "Periodic sync is owned by the
  scheduled sync service" warning — local runs are now safe, since the script
  self-heals drift rather than creating duplicates.

## [1.8.0] - 2026-04-10

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
- `skills/ark-workflow/` — Hygiene chains previously ended with `/wiki-update
  (if vault) + session log`. The `+ session log` suffix is dropped in the
  progressive-disclosure chain files because session log creation is now
  implicit in `/wiki-update`.
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
- Existing session logs in `vault/Session-Logs/` (S001, S002×2, S003, S004) lack
  the new `date` and `status` fields. They still parse cleanly against
  `_meta/generate-index.py` (defaults via `.get()`), so no migration is strictly
  required. A follow-up PR should backfill them and resolve the pre-existing
  `S002` numbering collision (`S002-Ark-Workflow-Skill.md` vs
  `S002-Vault-Retrieval-Tiers-Phase1.md` both use session number 2).

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
