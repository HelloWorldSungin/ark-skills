---
title: "Index"
type: meta
tags:
  - meta
summary: "Machine-generated flat catalog of all vault pages."
last-updated: 2026-04-08
---

# Index

<!-- AUTO-GENERATED — do not edit manually. Run: python3 _meta/generate-index.py -->

| Page | Type | Summary |
|------|------|---------|
| [[00-Home.md|Ark Skills Knowledge Base]] | moc | Navigation hub for ark-skills: links to project areas and key resources. |
| [[Compiled-Insights/Development-Workflow-Patterns.md|Development Workflow Patterns]] | compiled-insight | Established workflow: brainstorm → spec → codex review → plan → implement. Audit-first for restructuring. NotebookLM for vault queries over reading files. |
| [[Compiled-Insights/Dogfooding-Driven-Skill-Development.md|Dogfooding-Driven Skill Development]] | compiled-insight | The most effective way to develop skills is to use them on the plugin's own repo — wiki-setup grew from 10 to 13 steps after dogfooding. |
| [[Compiled-Insights/Ecosystem-Architecture-Map.md|Ecosystem Architecture Map]] | compiled-insight | The Ark ecosystem connects 7 repos via shared skills plugin, Obsidian vaults synced to NotebookLM, Linear via linear-updater, and Proxmox homelab infrastructure. |
| [[Compiled-Insights/MemPalace-Integration-Architecture.md|MemPalace Integration Architecture]] | compiled-insight | claude-history-ingest wraps mempalace with custom hooks and three modes (index/compile/full) — NOT using mempalace's built-in hooks, which are too intrusive. |
| [[Compiled-Insights/Plugin-Architecture-and-Context-Discovery.md|Plugin Architecture & Context-Discovery Pattern]] | compiled-insight | Ark-skills uses a Claude Code plugin with context-discovery — skills read CLAUDE.md at runtime, eliminating hardcoded project config and enabling cross-project reuse. |
| [[Compiled-Insights/Plugin-Versioning-and-Cache-Pitfalls.md|Plugin Versioning & Cache Pitfalls]] | compiled-insight | Claude Code plugin versioning has 4 sources of truth (VERSION, plugin.json, marketplace.json, cache SHA) — any desync causes silent update failure. |
| [[Compiled-Insights/Session-Log-Knowledge-Burial.md|Session Log Knowledge Burial — The Core Vault Problem]] | compiled-insight | Session log knowledge burial is the primary vault problem — 103+ session logs with hard-won ML insights buried in chronological journals, inaccessible to retrieval. |
| [[Compiled-Insights/TaskNotes-MCP-Integration-Model.md|TaskNotes MCP Integration — Architecture & Limitations]] | compiled-insight | TaskNotes MCP is an HTTP endpoint inside Obsidian (not standalone), with limited schema — custom frontmatter requires post-edit or direct markdown write. |
| [[Compiled-Insights/Vault-Hosting-Evolution.md|Vault Hosting Evolution — Submodules to Standalone Repos]] | compiled-insight | Vaults evolved from submodules in ark-skills to standalone repos at ~/.superset/vaults/, symlinked from projects. Worktree branches can get lost during migration. |
| [[Session-Logs/S001-MemPalace-Integration.md|Session: MemPalace Integration for claude-history-ingest]] | session-log | Implemented MemPalace (ChromaDB) backend for claude-history-ingest: Stop hook, installer, SKILL.md rewrite, shipped v1.1.0-1.1.2. |
| [[TaskNotes/00-Project-Management-Guide.md|Project Management Guide]] | moc | How task IDs, statuses, and task notes work in the ark-skills project. |
