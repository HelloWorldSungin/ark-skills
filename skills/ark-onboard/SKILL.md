---
name: ark-onboard
description: Interactive setup wizard — greenfield, vault migration, partial repair. Absorbs /wiki-setup.
---

# Ark Onboard

Interactive setup wizard for new Ark projects. Detects project state (greenfield, migration, repair, healthy) and walks through setup at 3 tiers (Quick, Standard, Full). Absorbs all `/wiki-setup` functionality — single entry point for new project onboarding.

**Reference material (loaded on-demand):**

- `references/templates.md` — all file/config templates (shell, JSON, Python, markdown). Used by every path that writes a file.
- `references/externalize-vault-plan.md` — the Externalization plan-file template (199 LOC). Used by the Externalization path only.
- `references/state-detection.md` — project state detection bash + flag derivation. Used at wizard entry.
- `references/plugin-install.md` — Obsidian plugin download + fallback bash. Used by Greenfield Step 11 / Repair Check 12.
- `references/centralized-vault-repair.md` — centralized-vault repair scenarios (broken symlink, drift, missing script, missing hook). Used by Repair path.

## Context-Discovery Exemption

Exempt from normal context-discovery — must work when CLAUDE.md is missing, broken, or incomplete. When CLAUDE.md is absent, detect project state from the filesystem and route to the appropriate path (greenfield if no vault, partial/migration if a vault directory is found). Never abort because CLAUDE.md is missing — that's one of the states this skill is designed to handle.

## Vault Path Terminology

| Term | Meaning | Example |
|------|---------|---------|
| **Vault root** | Top-level directory containing all vault content | `vault/` |
| **Project docs path** | Subdirectory for project-specific knowledge (may equal vault root for standalone) | `vault/Trading-Signal-AI/` |
| **TaskNotes path** | Sibling of project docs under vault root, never nested | `vault/TaskNotes/` |

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

New projects default to a **centralized vault**: the vault lives in its own git repo at `~/.superset/vaults/<project>/` (or `~/Vaults/<project>/` for non-superset users), and the project repo contains a `vault` symlink. Mirrors ArkNode-Poly's production pattern. Benefits:

- Worktrees share a single vault — session logs and tasks visible everywhere.
- Obsidian desktop app points at exactly one vault, so `obsidian-cli` agrees with the agent.
- NotebookLM sync state is shared (not duplicated per worktree).

### Vault path terms

| Term | Meaning | Example |
|------|---------|---------|
| `<vault_repo_path>` | Absolute path to the centralized vault repo | `~/.superset/vaults/ArkNode-Poly` |
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

The chosen vault path **must start with `$HOME/`** (or `~/`, normalized to `$HOME/`). Reject absolute paths outside `$HOME` (e.g., `/Volumes/...`, `/mnt/...`, another user's home). Users wanting an external drive should `ln -s /Volumes/ExternalDrive/vaults $HOME/Vaults` and point the wizard at the `$HOME` path. Keeps tracked metadata portable across machines by construction.

When writing `VAULT_TARGET` into the tracked setup script, always store the `$HOME/`-prefixed literal form (e.g., `VAULT_TARGET="$HOME/.superset/vaults/ArkNode-Poly"`), not the expanded path. `$HOME` expands at runtime on whichever machine runs the script.

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

Check #20 (vault-externalized) reads this row: presence of `embedded` (case-insensitive) in the `Vault layout` row means opt-in to embedded — check #20 returns `pass`.

### Templates (load from references/templates.md)

All file templates for this section live in `references/templates.md`:

- § `scripts/setup-vault-symlink.sh` — the canonical script (has `VAULT_TARGET="$HOME/..."` grep contract: `^VAULT_TARGET="[^"]*"\s*$`, value must begin with `$HOME/`)
- § `.git/hooks/post-checkout` — the hook (install at `$(git rev-parse --git-common-dir)/hooks/post-checkout`, not `.git/hooks/` — worktrees share the main repo's hooks via `commondir`)
- § `.superset/config.json merge` — append-only merge via Python (preserves existing entries)
- § `Vault repo .gitignore`

## Required CLAUDE.md Fields (Normalized)

Four user-provided fields. Everything else derives:

| Field | Format | Example |
|-------|--------|---------|
| Project name | Any string | `trading-signal-ai` |
| Vault root | Path ending with `/` | `vault/` |
| Task prefix | Ends with `-` | `ArkSignal-` |
| TaskNotes path | Path ending with `/` | `vault/TaskNotes/` |

Derived:
- **Counter file:** `{tasknotes_path}/meta/{task_prefix}counter`
- **Project docs path:** From "Obsidian Vault" row, or `{vault_root}` for standalone layouts

## Shared Diagnostic Checklist

> **Sync note:** `/ark-health` is the authoritative source for all 22 check definitions. This summary exists so `/ark-onboard` can run diagnostics without invoking a separate skill. If this drifts from `/ark-health`, that skill is correct.

Summary of the 22 checks (pass conditions; full semantics + bash in `/ark-health`):

| # | Check | Tier | Pass |
|---|-------|------|------|
| 1 | superpowers plugin | Critical | Any `superpowers:*` skill in session |
| 2 | gstack plugin | Standard | Any gstack skill (`browse`, `qa`, `ship`, `review`) in session |
| 3 | obsidian plugin | Standard | `obsidian:obsidian-cli` in session |
| 4 | CLAUDE.md exists | Critical | File exists in project root |
| 5 | CLAUDE.md required fields | Critical | All 4 fields present/non-empty |
| 6 | Task prefix format | Critical | Prefix ends with `-`, counter file exists |
| 7 | Vault directory exists | Critical | Vault root path resolves |
| 8 | Vault structure | Critical | `_meta/`, `_Templates/`, `TaskNotes/` exist; plus `00-Home.md` (standalone) or project docs subdir (monorepo) |
| 9 | Python 3.10+ | Critical | `python3 --version` ≥ 3.10 |
| 10 | Index status | Standard | `index.md` exists (staleness = warn, not fail) |
| 11 | Task counter | Standard | Counter file exists, valid integer |
| 12 | Obsidian vault plugins | Standard | `tasknotes/main.js` + `obsidian-git/main.js` in `.obsidian/plugins/` |
| 13 | TaskNotes MCP | Standard | `mcpServers.tasknotes` in `.mcp.json` (config-only — Obsidian must be running for endpoint to respond) |
| 14 | MemPalace installed | Full | `mempalace` CLI on PATH |
| 15 | MemPalace wing indexed | Full | `mempalace status` shows wing for project |
| 16 | History auto-index hook | Full | `~/.claude/hooks/ark-history-hook.sh` exists AND registered in `.claude/settings.json` |
| 17 | NotebookLM CLI installed | Full | `notebooklm` CLI on PATH |
| 18 | NotebookLM config | Full | `.notebooklm/config.json` with non-empty notebook ID |
| 19 | NotebookLM authenticated | Full | `notebooklm auth check --test` exits 0 |
| 20 | Vault externalized | Standard (warn-only) | Symlink matches script `VAULT_TARGET`, OR `Vault layout: embedded` opt-out |
| 21 | OMC plugin | Standard (tier-agnostic) | `omc` on PATH or `~/.claude/plugins/cache/omc/` exists; `ARK_SKIP_OMC=true` forces skip |
| 22 | ark-skills version current | Standard (warn-only) | `.ark/plugin-version` matches `$ARK_SKILLS_ROOT/VERSION`; `.ark/` not gitignored |

Running diagnostics: run all 22 checks in sequence, never abort on failure. For records:

- Checks 7–20 with CLAUDE.md missing (Check 4 = fail): record `skip` — "cannot check — CLAUDE.md missing". Checks 21, 22 are exempt.
- Check 10 staleness: `warn` (not fail)
- Check 20 vault-externalized: `warn` (never fails)
- Checks 15, 16 if Check 14 failed: `skip` — "requires MemPalace (check 14)"
- Checks 18, 19 if Check 17 failed: `skip` — "requires NotebookLM CLI (check 17)"
- Full-tier checks (14–19) below Full tier: `upgrade`
- Check 21 OMC: `upgrade` if not installed; `skip` if `ARK_SKIP_OMC=true`; never `fail`. Tier-agnostic.

## Project State Detection

Detection logic (full bash + flag derivation in `references/state-detection.md`):

1. Scan for vault directory: check `vault/`, `docs/vault/`, `.vault/` — set `VAULT_DIR` if found.
2. Check CLAUDE.md existence, extract vault root.
3. Count Ark artifacts: `_meta/vault-schema.md`, `_meta/taxonomy.md`, `index.md`, `TaskNotes/meta/` (max 4).
4. Detect centralized-vault signals: `IS_SYMLINK`, `SYMLINK_BROKEN`, `SYMLINK_DRIFT`, `SCRIPT_EXISTS`, `EMBEDDED_OPTOUT`.
5. Classify:

| State | Condition | Path |
|-------|-----------|------|
| **No Vault** | CLAUDE.md missing AND no vault, OR CLAUDE.md present but vault root missing/unresolved | Greenfield |
| **Non-Ark Vault** | Vault exists but < 3 Ark artifacts present | Migration |
| **Partial Ark** | ≥ 3 Ark artifacts (or vault exists but CLAUDE.md missing); OR broken symlink; OR symlink drift; OR missing script with live symlink | Repair |
| **Healthy** | All Critical + Standard checks pass | Report |

**Key rules:**
- Vault exists + no CLAUDE.md → always Partial (never Greenfield).
- `SYMLINK_BROKEN` OR `SYMLINK_DRIFT` OR missing script with live symlink → Partial Ark with `REPAIR_REASON=centralized-vault-drift` (or `centralized-vault-script-missing`). Routes Partial Ark through the centralized-vault repair subsection FIRST.
- Real vault dir + `EMBEDDED_OPTOUT=true` → respect opt-out, classify by artifact count only.

## Tier Selection

| Tier | What Gets Set Up | Time |
|------|-----------------|------|
| **Quick** | CLAUDE.md + vault structure + Python check + index generation | ~5 min |
| **Standard** | Quick + TaskNotes MCP + Obsidian plugins | ~10 min |
| **Full** | Standard + MemPalace + history hook + NotebookLM CLI + vault mining | ~25 min |

Present after state detection. Recommend Standard for most users. For Partial Ark (Repair) and Healthy, also offer tier upgrade based on current tier.

```
Which setup tier would you like?

  [Q] Quick    — CLAUDE.md, vault structure, index (~5 min)
  [S] Standard — Quick + TaskNotes MCP, Obsidian plugins (~10 min)  [recommended]
  [F] Full     — Standard + MemPalace, history hook, NotebookLM (~25 min)

Choose [Q/S/F]:
```

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
[3] Run state detection (references/state-detection.md)
    |
    v
[4] Route by state:
    No Vault        --> Ask tier --> Greenfield path
    Non-Ark Vault   --> Ask tier --> Migration path
    Partial Ark     --> Show failures --> Repair path (+ tier upgrade offer)
    Healthy         --> Show scorecard --> surface Full-tier upgrades
    |
    v
[5] Run full 22-check diagnostic
    |
    v
[6] Show before/after scorecard
    |
    v
[7] List follow-up reminders
```

---

## Path: No Vault (Greenfield)

Absorbs all `/wiki-setup` functionality. Creates a complete Ark project from scratch. 18 steps.

### Prerequisites (git safety)

```bash
# Is this a git repo?
git rev-parse --git-dir 2>/dev/null && echo "GIT_REPO=yes" || echo "GIT_REPO=no"
# If git repo: is working tree clean?
git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null && echo "CLEAN=yes" || echo "CLEAN=no — warn user to stash"
# Git user configured?
git config user.name 2>/dev/null && echo "GIT_USER=configured" || echo "GIT_USER=missing — warn user"
```

If not a git repo, offer `git init`. If working tree dirty, warn and ask to stash or commit first.

### Step 1 of 18 — Gather project info

Ask the user 5 prompts with the centralized-vault defaulting behavior:

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

**Prompt 5 — Embedded escape hatch (rare):**

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
      '~/'*) USER_PATH="\$HOME/${USER_PATH#'~/'}" ;;  # normalize
      *)
        echo "ERROR: Vault path must be under \$HOME so tracked metadata stays portable."
        echo "To use an external drive, symlink it: ln -s /Volumes/Drive/vaults \$HOME/Vaults"
        echo "Then point the wizard at the \$HOME path."
        # Re-prompt
        ;;
    esac
    ```
  - The resolved absolute path (`eval echo "$USER_PATH"`) must not already exist, OR must exist and be empty. If it exists with content from a different project, refuse (see Step 2a edge case).
- **Vault path (if user picked embedded):** Default to `./vault/` inside the project repo. Still reject if the path already exists.

**If user picked embedded:** branch to the embedded sub-flow — skip centralized-vault Steps 2a–2d and proceed with the legacy `./vault/` setup.

**Otherwise:** Continue to Step 2 (Python check), then Steps 2a–2d (centralized setup).

### Step 2 of 18 — Verify Python 3.10+

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
  echo "PAUSE"
fi
```

If missing or too old, PAUSE and tell user to install. Do not proceed.

### Step 2a of 18 — Create centralized vault repo

Skip if user picked embedded in Prompt 5.

```bash
VAULT_REPO_PATH_EXPANDED=$(eval "echo $USER_PATH")

# Edge case: target exists with foreign content
if [ -d "$VAULT_REPO_PATH_EXPANDED" ] && [ -n "$(ls -A "$VAULT_REPO_PATH_EXPANDED" 2>/dev/null)" ]; then
  echo "ERROR: $VAULT_REPO_PATH_EXPANDED already exists with content."
  echo "If orphan from a failed run, delete it and retry."
  echo "If it belongs to another project, choose a different path."
  exit 1
fi

mkdir -p "$VAULT_REPO_PATH_EXPANDED"
cd "$VAULT_REPO_PATH_EXPANDED" && git init
```

Write `.gitignore` (template: `references/templates.md § Vault repo .gitignore`). Create initial NotebookLM sync-state (template: `references/templates.md § Vault repo initial NotebookLM sync-state`). Return to `<project_repo>`.

### Step 2b of 18 — Create the symlink

```bash
ln -s "$VAULT_REPO_PATH_EXPANDED" vault
grep -qxF 'vault' .gitignore 2>/dev/null || echo 'vault' >> .gitignore
test -L vault && test -e vault && echo "vault symlink OK -> $(readlink vault)"
```

### Step 2c of 18 — Install automation (script + hook)

Write `scripts/setup-vault-symlink.sh` using template from `references/templates.md § scripts/setup-vault-symlink.sh`. Substitute `{VAULT_TARGET}` with the `$HOME/`-prefixed form from Step 1 Prompt 4 (NOT the expanded path).

Verify the grep contract:

```bash
MATCH_COUNT=$(grep -cE '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh)
[ "$MATCH_COUNT" -eq 1 ] || { echo "ERROR: script must contain exactly one VAULT_TARGET= line"; exit 1; }
grep -qE '^VAULT_TARGET="\$HOME/' scripts/setup-vault-symlink.sh || { echo "ERROR: VAULT_TARGET must start with \$HOME/"; exit 1; }
```

Install post-checkout hook from `references/templates.md § .git/hooks/post-checkout`:

```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
# Write the template content to $HOOK_PATH
chmod +x "$HOOK_PATH"
```

If `.superset/config.json` exists, merge setup/teardown entries via `references/templates.md § .superset/config.json merge`.

Final post-install verification:

```bash
test -L vault && test -e vault \
  && test -x "$(git rev-parse --git-common-dir)/hooks/post-checkout" \
  && test -f scripts/setup-vault-symlink.sh \
  && grep -qE '^VAULT_TARGET="\$HOME/' scripts/setup-vault-symlink.sh \
  || { echo "ERROR: post-install verification failed"; exit 1; }
echo "Automation installed."
```

### Step 2d of 18 — Offer GitHub remote (optional)

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
      echo "Skipped. Later: cd $VAULT_REPO_PATH_EXPANDED && gh repo create --private <project>-vault --source=. --push"
      ;;
  esac
else
  echo "gh not installed or not authenticated — skipping. Create later: cd $VAULT_REPO_PATH_EXPANDED && gh repo create --private <project>-vault --source=. --push"
fi
```

**After Step 2d:** Steps 3–18 run with `{vault_path}` set to the **centralized** `<vault_repo_path>` (expanded absolute path), NOT the project-repo `vault` symlink. Directory creation, templates, index generation, and the final `git add . && git commit` happen **inside the centralized vault repo**.

### Step 3 of 18 — Create vault directory structure

```bash
mkdir -p {vault_path}/{_Templates,_Attachments,_meta,.obsidian/plugins/{tasknotes,obsidian-git},TaskNotes/{Tasks/{Epic,Story,Bug,Task},Archive/{Epic,Story,Bug,Enhancement},Templates,Views,meta}}
```

For monorepo layout, also: `mkdir -p {vault_path}/{project_docs_path}/Session-Logs`

### Step 4 of 18 — Create 00-Home.md

Write `{vault_path}/00-Home.md` (standalone) or `{vault_path}/{project_docs_path}/00-Home.md` (monorepo) from `references/templates.md § 00-Home.md`. Substitute `{Project Name}` and `{today}`.

### Step 5 of 18 — Create metadata files

Write from `references/templates.md`:
- `{vault_path}/_meta/vault-schema.md` — § `_meta/vault-schema.md`
- `{vault_path}/_meta/taxonomy.md` — § `_meta/taxonomy.md`
- `{vault_path}/_meta/generate-index.py` — § `_meta/generate-index.py` (chmod +x after)

### Step 6 of 18 — Create page templates

Write 6 files in `{vault_path}/_Templates/` from `references/templates.md § Page templates`:
- `Session-Template.md`, `Compiled-Insight-Template.md`, `Bug-Template.md`, `Task-Template.md`, `Research-Template.md`, `Service-Template.md`

### Step 7 of 18 — Task counter setup

```bash
echo "1" > {vault_path}/TaskNotes/meta/{task_prefix}counter
```

`{task_prefix}` includes the trailing dash (counter filename: `{task_prefix}counter` → `ArkNew-counter`; no double dash).

### Step 8 of 18 — Project management guide

Write `{vault_path}/TaskNotes/00-Project-Management-Guide.md` from `references/templates.md § TaskNotes/00-Project-Management-Guide.md`.

### Step 9 of 18 — Obsidian configuration

Write from `references/templates.md § Obsidian config files`:
- `{vault_path}/.gitignore` — vault-level gitignore (workspace/graph/themes/plugin data.json)
- `{vault_path}/.obsidian/app.json`, `appearance.json`, `community-plugins.json`, `core-plugins.json`

### Step 10 of 18 — Create/update CLAUDE.md

If CLAUDE.md missing, create from `references/templates.md § CLAUDE.md template`. If present but missing fields, update with vault/prefix/TaskNotes rows.

For **centralized** layout (default): no extra row needed — check #20 defaults to `pass` when the `vault` symlink resolves.

For **embedded** (escape hatch): append the `| **Vault layout** | embedded (not symlinked) |` row. Check #20's grep contract: `^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded` (case-insensitive) — do not deviate.

For monorepo layout, point Obsidian Vault row at the project docs subdirectory and add the vault root separately.

### Step 11 of 18 — Obsidian plugins (Standard+ tier only)

Skip to Step 16 if Quick tier. Three-tier install fallback — see `references/plugin-install.md`:

1. **Primary:** Download `main.js`, `manifest.json`, `styles.css` from GitHub releases (resolves repos via Obsidian's community-plugins.json registry).
2. **Fallback 1:** Copy from user-provided reference vault (NOT `data.json` — project-specific).
3. **Fallback 2:** PAUSE — manual GUI install.

### Step 12 of 18 — Plugin data + TaskNotes MCP (Standard+ only)

Skip to Step 16 if Quick tier.

Write plugin `data.json` configs (gitignored, project-specific) from `references/templates.md`:
- `{vault_path}/.obsidian/plugins/tasknotes/data.json` — § `TaskNotes plugin data.json`
- `{vault_path}/.obsidian/plugins/obsidian-git/data.json` — § `Obsidian Git plugin data.json`

Adjust `apiPort` if user runs multiple Obsidian instances (8080/8081/8082).

Configure TaskNotes MCP in `.mcp.json` — first validate JSON, then merge from `references/templates.md § .mcp.json TaskNotes MCP entry`:

```bash
if [ -f .mcp.json ]; then
  python3 -c "import json; json.load(open('.mcp.json'))" 2>/dev/null \
    || { echo "WARNING: .mcp.json is malformed JSON. Back up and recreate."; cp .mcp.json .mcp.json.bak; }
fi
```

### Step 13 of 18 — Install MemPalace (Full tier only)

Skip to Step 16 if Quick/Standard.

```bash
command -v mempalace 2>/dev/null && echo "MemPalace already installed: $(mempalace --version 2>/dev/null)" && MEMPALACE_OK=true

if [ -z "$MEMPALACE_OK" ]; then
  if command -v pipx 2>/dev/null; then
    pipx install "mempalace>=3.0.0,<4.0.0"
  elif command -v pip 2>/dev/null; then
    pip install "mempalace>=3.0.0,<4.0.0"
  else
    echo "WARNING: Neither pipx nor pip available. Install manually: pip install 'mempalace>=3.0.0,<4.0.0'"
    echo "Skipping — continuing without MemPalace."
    MEMPALACE_OK=false
  fi
fi
```

If install fails, warn and skip. Non-blocking.

### Step 14 of 18 — Vault mining + history hook (Full tier only)

Skip to Step 16 if Quick/Standard.

Mine the vault (creates vault content wing):
```bash
bash skills/shared/mine-vault.sh
```

If `mine-vault.sh` not found, warn and skip.

Install history hook (conversation history wing, separate from vault content wing). Pre-validate `.claude/settings.json`:

```bash
if [ -f .claude/settings.json ]; then
  python3 -c "import json; json.load(open('.claude/settings.json'))" 2>/dev/null \
    || { echo "ERROR: .claude/settings.json is malformed JSON. Skipping hook."; SKIP_HOOK=true; }
fi

if [ -z "$SKIP_HOOK" ]; then
  bash skills/claude-history-ingest/hooks/install-hook.sh
fi
```

Both non-blocking.

### Step 15 of 18 — NotebookLM (Full tier only)

Skip to Step 16 if Quick/Standard.

```bash
command -v notebooklm 2>/dev/null && echo "NotebookLM CLI found" || echo "NotebookLM CLI not found"
```

If not installed:
```
NotebookLM CLI not installed. To install:
  pipx install notebooklm-cli
Then authenticate: notebooklm auth login
Skipping — configure later with /notebooklm-vault.
```

If installed, check auth:
```bash
notebooklm auth check --test 2>/dev/null
if [ $? -ne 0 ]; then
  echo "NotebookLM not authenticated. Run: notebooklm auth login"
  echo "PAUSE — authenticate, then continue."
fi
```

Create `{vault_path}/.notebooklm/config.json` from `references/templates.md § NotebookLM config`. Tell user to fill in `notebooks.main.id` and run `/notebooklm-vault setup`.

If CLI missing or auth fails, warn and continue. Non-blocking.

### Step 16 of 18 — Generate index

```bash
cd {vault_path} && python3 _meta/generate-index.py
```

Verify output: "index.md generated with N entries."

### Step 17 of 18 — Git init + initial commit

Re-check git state:

```bash
if ! git rev-parse --git-dir 2>/dev/null; then
  echo "Initializing git repo..."
  git init
fi
git config user.name 2>/dev/null || echo "WARNING: git user.name not set. Run: git config user.name 'Your Name'"
git config user.email 2>/dev/null || echo "WARNING: git user.email not set. Run: git config user.email 'you@example.com'"
```

**Centralized vault (default):** the initial vault-content commit lives in the **vault repo**. The project repo only commits metadata + the tracked script.

```bash
# 1. Initial commit inside centralized vault repo
cd "$VAULT_REPO_PATH_EXPANDED"
git add .
git commit -m "feat: initialize {project_name} vault with Ark structure"

# 2. Project-repo metadata
cd "<project_repo>"
git add scripts/setup-vault-symlink.sh .gitignore CLAUDE.md
git add .mcp.json .claude/settings.json .notebooklm/config.json 2>/dev/null
if [ -f .superset/config.json ]; then git add .superset/config.json; fi
git commit -m "feat: wire {project_name} project to centralized vault"
```

**Embedded vault (escape hatch):** legacy single-commit flow.

```bash
git add {vault_path}/ CLAUDE.md .mcp.json .claude/settings.json .notebooklm/ 2>/dev/null
git commit -m "feat: initialize {project_name} vault with Ark structure (embedded)"
```

The post-checkout hook is NOT tracked — it's installed per-clone by `/ark-onboard`.

### Step 18 of 18 — Final diagnostic + reminders

Run the full 22-check diagnostic. Show the scorecard (§ Scorecard Output Format below).

Then show follow-up reminders. Adjust based on what was actually set up:

```
Setup complete! Follow-up reminders:

1. Open the vault in Obsidian — plugins are pre-configured (if downloaded/copied)
   OR: Install TaskNotes + Obsidian Git via Community Plugins (if manual fallback was needed)
2. Fill in NotebookLM notebook ID in .notebooklm/config.json (if Full tier)
3. Optional: install OMC for /ark-workflow Path B — https://github.com/anthropics/oh-my-claudecode
4. Run /ark-health anytime to check ecosystem health
5. Run /ark-onboard again to upgrade tiers
```

- Downloaded from GitHub / reference-vault copy: "plugins are pre-configured, just enable them in Settings > Community Plugins"
- Manual fallback needed: "Install TaskNotes + Obsidian Git via Settings > Community Plugins > Browse"
- Omit NotebookLM reminder if not Full tier
- Omit plugin reminder entirely if Quick tier
- Omit OMC reminder if Check 21 already reports OMC detected (`HAS_OMC=true`)

---

## Path: Non-Ark Vault (Ark Scaffolding + Externalization Offer)

Two distinct operations:

1. **Ark scaffolding (inline, safe)** — add `_meta/`, `_Templates/`, `TaskNotes/`, etc. to an existing vault. 15-step flow below. Non-destructive: never deletes/overwrites. Frontmatter changes are explicit and reversible (separate commits).
2. **Externalization offer (pointer only)** — if the scaffolded vault is still a real directory (not a symlink), the last step tells the user to re-run `/ark-onboard` to generate an externalization plan (the "Externalization Plan Generation" path below).

**Key principle:** additive only. Never delete or overwrite existing content. Destructive steps (externalization) live in a separate plan file, never inline.

### Migration Step 1 of 15 — Scan existing vault

```bash
find {vault_path} -name "*.md" | wc -l
ls -d {vault_path}*/ 2>/dev/null
head -20 {vault_path}/*.md 2>/dev/null | head -60
grep -rh "^tags:" {vault_path} --include="*.md" 2>/dev/null | head -10
grep -roh "#[a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sort | uniq -c | sort -rn | head -20
```

Report to user: "Found N pages, M existing tags, folder structure..."

### Migration Step 2 of 15 — Gather project info

Ask for project name + task prefix (must end with `-`). Vault path already known; confirm as vault root.

### Migration Step 3 of 15 — Pre-commit existing state

Run git safety checks (same as Greenfield Prerequisites). If not a git repo, offer `git init`. Commit a rollback point:

```bash
git add -A && git commit -m "checkpoint: pre-Ark migration"
```

If nothing to commit, continue.

### Migration Step 4 of 15 — Add Ark scaffolding (non-destructive)

Create only directories/files that don't already exist. Never overwrite.

```bash
[ -d "{vault_path}_meta" ] || mkdir -p "{vault_path}_meta"
[ -d "{vault_path}_Templates" ] || mkdir -p "{vault_path}_Templates"
[ -d "{vault_path}_Attachments" ] || mkdir -p "{vault_path}_Attachments"
[ -d "{vault_path}.obsidian" ] || mkdir -p "{vault_path}.obsidian"
[ -d "{vault_path}TaskNotes/Tasks/Epic" ] || mkdir -p "{vault_path}TaskNotes/Tasks/"{Epic,Story,Bug,Task}
[ -d "{vault_path}TaskNotes/Archive/Epic" ] || mkdir -p "{vault_path}TaskNotes/Archive/"{Epic,Story,Bug,Enhancement}
[ -d "{vault_path}TaskNotes/meta" ] || mkdir -p "{vault_path}TaskNotes/"{Templates,Views,meta}
```

Check before writing files:

```bash
[ -f "{vault_path}00-Home.md" ] && echo "00-Home.md exists — skipping" || echo "Creating 00-Home.md"
```

Create missing files from templates in `references/templates.md`, only if not already present.

### Migration Step 5 of 15 — Generate vault-schema.md

Write `{vault_path}/_meta/vault-schema.md` from `references/templates.md § _meta/vault-schema.md`. If file exists, ask user before overwriting.

### Migration Step 6 of 15 — Scan tags and propose taxonomy

```bash
grep -roh "^  - [a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sed 's/^  - //' | sort | uniq -c | sort -rn
grep -roh "#[a-zA-Z][a-zA-Z0-9_-]*" {vault_path} --include="*.md" 2>/dev/null | sed 's/^#//' | sort | uniq -c | sort -rn
```

Show the proposed mapping (existing tags kept as-is, mapped to Ark structural tags, new Ark tags added). Ask the user to accept/edit. Write `{vault_path}/_meta/taxonomy.md`.

### Migration Step 7 of 15 — Offer frontmatter backfill (optional)

Show 3 sample pages with current vs proposed Ark frontmatter. Ask: `Apply frontmatter backfill to all N pages? [y/n/select]`.

**Skip non-standard pages** during bulk backfill:
- No YAML frontmatter (first line is not `---`)
- Fenced code blocks (``` ```) at top of file
- UTF-8 decode failure
- Binary masquerading as `.md`

Log skipped: `Skipped: {filename} — {reason}`.

If accepted, apply backfill (Claude reads/edits each file, skipping non-standard). Separate commit:

```bash
git add -A && git commit -m "chore: backfill Ark frontmatter on N pages (M skipped)"
```

Individually revertable. If declined, skip — add later with `/wiki-lint --fix`.

### Migration Step 8 of 15 — Task counter and management guide

Same as Greenfield Steps 7–8. Create counter + project management guide.

### Migration Step 9 of 15 — Obsidian configuration

Same as Greenfield Step 9, but check before writing:

```bash
[ -f "{vault_path}.obsidian/app.json" ] || echo '{ "alwaysUpdateLinks": true }' > "{vault_path}.obsidian/app.json"
[ -f "{vault_path}.obsidian/appearance.json" ] || echo '{}' > "{vault_path}.obsidian/appearance.json"
```

For `community-plugins.json`: merge existing plugin list with Ark plugins (don't remove existing). For `.gitignore`: append Ark patterns if not already present.

### Migration Step 10 of 15 — Create/update CLAUDE.md

Same as Greenfield Step 10. Update existing or create new.

### Migration Step 11 of 15 — Standard/Full tier steps

- **Standard:** Greenfield Steps 11–12 (Obsidian plugins + TaskNotes MCP).
- **Full:** Greenfield Steps 13–15 (MemPalace + hook + NotebookLM).

### Migration Step 12 of 15 — Generate index

```bash
cd {vault_path} && python3 _meta/generate-index.py
```

### Migration Step 13 of 15 — Run diagnostic

Run all 22 checks. Show scorecard.

### Migration Step 14 of 15 — Final commit + reminders

```bash
git add -A && git commit -m "feat: add Ark scaffolding to {project_name} vault"
```

Show follow-up reminders (same format as Greenfield Step 18, adjusted for migration).

### Migration Step 15 of 15 — Externalization offer (if vault is still embedded)

```bash
if [ -d vault ] && [ ! -L vault ]; then
  echo "Ark scaffolding complete. The vault is still embedded inside the project repo."
  echo "To externalize it (recommended for worktree/Obsidian-app consistency), run:"
  echo "  /ark-onboard"
  echo "The wizard will detect the embedded-Ark state and generate an externalization plan."
fi
```

Pointer only — does NOT generate the plan inline. The externalization offer triggers when the user re-runs `/ark-onboard` and state detection classifies the project as `Partial Ark` with a real `vault/` + Ark artifacts + no opt-out.

---

## Path: Externalization Plan Generation

**Triggered when:** state detection finds `vault/` is a real directory with Ark artifacts AND `EMBEDDED_OPTOUT=false`.

**Behavior:** no filesystem changes except writing the plan file. User reviews and executes via `/executing-plans`.

### Externalization Step 1 of 2 — Prompt for target path + remote

Compute default path per `Default path detection`.

```bash
if [ -d "$HOME/.superset" ]; then
  DEFAULT_PATH="\$HOME/.superset/vaults/<project>"
else
  DEFAULT_PATH="\$HOME/Vaults/<project>"
fi

echo "Detected: vault/ is committed to this repo as a real directory."
echo "The Ark convention is to externalize it. I'll generate a plan file (no destructive actions)."
echo "Review and run via /executing-plans."
echo ""
read -rp "Centralized location for the extracted vault [default: $DEFAULT_PATH]: " USER_PATH
USER_PATH="${USER_PATH:-$DEFAULT_PATH}"

# Path constraint (same as Greenfield)
case "$USER_PATH" in
  '$HOME/'*) ;;
  '~/'*) USER_PATH="\$HOME/${USER_PATH#'~/'}" ;;
  *) echo "ERROR: path must start with \$HOME/ or ~/"; exit 1 ;;
esac

read -rp "Create a GitHub repo for the vault now? [y/N] " WANT_GH
case "$WANT_GH" in y|Y) WANT_GH=true ;; *) WANT_GH=false ;; esac
```

### Externalization Step 2 of 2 — Generate the plan file

Discover sibling worktrees:

```bash
SIBLINGS=$(git worktree list --porcelain | awk '/^worktree /{print $2}' | grep -v "^$(git rev-parse --show-toplevel)$")
```

Write `docs/superpowers/plans/$(date +%Y-%m-%d)-externalize-vault.md` using the template in `references/externalize-vault-plan.md`. Substitute at generation time:

- `<PROJECT>` → project name from CLAUDE.md
- `<VAULT_REPO_PATH_PORTABLE>` → user's chosen path (e.g., `$HOME/.superset/vaults/my-project`)
- `<VAULT_REPO_PATH_EXPANDED>` → `eval "echo $USER_PATH"`
- `<SIBLINGS>` → newline-separated list; inject one Phase 2 sub-step per sibling
- `<WANT_GH>` → true/false; only include Phase 1 Step 1.7 if true
- `<MAIN>` → main worktree path

After writing:

```
Plan file written to: docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md

Sibling worktrees that will be touched:
<SIBLINGS>

Next step: review the plan, then run /executing-plans <plan-file>
```

**Exit the wizard.** No filesystem changes beyond the plan file.

---

## Path: Partial Ark (Repair)

For vaults that have Ark structure but some checks are failing.

### Centralized-Vault Repair (runs BEFORE generic repair)

If `REPAIR_REASON=centralized-vault-drift` or `centralized-vault-script-missing`, run this FIRST — before the generic 5-step flow below. Full scenarios + bash in `references/centralized-vault-repair.md`:

- **vault missing entirely + script present** — prompt to recreate symlink
- **vault is a broken symlink** — prompt to remove and relink
- **symlink drift** (`readlink` != script's `VAULT_TARGET`) — prompt: trust symlink (update script) OR trust script (recreate symlink) OR do nothing
- **script missing but symlink valid** (e.g., ArkNode-Poly's hand-rolled layout) — backfill `scripts/setup-vault-symlink.sh` using the portable form from `readlink`
- **post-checkout hook missing or non-executable** — install hook from template

After centralized-vault repairs, fall through to the generic 5-step repair flow (which re-runs the diagnostic and catches any remaining failures).

### Repair Step 1 — Run full diagnostic

Run all 22 checks. Record failures.

### Repair Step 2 — Show failures

Scorecard with failures highlighted, grouped by severity:

```
Ark Health — Repair Mode

Critical failures (must fix):
  !! Check 5: CLAUDE.md missing task prefix
  !! Check 8: Vault structure missing _Templates/

Standard failures (recommended):
  !! Check 11: Task counter file not found
  !! Check 13: TaskNotes MCP not configured
  !! Check 16: History auto-index hook not registered

Warnings (non-blocking, review interactively):
  ~~ Check 16: Wing-mismatch — expected -my-project, found -my-project-subdir
  ~~ Check 16: Threshold-lock — baseline stuck at 4319 drawers

Available upgrades:
  -- Check 14: MemPalace not installed
  -- Check 17: NotebookLM not installed

Fix critical + standard issues now? [y/n]
```

**Check 16 classification (context-dependent):**

| Condition | Classification |
|-----------|----------------|
| MemPalace installed (Check 14 pass) AND vault wing has drawers (Check 15 pass) AND hook NOT in project-local settings | **Standard failure** — defensive coverage. Global hook usually covers this, so auto-fix is defense-in-depth rather than strictly functional. |
| MemPalace NOT installed | **Available upgrade** — hook depends on mempalace; present as Full-tier upgrade. |
| Hook registered but sub-warnings (wing-mismatch / threshold-staleness / threshold-lock) | **Warning** — surface in Step 3b. Do NOT auto-fix. `threshold-lock` is high-signal: it looks like "hook not running" but is a stuck baseline. |

### Repair Step 3 — Fix each failing check

Fix in order (Critical first, then Standard). For each fix:

1. State: "Fixing Check N: {description}"
2. Apply fix from the diagnostic checklist
3. Verify: re-run the specific check
4. Report: "Check N: FIXED" or "Check N: STILL FAILING — {reason}"

**Critical fixes (checks 4–9):**
- Check 4 (CLAUDE.md missing) — create from `references/templates.md § CLAUDE.md template`
- Check 5 (missing fields) — add interactively
- Check 6 (task prefix) — fix format or create counter file
- Check 7 (vault dir) — create directory or fix path in CLAUDE.md
- Check 8 (vault structure) — create missing subdirectories
- Check 9 (Python) — can't auto-fix; tell user to install, PAUSE

**Standard fixes (checks 10–13, 16):**
- Check 10 (index) — `python3 _meta/generate-index.py`
- Check 11 (counter) — `echo "1" > {path}`
- Check 12 (plugins) — `references/plugin-install.md` (download → reference vault → manual fallback)
- Check 13 (MCP) — merge tasknotes entry into `.mcp.json` (see `references/templates.md § .mcp.json TaskNotes MCP entry`)
- Check 16 (hook registration, when reclassified as Standard) — `bash skills/claude-history-ingest/hooks/install-hook.sh`

### Repair Step 3b — Warnings (interactive review)

Check 16's sub-warnings need human judgment. Present each individually: fix now, skip, or explain.

**Wing-mismatch** (e.g., `-ArkNode-AI` expected, `-ArkNode-AI-projects-trading-signal-ai` found):
- Fix now → `bash skills/shared/mine-vault.sh` from current CWD to index the current project as its own wing
- Skip → The subproject is the intended wing (monorepo or active subproject)
- Explain → "Wing is derived from CWD. If you usually run Claude from a subproject root, that subproject will be the wing root."

**Threshold-staleness (new_drawers >= 200):**
- Fix now → `/claude-history-ingest compile` to clear the backlog and reset the baseline
- Skip → You plan to compile manually later
- Explain → "Stop hook appends to drawer count but only triggers compile when new_drawers >= 50. If compile never fired despite a large backlog, something prevented it — manual compile restores the invariant."

**Threshold-lock (current == baseline, baseline > 500):**
- Fix now → Reset baseline:
  ```bash
  jq '."<wing>".drawers_at_last_compile = 0' ~/.mempalace/hook_state/compile_threshold.json \
    > /tmp/t && mv /tmp/t ~/.mempalace/hook_state/compile_threshold.json
  ```
- Skip → Let natural drawer accumulation unstick it
- Explain → "After a successful compile, hook stores current drawer count as new baseline. If no new sessions get indexed, current stays equal and new_drawers stays at 0 — compile never re-fires. Resetting baseline to 0 makes the next 50 drawers trigger compile."

### Repair Step 4 — Tier upgrade offer

After fixes, determine current tier and offer upgrade. If user accepts, execute Greenfield Steps 13–15 (MemPalace + hook + NotebookLM).

### Repair Step 5 — Final diagnostic + before/after scorecard

Run all 22 checks again. Show before/after comparison (§ Scorecard Output Format § before/after below).

For version drift (plugin updated but project conventions out of date), run `/ark-update` — it replays additive conventions from the current target profile. `/ark-update` refuses to run on malformed CLAUDE.md / `.mcp.json` / `.ark/migrations-applied.jsonl` and points back here; coexistence is intentional. Note: if `.ark/` is gitignored, remove the pattern and commit before running `/ark-update`.

---

## Path: Healthy

For projects where all Critical + Standard checks pass.

### Healthy Step 1 — Run full diagnostic

Run all 22 checks. All Critical + Standard should pass.

### Healthy Step 2 — Show scorecard

Full scorecard per § Scorecard Output Format. Highlight the current tier.

### Healthy Step 3 — Surface upgrade opportunities

If not at Full tier, show what's available:

```
Current tier: Standard. Available Full-tier upgrades:

  MemPalace — deep vault search + experiential synthesis
    Install: pipx install "mempalace>=3.0.0,<4.0.0"
    Then: bash skills/shared/mine-vault.sh

  History hook — auto-index Claude sessions on exit
    Install: bash skills/claude-history-ingest/hooks/install-hook.sh

  NotebookLM — fastest pre-synthesized vault queries
    Install: pipx install notebooklm-cli
    Then: /notebooklm-vault setup

Upgrade to Full tier now? [y/n]

Optional capability extensions (do NOT promote tier):

  OMC plugin — autonomous execution for /ark-workflow Path B
    Install: see https://github.com/anthropics/oh-my-claudecode
```

If accepted, execute Greenfield Steps 13–15. Re-run diagnostic + show updated scorecard.

If at Full tier:

```
Checks 1-20 all pass. Full tier active. (Checks 21 and 22 are tier-agnostic.)
No upgrades available. Run /ark-health anytime to verify.
```

---

## Scorecard Output Format

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
| OMC plugin         --  not installed |
| Plugin version     OK  v1.14.0       |
+--------------------------------------+
| Tier: Standard                       |
| 0 fixes, 0 warnings, 3 upgrades      |
| Run /ark-health anytime to check     |
+--------------------------------------+
```

**Symbols:** `OK` = pass, `!!` = fail (has fix), `~~` = warning, `--` = available upgrade

**Rules:**
- Always show all logical groups. Related checks collapse: 4+5+6 → "CLAUDE.md", 7+8 → "Vault structure", 14+15 → "MemPalace", 17+18+19 → "NotebookLM", 21 → "OMC plugin", 22 → "Plugin version"
- `!!` rows: short failure description (`missing`, `malformed`, `not found`)
- `--` rows: `not installed` or `not configured`
- `~~` rows: short warning (`stale (5 pages changed)`)
- Summary line: `{N} fixes, {N} warnings, {N} upgrades` (singular when count is 1)
- Tier line: `Tier: {Quick|Standard|Full}`; below Quick → `Tier: --`
- Always end: `Run /ark-health anytime to check`

**Tier rules:**

| Tier | Condition |
|------|-----------|
| Quick | No Critical/Standard fail in checks 1–11 (warn is OK) |
| Standard | No Critical/Standard fail in checks 1–13 (warn is OK) |
| Full | No Critical/Standard fail in checks 1–20 (warn is OK); Check 21 is tier-agnostic |
| Below Quick | Any critical check (1, 4–9) failing |

Warn and upgrade checks don't block tier classification. Checks 10/20/22 (warn) and 14/17/18/21 (upgrade) count as "no fail". `/ark-health` defines a "Minimal" tier (checks 1–9 pass, 10–11 skip); the wizard never uses Minimal because it always creates the vault.

**Before/after comparison (Repair path):**

```
--- BEFORE ---
{scorecard}

--- AFTER ---
{scorecard}

Changes: {N} fixes applied, {N} upgrades added
```

## Design Decisions

- **Absorbs /wiki-setup completely.** All directory creation, template generation, metadata setup, and Obsidian configuration from `/wiki-setup` is in the Greenfield path. Users should run `/ark-onboard` instead of `/wiki-setup` for new projects.
- **Additive migration.** Migration path never deletes or overwrites. Ark scaffolding layers on top. Frontmatter changes require explicit confirmation and get their own commit.
- **Git safety everywhere.** Every path that touches git checks repo state first (is it a repo? clean tree? user configured?). Migration commits a checkpoint before any changes.
- **Graceful degradation.** Every Full-tier step (MemPalace, NotebookLM, history hook) has "warn and skip" fallbacks. Installation failures never block the wizard.
- **Hook pre-validation.** Before `install-hook.sh`, verify `.claude/settings.json` is valid JSON (script uses Python and fails on malformed JSON).
- **MemPalace wing distinction.** Check 15 covers the vault content wing; Check 16 covers the conversation history wing. Independent.
- **Zero-GUI plugin setup.** Step 11 downloads plugin binaries from GitHub releases using the Obsidian registry. Step 12 generates `data.json` for both plugins with Ark-specific defaults. User only enables plugins in Obsidian — no manual configuration. Falls back to reference vault copy, then manual install.
- **MCP check is config-only.** Check 13 verifies `mcpServers.tasknotes` presence in `.mcp.json`, not endpoint reachability.
- **Clear step markers.** Each step heading includes "Step X of Y" numbering (e.g., `### Step 1 of 18 — …`) so progress is trackable at a glance.
- **No hardcoded references.** No project names, vault paths, or task prefixes are hardcoded. All values come from user input or runtime detection.
- **`/ark-health` is authoritative** for all 22 check definitions. If this convenience summary drifts, that skill wins.
- **Reference material load-on-demand.** Templates, plan templates, state-detection bash, plugin-install bash, and repair-scenario bash live in `references/*.md`. The agent loads what it needs when it needs it, cutting the at-invocation footprint without losing any operational detail.
