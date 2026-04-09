---
title: "Session: Vault Retrieval Tiers Phase 1 Implementation"
type: session-log
tags:
  - session-log
  - skill
  - plugin
  - retrieval
  - S002
summary: "Implemented T1-T4 multi-backend retrieval for wiki-query: mine-vault.sh, CLAUDE.md tier table, wiki-query rewrite, README update. 4 commits, all reviews passed."
prev: "[[S001-MemPalace-Integration]]"
epic: "[[Arkskill-001-vault-retrieval-tiers]]"
session: "S002"
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Session: Vault Retrieval Tiers Phase 1 Implementation

## Epic
[[Arkskill-001-vault-retrieval-tiers]] — Multi-backend vault retrieval

## Objective

Implement Phase 1 of the vault retrieval tiers design: add NotebookLM (T1), MemPalace (T2), Obsidian-CLI (T3), and index.md (T4) backends to wiki-query, with a shared mining helper and project-level documentation.

## Context

Design spec and implementation plan were written and reviewed by Codex in prior sessions. This session executed the plan using subagent-driven-development with per-task spec compliance and code quality reviews.

- Spec: `docs/superpowers/specs/2026-04-08-vault-retrieval-tiers-design.md`
- Plan: `docs/superpowers/plans/2026-04-08-vault-retrieval-tiers-phase1.md`
- Branch: `mem-palance-explore`

## Work Done

### Task 1: mine-vault.sh

Created `skills/shared/mine-vault.sh` — a bash script to index vault .md files into MemPalace:
- Accepts vault path as argument (for monorepo hub setups)
- Falls back to extracting from CLAUDE.md's "Obsidian Vault" row
- Detects symlink (shared vault) vs real dir (in-repo vault) for wing derivation
- Filters to .md only, excluding .obsidian/, node_modules/, _Templates/
- Uses `MINE_TMPDIR` (not `TMPDIR`) to avoid POSIX env collision
- EXIT trap for cleanup on unexpected exits
- Captures `mempalace init` failure (not swallowed by pipeline)

### Task 2: CLAUDE.md Vault Retrieval Defaults

Appended a new section to CLAUDE.md with:
- T1-T4 tier table (Backend, Best For, Token Cost)
- Availability checks: T1 checks BOTH vault_path and project root for config
- Failure messaging with specific `{vault_path}` and `{wing}` placeholders
- 7-rule query routing guide mapping question patterns to tier chains

### Task 3: wiki-query SKILL.md Rewrite

Full rewrite of skills/wiki-query/SKILL.md:
- Tier availability check with bash code block (T1-T4)
- Query classification: Factual, Relationship, Synthesis, Gap, Search, Browse
- Routing: Factual→T1, Synthesis/Relationship→T2, Gap→T2→T1→T4, Search→T3, Browse→T4
- `CONVO_WING` defined for shared vault dual-wing search
- T4 fallback guard when index.md is absent
- Failure messages include "Falling back to T4."
- Default to T4-only if "Vault Retrieval Defaults" section missing from CLAUDE.md
- Old Tier 1/2/3 renamed to Step 3a/3b/3c within T4 fallback

### Task 4: README.md Update

- Prerequisites: optional dependency table (MemPalace, NotebookLM CLI, Obsidian CLI)
- mine-vault.sh setup instructions
- Vault Maintenance section rewritten for T1-T4 multi-backend language
- Scoped to wiki-query only (Phase 1)
- /claude-history-ingest paragraph preserved word-for-word

### Task 5: End-to-end validation

22 automated checks passed:
- Zero hardcoded project references in skills/
- 14 SKILL.md files (all skills intact)
- mine-vault.sh executable (rwxr-xr-x)
- Context-discovery references present in wiki-query
- obsidian:obsidian-cli fully qualified (2 references)
- Routing trace verified for all 4 query type examples

## Decisions Made

- **MINE_TMPDIR, not TMPDIR:** Code quality review caught that `TMPDIR` shadows a POSIX environment variable. Renamed throughout.
- **EXIT trap + init failure capture:** Two quality improvements over the plan's verbatim script. EXIT trap ensures cleanup on unexpected exits; init failure is captured instead of being swallowed by a pipe to `tail`.
- **CONVO_WING in availability check block:** Code quality review caught that `$CONVO_WING` was used in routing but never defined. Added to the bash code block.
- **T4 fallback guard:** Code quality review noted T4 could fail if index.md doesn't exist. Added a guard with actionable error message.
- **Failure messages match spec, not plan:** The plan's template had weakened versions of the spec's failure messages (missing config paths and {wing} placeholder). Restored the spec-level detail.
- **Default to T4 when Vault Retrieval Defaults absent:** Ensures wiki-query works in projects that haven't adopted tiers yet.

## Quality Process

Used subagent-driven-development: fresh subagent per task, two-stage review (spec compliance then code quality) after each. Fixes applied and re-reviewed. Final cross-file consistency review confirmed all 4 files agree on tier numbering, backend names, availability logic, wing derivation, and failure messaging.

## Open Questions

- The `stat -f %m` pattern in mine-vault.sh's parent (ark-history-hook.sh) is macOS-only. mine-vault.sh itself doesn't have this issue.
- Should the `obsidian:obsidian-cli` skill name format be documented in CLAUDE.md's context-discovery section? Currently it's only in the tier table.
- Phase 2 timing: when to start adding T2 to ark-code-review and wiki-update depends on wiki-query validation across 2-3 projects.

## Next Steps

- Test wiki-query with all 4 tiers on ArkNode-AI (has NotebookLM + MemPalace + Obsidian)
- Test wiki-query T4-only fallback on a project without optional backends
- Validate the mine-vault.sh script on ArkNode-Poly vault (shared external vault via symlink)
- Begin Phase 2 planning: T2 for ark-code-review and wiki-update, T3 for cross-linker
