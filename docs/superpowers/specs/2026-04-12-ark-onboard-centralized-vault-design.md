# `/ark-onboard` Centralized Vault Recommendation — Design Spec

**Date:** 2026-04-12
**Branch:** vault-symlink
**Status:** Draft

## Problem

`/ark-onboard` greenfield currently defaults to creating the Obsidian vault as `./vault/` inside the project repo. This is the wrong default for the Ark ecosystem:

1. **Worktrees cannot share vault content.** Each `git worktree add` produces an independent `vault/` tree. Session logs and task notes written in one worktree don't appear in another.
2. **Obsidian app mismatch.** The Obsidian desktop app opens exactly one vault at a time. Agents running in worktrees read from their local `vault/` directory, but the app is pointed at the main repo's copy — so `obsidian-cli` searches return stale content from the agent's perspective.
3. **NotebookLM sync state diverges.** Each worktree has its own `.notebooklm/sync-state.json`, causing duplicate uploads unless the sync script is patched (see ArkNode-Poly commit `42937e6`).
4. **Session log collisions.** Two worktrees can create session logs with the same timestamp-based filename.

ArkNode-Poly solved this on 2026-04-01 by externalizing the vault into its own git repo at `~/.superset/vaults/ArkNode-Poly/` and symlinking `vault` into every project/worktree directory. The pattern works — but `/ark-onboard` does not know about it, so every new Ark project recreates the embedded-vault anti-pattern from day one.

## Goals

- Make the centralized-vault layout the default for all new Ark projects (Greenfield path).
- Offer migration assistance for projects that already have an embedded vault (Migration path).
- Repair broken symlinks / missing automation after a reclone (Repair path).
- Audit `Healthy`-state projects for the anti-pattern (Healthy path — new check #20).
- Keep the one-off `embedded vault` choice available as an explicit escape hatch.
- Do not break ArkNode-Poly, which already runs this pattern by hand.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | All four `/ark-onboard` state paths (No Vault, Non-Ark Vault, Partial Ark, Healthy) | Centralized vault is the canonical Ark convention; any embedded vault should surface as a warning somewhere. |
| Greenfield aggressiveness | Default yes with explicit `y/N` escape | Other defaults in `/ark-onboard` already assume the Ark convention (tier, layout); centralized vault fits the same pattern. |
| Migration depth | Plan file only, consumed by `/executing-plans` | Migration touches committed vault content and multiple worktrees simultaneously. A plan file gates destructive steps behind review. |
| Greenfield depth | Full auto, one confirmation | Greenfield has no committed state to destroy, so the same auto-execute model as the rest of `/ark-onboard` greenfield applies. |
| GitHub remote | Optional, offered after local `git init` | `gh repo create` is nice-to-have, not required for the symlink/hook logic to work. Offer only if `gh` is installed and authenticated. |
| Centralized-location default | Prompt with smart default (`~/.superset/vaults/<project>/` for superset users, `~/Vaults/<project>/` otherwise) | Not every Ark user runs the superset CLI; hardcoding `~/.superset/` would surprise them. Detection keeps the default consistent with the user's existing toolchain. |
| Worktree symlink automation | Three layers: `scripts/setup-vault-symlink.sh` (tracked, single source of truth), `.git/hooks/post-checkout` (local, reinstalled by `/ark-onboard`), `.superset/config.json` setup entry (for superset users) | The post-checkout hook fires on `git worktree add` universally. The setup script is version-controlled so logic is reviewable. The superset hook preserves existing ArkNode-Poly behavior. |
| `.vault-path` fallback file (CT110 / tinyAGI) | Not handled by `/ark-onboard` directly | Environment-specific concern. The script already includes the `~/.tinyagi/vaults/<project>/` fallback for production deploys. |
| NotebookLM config duality | Project copy uses `vault_root: "vault"`, vault copy uses `vault_root: "."` | Matches the 2026-04-01 pattern. Both resolve to the same directory. |
| `sync-state.json` location | Vault repo only | Shared across environments; prevents duplicate uploads. |

## Architecture

### Directory layout

```
~/.superset/vaults/<project>/          (centralized vault — its own git repo)
├── .git/
├── .obsidian/
├── .notebooklm/
│   ├── config.json              (vault_root: ".")
│   └── sync-state.json          (lives here only)
├── _meta/, _Templates/, _Attachments/
├── TaskNotes/
├── 00-Home.md
└── <ProjectDocs>/                (monorepo layout)  OR  flat (standalone)

<project-repo>/
├── vault → ~/.superset/vaults/<project>/   (symlink, git-ignored)
├── .notebooklm/config.json        (vault_root: "vault", tracked)
├── .gitignore                      (contains `vault`)
├── .git/hooks/post-checkout        (installed, not tracked)
├── .superset/config.json           (setup+teardown entries — if superset project)
└── scripts/setup-vault-symlink.sh  (tracked, single source of truth)
```

### Centralized-location default detection

```bash
if [ -d "$HOME/.superset" ]; then
  DEFAULT_CENTRALIZED_ROOT="$HOME/.superset/vaults/<project>"
else
  DEFAULT_CENTRALIZED_ROOT="$HOME/Vaults/<project>"
fi
```

User is prompted with this default; can accept with Enter or override.

### `scripts/setup-vault-symlink.sh` — single source of truth

Parameterized on `<project_name>` and `<centralized_root>` at generation time. Logic:

1. If `vault` is a valid symlink and target exists → `exit 0`.
2. If `vault` is a broken symlink (link exists, target missing) → `rm vault`, continue.
3. If `vault` is a real directory → `echo ERROR` and `exit 1` (indicates unfinished migration).
4. If `<centralized_root>/<project>` exists → `ln -s <centralized_root> vault`, `exit 0`.
5. If `~/.tinyagi/vaults/<project>` exists → `ln -s <tinyagi_path> vault`, `exit 0`.
6. Else → print clone instructions, `exit 1`.

The script is idempotent. Both the post-checkout hook and the superset setup hook call it.

### `.git/hooks/post-checkout`

```bash
#!/usr/bin/env bash
# Fires on branch checkouts (including git worktree add).
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
```

Installed with `chmod +x`. Since `.git/hooks/` is not tracked by git, this must be reinstalled after reclones — `/ark-onboard`'s Repair path handles that.

**Worktree note:** when `/ark-onboard` runs inside a worktree, the hook must be installed in the common `.git/hooks/` directory (shared across all worktrees via `commondir`), not the worktree's local `.git/` pointer-file. Use `git rev-parse --git-common-dir` to find the right path.

### `.superset/config.json` setup/teardown entries (if `.superset/` exists)

```json
{
  "setup": [
    "...existing entries...",
    "bash scripts/setup-vault-symlink.sh"
  ],
  "teardown": [
    "...existing entries...",
    "[ -L vault ] && rm vault || true"
  ]
}
```

## Wizard Flow Changes

### Greenfield — diff against current SKILL.md

Current Greenfield Step 1 asks for four fields; the `vault path (default ./vault/)` prompt is replaced with:

```
[1] Where should the centralized vault live?
    Default: ~/.superset/vaults/<project>/
    [press Enter to accept, or type a path]

[2] (rare) Use embedded vault inside the project repo instead? [y/N]
    The centralized layout lets multiple worktrees and the Obsidian
    app share one source of truth. Only pick embedded if you
    explicitly want the vault committed to the project repo.
```

If the user answers `y` to prompt 2, the wizard falls back to the legacy `./vault/` path and skips all symlink/hook logic. All other steps run as before.

Otherwise, **four new steps** are inserted between current Step 2 (Python check) and Step 3 (Create vault directories):

- **Step 2a — Create centralized vault repo.** `mkdir -p <centralized_root>`; `cd` in; `git init`; write `.gitignore` containing Obsidian per-user files (`workspace.json`, `workspace-mobile.json`, `graph.json`, `plugin data.json`).
- **Step 2b — Create symlink.** `ln -s <centralized_root> <repo>/vault`; append `vault` to `<repo>/.gitignore`.
- **Step 2c — Install automation.** Write `<repo>/scripts/setup-vault-symlink.sh` (templated on project name and centralized root); install `<common_git_dir>/hooks/post-checkout` with `chmod +x`. If `<repo>/.superset/config.json` exists, append setup/teardown entries.
- **Step 2d — Offer GitHub remote.** If `gh` CLI is installed and `gh auth status` succeeds, prompt: `Create a GitHub repo for this vault now? [y/N]`. On yes, `gh repo create --private <project>-vault --source=<centralized_root> --push`. On no (or if `gh` unavailable), print the one-line command for later use.

All subsequent greenfield steps (3 through 18 — directory creation, `00-Home.md`, `_meta/*`, TaskNotes scaffolding, index generation) run **inside the centralized vault repo**, not the project repo. The final `git add . && git commit -m "Initial vault scaffolding"` happens in the vault repo.

The existing NotebookLM step writes `<repo>/.notebooklm/config.json` with `vault_root: "vault"` and additionally writes `<centralized_root>/.notebooklm/config.json` with `vault_root: "."`.

### Migration — new section

Triggered when state detection finds `vault/` is a real directory (not a symlink) containing Ark artifacts. Wizard does NOT execute — it generates a plan file.

Prompt sequence:
```
Detected: vault/ is committed to this repo as a real directory.
The Ark convention is to externalize it. I'll generate a migration plan
(no destructive actions). You can review and run it via /executing-plans.

Centralized location for the extracted vault: <default>  [Enter to accept]
Create a GitHub repo for the vault? [y/N]
```

The wizard then writes `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`, parameterized with the detected project name, centralized root, sibling worktree paths, and NotebookLM config locations. The plan mirrors ArkNode-Poly's 14-step migration (2026-04-01):

1. Clone target location (or `git init` at `<centralized_root>`).
2. Copy existing `vault/` contents into `<centralized_root>`.
3. Copy `.notebooklm/config.json` into vault, update `vault_root: "."`.
4. Move `.notebooklm/sync-state.json` into vault (if it exists).
5. `cd <centralized_root> && git add . && git commit`.
6. (Optional) `gh repo create` and push.
7. `git rm -r --cached vault/` in project repo.
8. Append `vault` to project `.gitignore`.
9. Verify project `.notebooklm/config.json` has `vault_root: "vault"`.
10. `rm -rf vault/ && ln -s <centralized_root> vault`.
11. Write `scripts/setup-vault-symlink.sh`, install post-checkout hook, update `.superset/config.json` if present.
12. Update `CLAUDE.md` to note the symlink convention.
13. For each sibling worktree: `rm -rf <worktree>/vault && ln -s <centralized_root> <worktree>/vault`.
14. Reopen `<centralized_root>/` in the Obsidian app (close old vault first — manual step).

Each step includes the exact command to run and a rollback note where applicable.

Wizard prints the plan path, lists sibling worktrees that will be touched, and exits. No filesystem changes.

### Repair — new branch

Triggered on Partial Ark when diagnostic finds any of:

- `vault` missing entirely, OR
- `vault` is a broken symlink, OR
- `.git/hooks/post-checkout` missing/non-executable, OR
- `scripts/setup-vault-symlink.sh` missing.

For each missing piece, prompt `Fix [item]? [Y/n]` and either recreate it (if `<centralized_root>` already holds the vault) or print clone instructions and skip. All fixes are idempotent.

**Determining `<centralized_root>` in Repair flow** (in this order):

1. If `vault` is a broken symlink: `readlink vault` gives the original target. Check whether it exists now (vault repo may have been restored); if not, treat it as the intended path and print `git clone <remote> <target>` instructions.
2. Else if `scripts/setup-vault-symlink.sh` exists: grep the hardcoded `VAULT_TARGET` value.
3. Else if `.superset/config.json` exists: parse the setup-hook command.
4. Else: prompt the user using the same smart default as Greenfield.

No plan file — these are low-risk, non-destructive operations.

### Healthy — audit check

Add one check to the diagnostic:

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| **20** | Vault externalized | Standard | `vault` is a symlink (not a real directory), OR CLAUDE.md explicitly declares `embedded-vault: true` |

Status options: `pass` (symlink), `warn` (real directory), `skip` (embedded opted-in).

`/ark-onboard` surfaces a `warn` as: "Vault is embedded inside the project repo. Run `/ark-onboard` and select the externalize-vault plan to migrate." `/ark-health` picks this up automatically since the check definitions are synced between the two skills.

Check count rises from 19 → 20.

### State → action summary

| Detected State | Action |
|---|---|
| No Vault (greenfield) | Centralized default → full-auto setup + hook install |
| Non-Ark Vault (real dir, no Ark artifacts) | Normal Ark migration runs inside embedded dir, followed by externalization plan file |
| Partial Ark (symlink broken / hook missing / script missing) | Repair prompts + idempotent fixes |
| Partial Ark (real `vault/` with Ark artifacts) | Externalization plan file |
| Healthy (symlink present) | Check 20 passes |
| Healthy (real `vault/` with Ark artifacts) | Check 20 warns, offer externalization plan |

## Files Created or Modified

| File | Greenfield | Migration | Repair | Healthy |
|------|-----------|-----------|--------|---------|
| `<centralized_root>/` (vault repo) | create + `git init` + initial commit | via plan | — | — |
| `<repo>/vault` symlink | create | via plan | recreate | — |
| `<repo>/.gitignore` | append `vault` | via plan | verify | — |
| `<repo>/.git/hooks/post-checkout` | install | via plan | install if missing | — |
| `<repo>/scripts/setup-vault-symlink.sh` | write | via plan | write if missing | — |
| `<repo>/.superset/config.json` | append entries (if exists) | via plan | — | — |
| `<centralized_root>/.notebooklm/config.json` | write (`vault_root: "."`) | via plan | — | — |
| `<repo>/.notebooklm/config.json` | write (`vault_root: "vault"`) | via plan | — | — |
| `<repo>/CLAUDE.md` | normal greenfield write | via plan | — | — |
| `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md` | — | create | — | create on demand |

## Edge Cases

| Edge case | Handling |
|-----------|----------|
| `/ark-onboard` run from inside a worktree | Resolve common `.git` via `git rev-parse --git-common-dir`; install hook there. |
| Centralized dir exists and is empty | Treat as orphan from a prior failed run: prompt user to delete + retry or pick a different path. |
| Centralized dir exists with content from a different project | Refuse; compare `00-Home.md` title and `.notebooklm/config.json` to confirm mismatch. Never overwrite. |
| User types a centralized path inside the project repo | Refuse — defeats the purpose. |
| Centralized path parent doesn't exist | `mkdir -p` silently; confirm before creating. |
| `vault` symlink points to the wrong location | Repair flow: remove stale symlink, recreate. |
| `gh` CLI not installed or not authenticated | Skip the remote prompt. Print one-liner for later. |
| Project repo isn't a git repo yet | Existing Greenfield prereqs offer `git init` first. |
| Centralized path is on a network mount / external drive | Warn about mount availability; continue. |
| ArkNode-Poly (already on this pattern) running `/ark-onboard` | State detection classifies as Healthy with symlink → check 20 passes → no changes made. |

## Failure Modes

- **Symlink creation fails** (permission denied, etc.): print the `ln` error verbatim, abort the wizard. Do not continue with partial state.
- **Post-checkout hook install fails** (write-denied on `.git/hooks/`): abort, surface the error. Do not claim success.
- **Post-install verification.** After installation, run `test -L vault && test -e vault && test -x <common_git>/hooks/post-checkout && test -f scripts/setup-vault-symlink.sh`. If any check fails, wizard reports the specific step.
- **Migration plan partial execution**: `/executing-plans` handles recovery. Plan includes explicit rollback notes per destructive step.
- **`gh repo create` fails** (name taken, auth): keep local init state; print error + manual-create instructions. Do not roll back.
- **Orphan centralized dir from prior failed greenfield**: detection finds it on second run; user prompted to delete or choose new path. No auto-overwrite.

## Downstream Skill Updates

| Skill | Change |
|-------|--------|
| `/ark-health` | Add check #20 (vault-is-symlink). Count rises 19 → 20. Sync with `/ark-onboard` shared diagnostic section. |
| `/ark-onboard` | All changes in this spec. |
| `/notebooklm-vault` | Confirm it reads config from project's `.notebooklm/` first, falls back to `<vault>/.notebooklm/`, and resolves `sync-state.json` inside the vault. Add note about centralized-vault assumption. |
| `/wiki-update` | Session log filenames should include an environment prefix (`mac-`, `ct110-`) when `vault` is a symlink (cross-env collision prevention). |
| `/codebase-maintenance` | Add note: "When vault is symlinked, commit/push vault changes in the vault repo, not the project repo." |
| `/ark-workflow` | When detection finds embedded `vault/`, surface externalize-vault as a recommended next step. |

## Testing

### Greenfield — happy path

1. Fresh empty git repo; run `/ark-onboard`; accept all defaults.
2. Verify `<centralized_root>` exists with `.git/` and Ark artifacts.
3. Verify `vault` symlink resolves, `vault` present in `.gitignore`, `.git/hooks/post-checkout` executable, `scripts/setup-vault-symlink.sh` tracked.
4. `git worktree add ../test-wt` → verify `../test-wt/vault` symlink auto-created.
5. `ls <centralized_root>/.notebooklm/` → `config.json` and `sync-state.json` present.

### Greenfield — escape hatch

1. Fresh repo; answer `y` to "use embedded vault?"
2. Verify `vault/` is a real directory; no symlink; no post-checkout hook; no `setup-vault-symlink.sh`; `vault/` NOT in `.gitignore`.

### Migration

1. Repo with pre-existing `vault/` dir + Ark artifacts; run `/ark-onboard`.
2. Verify plan file at `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`, parameterized with correct project name and centralized root.
3. Verify no filesystem changes beyond creating the plan file.
4. Pipe plan to `/executing-plans`; verify end state matches Greenfield happy path.

### Repair

1. From a healthy setup: `rm vault && rm .git/hooks/post-checkout`.
2. Run `/ark-onboard`.
3. Verify both artifacts are recreated.

### Healthy audit

1. Project with real `vault/` dir + Ark artifacts + all other checks passing.
2. Verify check 20 returns `warn` with externalize recommendation.

### Failure-mode smoke tests

1. Greenfield with `chmod -w ~/.superset/vaults/` → verify loud failure, no partial state.
2. Greenfield with `gh` uninstalled → verify `gh repo create` prompt is skipped.
3. Greenfield with centralized-root parent unwritable → abort with specific error.

## Non-Goals

- **CT110 / tinyAGI deploy automation.** The `~/.tinyagi/vaults/<project>/` fallback in the symlink script is preserved, but `/ark-onboard` does not deploy or configure the vault on remote hosts. That remains environment-specific tooling.
- **`.vault-path` fallback file.** Not in scope. Only relevant for tinyAGI's Node.js agents that historically had symlink issues. Production deploy tooling handles it.
- **Vault content migration between projects.** Renaming a project or merging two vaults is manual.
- **Obsidian app auto-switch.** Opening the new vault in the Obsidian desktop app is a manual step in migration. The wizard cannot drive the Obsidian UI.
