# /ark-health — Check Implementations

Bash implementations for the checks whose detection logic is too large to keep inline in `SKILL.md`. Each section below is keyed by check number, matching the pointers in the main skill file. Loaded on-demand by the agent when running the corresponding check.

The pass/fail semantics, tier tags, and fix actions live authoritatively in `SKILL.md`. This file is implementation-only.

---

## Check 5 — CLAUDE.md required fields

Parse CLAUDE.md for all 4 required fields (project name, vault root, task prefix, TaskNotes path). A field is "present" if it has a non-empty value with the correct format.

```bash
# Check for vault root (line containing "Obsidian Vault" with a path, or vault/ reference)
grep -q "vault" CLAUDE.md 2>/dev/null && echo "vault: found" || echo "vault: MISSING"

# Check for task prefix (pattern: word ending with dash, like ArkSignal-)
grep -oE '[A-Za-z][A-Za-z0-9]*-' CLAUDE.md 2>/dev/null | head -3

# Check for project name (usually in header or table)
head -5 CLAUDE.md 2>/dev/null

# Check for TaskNotes path
grep -i "tasknotes" CLAUDE.md 2>/dev/null | head -3
```

---

## Check 6 — Task prefix format

Extract the task prefix from CLAUDE.md, verify it ends with `-`, then verify the counter file path resolves.

```bash
# Extract task prefix from CLAUDE.md — look for "prefix:" row or similar
TASK_PREFIX=$(grep -oE 'prefix: `?[A-Za-z][A-Za-z0-9]*-`?' CLAUDE.md 2>/dev/null | grep -oE '[A-Za-z][A-Za-z0-9]*-' | head -1)

# Extract TaskNotes path
TASKNOTES_PATH=$(grep -i "tasknotes" CLAUDE.md 2>/dev/null | grep -oE 'vault/[^ ]+/' | head -1)

# Derive and check counter file
COUNTER_FILE="${TASKNOTES_PATH}meta/${TASK_PREFIX}counter"
echo "Expected counter file: $COUNTER_FILE"
ls "$COUNTER_FILE" 2>/dev/null && echo "PASS: counter file exists" || echo "FAIL: counter file not found at $COUNTER_FILE"
```

---

## Check 8 — Vault structure

`VAULT_ROOT` extracted from CLAUDE.md. A well-formed vault must have `_meta/`, `_Templates/`, and `TaskNotes/` subdirectories. Layout detection: standalone = `00-Home.md` at vault root; monorepo = has a project docs subdirectory.

```bash
# Required subdirectories
ls -d "${VAULT_ROOT}_meta/" 2>/dev/null && echo "_meta: OK" || echo "_meta: MISSING"
ls -d "${VAULT_ROOT}_Templates/" 2>/dev/null && echo "_Templates: OK" || echo "_Templates: MISSING"
ls -d "${VAULT_ROOT}TaskNotes/" 2>/dev/null && echo "TaskNotes: OK" || echo "TaskNotes: MISSING"

# Layout detection
ls "${VAULT_ROOT}00-Home.md" 2>/dev/null && echo "layout: standalone" || echo "layout: monorepo (or missing 00-Home.md)"
```

---

## Check 10 — Index status

Index staleness is a **warning**, not a failure.

```bash
# Does index.md exist?
ls "${VAULT_ROOT}index.md" 2>/dev/null && echo "index.md: exists" || echo "index.md: MISSING"

# Check staleness: compare index.md mtime against newest .md file
# (excluding TaskNotes/Archive/, _Templates/, _Attachments/)
INDEX_MTIME=$(stat -f "%m" "${VAULT_ROOT}index.md" 2>/dev/null || stat -c "%Y" "${VAULT_ROOT}index.md" 2>/dev/null)

NEWEST_PAGE_MTIME=$(find "${VAULT_ROOT}" -name "*.md" \
  ! -path "${VAULT_ROOT}TaskNotes/Archive/*" \
  ! -path "${VAULT_ROOT}_Templates/*" \
  ! -path "${VAULT_ROOT}_Attachments/*" \
  ! -name "index.md" \
  -newer "${VAULT_ROOT}index.md" 2>/dev/null | wc -l | tr -d ' ')

echo "Pages modified since last index generation: $NEWEST_PAGE_MTIME"
```

---

## Check 11 — Task counter

```bash
# TASKNOTES_PATH and TASK_PREFIX from CLAUDE.md
COUNTER_FILE="${TASKNOTES_PATH}meta/${TASK_PREFIX}counter"
ls "$COUNTER_FILE" 2>/dev/null || echo "FAIL: counter file not found"

# Verify contents are an integer
COUNTER_VALUE=$(cat "$COUNTER_FILE" 2>/dev/null | tr -d '[:space:]')
echo "$COUNTER_VALUE" | grep -qE '^[0-9]+$' && echo "PASS: counter = $COUNTER_VALUE" || echo "FAIL: counter file is not an integer"
```

---

## Check 16 — History auto-index hook

Five sub-conditions. 1–2 are pass/fail; 3–5 are warnings (hook installed but effect silently compromised).

Note on condition 2: Claude Code merges hook arrays from global `~/.claude/settings.json` and project-local `.claude/settings.json`. If the hook is registered globally, it fires even when project-local has no Stop hook. Checking project-local registration is defensive coverage, not a strict correctness check — but the cleanest way to prove the hook is set up for this project without parsing global settings.

```bash
# --- Conditions 1 and 2: pass/fail ---
ls ~/.claude/hooks/ark-history-hook.sh 2>/dev/null && echo "hook script: OK" || echo "hook script: MISSING"
grep -q "ark-history-hook" .claude/settings.json 2>/dev/null && echo "hook registered: OK" || echo "hook registered: MISSING"

# --- Condition 3: wing-match (warn) ---
# Use the same derivation as skills/shared/mine-vault.sh:61-72
# NOTE: always pass `--` to grep so that wing keys starting with `-` are not parsed as flags
EXPECTED_WING=$(echo "$PWD" | sed 's|[/.]|-|g')
ACTUAL_WINGS=$(mempalace status 2>/dev/null | grep -oE 'WING:[[:space:]]*[^[:space:]]+' | awk '{print $2}')
if echo "$ACTUAL_WINGS" | grep -Fxq -- "$EXPECTED_WING"; then
  echo "wing-match: OK ($EXPECTED_WING)"
else
  CLOSEST=$(echo "$ACTUAL_WINGS" | grep -F -- "$EXPECTED_WING" | head -1)
  CLOSEST=${CLOSEST:-none}
  echo "wing-match: WARN (expected $EXPECTED_WING, found $CLOSEST)"
fi

# --- Conditions 4 and 5: threshold state (warn) ---
THRESH_FILE="$HOME/.mempalace/hook_state/compile_threshold.json"
DRAWER_FILE="$HOME/.mempalace/hook_state/${EXPECTED_WING}_drawer_count"
if [ -f "$THRESH_FILE" ] && [ -f "$DRAWER_FILE" ]; then
  BASELINE=$(python3 -c "import json,sys;d=json.load(open('$THRESH_FILE'));print(d.get('$EXPECTED_WING',{}).get('drawers_at_last_compile',0))")
  CURRENT=$(cat "$DRAWER_FILE")
  NEW=$((CURRENT - BASELINE))
  # Condition 4: threshold-staleness — way overdue for compile
  if [ "$NEW" -ge 200 ]; then
    echo "threshold-staleness: WARN ($NEW new drawers >= 200 but compile never fired)"
  else
    echo "threshold-staleness: OK ($NEW new drawers since last compile)"
  fi
  # Condition 5: threshold-lock — baseline frozen at current large count
  if [ "$CURRENT" = "$BASELINE" ] && [ "$BASELINE" -gt 500 ]; then
    echo "threshold-lock: WARN (baseline locked at $BASELINE, no new drawers)"
  else
    echo "threshold-lock: OK"
  fi
fi
```

**Warn fixes (detail):**
- **Wing-match:** If you recently moved the project, re-run `bash skills/shared/mine-vault.sh`. Subproject wings by design (e.g., monorepo) are cosmetic — skip.
- **Threshold-staleness:** Run `/claude-history-ingest compile` manually to clear the backlog.
- **Threshold-lock:** Accumulate ≥50 new drawers naturally (run more sessions) or reset baseline:
  ```bash
  jq '."<wing>".drawers_at_last_compile = 0' ~/.mempalace/hook_state/compile_threshold.json > /tmp/t \
    && mv /tmp/t ~/.mempalace/hook_state/compile_threshold.json
  ```

---

## Check 18 — NotebookLM config

Config may be in either the vault or the project root.

```bash
# Check project root first, then vault root
CONFIG_FOUND=""
if [ -f .notebooklm/config.json ]; then
  echo "config: project root"
  CONFIG_FOUND=".notebooklm/config.json"
elif [ -f "${VAULT_ROOT}.notebooklm/config.json" ]; then
  echo "config: vault root"
  CONFIG_FOUND="${VAULT_ROOT}.notebooklm/config.json"
else
  echo "FAIL: .notebooklm/config.json not found in project root or vault root"
fi

# If config found, check for non-empty notebook ID
if [ -n "$CONFIG_FOUND" ]; then
  grep -q '"id":\s*"[^"]' "$CONFIG_FOUND" && echo "notebook ID: present" || echo "notebook ID: MISSING or empty"
fi
```

---

## Check 20 — Vault externalized

Warn-only; never fails. Detection inputs: `vault` artifact (symlink / real dir / missing), `scripts/setup-vault-symlink.sh` (present / absent), CLAUDE.md `Vault layout` row (opt-out present / absent).

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
```

**Status matrix:**

| Observed state | Status | Message |
|----------------|--------|---------|
| Symlink, target resolves, matches script VAULT_TARGET (`SYMLINK_OK && SCRIPT_OK && !SYMLINK_DRIFT`) | `pass` | — |
| Real directory + opt-out present (`REAL_DIR && OPTOUT`) | `pass` | — |
| Missing entirely + opt-out present + no script (`MISSING && OPTOUT && !SCRIPT_OK`) | `pass` | Opt-out declares embedded; check 7 handles missing vault as Critical fail. |
| Real directory, no opt-out (`REAL_DIR && !OPTOUT`) | `warn` | "Vault is embedded inside the project repo. Run `/ark-onboard` to externalize, or set `Vault layout: embedded` in CLAUDE.md if this is intentional." |
| Symlink, target missing (`SYMLINK_BROKEN`) | `warn` | "Vault symlink is broken. Run `/ark-onboard` Repair." |
| Symlink, target mismatch (`SYMLINK_DRIFT`) | `warn` | "Vault symlink target disagrees with `scripts/setup-vault-symlink.sh` VAULT_TARGET. Run `/ark-onboard` Repair." |
| Symlink present but script missing (`IS_SYMLINK && !SCRIPT_OK`) | `warn` | "Vault symlink exists but canonical script `scripts/setup-vault-symlink.sh` is missing. Run `/ark-onboard` Repair to backfill." |
| Missing entirely + script present (`MISSING && SCRIPT_OK`) | `warn` | "Canonical vault script exists but no `vault` artifact. Run `/ark-onboard` Repair to create the symlink." |
| Missing entirely + no script + no opt-out (`MISSING && !SCRIPT_OK && !OPTOUT`) | `warn` | "No vault configured. Run `/ark-onboard` Greenfield." |

Check #20 **never returns `fail`**. State detection classifies these independently for routing purposes.

---

## Check 22 — ark-skills plugin version current

Compare the project's recorded plugin version against the current plugin version, and assert `.ark/` is not gitignored.

```bash
# Read project's recorded plugin version
ARK_PLUGIN_VERSION_FILE=".ark/plugin-version"
if [ -f "$ARK_PLUGIN_VERSION_FILE" ]; then
  PROJECT_PLUGIN_VERSION=$(cat "$ARK_PLUGIN_VERSION_FILE")
else
  PROJECT_PLUGIN_VERSION="(not recorded)"
fi

# Read the canonical VERSION from the plugin root
if [ -n "$ARK_SKILLS_ROOT" ] && [ -f "$ARK_SKILLS_ROOT/VERSION" ]; then
  CURRENT_PLUGIN_VERSION=$(cat "$ARK_SKILLS_ROOT/VERSION")
else
  CURRENT_PLUGIN_VERSION="(ARK_SKILLS_ROOT not set or VERSION missing)"
fi

if [ "$PROJECT_PLUGIN_VERSION" = "$CURRENT_PLUGIN_VERSION" ]; then
  echo "PASS: plugin version current ($CURRENT_PLUGIN_VERSION)"
elif [ "$PROJECT_PLUGIN_VERSION" = "(not recorded)" ]; then
  echo "WARN: .ark/plugin-version not found — run /ark-update to record current version"
else
  echo "WARN: upgrade available: run /ark-update (project: $PROJECT_PLUGIN_VERSION, current: $CURRENT_PLUGIN_VERSION)"
fi

# Assert .ark/ is not gitignored (pre-mortem Scenario 3 mitigation)
if git check-ignore -q .ark/ 2>/dev/null; then
  echo "WARN: .ark/ is gitignored — remove the pattern and commit before running /ark-update"
fi
```
