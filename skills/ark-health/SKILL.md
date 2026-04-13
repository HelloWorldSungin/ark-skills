---
name: ark-health
description: Diagnostic check for Ark ecosystem health — plugins, CLAUDE.md, vault, integrations
---

# Ark Health Check

Run all 19 diagnostic checks across the Ark ecosystem and produce a scored report with actionable fix instructions.

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete. When CLAUDE.md is absent:

- Checks 1–3 (Plugins) run normally
- Checks 4–6 (Project Configuration) report **fail** with explanation
- Checks 7–19 report "cannot check — CLAUDE.md missing" instead of failing silently

Never abort early. Run all 19 checks regardless of earlier failures.

## Vault Path Terminology

| Term | Meaning | Example |
|------|---------|---------|
| **Vault root** | Top-level directory containing all vault content | `vault/` |
| **Project docs path** | Subdirectory for project-specific knowledge (may equal vault root for standalone projects) | `vault/Trading-Signal-AI/` |
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

## Required CLAUDE.md Fields

Four user-provided fields (everything else is derived):

| Field | Format | Example |
|-------|--------|---------|
| Project name | Any string | `trading-signal-ai` |
| Vault root | Path ending with `/` | `vault/` |
| Task prefix | Ends with `-` | `ArkSignal-` |
| TaskNotes path | Path ending with `/` | `vault/TaskNotes/` |

Derived values:
- **Counter file:** `{tasknotes_path}/meta/{task_prefix}counter` (e.g., `vault/TaskNotes/meta/ArkSignal-counter`)
- **Project docs path:** From "Obsidian Vault" row in CLAUDE.md

## Diagnostic Checklist

### Plugins (Checks 1–3)

**Check 1 — superpowers plugin** | Tier: Critical

Detect by checking if superpowers skills are available in the current session. Look for: `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`.

Detection: Read the `system-reminder` skill list in your current session context. Search for entries prefixed with `superpowers:` (e.g., `superpowers:brainstorming`, `superpowers:writing-plans`). If at least one matching entry exists, pass.

- **Pass:** At least one `superpowers:*` skill is available in the current session
- **Fail action:** Install with `/plugin install superpowers@claude-plugins-official` (marketplace: `anthropics/claude-plugins-official`)
- **Tier:** Critical — brainstorming, TDD, writing-plans, and code review patterns depend on this

---

**Check 2 — gstack plugin** | Tier: Standard

Best-effort detection: check if gstack skills are loadable in the current session. Look for: `browse`, `qa`, `ship`, `review`, `design-review`.

Note: Plugin detection relies on skill availability in the session, not filesystem inspection of `~/.claude/plugins/`.

Detection: Read the `system-reminder` skill list in your current session context. Search for gstack skill entries (e.g., `browse`, `qa`, `ship`, `review`, `design-review`). If at least one matching entry exists, pass.

- **Pass:** At least one gstack skill (`browse`, `qa`, `ship`, `review`) is available in the current session
- **Fail action:** Check `/plugin marketplace list` for gstack source and install
- **Tier:** Standard — enables `/browse`, `/qa`, `/ship`, `/review`, `/design-review` and more

---

**Check 3 — obsidian plugin** | Tier: Standard

Detect by checking if `obsidian:obsidian-cli` skill is available in the current session.

Detection: Read the `system-reminder` skill list in your current session context. Search for entries prefixed with `obsidian:` (e.g., `obsidian:obsidian-cli`). If at least one matching entry exists, pass.

- **Pass:** `obsidian:obsidian-cli` skill is available in the current session
- **Fail action:** Install with `/plugin install obsidian@obsidian-skills` (marketplace: `kepano/obsidian-skills`)
- **Tier:** Standard — required for T3 vault retrieval (full-text search, inline mentions)

---

### Project Configuration (Checks 4–6)

Read CLAUDE.md before running these checks. If CLAUDE.md does not exist, checks 4–6 all fail and checks 7–19 report "cannot check — CLAUDE.md missing".

```bash
# Attempt to read CLAUDE.md from current working directory
ls CLAUDE.md 2>/dev/null && echo "found" || echo "missing"
```

**Check 4 — CLAUDE.md exists** | Tier: Critical

```bash
ls CLAUDE.md 2>/dev/null && echo "PASS" || echo "FAIL"
```

- **Pass:** `CLAUDE.md` exists in the project root (current working directory)
- **Fail action:** Create `CLAUDE.md` with project name, vault root, task prefix, and TaskNotes path fields

---

**Check 5 — CLAUDE.md required fields** | Tier: Critical

Parse CLAUDE.md for all 4 required fields. A field is "present" if it has a non-empty value with correct format.

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

- **Pass:** All 4 fields found — project name, vault root, task prefix (ending with `-`), TaskNotes path
- **Fail action:** Add missing fields to CLAUDE.md. Required: project name, vault root (path to vault directory), task prefix (ends with `-`), TaskNotes path (sibling of project docs under vault root)

---

**Check 6 — Task prefix format** | Tier: Critical

Extract task prefix from CLAUDE.md and verify it ends with `-`. Then verify the counter file path resolves.

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

- **Pass:** Task prefix ends with `-` AND counter file exists at `{tasknotes_path}/meta/{task_prefix}counter`
- **Fail action:** Verify task prefix ends with `-` (not `--`). Create counter file: `echo "1" > {tasknotes_path}/meta/{task_prefix}counter`

---

### Vault Structure (Checks 7–11)

These checks require vault root from CLAUDE.md. If CLAUDE.md is missing, report "cannot check — CLAUDE.md missing" for all.

**Check 7 — Vault directory exists** | Tier: Critical

```bash
# VAULT_ROOT extracted from CLAUDE.md
ls -d "${VAULT_ROOT}" 2>/dev/null && echo "PASS" || echo "FAIL: vault root not found at ${VAULT_ROOT}"
```

- **Pass:** Vault root path resolves to a real directory on disk
- **Fail action:** Check vault root path in CLAUDE.md. Create vault directory or correct the path.

---

**Check 8 — Vault structure** | Tier: Critical

A well-formed vault must have `_meta/`, `_Templates/`, and `TaskNotes/` subdirectories. For layout detection:
- **Standalone:** also has `00-Home.md` at vault root
- **Monorepo:** has a project docs subdirectory (e.g., `vault/Trading-Signal-AI/`)

```bash
# Required subdirectories
ls -d "${VAULT_ROOT}_meta/" 2>/dev/null && echo "_meta: OK" || echo "_meta: MISSING"
ls -d "${VAULT_ROOT}_Templates/" 2>/dev/null && echo "_Templates: OK" || echo "_Templates: MISSING"
ls -d "${VAULT_ROOT}TaskNotes/" 2>/dev/null && echo "TaskNotes: OK" || echo "TaskNotes: MISSING"

# Layout detection
ls "${VAULT_ROOT}00-Home.md" 2>/dev/null && echo "layout: standalone" || echo "layout: monorepo (or missing 00-Home.md)"
```

- **Pass:** `_meta/`, `_Templates/`, and `TaskNotes/` all exist; plus either `00-Home.md` (standalone) or a project docs subdirectory (monorepo)
- **Fail action:** Run `/wiki-setup` to initialize standard vault structure, or manually create missing directories

---

**Check 9 — Python 3.10+** | Tier: Critical

Required for index generation even at Quick tier.

```bash
python3 --version 2>/dev/null
```

Parse the version string. Extract major and minor version numbers. Require `>= 3.10`.

```bash
PYTHON_VERSION=$(python3 --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ -z "$PYTHON_VERSION" ]; then
  echo "FAIL: python3 not found"
elif [ "$MAJOR" -gt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]); then
  echo "PASS: Python $PYTHON_VERSION"
else
  echo "FAIL: Python $PYTHON_VERSION is too old (need >= 3.10)"
fi
```

- **Pass:** `python3 --version` returns `>= 3.10`
- **Fail action:** Install Python 3.10 or newer. On macOS: `brew install python@3.12`

---

**Check 10 — Index status** | Tier: Standard

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

- **Pass:** `index.md` exists
- **Warn (not fail):** `index.md` exists but pages have been modified since it was generated — report count of stale pages
- **Fail:** `index.md` does not exist
- **Fail action:** `cd {vault_root} && python3 _meta/generate-index.py`
- **Warn action:** `cd {vault_root} && python3 _meta/generate-index.py` (refresh recommended)

---

**Check 11 — Task counter** | Tier: Standard

```bash
# TASKNOTES_PATH and TASK_PREFIX from CLAUDE.md
COUNTER_FILE="${TASKNOTES_PATH}meta/${TASK_PREFIX}counter"
ls "$COUNTER_FILE" 2>/dev/null || echo "FAIL: counter file not found"

# Verify contents are an integer
COUNTER_VALUE=$(cat "$COUNTER_FILE" 2>/dev/null | tr -d '[:space:]')
echo "$COUNTER_VALUE" | grep -qE '^[0-9]+$' && echo "PASS: counter = $COUNTER_VALUE" || echo "FAIL: counter file is not an integer"
```

- **Pass:** Counter file exists at `{tasknotes_path}/meta/{task_prefix}counter` and contains a valid integer
- **Fail action:** Create counter: `mkdir -p {tasknotes_path}/meta && echo "1" > {tasknotes_path}/meta/{task_prefix}counter`

---

### Integrations (Checks 12–19)

**Check 12 — Obsidian vault plugins** | Tier: Standard

```bash
ls "${VAULT_ROOT}.obsidian/plugins/tasknotes/main.js" 2>/dev/null && echo "tasknotes: OK" || echo "tasknotes: MISSING"
ls "${VAULT_ROOT}.obsidian/plugins/obsidian-git/main.js" 2>/dev/null && echo "obsidian-git: OK" || echo "obsidian-git: MISSING"
```

- **Pass:** Both `tasknotes/main.js` and `obsidian-git/main.js` exist in `{vault_root}/.obsidian/plugins/`
- **Fail action:** Open Obsidian → Settings → Community Plugins → install "TaskNotes" and "Obsidian Git"

---

**Check 13 — TaskNotes MCP** | Tier: Standard

Config check only — not connectivity. Obsidian must be running for the endpoint to respond.

```bash
# Check .mcp.json in project root for tasknotes MCP entry
cat .mcp.json 2>/dev/null | grep -q "tasknotes" && echo "PASS: tasknotes MCP configured" || echo "FAIL: tasknotes not found in .mcp.json"
```

- **Pass:** `tasknotes` entry exists in `.mcp.json` (project root)
- **Fail action:** Add tasknotes HTTP transport to `.mcp.json` (TaskNotes v4.5+ has a built-in MCP server on its API port). Example entry:
  ```json
  "mcpServers": {
    "tasknotes": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
  ```
  Or use CLI: `claude mcp add --transport http --scope project tasknotes http://localhost:8080/mcp`

---

**Check 14 — MemPalace installed** | Tier: Full

```bash
command -v mempalace 2>/dev/null && mempalace --version 2>/dev/null && echo "PASS" || echo "FAIL: mempalace not found"
```

- **Pass:** `mempalace` CLI is on PATH
- **Fail / Available upgrade action:**
  - If `pipx` available: `pipx install "mempalace>=3.0.0,<4.0.0"`
  - If `pipx` not available: `pip install "mempalace>=3.0.0,<4.0.0"`
  - Check pipx: `command -v pipx 2>/dev/null && echo "use pipx" || echo "use pip"`
- **Unlocks:** T2 retrieval for `/wiki-query` (deep synthesis, experiential recall), history auto-index hook

---

**Check 15 — MemPalace wing indexed** | Tier: Full

This is the vault content wing (indexed by `mine-vault.sh`). The conversation history wing is separate — covered by check 16.

```bash
# Derive the wing key from current working directory
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
echo "Expected wing: $WING"

# Check if wing exists in mempalace status
mempalace status 2>/dev/null | grep -q "$WING" && echo "PASS: wing found" || echo "FAIL: wing not indexed"
```

- **Pass:** `mempalace status` shows a wing for this project
- **Fail / Available upgrade action:** Index the vault: `bash skills/shared/mine-vault.sh`
- **Requires:** Check 14 (MemPalace installed)

---

**Check 16 — History auto-index hook** | Tier: Full

Five conditions. Conditions 1–2 determine pass/fail. Conditions 3–5 are warnings (hook is
installed, but its effect is silently compromised).

Note on condition 2: Claude Code merges hook arrays from global `~/.claude/settings.json`
and project-local `.claude/settings.json`. If the hook is registered globally, it fires even
when project-local has no Stop hook. Checking project-local registration is therefore
defensive coverage rather than a strict correctness check — but it's still the cleanest way
to prove the hook is set up for this project without having to parse global settings.

1. Hook script exists at `~/.claude/hooks/ark-history-hook.sh` **(required)**
2. Hook registered as a Stop hook in project-local `.claude/settings.json` **(required — defensive)**
3. Wing-match: `mempalace status` has a wing matching the expected key for `$PWD` **(warn)**
4. Threshold-staleness: new drawers since last compile is `< 50 * 4` (not absurdly over-due) **(warn)**
5. Threshold-lock: `current_drawers == drawers_at_last_compile` AND baseline > 500 **(warn — high signal, catches "stuck compile baseline" which looks like "hook not running")**

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
  # Find the closest actual wing (substring match) for the fix hint
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

- **Pass:** Conditions 1 and 2 are true AND no warnings from 3–5
- **Warn:** Conditions 1 and 2 true, but one or more of 3–5 triggers
- **Fail / Available upgrade action:** `bash skills/claude-history-ingest/hooks/install-hook.sh`
- **Warn fixes:**
  - Wing-match: If you recently moved the project, re-run `bash skills/shared/mine-vault.sh`. If the project has a subproject wing by design (e.g., monorepo), this is cosmetic — skip.
  - Threshold-staleness: Run `/claude-history-ingest compile` manually to clear the backlog.
  - Threshold-lock: Accumulate ≥50 new drawers naturally (run more sessions) or reset baseline via `jq '."<wing>".drawers_at_last_compile = 0' ~/.mempalace/hook_state/compile_threshold.json > /tmp/t && mv /tmp/t ~/.mempalace/hook_state/compile_threshold.json`
- **Requires:** Check 14 (MemPalace installed)
- **Unlocks:** Auto-index Claude sessions into MemPalace on session exit (zero LLM tokens per session)

---

**Check 17 — NotebookLM CLI installed** | Tier: Full

```bash
command -v notebooklm 2>/dev/null && notebooklm --version 2>/dev/null && echo "PASS" || echo "FAIL: notebooklm not found"
```

- **Pass:** `notebooklm` CLI is on PATH
- **Fail / Available upgrade action:** `pipx install notebooklm-cli`
- **Unlocks:** T1 retrieval (fastest, pre-synthesized answers) + `/notebooklm-vault` skill

---

**Check 18 — NotebookLM config** | Tier: Full

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

Parse the config and verify the notebook ID field is non-empty.

- **Pass:** `.notebooklm/config.json` exists (project root or vault root) with a non-empty notebook ID
- **Fail / Available upgrade action:** Run `/notebooklm-vault` to set up NotebookLM config, or create `.notebooklm/config.json` with a valid notebook ID

---

**Check 19 — NotebookLM authenticated** | Tier: Full

```bash
notebooklm auth check --test 2>/dev/null && echo "PASS: authenticated" || echo "FAIL: auth check failed"
```

- **Pass:** `notebooklm auth check --test` exits with code 0
- **Fail / Available upgrade action:** Re-authenticate with `notebooklm auth login`, then rerun `/ark-health`
- **Note:** Auth failure is non-blocking — continue with rest of checks

---

## Workflow

### Step 1: Run All 19 Checks

Run checks in sequence. Do not abort on failure — complete all 19. Track results as you go:

```
results = {
  1: pass|fail,
  2: pass|fail,
  3: pass|fail,
  4: pass|fail,
  5: pass|fail,
  6: pass|fail,
  7: pass|fail|skip,
  8: pass|fail|skip,
  9: pass|fail,
  10: pass|fail|warn,
  11: pass|fail|skip,
  12: pass|fail|skip,
  13: pass|fail|skip,
  14: pass|fail|upgrade,
  15: pass|fail|upgrade|skip,
  16: pass|fail|warn|upgrade|skip,
  17: pass|fail|upgrade,
  18: pass|fail|upgrade|skip,
  19: pass|fail|upgrade|skip,
}
```

For checks 7–19: if CLAUDE.md was missing (check 4 = fail), record `skip` with message "cannot check — CLAUDE.md missing".

For checks 15, 16, 18, 19: if their prerequisite check failed, record `skip` with message "requires check N".

### Step 2: Classify Results

Each check gets one of four outcomes:

| Symbol | Outcome | Condition |
|--------|---------|-----------|
| `OK` | Pass | Check passed |
| `!!` | Fail | Check failed — has a fix instruction |
| `~~` | Warning | Non-blocking issue (used for check 10 staleness and check 16 hook-state drift) |
| `--` | Available upgrade | Feature not installed but optional; above user's current tier |

**Tier assignment:**

Determine the user's implicit tier from the highest tier where no Critical or Standard check returns `fail`. Warn and skip outcomes do NOT block tier classification.

- **Minimal tier:** No fail in checks 1–9, checks 10–11 skip (no vault)
- **Quick tier:** No fail in checks 1–11 (vault present, no integrations)
- **Standard tier:** No fail in checks 1–13 (TaskNotes MCP configured)
- **Full tier:** No fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Warn-returning checks (10 index staleness, 20 vault externalized) are advisory — they surface in the scorecard but don't demote the tier.

Use this tier label in the summary line.

### Step 3: Output Scorecard

Format the output exactly as shown in the Output Format section below. Then follow with a final summary line and the `/ark-onboard` prompt.

---

## Output Format

```
Ark Health Check -- {project_name}

Plugins
  OK  superpowers v{version}
  OK  obsidian v{version}
  !!  gstack -- not detected
      Unlock: /browse, /qa, /ship, /review, /design-review + more
      Check: /plugin marketplace list for gstack source

Project Configuration
  OK  CLAUDE.md exists and has required fields
  OK  Task prefix: {task_prefix} (counter at {N})

Vault Structure
  OK  Vault healthy ({N} pages, {standalone|monorepo} layout)
  ~~  Index stale ({N} pages modified since last generation)
      Refresh: cd {vault_root} && python3 _meta/generate-index.py
  OK  Python {version} available

Integrations
  OK  Obsidian vault plugins installed
  !!  TaskNotes MCP -- not in .mcp.json
      Fix: Add tasknotes HTTP transport to .mcp.json (type: http, url: http://localhost:{apiPort}/mcp)
  --  MemPalace -- not installed
      Unlock: T2 retrieval for /wiki-query (deep synthesis, experiential recall)
      Install: pipx install "mempalace>=3.0.0,<4.0.0"
  --  History hook -- not installed (requires MemPalace)
      Unlock: Auto-index Claude sessions into MemPalace on exit
      Install: bash skills/claude-history-ingest/hooks/install-hook.sh
  --  NotebookLM -- not installed
      Unlock: T1 retrieval (fastest answers) + /notebooklm-vault
      Install: pipx install notebooklm-cli

Score: {tier} tier | {N} fix, {N} warning, {N} upgrades available
Run /ark-onboard to fix or upgrade
```

**Rules for the output:**
- Always show all 4 section headers (Plugins, Project Configuration, Vault Structure, Integrations)
- Never omit a check from the output — skipped checks show as `--  {check name} -- cannot check (CLAUDE.md missing)` with `--` symbol
- For `!!` entries: always follow with an indented `Fix:` line
- For `~~` entries: always follow with an indented `Refresh:`, `Note:`, `Fix:`, or `Reset:` line (Check 16 hook-state drift uses `Fix:` or `Reset:` depending on the sub-warning)
- For `--` entries: always follow with an indented `Unlock:` line and an indented `Install:` or `Check:` line
- Summary line format: `Score: {tier} tier | {fails} fix, {warns} warning, {upgrades} upgrades available`
- Use singular (`1 fix`, not `1 fixes`) when count is 1
- Always end with `Run /ark-onboard to fix or upgrade`

## Design Decisions

- **No auto-fix.** `/ark-health` diagnoses and recommends only. All fixes go through `/ark-onboard`.
- **Always points to `/ark-onboard`** for remediation at the end of every run.
- **Index staleness is a warning, not a failure.** A stale index does not block any workflow.
- **Tier vocabulary** gives the user a name for their current setup level (Minimal / Quick / Standard / Full).
- **This skill is authoritative** for all 19 check definitions. If `/ark-onboard`'s copy of a check drifts from this file, this file is the source of truth.
- **Plugin detection is session-based**, not filesystem-based. Plugins are detected by whether their skills appear in the current session — not by inspecting `~/.claude/plugins/`.
- **Graceful degradation:** Never abort on CLAUDE.md absence. Report clearly and continue.
