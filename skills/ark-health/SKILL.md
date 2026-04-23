---
name: ark-health
description: Diagnostic check for Ark ecosystem health — plugins, CLAUDE.md, vault, integrations
---

# Ark Health Check

Run 22 diagnostic checks across the Ark ecosystem and produce a scored report with actionable fix instructions. Bash implementations for the longer checks live in `references/check-implementations.md` (load-on-demand).

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete. When CLAUDE.md is absent:

- Checks 1–3 (Plugins) run normally
- Checks 4–6 (Project Configuration) report **fail** with explanation
- Checks 7–20 report "cannot check — CLAUDE.md missing" instead of failing silently (Checks 21 and 22 are exempt — run unconditionally)

Never abort early. Run all 22 checks regardless of earlier failures.

## Required CLAUDE.md fields

Four user-provided fields (see plugin CLAUDE.md § Context-Discovery Pattern for path-layout detail):

- **Project name** — any string
- **Vault root** — path ending with `/`
- **Task prefix** — ends with `-` (e.g. `ArkSignal-`)
- **TaskNotes path** — sibling of project docs under vault root (never nested)

Derived: counter file = `{tasknotes_path}/meta/{task_prefix}counter`.

---

## Diagnostic Checklist

### Plugins (Checks 1–3)

Detection is session-capability: read the `system-reminder` skill list in the current session and match for the listed skill names. Plugin detection is session-based, never filesystem-based.

**Check 1 — superpowers plugin** | Tier: Critical

- Detect: session-list contains any `superpowers:*` entry (e.g., `superpowers:brainstorming`, `superpowers:writing-plans`)
- Pass: ≥1 match
- Fail action: `/plugin install superpowers@claude-plugins-official` (marketplace: `anthropics/claude-plugins-official`)
- Why Critical: brainstorming, TDD, writing-plans, and code-review patterns depend on this

**Check 2 — gstack plugin** | Tier: Standard

- Detect: session-list contains any of `browse`, `qa`, `ship`, `review`, `design-review`
- Pass: ≥1 match
- Fail action: check `/plugin marketplace list` for gstack source and install
- Unlocks: `/browse`, `/qa`, `/ship`, `/review`, `/design-review`, and more

**Check 3 — obsidian plugin** | Tier: Standard

- Detect: session-list contains any `obsidian:*` entry (e.g., `obsidian:obsidian-cli`)
- Pass: ≥1 match
- Fail action: `/plugin install obsidian@obsidian-skills` (marketplace: `kepano/obsidian-skills`)
- Unlocks: T3 vault retrieval (full-text search, inline mentions)

---

### Project Configuration (Checks 4–6)

Read CLAUDE.md first. If CLAUDE.md does not exist, checks 4–6 all fail and checks 7–20 report "cannot check — CLAUDE.md missing". Checks 21 and 22 are exempt.

```bash
ls CLAUDE.md 2>/dev/null && echo "found" || echo "missing"
```

**Check 4 — CLAUDE.md exists** | Tier: Critical

- Pass: `CLAUDE.md` exists in the project root
- Fail action: create `CLAUDE.md` with the four required fields above

**Check 5 — CLAUDE.md required fields** | Tier: Critical

- Pass: all 4 required fields present with correct format
- Fail action: add missing fields (project name, vault root, task prefix ending with `-`, TaskNotes path)
- Bash: `references/check-implementations.md` § Check 5

**Check 6 — Task prefix format** | Tier: Critical

- Pass: task prefix ends with `-` AND counter file exists at `{tasknotes_path}/meta/{task_prefix}counter`
- Fail action: verify prefix ends with `-` (not `--`); create counter: `echo "1" > {tasknotes_path}/meta/{task_prefix}counter`
- Bash: `references/check-implementations.md` § Check 6

---

### Vault Structure (Checks 7–11)

These checks require vault root from CLAUDE.md. If CLAUDE.md is missing, report "cannot check — CLAUDE.md missing" for all five.

**Check 7 — Vault directory exists** | Tier: Critical

```bash
ls -d "${VAULT_ROOT}" 2>/dev/null && echo "PASS" || echo "FAIL: vault root not found at ${VAULT_ROOT}"
```

- Pass: vault root path resolves to a real directory on disk
- Fail action: check path in CLAUDE.md; create vault directory or correct the path

**Check 8 — Vault structure** | Tier: Critical

- Pass: `_meta/`, `_Templates/`, and `TaskNotes/` all exist; plus `00-Home.md` (standalone layout) OR a project docs subdirectory (monorepo layout)
- Fail action: `/wiki-setup` to initialize, or manually create missing directories
- Bash: `references/check-implementations.md` § Check 8

**Check 9 — Python 3.10+** | Tier: Critical

Required for index generation even at Quick tier.

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

- Pass: `python3 --version` ≥ 3.10
- Fail action: install Python 3.10+ (macOS: `brew install python@3.12`)

**Check 10 — Index status** | Tier: Standard

Staleness is a **warning**, not a failure.

- Pass: `index.md` exists
- Warn: `index.md` exists but pages have been modified since generation — report count of stale pages
- Fail: `index.md` does not exist
- Refresh / Fail action: `cd {vault_root} && python3 _meta/generate-index.py`
- Bash: `references/check-implementations.md` § Check 10

**Check 11 — Task counter** | Tier: Standard

- Pass: counter file exists at `{tasknotes_path}/meta/{task_prefix}counter` and contains a valid integer
- Fail action: `mkdir -p {tasknotes_path}/meta && echo "1" > {counter_file}`
- Bash: `references/check-implementations.md` § Check 11

---

### Integrations (Checks 12–20)

**Check 12 — Obsidian vault plugins** | Tier: Standard

```bash
ls "${VAULT_ROOT}.obsidian/plugins/tasknotes/main.js" 2>/dev/null && echo "tasknotes: OK" || echo "tasknotes: MISSING"
ls "${VAULT_ROOT}.obsidian/plugins/obsidian-git/main.js" 2>/dev/null && echo "obsidian-git: OK" || echo "obsidian-git: MISSING"
```

- Pass: both `tasknotes/main.js` and `obsidian-git/main.js` exist in `{vault_root}/.obsidian/plugins/`
- Fail action: Obsidian → Settings → Community Plugins → install "TaskNotes" and "Obsidian Git"

**Check 13 — TaskNotes MCP** | Tier: Standard

Config check only — does not verify connectivity (Obsidian must be running for the endpoint to respond).

```bash
cat .mcp.json 2>/dev/null | grep -q "tasknotes" && echo "PASS: tasknotes MCP configured" || echo "FAIL: tasknotes not found in .mcp.json"
```

- Pass: `tasknotes` entry exists in `.mcp.json` (project root)
- Fail action: add HTTP transport to `.mcp.json` (TaskNotes v4.5+ ships a built-in MCP server on its API port):
  ```json
  "mcpServers": {
    "tasknotes": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
  ```
  Or CLI: `claude mcp add --transport http --scope project tasknotes http://localhost:8080/mcp`

**Check 14 — MemPalace installed** | Tier: Full | Non-blocking upgrade

```bash
command -v mempalace 2>/dev/null && mempalace --version 2>/dev/null && echo "PASS" || echo "FAIL: mempalace not found"
```

- Pass: `mempalace` CLI on PATH
- Upgrade action: prefer `pipx install "mempalace>=3.0.0,<4.0.0"`; fallback `pip install` if `pipx` unavailable
- Unlocks: T2 retrieval for `/wiki-query` (deep synthesis, experiential recall) + history auto-index hook

**Check 15 — MemPalace wing indexed** | Tier: Full | Requires Check 14

Covers the vault content wing (indexed by `mine-vault.sh`). The conversation history wing is separate — see Check 16.

```bash
WING=$(echo "$PWD" | sed 's|[/.]|-|g')
echo "Expected wing: $WING"
mempalace status 2>/dev/null | grep -q "$WING" && echo "PASS: wing found" || echo "FAIL: wing not indexed"
```

- Pass: `mempalace status` shows a wing for this project
- Fail action: `bash skills/shared/mine-vault.sh`

**Check 16 — History auto-index hook** | Tier: Full | Requires Check 14

Five sub-conditions. Conditions 1–2 determine pass/fail; conditions 3–5 are warnings (hook installed, but effect silently compromised).

- Condition 1 (required): hook script at `~/.claude/hooks/ark-history-hook.sh`
- Condition 2 (required — defensive): hook registered as a Stop hook in `.claude/settings.json` (project-local; global registration also works but is harder to verify)
- Condition 3 (warn): wing-match — `mempalace status` has a wing matching the expected key for `$PWD`
- Condition 4 (warn): threshold-staleness — fewer than `50 * 4 = 200` new drawers since last compile
- Condition 5 (warn): threshold-lock — `current_drawers == drawers_at_last_compile` AND baseline > 500 (high signal: "stuck compile baseline" looks like "hook not running")
- Pass: conditions 1 and 2 true AND no warnings from 3–5
- Warn: conditions 1 and 2 true, but one or more of 3–5 triggers
- Fail action: `bash skills/claude-history-ingest/hooks/install-hook.sh`
- Unlocks: auto-index Claude sessions into MemPalace on session exit (zero LLM tokens per session)
- Bash + warn fixes: `references/check-implementations.md` § Check 16

**Check 17 — NotebookLM CLI installed** | Tier: Full | Non-blocking upgrade

```bash
command -v notebooklm 2>/dev/null && notebooklm --version 2>/dev/null && echo "PASS" || echo "FAIL: notebooklm not found"
```

- Pass: `notebooklm` CLI on PATH
- Upgrade action: `pipx install notebooklm-cli`
- Unlocks: T1 retrieval (fastest, pre-synthesized answers) + `/notebooklm-vault` skill

**Check 18 — NotebookLM config** | Tier: Full | Requires Check 17

- Pass: `.notebooklm/config.json` (project root or vault root) with non-empty notebook ID
- Fail action: run `/notebooklm-vault` to set up, or create `.notebooklm/config.json` with a valid notebook ID
- Bash: `references/check-implementations.md` § Check 18

**Check 19 — NotebookLM authenticated** | Tier: Full | Non-blocking

```bash
notebooklm auth check --test 2>/dev/null && echo "PASS: authenticated" || echo "FAIL: auth check failed"
```

- Pass: `notebooklm auth check --test` exits 0
- Fail action: `notebooklm auth login`, then rerun `/ark-health`

**Check 20 — Vault externalized** | Tier: Standard | Warn-only (never fails)

Detection inputs: `vault` artifact (symlink / real dir / missing), `scripts/setup-vault-symlink.sh` (present / absent), CLAUDE.md `Vault layout` opt-out row (present / absent).

- Pass conditions (any): (a) symlink with target resolving to script `VAULT_TARGET`; (b) real directory + opt-out present; (c) missing + opt-out present + no script
- Warn conditions: real dir without opt-out; broken symlink; symlink target drift; symlink without canonical script; missing with script present; missing without script or opt-out
- Never fails. Each warn points to `/ark-onboard` Repair or Greenfield.
- Full state matrix + detection bash: `references/check-implementations.md` § Check 20

---

### Plugin Versioning (Checks 21–22)

**Check 21 — OMC plugin** | Tier: Standard | Upgrade-style (never fails)

Exempt from CLAUDE.md-missing skip rule (OMC presence is a CLI/cache-dir property). Detection mirrors the canonical `HAS_OMC` probe in `skills/ark-workflow/SKILL.md:54-61` — detect first, then apply the `ARK_SKIP_OMC=true` override (downstream emergency rollback per `skills/ark-workflow/references/omc-integration.md` § Section 3).

```bash
if command -v omc >/dev/null 2>&1 || [ -d "$HOME/.claude/plugins/cache/omc" ]; then
  HAS_OMC=true
else
  HAS_OMC=false
fi
[ "$ARK_SKIP_OMC" = "true" ] && HAS_OMC=false

if [ "$HAS_OMC" = "true" ]; then
  echo "PASS: OMC detected"
elif [ "$ARK_SKIP_OMC" = "true" ]; then
  echo "SKIP: ARK_SKIP_OMC=true (user-suppressed)"
else
  echo "UPGRADE: OMC not installed"
fi
```

- Pass: `omc` on PATH OR `~/.claude/plugins/cache/omc` exists, AND `ARK_SKIP_OMC` is not `true`
- Upgrade action: install at https://github.com/anthropics/oh-my-claudecode — unlocks `/ark-workflow` Path B (`/autopilot`, `/ralph`, `/ultrawork`, `/team`)
- Skip: `ARK_SKIP_OMC=true` → render as `--` with note `OMC suppressed (ARK_SKIP_OMC=true)`
- Tier: Standard — absence never blocks any tier classification (mirrors Checks 14/17/18)

**Check 22 — ark-skills plugin version current** | Tier: Standard | Warn-only (never fails)

Exempt from CLAUDE.md-missing skip rule. Compares `.ark/plugin-version` against `$ARK_SKILLS_ROOT/VERSION` and asserts `.ark/` is not gitignored.

- Pass: `.ark/plugin-version` exists and matches `$ARK_SKILLS_ROOT/VERSION`
- Warn (version drift): surface `upgrade available: run /ark-update` (project vs current versions)
- Warn (not recorded): `.ark/plugin-version` absent → `run /ark-update to record current version`
- Warn (gitignored): `.ark/` is gitignored → `remove pattern and commit before running /ark-update`
- Bash: `references/check-implementations.md` § Check 22

---

## Workflow

1. **Run all 22 checks in sequence.** Do not abort on failure.
   - Checks 7–20: if Check 4 failed (CLAUDE.md missing), record `skip` with message "cannot check — CLAUDE.md missing". Checks 21, 22 are exempt.
   - Checks 15, 16, 18, 19: if the prerequisite failed, record `skip` with message "requires check N".

2. **Classify each result** with one of four outcomes:

| Symbol | Outcome | Condition |
|--------|---------|-----------|
| `OK` | Pass | Check passed |
| `!!` | Fail | Check failed — has a fix instruction |
| `~~` | Warning | Non-blocking (Check 10 staleness, Check 16 hook-state drift, Check 20, Check 22) |
| `--` | Available upgrade | Feature not installed, above current tier |

3. **Assign tier** from the highest level where no Critical or Standard check returns `fail`. Warn, skip, and upgrade outcomes never demote tier.

- **Minimal:** no fail in checks 1–9; checks 10–11 skip (no vault)
- **Quick:** no fail in checks 1–11 (vault present, no integrations)
- **Standard:** no fail in checks 1–13 (TaskNotes MCP configured)
- **Full:** no fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Check 21 (OMC plugin) is tier-agnostic. Warn-only checks (10, 20, 22) and upgrade-only checks (14, 17, 18, 21) are advisory — they surface in the scorecard but never block tier classification.

4. **Emit scorecard** per the Output Format below. Always end with `Run /ark-onboard to fix or upgrade`.

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
  OK  Vault externalized (symlink -> $HOME/.superset/vaults/{project})

Integrations
  OK  Obsidian vault plugins installed
  !!  TaskNotes MCP -- not in .mcp.json
      Fix: Add tasknotes HTTP transport to .mcp.json
  --  MemPalace -- not installed
      Unlock: T2 retrieval for /wiki-query
      Install: pipx install "mempalace>=3.0.0,<4.0.0"
  --  OMC plugin -- not installed
      Unlock: /ark-workflow Path B (autonomous execution)
      Install: https://github.com/anthropics/oh-my-claudecode

Score: {tier} tier | {N} fix, {N} warning, {N} upgrades available
Run /ark-onboard to fix or upgrade
```

**Rules:**

- Always show all 4 section headers (Plugins, Project Configuration, Vault Structure, Integrations)
- Never omit a check — skipped checks render as `--  {name} -- cannot check (CLAUDE.md missing)` with `--` symbol
- `!!` → indented `Fix:` line
- `~~` → indented `Refresh:` / `Fix:` / `Reset:` line (Check 16 hook drift uses `Fix:` or `Reset:` per sub-warning)
- `--` → indented `Unlock:` + `Install:` or `Check:` line
- Singular/plural: `1 fix`, not `1 fixes`
- Always end with: `Run /ark-onboard to fix or upgrade`

---

## Design Decisions

- **No auto-fix.** `/ark-health` diagnoses and recommends only. All fixes go through `/ark-onboard`.
- **Authoritative check definitions.** This skill is the source of truth for all 22 check definitions. If `/ark-onboard`'s copy drifts from here, this file wins.
- **Session-based plugin detection.** Plugins are detected by whether their skills appear in the current session — never by inspecting `~/.claude/plugins/`.
- **Graceful degradation.** Never abort on CLAUDE.md absence. Report clearly and continue.
- **Index staleness is a warning, not a failure.** A stale index does not block any workflow.
- **Tier vocabulary** gives the user a name for their current setup level (Minimal / Quick / Standard / Full).
- **Bash implementations relocated.** Longer detection bash lives in `references/check-implementations.md` (load-on-demand). This reduces the at-invocation token footprint without changing check semantics.
