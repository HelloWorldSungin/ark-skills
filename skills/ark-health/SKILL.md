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

**Check 14a — MemPalace plugin installed (user scope)** | Tier: Full | Returns: `warn`

The Claude Code plugin wires the MemPalace MCP server into every session, giving the LLM native access to 19 memory tools for T2 reads without a CLI round-trip.

```bash
# Block-aware parse: `claude plugin list` emits one block per plugin, each
# starting with "  ❯ <name>@<marketplace>" and continuing until the next "  ❯ ".
# We must scope Version/Scope/Status checks to the mempalace block — scanning
# the whole output as one stream false-PASSes when a DIFFERENT plugin is the
# user-scope/enabled one.
claude plugin list 2>/dev/null | awk '
  /^  ❯ / {in_target = ($0 ~ /^  ❯ mempalace@/); next}
  in_target && /Scope: user/ {scope=1}
  in_target && /Status: ✔ enabled/ {enabled=1}
  END {exit !(scope && enabled)}
' && echo "PASS" || echo "WARN: plugin not installed at user scope"
```

- **Pass:** `mempalace` plugin present at user scope and enabled.
- **Warn / Available upgrade action:**
  ```bash
  # One-time shim — plugin declares command: mempalace-mcp but pip ships it as a module
  cat > ~/.local/bin/mempalace-mcp <<'EOF'
  #!/bin/bash
  exec "$(pipx environment --value PIPX_LOCAL_VENVS)/mempalace/bin/python" -m mempalace.mcp_server "$@"
  EOF
  chmod +x ~/.local/bin/mempalace-mcp
  claude plugin marketplace add milla-jovovich/mempalace
  claude plugin install --scope user mempalace@mempalace
  ```
- **Requires:** Check 14 (pip package) — plugin depends on the CLI for its `hook` subcommand.
- **Unlocks:** Auto-MCP server on every Claude Code session (19 tools for T2 reads), `/mempalace:*` slash commands, auto-save Stop/PreCompact hooks.

**Check 14b — MemPalace MCP server responds** | Tier: Full | Returns: `warn`

> **Note:** this probe verifies that Claude Code has the plugin's MCP wired up AND the shim actually starts. It does NOT prove the *current interactive session* has the `mcp__mempalace__*` tools loaded — that's only knowable from inside the session. If this PASSes but the tools aren't showing, restart Claude Code.

```bash
# Probe 1: Claude Code's `claude mcp list` emits lines like
#   "plugin:mempalace:mempalace: mempalace-mcp  - ✓ Connected"
# when the plugin registered its MCP config and the shim is reachable.
if claude mcp list 2>/dev/null | grep -qE '^plugin:mempalace:.*- *✓ Connected'; then
  echo "PASS"
elif command -v mempalace-mcp >/dev/null 2>&1; then
  # Probe 2 (fallback): shim exists — do a stdio `initialize` handshake.
  # Portable timeout: `timeout`/`gtimeout` aren't on stock macOS, so use perl
  # (universally available) which sets an alarm before exec-ing the target.
  HANDSHAKE=$(
    echo '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"health","version":"0"}},"id":1}' \
      | perl -e 'alarm 5; exec @ARGV' mempalace-mcp 2>/dev/null
  )
  if echo "$HANDSHAKE" | grep -q '"protocolVersion"'; then
    echo "PASS"
  else
    echo "WARN: shim exists but MCP initialize handshake failed"
  fi
else
  echo "WARN: MCP not reachable — plugin not wired and no shim on PATH"
fi
```

- **Pass:** Plugin-declared MCP server is listed as Connected in `claude mcp list` OR the shim responds to `initialize` within 5s.
- **Warn paths:**
  - `claude mcp list` doesn't show mempalace → plugin not registered; re-run Check 14a upgrade.
  - Shim exists but handshake fails → shim points at a broken venv; re-run `/ark-onboard` Step 13 to rebuild on Python 3.13.
  - Neither works → nothing to restart; run the full Step 13/13b flow.
- **Requires:** Check 14a.
- **Unlocks:** T2 reads via `mcp__mempalace__*` tools in a restarted Claude Code session.

**Check 14c — MemPalace hook state (informational)** | Tier: Full | Returns: `pass` (both states)

> mempalace 3.3.2 ships [#1023](https://github.com/MemPalace/mempalace/pull/1023) (PID-file guard on the plugin's auto-ingest hook) and [#784](https://github.com/MemPalace/mempalace/pull/784) (per-source-file `mine_lock`), so the plugin's own Stop/PreCompact hooks are meaningfully safer than they were initially. Neutralizing them is a defense-in-depth choice, not a corruption-prevention requirement. Revisit retiring this check entirely once upstream [#976](https://github.com/MemPalace/mempalace/pull/976) / [#991](https://github.com/MemPalace/mempalace/pull/991) / [#1062](https://github.com/MemPalace/mempalace/pull/1062) land.

```bash
# JSON-aware: check `.hooks.Stop` and `.hooks.PreCompact` specifically.
# A raw grep would false-warn on any hooks.json that mentions those strings
# outside the `.hooks` path (e.g., in a description), and it tells us nothing
# about whether the hooks are actually *active* (non-empty array).
ACTIVE=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  HAS_ACTIVE_HOOK=$(python3 - "$f" 2>/dev/null <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    h = d.get("hooks", {}) or {}
    active = bool(h.get("Stop")) or bool(h.get("PreCompact"))
    print("1" if active else "0")
except Exception:
    print("0")
PY
)
  [ "$HAS_ACTIVE_HOOK" = "1" ] && ACTIVE="$ACTIVE $f"
done < <(find "$HOME/.claude/plugins/cache/mempalace/mempalace" -name hooks.json 2>/dev/null)

if [ -z "$ACTIVE" ]; then
  echo "PASS: mempalace hooks neutralized (defense-in-depth)"
else
  echo "PASS: mempalace hooks active (plugin auto-save enabled — relying on #1023 + #784 serialization)"
fi
```

- **Pass — state A (hooks neutralized):** No cached `hooks.json` has `.hooks.Stop` or `.hooks.PreCompact`. Auto-save via plugin is off; the LLM must explicitly call `mempalace_add_drawer` / `diary_write` to save memories.
- **Pass — state B (hooks active):** Plugin auto-save is enabled, relying on mempalace 3.3.2's #1023 PID guard + #784 per-file locks. Cross-wing mine races are addressed at the ark-skills layer by the palace-global mutex in `skills/claude-history-ingest/hooks/ark-history-hook.sh`, not by this plugin.
- **When to prefer state A:** palace past ~30k drawers, frequent multi-session workflows, or recent corruption recovery.
- **When to prefer state B:** smaller palace, fewer parallel sessions, you want auto-save convenience.
- **Neutralize command** (B → A):
  ```bash
  for f in $(find ~/.claude/plugins/cache/mempalace/mempalace -name hooks.json); do
    [ -f "$f.pre-1092-disable" ] || cp "$f" "$f.pre-1092-disable"
    python3 -c "import json,sys; p=sys.argv[1]; d=json.load(open(p)); d['hooks']={}; d['description']='DISABLED defense-in-depth for #1092/#1109'; json.dump(d, open(p,'w'), indent=2)" "$f"
  done
  ```
- **Un-neutralize command** (A → B):
  ```bash
  for backup in $(find ~/.claude/plugins/cache/mempalace/mempalace -name 'hooks.json.pre-1092-disable'); do
    mv "$backup" "${backup%.pre-1092-disable}"
  done
  ```
- **Requires:** Check 14a (plugin installed).

**Check 14d — MemPalace palace read sanity** | Tier: Full | Returns: `warn`

> Exercises the HNSW read path via a real `mempalace_search` through the shim. If the palace read crashes, check for HNSW/SQLite drift (the corruption pattern in [#1092](https://github.com/MemPalace/mempalace/issues/1092)) and offer the `quarantine_stale_hnsw()` recovery.

```bash
if ! command -v mempalace-mcp >/dev/null 2>&1; then
  echo "SKIP: mempalace-mcp shim not on PATH (check 14a upgrade action)"
else
  PROBE_OUT=$(
    printf '%s\n%s\n%s\n' \
      '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"health","version":"0"}},"id":1}' \
      '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
      '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"mempalace_search","arguments":{"query":"health probe","limit":1}},"id":2}' \
      | perl -e 'alarm 20; exec @ARGV' mempalace-mcp 2>/dev/null
  )

  # MCP wraps tool output as escaped JSON inside content[].text, so the sentinel
  # "total_before_filter" appears as \"total_before_filter\". Match without quote
  # anchors to catch both forms.
  if echo "$PROBE_OUT" | grep -q 'total_before_filter'; then
    echo "PASS: palace read path healthy"
  else
    PALACE="$HOME/.mempalace/palace"
    SQ_AGE=$(stat -f %m "$PALACE/chroma.sqlite3" 2>/dev/null)
    DRIFT_SEG=""
    if [ -n "$SQ_AGE" ]; then
      for seg in "$PALACE"/*-*-*-*-*; do
        [ -f "$seg/data_level0.bin" ] || continue
        SEG_AGE=$(stat -f %m "$seg/data_level0.bin" 2>/dev/null)
        [ -z "$SEG_AGE" ] && continue
        DRIFT=$((SQ_AGE - SEG_AGE))
        [ "$DRIFT" -gt 3600 ] && DRIFT_SEG="$seg (${DRIFT}s drift)"
      done
    fi
    if [ -n "$DRIFT_SEG" ]; then
      echo "WARN: palace read crashed + HNSW drift detected at $DRIFT_SEG — run quarantine_stale_hnsw (see below)"
    else
      echo "WARN: palace read crashed with no obvious drift — inspect /tmp/mempalace-mcp-last.log"
    fi
  fi
fi
```

- **Pass:** Shim's `mempalace_search` returns a valid JSON-RPC response with `"total_before_filter"`.
- **Warn (drift detected):** HNSW segment's `data_level0.bin` is more than 1 hour older than `chroma.sqlite3` — matches the [#1000](https://github.com/MemPalace/mempalace/pull/1000) drift signature. Recovery:
  ```bash
  $(pipx environment --value PIPX_LOCAL_VENVS)/mempalace/bin/python -c "
  from mempalace.backends.chroma import quarantine_stale_hnsw
  renamed = quarantine_stale_hnsw('$HOME/.mempalace/palace')
  print('Quarantined segments:', renamed)
  "
  # Then restart Claude Code. Plugin MCP server reopens, chromadb writes a fresh segment
  # from chroma.sqlite3. The quarantined dir is renamed to `<uuid>.drift-YYYYMMDD-HHMMSS`
  # — not deleted — so you can recover if the heuristic misfires.
  ```
- **Warn (crashed, no drift):** HNSW corruption without drift signature — more severe. Options: (a) `mempalace repair`, (b) full nuke + re-mine (lossy).
- **Requires:** Check 14a (plugin), Check 14b (MCP server responds).
- **Self-heal opportunity:** when upstream [#1062](https://github.com/MemPalace/mempalace/pull/1062) lands (wires `quarantine_stale_hnsw()` automatically on MCP startup), this check can be retired.

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

**Check 16b — History hook content drift** | Tier: Full | Returns: `warn` | Requires Check 16

Detects when the installed copy at `~/.claude/hooks/ark-history-hook.sh` diverges from the plugin's current version — for example, after a plugin upgrade that added the palace-global cross-wing mutex (v1.21.1). The user must re-run `install-hook.sh` to pick up the new script; a version-only plugin upgrade doesn't touch the already-installed copy.

```bash
INSTALLED="$HOME/.claude/hooks/ark-history-hook.sh"
PLUGIN_COPY=""

# Find the plugin's current copy — prefer the installed plugin cache,
# fall back to CWD (dev/test mode on the ark-skills repo itself).
for candidate in \
  "$HOME/.claude/plugins/cache/ark-skills/ark-skills"/*/skills/claude-history-ingest/hooks/ark-history-hook.sh \
  "$HOME/.claude/plugins/cache/ark-skills/skills/claude-history-ingest/hooks/ark-history-hook.sh" \
  "$(pwd)/skills/claude-history-ingest/hooks/ark-history-hook.sh"; do
  if [ -f "$candidate" ]; then
    PLUGIN_COPY="$candidate"
    break
  fi
done

if [ ! -f "$INSTALLED" ]; then
  echo "SKIP: hook not installed (see Check 16)"
elif [ -z "$PLUGIN_COPY" ]; then
  echo "SKIP: cannot locate plugin's reference copy"
elif cmp -s "$INSTALLED" "$PLUGIN_COPY"; then
  echo "PASS: installed hook matches plugin's current version"
else
  echo "WARN: installed hook drifts from plugin copy — re-install to pick up latest"
fi
```

- **Pass:** `cmp -s` reports installed file is byte-identical to the plugin's current copy.
- **Skip:** Check 16 failed (nothing installed) OR plugin's reference copy can't be located (dev environments where neither the cache path nor CWD has it).
- **Warn:** Files differ. Re-install: `bash skills/claude-history-ingest/hooks/install-hook.sh`.
- **Why this matters:** plugin upgrades don't overwrite `~/.claude/hooks/*`. A user still running a v1.20.x copy after upgrading the plugin to v1.21.1 is missing the cross-wing mutex and remains exposed to the HNSW write race that the release closes.
- **Requires:** Check 16 (hook installed).

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
   - Checks 14b, 14c, 14d: if Check 14a failed, record `skip` with message "requires MemPalace plugin (check 14a)".
   - Check 16b: if Check 16 failed (hook not installed), record `skip` with message "requires check 16".
   - Checks 15, 16, 18, 19: if the prerequisite failed, record `skip` with message "requires check N".

2. **Classify each result** with one of four outcomes:

| Symbol | Outcome | Condition |
|--------|---------|-----------|
| `OK` | Pass | Check passed |
| `!!` | Fail | Check failed — has a fix instruction |
| `~~` | Warning | Non-blocking (Check 10 staleness, Check 14a/14b/14d MemPalace, Check 16 hook-state drift, Check 16b hook content drift, Check 20, Check 22) |
| `--` | Available upgrade | Feature not installed, above current tier |
| `>>` | Informational | State display only (Check 14c MemPalace hook state — always passes) |

3. **Assign tier** from the highest level where no Critical or Standard check returns `fail`. Warn, skip, and upgrade outcomes never demote tier.

- **Minimal:** no fail in checks 1–9; checks 10–11 skip (no vault)
- **Quick:** no fail in checks 1–11 (vault present, no integrations)
- **Standard:** no fail in checks 1–13 (TaskNotes MCP configured)
- **Full:** no fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Check 21 (OMC plugin) is tier-agnostic. Warn-returning checks (10 index staleness, 14a MemPalace plugin, 14b MemPalace MCP reachable, 14d MemPalace palace read sanity, 16b history hook content drift, 20 vault externalized, 22 plugin version) are advisory — they surface in the scorecard but never block tier classification. Upgrade-returning checks (14 MemPalace, 17 NotebookLM CLI, 18 NotebookLM config, 21 OMC plugin) are also non-blocking. Informational checks (14c MemPalace hook state) always return `pass` and exist purely to surface state on the scorecard.

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
  ~~  MemPalace plugin -- not installed (user scope)
      Unlock: Auto-MCP server on all Claude Code sessions (19 read tools for T2)
      Install: claude plugin marketplace add milla-jovovich/mempalace && claude plugin install --scope user mempalace@mempalace
      Note: requires the `mempalace-mcp` shim — see check 14a for the one-liner
  ~~  MemPalace MCP -- not reachable this session
      Fix: restart Claude Code to pick up the plugin's MCP server, or verify the shim at ~/.local/bin/mempalace-mcp
  >>  MemPalace hooks -- active (plugin auto-save on, relying on #1023 + #784)
      Optional: neutralize for defense-in-depth on large palaces — see check 14c
  >>  MemPalace hooks -- neutralized (defense-in-depth, auto-save off)
      Revisit: consider re-enabling after 2-week soak on 3.3.2 — see check 14c
  ~~  MemPalace palace read -- crashed + HNSW drift detected
      Fix: run quarantine_stale_hnsw() one-liner in check 14d; then restart Claude Code
      Upstream: MemPalace #1062 (self-heal on MCP startup; retire check 14d when merged)
  ~~  History hook -- installed copy drifts from plugin's current version
      Fix: bash skills/claude-history-ingest/hooks/install-hook.sh to re-install
      Note: plugin upgrades don't overwrite ~/.claude/hooks/; re-run after every bump
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
- `>>` → state-display only; indented `Optional:`, `Revisit:`, or `Note:` line (Check 14c MemPalace hook state)
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
