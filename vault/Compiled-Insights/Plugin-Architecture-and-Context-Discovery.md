---
title: "Plugin Architecture & Context-Discovery Pattern"
type: compiled-insight
tags:
  - compiled-insight
  - plugin
  - context-discovery
  - skill
summary: "Ark-skills uses a Claude Code plugin with context-discovery — skills read CLAUDE.md at runtime, eliminating hardcoded project config and enabling cross-project reuse."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Plugin Architecture & Context-Discovery Pattern

## Summary

The ark-skills plugin solves skill duplication across ArkNode-AI and ArkNode-Poly by distributing 14 shared skills as a Claude Code plugin with user-scoped skills. The critical design decision is the **context-discovery pattern**: no skill contains hardcoded project names, vault paths, or task prefixes. Every skill begins with a "Project Discovery" step that reads the current project's `CLAUDE.md` to extract runtime configuration.

## Key Insights

### Distribution Model: Claude Code Plugin Over Alternatives

Submodules and symlinks were considered and rejected. Submodules cause version drift between consumer projects. Symlinks require manual setup and break cross-platform. A Claude Code plugin with user-scoped skills makes all 14 skills automatically available to every project without per-project installation.

### Context-Discovery Eliminates Configuration Files

Instead of `.env` files or config JSONs, skills read project CLAUDE.md at runtime. This works because CLAUDE.md is already the authoritative source of project identity — it declares task prefix, vault path, deployment targets, and infrastructure details. Skills that need infrastructure-specific behavior (container drift checks, dashboard sync) only activate when CLAUDE.md declares those targets.

### Monorepo Discovery Precedence

For monorepos like ArkNode-AI (which is a hub pointing to sub-project CLAUDEs), discovery follows a strict precedence:
1. Read CLAUDE.md in current working directory
2. If it's a hub, follow the link matching the active project
3. Extract config from the most specific CLAUDE.md
4. If a required field is missing, surface an error rather than guessing

### obsidian-wiki Skill Adaptation Was Heavier Than Expected

Initial assumption: symlink most obsidian-wiki skills. Reality: 9 of 10 skills need copy-and-adapt due to three incompatibilities:
- **Folder structure**: obsidian-wiki expects `concepts/`, `entities/`, `skills/`. Ark vaults use domain-specific folders.
- **Frontmatter schema**: obsidian-wiki uses `sources:`, `provenance:`, `category:`. Ark uses `source-sessions:`, `source-tasks:`, `type:`.
- **Config mechanism**: obsidian-wiki reads `.env`. Ark uses context-discovery from CLAUDE.md.

Only `cross-linker` was initially considered generic enough, but it too needed adaptation due to `.env` and `log.md` dependencies. All 10 skills were ultimately copied.

### Submodule Reference Architecture Was Abandoned

The original design kept obsidian-wiki as a submodule for "reference/audit" to allow periodic upstream diffing. All 7 submodules were eventually removed because they added unnecessary coupling. Upstream tracking can be done with simple git remote commands instead.

### Iterative Skill Development by Dogfooding

The most effective skill development pattern: use the skill on the plugin's own repo. The wiki-setup skill was invoked to set up the ark-skills vault, and three missing features were discovered during that process (Obsidian plugin setup, NotebookLM config, complete CLAUDE.md template). The vault at `./vault/` serves as the canonical test case for all new vault tooling.

### Skill Scoping Is Critical

Skills that glob across all projects are a foot-gun in a multi-project ecosystem. The original `claude-history-ingest` scanned all 15 project directories under `~/.claude/projects/`. This was fixed to derive the project-specific directory from `$PWD` and scope all reads to that single directory.

## Evidence

- Design spec: `docs/superpowers/specs/2026-04-07-ark-skills-plugin-design.md`
- Memory file: `project_ark_skills_plugin.md` (key decisions documented 2026-04-07)
- Vault audit: `docs/vault-audit.md` (confirmed vaults already outperform obsidian-wiki defaults in cross-linking and frontmatter coverage)

## Implications

- New projects joining the ecosystem only need: install plugin, configure CLAUDE.md, and configure tasknotes MCP. No skill-level configuration required.
- Skills should never import project-specific constants. If a skill needs project context, it must use discovery.
- When diffing against upstream obsidian-wiki for improvements, expect most changes to need adaptation for the Ark frontmatter schema.
