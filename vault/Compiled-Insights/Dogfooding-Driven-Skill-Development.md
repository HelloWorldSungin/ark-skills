---
title: "Dogfooding-Driven Skill Development"
type: compiled-insight
tags:
  - compiled-insight
  - skill
summary: "The most effective way to develop skills is to use them on the plugin's own repo — wiki-setup grew from 10 to 13 steps after dogfooding."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Dogfooding-Driven Skill Development

## Summary

Using skills on the ark-skills plugin's own repo is the most effective development method. When `/wiki-setup` was invoked to initialize the ark-skills vault, three missing features were discovered that would not have surfaced through spec review alone: Obsidian plugin binary setup, NotebookLM config generation, and a complete CLAUDE.md template in the onboarding guide. The skill grew from 10 to 13 steps as a result.

## Key Insights

### Dogfooding Catches What Specs Miss

The wiki-setup skill was spec'd, codex-reviewed, and plan-approved — yet running it on a real vault exposed three gaps:

1. **Obsidian plugin binary setup** (Step 8-9) — The skill needed to ask "do you have an existing Ark vault to copy plugin binaries from?" and handle both yes (copy `main.js`, `manifest.json`, `styles.css`) and no (manual install later) paths.
2. **NotebookLM config generation** (Step 10) — Template `.notebooklm/config.json` with placeholder notebook ID, persona, and vault_root needed to be part of vault scaffolding.
3. **Complete CLAUDE.md template** — The onboarding guide needed a full copy-paste template with all context-discovery fields, not just a list of required fields.

### Testing Strategy Progression

The recommended testing order for a new plugin with 14 skills:

1. **Smoke test** — Can Claude see the skills? (`/wiki-status` in skills list)
2. **Dry-run read-only skills** — `/wiki-status` and `/wiki-lint` are safe first tests (read vault, report issues, change nothing)
3. **Context discovery validation** — Test against projects with and without CLAUDE.md fields to verify graceful failure messages
4. **Cross-project isolation** — Verify skills read the *current* project's CLAUDE.md, not a cached or wrong one

### The Onboarding Guide as Living Documentation

The onboarding guide (`docs/onboarding-guide.md`) evolved from a minimal checklist to a 7-step comprehensive guide with:
- Full vault structure diagrams for standalone, separate-repo, and monorepo layouts
- Three CLAUDE.md templates (minimal, full, monorepo hub)
- Plugin configuration details (TaskNotes port routing, Obsidian Git setup)
- Troubleshooting section for common failure modes
- Manual verification checklist

This evolution was driven entirely by dogfooding — each gap was discovered by actually trying to onboard the plugin's own repo.

## Evidence

- "The most effective way to develop skills is to use them on the plugin's own repo" — session insight during vault setup
- wiki-setup Step renumbering from 10 to 13 during self-test session
- "I want to set up a vault for this repo, a good way to test how the setup process is like for a brand new project and vault" — user intent
- PR #2: "feat: initialize vault with Obsidian, TaskNotes, and NotebookLM" — the dogfooding PR itself

## Implications

- Every new skill should be tested on the ark-skills repo first before release — it's the cheapest real-world test.
- Read-only skills (`/wiki-status`, `/wiki-lint`) are the safest smoke tests and should always be tested before write operations.
- The onboarding guide should be updated every time dogfooding reveals a gap — it's the skill plugin's most user-facing artifact.
- Spec review (/codex) catches architectural errors; dogfooding catches UX and completeness gaps. Both are needed.
