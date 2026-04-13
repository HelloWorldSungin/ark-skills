---
name: ark-onboard
description: Interactive setup wizard — greenfield, vault migration, partial repair. Absorbs /wiki-setup.
---

# Ark Onboard

Interactive setup wizard for new Ark projects. Detects project state (greenfield, migration, repair, healthy) and walks through setup at 3 tiers (Quick, Standard, Full). This skill absorbs all `/wiki-setup` functionality and is the single entry point for new project onboarding.

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete. When CLAUDE.md is absent, the wizard detects project state from the filesystem and enters the appropriate path (greenfield if no vault exists, partial/migration if a vault directory is found).

Never abort because CLAUDE.md is missing. That is one of the states this skill is designed to handle.

## Vault Path Terminology

| Term | Meaning | Example |
|------|---------|---------|
| **Vault root** | Top-level directory containing all vault content | `vault/` |
| **Project docs path** | Subdirectory for project-specific knowledge (may equal vault root for standalone) | `vault/Trading-Signal-AI/` |
| **TaskNotes path** | Sibling of project docs under vault root, never nested under project docs | `vault/TaskNotes/` |

Path layout:
```
vault/                        # {vault_root}
├── Trading-Signal-AI/        # {project_docs_path}
│   ├── Session-Logs/
│   └── ...
└── TaskNotes/                # {tasknotes_path} — sibling, NOT nested
    ├── Tasks/
    ├── Archive/
    └── meta/ArkSignal-counter
```

## Centralized Vault Layout (Default)

New projects default to a **centralized vault**: the vault lives in its own git repo at `~/.superset/vaults/<project>/` (or `~/Vaults/<project>/` for non-superset users), and the project repo contains a `vault` symlink to it. This mirrors ArkNode-Poly's production pattern. Benefits:

- Worktrees share a single vault — session logs and tasks are visible everywhere.
- Obsidian desktop app points at exactly one vault for any project, so `obsidian-cli` agrees with the agent.
- NotebookLM sync state is shared (not duplicated per worktree).

### Vault path terms

| Term | Meaning | Example |
|------|---------|---------|
| `<vault_repo_path>` | Absolute path to the centralized vault repo — the full path, not its parent | `~/.superset/vaults/ArkNode-Poly` |
| `<project_repo>` | The project repo that symlinks into the vault | `~/.superset/projects/ArkNode-Poly` |
| `<common_git_dir>` | Output of `git rev-parse --git-common-dir` (shared across worktrees) | `~/.superset/projects/ArkNode-Poly/.git` |

### Default path detection

```bash
if [ -d "$HOME/.superset" ]; then
  DEFAULT_VAULT_REPO_PATH="$HOME/.superset/vaults/<project>"
else
  DEFAULT_VAULT_REPO_PATH="$HOME/Vaults/<project>"
fi
```

### Path constraint — `$HOME`-portable

The chosen vault path **must start with `$HOME/`** (or `~/`, which normalizes to `$HOME/`). The wizard rejects absolute paths outside `$HOME` (e.g., `/Volumes/...`, `/mnt/...`, another user's home). Users who want a vault on an external drive should `ln -s /Volumes/ExternalDrive/vaults $HOME/Vaults` and point the wizard at the `$HOME` path. This keeps tracked metadata portable across machines by construction.

When writing `VAULT_TARGET` into the tracked setup script, always store the `$HOME/`-prefixed form (e.g., `VAULT_TARGET="$HOME/.superset/vaults/ArkNode-Poly"`), not the expanded absolute path. `$HOME` expands at runtime on whichever machine runs the script.

### Layout diagram

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

### Embedded vault opt-out

Users who explicitly want the vault committed to the project repo can skip the centralized layout. When they do, the wizard writes this row into CLAUDE.md's `Project Configuration` table:

```markdown
| **Vault layout** | embedded (not symlinked) |
```

Check #20 (vault-externalized) reads this row: presence of the word `embedded` (case-insensitive) in the `Vault layout` row means the user opted in to embedded. In that case, check #20 returns `pass` for the opt-out.

### `scripts/setup-vault-symlink.sh` template

The wizard writes this script into `<project_repo>/scripts/setup-vault-symlink.sh` during Greenfield (Step 2c) or Externalization (plan step 16). Substitute `<PROJECT_NAME>` and `<VAULT_REPO_PATH_PORTABLE>` at generation time. `<VAULT_REPO_PATH_PORTABLE>` always begins with the literal prefix `$HOME/`.

**Contract (grep-friendly):** The generated script MUST contain exactly one line matching the regex `^VAULT_TARGET="[^"]*"\s*$`, and the quoted value MUST begin with `$HOME/`. Repair and check #20 rely on this grep contract.

```bash
#!/usr/bin/env bash
# AUTOGENERATED by /ark-onboard — do not hand-edit.
# Ensures the project repo has a `vault` symlink to the centralized vault repo.
# Called by .git/hooks/post-checkout on every branch checkout / worktree add.
# Also called by .superset/config.json setup hook if the project uses superset.
set -e
VAULT_TARGET="<VAULT_REPO_PATH_PORTABLE>"
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
  echo "vault symlink created -> $VAULT_TARGET"
  exit 0
fi
# 5. TinyAGI fallback exists -> link.
if [ -n "$TINYAGI_FALLBACK" ] && [ -d "$TINYAGI_FALLBACK" ]; then
  ln -s "$TINYAGI_FALLBACK" vault
  echo "vault symlink created (tinyagi fallback) -> $TINYAGI_FALLBACK"
  exit 0
fi
# 6. Nothing found -> clone instructions.
echo "ERROR: vault repo not cloned. Clone the vault repo to $VAULT_TARGET, then retry." >&2
exit 1
```

The script is idempotent: re-running it when `vault` is already a valid symlink is a no-op.

### `.git/hooks/post-checkout` template

```bash
#!/usr/bin/env bash
# AUTOGENERATED by /ark-onboard — do not hand-edit.
# Fires on branch checkouts (including git worktree add).
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
```

Install with `chmod +x`. **Always install into `<common_git_dir>/hooks/post-checkout`**, not `<worktree>/.git/hooks/post-checkout` — worktrees share the main repo's hooks via `commondir`. Use `git rev-parse --git-common-dir` to find the right path:

```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
```

### `.superset/config.json` — optional, backward-compat

Only append if `<project_repo>/.superset/config.json` already exists. The setup entry delegates to the canonical script. The teardown entry removes the symlink (redundant with `git worktree remove`, kept for ArkNode-Poly compatibility).

```json
{
  "setup":    ["...existing...", "bash scripts/setup-vault-symlink.sh"],
  "teardown": ["...existing...", "[ -L vault ] && rm vault || true"]
}
```

## Required CLAUDE.md Fields (Normalized)

Only 4 user-provided fields (everything else is derived):

| Field | Format | Example |
|-------|--------|---------|
| Project name | Any string | `trading-signal-ai` |
| Vault root | Path ending with `/` | `vault/` |
| Task prefix | Ends with `-` | `ArkSignal-` |
| TaskNotes path | Path ending with `/` | `vault/TaskNotes/` |

Derived values:
- **Counter file:** `{tasknotes_path}/meta/{task_prefix}counter` (e.g., `vault/TaskNotes/meta/ArkSignal-counter`)
- **Project docs path:** From "Obsidian Vault" row in CLAUDE.md, or `{vault_root}` for standalone layouts

## Shared Diagnostic Checklist

> **Sync note:** `/ark-health` is the authoritative source for all 19 check definitions. If this copy drifts from `/ark-health`, that skill is correct. This copy exists so `/ark-onboard` can run diagnostics without invoking a separate skill.

### Plugins (Checks 1-3)

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| 1 | superpowers plugin | Critical | At least one `superpowers:*` skill in session |
| 2 | gstack plugin | Standard | At least one gstack skill (`browse`, `qa`, `ship`, `review`) in session |
| 3 | obsidian plugin | Standard | `obsidian:obsidian-cli` skill in session |

### Project Configuration (Checks 4-6)

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| 4 | CLAUDE.md exists | Critical | `CLAUDE.md` exists in project root |
| 5 | CLAUDE.md required fields | Critical | All 4 fields present and non-empty |
| 6 | Task prefix format | Critical | Prefix ends with `-`, counter file exists |

### Vault Structure (Checks 7-11)

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| 7 | Vault directory exists | Critical | Vault root path resolves to a real directory |
| 8 | Vault structure | Critical | `_meta/`, `_Templates/`, `TaskNotes/` exist; plus `00-Home.md` (standalone) or project docs subdir (monorepo) |
| 9 | Python 3.10+ | Critical | `python3 --version` returns >= 3.10 |
| 10 | Index status | Standard | `index.md` exists (staleness is warning, not fail) |
| 11 | Task counter | Standard | Counter file exists and contains valid integer |

### Integrations (Checks 12-19)

| # | Check | Tier | Pass Condition |
|---|-------|------|----------------|
| 12 | Obsidian vault plugins | Standard | `tasknotes/main.js` and `obsidian-git/main.js` in `.obsidian/plugins/` |
| 13 | TaskNotes MCP | Standard | `mcpServers.tasknotes` in `.mcp.json` (config only, not connectivity; Obsidian must be running for endpoint to respond) |
| 14 | MemPalace installed | Full | `mempalace` CLI on PATH |
| 15 | MemPalace wing indexed | Full | `mempalace status` shows wing for project (vault content wing; conversation history wing is separate) |
| 16 | History auto-index hook | Full | `~/.claude/hooks/ark-history-hook.sh` exists AND registered in `.claude/settings.json` |
| 17 | NotebookLM CLI installed | Full | `notebooklm` CLI on PATH |
| 18 | NotebookLM config | Full | `.notebooklm/config.json` exists (project root or vault root) with non-empty notebook ID |
| 19 | NotebookLM authenticated | Full | `notebooklm auth check --test` exits 0 |

### Running Diagnostics

Run all 19 checks in sequence. Never abort on failure. Track results:

```
results = { 1..19: pass | fail | warn | skip | upgrade }
```

- Checks 7-19 with CLAUDE.md missing (check 4 = fail): record `skip` — "cannot check — CLAUDE.md missing"
- Check 10 staleness: record `warn` (not fail)
- Checks 15, 16: if check 14 failed, record `skip` — "requires MemPalace (check 14)"
- Checks 18, 19: if check 17 failed, record `skip` — "requires NotebookLM CLI (check 17)"
- Full-tier checks (14-19) when user is below Full tier: record `upgrade`

## Project State Detection

Detection logic: check for vault directory FIRST, then check CLAUDE.md.

### Step 1: Scan for vault directory

```bash
# Look for vault indicators in common locations
for DIR in vault/ docs/vault/ .vault/; do
  if [ -d "$DIR" ]; then
    echo "VAULT_DIR=$DIR"
    # Check for .obsidian/ or .md files as confirmation
    ls "$DIR"/.obsidian/ 2>/dev/null && echo "has .obsidian"
    find "$DIR" -maxdepth 2 -name "*.md" 2>/dev/null | head -5
  fi
done
```

### Step 2: Check CLAUDE.md

```bash
ls CLAUDE.md 2>/dev/null && echo "CLAUDE_MD=found" || echo "CLAUDE_MD=missing"
```

If CLAUDE.md exists, extract vault root from it:
```bash
grep -i "vault" CLAUDE.md 2>/dev/null | grep -oE '`[^`]+/`' | tr -d '`' | head -1
```

### Step 3: Classify project state

| State | Condition | Wizard Path |
|-------|-----------|-------------|
| **No Vault** | CLAUDE.md missing AND no vault directory found, OR CLAUDE.md present but vault root field missing/path doesn't exist | Greenfield (full setup) |
| **Non-Ark Vault** | Vault directory exists but missing 3+ of: `_meta/vault-schema.md`, `_meta/taxonomy.md`, `index.md`, `TaskNotes/meta/` | Migration (add Ark scaffolding) |
| **Partial Ark** | Has Ark structure (3+ artifacts present) but some diagnostic checks fail. Also: vault exists but CLAUDE.md missing. | Repair (fix what's broken) |
| **Healthy** | All Critical + Standard checks pass | Report (show status, surface upgrades) |

```bash
# Count Ark artifacts to distinguish Non-Ark from Partial
ARK_ARTIFACTS=0
[ -f "${VAULT_DIR}_meta/vault-schema.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -f "${VAULT_DIR}_meta/taxonomy.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -f "${VAULT_DIR}index.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -d "${VAULT_DIR}TaskNotes/meta" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
echo "Ark artifacts found: $ARK_ARTIFACTS / 4"

# Centralized-vault detection (independent of artifact count)
IS_SYMLINK=false
SCRIPT_EXISTS=false
EMBEDDED_OPTOUT=false
SYMLINK_BROKEN=false
SYMLINK_DRIFT=false

if [ -L "${VAULT_DIR%/}" ]; then
  IS_SYMLINK=true
  if [ ! -e "${VAULT_DIR%/}" ]; then
    SYMLINK_BROKEN=true
  fi
fi

if [ -f "scripts/setup-vault-symlink.sh" ]; then
  SCRIPT_EXISTS=true
  # Extract VAULT_TARGET for drift check (grep contract)
  SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
  # Expand $HOME so we can compare against readlink output
  SCRIPT_TARGET_EXPANDED=$(eval "echo $SCRIPT_TARGET")
  if [ "$IS_SYMLINK" = "true" ] && [ -e "${VAULT_DIR%/}" ]; then
    SYMLINK_TARGET=$(readlink "${VAULT_DIR%/}")
    if [ "$SYMLINK_TARGET" != "$SCRIPT_TARGET_EXPANDED" ]; then
      SYMLINK_DRIFT=true
    fi
  fi
fi

# Check for embedded-vault opt-out row in CLAUDE.md
if [ -f CLAUDE.md ] && grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md; then
  EMBEDDED_OPTOUT=true
fi

echo "IS_SYMLINK=$IS_SYMLINK"
echo "SCRIPT_EXISTS=$SCRIPT_EXISTS"
echo "SYMLINK_BROKEN=$SYMLINK_BROKEN"
echo "SYMLINK_DRIFT=$SYMLINK_DRIFT"
echo "EMBEDDED_OPTOUT=$EMBEDDED_OPTOUT"

# Classification
# Key rules:
#   - vault exists + no CLAUDE.md = Partial (never greenfield)
#   - broken symlink OR symlink drift OR missing script with live symlink = Partial Ark (centralized-vault repair)
#   - real vault dir + embedded opt-out present = respect opt-out, classify by artifact count only
if [ -z "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "missing" ]; then
  echo "STATE=no_vault"
elif [ -z "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "found" ]; then
  # CLAUDE.md exists but vault root missing or doesn't exist
  echo "STATE=no_vault"
elif [ "$SYMLINK_BROKEN" = "true" ] || [ "$SYMLINK_DRIFT" = "true" ]; then
  echo "STATE=partial_ark"
  echo "REPAIR_REASON=centralized-vault-drift"
elif [ "$IS_SYMLINK" = "true" ] && [ "$SCRIPT_EXISTS" = "false" ]; then
  echo "STATE=partial_ark"
  echo "REPAIR_REASON=centralized-vault-script-missing"
elif [ -n "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "missing" ]; then
  # Vault exists but no CLAUDE.md — always Partial, regardless of artifact count
  echo "STATE=partial_ark"
elif [ $ARK_ARTIFACTS -ge 3 ]; then
  echo "STATE=partial_ark"
elif [ -n "$VAULT_DIR" ]; then
  echo "STATE=non_ark_vault"
else
  echo "STATE=no_vault"
fi
```

### Centralized-Vault Signals

The classification block above sets five flags used throughout the wizard:

| Flag | Meaning | Used by |
|------|---------|---------|
| `IS_SYMLINK` | `vault` is a symlink | Routing, check #20 |
| `SYMLINK_BROKEN` | Symlink target missing | Repair |
| `SYMLINK_DRIFT` | `readlink vault` disagrees with `VAULT_TARGET` in script | Repair |
| `SCRIPT_EXISTS` | `scripts/setup-vault-symlink.sh` present | Repair (script backfill) |
| `EMBEDDED_OPTOUT` | CLAUDE.md has `\| **Vault layout** \| embedded ... \|` row | Externalization gating, check #20 |

When `REPAIR_REASON=centralized-vault-drift` or `centralized-vault-script-missing`, Partial Ark routing prioritizes the centralized-vault repair subsection (Task 11) over generic Ark-artifact repair.

## Tier Selection

| Tier | What Gets Set Up | Time |
|------|-----------------|------|
| **Quick** | CLAUDE.md + vault structure + Python check + index generation | ~5 min |
| **Standard** | Quick + TaskNotes MCP + Obsidian plugins | ~10 min |
| **Full** | Standard + MemPalace + history hook + NotebookLM CLI + vault mining | ~25 min |

Present tier choices after state detection. Recommend Standard for most users. Note which tiers are available based on current state:

```
Which setup tier would you like?

  [Q] Quick    — CLAUDE.md, vault structure, index (~5 min)
  [S] Standard — Quick + TaskNotes MCP, Obsidian plugins (~10 min)  [recommended]
  [F] Full     — Standard + MemPalace, history hook, NotebookLM (~25 min)

Choose [Q/S/F]:
```

For **Partial Ark (Repair)** and **Healthy** states, also offer tier upgrade:
- If currently at Quick tier: "Upgrade to Standard or Full?"
- If currently at Standard tier: "Upgrade to Full?"
- If already at Full tier: "All tiers complete."

## Entry Flow

```
User runs /ark-onboard
    |
    v
[1] Check plugins (superpowers, gstack, obsidian)
    |
    v
[2] Missing critical plugin? --> Show install commands, PAUSE for user to install
    Missing standard plugin?  --> Note for later, continue
    |
    v
[3] Run state detection (vault scan + CLAUDE.md check + artifact count)
    |
    v
[4] State = No Vault?       --> Ask tier --> Execute Greenfield path
    State = Non-Ark Vault?   --> Ask tier --> Execute Migration path
    State = Partial Ark?     --> Show failures, offer repair + tier upgrade --> Execute Repair path
    State = Healthy?          --> Show scorecard, surface Full tier upgrades --> Execute Healthy path
    |
    v
[5] Run full 19-check diagnostic
    |
    v
[6] Show before/after scorecard
    |
    v
[7] List follow-up reminders
```

---

## Path: No Vault (Greenfield)

This path absorbs all functionality from `/wiki-setup`. It creates a complete Ark project from scratch.

### Prerequisites

Before starting, run these pre-checks:

**Git safety checks:**
```bash
# Is this a git repo?
git rev-parse --git-dir 2>/dev/null && echo "GIT_REPO=yes" || echo "GIT_REPO=no"

# If git repo: is working tree clean?
git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null && echo "CLEAN=yes" || echo "CLEAN=no — warn user to stash"

# Git user configured?
git config user.name 2>/dev/null && echo "GIT_USER=configured" || echo "GIT_USER=missing — warn user"
```

If not a git repo, offer `git init`. If working tree is dirty, warn user and ask them to stash or commit first.

### Greenfield Step 1: Gather project info

> **You are at Step 1 of 18 — Gathering project info.**

Ask the user for 4 fields, with the new centralized-vault defaulting behavior:

**Prompt 1 — Project name:**
```
Project name? (e.g., my-new-project)
```

**Prompt 2 — Task prefix:**
```
Task prefix? (e.g., ArkNew-) — must end with `-`
```

**Prompt 3 — Vault layout:**
```
Vault layout?
  [S] Standalone — flat, project docs at vault root
  [M] Monorepo   — project docs in a subdirectory under vault root
Choose [S/M]:
```

**Prompt 4 — Centralized vault location:**

Compute the default by detecting whether `$HOME/.superset` exists:
```bash
if [ -d "$HOME/.superset" ]; then
  DEFAULT_PATH="\$HOME/.superset/vaults/<project>"
else
  DEFAULT_PATH="\$HOME/Vaults/<project>"
fi
```

Substitute `<project>` with the project name from Prompt 1. Show the literal `$HOME/` form (not expanded) as the default:
```
Where should the centralized vault live?
Default: $DEFAULT_PATH
[press Enter to accept, or type a $HOME-prefixed path]
```

**Prompt 5 — Escape hatch (rare):**
```
Use embedded vault inside the project repo instead? [y/N]
The centralized layout lets multiple worktrees and the Obsidian app share
one source of truth. Pick embedded only if you explicitly want the vault
committed to the project repo.
```

**Validate each answer before proceeding:**

- **Task prefix:** Must end with exactly one `-`. Reject `ArkNew` (no dash) or `ArkNew--` (double dash).
- **Project name:** Lowercase-kebab-case recommended. Warn but allow otherwise.
- **Vault path (if user accepted centralized):**
  - Must start with `$HOME/` or `~/` (normalize `~/` to `$HOME/`). Reject any other absolute path:
    ```bash
    case "$USER_PATH" in
      '$HOME/'*) ;;  # OK
      '~/'*) USER_PATH="\$HOME/${USER_PATH#~/}" ;;  # normalize
      *)
        echo "ERROR: Vault path must be under \$HOME so tracked metadata stays portable."
        echo "To use an external drive, symlink it: ln -s /Volumes/Drive/vaults \$HOME/Vaults"
        echo "Then point the wizard at the \$HOME path."
        # Re-prompt
        ;;
    esac
    ```
  - The resolved absolute path (`eval echo "$USER_PATH"`) must not already exist, OR must exist and be empty. If it exists with content from a different project, refuse (see Edge Cases).
- **Vault path (if user picked embedded):** Default to `./vault/` inside the project repo. Still reject if the path already exists.

**If user picked embedded:** Branch to the "Embedded escape hatch" sub-flow (Task 7). The wizard skips centralized-vault steps (2a-2d) and proceeds with the legacy `./vault/` setup.

**Otherwise:** Continue to Step 2 (Python check), then Steps 2a-2d (centralized setup).

### Greenfield Step 2: Verify Python 3.10+

> **You are at Step 2 of 18 — Python version check.**

```bash
PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ -z "$PYTHON_VERSION" ]; then
  echo "FAIL: python3 not found — install Python 3.10+ before continuing"
  echo "macOS: brew install python@3.12"
  echo "PAUSE — cannot continue without Python"
elif [ "$MAJOR" -gt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]); then
  echo "OK: Python $PYTHON_VERSION"
else
  echo "FAIL: Python $PYTHON_VERSION too old — need >= 3.10"
  echo "PAUSE — cannot continue without Python 3.10+"
fi
```

If Python is missing or too old, PAUSE and tell the user to install before continuing. Do not proceed.

### Greenfield Step 2a: Create centralized vault repo

> **You are at Step 2a of 18 — Creating the centralized vault repo at `<vault_repo_path>`.**

If user picked embedded vault in Step 1 Prompt 5, skip to Step 3 (legacy flow).

```bash
VAULT_REPO_PATH_EXPANDED=$(eval "echo $USER_PATH")

# Edge case: target exists with foreign content
if [ -d "$VAULT_REPO_PATH_EXPANDED" ] && [ -n "$(ls -A "$VAULT_REPO_PATH_EXPANDED" 2>/dev/null)" ]; then
  echo "ERROR: $VAULT_REPO_PATH_EXPANDED already exists with content."
  echo "Inspect it: ls -la $VAULT_REPO_PATH_EXPANDED"
  echo "If it's an orphan from a failed run, delete it and retry: rm -rf $VAULT_REPO_PATH_EXPANDED"
  echo "If it belongs to another project, choose a different path."
  exit 1
fi

mkdir -p "$VAULT_REPO_PATH_EXPANDED"
cd "$VAULT_REPO_PATH_EXPANDED" && git init
```

Write `<vault_repo_path>/.gitignore`:
```
# Obsidian per-user files (tracked plugins go in .obsidian/plugins/)
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/graph.json
.obsidian/themes/

# Plugin data.json files may contain credentials
.obsidian/plugins/*/data.json

# NotebookLM sync state is tracked (shared across environments) — NOT ignored
```

Create the NotebookLM directory and initial empty sync-state (tracked in the vault repo):
```bash
mkdir -p "$VAULT_REPO_PATH_EXPANDED/.notebooklm"
echo '{"last_sync": null, "files": {}}' > "$VAULT_REPO_PATH_EXPANDED/.notebooklm/sync-state.json"
```

Return to the project repo for the next step:
```bash
cd "<project_repo>"
```

### Greenfield Step 2b: Create the symlink

> **You are at Step 2b of 18 — Linking `<project_repo>/vault` to the centralized vault.**

```bash
ln -s "$VAULT_REPO_PATH_EXPANDED" vault
```

Append `vault` to `<project_repo>/.gitignore`. Check if it's already there first:
```bash
grep -qxF 'vault' .gitignore 2>/dev/null || echo 'vault' >> .gitignore
```

Verify:
```bash
test -L vault && test -e vault && echo "vault symlink OK -> $(readlink vault)"
```

### Greenfield Step 2c: Install automation (script + hook)

> **You are at Step 2c of 18 — Installing the post-checkout hook and canonical script.**

Write `<project_repo>/scripts/setup-vault-symlink.sh` using the template from the "`scripts/setup-vault-symlink.sh` template" section above. Substitute:
- `<PROJECT_NAME>` → the project name from Step 1 Prompt 1.
- `<VAULT_REPO_PATH_PORTABLE>` → the `$HOME/`-prefixed form the user entered in Step 1 Prompt 4 (NOT the expanded absolute path). For example, `$HOME/.superset/vaults/my-new-project`.

```bash
mkdir -p scripts
# Use the template from the SKILL.md section above. Key substitutions:
#   VAULT_TARGET="$HOME/.superset/vaults/my-new-project"  (or whatever user chose)
# Write the full template content to scripts/setup-vault-symlink.sh.
chmod +x scripts/setup-vault-symlink.sh
```

Verify the grep contract holds (exactly one matching line, value starts with `$HOME/`):
```bash
MATCH_COUNT=$(grep -cE '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh)
[ "$MATCH_COUNT" -eq 1 ] || { echo "ERROR: script must contain exactly one VAULT_TARGET= line"; exit 1; }
grep -qE '^VAULT_TARGET="\$HOME/' scripts/setup-vault-symlink.sh || { echo "ERROR: VAULT_TARGET must start with \$HOME/"; exit 1; }
```

Install the post-checkout hook in the common `.git` dir (handles worktrees correctly):
```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
# AUTOGENERATED by /ark-onboard — do not hand-edit.
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
HOOK_EOF
chmod +x "$HOOK_PATH"
```

If `<project_repo>/.superset/config.json` exists, append the setup/teardown entries using a python JSON merge (preserve existing entries):

```bash
if [ -f .superset/config.json ]; then
  python3 <<'PY_EOF'
import json, pathlib
p = pathlib.Path('.superset/config.json')
cfg = json.loads(p.read_text())
setup = cfg.setdefault('setup', [])
teardown = cfg.setdefault('teardown', [])
entry_setup = 'bash scripts/setup-vault-symlink.sh'
entry_teardown = '[ -L vault ] && rm vault || true'
if entry_setup not in setup:
    setup.append(entry_setup)
if entry_teardown not in teardown:
    teardown.append(entry_teardown)
p.write_text(json.dumps(cfg, indent=2) + '\n')
print("Updated .superset/config.json")
PY_EOF
fi
```

Final post-install verification:
```bash
test -L vault && test -e vault \
  && test -x "$(git rev-parse --git-common-dir)/hooks/post-checkout" \
  && test -f scripts/setup-vault-symlink.sh \
  && grep -qE '^VAULT_TARGET="\$HOME/' scripts/setup-vault-symlink.sh \
  || { echo "ERROR: post-install verification failed"; exit 1; }
echo "Automation installed."
```

### Greenfield Step 2d: Offer GitHub remote (optional)

> **You are at Step 2d of 18 — Optionally creating a GitHub repo for the vault.**

```bash
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  read -rp "Create a GitHub repo for this vault now? [y/N] " ANS
  case "$ANS" in
    y|Y)
      cd "$VAULT_REPO_PATH_EXPANDED"
      gh repo create --private "<project>-vault" --source=. --push
      cd "<project_repo>"
      ;;
    *)
      echo "Skipped. You can push later with:"
      echo "  cd $VAULT_REPO_PATH_EXPANDED && gh repo create --private <project>-vault --source=. --push"
      ;;
  esac
else
  echo "gh not installed or not authenticated — skipping GitHub remote."
  echo "To create a remote later: cd $VAULT_REPO_PATH_EXPANDED && gh repo create --private <project>-vault --source=. --push"
fi
```

**After Step 2d:** All subsequent greenfield steps (3 through 18) run with `{vault_path}` set to the **centralized** `<vault_repo_path>` (expanded absolute path), NOT the project-repo's `vault` symlink. Directory creation, templates, index generation, and the final `git add . && git commit` happen **inside the centralized vault repo**.

### Greenfield Step 3: Create vault directory structure

> **You are at Step 3 of 18 — Creating directories.**

```bash
mkdir -p {vault_path}/{_Templates,_Attachments,_meta,.obsidian/plugins/{tasknotes,obsidian-git},TaskNotes/{Tasks/{Epic,Story,Bug,Task},Archive/{Epic,Story,Bug,Enhancement},Templates,Views,meta}}
```

For monorepo layout, also create the project docs subdirectory:
```bash
mkdir -p {vault_path}/{project_docs_path}/Session-Logs
```

### Greenfield Step 4: Create 00-Home.md

> **You are at Step 4 of 18 — Creating home page.**

Write `{vault_path}/00-Home.md` (standalone layout) or `{vault_path}/{project_docs_path}/00-Home.md` (monorepo layout):

```markdown
---
title: "{Project Name} Knowledge Base"
type: moc
tags:
  - home
  - dashboard
summary: "Navigation hub for {Project Name}: links to project areas and key resources."
created: {today}
last-updated: {today}
---

# {Project Name} Knowledge Base

## Quick Links

- [[TaskNotes/00-Project-Management-Guide|Project Management Guide]]
- [[_meta/vault-schema|Vault Schema]]
- [[_meta/taxonomy|Tag Taxonomy]]

## Project Areas

> Add links to key project areas as the vault grows.

## Recent Activity

> Recent session logs and task updates will be linked here.
```

Replace `{Project Name}` with the user's project name and `{today}` with today's date in `YYYY-MM-DD` format.

### Greenfield Step 5: Create metadata files

> **You are at Step 5 of 18 — Creating metadata (vault-schema, taxonomy, generate-index.py).**

**`{vault_path}/_meta/vault-schema.md`:**

```markdown
---
title: "Vault Schema"
type: meta
tags:
  - meta
  - schema
summary: "Self-documenting vault structure, folder conventions, and frontmatter spec."
created: {today}
last-updated: {today}
---

# Vault Schema

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `_meta/` | Vault metadata — schema, taxonomy, index generator |
| `_Templates/` | Page templates for session logs, tasks, research |
| `_Attachments/` | Images and binary files |
| `TaskNotes/` | Task management — tasks, archive, counter |
| `TaskNotes/Tasks/` | Active tasks by type (Epic, Story, Bug, Task) |
| `TaskNotes/Archive/` | Completed tasks by type |
| `TaskNotes/meta/` | Task counter and management metadata |

## Frontmatter Conventions

All pages use YAML frontmatter with these standard fields:

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Page title (quoted string) |
| `type` | Yes | Page type: `session-log`, `compiled-insight`, `task`, `research`, `service`, `moc`, `meta` |
| `tags` | Yes | List of tags from taxonomy |
| `summary` | Yes | <= 200 character description |
| `created` | Yes | ISO date (YYYY-MM-DD) |
| `last-updated` | Yes | ISO date (YYYY-MM-DD) |

### Type-Specific Fields

**Session logs:** `prev:`, `epic:`, `session:` (session ID)
**Compiled insights:** `source-sessions:`, `source-tasks:` (lists)
**Tasks:** `task-id:`, `status:`, `priority:`, `component:`

## Notes

- Use `type:` (not `category:`)
- Use `source-sessions:` and `source-tasks:` (not `sources:`)
- Do NOT use `provenance:` markers
```

**`{vault_path}/_meta/taxonomy.md`:**

```markdown
---
title: "Tag Taxonomy"
type: meta
tags:
  - meta
  - taxonomy
summary: "Canonical tag vocabulary for the vault. All tags should come from this list."
created: {today}
last-updated: {today}
---

# Tag Taxonomy

## Structural Tags

| Tag | Used On |
|-----|---------|
| `home` | Home/dashboard page |
| `moc` | Map of Content pages |
| `meta` | Vault metadata pages |
| `session-log` | Session logs |
| `compiled-insight` | Synthesized knowledge from sessions |
| `task` | Task pages |
| `research` | Research findings |
| `service` | Service/infrastructure docs |
| `template` | Template files |

## Status Tags

| Tag | Meaning |
|-----|---------|
| `active` | Currently in progress |
| `archived` | Completed or deprecated |
| `draft` | Work in progress |

## Domain Tags

> Add project-specific domain tags here as the vault grows.
> Keep this list curated — prefer existing tags over creating new ones.
```

**`{vault_path}/_meta/generate-index.py`:**

Write the full index generator script:

```python
#!/usr/bin/env python3
"""Generate index.md — a flat catalog of all vault pages with summaries.

Usage:
    cd vault/
    python3 _meta/generate-index.py

Scans all .md files (excluding index.md, templates, and _meta/),
extracts frontmatter title and summary, and writes index.md.
"""

import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = VAULT_ROOT / "index.md"

EXCLUDE_DIRS = {"_Templates", "_Attachments", "_meta", ".obsidian"}
EXCLUDE_FILES = {"index.md"}


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter fields from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    fm = {}
    for line in match.group(1).splitlines():
        m = re.match(r'^(\w[\w-]*):\s*"?(.*?)"?\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip('"').strip("'")
    return fm


def collect_pages() -> list[dict]:
    """Walk the vault and collect page metadata."""
    pages = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        rel_root = Path(root).relative_to(VAULT_ROOT)
        for fname in sorted(files):
            if not fname.endswith(".md") or fname in EXCLUDE_FILES:
                continue

            filepath = Path(root) / fname
            rel_path = rel_root / fname

            fm = parse_frontmatter(filepath)
            title = fm.get("title", fname.removesuffix(".md"))
            summary = fm.get("summary", "")
            page_type = fm.get("type", "")

            pages.append(
                {
                    "path": str(rel_path),
                    "title": title,
                    "summary": summary,
                    "type": page_type,
                }
            )

    return sorted(pages, key=lambda p: p["path"])


def generate_index(pages: list[dict]) -> str:
    """Render index.md content."""
    lines = [
        "---",
        'title: "Index"',
        "type: meta",
        "tags:",
        "  - meta",
        'summary: "Machine-generated flat catalog of all vault pages."',
        f"last-updated: {__import__('datetime').date.today().isoformat()}",
        "---",
        "",
        "# Index",
        "",
        "<!-- AUTO-GENERATED — do not edit manually. Run: python3 _meta/generate-index.py -->",
        "",
        "| Page | Type | Summary |",
        "|------|------|---------|",
    ]

    for p in pages:
        title = p["title"].replace("|", "\\|")
        summary = p["summary"].replace("|", "\\|")
        page_type = p["type"]
        link = f'[[{p["path"]}|{title}]]'
        lines.append(f"| {link} | {page_type} | {summary} |")

    lines.append("")
    return "\n".join(lines)


def main():
    pages = collect_pages()
    content = generate_index(pages)
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"index.md generated with {len(pages)} entries.")


if __name__ == "__main__":
    main()
```

Make the script executable:
```bash
chmod +x {vault_path}/_meta/generate-index.py
```

### Greenfield Step 6: Create templates

> **You are at Step 6 of 18 — Creating page templates.**

Create these files in `{vault_path}/_Templates/`:

**Session-Template.md:**
```markdown
---
title: ""
type: session-log
tags:
  - session-log
summary: ""
prev: ""
epic: ""
session: ""
created: {{date}}
last-updated: {{date}}
---

# Session: {{title}}

## Goals

-

## Work Done

-

## Decisions

-

## Open Questions

-

## Next Steps

-
```

**Compiled-Insight-Template.md:**
```markdown
---
title: ""
type: compiled-insight
tags:
  - compiled-insight
summary: ""
source-sessions: []
source-tasks: []
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Key Insight

## Evidence

## Implications

## Related
```

**Bug-Template.md:**
```markdown
---
title: ""
type: task
tags:
  - task
  - bug
summary: ""
task-id: ""
status: backlog
priority: ""
component: ""
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Description

## Steps to Reproduce

1.

## Expected Behavior

## Actual Behavior

## Fix
```

**Task-Template.md:**
```markdown
---
title: ""
type: task
tags:
  - task
summary: ""
task-id: ""
status: backlog
priority: ""
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Description

## Acceptance Criteria

-

## Notes
```

**Research-Template.md:**
```markdown
---
title: ""
type: research
tags:
  - research
summary: ""
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Question

## Findings

## Sources

## Conclusions
```

**Service-Template.md:**
```markdown
---
title: ""
type: service
tags:
  - service
summary: ""
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Overview

## Configuration

## Endpoints

## Monitoring

## Runbook
```

### Greenfield Step 7: Create task counter

> **You are at Step 7 of 18 — Task counter setup.**

```bash
echo "1" > {vault_path}/TaskNotes/meta/{task_prefix}counter
```

Note: `{task_prefix}` includes the trailing dash. Counter filename is `{task_prefix}counter` (e.g., `ArkNew-counter`). No double dash.

### Greenfield Step 8: Create project management guide

> **You are at Step 8 of 18 — Project management guide.**

Write `{vault_path}/TaskNotes/00-Project-Management-Guide.md`:

```markdown
---
title: "Project Management Guide"
type: meta
tags:
  - meta
  - task
summary: "How tasks are created, tracked, and archived in this vault."
created: {today}
last-updated: {today}
---

# Project Management Guide

## Task ID Format

All tasks use the prefix `{task_prefix}` followed by a sequential number:
- `{task_prefix}1`, `{task_prefix}2`, `{task_prefix}3`, ...

The counter file at `TaskNotes/meta/{task_prefix}counter` tracks the next available number.

## Task Types

| Type | Folder | Description |
|------|--------|-------------|
| Epic | `Tasks/Epic/` | Large multi-session efforts |
| Story | `Tasks/Story/` | User-facing features |
| Bug | `Tasks/Bug/` | Defects and fixes |
| Task | `Tasks/Task/` | Generic work items |

## Status Values

| Status | Meaning |
|--------|---------|
| `backlog` | Not yet started |
| `todo` | Planned for upcoming work |
| `in-progress` | Currently being worked on |
| `done` | Completed |

## Archive

Completed tasks are moved from `Tasks/{Type}/` to `Archive/{Type}/`.

## Creating Tasks

Use `/ark-tasknotes` to create tasks via the TaskNotes MCP, or create markdown files manually following the templates in `_Templates/`.
```

### Greenfield Step 9: Set up Obsidian configuration

> **You are at Step 9 of 18 — Obsidian configuration files.**

**`{vault_path}/.gitignore`:**
```
# Obsidian — ignore transient state, track plugins and core config
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/graph.json
.obsidian/themes/

# Plugin data.json files may contain credentials — gitignore them
.obsidian/plugins/*/data.json

# NotebookLM sync state is tracked (shared across environments)
```

**`{vault_path}/.obsidian/app.json`:**
```json
{ "alwaysUpdateLinks": true }
```

**`{vault_path}/.obsidian/appearance.json`:**
```json
{}
```

**`{vault_path}/.obsidian/community-plugins.json`:**
```json
["tasknotes", "obsidian-git"]
```

**`{vault_path}/.obsidian/core-plugins.json`:**
```json
["file-explorer","global-search","switcher","graph","markdown-importer","page-preview","note-composer","command-palette","editor-status","outline","word-count","file-recovery","properties"]
```

### Greenfield Step 10: Create/update CLAUDE.md

> **You are at Step 10 of 18 — CLAUDE.md configuration.**

If CLAUDE.md does not exist, create it. If it exists but is missing fields, update it.

**Template for new CLAUDE.md:**

```markdown
# {Project Name}

{Brief description — ask user or leave placeholder}

## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `{vault_root}` |
| **Session Logs** | `{vault_root}Session-Logs/` |
| **Task Management** | `{tasknotes_path}` — prefix: `{task_prefix}`, project: `{project_name}` |
```

**Vault-layout row (conditional):**

If the user picked **centralized** in Step 1, the default layout is symlinked. No extra row needed — check #20 defaults to `pass` when the `vault` symlink resolves.

If the user picked **embedded** (escape hatch), append this row to the Project Configuration table so check #20 recognizes the opt-out:

```markdown
| **Vault layout** | embedded (not symlinked) |
```

Check #20's grep contract: `^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded` (case-insensitive). Do not deviate from this exact row format — the diagnostic won't detect alternatives.

For monorepo layout, adjust the Obsidian Vault row to point at the project docs subdirectory and add the vault root separately.

### Greenfield Step 11: Obsidian plugins (Standard+ tier only)

> **You are at Step 11 of 18 — Obsidian plugin setup (Standard+ only). Skip to Step 16 if Quick tier.**

Install plugin binaries and generate `data.json` configs so the user does not need to configure anything through the Obsidian GUI.

**Primary: Download from GitHub releases (automatic)**

Look up the plugin repos from the Obsidian community plugin registry, then download the latest release assets:

```bash
# Step 1: Resolve plugin repos from Obsidian's community plugin registry
COMMUNITY_PLUGINS=$(curl -sfL "https://raw.githubusercontent.com/obsidianmd/obsidian-releases/master/community-plugins.json" 2>/dev/null)

if [ -n "$COMMUNITY_PLUGINS" ]; then
  TASKNOTES_REPO=$(echo "$COMMUNITY_PLUGINS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if p['id'] == 'tasknotes':
        print(p['repo']); break
" 2>/dev/null)

  GIT_REPO=$(echo "$COMMUNITY_PLUGINS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if p['id'] == 'obsidian-git':
        print(p['repo']); break
" 2>/dev/null)
fi

DOWNLOAD_OK=true

# Step 2: Download TaskNotes plugin
if [ -n "$TASKNOTES_REPO" ]; then
  for FILE in main.js manifest.json styles.css; do
    curl -sfL "https://github.com/$TASKNOTES_REPO/releases/latest/download/$FILE" \
      -o "{vault_path}/.obsidian/plugins/tasknotes/$FILE"
  done
  if [ -s "{vault_path}/.obsidian/plugins/tasknotes/main.js" ]; then
    echo "OK: TaskNotes plugin downloaded from $TASKNOTES_REPO"
  else
    echo "WARN: TaskNotes download failed"
    DOWNLOAD_OK=false
  fi
else
  echo "WARN: Could not resolve TaskNotes repo from registry"
  DOWNLOAD_OK=false
fi

# Step 3: Download Obsidian Git plugin
if [ -n "$GIT_REPO" ]; then
  for FILE in main.js manifest.json styles.css; do
    curl -sfL "https://github.com/$GIT_REPO/releases/latest/download/$FILE" \
      -o "{vault_path}/.obsidian/plugins/obsidian-git/$FILE"
  done
  if [ -s "{vault_path}/.obsidian/plugins/obsidian-git/main.js" ]; then
    echo "OK: Obsidian Git plugin downloaded from $GIT_REPO"
  else
    echo "WARN: Obsidian Git download failed"
    DOWNLOAD_OK=false
  fi
else
  echo "WARN: Could not resolve Obsidian Git repo from registry"
  DOWNLOAD_OK=false
fi
```

**Fallback 1: Copy from reference vault (if download failed)**

If any download failed, ask the user if they have a reference vault:

```bash
if [ "$DOWNLOAD_OK" = "false" ]; then
  echo "Some plugin downloads failed. Do you have a reference vault to copy from?"
  # If yes:
  # TaskNotes (do NOT copy data.json — it's gitignored and project-specific)
  cp {reference_vault}/.obsidian/plugins/tasknotes/main.js {vault_path}/.obsidian/plugins/tasknotes/
  cp {reference_vault}/.obsidian/plugins/tasknotes/manifest.json {vault_path}/.obsidian/plugins/tasknotes/
  cp {reference_vault}/.obsidian/plugins/tasknotes/styles.css {vault_path}/.obsidian/plugins/tasknotes/

  # Obsidian Git
  cp {reference_vault}/.obsidian/plugins/obsidian-git/main.js {vault_path}/.obsidian/plugins/obsidian-git/
  cp {reference_vault}/.obsidian/plugins/obsidian-git/manifest.json {vault_path}/.obsidian/plugins/obsidian-git/
  cp {reference_vault}/.obsidian/plugins/obsidian-git/styles.css {vault_path}/.obsidian/plugins/obsidian-git/
fi
```

**Fallback 2: Manual install (last resort)**

If both download and reference vault fail:
```
Plugin binaries could not be installed automatically. Install manually:
  1. Open the vault in Obsidian
  2. Settings > Community Plugins > Browse
  3. Install "TaskNotes" and "Obsidian Git"
  4. Enable both plugins

PAUSE — manual handoff. Continue when plugins are installed, or type "skip" to proceed without plugins.
```

**PAUSE for manual handoff** only if reaching Fallback 2. If download or reference vault succeeded, continue automatically.

### Greenfield Step 12: Configure plugin data + TaskNotes MCP (Standard+ tier only)

> **You are at Step 12 of 18 — Plugin configuration + TaskNotes MCP (Standard+ only). Skip to Step 16 if Quick tier.**

Generate `data.json` for both plugins so the user does not need to configure anything through the Obsidian GUI. These files are gitignored (per Step 9's `.gitignore`), so each vault gets its own config.

**TaskNotes `data.json`:**

Write `{vault_path}/.obsidian/plugins/tasknotes/data.json`:
```json
{
  "tasksFolder": "TaskNotes/Tasks",
  "moveArchivedTasks": false,
  "archiveFolder": "TaskNotes/Archive",
  "taskTag": "task",
  "taskIdentificationMethod": "tag",
  "taskFilenameFormat": "zettel",
  "storeTitleInFilename": true,
  "defaultTaskStatus": "open",
  "defaultTaskPriority": "normal",
  "apiPort": 8080,
  "enableMCP": true,
  "enableNaturalLanguageInput": true,
  "nlpDefaultToScheduled": true,
  "enableTaskLinkOverlay": true,
  "enableInstantTaskConvert": true,
  "useDefaultsOnInstantConvert": true,
  "enableBases": true,
  "commandFileMapping": {
    "open-calendar-view": "TaskNotes/Views/mini-calendar-default.base",
    "open-kanban-view": "TaskNotes/Views/kanban-default.base",
    "open-tasks-view": "TaskNotes/Views/tasks-default.base",
    "open-advanced-calendar-view": "TaskNotes/Views/calendar-default.base",
    "open-agenda-view": "TaskNotes/Views/agenda-default.base",
    "relationships": "TaskNotes/Views/relationships.base"
  },
  "customStatuses": [
    { "id": "none", "value": "none", "label": "None", "color": "#cccccc", "isCompleted": false, "order": 0, "autoArchive": false, "autoArchiveDelay": 5 },
    { "id": "open", "value": "open", "label": "Open", "color": "#808080", "isCompleted": false, "order": 1, "autoArchive": false, "autoArchiveDelay": 5 },
    { "id": "in-progress", "value": "in-progress", "label": "In progress", "color": "#0066cc", "isCompleted": false, "order": 2, "autoArchive": false, "autoArchiveDelay": 5 },
    { "id": "done", "value": "done", "label": "Done", "color": "#00cc66", "isCompleted": true, "order": 3, "autoArchive": false, "autoArchiveDelay": 5 },
    { "id": "cancelled", "value": "cancelled", "label": "Cancelled", "color": "#cc0000", "isCompleted": true, "order": 4, "autoArchive": false, "autoArchiveDelay": 5 }
  ],
  "fieldMapping": {
    "title": "title",
    "status": "status",
    "priority": "priority",
    "due": "due",
    "scheduled": "scheduled",
    "contexts": "contexts",
    "projects": "projects",
    "timeEstimate": "timeEstimate",
    "completedDate": "completedDate",
    "dateCreated": "dateCreated",
    "dateModified": "dateModified",
    "recurrence": "recurrence",
    "recurrenceAnchor": "recurrence_anchor",
    "archiveTag": "archived",
    "timeEntries": "timeEntries",
    "completeInstances": "complete_instances",
    "skippedInstances": "skipped_instances",
    "blockedBy": "blockedBy",
    "pomodoros": "pomodoros",
    "reminders": "reminders",
    "sortOrder": "tasknotes_manual_order"
  }
}
```

Note: `data.json` is gitignored. Adjust `apiPort` if user has multiple Obsidian instances (suggest unique ports: 8080, 8081, 8082). TaskNotes will populate any missing fields with defaults on first launch — this config covers Ark-specific settings (folder paths, statuses, field mappings, Bases views) so the plugin works correctly without GUI configuration.

**Obsidian Git `data.json`:**

Write `{vault_path}/.obsidian/plugins/obsidian-git/data.json`:
```json
{
  "autoSaveInterval": 5,
  "autoPushInterval": 5,
  "autoPullInterval": 10,
  "autoPullOnBoot": true,
  "disablePush": false,
  "pullBeforePush": true,
  "syncMethod": "merge",
  "autoCommitMessage": "vault backup: {{date}}",
  "commitDateFormat": "YYYY-MM-DD HH:mm:ss",
  "listChangedFilesInMessageBody": false
}
```

Note: This gives sensible defaults (auto-save every 5 min, auto-pull on open, merge strategy). The user can adjust intervals in Obsidian settings later.

**Configure TaskNotes MCP in `.mcp.json` (project root):**

```bash
# Pre-validation: check if .mcp.json exists and is valid JSON
if [ -f .mcp.json ]; then
  python3 -c "import json; json.load(open('.mcp.json'))" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "WARNING: .mcp.json is malformed JSON. Back up and recreate."
    cp .mcp.json .mcp.json.bak
  fi
fi
```

Add or merge `tasknotes` into `.mcp.json` (TaskNotes v4.5+ exposes a built-in MCP server via HTTP on its API port — there is no separate `tasknotes-mcp` npm package):
```json
{
  "mcpServers": {
    "tasknotes": {
      "type": "http",
      "url": "http://localhost:{apiPort}/mcp"
    }
  }
}
```

Where `{apiPort}` comes from the TaskNotes `data.json` above (default: `8080`). Alternatively, use the CLI: `claude mcp add --transport http --scope project tasknotes http://localhost:{apiPort}/mcp`.

### Greenfield Step 13: Install MemPalace (Full tier only)

> **You are at Step 13 of 18 — MemPalace setup (Full only). Skip to Step 15 if Quick or Standard tier.**

```bash
# Check if already installed
command -v mempalace 2>/dev/null && echo "MemPalace already installed: $(mempalace --version 2>/dev/null)" && MEMPALACE_OK=true

# If not installed, try to install
if [ -z "$MEMPALACE_OK" ]; then
  if command -v pipx 2>/dev/null; then
    echo "Installing via pipx..."
    pipx install "mempalace>=3.0.0,<4.0.0"
  elif command -v pip 2>/dev/null; then
    echo "Installing via pip..."
    pip install "mempalace>=3.0.0,<4.0.0"
  else
    echo "WARNING: Neither pipx nor pip available. Cannot install MemPalace."
    echo "Install manually: pip install 'mempalace>=3.0.0,<4.0.0'"
    echo "Skipping MemPalace setup — continuing without it."
    MEMPALACE_OK=false
  fi
fi
```

If install fails, warn and skip. Do not block the rest of the wizard.

### Greenfield Step 14: Run vault mining and install history hook (Full tier only)

> **You are at Step 14 of 18 — Vault mining + history hook (Full only). Skip to Step 15 if Quick or Standard tier.**

**Mine the vault (creates vault content wing):**
```bash
bash skills/shared/mine-vault.sh
```

If `mine-vault.sh` is not found (skill repo not in expected location), warn and skip.

**Install history hook (creates conversation history wing separately):**

Pre-validation before running install script:
```bash
# Verify .claude/settings.json is valid JSON (install-hook.sh uses Python and will fail on malformed JSON)
if [ -f .claude/settings.json ]; then
  python3 -c "import json; json.load(open('.claude/settings.json'))" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "ERROR: .claude/settings.json is malformed JSON. Fix before installing hook."
    echo "Skipping history hook installation."
    SKIP_HOOK=true
  fi
fi

if [ -z "$SKIP_HOOK" ]; then
  bash skills/claude-history-ingest/hooks/install-hook.sh
fi
```

If either step fails, warn and continue. These are non-blocking.

### Greenfield Step 15: Set up NotebookLM (Full tier only)

> **You are at Step 15 of 18 — NotebookLM setup (Full only). Skip to Step 16 if Quick or Standard tier.**

```bash
# Check NotebookLM CLI
command -v notebooklm 2>/dev/null && echo "NotebookLM CLI found" || echo "NotebookLM CLI not found"
```

If not installed:
```
NotebookLM CLI not installed. To install:
  pipx install notebooklm-cli

Then authenticate:
  notebooklm auth login

Skipping NotebookLM setup — you can configure later with /notebooklm-vault.
```

If installed, walk through authentication:
```bash
notebooklm auth check --test 2>/dev/null
if [ $? -ne 0 ]; then
  echo "NotebookLM not authenticated. Run: notebooklm auth login"
  echo "PAUSE — authenticate, then continue."
fi
```

**Create NotebookLM config:**

```bash
mkdir -p {vault_path}/.notebooklm
```

Write `{vault_path}/.notebooklm/config.json`:
```json
{
  "notebooks": {
    "main": { "id": "", "title": "{Project Name}" }
  },
  "persona": "You are a senior engineer reviewing the {project_name} project. Answer questions with specific references. Be thorough and precise.",
  "mode": "detailed",
  "response_length": "longer",
  "vault_root": "."
}
```

Tell user: "Fill in `notebooks.main.id` after creating a notebook in NotebookLM. Then run `/notebooklm-vault setup` to bootstrap."

If NotebookLM CLI is not installed or auth fails, warn and continue. Non-blocking.

### Greenfield Step 16: Generate index

> **You are at Step 16 of 18 — Index generation.**

```bash
cd {vault_path} && python3 _meta/generate-index.py
```

Verify output: "index.md generated with N entries."

### Greenfield Step 17: Git init + initial commit

> **You are at Step 17 of 18 — Git commit.**

**Git safety pre-checks (re-check, may have changed since start):**
```bash
# Is this a git repo?
if ! git rev-parse --git-dir 2>/dev/null; then
  echo "Initializing git repo..."
  git init
fi

# Check git user
git config user.name 2>/dev/null || echo "WARNING: git user.name not set. Run: git config user.name 'Your Name'"
git config user.email 2>/dev/null || echo "WARNING: git user.email not set. Run: git config user.email 'you@example.com'"
```

**Centralized vault (default):** the initial commit of vault content happens in the **vault repo**, not the project repo. The project repo only commits project-level metadata and the tracked script.

```bash
# 1. Commit initial vault state inside the centralized vault repo
cd "$VAULT_REPO_PATH_EXPANDED"
git add .
git commit -m "feat: initialize {project_name} vault with Ark structure"

# 2. Commit project-repo metadata (symlink is gitignored; script + .gitignore + CLAUDE.md + configs are tracked)
cd "<project_repo>"
git add scripts/setup-vault-symlink.sh .gitignore CLAUDE.md
git add .mcp.json .claude/settings.json .notebooklm/config.json 2>/dev/null
if [ -f .superset/config.json ]; then git add .superset/config.json; fi
git commit -m "feat: wire {project_name} project to centralized vault"
```

**Embedded vault (escape hatch):** the legacy single-commit flow applies. `vault/` is a real directory inside the project repo.

```bash
git add {vault_path}/ CLAUDE.md .mcp.json .claude/settings.json .notebooklm/ 2>/dev/null
git commit -m "feat: initialize {project_name} vault with Ark structure (embedded)"
```

If `.mcp.json` or `.claude/settings.json` was modified (Standard+ tier), include them in the commit. The post-checkout hook is NOT tracked in either case — it's installed per-clone by `/ark-onboard`.

### Greenfield Step 18: Final diagnostic + reminders

> **You are at Step 18 of 18 — Final verification.**

Run the full 19-check diagnostic (see Shared Diagnostic Checklist above). Show the scorecard (see Scorecard Output Format below).

Then show follow-up reminders:

```
Setup complete! Follow-up reminders:

1. Open the vault in Obsidian — plugins are pre-configured (if downloaded/copied)
   OR: Install TaskNotes + Obsidian Git via Community Plugins (if manual fallback was needed)
2. Fill in NotebookLM notebook ID in .notebooklm/config.json (if Full tier)
3. Run /ark-health anytime to check ecosystem health
4. Run /ark-onboard again to upgrade tiers
```

Adjust reminders based on what was actually set up:
- If plugins were downloaded from GitHub or copied from reference vault: use "Open the vault in Obsidian — plugins are pre-configured, just enable them in Settings > Community Plugins"
- If manual fallback was needed: use "Install TaskNotes + Obsidian Git via Settings > Community Plugins > Browse"
- Omit NotebookLM reminder if not Full tier
- Omit plugin reminder entirely if Quick tier

---

## Path: Non-Ark Vault (Ark Scaffolding + Externalization Offer)

This path handles two distinct operations:

1. **Ark scaffolding** (inline, safe) — add `_meta/`, `_Templates/`, `TaskNotes/`, etc. to an existing vault that doesn't have Ark structure yet. Runs the 14-step flow below, same as the prior "Migration" behavior. Non-destructive: never deletes or overwrites existing content. Frontmatter changes are explicit and reversible (separate commits).

2. **Externalization** (destructive, plan file only) — if the scaffolded vault is still a real directory inside the project repo (i.e., `vault/` is not a symlink), the wizard also generates a plan file for moving the vault out into its own git repo and creating the symlink. The plan file is NOT executed; the user reviews and runs it via `/executing-plans` (see "Path: Externalization Plan Generation" below).

**Key principle (scaffolding):** additive only. Never delete or overwrite existing content. Frontmatter changes are explicit and reversible (separate commits).

**Key principle (externalization):** destructive steps live in a plan file, never in this skill's inline execution. Preflight gates prevent data loss.

### Migration Step 1: Scan existing vault

> **You are at Step 1 of 14 — Scanning existing vault.**

```bash
# Count existing pages
find {vault_path} -name "*.md" | wc -l

# Check for existing folder structure
ls -d {vault_path}*/ 2>/dev/null

# Check for existing frontmatter patterns
head -20 {vault_path}/*.md 2>/dev/null | head -60

# Check for existing tags
grep -rh "^tags:" {vault_path} --include="*.md" 2>/dev/null | head -10
grep -roh "#[a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sort | uniq -c | sort -rn | head -20
```

Report to user: "Found N pages, M existing tags, the following folder structure..."

### Migration Step 2: Gather project info

> **You are at Step 2 of 14 — Gathering project info.**

Ask the user for:
1. **Project name** — e.g., `my-project`
2. **Task prefix** — e.g., `ArkMy-` (must end with `-`)

The vault path is already known (detected vault directory). Ask user to confirm it as the vault root.

### Migration Step 3: Pre-commit existing state

> **You are at Step 3 of 14 — Checkpointing existing state.**

**Git safety checks:**
```bash
# Is this a git repo?
git rev-parse --git-dir 2>/dev/null && echo "GIT_REPO=yes" || echo "GIT_REPO=no"

# If not a git repo, offer to init
if ! git rev-parse --git-dir 2>/dev/null; then
  echo "Not a git repo. Initializing..."
  git init
fi

# Check working tree
git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null && echo "CLEAN=yes" || echo "CLEAN=no"

# Check git user
git config user.name 2>/dev/null || echo "WARNING: git user.name not set"
```

Commit the pre-migration state:
```bash
git add -A && git commit -m "checkpoint: pre-Ark migration"
```

This gives the user a clean rollback point. If git add/commit fails (nothing to commit), that's fine — continue.

### Migration Step 4: Add Ark scaffolding

> **You are at Step 4 of 14 — Adding Ark scaffolding (non-destructive).**

Create only the directories and files that don't already exist:

```bash
# Create missing directories only
[ -d "{vault_path}_meta" ] || mkdir -p "{vault_path}_meta"
[ -d "{vault_path}_Templates" ] || mkdir -p "{vault_path}_Templates"
[ -d "{vault_path}_Attachments" ] || mkdir -p "{vault_path}_Attachments"
[ -d "{vault_path}.obsidian" ] || mkdir -p "{vault_path}.obsidian"
[ -d "{vault_path}TaskNotes/Tasks/{Epic,Story,Bug,Task}" ] || mkdir -p "{vault_path}TaskNotes/Tasks/"{Epic,Story,Bug,Task}
[ -d "{vault_path}TaskNotes/Archive/{Epic,Story,Bug,Enhancement}" ] || mkdir -p "{vault_path}TaskNotes/Archive/"{Epic,Story,Bug,Enhancement}
[ -d "{vault_path}TaskNotes/{Templates,Views,meta}" ] || mkdir -p "{vault_path}TaskNotes/"{Templates,Views,meta}
```

Do NOT overwrite existing files. Check before writing:
```bash
[ -f "{vault_path}00-Home.md" ] && echo "00-Home.md exists — skipping" || echo "Creating 00-Home.md"
```

Create missing files using the same templates from Greenfield Steps 4-9, but only if they don't already exist.

### Migration Step 5: Generate vault-schema.md

> **You are at Step 5 of 14 — Creating vault schema.**

Write `{vault_path}/_meta/vault-schema.md` using the template from Greenfield Step 5. If the file already exists, ask user before overwriting.

### Migration Step 6: Scan tags and propose taxonomy

> **You are at Step 6 of 14 — Building tag taxonomy.**

```bash
# Collect all tags from existing vault
grep -roh "^  - [a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sed 's/^  - //' | sort | uniq -c | sort -rn
grep -roh "#[a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sed 's/^#//' | sort | uniq -c | sort -rn
```

Map existing tags to Ark structural tags. Show the mapping:

```
Proposed tag taxonomy:

Existing tags kept as-is:
  - {tag1} (N pages)
  - {tag2} (N pages)

Mapped to Ark structural tags:
  - {old_tag} -> session-log
  - {old_tag} -> task

New Ark structural tags (added):
  - compiled-insight
  - moc
  - meta

Accept this taxonomy? [y/n/edit]
```

Write `{vault_path}/_meta/taxonomy.md` with the accepted taxonomy.

### Migration Step 7: Offer frontmatter backfill

> **You are at Step 7 of 14 — Frontmatter backfill (optional).**

Show 3 sample pages with their current frontmatter and proposed Ark frontmatter:

```
Sample backfill preview:

--- Page: existing-page.md ---
Current:
  category: note
  tags: [some-tag]

Proposed:
  type: research
  tags:
    - research
    - some-tag
  summary: ""
  created: 2025-01-15
  last-updated: 2025-01-15

--- Page: another-page.md ---
...

Apply frontmatter backfill to all N pages? [y/n/select]
```

**Skip non-standard pages** during bulk backfill. Do NOT touch pages that:
- Have no YAML frontmatter (first line is not `---`)
- Have fenced code blocks (`` ``` ``) at the top of the file
- Fail UTF-8 decoding
- Are binary files masquerading as `.md`

Log skipped pages in the output: `Skipped: {filename} — {reason}`

If user accepts:
```bash
# Apply backfill (done by Claude reading and editing each file, skipping non-standard)
# Then commit separately
git add -A && git commit -m "chore: backfill Ark frontmatter on N pages (M skipped)"
```

This is a **separate commit** from the scaffolding — makes it individually revertable.

If user declines, skip. Frontmatter can be added later with `/wiki-lint --fix`.

### Migration Step 8: Create task counter and management guide

> **You are at Step 8 of 14 — Task management setup.**

Same as Greenfield Steps 7-8. Create counter file and project management guide.

### Migration Step 9: Set up Obsidian configuration

> **You are at Step 9 of 14 — Obsidian configuration.**

Same as Greenfield Step 9, but check for existing `.obsidian/` config files first:

```bash
# Only create config files that don't exist
[ -f "{vault_path}.obsidian/app.json" ] || echo '{ "alwaysUpdateLinks": true }' > "{vault_path}.obsidian/app.json"
[ -f "{vault_path}.obsidian/appearance.json" ] || echo '{}' > "{vault_path}.obsidian/appearance.json"
```

For `community-plugins.json`: merge existing plugin list with Ark plugins (don't remove what's already there):
```bash
# If community-plugins.json exists, merge lists
# If not, create with Ark defaults
```

For `.gitignore`: append Ark patterns if not already present, don't overwrite existing patterns.

### Migration Step 10: Create/update CLAUDE.md

> **You are at Step 10 of 14 — CLAUDE.md configuration.**

Same as Greenfield Step 10. If CLAUDE.md exists, update it with vault-related fields. If it doesn't exist, create it.

### Migration Step 11: Standard/Full tier steps

> **You are at Step 11 of 14 — Tier-specific setup.**

**Standard tier:** Same as Greenfield Steps 11-12 (Obsidian plugins + TaskNotes MCP).

**Full tier:** Same as Greenfield Steps 13-15 (MemPalace + history hook + NotebookLM).

### Migration Step 12: Generate index

> **You are at Step 12 of 14 — Index generation.**

```bash
cd {vault_path} && python3 _meta/generate-index.py
```

### Migration Step 13: Run diagnostic

> **You are at Step 13 of 14 — Diagnostic check.**

Run the full 19-check diagnostic. Show scorecard.

### Migration Step 14: Final commit + reminders

> **You are at Step 14 of 14 — Final commit.**

```bash
git add -A && git commit -m "feat: add Ark scaffolding to {project_name} vault"
```

Show follow-up reminders (same as Greenfield Step 18, adjusted for migration context).

### Migration Step 15: Offer externalization (if vault is still embedded)

> **You are at Step 15 of 15 — Externalization offer.**

```bash
# Re-detect: is vault/ still a real directory (not a symlink)?
if [ -d vault ] && [ ! -L vault ]; then
  echo "Ark scaffolding complete. The vault is still embedded inside the project repo."
  echo "To externalize it (recommended for worktree/Obsidian-app consistency), run:"
  echo "  /ark-onboard"
  echo "The wizard will detect the embedded-Ark state and generate an externalization plan."
fi
```

This is a pointer only — it does NOT generate the plan inline. The externalization offer triggers when the user re-runs `/ark-onboard` and state detection classifies the project as `Partial Ark (real vault/ with Ark artifacts, no opt-out)`.

---

## Path: Externalization Plan Generation

**Triggered when:** State detection finds `vault/` is a real directory with Ark artifacts (`STATE=partial_ark` from artifact count OR from a prior Ark-scaffolded embedded vault), AND `EMBEDDED_OPTOUT=false`.

**Behavior:** No filesystem changes except creating the plan file. User reviews and executes via `/executing-plans`.

### Externalization Step 1: Prompt user for target path + remote

> **You are at Step 1 of 2 — Gathering externalization parameters.**

```bash
# Compute default path (same logic as Greenfield)
if [ -d "$HOME/.superset" ]; then
  DEFAULT_PATH="\$HOME/.superset/vaults/<project>"
else
  DEFAULT_PATH="\$HOME/Vaults/<project>"
fi

echo "Detected: vault/ is committed to this repo as a real directory."
echo "The Ark convention is to externalize it. I'll generate a plan file"
echo "(no destructive actions). You can review and run it via /executing-plans."
echo ""
read -rp "Centralized location for the extracted vault [default: $DEFAULT_PATH]: " USER_PATH
USER_PATH="${USER_PATH:-$DEFAULT_PATH}"

# Path constraint (same as Greenfield)
case "$USER_PATH" in
  '$HOME/'*) ;;
  '~/'*) USER_PATH="\$HOME/${USER_PATH#~/}" ;;
  *) echo "ERROR: path must start with \$HOME/ or ~/"; exit 1 ;;
esac

read -rp "Create a GitHub repo for the vault now? [y/N] " WANT_GH
case "$WANT_GH" in y|Y) WANT_GH=true ;; *) WANT_GH=false ;; esac
```

### Externalization Step 2: Generate the plan file

> **You are at Step 2 of 2 — Writing plan file.**

Discover sibling worktrees for inclusion in the plan's Phase 2:
```bash
SIBLINGS=$(git worktree list --porcelain | awk '/^worktree /{print $2}' | grep -v "^$(git rev-parse --show-toplevel)$")
```

Write `docs/superpowers/plans/$(date +%Y-%m-%d)-externalize-vault.md`. Substitute at generation time:
- `<PROJECT>` → project name (from CLAUDE.md)
- `<VAULT_REPO_PATH_PORTABLE>` → user's chosen path (e.g., `$HOME/.superset/vaults/my-project`)
- `<VAULT_REPO_PATH_EXPANDED>` → `eval "echo $USER_PATH"`
- `<SIBLINGS>` → newline-separated list; inject one Phase 2 sub-step per sibling
- `<WANT_GH>` → true/false; only include Phase 1 step 12 if true

**Plan file template:**

````markdown
# Externalize Vault for <PROJECT>

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this plan step-by-step, stopping for review between phases.

**Goal:** Move the currently-embedded `vault/` directory out of the project repo into its own git repo at `<VAULT_REPO_PATH_PORTABLE>` and replace `vault/` with a symlink.

**Safety model:** Phase 0 is preflight (no mutation). Phase 1 operates on the main repo + vault target atomically. Phase 2 operates on sibling worktrees one at a time, with explicit confirmation each. Phase 3 is manual follow-up.

---

## Phase 0 — Preflight (no mutation)

### Step 0.1: Discover sibling worktrees
- [ ] Run: `git worktree list --porcelain | awk '/^worktree /{print $2}'`
- [ ] Record the list. The main repo is the first entry. Siblings are the rest.
- [ ] For this execution, siblings are: `<SIBLINGS>`

### Step 0.2: Confirm every sibling has a real `vault/` directory (not symlinks)
- [ ] For each sibling `S`, run: `[ -d "$S/vault" ] && [ ! -L "$S/vault" ] && echo "$S: OK" || echo "$S: ABORT ($S/vault is missing or a symlink)"`
- [ ] If any sibling reports ABORT, stop the plan. Resolve manually and re-run `/ark-onboard` to regenerate the plan.

### Step 0.3: Pairwise compare sibling vault contents (git diff)
- [ ] Pick the main repo as baseline. For every other sibling `S`, run:
```bash
git -c core.safecrlf=false diff --no-index --stat -- <MAIN>/vault "$S/vault"
```
- [ ] Non-zero exit OR non-empty output means divergence. **Abort on divergence.** Print the full diff for each divergent pair.

### Step 0.4: Supplementary empty-directory comparison
Git does not track empty dirs; compare their shape explicitly:
- [ ] For each sibling pair (baseline, `S`):
```bash
diff <(cd <MAIN>/vault && find . -type d -empty | sort) <(cd "$S/vault" && find . -type d -empty | sort)
```
- [ ] If non-empty output, treat as divergence and abort.

### Step 0.5: Check for uncommitted / untracked content under `vault/`
- [ ] For each sibling `S`:
```bash
(cd "$S" && git status --porcelain vault/)
```
- [ ] If any output, abort with instructions to commit or discard first.

### Step 0.6: Confirm target path is empty or absent
- [ ] `ls -la <VAULT_REPO_PATH_EXPANDED> 2>/dev/null || echo "not present (OK)"`
- [ ] If the directory exists and has content, abort. If empty or absent, proceed.

**Phase 0 gate:** All steps above must succeed. If anything aborts, stop the plan, resolve manually, and regenerate the plan via `/ark-onboard`.

---

## Phase 1 — Externalize (destructive; main repo + vault target only)

### Step 1.1: Initialize the centralized vault repo
- [ ] `mkdir -p <VAULT_REPO_PATH_EXPANDED>`
- [ ] `cd <VAULT_REPO_PATH_EXPANDED> && git init`

### Step 1.2: Copy vault contents
- [ ] From the main project repo root:
```bash
cp -a vault/. <VAULT_REPO_PATH_EXPANDED>/
```
- [ ] Verify: `diff -qr vault/ <VAULT_REPO_PATH_EXPANDED>/ | head` should report only the `.git/` difference (the vault repo has its own `.git/` from Step 1.1).

### Step 1.3: Move NotebookLM config into the vault
- [ ] If `<MAIN>/.notebooklm/config.json` exists:
```bash
mkdir -p <VAULT_REPO_PATH_EXPANDED>/.notebooklm
cp <MAIN>/.notebooklm/config.json <VAULT_REPO_PATH_EXPANDED>/.notebooklm/config.json
# Update vault_root to "."
python3 -c "
import json, pathlib
p = pathlib.Path('<VAULT_REPO_PATH_EXPANDED>/.notebooklm/config.json')
c = json.loads(p.read_text())
c['vault_root'] = '.'
p.write_text(json.dumps(c, indent=2) + '\n')
"
```
- [ ] The project's `<MAIN>/.notebooklm/config.json` keeps `vault_root: "vault"` (resolves via the forthcoming symlink).

### Step 1.4: Move NotebookLM sync-state
- [ ] If `<MAIN>/.notebooklm/sync-state.json` exists, move it:
```bash
mv <MAIN>/.notebooklm/sync-state.json <VAULT_REPO_PATH_EXPANDED>/.notebooklm/sync-state.json
```
- [ ] Otherwise, create empty state:
```bash
echo '{"last_sync": null, "files": {}}' > <VAULT_REPO_PATH_EXPANDED>/.notebooklm/sync-state.json
```

### Step 1.5: Write vault repo `.gitignore`
- [ ] Write `<VAULT_REPO_PATH_EXPANDED>/.gitignore` with Obsidian per-user files only (`sync-state.json` is NOT ignored):
```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/graph.json
.obsidian/themes/
.obsidian/plugins/*/data.json
```

### Step 1.6: Initial commit in the vault repo
- [ ] `cd <VAULT_REPO_PATH_EXPANDED> && git add . && git commit -m "Initial externalized vault"`

### Step 1.7 (optional): Create GitHub remote
- [ ] If user requested a remote AND `gh` is authenticated:
```bash
cd <VAULT_REPO_PATH_EXPANDED> && gh repo create --private <PROJECT>-vault --source=. --push
```
- [ ] On failure, keep the local repo. Print manual-create instructions. Do NOT roll back.

### Step 1.8: Remove `vault/` from project repo tracking
- [ ] `cd <MAIN> && git rm -r --cached vault/`

### Step 1.9: Add `vault` to `.gitignore`
- [ ] `grep -qxF 'vault' <MAIN>/.gitignore || echo 'vault' >> <MAIN>/.gitignore`

### Step 1.10: Replace real dir with symlink
- [ ] `cd <MAIN> && rm -rf vault && ln -s <VAULT_REPO_PATH_EXPANDED> vault`
- [ ] Verify: `test -L vault && test -e vault && echo "symlink OK -> $(readlink vault)"`

### Step 1.11: Write the canonical script + install the post-checkout hook
- [ ] Write `<MAIN>/scripts/setup-vault-symlink.sh` using the template from `skills/ark-onboard/SKILL.md`. Set `VAULT_TARGET="<VAULT_REPO_PATH_PORTABLE>"` (literal `$HOME/...` form).
- [ ] `chmod +x <MAIN>/scripts/setup-vault-symlink.sh`
- [ ] Install the post-checkout hook:
```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
HOOK_EOF
chmod +x "$HOOK_PATH"
```
- [ ] If `<MAIN>/.superset/config.json` exists, append setup/teardown entries (see Greenfield Step 2c).

### Step 1.12: Update CLAUDE.md "Obsidian Vault" row
- [ ] Edit `<MAIN>/CLAUDE.md`: change the `| **Obsidian Vault** |` row value to note the symlink, e.g.:
```
| **Obsidian Vault** | `vault/` (symlink to `<VAULT_REPO_PATH_PORTABLE>`) |
```

### Step 1.13: Commit the project-repo changes
- [ ] `cd <MAIN> && git add scripts/setup-vault-symlink.sh .gitignore CLAUDE.md .notebooklm/config.json`
- [ ] If `.superset/config.json` changed: `git add .superset/config.json`
- [ ] `git commit -m "Externalize vault: symlink vault/ to <VAULT_REPO_PATH_PORTABLE>"`

**Phase 1 gate:** Main repo has a working `vault` symlink. `git status` is clean. Vault repo has its initial commit. Do NOT proceed to Phase 2 until verified.

---

## Phase 2 — Sibling worktrees (destructive, one at a time)

For each sibling worktree found in Phase 0.1 (excluding `<MAIN>`):

### Step 2.<N>: Convert sibling `<SIBLING>` vault to symlink
- [ ] Confirm this sibling was marked identical in Phase 0.3/0.4.
- [ ] Prompt: `Proceed with sibling <SIBLING>? [y/N]`
- [ ] If yes:
```bash
rm -rf "<SIBLING>/vault"
ln -s "<VAULT_REPO_PATH_EXPANDED>" "<SIBLING>/vault"
```
- [ ] Verify: `test -L <SIBLING>/vault && test -e <SIBLING>/vault && echo "OK"`
- [ ] If no, skip this sibling. Note that this sibling will be in a mixed state until converted manually.

(Repeat for each sibling; inject one step per sibling from `<SIBLINGS>` at generation time.)

**Phase 2 gate:** All confirmed siblings have working `vault` symlinks. Any skipped siblings are documented.

---

## Phase 3 — Manual follow-ups

### Step 3.1: Reopen vault in Obsidian desktop app
- [ ] Close the old `vault/` in Obsidian (if open).
- [ ] Open `<VAULT_REPO_PATH_EXPANDED>/` as the new vault.
- [ ] Verify `obsidian-cli` now points at the same directory the agents use.

### Step 3.2: Re-run /ark-health
- [ ] `cd <MAIN> && /ark-health`
- [ ] Check #20 should return `pass` (symlink matches VAULT_TARGET, target exists).
- [ ] All other checks should be unchanged from pre-externalization.

### Step 3.3: Optional — push the vault repo
- [ ] If GitHub remote was created in Step 1.7: already pushed.
- [ ] If not and user wants one later: `cd <VAULT_REPO_PATH_EXPANDED> && gh repo create --private <PROJECT>-vault --source=. --push`

---

## Rollback (if Phase 1 fails partway)

If the plan aborts during Phase 1:
- **Before Step 1.8:** No destructive project-repo changes yet. Delete `<VAULT_REPO_PATH_EXPANDED>` and retry.
- **After Step 1.8, before Step 1.10:** `git reset HEAD vault/` to un-stage the `git rm --cached`, then re-run from 1.8.
- **After Step 1.10:** The real directory is gone. Rollback: `rm <MAIN>/vault && cp -a <VAULT_REPO_PATH_EXPANDED> <MAIN>/vault && git reset HEAD vault/`.
- **After Step 1.13 (committed):** `git revert HEAD` and delete `<VAULT_REPO_PATH_EXPANDED>`.

Never rollback Phase 2 automatically. Each sibling is handled independently.
````

After writing the plan file:

```bash
PLAN_FILE="docs/superpowers/plans/$(date +%Y-%m-%d)-externalize-vault.md"
echo ""
echo "Plan file written to: $PLAN_FILE"
echo ""
echo "Sibling worktrees that will be touched:"
echo "<SIBLINGS>"
echo ""
echo "Next step: review the plan, then run /executing-plans $PLAN_FILE"
```

**Exit the wizard.** No filesystem changes beyond the plan file.

---

## Path: Partial Ark (Repair)

For vaults that have Ark structure but some checks are failing.

### Centralized-Vault Repair (triggered before generic repair)

If state detection set `REPAIR_REASON=centralized-vault-drift` or `centralized-vault-script-missing`, run this subsection FIRST — before the generic 5-step repair flow below. These are idempotent, non-destructive fixes.

**Determine `<vault_repo_path>` in this order:**

1. If `scripts/setup-vault-symlink.sh` exists, extract `VAULT_TARGET` via the grep contract, then expand `$HOME`:
```bash
SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
VAULT_REPO_PATH_EXPANDED=$(eval "echo $SCRIPT_TARGET")
```
2. Else if `vault` is a broken symlink, use `readlink vault` as the intended target.
3. Else prompt the user with the Greenfield smart default (detect `$HOME/.superset/` etc.).

**Apply fixes based on the specific failure:**

- **`vault` missing entirely + script present:**
```bash
read -rp "Recreate vault symlink to $VAULT_REPO_PATH_EXPANDED? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  if [ -d "$VAULT_REPO_PATH_EXPANDED" ]; then
    ln -s "$VAULT_REPO_PATH_EXPANDED" vault
    echo "vault symlink recreated."
  else
    echo "ERROR: $VAULT_REPO_PATH_EXPANDED not present. Clone the vault repo there first:"
    echo "  git clone <remote> $VAULT_REPO_PATH_EXPANDED"
  fi
;; esac
```

- **`vault` is a broken symlink:**
```bash
read -rp "Remove broken symlink and relink? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  TARGET=$(readlink vault)
  rm vault
  if [ -d "$TARGET" ]; then
    ln -s "$TARGET" vault
    echo "symlink recreated."
  else
    echo "Original target $TARGET missing. Clone or restore it, then rerun /ark-onboard."
  fi
;; esac
```

- **Symlink drift (`readlink vault` != script's `VAULT_TARGET`):**
```bash
SYMLINK_TARGET=$(readlink vault)
echo "Drift detected:"
echo "  vault symlink points to: $SYMLINK_TARGET"
echo "  script VAULT_TARGET expands to: $VAULT_REPO_PATH_EXPANDED"
echo ""
echo "Which is canonical? Choose one:"
echo "  [S] Trust the symlink — update the script's VAULT_TARGET to match."
echo "  [V] Trust the script — remove the symlink and recreate from VAULT_TARGET."
echo "  [N] Do nothing — leave as-is."
read -rp "Choice [S/V/N]: " ANS
case "$ANS" in
  S|s)
    # Convert back to portable form (if possible)
    PORTABLE=$(echo "$SYMLINK_TARGET" | sed "s|^$HOME|\$HOME|")
    case "$PORTABLE" in
      '$HOME/'*)
        sed -i.bak -E "s|^VAULT_TARGET=\"[^\"]*\"|VAULT_TARGET=\"$PORTABLE\"|" scripts/setup-vault-symlink.sh
        rm scripts/setup-vault-symlink.sh.bak
        echo "Script updated. Commit the change."
        ;;
      *)
        echo "ERROR: current symlink target $SYMLINK_TARGET is not under \$HOME."
        echo "Move the vault under \$HOME first, then rerun."
        ;;
    esac
    ;;
  V|v)
    rm vault
    if [ -d "$VAULT_REPO_PATH_EXPANDED" ]; then
      ln -s "$VAULT_REPO_PATH_EXPANDED" vault
      echo "Symlink recreated from script VAULT_TARGET."
    else
      echo "ERROR: $VAULT_REPO_PATH_EXPANDED not present. Fix the script OR clone to that path."
    fi
    ;;
  *) echo "No changes made." ;;
esac
```

- **`scripts/setup-vault-symlink.sh` missing but symlink is valid (backfill, e.g., ArkNode-Poly's original hand-rolled layout):**
```bash
SYMLINK_TARGET=$(readlink vault)
PORTABLE=$(echo "$SYMLINK_TARGET" | sed "s|^$HOME|\$HOME|")
case "$PORTABLE" in
  '$HOME/'*)
    read -rp "Backfill scripts/setup-vault-symlink.sh with VAULT_TARGET=$PORTABLE? [Y/n] " ANS
    case "$ANS" in n|N) ;; *)
      mkdir -p scripts
      # Write the template from the SKILL.md "scripts/setup-vault-symlink.sh template" section,
      # with VAULT_TARGET set to $PORTABLE.
      # (Template body elided here — see the canonical section for the exact content.)
      chmod +x scripts/setup-vault-symlink.sh
      echo "Script backfilled."
    ;; esac
    ;;
  *) echo "Current symlink target not under \$HOME. Cannot backfill portable script."; ;;
esac
```

- **`<common_git_dir>/hooks/post-checkout` missing or non-executable:**
```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
read -rp "Install post-checkout hook at $HOOK_PATH? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
HOOK_EOF
  chmod +x "$HOOK_PATH"
  echo "Hook installed."
;; esac
```

After centralized-vault repairs complete, fall through to the generic 5-step repair flow below (it will re-run the diagnostic and catch any remaining failures).

### Repair Step 1: Run full diagnostic

> **You are at Step 1 — Diagnostic scan.**

Run all 19 checks. Record which checks fail.

### Repair Step 2: Show failures

> **You are at Step 2 — Showing failures.**

Display the scorecard with all failures highlighted. Group by severity:

```
Ark Health — Repair Mode

Critical failures (must fix):
  !! Check 5: CLAUDE.md missing task prefix
  !! Check 8: Vault structure missing _Templates/

Standard failures (recommended):
  !! Check 11: Task counter file not found
  !! Check 13: TaskNotes MCP not configured
  !! Check 16: History auto-index hook not registered (mempalace installed but hook dormant)

Warnings (non-blocking, review interactively):
  ~~ Check 16: Wing-mismatch — expected -my-project, found -my-project-subdir
  ~~ Check 16: Threshold-lock — baseline stuck at 4319 drawers

Available upgrades:
  -- Check 14: MemPalace not installed
  -- Check 17: NotebookLM not installed

Fix critical + standard issues now? [y/n]
```

**Check 16 classification logic.** Check 16 is special — where it lands depends on adjacent state:

| Condition | Classification |
|-----------|----------------|
| MemPalace installed (Check 14 pass) AND vault wing has drawers (Check 15 pass) AND hook NOT registered in project-local settings | **Standard failure** — defensive coverage: project-local registration ensures the hook fires even if the user ever unsets their global `~/.claude/settings.json`. Note: Claude Code merges hook arrays from global + project-local, so in most cases the global hook is already firing and this is cosmetic. Auto-fix in Step 3 is still worthwhile for defense-in-depth. |
| MemPalace NOT installed | **Available upgrade** — hook depends on mempalace; present as Full-tier upgrade. |
| Hook registered but sub-warnings (wing-mismatch / threshold-staleness / threshold-lock) fire | **Warning** — surface in the new interactive review subsection of Step 3. Do NOT auto-fix. `threshold-lock` is the high-signal one — it's the failure mode that looks like "the hook isn't running" but is actually a stuck baseline. |

### Repair Step 3: Fix each failing check

> **You are at Step 3 — Applying fixes.**

Fix checks in order (Critical first, then Standard). For each fix:

1. State what is being fixed: "Fixing Check N: {description}"
2. Apply the fix instruction from the diagnostic checklist
3. Verify the fix: re-run the specific check
4. Report result: "Check N: FIXED" or "Check N: STILL FAILING — {reason}"

**Critical fixes (checks 4-9):**
- Check 4 (CLAUDE.md missing): Create CLAUDE.md using template from Greenfield Step 10
- Check 5 (missing fields): Add missing fields interactively (ask user for values)
- Check 6 (task prefix): Fix prefix format or create counter file
- Check 7 (vault dir): Create vault directory or fix path in CLAUDE.md
- Check 8 (vault structure): Create missing subdirectories
- Check 9 (Python): Cannot auto-fix — tell user to install, PAUSE

**Standard fixes (checks 10-13, 16):**
- Check 10 (index): Regenerate with `python3 _meta/generate-index.py`
- Check 11 (counter): Create counter file: `echo "1" > {path}`
- Check 12 (plugins): Download from GitHub releases (see Greenfield Step 11). If download fails, fall back to reference vault copy, then manual install as last resort
- Check 13 (MCP): Add tasknotes HTTP transport to `.mcp.json`: `{"mcpServers":{"tasknotes":{"type":"http","url":"http://localhost:{apiPort}/mcp"}}}` (or run `claude mcp add --transport http --scope project tasknotes http://localhost:{apiPort}/mcp`)
- Check 16 (hook registration): Only reclassified as Standard when mempalace + wing are present. Fix: `bash skills/claude-history-ingest/hooks/install-hook.sh` from the project root. This adds a project-local entry; Claude Code will merge it with the global registration and the shared hook lock de-duplicates the actual mine call, so the practical effect is defensive rather than functional in most setups.

### Repair Step 3b: Warnings (interactive review)

> **You are at Step 3b — Reviewing warnings.**

Check 16's sub-warnings (wing-mismatch, threshold-staleness, threshold-lock) need human judgment
because the "right" answer depends on intent. Present each warning individually and ask the user
to choose: fix now, skip, or explain.

**Wing-mismatch (example: `-ArkNode-AI` expected, `-ArkNode-AI-projects-trading-signal-ai` found):**
- Fix now → Run `bash skills/shared/mine-vault.sh` from the current CWD to index the current project as its own wing.
- Skip → The subproject is the intended wing (e.g., monorepo or active subproject).
- Explain → "Wing is derived from CWD. If you usually run Claude from a subproject root, that subproject will be the wing root. Sessions run from the parent would not accumulate into this wing."

**Threshold-staleness (new_drawers >= 200):**
- Fix now → Run `/claude-history-ingest compile` to clear the backlog and reset the baseline.
- Skip → You plan to compile manually later.
- Explain → "The Stop hook appends to drawer count but only triggers compile when new_drawers >= 50. If compile has never fired despite a large backlog, something prevented it (hook error, session-end abort). Compiling manually restores the invariant."

**Threshold-lock (current == baseline, baseline > 500):**
- Fix now → Reset baseline: `jq '."<wing>".drawers_at_last_compile = 0' ~/.mempalace/hook_state/compile_threshold.json > /tmp/t && mv /tmp/t ~/.mempalace/hook_state/compile_threshold.json`
- Skip → Let natural drawer accumulation unstick it (may take several sessions).
- Explain → "After a successful compile, the hook stores current drawer count as the new baseline. If no new sessions get indexed, current stays equal to baseline and new_drawers stays at 0, so compile never re-fires. Resetting baseline to 0 makes the next 50 drawers trigger compile; otherwise natural use unsticks it."

### Repair Step 4: Offer tier upgrade

> **You are at Step 4 — Tier upgrade offer.**

After fixes, determine current tier and offer upgrade:

```
All Critical + Standard checks now pass. Current tier: Standard.

Upgrade to Full tier? This adds:
  - MemPalace (deep vault search + synthesis)
  - History auto-index hook (zero-token session capture)
  - NotebookLM CLI (fastest vault queries)

Estimated time: ~15 min. Upgrade? [y/n]
```

If user accepts, execute Greenfield Steps 13-15 (MemPalace + hook + NotebookLM).

### Repair Step 5: Final diagnostic + scorecard

> **You are at Step 5 — Before/after comparison.**

Run all 19 checks again. Show before/after scorecard:

```
Ark Health — Repair Complete

Before: 5 pass, 6 fail, 8 skip
After:  14 pass, 0 fail, 5 upgrade

{full scorecard here}
```

---

## Path: Healthy

For projects where all Critical + Standard checks pass.

### Healthy Step 1: Run full diagnostic

> **You are at Step 1 — Diagnostic scan.**

Run all 19 checks. All Critical and Standard checks should pass.

### Healthy Step 2: Show scorecard

> **You are at Step 2 — Status report.**

Display the full scorecard. Highlight the current tier.

### Healthy Step 3: Surface upgrade opportunities

> **You are at Step 3 — Upgrade opportunities.**

If not at Full tier, show what's available:

```
Current tier: Standard. Available upgrades:

  MemPalace — deep vault search + experiential synthesis
    Install: pipx install "mempalace>=3.0.0,<4.0.0"
    Then run: bash skills/shared/mine-vault.sh

  History hook — auto-index Claude sessions on exit
    Install: bash skills/claude-history-ingest/hooks/install-hook.sh

  NotebookLM — fastest pre-synthesized vault queries
    Install: pipx install notebooklm-cli
    Then configure: /notebooklm-vault setup

Upgrade to Full tier now? [y/n]
```

If user accepts, execute Greenfield Steps 13-15. Then re-run diagnostic and show updated scorecard.

If already at Full tier:
```
All 19 checks pass. Full tier active.
No upgrades available. Run /ark-health anytime to verify.
```

---

## Scorecard Output Format

Use this exact format for all scorecard output:

```
+--------------------------------------+
|        Ark Setup -- Scorecard        |
+--------------------------------------+
| CLAUDE.md          OK  configured    |
| Vault structure    OK  healthy       |
| Python             OK  3.12          |
| Index              OK  fresh         |
| Task counter       OK  ready         |
| Superpowers plugin OK  v5.0.7        |
| Obsidian plugin    OK  v1.0.1        |
| Gstack plugin      OK  detected      |
| TaskNotes MCP      OK  connected     |
| MemPalace          --  not installed |
| NotebookLM         --  not installed |
+--------------------------------------+
| Tier: Standard                       |
| 0 fixes, 0 warnings, 2 upgrades     |
| Run /ark-health anytime to check     |
+--------------------------------------+
```

**Scorecard rules:**

- Symbols: `OK` = pass, `!!` = fail (has fix), `~~` = warning, `--` = available upgrade
- Always show all logical groups, never omit a group. Related checks are collapsed: checks 4+5+6 → "CLAUDE.md", checks 7+8 → "Vault structure", checks 14+15 → "MemPalace", checks 17+18+19 → "NotebookLM"
- For `!!` rows: use a short failure description (e.g., `missing`, `malformed`, `not found`)
- For `--` rows: use `not installed` or `not configured`
- For `~~` rows: use a short warning (e.g., `stale (5 pages changed)`)
- Summary line format: `{N} fixes, {N} warnings, {N} upgrades`
  - Use singular when count is 1: `1 fix, 0 warnings, 2 upgrades`
- Tier line: `Tier: {Quick|Standard|Full}`
- Always end with: `Run /ark-health anytime to check`

**Tier assignment for scorecard:**

| Tier | Condition |
|------|-----------|
| Quick | No Critical or Standard fail in checks 1-11 (warn is OK) |
| Standard | No Critical or Standard fail in checks 1-13 (warn is OK) |
| Full | No Critical or Standard fail in checks 1-20 (warn is OK) |
| Below Quick | Any critical check (1, 4-9) failing |

**Warn checks do not block tier classification.** Checks 10 (index staleness) and 20 (vault externalized) return `warn`, which counts as "no fail" for tier purposes. They still surface in the scorecard as warnings.

Note: `/ark-health` defines a "Minimal" tier (checks 1-9 pass, 10-11 skip). The wizard does not use Minimal because it always creates the vault — after `/ark-onboard` runs, the result is always Quick or higher.

If below Quick tier, show `Tier: --` instead of a tier name.

**Before/after scorecard (for Repair path):**

When showing a before/after comparison, display two scorecards side by side or sequentially with labels:

```
--- BEFORE ---
{scorecard}

--- AFTER ---
{scorecard}

Changes: {N} fixes applied, {N} upgrades added
```

## Design Decisions

- **Absorbs /wiki-setup completely.** All directory creation, template generation, metadata setup, and Obsidian configuration from `/wiki-setup` is replicated in the Greenfield path. Users should run `/ark-onboard` instead of `/wiki-setup` for new projects.
- **Additive migration.** The Migration path never deletes or overwrites existing content. Ark scaffolding is layered on top. Frontmatter changes require explicit user confirmation and get their own commit.
- **Git safety everywhere.** Every path that touches git checks repo state first (is it a repo? clean tree? user configured?). Migration path commits a checkpoint before any changes.
- **Graceful degradation.** Every Full-tier step (MemPalace, NotebookLM, history hook) includes a "warn and skip" fallback. Installation failures never block the wizard.
- **Hook pre-validation.** Before running `install-hook.sh`, verify `.claude/settings.json` is valid JSON. The install script uses Python and will fail on malformed JSON.
- **MemPalace wing distinction.** Check 15 covers the vault content wing (indexed by `mine-vault.sh`). The conversation history wing is managed separately by `ark-history-hook.sh` (check 16). They are independent.
- **Zero-GUI plugin setup.** Step 11 downloads plugin binaries from GitHub releases using the Obsidian community-plugins.json registry to resolve repo URLs. Step 12 generates `data.json` for both TaskNotes and Obsidian Git with Ark-specific defaults (folder paths, custom statuses, field mappings, Bases views, auto-sync intervals). The user only needs to open Obsidian and enable the plugins — no manual configuration required. Falls back to reference vault copy, then manual GUI install as last resort.
- **MCP check is config-only.** Check 13 verifies `mcpServers.tasknotes` presence in `.mcp.json` (project root), not endpoint reachability. Obsidian must be running for the endpoint to respond.
- **Clear step markers.** Each step includes "You are at Step X of Y" markers so Claude can track progress and the user knows where they are in the wizard.
- **No hardcoded references.** No project names, vault paths, or task prefixes are hardcoded anywhere in this skill. All values come from user input or runtime detection.
- **`/ark-health` is authoritative.** The diagnostic checklist in this file is a convenience copy. If it drifts from `/ark-health`'s definitions, `/ark-health` is the source of truth.
