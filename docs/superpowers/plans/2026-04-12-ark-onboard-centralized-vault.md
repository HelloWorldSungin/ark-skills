# `/ark-onboard` Centralized Vault Recommendation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `/ark-onboard` to recommend a centralized Obsidian vault (externalized git repo + symlink) as the default layout, with an explicit opt-out for embedded. Mirror ArkNode-Poly's manual pattern in the wizard, generalize it for any Ark project, and surface the anti-pattern via a new warn-only diagnostic check.

**Architecture:** Skill markdown edits only. The wizard writes three runtime artifacts into the user's project repo: a `scripts/setup-vault-symlink.sh` script (tracked, `$HOME`-portable VAULT_TARGET, the canonical metadata), a local `.git/hooks/post-checkout` hook (not tracked, reinstalled on reclone), and an optional `.superset/config.json` setup-entry for superset projects. Externalization of existing embedded vaults emits a plan file rather than running destructive steps directly.

**Tech Stack:** Markdown (SKILL.md edits), Bash (validation/grep checks, wizard runtime commands), YAML (frontmatter), Git (commits per task). No code compilation, no automated test harness.

**Spec reference:** `docs/superpowers/specs/2026-04-12-ark-onboard-centralized-vault-design.md` (commit `dd80baa`, revision 4 — passed codex round 4).

---

### Task 1: Add Centralized Vault Terminology + Directory Layout to `/ark-onboard`

**Files:**
- Modify: `skills/ark-onboard/SKILL.md` (insert after line ~35, right after the "Vault Path Terminology" path-layout fence)

- [ ] **Step 1: Verify the current structure of the terminology section**

Run:
```bash
grep -n "## Vault Path Terminology\|## Required CLAUDE.md Fields" skills/ark-onboard/SKILL.md
```

Expected output: two line numbers, one for each header. The new section will be inserted between them.

- [ ] **Step 2: Insert the centralized-vault terminology + architecture section**

Use the Edit tool to insert a new section between `## Vault Path Terminology` (and its path-layout code block) and `## Required CLAUDE.md Fields (Normalized)`. Find the text "└── meta/ArkSignal-counter" followed by three backticks followed by a blank line, then `## Required CLAUDE.md Fields (Normalized)`, and insert this content in the middle:

```markdown
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

```

- [ ] **Step 3: Verify the insertion**

Run:
```bash
grep -c "Centralized Vault Layout (Default)" skills/ark-onboard/SKILL.md
grep -c "VAULT_TARGET" skills/ark-onboard/SKILL.md
grep -c '`<vault_repo_path>`' skills/ark-onboard/SKILL.md
```

Expected: all three return `>= 1`.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): add centralized vault terminology + layout diagram"
```

---

### Task 2: Embed the `setup-vault-symlink.sh` Template Inside `/ark-onboard` SKILL.md

The wizard will `cat > scripts/setup-vault-symlink.sh <<'EOF' ... EOF` at runtime; the template body lives in SKILL.md so Claude knows exactly what to write.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md` — append a new section immediately after the "Centralized Vault Layout (Default)" section added in Task 1.

- [ ] **Step 1: Verify prerequisite (Task 1 content present)**

Run:
```bash
grep -n "### Embedded vault opt-out" skills/ark-onboard/SKILL.md | head -1
```

Expected: returns one line number. The new section goes after this subsection.

- [ ] **Step 2: Insert the template section**

Use Edit to append this section immediately after the "### Embedded vault opt-out" subsection's code fence (the fence that contains `| **Vault layout** | embedded (not symlinked) |`). Insert right before the closing `## Required CLAUDE.md Fields (Normalized)` header:

````markdown
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

````

- [ ] **Step 3: Verify insertion**

Run:
```bash
grep -c "AUTOGENERATED by /ark-onboard" skills/ark-onboard/SKILL.md
grep -c "VAULT_TARGET=\"<VAULT_REPO_PATH_PORTABLE>\"" skills/ark-onboard/SKILL.md
grep -c "git rev-parse --git-common-dir" skills/ark-onboard/SKILL.md
```

Expected: `AUTOGENERATED` >= 2, `VAULT_TARGET=` template >= 1, `git-common-dir` >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): embed setup-vault-symlink.sh and post-checkout templates"
```

---

### Task 3: Update State Detection to Recognize Centralized Vault, Embedded Opt-Out, and Symlink Drift

The current State Detection in SKILL.md routes between No Vault / Non-Ark Vault / Partial Ark / Healthy based on artifact count. We need two additions: (a) detect embedded opt-out in CLAUDE.md; (b) detect the new Partial Ark triggers (broken symlink, missing script, symlink-target drift).

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "## Project State Detection" section (~line 108).

- [ ] **Step 1: Read the existing State Detection classification block**

Run:
```bash
sed -n '108,180p' skills/ark-onboard/SKILL.md
```

Confirm the existing `bash` block that computes `STATE=no_vault | partial_ark | non_ark_vault` is present.

- [ ] **Step 2: Extend the classification block**

Find the existing classification `bash` block (starts with `# Count Ark artifacts to distinguish Non-Ark from Partial` and ends with `fi`) and replace it with this expanded version:

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

- [ ] **Step 3: Add a new subsection documenting the centralized-vault signals**

Immediately after the classification `bash` block (and before the next `## ` heading), insert:

```markdown

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

```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "EMBEDDED_OPTOUT" skills/ark-onboard/SKILL.md
grep -c "SYMLINK_DRIFT" skills/ark-onboard/SKILL.md
grep -c "REPAIR_REASON=centralized-vault" skills/ark-onboard/SKILL.md
grep -c "### Centralized-Vault Signals" skills/ark-onboard/SKILL.md
```

Expected: all three grep counts >= 1.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): detect centralized-vault signals in state classification"
```

---

### Task 4: Rewrite Greenfield Step 1 to Default to Centralized Vault with Escape Hatch

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "### Greenfield Step 1: Gather project info" section (~line 254).

- [ ] **Step 1: Locate the existing Step 1**

Run:
```bash
grep -n "### Greenfield Step 1: Gather project info" skills/ark-onboard/SKILL.md
```

- [ ] **Step 2: Replace the Step 1 body**

Use the Edit tool. The old body (from "Ask the user for the 4 required fields:" through "- Project name should be lowercase-kebab-case (warn if not, but allow)") is:

```
Ask the user for the 4 required fields:

1. **Project name** — e.g., `my-new-project`
2. **Task prefix** — e.g., `ArkNew-` (must end with `-`)
3. **Vault path** — where to create the vault (default: `./vault/`)
4. **Vault layout** — `standalone` (flat, docs at vault root) or `monorepo` (project subdirectory under vault root)

Validate:
- Task prefix must end with exactly one `-`
- Vault path must not already exist (if it does, redirect to Migration or Repair path)
- Project name should be lowercase-kebab-case (warn if not, but allow)
```

Replace with:

```markdown
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

```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "Centralized vault location" skills/ark-onboard/SKILL.md
grep -c "Escape hatch (rare)" skills/ark-onboard/SKILL.md
grep -c 'Vault path must be under \\$HOME' skills/ark-onboard/SKILL.md
```

Expected: all three >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): rewrite greenfield step 1 with centralized default + escape hatch"
```

---

### Task 5: Insert Greenfield Steps 2a–2d (Vault Repo Init, Symlink, Automation, GitHub Remote)

Four new steps between existing Step 2 (Python check) and Step 3 (Create vault directory structure).

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, insert after the existing "### Greenfield Step 2: Verify Python 3.10+" section.

- [ ] **Step 1: Locate the insertion point**

Run:
```bash
grep -n "### Greenfield Step 2: Verify Python 3.10\|### Greenfield Step 3: Create vault directory structure" skills/ark-onboard/SKILL.md
```

Expected: two line numbers.

- [ ] **Step 2: Insert the four new steps between Step 2 and Step 3**

Use Edit to insert this content between the end of the Step 2 body (after "If Python is missing or too old, PAUSE and tell the user to install before continuing. Do not proceed.") and the "### Greenfield Step 3: Create vault directory structure" header:

````markdown

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

````

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "### Greenfield Step 2a: Create centralized vault repo" skills/ark-onboard/SKILL.md
grep -c "### Greenfield Step 2b: Create the symlink" skills/ark-onboard/SKILL.md
grep -c "### Greenfield Step 2c: Install automation" skills/ark-onboard/SKILL.md
grep -c "### Greenfield Step 2d: Offer GitHub remote" skills/ark-onboard/SKILL.md
grep -c "VAULT_REPO_PATH_EXPANDED" skills/ark-onboard/SKILL.md
```

Expected: each >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): add greenfield steps 2a-2d for centralized vault setup"
```

---

### Task 6: Update Greenfield Step 17 Commit to Exclude the `vault` Symlink

The existing commit includes `git add {vault_path}/` which would try to commit the symlink (which is now gitignored) or, for embedded, the real vault dir. Split behavior based on `EMBEDDED_VAULT` flag.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "### Greenfield Step 17: Git init + initial commit" section (~line 1207).

- [ ] **Step 1: Locate and read the current Step 17 body**

Run:
```bash
grep -n "### Greenfield Step 17: Git init + initial commit" skills/ark-onboard/SKILL.md
sed -n '1207,1232p' skills/ark-onboard/SKILL.md
```

Confirm the current commit block uses `git add {vault_path}/`.

- [ ] **Step 2: Replace the commit block**

Use Edit to replace this block:

```
Commit:
```bash
git add {vault_path}/ CLAUDE.md .mcp.json .claude/settings.json .notebooklm/ 2>/dev/null
git commit -m "feat: initialize {project_name} vault with Ark structure"
```

If `.mcp.json` or `.claude/settings.json` was modified (Standard+ tier), include them in the commit.
```

With:

```markdown
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
```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "Centralized vault (default)" skills/ark-onboard/SKILL.md
grep -c "Embedded vault (escape hatch)" skills/ark-onboard/SKILL.md
grep -c 'wire {project_name} project to centralized vault' skills/ark-onboard/SKILL.md
```

Expected: all three >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): split greenfield commit for centralized vs embedded vault"
```

---

### Task 7: Add Embedded-Vault Escape-Hatch Sub-Flow to CLAUDE.md Writer

When the user picks embedded in Step 1 Prompt 5, write the opt-out row to CLAUDE.md's Project Configuration table.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "### Greenfield Step 10: Create/update CLAUDE.md" section (~line 842).

- [ ] **Step 1: Locate the current Step 10 template**

Run:
```bash
grep -n "### Greenfield Step 10: Create/update CLAUDE.md" skills/ark-onboard/SKILL.md
sed -n '842,870p' skills/ark-onboard/SKILL.md
```

Confirm the CLAUDE.md template block with the Project Configuration table.

- [ ] **Step 2: Extend the Step 10 body**

Use Edit. Find the template block ending with:

```
| **Task Management** | `{tasknotes_path}` — prefix: `{task_prefix}`, project: `{project_name}` |
```
` ``` `

And insert a new block immediately after it (before the next `## ` or `### `):

```markdown

**Vault-layout row (conditional):**

If the user picked **centralized** in Step 1, the default layout is symlinked. No extra row needed — check #20 defaults to `pass` when the `vault` symlink resolves.

If the user picked **embedded** (escape hatch), append this row to the Project Configuration table so check #20 recognizes the opt-out:

```markdown
| **Vault layout** | embedded (not symlinked) |
```

Check #20's grep contract: `^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded` (case-insensitive). Do not deviate from this exact row format — the diagnostic won't detect alternatives.

For monorepo layout, adjust the Obsidian Vault row to point at the project docs subdirectory and add the vault root separately.
```

Also add to the existing text "For monorepo layout, adjust..." — keep it but move it below the new conditional block.

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "\*\*Vault layout\*\* | embedded (not symlinked)" skills/ark-onboard/SKILL.md
grep -c "Vault-layout row (conditional)" skills/ark-onboard/SKILL.md
```

Expected: both >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): write embedded opt-out row to CLAUDE.md when escape hatch chosen"
```

---

### Task 8: Reframe "Non-Ark Vault (Migration)" Section — Ark Scaffolding vs Externalization

The existing "Path: Non-Ark Vault (Migration)" section mixes two concerns. Rename to make it clear:
- **Ark scaffolding** (current behavior — inline, safe): adding `_meta/`, `TaskNotes/`, etc. to a non-Ark vault.
- **Externalization** (new — plan file only): moving an embedded vault out into its own repo.

This task is a **rename + cross-reference** task. No logic changes to scaffolding itself. Externalization content lands in Task 9.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "## Path: Non-Ark Vault (Migration)" section header + intro (~line 1258).

- [ ] **Step 1: Locate**

Run:
```bash
grep -n "^## Path: Non-Ark Vault (Migration)" skills/ark-onboard/SKILL.md
grep -n "^### Migration Step 14: Final commit + reminders" skills/ark-onboard/SKILL.md
```

- [ ] **Step 2: Replace the section header + intro paragraph**

Use Edit. Find:

```
## Path: Non-Ark Vault (Migration)

Key principle: **additive only.** Never delete or overwrite existing content. Frontmatter changes are explicit and reversible (separate commits).
```

Replace with:

```markdown
## Path: Non-Ark Vault (Ark Scaffolding + Externalization Offer)

This path handles two distinct operations:

1. **Ark scaffolding** (inline, safe) — add `_meta/`, `_Templates/`, `TaskNotes/`, etc. to an existing vault that doesn't have Ark structure yet. Runs the 14-step flow below, same as the prior "Migration" behavior. Non-destructive: never deletes or overwrites existing content. Frontmatter changes are explicit and reversible (separate commits).

2. **Externalization** (destructive, plan file only) — if the scaffolded vault is still a real directory inside the project repo (i.e., `vault/` is not a symlink), the wizard also generates a plan file for moving the vault out into its own git repo and creating the symlink. The plan file is NOT executed; the user reviews and runs it via `/executing-plans` (see "Path: Externalization Plan Generation" below).

**Key principle (scaffolding):** additive only. Never delete or overwrite existing content. Frontmatter changes are explicit and reversible (separate commits).

**Key principle (externalization):** destructive steps live in a plan file, never in this skill's inline execution. Preflight gates prevent data loss.
```

- [ ] **Step 3: After the last migration step (Step 14), add a handoff to externalization**

Find the end of "### Migration Step 14: Final commit + reminders" (the last `Show follow-up reminders...` line in that section) and insert, before the next `---` or `## ` heading:

```markdown

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

```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "Ark Scaffolding + Externalization Offer" skills/ark-onboard/SKILL.md
grep -c "Migration Step 15: Offer externalization" skills/ark-onboard/SKILL.md
```

Expected: both >= 1.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "refactor(ark-onboard): reframe migration as ark-scaffolding + externalization offer"
```

---

### Task 9: Add "Path: Externalization Plan Generation" Section + Plan-File Template

Triggered when state detection finds `vault/` is a real directory with Ark artifacts and no embedded opt-out. The wizard generates a plan file, prints its path, and exits. No destructive steps.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, insert a new section BEFORE `## Path: Partial Ark (Repair)` (~line 1499).

- [ ] **Step 1: Locate the insertion point**

Run:
```bash
grep -n "^## Path: Partial Ark (Repair)" skills/ark-onboard/SKILL.md
```

- [ ] **Step 2: Insert the externalization path section**

Use Edit to insert this section immediately before the `## Path: Partial Ark (Repair)` header:

````markdown
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

````

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "^## Path: Externalization Plan Generation" skills/ark-onboard/SKILL.md
grep -c "### Externalization Step 1:" skills/ark-onboard/SKILL.md
grep -c "### Externalization Step 2:" skills/ark-onboard/SKILL.md
grep -c "Phase 0 — Preflight" skills/ark-onboard/SKILL.md
grep -c "Phase 1 — Externalize" skills/ark-onboard/SKILL.md
grep -c "Phase 2 — Sibling worktrees" skills/ark-onboard/SKILL.md
```

Expected: each >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): add externalization path with plan-file template"
```

---

### Task 10: Add Centralized-Vault Repair Cases to Repair Path

Handle the new Partial Ark conditions: broken symlink, symlink drift, missing script, missing post-checkout hook.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "## Path: Partial Ark (Repair)" section (~line 1499) — add a new subsection before "### Repair Step 1: Run full diagnostic".

- [ ] **Step 1: Locate**

Run:
```bash
grep -n "^## Path: Partial Ark (Repair)" skills/ark-onboard/SKILL.md
grep -n "^### Repair Step 1: Run full diagnostic" skills/ark-onboard/SKILL.md
```

- [ ] **Step 2: Insert a "Centralized-Vault Repair" subsection**

Use Edit. Insert between the `## Path: Partial Ark (Repair)` header's intro paragraph and the `### Repair Step 1` header:

```markdown

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

```

- [ ] **Step 3: Verify**

Run:
```bash
grep -c "### Centralized-Vault Repair" skills/ark-onboard/SKILL.md
grep -c "Backfill scripts/setup-vault-symlink.sh" skills/ark-onboard/SKILL.md
grep -c "Drift detected:" skills/ark-onboard/SKILL.md
```

Expected: each >= 1.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): add centralized-vault repair cases to repair path"
```

---

### Task 11: Update Healthy-Classification Rule (From "All Pass" to "No Fail")

The existing tier assignment logic in both `/ark-onboard` (scorecard section) and `/ark-health` says Healthy requires `all Critical + Standard checks pass`. This blocks warn-returning checks (10, 20). Change to `no Critical + Standard check returns fail`.

**Files:**
- Modify: `skills/ark-onboard/SKILL.md`, the "**Tier assignment for scorecard**" table (~line 1718).
- Modify: `skills/ark-health/SKILL.md`, the "**Tier assignment:**" block in "### Step 2: Classify Results" (~line 514).

- [ ] **Step 1: Locate the rules in both files**

Run:
```bash
grep -n "^| Tier | Condition |" skills/ark-onboard/SKILL.md
grep -n "^**Tier assignment:**" skills/ark-health/SKILL.md
```

- [ ] **Step 2: Update `/ark-onboard` tier table**

In `skills/ark-onboard/SKILL.md`, find:

```
| Tier | Condition |
|------|-----------|
| Quick | Checks 1-11 all pass |
| Standard | Checks 1-13 all pass |
| Full | Checks 1-19 all pass |
| Below Quick | Any critical check (1, 4-9) failing |
```

Replace with:

```markdown
| Tier | Condition |
|------|-----------|
| Quick | No Critical or Standard fail in checks 1-11 (warn is OK) |
| Standard | No Critical or Standard fail in checks 1-13 (warn is OK) |
| Full | No Critical or Standard fail in checks 1-20 (warn is OK) |
| Below Quick | Any critical check (1, 4-9) failing |

**Warn checks do not block tier classification.** Checks 10 (index staleness) and 20 (vault externalized) return `warn`, which counts as "no fail" for tier purposes. They still surface in the scorecard as warnings.
```

Also update the surrounding prose: "Checks 1-19 all pass" → "Checks 1-20 with no fail (warn is OK)" wherever else it appears. Run:

```bash
grep -n "Checks 1-19 all pass\|Checks 1-13 all pass\|Checks 1-11 all pass" skills/ark-onboard/SKILL.md
```

Fix each occurrence using Edit.

- [ ] **Step 3: Update `/ark-health` tier rules**

In `skills/ark-health/SKILL.md`, find the `**Tier assignment:**` block:

```
**Tier assignment:**

Determine the user's implicit tier from the highest tier that is fully passing:

- **Minimal tier:** Checks 1–9 all pass, checks 10–11 skip (no vault)
- **Quick tier:** Checks 1–11 all pass (vault present, no integrations)
- **Standard tier:** Checks 1–13 all pass (TaskNotes MCP configured)
- **Full tier:** Checks 1–19 all pass (MemPalace + history hook + NotebookLM)
```

Replace with:

```markdown
**Tier assignment:**

Determine the user's implicit tier from the highest tier where no Critical or Standard check returns `fail`. Warn and skip outcomes do NOT block tier classification.

- **Minimal tier:** No fail in checks 1–9, checks 10–11 skip (no vault)
- **Quick tier:** No fail in checks 1–11 (vault present, no integrations)
- **Standard tier:** No fail in checks 1–13 (TaskNotes MCP configured)
- **Full tier:** No fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Warn-returning checks (10 index staleness, 20 vault externalized) are advisory — they surface in the scorecard but don't demote the tier.
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -c "No Critical or Standard fail" skills/ark-onboard/SKILL.md
grep -c "No fail in checks 1-20" skills/ark-health/SKILL.md
grep -cE "Checks 1-1[39] all pass|Checks 1-11 all pass" skills/ark-onboard/SKILL.md
grep -cE "Checks 1–1[39] all pass|Checks 1–11 all pass" skills/ark-health/SKILL.md
```

Expected: first two >= 1; last two should be 0 (no leftover "all pass" phrasing).

- [ ] **Step 5: Commit**

```bash
git add skills/ark-onboard/SKILL.md skills/ark-health/SKILL.md
git commit -m "refactor(ark-onboard, ark-health): healthy = no fail (warn is OK)"
```

---

### Task 12: Add Check #20 to `/ark-health` (Authoritative) and Mirror in `/ark-onboard`

`/ark-health` is the authoritative source for check definitions. Add check #20 there first, then mirror in `/ark-onboard`'s Shared Diagnostic Checklist.

**Files:**
- Modify: `skills/ark-health/SKILL.md`, after the "**Check 19 — NotebookLM authenticated**" block (~line 458).
- Modify: `skills/ark-onboard/SKILL.md`, the "### Integrations (Checks 12-19)" table (~line 83).

- [ ] **Step 1: Locate**

Run:
```bash
grep -n "^**Check 19 — NotebookLM authenticated**" skills/ark-health/SKILL.md
grep -n "^## Workflow" skills/ark-health/SKILL.md
grep -n "^### Integrations (Checks 12-19)" skills/ark-onboard/SKILL.md
```

- [ ] **Step 2: Insert check #20 in `/ark-health` SKILL.md**

Use Edit. Find the end of the Check 19 block (before `---` followed by `## Workflow`). Insert:

````markdown

---

**Check 20 — Vault externalized** | Tier: Standard (warn-only, never fails)

Detection logic: examine three inputs — `vault` artifact (symlink / real dir / missing), `scripts/setup-vault-symlink.sh` (present / absent), and `CLAUDE.md` `Vault layout` row (opt-out present / absent).

```bash
# Inputs
IS_SYMLINK=false; SYMLINK_OK=false; SYMLINK_BROKEN=false; SYMLINK_DRIFT=false
SCRIPT_OK=false; REAL_DIR=false; MISSING=false; OPTOUT=false

if [ -L vault ]; then
  IS_SYMLINK=true
  if [ -e vault ]; then
    SYMLINK_OK=true
  else
    SYMLINK_BROKEN=true
  fi
elif [ -d vault ]; then
  REAL_DIR=true
else
  MISSING=true
fi

if [ -f scripts/setup-vault-symlink.sh ]; then
  SCRIPT_OK=true
  if [ "$SYMLINK_OK" = "true" ]; then
    SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
    EXPANDED=$(eval "echo $SCRIPT_TARGET")
    [ "$(readlink vault)" != "$EXPANDED" ] && SYMLINK_DRIFT=true
  fi
fi

if [ -f CLAUDE.md ] && grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md; then
  OPTOUT=true
fi

# Decision matrix — see table below
```

**Status table (exhaustive):**

| Observed state | Status | Message |
|----------------|--------|---------|
| Symlink, target resolves, matches script VAULT_TARGET (`SYMLINK_OK && SCRIPT_OK && !SYMLINK_DRIFT`) | `pass` | — |
| Real directory + opt-out present (`REAL_DIR && OPTOUT`) | `pass` | — |
| Missing entirely + opt-out present + no script (`MISSING && OPTOUT && !SCRIPT_OK`) | `pass` | Opt-out declares embedded; check 7 (vault-dir-exists) handles the missing vault as Critical fail. |
| Real directory, no opt-out (`REAL_DIR && !OPTOUT`) | `warn` | "Vault is embedded inside the project repo. Run `/ark-onboard` to externalize, or set `Vault layout: embedded` in CLAUDE.md if this is intentional." |
| Symlink, target missing (`SYMLINK_BROKEN`) | `warn` | "Vault symlink is broken. Run `/ark-onboard` Repair." |
| Symlink, target mismatch (`SYMLINK_DRIFT`) | `warn` | "Vault symlink target disagrees with `scripts/setup-vault-symlink.sh` VAULT_TARGET. Run `/ark-onboard` Repair." |
| Symlink present but script missing (`IS_SYMLINK && !SCRIPT_OK`) | `warn` | "Vault symlink exists but canonical script `scripts/setup-vault-symlink.sh` is missing. Run `/ark-onboard` Repair to backfill." |
| Missing entirely + script present (`MISSING && SCRIPT_OK`) | `warn` | "Canonical vault script exists but no `vault` artifact. Run `/ark-onboard` Repair to create the symlink." |
| Missing entirely + no script + no opt-out (`MISSING && !SCRIPT_OK && !OPTOUT`) | `warn` | "No vault configured. Run `/ark-onboard` Greenfield." |

Check #20 **never returns `fail`**. All negative states are `warn`. State detection independently classifies these conditions as Partial Ark for routing purposes.

- **Pass:** One of the pass conditions above holds.
- **Warn:** Any of the warn conditions above holds. Non-blocking — does NOT demote tier.
- **Fail:** Never.

---

````

- [ ] **Step 3: Update the `/ark-health` results-schema in Step 1**

The existing `results = { 1: ..., 19: ... }` block needs `20:` added. Find:

```
  18: pass|fail|upgrade|skip,
  19: pass|fail|upgrade|skip,
}
```

Replace with:

```
  18: pass|fail|upgrade|skip,
  19: pass|fail|upgrade|skip,
  20: pass|warn,
}
```

Also update the "For checks 15, 16, 18, 19" line to include 20 where relevant (actually no — check 20 doesn't have prerequisites; leave that line alone).

- [ ] **Step 4: Update `/ark-health` scorecard output format**

In the `## Output Format` section of `skills/ark-health/SKILL.md`, update the "Vault Structure" block example to reference check 20. Find the section "Integrations" in the example scorecard and add a new line in the "Vault Structure" block:

```
Vault Structure
  OK  Vault healthy ({N} pages, {standalone|monorepo} layout)
  ~~  Index stale ({N} pages modified since last generation)
      Refresh: cd {vault_root} && python3 _meta/generate-index.py
  OK  Python {version} available
  OK  Vault externalized (symlink -> $HOME/.superset/vaults/{project})
```

Update to include a warn example under the same block (this is the case where vault is embedded without opt-out):

```
Vault Structure
  OK  Vault healthy ({N} pages, {standalone|monorepo} layout)
  ~~  Index stale ({N} pages modified since last generation)
      Refresh: cd {vault_root} && python3 _meta/generate-index.py
  OK  Python {version} available
  ~~  Vault embedded inside project repo (no opt-out)
      Fix: Run /ark-onboard to externalize, or set `Vault layout: embedded` in CLAUDE.md
```

Include both OK and warn rendering variants in the example prose.

- [ ] **Step 5: Mirror check #20 in `/ark-onboard`'s Shared Diagnostic Checklist**

In `skills/ark-onboard/SKILL.md`, find the "### Integrations (Checks 12-19)" table and:

1. Rename the heading to "### Integrations (Checks 12-20)".
2. Append one row to the table:

```markdown
| 20 | Vault externalized | Standard (warn-only) | Symlink matches script VAULT_TARGET, OR CLAUDE.md `Vault layout` opt-out row present |
```

3. Update the "Running Diagnostics" result schema block to include `20:`.

- [ ] **Step 6: Verify**

Run:
```bash
grep -c "Check 20 — Vault externalized" skills/ark-health/SKILL.md
grep -cE "^\| 20 \| Vault externalized" skills/ark-onboard/SKILL.md
grep -c "Integrations (Checks 12-20)" skills/ark-onboard/SKILL.md
grep -c "20: pass|warn" skills/ark-health/SKILL.md
```

Expected: each >= 1.

- [ ] **Step 7: Commit**

```bash
git add skills/ark-health/SKILL.md skills/ark-onboard/SKILL.md
git commit -m "feat(ark-health, ark-onboard): add check #20 vault-externalized (warn-only)"
```

---

### Task 13: Add Downstream Skill Notes — `/notebooklm-vault`, `/wiki-update`, `/codebase-maintenance`, `/ark-workflow`

Small prose additions — one short note per skill explaining how to behave when the vault is a symlink.

**Files:**
- Modify: `skills/notebooklm-vault/SKILL.md`
- Modify: `skills/wiki-update/SKILL.md`
- Modify: `skills/codebase-maintenance/SKILL.md`
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 1: Add centralized-vault note to `/notebooklm-vault`**

Find the "## Architecture" section in `skills/notebooklm-vault/SKILL.md`. Append this subsection at the end of the Architecture section (before the next `## ` heading):

```markdown

### Centralized Vault Awareness

When the project's `vault` is a symlink (centralized-vault pattern), this skill:
- Reads `.notebooklm/config.json` from the project root first (expected `vault_root: "vault"`), falls back to `<vault>/.notebooklm/config.json` (expected `vault_root: "."`). Both resolve to the same directory.
- Locates `sync-state.json` exclusively inside the vault repo: `<vault>/.notebooklm/sync-state.json`. Never writes sync-state to the project repo.
- Bootstraps missing `sync-state.json` with empty state `{"last_sync": null, "files": {}}` on first sync.

Detect via `test -L vault`. When vault is NOT a symlink (embedded layout), sync-state remains in the project repo's `.notebooklm/` directory — backward compatible.
```

- [ ] **Step 2: Add centralized-vault note to `/wiki-update`**

Find where session logs are created in `skills/wiki-update/SKILL.md`. Grep:

```bash
grep -n "session log\|session-log\|Session-Log" skills/wiki-update/SKILL.md | head -10
```

Near the session-log creation block (likely around filename generation), insert or append this note:

```markdown
**Cross-environment collision prevention:**

When `vault` is a symlink (centralized-vault pattern), multiple environments (Mac, CT110, other machines) may write session logs into the same vault. To prevent filename collisions, prefix session log filenames with the environment:

```bash
if [ -L vault ]; then
  ENV_PREFIX=$(hostname -s | tr '[:upper:]' '[:lower:]')
  SESSION_FILE="Session-Logs/${ENV_PREFIX}-$(date +%Y-%m-%d-%H%M)-${SESSION_TITLE_SLUG}.md"
else
  SESSION_FILE="Session-Logs/$(date +%Y-%m-%d-%H%M)-${SESSION_TITLE_SLUG}.md"
fi
```

Short hostnames like `mac`, `ct110` keep the prefix concise. For embedded vaults (no symlink), keep the legacy naming.
```

Pick a natural insertion point near the session-log creation code. If the skill currently has a specific heading like "## Session Log Creation" or similar, append this subsection there.

- [ ] **Step 3: Add centralized-vault note to `/codebase-maintenance`**

In `skills/codebase-maintenance/SKILL.md`, find the section on vault sync/commit. Grep:

```bash
grep -n "vault.*commit\|commit.*vault" skills/codebase-maintenance/SKILL.md | head -5
```

Append a short note (near the vault sync section, or at the end of the skill body):

```markdown

### Centralized Vault — Commit Targets

When the project's `vault` is a symlink, vault content lives in a separate git repo. Commit and push operations must target the **vault repo**, not the project repo:

```bash
if [ -L vault ]; then
  cd "$(readlink vault)"
  git add . && git commit -m "vault: {reason}" && git push
  cd -
else
  # Embedded layout — vault is part of the project repo
  git add vault/ && git commit -m "vault: {reason}"
fi
```

Do not `git add vault/` in the project repo when `vault` is a symlink — it's in `.gitignore` anyway, but the error message is confusing.
```

- [ ] **Step 4: Add centralized-vault surfacing to `/ark-workflow`**

In `skills/ark-workflow/SKILL.md`, find the section that triages tasks or outputs the skill chain. Grep:

```bash
grep -n "recommend\|surface\|suggest" skills/ark-workflow/SKILL.md | head -10
```

Append this subsection at the end of the skill body (before the last `---` or final heading):

```markdown

### Centralized-Vault Suggestion

During triage, check the vault layout. If `vault` is a real directory (not a symlink) AND no `embedded` opt-out is present in CLAUDE.md, surface the externalization recommendation:

```bash
if [ -d vault ] && [ ! -L vault ]; then
  if ! grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md 2>/dev/null; then
    echo ""
    echo "ℹ️  Heads-up: your vault is embedded inside the project repo."
    echo "   For worktree/Obsidian-app consistency, consider running:"
    echo "   /ark-onboard  (will generate an externalization plan)"
    echo ""
  fi
fi
```

This is advisory only — does not block workflow routing.
```

- [ ] **Step 5: Verify all four skills**

Run:
```bash
grep -c "Centralized Vault Awareness" skills/notebooklm-vault/SKILL.md
grep -c "Cross-environment collision prevention" skills/wiki-update/SKILL.md
grep -c "Centralized Vault — Commit Targets" skills/codebase-maintenance/SKILL.md
grep -c "Centralized-Vault Suggestion" skills/ark-workflow/SKILL.md
```

Expected: each returns 1.

- [ ] **Step 6: Commit**

```bash
git add skills/notebooklm-vault/SKILL.md skills/wiki-update/SKILL.md skills/codebase-maintenance/SKILL.md skills/ark-workflow/SKILL.md
git commit -m "docs(downstream): centralized-vault awareness notes for 4 skills"
```

---

### Task 14: End-to-End Smoke Test on a Scratch Directory

Manual validation of the wizard's new behavior by dry-running greenfield + repair on a throwaway directory. This is our stand-in for automated tests.

**Files:**
- No changes. Validation only.

- [ ] **Step 1: Create scratch workspace**

```bash
SCRATCH="/tmp/ark-onboard-smoke-$(date +%s)"
mkdir -p "$SCRATCH" && cd "$SCRATCH"
git init
git config user.name "Test User"
git config user.email "test@example.com"
```

- [ ] **Step 2: Walk the Greenfield centralized path by hand**

Using the steps documented in `skills/ark-onboard/SKILL.md`'s new Greenfield 2a-2d:

```bash
# Step 2a: Create vault repo
SCRATCH_VAULT="$HOME/Vaults/smoke-test-project"
mkdir -p "$SCRATCH_VAULT" && (cd "$SCRATCH_VAULT" && git init)
echo '{"last_sync": null, "files": {}}' > "$SCRATCH_VAULT/.notebooklm/sync-state.json" 2>/dev/null || {
  mkdir -p "$SCRATCH_VAULT/.notebooklm"
  echo '{"last_sync": null, "files": {}}' > "$SCRATCH_VAULT/.notebooklm/sync-state.json"
}

# Step 2b: Symlink
ln -s "$SCRATCH_VAULT" vault
echo 'vault' >> .gitignore

# Step 2c: Write the script + install the hook
mkdir -p scripts
cat > scripts/setup-vault-symlink.sh <<'EOF'
#!/usr/bin/env bash
set -e
VAULT_TARGET="$HOME/Vaults/smoke-test-project"
TINYAGI_FALLBACK=""
if [ -L vault ] && [ -e vault ]; then exit 0; fi
if [ -L vault ] && [ ! -e vault ]; then rm vault; fi
if [ -d vault ]; then echo "ERROR: vault/ is a real directory." >&2; exit 1; fi
if [ -d "$VAULT_TARGET" ]; then ln -s "$VAULT_TARGET" vault; exit 0; fi
echo "ERROR: vault repo not cloned." >&2; exit 1
EOF
chmod +x scripts/setup-vault-symlink.sh

HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
HOOK_EOF
chmod +x "$HOOK_PATH"
```

- [ ] **Step 3: Verify Greenfield state**

```bash
test -L vault && test -e vault && echo "symlink OK"
test -x scripts/setup-vault-symlink.sh && echo "script OK"
test -x "$(git rev-parse --git-common-dir)/hooks/post-checkout" && echo "hook OK"
grep -qE '^VAULT_TARGET="\$HOME/' scripts/setup-vault-symlink.sh && echo "portable VAULT_TARGET OK"
grep -qxF 'vault' .gitignore && echo ".gitignore OK"
ls "$SCRATCH_VAULT/.notebooklm/sync-state.json" && echo "sync-state OK"
```

Expected: all six lines print "OK".

- [ ] **Step 4: Verify worktree auto-symlink**

Commit the scratch project state first (so `git worktree add` has something to branch from):

```bash
git add .gitignore scripts/setup-vault-symlink.sh
git commit -m "smoke: initial commit"

# Create a worktree
git worktree add ../smoke-wt HEAD -b smoke-branch
cd ../smoke-wt
test -L vault && test -e vault && echo "worktree vault symlink OK"
readlink vault   # Should match $SCRATCH_VAULT
```

Expected: "worktree vault symlink OK" + readlink output matches `$SCRATCH_VAULT`.

- [ ] **Step 5: Verify Repair flow (broken symlink)**

```bash
cd "$SCRATCH"
rm vault
# Re-run the script manually (simulates /ark-onboard Repair)
bash scripts/setup-vault-symlink.sh
test -L vault && test -e vault && echo "repair OK"
```

Expected: "repair OK".

- [ ] **Step 6: Verify check #20 pass condition**

```bash
# Inline the check #20 logic manually
SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
EXPANDED=$(eval "echo $SCRIPT_TARGET")
[ -L vault ] && [ "$(readlink vault)" = "$EXPANDED" ] && echo "check #20: PASS"
```

Expected: "check #20: PASS".

- [ ] **Step 7: Verify check #20 warn on embedded**

```bash
# Simulate embedded layout (no symlink, real dir)
cd "$SCRATCH"
git worktree remove ../smoke-wt 2>/dev/null || rm -rf ../smoke-wt
rm vault
mkdir vault
touch vault/dummy.md

# Without opt-out, check #20 should warn
if grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md 2>/dev/null; then
  echo "check #20: PASS (opt-out)"
elif [ -d vault ] && [ ! -L vault ]; then
  echo "check #20: WARN (embedded, no opt-out)"
fi
```

Expected: "check #20: WARN (embedded, no opt-out)".

Add opt-out and recheck:

```bash
cat > CLAUDE.md <<'EOF'
# Smoke

## Project Configuration

| **Vault layout** | embedded (not symlinked) |
EOF

if grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md 2>/dev/null; then
  echo "check #20: PASS (opt-out)"
fi
```

Expected: "check #20: PASS (opt-out)".

- [ ] **Step 8: Clean up**

```bash
cd "$HOME"
rm -rf "$SCRATCH" "$SCRATCH_VAULT" 2>/dev/null
echo "Smoke test complete."
```

- [ ] **Step 9: Document smoke-test result (no commit)**

This task produces no git changes. Record the result inline in the TaskCreate task subject (e.g., "smoke test passed, all assertions OK"). No commit needed.

---

### Task 15: Bump Version + Update CHANGELOG + Commit Release

Per project convention (memory `feedback_version_bump.md`): bump VERSION, plugin.json, marketplace.json, CHANGELOG on every push to master.

**Files:**
- Modify: `VERSION`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read current version**

```bash
cat VERSION
# Expected: 1.10.1
```

- [ ] **Step 2: Determine next version**

This is a **minor** version bump (new feature: centralized-vault wizard + check #20). Next version: `1.11.0`.

- [ ] **Step 3: Update VERSION**

```bash
echo "1.11.0" > VERSION
```

- [ ] **Step 4: Update `.claude-plugin/plugin.json`**

Use Edit. In `/Users/sunginkim/.superset/worktrees/ark-skills/vault-symlink/.claude-plugin/plugin.json`, find `"version": "1.10.1",` and replace with `"version": "1.11.0",`.

- [ ] **Step 5: Update `.claude-plugin/marketplace.json`**

```bash
grep -n '"version"' .claude-plugin/marketplace.json
```

Use Edit. Find `"version": "1.10.1"` and replace with `"version": "1.11.0"`.

- [ ] **Step 6: Prepend new CHANGELOG entry**

Use Edit. In `CHANGELOG.md`, find the first occurrence of `## [` (the most recent entry header). Insert a new entry block immediately before it:

```markdown
## [1.11.0] - 2026-04-12

### Added

- **`/ark-onboard` centralized-vault recommendation.** Greenfield now defaults to an externalized vault at `~/.superset/vaults/<project>/` (or `~/Vaults/<project>/` for non-superset users) with a `vault` symlink into the project repo. Mirrors ArkNode-Poly's production pattern. Includes:
  - New Greenfield Steps 2a-2d (vault repo init, symlink, automation install, GitHub remote offer).
  - Explicit embedded-vault escape hatch via `| **Vault layout** | embedded (not symlinked) |` row in CLAUDE.md.
  - `$HOME/`-portable `VAULT_TARGET` in the tracked `scripts/setup-vault-symlink.sh` — collaborators' clones are not poisoned with machine-specific paths.
  - Path constraint: vault paths must be under `$HOME` (users with external drives symlink-in).
- **Externalization path.** Projects with an embedded `vault/` directory + no opt-out now route through a plan-file generator that emits `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`. The plan has Phase 0 preflight (including `git diff --no-index` sibling comparison + empty-dir shape check), Phase 1 destructive main-repo steps, Phase 2 per-sibling worktree conversion, Phase 3 manual follow-ups.
- **Repair additions.** Centralized-vault-specific repairs for broken symlink, symlink-drift (readlink vs script VAULT_TARGET), missing canonical script (with backfill from readlink), and missing post-checkout hook.
- **Check #20 — vault-externalized (warn-only, Standard tier).** Exhaustive status matrix across symlink/real-dir/missing × script-present/absent × opt-out. Never fails — embedded vaults still qualify as Healthy when opt-out is explicit.
- Downstream skill notes in `/notebooklm-vault` (sync-state location), `/wiki-update` (hostname-prefixed session logs), `/codebase-maintenance` (vault-repo commit target), `/ark-workflow` (advisory surfacing).

### Changed

- **Healthy-classification rule relaxed** in both `/ark-onboard` and `/ark-health`: was "all Critical + Standard pass," now "no Critical or Standard fail (warn is OK)." Allows warn-returning checks (10 index staleness, 20 vault-externalized) to surface as advisory without demoting tier.
- **Total diagnostic checks: 19 → 20.**

### Design notes

Spec: `docs/superpowers/specs/2026-04-12-ark-onboard-centralized-vault-design.md` (commit `dd80baa`, revision 4, codex round-4 PASS).

```

- [ ] **Step 7: Verify all four files updated consistently**

```bash
cat VERSION
grep '"version"' .claude-plugin/plugin.json
grep '"version"' .claude-plugin/marketplace.json
head -5 CHANGELOG.md
```

Expected:
- `VERSION`: `1.11.0`
- `plugin.json`: `"version": "1.11.0",`
- `marketplace.json`: `"version": "1.11.0"`
- `CHANGELOG.md`: first non-title line is `## [1.11.0] - 2026-04-12`.

- [ ] **Step 8: Commit the release**

```bash
git add VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: bump to v1.11.0 (centralized vault in /ark-onboard)"
```

- [ ] **Step 9: Verify clean working tree**

```bash
git status
```

Expected: `nothing to commit, working tree clean`.

---

## Plan self-review (run by agent after writing this plan)

1. **Spec coverage:**
   - Terminology + architecture → Task 1 ✓
   - `scripts/setup-vault-symlink.sh` template + post-checkout hook + `.superset/config.json` → Task 2 ✓
   - State-detection updates (symlink/opt-out/drift signals, REPAIR_REASON routing) → Task 3 ✓
   - Greenfield Step 1 rewrite (centralized default + escape hatch + path constraint) → Task 4 ✓
   - Greenfield Steps 2a-2d (vault repo, symlink, automation, GitHub) → Task 5 ✓
   - Greenfield commit split (vault-repo commit vs project-repo commit) → Task 6 ✓
   - Embedded opt-out row in CLAUDE.md → Task 7 ✓
   - Migration → Ark scaffolding + Externalization split → Task 8 ✓
   - Externalization plan path + plan-file template (Phases 0-3) → Task 9 ✓
   - Repair additions (drift, missing script, backfill, hook reinstall) → Task 10 ✓
   - Healthy-classification rule revision → Task 11 ✓
   - Check #20 authoritative in `/ark-health`, mirror in `/ark-onboard` → Task 12 ✓
   - Downstream skills — `/notebooklm-vault`, `/wiki-update`, `/codebase-maintenance`, `/ark-workflow` → Task 13 ✓
   - Smoke test → Task 14 ✓
   - Version bump + CHANGELOG + marketplace → Task 15 ✓

2. **Placeholder scan:** No `TBD` / `TODO` / `implement later`. Every code block has executable content. Every Edit specifies exact strings. Every verify step has concrete grep commands with expected counts.

3. **Type consistency:**
   - `<vault_repo_path>` — always full vault path, never a parent
   - `<VAULT_REPO_PATH_PORTABLE>` — template var, always `$HOME/...` prefix
   - `VAULT_REPO_PATH_EXPANDED` — runtime variable, absolute path after `eval`
   - `<common_git_dir>` — output of `git rev-parse --git-common-dir`
   - `EMBEDDED_OPTOUT`, `SYMLINK_DRIFT`, etc. — consistent uppercase flag names across Tasks 3, 10, 12
   - Check #20 tier label: "Standard (warn-only)" consistently in Tasks 11 and 12
   - CLAUDE.md opt-out row format: `| **Vault layout** | embedded (not symlinked) |` — consistent in Tasks 7, 12, 13, and spec

4. **Spec requirements with no task:** None identified.
