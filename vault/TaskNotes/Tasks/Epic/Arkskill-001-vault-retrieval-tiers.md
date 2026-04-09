---
tags:
  - task
title: "Multi-Backend Vault Retrieval Tiers"
task-id: "Arkskill-001"
status: in-progress
priority: high
project: "ark-skills"
work-type: development
task-type: epic
urgency: normal
session: "S002"
created: "2026-04-08"
---

# Arkskill-001: Multi-Backend Vault Retrieval Tiers

## Summary

Add T1-T4 retrieval backends (NotebookLM, MemPalace, Obsidian-CLI, index.md) to vault skills. Phase 1 targets wiki-query; Phase 2 extends to ark-code-review, wiki-update, and cross-linker.

## Spec & Plan

- Design: `docs/superpowers/specs/2026-04-08-vault-retrieval-tiers-design.md`
- Phase 1 Plan: `docs/superpowers/plans/2026-04-08-vault-retrieval-tiers-phase1.md`

## Phase 1 — wiki-query + foundation (DONE)

- [x] `skills/shared/mine-vault.sh` — vault mining helper
- [x] CLAUDE.md — Vault Retrieval Defaults section
- [x] `skills/wiki-query/SKILL.md` — T1-T4 rewrite
- [x] README.md — dependency table, setup, vault maintenance

## Phase 2 — remaining skills (TODO)

- [ ] `skills/ark-code-review/SKILL.md` — add T2 for historical context (bounded to diff file paths, 5 results)
- [ ] `skills/wiki-update/SKILL.md` — add T2 for undocumented knowledge discovery (suggestions only)
- [ ] `skills/cross-linker/SKILL.md` — add T3 via obsidian:obsidian-cli as experimental pre-filter

## Validation

- [ ] Test wiki-query on ArkNode-AI (all 4 tiers available)
- [ ] Test wiki-query T4-only fallback on a project without optional backends
- [ ] Test mine-vault.sh on shared external vault (symlink setup)

## Session Log

- [[S002-Vault-Retrieval-Tiers-Phase1]] — 2026-04-08: Phase 1 implemented, all reviews passed, 4 commits
