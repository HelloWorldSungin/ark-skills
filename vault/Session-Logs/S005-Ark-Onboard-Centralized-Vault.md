---
title: "Session 5: /ark-onboard Centralized Vault Recommendation (v1.11.0)"
type: session-log
tags:
  - session-log
  - S005
  - skill
  - ark-onboard
  - centralized-vault
  - symlink
  - worktree
  - migration
  - release
summary: "Shipped /ark-onboard centralized-vault default (symlinked vault repo at $HOME/.superset/vaults/<project>), externalization plan-file generator, check #20 (warn-only), downstream skill notes. v1.10.1 → v1.11.0. PR #13."
session: "S005"
status: complete
date: 2026-04-12
prev: "[[S004-Ark-Workflow-Split]]"
epic: ""
source-tasks: []
created: 2026-04-12
last-updated: 2026-04-12
---

# Session 5: /ark-onboard Centralized Vault Recommendation (v1.11.0)

## Objective

Extend `/ark-onboard` to recommend a **centralized vault** (externalized git repo + symlink) as the greenfield default, with an explicit embedded escape hatch. Mirror ArkNode-Poly's production pattern so all Ark projects get worktree-safe, Obsidian-app-safe vaults by default.

## Context

S004 finished the `/ark-workflow` v2 progressive-disclosure split. This session picked up the next piece of plugin work: the `/ark-onboard` wizard still defaulted to `./vault/` embedded layout, while ArkNode-Poly had evolved to a symlinked-standalone pattern months prior (see [[Vault-Hosting-Evolution]]). The gap meant new projects onboarded with the inferior pattern, and existing embedded projects had no safe externalization path.

Branch `vault-symlink` already contained the approved spec (revision 4, codex round-4 PASS at commit `dd80baa`) and the implementation plan (`docs/superpowers/plans/2026-04-12-ark-onboard-centralized-vault.md`). This session's job: execute the plan, verify, and ship.

## Work Done

### Subagent-driven execution (15 tasks, 14 commits)

Used `superpowers:subagent-driven-development` to dispatch a fresh implementer subagent per task, with two-stage review (spec compliance → code quality) between tasks. Commits `0245400`..`bdeaf0e`:

| Task | Commit | Scope |
|------|--------|-------|
| 1 | `0245400` | Centralized vault terminology + layout diagram |
| 2 | `4085e03` | Embed `setup-vault-symlink.sh` + post-checkout hook templates |
| 3 | `77d0e55` | State-detection flags (`IS_SYMLINK`, `SCRIPT_EXISTS`, `SYMLINK_DRIFT`, `EMBEDDED_OPTOUT`) + `REPAIR_REASON` routing |
| 4 | `6eda793` | Greenfield Step 1 rewrite (centralized default + embedded escape hatch + `$HOME/` path constraint) |
| 5 | `de92181` | Greenfield Steps 2a–2d (vault repo init, symlink, automation install, GitHub remote offer) |
| 6 | `a6c7ec3` | Step 17 commit split (centralized: vault-repo + project-repo; embedded: legacy single commit) |
| 7 | `06e7d1c` | Embedded opt-out row `\| **Vault layout** \| embedded (not symlinked) \|` in CLAUDE.md writer |
| 8 | `cdb7508` | Reframe "Non-Ark Vault (Migration)" → "Ark Scaffolding + Externalization Offer" |
| 9 | `eb3cdf8` | Externalization path + plan-file template (Phases 0–3 + rollback) |
| 10 | `b781c2c` | Repair cases (broken symlink, drift, script backfill, hook reinstall) |
| 11 | `3eb9a9f` | Healthy-classification rule: "all pass" → "no fail (warn is OK)" |
| 12 | `2c1e5ce` | Check #20 vault-externalized (warn-only, Standard tier) + scorecard mirror |
| 13 | `65d9c24` | Downstream awareness notes (`/notebooklm-vault`, `/wiki-update`, `/codebase-maintenance`, `/ark-workflow`) |
| 14 | — | Manual smoke test on scratch dir (no commit per plan) |
| 15 | `bdeaf0e` | VERSION 1.10.1 → 1.11.0 + CHANGELOG + plugin.json + marketplace.json |

### Cleanup commit (post-plan, found in final review)

`superpowers:code-reviewer` final cross-task pass surfaced 3 residual issues the plan hadn't explicitly enumerated. Fixed in commit `ab62949`:

1. **12 stale "19" references** (8 in `/ark-onboard`, 4 in `/ark-health`) — text still said "Run all 19 checks" after adding check #20, which would cause an agent running the full diagnostic to skip the new check. Self-defeating.
2. **Tilde-expansion bug** in `'~/'*) USER_PATH="\$HOME/${USER_PATH#~/}"` — verified empirically: bash performs tilde expansion on the `~/` pattern before parameter stripping, so `${USER_PATH#~/}` returns the original `~/path` unchanged. Result: `$HOME/~/path` (broken). Fix: quote the tilde: `${USER_PATH#'~/'}`.
3. **Migration step count** — section header said "14-step flow" but Step 15 (externalization offer) was added in Task 8.

### Smoke test (Task 14)

Manually walked through Greenfield + Repair + Check #20 on a scratch `/tmp` directory. All 8 assertions passed:
- symlink, script, hook, portable `VAULT_TARGET`, `.gitignore`, sync-state created
- `git worktree add` auto-created the `vault` symlink in the new worktree (via the common-dir hook)
- Removing symlink → running `bash scripts/setup-vault-symlink.sh` recreates it
- Check #20 PASS when symlink matches `VAULT_TARGET`
- Check #20 WARN when vault becomes a real directory without opt-out
- Check #20 PASS when CLAUDE.md opt-out row is added

### Ship

`/ship` workflow — pushed `vault-symlink`, opened PR #13. 21 commits (6 pre-session spec/plan docs + 14 implementation + 1 cleanup). 12 files, +3644 / -48.

## Decisions Made

### `$HOME/`-portable `VAULT_TARGET` as a hard constraint

The wizard stores `VAULT_TARGET="$HOME/.superset/vaults/<project>"` (literal `$HOME/` form) in the tracked `scripts/setup-vault-symlink.sh`, not the expanded absolute path. Rationale: an earlier draft used a `.ark/vault-path` metadata file that captured machine-specific absolute paths, which poisoned collaborators' clones on different users. The `$HOME/` form expands at runtime on whichever machine runs the script. **Path inputs are rejected if they don't start with `$HOME/` or `~/`** — users with external drives must symlink-in (`ln -s /Volumes/Drive/vaults $HOME/Vaults`) rather than pass the external path directly.

### Post-checkout hook installed into common-dir, not worktree-local

`git rev-parse --git-common-dir` resolves to the main repo's `.git/` (shared across all worktrees). Installing the hook there means `git worktree add` automatically creates the `vault` symlink in new worktrees — which was the whole reason to prefer symlinks over embedded directories. Installing to the worktree-local `.git/hooks/` would have defeated the purpose. Prior codex review rounds flagged this as a gotcha; the implementation uses `--git-common-dir` consistently in Greenfield Step 2c, Externalization plan Step 1.11, and Repair Case E.

### Externalization is plan-file-only; Ark scaffolding stays inline

The prior "Migration" section conflated two unrelated operations: (a) **Ark scaffolding** — adding `_meta/`, `TaskNotes/`, etc. to an embedded non-Ark vault (safe, additive, inline); (b) **Externalization** — moving an embedded vault out to its own repo + symlink (destructive, needs preflight + rollback). Split: scaffolding stays in the "Non-Ark Vault" path's 15-step flow; externalization generates `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md` via the new "Externalization Plan Generation" path, and the user runs it via `/executing-plans` after review. The plan file has Phase 0 preflight (git-diff sibling comparison + empty-dir shape check + uncommitted-content check + target-path-empty check), Phase 1 destructive main-repo + vault-target, Phase 2 per-sibling worktree conversion with individual confirmation, Phase 3 manual follow-ups, plus phase-specific rollback instructions.

### Check #20 is warn-only, healthy rule relaxed

Check #20 (vault-externalized) **never returns `fail`** — an embedded vault with explicit opt-out is a valid choice, not a failure. To make this work, the Healthy tier rule changed from "all Critical + Standard pass" to "no Critical + Standard fail (warn is OK)" in both `/ark-onboard` and `/ark-health`. Check 10 (index staleness) was already warn-only but was being blocked by the old rule. This change unblocks warn-returning advisories from demoting the user's tier.

### Two-stage review between tasks

Used `superpowers:subagent-driven-development`'s two-stage review: **spec compliance reviewer** (did the implementer build exactly what the plan specified?) before **code quality reviewer** (is the implementation well-built?). Each reviewer had independent fresh context. The spec reviewer caught placement and verbatim-contract issues; the code reviewer caught the tilde-expansion bug, `eval` trust-boundary questions, and `.notebooklm/config.json` dual-write gap. Without the split, the reviewer tends to conflate "matches the plan" with "is well-engineered."

## Issues & Discoveries

### Bash tilde expansion inside parameter stripping is a footgun

`${VAR#~/}` does NOT strip a literal `~/` prefix. Bash performs tilde expansion on the unquoted `~/` in the pattern BEFORE parameter substitution runs, so the pattern becomes `/Users/sunginkim/` which doesn't match. `${VAR#'~/'}` (quoted tilde) strips the literal `~/` correctly. Verified:

```bash
$ USER_PATH="~/Vaults/test"
$ echo "${USER_PATH#~/}"        # broken — returns "~/Vaults/test"
$ echo "${USER_PATH#'~/'}"      # correct — returns "Vaults/test"
```

This bug was in the approved spec (codex round-4 PASS) and propagated through two task bodies before the final code-reviewer caught it. Codex reviews do not execute code — spec approval is not the same as behavioral verification.

### Spec gaps not enumerated in the plan surface only at cross-task review

The per-task reviewers passed each task individually — but they reviewed against the **task**'s local requirements, not against the **feature**'s coherent completeness. The final cross-task reviewer (`superpowers:code-reviewer`) found issues that span tasks: the "all 19 checks" phrasing wasn't enumerated in Task 12 (which only explicitly added check #20), leaving 12 stale references across the codebase that defeat the new check. Lesson: per-task review is necessary but not sufficient. A final cross-task pass is non-optional for any multi-task feature.

### `eval "echo $USER_PATH"` pattern used throughout

The wizard uses `eval` to expand `$HOME` in user-supplied paths. Safer alternative is parameter expansion: `"${USER_PATH/#\$HOME/$HOME}"`. The `eval` pattern survived into v1.11.0 — flagged as a follow-up. Low practical risk (wizard reads from a local trusted script it wrote itself), but worth hardening.

### Greenfield NotebookLM config write is incomplete

The layout diagram envisions two `.notebooklm/config.json` files: one in the vault repo (`vault_root: "."`) and one in the project repo (`vault_root: "vault"`). Step 15 writes only the vault-repo config. Step 17 does `git add .notebooklm/config.json 2>/dev/null` in the project repo, which silently succeeds with no file added. The Externalization plan at Step 1.3 correctly handles both. The Greenfield gap is a follow-up.

## Next Steps

Ordered by priority:

1. **Merge PR #13** — review outstanding. After merge, bump VERSION to trigger marketplace refresh on users' machines. Check `/ark-onboard` dogfoods cleanly on the ark-skills repo itself (which is still embedded).
2. **Greenfield Step 15 dual-config fix** — write both `.notebooklm/config.json` files (project repo + vault repo). Current gap means fresh-onboarded centralized-vault projects lack the project-root config that `/notebooklm-vault`'s awareness note expects.
3. **Harden `eval "echo $USER_PATH"` → parameter expansion** — replace in Tasks 3/4/5/10/12 with `"${USER_PATH/#\$HOME/$HOME}"`. Consistency across wizard + drift-check + repair.
4. **Externalize the ark-skills vault itself** — this project still has an embedded `vault/`. After PR #13 merges, dogfood the new externalization plan to move `vault/` → `~/.superset/vaults/ark-skills/` and symlink. Confirms end-to-end the path the wizard generates.
5. **Tilde-bug follow-up** — review whether any existing ArkNode-Poly or Trading-Signal-AI setup scripts have the same `${var#~/}` pattern. Unlikely (those were hand-rolled), but worth a grep sweep.
