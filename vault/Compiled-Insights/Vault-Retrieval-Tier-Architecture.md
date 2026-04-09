---
title: "Vault Retrieval Tier Architecture — T1-T4 Design"
type: compiled-insight
tags:
  - compiled-insight
  - vault
  - skill
summary: "Four-tier retrieval: NotebookLM (T1, ~500 tokens), MemPalace (T2, ~2500), Obsidian-CLI (T3, ~119+reads), index.md (T4, ~2100). Routing by query type, not corpus. Key finding: MemPalace on vault pages scored 8/10 vs 0/10 on conversations alone."
source-sessions:
  - "[[S002-Vault-Retrieval-Tiers-Phase1]]"
source-tasks:
  - "[[Arkskill-001-vault-retrieval-tiers]]"
created: 2026-04-08
last-updated: 2026-04-08
---

# Vault Retrieval Tier Architecture — T1-T4 Design

## Summary

The vault retrieval system uses four backends (T1-T4) routed by query type rather than corpus type. This inverts the earlier benchmark finding that backends should route by corpus — in practice, query intent is a better discriminator. The tier defaults live in CLAUDE.md (context-discovery pattern), not a dispatcher skill. wiki-query checks availability and routes; other skills will adopt tiers in Phase 2.

## Key Insights

### MemPalace on Vault Pages Is the Missing Piece

The initial benchmark (see [[Retrieval-Backend-Benchmark]]) tested MemPalace on conversation history only and scored 0/10. When vault markdown pages were mined into MemPalace alongside conversations, the score jumped to 8/10 — it surfaced the reasoning trail (Session 269 pivot, failure modes, metalabel dead end) that other backends missed. The `mine-vault.sh` script enables this by indexing vault .md files into the same wing as conversation history.

### Route by Query Intent, Not Corpus Type

The benchmark suggested routing by corpus (vault vs. conversations). Implementation proved that query intent is the better discriminator:
- "What did we decide?" → T1 (NotebookLM) — pre-synthesized, cheapest
- "Why did we decide it?" → T2 (MemPalace) — surfaces reasoning from sessions + vault
- "Find all mentions" → T3 (Obsidian-CLI) — full-text search
- "What pages exist?" → T4 (index.md) — structured catalog

The gap query type ("What don't we know?") chains T2→T1→T4 — the delta between experiential (T2) and documented (T1/T4) results reveals uncaptured knowledge.

### Tier Defaults in CLAUDE.md, Not a Dispatcher Skill

Three options were considered: per-skill hardcoding, a shared dispatcher skill, or tier defaults in CLAUDE.md. The CLAUDE.md approach won because it follows the existing context-discovery pattern — skills already read CLAUDE.md at runtime. No new skill infrastructure needed. The tier table, availability checks, and query routing guide live alongside existing project config.

### NotebookLM Added as T1 (Not in Original Benchmark)

NotebookLM was benchmarked separately at ~480 tokens with pre-synthesized answers and citations. It became T1 because it's the cheapest factual lookup: the notebook has already synthesized the vault content, so queries cost only the question + response (~500 tokens total). The catch: requires `notebooklm` CLI authenticated and a `.notebooklm/config.json` in the vault or project root.

## Evidence

- Benchmark: ArkNode-AI vault, 394 pages, query "what kind of model have we decided?"
- MemPalace vault pages: 8/10 (vs 0/10 conversations-only)
- NotebookLM: ~480 tokens, pre-synthesized with citations
- Design spec: `docs/superpowers/specs/2026-04-08-vault-retrieval-tiers-design.md`
- Codex review: 14 findings incorporated (symlink handling, gap routing, failure messaging)

## Implications

- Always mine vault pages into MemPalace (not just conversations) — `mine-vault.sh` is a prerequisite for T2 to work on vault queries
- Query classification matters more than backend selection — a well-classified query routes to the right tier automatically
- Phase 2 extensions (ark-code-review T2, wiki-update T2, cross-linker T3) should follow the same CLAUDE.md tier pattern
- Projects without optional backends gracefully degrade to T4 — the system is additive, not all-or-nothing
