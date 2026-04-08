---
title: "Session Log Knowledge Burial — The Core Vault Problem"
type: compiled-insight
tags:
  - compiled-insight
  - vault
summary: "Session log knowledge burial is the primary vault problem — 103+ session logs with hard-won ML insights buried in chronological journals, inaccessible to retrieval."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Session Log Knowledge Burial — The Core Vault Problem

## Summary

The 2026-04-07 vault audit identified session log knowledge burial as the **primary problem** across both Obsidian vaults, not structural deficiency. The AI vault has 103 session logs spanning ~6 months of ML trading research. Critical insights — like "TFT does NOT help" and "condition filters are the sole alpha source" — are buried in chronological work journals, discoverable only by reading specific sessions sequentially.

## Key Insights

### The Vaults Are Structurally Sound

Before the audit, the assumption was that vaults needed significant restructuring to match obsidian-wiki's three-layer pattern. The audit found the opposite:
- **Cross-linking**: 5.1 links/file (AI vault), zero orphans
- **Frontmatter coverage**: 99.1% (AI vault), 96%+ (Poly vault)
- **TaskNotes schema**: richer than obsidian-wiki's generic template
- **Session log chaining**: `prev:` / `epic:` frontmatter creates navigable timeline

These strengths should be preserved, not restructured away.

### Specific Buried Knowledge (AI Vault)

High-value findings locked inside individual session logs:
- **TFT conclusively does not help** — Session/ArkSignal-034, with 4-way deployment matrices
- **Spot-to-perp volume swap provides no benefit** — Session-329
- **Condition filters are the sole alpha source** — +1.0 to +2.5 Sharpe lift across multiple sessions
- **Model architecture decisions** with supporting evidence scattered across sessions

An LLM or human asking "what did we learn about TFT?" must read sessions sequentially. At 103+ sessions, this is impractical.

### Incremental Adoption Over Full Restructure

The recommendation is targeted intervention, not wholesale restructuring:
- **Phase 1**: Extract compiled insight pages from highest-value buried knowledge (~3 sessions)
- **Phase 2**: Add `summary:` frontmatter, generate `index.md`, write vault schema (~2 sessions per vault)
- **Phase 3**: Run wiki-lint, create tag taxonomy, cross-linker pass (~1 session each)

### NotebookLM as a Retrieval Shortcut

Until compiled insights exist, NotebookLM (`notebooklm ask`) can query across all vault content including session logs. It already has everything indexed. This is faster and cheaper than having subagents read individual session logs.

## Evidence

- Full audit: `docs/vault-audit.md` (2026-04-07)
- Implementation plan: `docs/superpowers/plans/2026-04-07-vault-restructure.md` (19 tasks, 3 phases)
- Memory: `project_vault_audit_findings.md`, `feedback_notebooklm_for_vault.md`

## Implications

- The ark-skills vault maintenance skills (wiki-lint, wiki-update, tag-taxonomy) should operate on well-structured vaults. The restructuring plan establishes the foundation these skills need.
- Session log compilation should happen after every major epic or ~20 sessions.
- Poly vault (24 sessions) is not yet critical — revisit at ~50 sessions or when specific knowledge becomes hard to find.
- For immediate vault queries, prefer `notebooklm ask` over reading individual files.
