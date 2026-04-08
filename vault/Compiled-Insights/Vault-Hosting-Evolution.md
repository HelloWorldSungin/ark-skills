---
title: "Vault Hosting Evolution — Submodules to Standalone Repos"
type: compiled-insight
tags:
  - compiled-insight
  - vault
  - infrastructure
summary: "Vaults evolved from submodules in ark-skills to standalone repos at ~/.superset/vaults/, symlinked from projects. Worktree branches can get lost during migration."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Vault Hosting Evolution — Submodules to Standalone Repos

## Summary

The Obsidian vaults went through two architectural transitions: (1) from submodules inside ark-skills to standalone repos at `~/.superset/vaults/`, symlinked from project directories, and (2) the ark-skills repo itself adopted its own vault at `./vault/` for dogfooding. Along the way, work done in worktree branches became invisible when repos were extracted, requiring manual branch recovery.

## Key Insights

### Submodules Removed for Independence

The original design kept 7 submodules (ArkNode-AI, ArkNode-Poly, both Obsidian vaults, linear-updater, tasknotes, obsidian-wiki) inside ark-skills for reference and audit purposes. This was abandoned because:
- Submodules added unnecessary coupling between repos
- obsidian-wiki upstream diffing can be done with simple git remote commands, not submodules
- Vault repos need independent commit histories for Obsidian Git sync

### Standalone Vaults with Symlinks

Vaults now live at `~/.superset/vaults/{VaultName}/` as standalone git repos. Project directories symlink to them:
```
~/.superset/projects/ArkNode-Poly/vault → ~/.superset/vaults/ArkNode-Poly/
```

This lets Obsidian open the vault directly while projects reference it via the symlink.

### Worktree Branches Can Get Lost During Migration

The vault restructuring work (10+ commits per vault with summaries on all pages, _meta directory, taxonomy, lint fixes) was done in old submodule repos inside a git worktree at `~/.superset/worktrees/ark-skills/`. When submodules were extracted to standalone repos, the `vault-restructure` branches were NOT carried over — standalone repos only had `master`.

**Fix:** Push branches from old worktree paths, then fetch in standalone repos.

**Lesson:** Always push feature branches to remote before changing repo hosting.

### Vault Restructuring Merges Cleanly

The restructuring branch added `summary:` frontmatter to 300+ pages (AI) and 175+ pages (Poly). Meanwhile, master had new sessions and content changes. Git auto-merged all conflicts because frontmatter additions and content body changes were in different file sections. Zero manual conflict resolution required.

### Plugin Repo Dogfooding

The ark-skills plugin repo has its own vault at `./vault/` (not a submodule, not a symlink). This was a deliberate choice to dogfood the vault setup process — the plugin's own vault tests the wiki-setup skill for new projects.

### External Content Goes Through Skills, Not Raw Drops

There's no `_sources/` folder (intentionally deferred). External articles are distilled directly into vault pages in the appropriate domain folder (`Research/`, `Architecture/`, etc.) via `/wiki-ingest`. Raw source material is never stored — the vault philosophy is "distill, don't store."

### New Content After Restructuring Needs Backfill

Sessions added to master after the restructure branch was created won't have `summary:` fields. These need backfill via `/wiki-update` or the summary generation script after merging.

## Evidence

- Conversation `a5ed3c76`: submodule removal (commit `793cc13`)
- Conversation `b4369062`: vault restructuring merge, branch recovery from worktrees
- Conversation `29145231`: vault setup dogfooding inside plugin repo

## Implications

- When extracting repos from submodules, always verify that all feature branches are preserved on the remote before deleting the submodule.
- New sessions created between restructuring and merge will lack `summary:` fields — run a backfill pass after merging.
- The `./vault/` in ark-skills is the canonical test case for new vault tooling. Test wiki skills here first.
- The "distill, don't store" philosophy means there's no raw document archive. If provenance matters, link back to the source URL in the vault page.
