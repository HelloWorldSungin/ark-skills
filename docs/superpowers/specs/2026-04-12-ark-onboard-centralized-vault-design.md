# `/ark-onboard` Centralized Vault Recommendation — Design Spec

**Date:** 2026-04-12
**Branch:** vault-symlink
**Status:** Draft (revision 4 — post-codex round 3)

## Problem

`/ark-onboard` greenfield currently defaults to creating the Obsidian vault as `./vault/` inside the project repo. This is the wrong default for the Ark ecosystem:

1. **Worktrees cannot share vault content.** Each `git worktree add` produces an independent `vault/` tree. Session logs and task notes written in one worktree don't appear in another.
2. **Obsidian app mismatch.** The Obsidian desktop app opens exactly one vault at a time. Agents running in worktrees read from their local `vault/` directory, but the app is pointed at the main repo's copy — so `obsidian-cli` searches return stale content from the agent's perspective.
3. **NotebookLM sync state diverges.** Each worktree has its own `.notebooklm/sync-state.json`, causing duplicate uploads unless the sync script is patched (see ArkNode-Poly commit `42937e6`).
4. **Session log collisions.** Two worktrees can create session logs with the same timestamp-based filename.

ArkNode-Poly solved this on 2026-04-01 by externalizing the vault into its own git repo at `~/.superset/vaults/ArkNode-Poly/` and symlinking `vault` into every project/worktree directory. The pattern works — but `/ark-onboard` does not know about it, so every new Ark project recreates the embedded-vault anti-pattern from day one.

> **Prior-art reference:** The 2026-04-01 design and plan live inside the ArkNode-Poly project repo (at `docs/superpowers/specs/2026-04-01-centralized-obsidian-vault-design.md` and `docs/superpowers/plans/2026-04-01-centralized-obsidian-vault.md`), not in this ark-skills repo. This spec generalizes that one-off implementation into reusable `/ark-onboard` wizard logic.

## Terminology

One variable, one meaning:

| Term | Meaning | Example |
|------|---------|---------|
| `<vault_repo_path>` | Absolute path to the centralized vault repo — the full path, not its parent | `~/.superset/vaults/ArkNode-Poly` |
| `<project_repo>` | The project repo that symlinks into the vault | `~/.superset/projects/ArkNode-Poly` |
| `<common_git_dir>` | Output of `git rev-parse --git-common-dir` (shared across worktrees) | `~/.superset/projects/ArkNode-Poly/.git` |

`<vault_repo_path>` is never the parent directory. When the spec needs the parent for `mkdir -p`, it uses `dirname <vault_repo_path>` explicitly.

## Goals

- Make the centralized-vault layout the default for all new Ark projects (Greenfield path).
- Offer migration assistance for projects that already have an embedded vault (Externalization path).
- Repair broken symlinks / missing automation after a reclone (Repair path).
- Audit projects for the anti-pattern via a new warn-only diagnostic check #20.
- Keep the one-off embedded-vault choice available as an explicit, persisted escape hatch.
- Do not break ArkNode-Poly, which already runs this pattern by hand.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | All four `/ark-onboard` state paths (No Vault, Non-Ark Vault, Partial Ark, Healthy) | Centralized vault is the canonical Ark convention; any embedded vault should surface as a warning somewhere. |
| Greenfield aggressiveness | Default yes with explicit `y/N` escape | Other defaults in `/ark-onboard` already assume the Ark convention (tier, layout); centralized vault fits the same pattern. |
| Externalization depth | Plan file only, consumed by `/executing-plans` | Externalization touches committed vault content and multiple worktrees simultaneously. A plan file gates destructive steps behind review. |
| Ark-scaffolding depth (adding `_meta/`, `TaskNotes/` to a non-Ark vault) | Inline, as today | Scaffolding only writes new files into an existing vault — it is non-destructive and already runs inline in the current skill. Not part of this spec's change surface. |
| Greenfield depth | Full auto, one confirmation | Greenfield has no committed state to destroy. Same auto-execute model as the rest of `/ark-onboard` greenfield applies. |
| GitHub remote | Optional, offered after local `git init` | `gh repo create` is nice-to-have, not required for the symlink/hook logic to work. Offer only if `gh` is installed and authenticated. |
| Centralized-location default | Prompt with smart default (`~/.superset/vaults/<project>/` for superset users, `~/Vaults/<project>/` otherwise) | Not every Ark user runs the superset CLI; hardcoding `~/.superset/` would surprise them. Detection keeps the default consistent with the user's existing toolchain. |
| Canonical metadata for `<vault_repo_path>` | The tracked `scripts/setup-vault-symlink.sh` script itself, which contains a single `VAULT_TARGET="$HOME/..."` line by generation-time contract. `$HOME` keeps the path portable across machines. | Tracking an absolute path (e.g., `/Users/<specific_user>/.superset/...`) would poison every collaborator's clone with the wrong path. Using the tracked script as the metadata source means portability is already solved (by `$HOME`), and there's only one tracked artifact to keep consistent. Parsing the script is a contract, not inference — the template guarantees the line format. |
| Worktree symlink automation | Primary: git `post-checkout` hook that calls a tracked script; Optional: `.superset/config.json` integration for existing superset projects | Post-checkout fires on `git worktree add` universally. The tracked script is the single logic source of truth. `.superset/config.json` is kept for backward compatibility with superset-based flows, not as a required layer. |
| `embedded-vault` opt-out schema | Row in the `Project Configuration` table of CLAUDE.md: `\| **Vault layout** \| embedded (not symlinked) \|` — presence of the exact word `embedded` in that row marks the opt-out | Keeps escape hatch visible to humans, greppable by diagnostic, doesn't require a new config file. |
| Check #20 severity | Warn-only (never fail), matching check #10 (index staleness) | An embedded vault is a smell, not a breakage — the project still works. Warn-only means embedded vaults can still reach the `Healthy` state, which matches the escape-hatch contract. |
| NotebookLM config duality | Project copy uses `vault_root: "vault"`, vault copy uses `vault_root: "."` | Matches the 2026-04-01 pattern. Both resolve to the same directory. |
| NotebookLM `sync-state.json` | Created in `<vault_repo_path>/.notebooklm/sync-state.json` during greenfield Step 2a with empty state `{"last_sync": null, "files": {}}`; tracked in vault repo (not ignored) | Shared across environments; prevents duplicate uploads. Creating it upfront avoids bootstrap edge cases on first sync. |

## Architecture

### Directory layout

```
<vault_repo_path>/                      (centralized vault — its own git repo)
├── .git/
├── .obsidian/
├── .notebooklm/
│   ├── config.json                 (vault_root: ".",  tracked)
│   └── sync-state.json             (empty init, tracked)
├── _meta/, _Templates/, _Attachments/
├── TaskNotes/
├── 00-Home.md
└── <ProjectDocs>/                   (monorepo layout)  OR  flat (standalone)

<project_repo>/
├── vault → <vault_repo_path>/        (symlink, git-ignored)
├── .notebooklm/config.json          (vault_root: "vault", tracked)
├── .gitignore                        (contains `vault`)
├── <common_git_dir>/hooks/post-checkout   (installed, not tracked)
├── .superset/config.json             (optional — if already present)
└── scripts/setup-vault-symlink.sh    (tracked; canonical source — contains VAULT_TARGET with $HOME)
```

### Centralized-location default detection

```bash
if [ -d "$HOME/.superset" ]; then
  DEFAULT_VAULT_REPO_PATH="$HOME/.superset/vaults/<project>"
else
  DEFAULT_VAULT_REPO_PATH="$HOME/Vaults/<project>"
fi
```

User is prompted with this default; can accept with Enter or override. The chosen value is converted to its `$HOME`-portable form (e.g., `$HOME/.superset/vaults/<project>`) and written as the `VAULT_TARGET=` literal inside `scripts/setup-vault-symlink.sh` at generation time. That file — tracked in the project repo — is the single canonical source of truth for the vault location.

### `scripts/setup-vault-symlink.sh` as canonical metadata

The script is tracked. By template contract, it contains exactly one line matching the regex `^VAULT_TARGET="[^"]*"\s*$`, somewhere in the script body. The quoted value must start with `$HOME/`. Example:

```bash
VAULT_TARGET="$HOME/.superset/vaults/ArkNode-Poly"
```

`$HOME` expands at runtime, so the same tracked file works on any machine regardless of the user's actual home path. This is the same pattern ArkNode-Poly's existing `.git/hooks/post-checkout` uses in production.

**Path constraint:** The vault path must be under `$HOME`. The Greenfield wizard rejects any input that does not start with `$HOME/` or `~/` (which is normalized to `$HOME/`). Users who need a vault on an external drive or shared mount should `ln -s /Volumes/.../vaults $HOME/Vaults` and then point the wizard at `$HOME/Vaults/<project>`. This keeps the tracked metadata portable across machines by construction.

Read by:
- Repair flow (primary source when locating `<vault_repo_path>`). Extraction: `grep -E '^VAULT_TARGET=' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/'`.
- `/ark-health` check #20 (confirming the declared target matches the symlink target).

Written by:
- Greenfield Step 2c (initial creation).
- Externalization plan step 16 (during plan execution).

Never edited by hand in normal operation. If the vault is intentionally moved, the user runs `/ark-onboard` Repair to update the script and the symlink atomically.

### `scripts/setup-vault-symlink.sh` — single source of truth

Generated from a template at wizard run time. Template variables substituted:
- `PROJECT_NAME` — e.g., `ArkNode-Poly`
- `VAULT_REPO_PATH_PORTABLE` — the `$HOME`-portable form, e.g., `$HOME/.superset/vaults/ArkNode-Poly`. Always begins with the literal prefix `$HOME/`. See "Path constraint" above.
- `TINYAGI_FALLBACK` — e.g., `$HOME/.tinyagi/vaults/ArkNode-Poly` (optional, only included if project declares tinyAGI deploy)

Resulting script skeleton (values shown for a project named `ArkNode-Poly`):

```bash
#!/usr/bin/env bash
# AUTOGENERATED by /ark-onboard — do not hand-edit.
set -e
VAULT_TARGET="$HOME/.superset/vaults/ArkNode-Poly"
TINYAGI_FALLBACK=""   # may be empty; populated only if the project declares a tinyAGI deploy

# 1. Existing valid symlink -> done.
if [ -L vault ] && [ -e vault ]; then
  exit 0
fi
# 2. Broken symlink -> remove it and continue.
if [ -L vault ] && [ ! -e vault ]; then
  rm vault
fi
# 3. Real directory -> loud failure; indicates unfinished migration.
if [ -d vault ]; then
  echo "ERROR: vault/ is a real directory. Run /ark-onboard to externalize." >&2
  exit 1
fi
# 4. Centralized target exists -> link.
if [ -d "$VAULT_TARGET" ]; then
  ln -s "$VAULT_TARGET" vault
  exit 0
fi
# 5. TinyAGI fallback exists -> link.
if [ -n "$TINYAGI_FALLBACK" ] && [ -d "$TINYAGI_FALLBACK" ]; then
  ln -s "$TINYAGI_FALLBACK" vault
  exit 0
fi
# 6. Nothing found -> clone instructions.
echo "ERROR: vault repo not cloned. Clone to $VAULT_TARGET, then retry." >&2
exit 1
```

Idempotent. Called by the post-checkout hook and (optionally) the `.superset/config.json` setup entry.

### `<common_git_dir>/hooks/post-checkout`

```bash
#!/usr/bin/env bash
# Fires on branch checkouts (including git worktree add).
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
```

Installed with `chmod +x`. Since git hooks are not tracked by git, this is reinstalled by `/ark-onboard`'s Greenfield and Repair flows on every fresh clone. Installed into `<common_git_dir>/hooks/` so it is shared across all worktrees.

### `.superset/config.json` — optional, backward-compat only

Only written if `<project_repo>/.superset/config.json` already exists. Preserves ArkNode-Poly's existing setup flow; not a requirement for the centralized-vault mechanism. The setup entry delegates to `scripts/setup-vault-symlink.sh`; the teardown entry removes the symlink if present. `git worktree remove` already deletes the symlink as part of removing the worktree directory, so the teardown is redundant in practice — it is kept only to match ArkNode-Poly's existing layout.

```json
{
  "setup": ["...existing...", "bash scripts/setup-vault-symlink.sh"],
  "teardown": ["...existing...", "[ -L vault ] && rm vault || true"]
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

If the user answers `y` to prompt 2, the wizard falls back to the legacy `./vault/` path, skips all symlink/hook logic, and writes the escape-hatch opt-out to CLAUDE.md. Specifically, in the `Project Configuration` table of CLAUDE.md it writes:

```markdown
| **Vault layout** | embedded (not symlinked) |
```

Check #20 looks for exactly that row (case-insensitive match on the word `embedded`) and reports `pass` when present. All other steps run as before.

Otherwise, **four new steps** are inserted between current Step 2 (Python check) and Step 3 (Create vault directories):

- **Step 2a — Create centralized vault repo.** `mkdir -p <vault_repo_path>`; `cd` in; `git init`; write `.gitignore` containing per-user Obsidian files (`workspace.json`, `workspace-mobile.json`, `graph.json`, `plugin data.json`) **and nothing else** — `sync-state.json` is intentionally tracked. Create `<vault_repo_path>/.notebooklm/sync-state.json` with content `{"last_sync": null, "files": {}}`.
- **Step 2b — Create symlink.** `ln -s <vault_repo_path> <project_repo>/vault`; append `vault` to `<project_repo>/.gitignore`.
- **Step 2c — Install automation.** Write `<project_repo>/scripts/setup-vault-symlink.sh` from the template, with `VAULT_TARGET=` set to the `$HOME`-relative form of the chosen vault path (e.g., `$HOME/.superset/vaults/<project>`). Install `<common_git_dir>/hooks/post-checkout` with `chmod +x`. If `<project_repo>/.superset/config.json` exists, append the optional setup/teardown entries.
- **Step 2d — Offer GitHub remote.** If `gh` CLI is installed and `gh auth status` succeeds, prompt: `Create a GitHub repo for this vault now? [y/N]`. On yes, `gh repo create --private <project>-vault --source=<vault_repo_path> --push`. On no (or if `gh` unavailable), print the one-line command for later use.

All subsequent greenfield steps (3 through 18 — directory creation, `00-Home.md`, `_meta/*`, TaskNotes scaffolding, index generation) run **inside the centralized vault repo**, not the project repo. The final `git add . && git commit -m "Initial vault scaffolding"` happens in the vault repo.

The existing NotebookLM step writes `<project_repo>/.notebooklm/config.json` with `vault_root: "vault"` and additionally writes `<vault_repo_path>/.notebooklm/config.json` with `vault_root: "."`.

### Externalization — new section

Triggered when state detection finds `vault/` is a real directory (not a symlink) containing Ark artifacts, **and** the escape-hatch opt-out is NOT present in CLAUDE.md. Wizard does NOT execute — it generates a plan file.

Prompt sequence:
```
Detected: vault/ is committed to this repo as a real directory.
The Ark convention is to externalize it. I'll generate a plan
(no destructive actions). You can review and run it via /executing-plans.

Centralized location for the extracted vault: <default>  [Enter to accept]
Create a GitHub repo for the vault? [y/N]
```

The wizard then writes `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`, parameterized with the detected project name, vault repo path, sibling worktree paths, and NotebookLM config locations. The plan has **three phases**:

**Phase 0 — Preflight (no mutation):**

1. Discover sibling worktrees: `git worktree list --porcelain | awk '/^worktree /{print $2}'`.
2. For each sibling (including the main repo): check that `<sibling>/vault/` exists and is a real directory (not a symlink). Abort with a clear message listing any siblings where `vault/` is missing, a symlink, or a broken symlink.
3. Pairwise compare sibling `vault/` directories using git's own diff engine, which handles symlinks, file modes, and binary files portably across macOS and Linux. Pick one sibling as the baseline (arbitrary — e.g., the main repo), then for every other sibling run: `git -c core.safecrlf=false diff --no-index --stat -- <baseline>/vault <sibling>/vault`. A non-zero exit or non-empty output means divergence. Supplementary empty-directory check (git does not track empty dirs): `diff <(cd <baseline>/vault && find . -type d -empty | sort) <(cd <sibling>/vault && find . -type d -empty | sort)`. If ANY content or empty-dir divergence is found, print the full diff output for each divergent pair and **abort the plan**. The user must resolve divergence manually (commit, discard, or merge) before re-running `/ark-onboard`.
4. Check every sibling for uncommitted or untracked files under `vault/`: `(cd <sibling> && git status --porcelain vault/)`. Abort if any are present.
5. Confirm `<vault_repo_path>` does not already exist, or exists but is empty.

Phase 0 exits the plan cleanly if any check fails. No destructive step runs unless all preflight checks pass.

**Phase 1 — Externalize (destructive, scoped to main repo + vault target):**

6. `git init <vault_repo_path>`.
7. Copy main-repo `vault/` contents into `<vault_repo_path>`.
8. Copy `<project_repo>/.notebooklm/config.json` into `<vault_repo_path>/.notebooklm/` and update `vault_root: "."`.
9. Move `<project_repo>/.notebooklm/sync-state.json` into `<vault_repo_path>/.notebooklm/` (or create empty state `{"last_sync": null, "files": {}}` if missing).
10. Write `<vault_repo_path>/.gitignore` containing Obsidian per-user files only (`workspace.json`, `workspace-mobile.json`, `graph.json`, `plugin data.json`). `sync-state.json` is intentionally tracked.
11. `cd <vault_repo_path> && git add . && git commit -m "Initial externalized vault"`.
12. (Optional) `gh repo create --private <project>-vault --source=<vault_repo_path> --push`.
13. `cd <project_repo> && git rm -r --cached vault/`.
14. Append `vault` to `<project_repo>/.gitignore`.
15. `rm -rf <project_repo>/vault && ln -s <vault_repo_path> <project_repo>/vault`.
16. Write `scripts/setup-vault-symlink.sh` (with `VAULT_TARGET="$HOME/..."` in `$HOME`-portable form), install post-checkout hook, append to `.superset/config.json` if present.
17. Update CLAUDE.md "Obsidian Vault" row to note symlink.
18. `cd <project_repo> && git add . && git commit -m "Externalize vault"`.

**Phase 2 — Sibling worktrees (destructive, scoped to each sibling):**

19. For each sibling worktree verified identical in Phase 0 preflight: `rm -rf <sibling>/vault && ln -s <vault_repo_path> <sibling>/vault`. One sibling at a time, with explicit confirmation per sibling.

**Phase 3 — Manual follow-ups (documented, not executed):**

20. Close the old vault in the Obsidian desktop app and open `<vault_repo_path>/` instead.

Each step in the plan file includes the exact command, a rollback note where applicable, and an explicit success criterion. Wizard prints the plan path, lists preflight sibling worktrees that will be touched, and exits. No filesystem changes.

### Repair — new branch

Triggered on Partial Ark when diagnostic finds any of:

- `vault` missing entirely, OR
- `vault` is a broken symlink, OR
- `<common_git_dir>/hooks/post-checkout` missing/non-executable, OR
- `scripts/setup-vault-symlink.sh` missing, OR
- `readlink vault` does not match the `VAULT_TARGET` declared in `scripts/setup-vault-symlink.sh` (after expanding `$HOME`).

**Determining `<vault_repo_path>` in Repair** (in this order):

1. If `scripts/setup-vault-symlink.sh` exists: extract `VAULT_TARGET` via the documented grep contract, expand `$HOME`, use the result. (Canonical source.)
2. Else if `vault` is a broken symlink: `readlink vault` gives the original target. Use it as the intended path and print `git clone <remote> <target>` instructions if the target doesn't exist.
3. Else: prompt the user with the Greenfield smart default.

For each missing piece, prompt `Fix [item]? [Y/n]` and either recreate it (if `<vault_repo_path>` already holds the vault) or print clone instructions and skip. All fixes are idempotent. No plan file — these are low-risk, non-destructive operations.

If a mismatch is detected between `readlink vault` and the script's `VAULT_TARGET`, Repair stops and surfaces both values, asking the user which to trust. It does not silently relink.

### Healthy — audit check

Add one warn-only check to the diagnostic:

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| **20** | Vault externalized | Standard (warn-only) | One of: (a) `vault` is a symlink AND `readlink vault` matches the `VAULT_TARGET` declared in `scripts/setup-vault-symlink.sh` AND the resolved target exists; OR (b) CLAUDE.md `Project Configuration` table contains a `Vault layout` row whose value matches `embedded` (case-insensitive). |

Status options for check 20, by observed state:

Exhaustive table — every combination of (`vault` artifact present? which kind?) × (`scripts/setup-vault-symlink.sh` present?) × (embedded opt-out in CLAUDE.md?) is listed:

| `vault` | Script | Opt-out | Status | Message |
|---------|--------|---------|--------|---------|
| Symlink, target resolves, matches script's `VAULT_TARGET` | present | (either) | `pass` | — |
| Symlink, target resolves, but does not match script's `VAULT_TARGET` | present | (either) | `warn` | "Vault symlink target disagrees with `scripts/setup-vault-symlink.sh` VAULT_TARGET. Run `/ark-onboard` Repair." |
| Symlink, target missing (broken link) | present | (either) | `warn` | "Vault symlink is broken. Run `/ark-onboard` Repair." |
| Symlink (any target state) | missing | (either) | `warn` | "Vault symlink exists but canonical script `scripts/setup-vault-symlink.sh` is missing. Run `/ark-onboard` Repair to backfill." |
| Real directory | (either) | present | `pass` | — |
| Real directory | (either) | absent | `warn` | "Vault is embedded inside the project repo. Run `/ark-onboard` to externalize, or set `Vault layout: embedded` in CLAUDE.md if this is intentional." |
| Missing entirely | present | (either) | `warn` | "Canonical vault script exists but no `vault` artifact. Run `/ark-onboard` Repair to create the symlink." |
| Missing entirely | missing | present | `pass` | (Opt-out declares the user chose embedded but hasn't created the vault yet. Check #7 — vault-directory-exists — independently handles this as Critical fail.) |
| Missing entirely | missing | absent | `warn` | "No vault configured. Run `/ark-onboard` Greenfield." |

Check #20 never returns `fail`. All negative states are `warn`. State detection independently classifies broken symlinks and missing scripts as Partial Ark for routing purposes; check #20 only reports diagnostic status.

**Impact on Healthy classification:** Because check 20 is warn-only (matches check #10 for index staleness), a project with an embedded `vault/` directory still qualifies as `Healthy` as long as all other Critical + Standard checks pass. This matches the escape-hatch contract: embedded vaults are a smell, not a breakage.

Total check count rises from 19 → 20.

### State → action summary

| Detected State | Action |
|---|---|
| No Vault (greenfield) | Centralized default → full-auto setup + hook install. If user picks embedded escape hatch, write opt-out row to CLAUDE.md. |
| Non-Ark Vault (real dir, no Ark artifacts) | Inline Ark scaffolding as today (no change to scaffolding logic), followed by externalization plan file generation. Scaffolding is inline/safe; externalization is plan-only. |
| Partial Ark (symlink broken / hook missing / script missing / symlink-target vs script-declared-target mismatch) | Repair prompts + idempotent fixes |
| Partial Ark (real `vault/` with Ark artifacts, no opt-out) | Externalization plan file |
| Partial Ark (real `vault/` with Ark artifacts, opt-out present) | Respect user choice; do not offer externalization |
| Healthy (symlink present + matches declared `VAULT_TARGET` in script) | Check 20 passes |
| Healthy (real `vault/` with Ark artifacts, no opt-out) | Check 20 warns. Project still qualifies as Healthy. Wizard offers externalization plan but does not require it. |
| Healthy (real `vault/` with Ark artifacts, opt-out present) | Check 20 passes. No externalization offered. |

## Files Created or Modified

| File | Greenfield | Externalization | Repair | Healthy |
|------|-----------|-----------------|--------|---------|
| `<vault_repo_path>/` (vault repo) | create + `git init` + initial commit | via plan | — | — |
| `<vault_repo_path>/.notebooklm/sync-state.json` | create empty | via plan | — | — |
| `<project_repo>/vault` symlink | create | via plan | recreate | — |
| `<project_repo>/.gitignore` | append `vault` | via plan | verify | — |
| `<common_git_dir>/hooks/post-checkout` | install | via plan | install if missing | — |
| `<project_repo>/scripts/setup-vault-symlink.sh` | write | via plan | write if missing | — |
| `<project_repo>/.superset/config.json` | append entries (if exists) | via plan | — | — |
| `<vault_repo_path>/.notebooklm/config.json` | write (`vault_root: "."`) | via plan | — | — |
| `<project_repo>/.notebooklm/config.json` | write (`vault_root: "vault"`) | via plan | — | — |
| `<project_repo>/CLAUDE.md` | normal greenfield write + opt-out row if embedded picked | via plan | — | — |
| `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md` | — | create | — | create on demand |

## Edge Cases

| Edge case | Handling |
|-----------|----------|
| `/ark-onboard` run from inside a worktree | Resolve common `.git` via `git rev-parse --git-common-dir`; install hook there. |
| `<vault_repo_path>` exists and is empty | Treat as orphan from a prior failed run: prompt user to delete + retry or pick a different path. |
| `<vault_repo_path>` exists with content from a different project | Refuse; compare `00-Home.md` title and `.notebooklm/config.json` to confirm mismatch. Never overwrite. |
| User types a `<vault_repo_path>` inside the project repo | Refuse — defeats the purpose. |
| User types a `<vault_repo_path>` not under `$HOME` (e.g., `/Volumes/...`, `/mnt/...`, another user's home) | Refuse with message: "Vault path must be under `$HOME` so tracked metadata stays portable across machines. To use an external drive, symlink it into `$HOME` first (e.g., `ln -s /Volumes/ExternalDrive/vaults $HOME/Vaults`) and point the wizard at the `$HOME` path." Re-prompt. |
| `<vault_repo_path>` parent doesn't exist | `mkdir -p` silently; confirm before creating. |
| `vault` symlink points to the wrong location | Repair flow: compare `readlink vault` with the script's `VAULT_TARGET`; stop and ask user which to trust; never silently relink. |
| Script's `VAULT_TARGET` and the symlink target disagree | Repair flow: surface both values, let user pick; never auto-fix. |
| `gh` CLI not installed or not authenticated | Skip the remote prompt. Print one-liner for later. |
| Project repo isn't a git repo yet | Existing Greenfield prereqs offer `git init` first. |
| `<vault_repo_path>` is on a network mount / external drive | Warn about mount availability; continue. |
| ArkNode-Poly (already on this pattern) running `/ark-onboard` | State detection classifies as Healthy. If `scripts/setup-vault-symlink.sh` is missing but the symlink and hook exist (ArkNode-Poly's original hand-rolled layout), wizard offers to backfill the tracked script by inferring `VAULT_TARGET` from `readlink vault`. |
| Externalization preflight finds divergent sibling vaults | Plan aborts before any destructive step. User must resolve divergence manually. Clear instructions printed. |

## Failure Modes

- **Symlink creation fails** (permission denied, etc.): print the `ln` error verbatim, abort the wizard. Do not continue with partial state.
- **Post-checkout hook install fails** (write-denied on `<common_git_dir>/hooks/`): abort, surface the error. Do not claim success.
- **Post-install verification.** After installation, run `test -L vault && test -e vault && test -x <common_git_dir>/hooks/post-checkout && test -f scripts/setup-vault-symlink.sh && grep -qE '^VAULT_TARGET=' scripts/setup-vault-symlink.sh`. If any check fails, wizard reports the specific step.
- **Externalization plan — divergent siblings**: Phase 0 preflight aborts before any destructive step. Plan prints the divergent file list and instructs user to resolve. Plan can be re-run after resolution.
- **Externalization plan — partial execution**: `/executing-plans` handles recovery. Plan is ordered so Phase 1 (main repo + vault target) completes atomically before Phase 2 (siblings) begins. Each phase has explicit rollback notes.
- **`gh repo create` fails** (name taken, auth): keep local init state; print error + manual-create instructions. Do not roll back.
- **Orphan `<vault_repo_path>` from prior failed greenfield**: detection finds it on second run; user prompted to delete or choose new path. No auto-overwrite.

## Downstream Skill Updates

| Skill | Change |
|-------|--------|
| `/ark-health` | Add check #20 (vault-externalized, warn-only). Count rises 19 → 20. Sync with `/ark-onboard` shared diagnostic section. Update the existing Healthy-classification rule — currently "all Critical + Standard checks pass" ([skills/ark-onboard/SKILL.md](../../../skills/ark-onboard/SKILL.md), Project State Detection table) — to read "no Critical or Standard check returns `fail`" so warn-returning checks (10, 20) don't block Healthy. |
| `/ark-onboard` | All changes in this spec, including the Healthy-classification rule revision above. |
| `/notebooklm-vault` | Confirm it reads config from project's `.notebooklm/` first, falls back to `<vault>/.notebooklm/`, and resolves `sync-state.json` inside the vault. Add note about centralized-vault assumption. Bootstrap logic: if `sync-state.json` missing, create empty state (matches greenfield Step 2a behavior). |
| `/wiki-update` | Session log filenames should include an environment prefix (`mac-`, `ct110-`) when `vault` is a symlink (cross-env collision prevention). Detect symlink via `test -L vault`. |
| `/codebase-maintenance` | Add note: "When vault is symlinked, commit/push vault changes in the vault repo, not the project repo." |
| `/ark-workflow` | When detection finds embedded `vault/` without opt-out, surface externalize-vault as a recommended next step. |

## Testing

### Greenfield — happy path

1. Fresh empty git repo; run `/ark-onboard`; accept all defaults.
2. Verify `<vault_repo_path>` exists with `.git/` and Ark artifacts.
3. Verify `vault` symlink resolves, `vault` present in `.gitignore`, `<common_git_dir>/hooks/post-checkout` executable, `scripts/setup-vault-symlink.sh` tracked and contains a `VAULT_TARGET="$HOME/..."` line.
4. `git worktree add ../test-wt` → verify `../test-wt/vault` symlink auto-created.
5. `ls <vault_repo_path>/.notebooklm/` → `config.json` and `sync-state.json` both present; `cat <vault_repo_path>/.notebooklm/sync-state.json` shows `{"last_sync": null, "files": {}}`.
6. `cd <vault_repo_path> && git ls-files | grep sync-state.json` → file is tracked (not ignored).
7. Reclone the project repo on a different machine (or with a different `$HOME`) → re-run `/ark-onboard` Repair → verify the symlink is recreated correctly using `$HOME` expansion, no user-specific paths leaked into tracked files.

### Greenfield — escape hatch

1. Fresh repo; answer `y` to "use embedded vault?"
2. Verify `vault/` is a real directory; no symlink; no post-checkout hook; no `setup-vault-symlink.sh`; `vault/` NOT in `.gitignore`.
3. Verify CLAUDE.md `Project Configuration` table contains a `Vault layout` row whose value contains `embedded`.
4. Run `/ark-health` → check 20 passes (opt-out present).

### Externalization — preflight gate

1. Repo with pre-existing real `vault/` dir + Ark artifacts + at least one sibling worktree whose `vault/` content differs (e.g., extra session log file).
2. Run `/ark-onboard` → plan file written.
3. Manually run Phase 0 preflight from the plan → verify it aborts with a clear divergent-file list.
4. Verify no filesystem changes beyond the plan file itself.

### Externalization — happy path

1. Repo with pre-existing real `vault/` dir + Ark artifacts + identical sibling worktrees; run `/ark-onboard`.
2. Verify plan file at `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`, parameterized with correct project name and `<vault_repo_path>`.
3. Pipe plan to `/executing-plans` → Phase 0 passes, Phase 1 runs, Phase 2 prompts per sibling, Phase 3 manual steps surfaced.
4. Verify end state matches Greenfield happy path (symlink, hook, script with `VAULT_TARGET`, etc.).

### Repair

1. From a healthy setup: `rm vault && rm <common_git_dir>/hooks/post-checkout`.
2. Run `/ark-onboard`.
3. Verify both artifacts recreated using the `VAULT_TARGET` in `scripts/setup-vault-symlink.sh` as the source of truth.
4. Separately: manually symlink `vault` to a bogus target that disagrees with the script's `VAULT_TARGET` → run `/ark-onboard` Repair → verify it surfaces both values and asks the user to choose, does not silently relink.

### Healthy audit

1. Project with real `vault/` dir + Ark artifacts + all other checks passing + NO opt-out in CLAUDE.md.
2. Verify check 20 returns `warn` (not fail) with externalize recommendation; project classified Healthy.
3. Add the `embedded` opt-out row → re-run → verify check 20 returns `pass`.

### Failure-mode smoke tests

1. Greenfield with `chmod -w ~/.superset/vaults/` → verify loud failure, no partial state, no stray tracked files written.
2. Greenfield with `gh` uninstalled → verify `gh repo create` prompt is skipped.
3. Greenfield with `<vault_repo_path>` parent unwritable → abort with specific error.

## Non-Goals

- **CT110 / tinyAGI deploy automation.** The `TINYAGI_FALLBACK` slot in the symlink script is preserved (optional), but `/ark-onboard` does not deploy or configure the vault on remote hosts. That remains environment-specific tooling.
- **`.vault-path` fallback file.** Not in scope. The tracked `scripts/setup-vault-symlink.sh` (via its `VAULT_TARGET` literal) serves the canonical-metadata role; the legacy tinyAGI `.vault-path` mechanism is orthogonal and handled by deploy tooling.
- **Vault content migration between projects.** Renaming a project or merging two vaults is manual.
- **Obsidian app auto-switch.** Opening the new vault in the Obsidian desktop app is a manual step in the externalization plan (Phase 3). The wizard cannot drive the Obsidian UI.
- **Automatic sync-state repair.** If `sync-state.json` is deleted or corrupted post-externalization, `/notebooklm-vault` bootstraps empty state on next sync. `/ark-onboard` does not try to reconstruct it.
