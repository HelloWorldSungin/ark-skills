---
title: "Vault Hosting Evolution — Submodules to Standalone Repos"
type: compiled-insight
tags:
  - compiled-insight
  - vault
  - infrastructure
  - ark-onboard
  - symlink
summary: "Vaults evolved from submodules in ark-skills to standalone repos at ~/.superset/vaults/, symlinked from projects. As of v1.11.0 this is /ark-onboard's greenfield default; embedded is an explicit escape hatch."
source-sessions:
  - "[[S005-Ark-Onboard-Centralized-Vault]]"
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-12
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

### Centralized-Symlink Pattern Codified in /ark-onboard v1.11.0

What started as ArkNode-Poly's hand-rolled setup became the `/ark-onboard` greenfield default in v1.11.0 (see [[S005-Ark-Onboard-Centralized-Vault]]). The wizard now creates:

```
~/.superset/vaults/<project>/       # its own git repo
└── .git/, _meta/, TaskNotes/, ...

~/.superset/projects/<project>/
├── vault → ~/.superset/vaults/<project>/   # symlink, git-ignored
├── scripts/setup-vault-symlink.sh          # tracked, canonical
└── <common_git_dir>/hooks/post-checkout    # installed, not tracked
```

Users can opt out of centralized via a Step 1 prompt; the wizard writes `| **Vault layout** | embedded (not symlinked) |` into CLAUDE.md so diagnostics recognize the intentional choice (check #20 is warn-only and returns `pass` when the opt-out row is present).

### $HOME-Portable VAULT_TARGET

The canonical script stores `VAULT_TARGET="$HOME/.superset/vaults/<project>"` (literal `$HOME/` form) — **not** the expanded absolute path. `$HOME` expands at runtime on whichever machine runs the script, so a collaborator who clones the project on their own machine gets a working setup without touching tracked files.

Path inputs are constrained to `$HOME/` prefix (or `~/` which normalizes to `$HOME/`). Users with external drives symlink-in: `ln -s /Volumes/Drive/vaults $HOME/Vaults`, then point the wizard at the `$HOME` path. An earlier draft tracked a `.ark/vault-path` file with machine-specific absolute paths — it poisoned collaborators' clones and was abandoned before v1.11.0.

### Post-Checkout Hook Must Install to Common-Dir

The hook that auto-recreates the `vault` symlink on `git checkout` / `git worktree add` **must** install into `$(git rev-parse --git-common-dir)/hooks/post-checkout` — the main repo's `.git/` that's shared across all worktrees — not the worktree-local `.git/hooks/`. This is the whole reason to prefer symlinks over embedded directories: new worktrees get the vault symlink for free. Installing to the worktree-local hook defeats the purpose. Prior codex-review rounds flagged this as a gotcha; v1.11.0 uses `--git-common-dir` consistently across Greenfield setup, Externalization plan, and Repair flows.

### Externalization Is Plan-File-Only

Moving an existing embedded vault to the centralized layout is destructive: it `rm -rf`s the real directory, copies content to a new repo, replaces with a symlink, and converts sibling worktrees one at a time. `/ark-onboard` **does not** do this inline — it generates `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md` and exits. The user reviews the plan, then runs `/executing-plans` to execute it phase-by-phase. The plan has preflight gates (`git diff --no-index` sibling comparison, empty-dir shape check, uncommitted-content check, target-path-empty check), Phase 1 destructive main-repo, Phase 2 per-sibling worktree with individual confirmation, and phase-specific rollback instructions. Separation of destructive-work-into-plan-file from safe-work-inline is a durable pattern for skill design.

## Evidence

- Conversation `a5ed3c76`: submodule removal (commit `793cc13`)
- Conversation `b4369062`: vault restructuring merge, branch recovery from worktrees
- Conversation `29145231`: vault setup dogfooding inside plugin repo
- [[S005-Ark-Onboard-Centralized-Vault]]: codified pattern as /ark-onboard v1.11.0 greenfield default, externalization plan-file generator, check #20 (warn-only)

## Implications

- When extracting repos from submodules, always verify that all feature branches are preserved on the remote before deleting the submodule.
- New sessions created between restructuring and merge will lack `summary:` fields — run a backfill pass after merging.
- The `./vault/` in ark-skills is the canonical test case for new vault tooling. Test wiki skills here first. (As of 2026-04-12 this vault is itself a candidate for dogfooding the new externalization plan — it's still embedded.)
- The "distill, don't store" philosophy means there's no raw document archive. If provenance matters, link back to the source URL in the vault page.
- Any tracked metadata that encodes filesystem paths should use `$HOME/`-portable form, never expanded absolute paths — otherwise collaborators' clones get poisoned.
- Destructive multi-worktree operations belong in plan files with preflight gates, not inline skill execution. Safe additive operations (like Ark scaffolding) stay inline.
