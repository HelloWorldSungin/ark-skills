---
title: "Index"
type: meta
tags:
  - meta
summary: "Machine-generated flat catalog of all vault pages."
last-updated: 2026-04-09
---

# Index

<!-- AUTO-GENERATED — do not edit manually. Run: python3 _meta/generate-index.py -->

| Page | Type | Summary |
|------|------|---------|
| [[00-Home.md|Ark Skills Knowledge Base]] | moc | Navigation hub for ark-skills: links to project areas and key resources. |
| [[Compiled-Insights/Development-Workflow-Patterns.md|Development Workflow Patterns]] | compiled-insight | Established workflow: brainstorm → spec → codex review → plan → implement. Audit-first for restructuring. NotebookLM for vault queries. Risk-primary triage with density escalation. Hybrid TodoWrite + file continuity for cross-session chains. |
| [[Compiled-Insights/Dogfooding-Driven-Skill-Development.md|Dogfooding-Driven Skill Development]] | compiled-insight | The most effective way to develop skills is to use them on the plugin's own repo — wiki-setup grew from 10 to 13 steps after dogfooding. |
| [[Compiled-Insights/Ecosystem-Architecture-Map.md|Ecosystem Architecture Map]] | compiled-insight | The Ark ecosystem connects 7 repos via shared skills plugin, Obsidian vaults synced to NotebookLM, Linear via linear-updater, and Proxmox homelab infrastructure. |
| [[Compiled-Insights/MemPalace-Integration-Architecture.md|MemPalace Integration Architecture]] | compiled-insight | claude-history-ingest wraps mempalace with custom hooks and three modes (index/compile/full) — NOT using mempalace's built-in hooks, which are too intrusive. |
| [[Compiled-Insights/Plugin-Architecture-and-Context-Discovery.md|Plugin Architecture & Context-Discovery Pattern]] | compiled-insight | Ark-skills uses a Claude Code plugin with context-discovery — skills read CLAUDE.md at runtime, eliminating hardcoded project config and enabling cross-project reuse. |
| [[Compiled-Insights/Plugin-Versioning-and-Cache-Pitfalls.md|Plugin Versioning & Cache Pitfalls]] | compiled-insight | Claude Code plugin versioning has 4 sources of truth (VERSION, plugin.json, marketplace.json, cache SHA) — any desync causes silent update failure. |
| [[Compiled-Insights/Retrieval-Backend-Benchmark.md|Retrieval Backend Benchmark — index.md vs Obsidian-CLI vs MemPalace]] | compiled-insight | Benchmarked 3 retrieval backends on ArkNode-AI vault (394 pages): index.md scan won for documented decisions (~2K tokens), Obsidian-CLI matched quality but needs two-step pattern, MemPalace failed on vault queries (wrong corpus — indexes conversations, not pages). |
| [[Compiled-Insights/Session-Log-Knowledge-Burial.md|Session Log Knowledge Burial — The Core Vault Problem]] | compiled-insight | Session log knowledge burial is the primary vault problem — 103+ session logs with hard-won ML insights buried in chronological journals, inaccessible to retrieval. |
| [[Compiled-Insights/Shell-Script-Safety-Patterns.md|Shell Script Safety Patterns — Lessons from mine-vault.sh Review]] | compiled-insight | Three shell scripting pitfalls caught by code review: TMPDIR env collision causes subprocess failures, pipefail+tail swallows errors, and missing EXIT traps leak temp dirs. All patterns apply to future bash scripts in skills/shared/. |
| [[Compiled-Insights/TaskNotes-MCP-Integration-Model.md|TaskNotes MCP Integration — Architecture & Limitations]] | compiled-insight | TaskNotes MCP is an HTTP endpoint inside Obsidian (not standalone), with limited schema — custom frontmatter requires post-edit or direct markdown write. |
| [[Compiled-Insights/TaskNotes-Status-Triage-Design.md|TaskNotes Status & Triage — Design Decisions]] | compiled-insight | ark-tasknotes status uses MCP-first data gathering with LLM triage — no algorithmic scoring. Six-section report with opinionated work plan recommendations. |
| [[Compiled-Insights/Vault-Hosting-Evolution.md|Vault Hosting Evolution — Submodules to Standalone Repos]] | compiled-insight | Vaults evolved from submodules in ark-skills to standalone repos at ~/.superset/vaults/, symlinked from projects. Worktree branches can get lost during migration. |
| [[Compiled-Insights/Vault-Retrieval-Tier-Architecture.md|Vault Retrieval Tier Architecture — T1-T4 Design]] | compiled-insight | Four-tier retrieval: NotebookLM (T1, ~500 tokens), MemPalace (T2, ~2500), Obsidian-CLI (T3, ~119+reads), index.md (T4, ~2100). Routing by query type, not corpus. Key finding: MemPalace on vault pages scored 8/10 vs 0/10 on conversations alone. |
| [[Session-Logs/S001-MemPalace-Integration.md|Session: MemPalace Integration for claude-history-ingest]] | session-log | Implemented MemPalace (ChromaDB) backend for claude-history-ingest: Stop hook, installer, SKILL.md rewrite, shipped v1.1.0-1.1.2. |
| [[Session-Logs/S002-Ark-Workflow-Skill.md|Session: /ark-workflow Skill Implementation]] | session-log | Implemented /ark-workflow skill: task triage, scenario detection, weight-class skill chains. 11 tasks via subagent-driven-development, shipped v1.2.0. |
| [[Session-Logs/S002-Vault-Retrieval-Tiers-Phase1.md|Session: Vault Retrieval Tiers Phase 1 Implementation]] | session-log | Implemented T1-T4 multi-backend retrieval for wiki-query: mine-vault.sh, CLAUDE.md tier table, wiki-query rewrite, README update. 4 commits, all reviews passed. |
| [[Session-Logs/S003-Ark-Workflow-v2-Rewrite.md|Session: /ark-workflow v2 Rewrite]] | session-log | Rewrote /ark-workflow SKILL.md to address 22 gaps: 7 scenarios, risk+density triage, batch triage, continuity mechanism, cross-session resume. Shipped 1.6.0 in 6 phases. |
| [[TaskNotes/00-Project-Management-Guide.md|Project Management Guide]] | moc | How task IDs, statuses, and task notes work in the ark-skills project. |
| [[TaskNotes/Tasks/Epic/Arkskill-001-vault-retrieval-tiers.md|Multi-Backend Vault Retrieval Tiers]] |  |  |
