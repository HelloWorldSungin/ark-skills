---
name: ark-health
description: Diagnostic check for the ark-skills v2 invariants — routing-destination ecosystems, the 6-skill roster, OKF conventions, GitHub-Issues conventions, and NotebookLM recall
---

# Ark Health Check

Run the v2 invariant checks across the Ark ecosystem and produce a scored report with actionable fix instructions. This skill diagnoses and recommends only — all fixes go through `/ark-onboard`.

ark-skills v2 is two co-equal cores: a **workflow consultant** (`/ark-consult`) that routes each task to one of four execution ecosystems, and a **conventions layer** (`/ark-onboard`, `/ark-health`, `/ark-update`, `/vault`, `/notebooklm-vault`) that converges projects onto OKF knowledge bundles + GitHub-Issues task management. The checks below verify both cores are healthy.

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete. When CLAUDE.md is absent:

- Ecosystem checks (1–4) and Repo & Skills checks (5–6) run normally
- OKF / GitHub / NotebookLM checks that need the vault root report "cannot check — CLAUDE.md missing" instead of failing silently

Never abort early. Run all checks regardless of earlier failures.

## Required CLAUDE.md fields (v2)

- **Project name** — any string (header or table)
- **Vault root** — path to the OKF bundle (e.g. `vault/`)

Task tracking is GitHub Issues (no task-prefix / counter fields — those were retired with TaskNotes).

---

## Diagnostic Checklist

### Ecosystems — the consultant's routing destinations (Checks 1–4)

Detection is session-capability: read the `system-reminder` skill list in the current session and match for the listed skill names. Never inspect `~/.claude/plugins/` for plugin presence.

**Check 1 — superpowers plugin** | Tier: Critical
- Detect: session-list contains any `superpowers:*` entry (e.g. `superpowers:brainstorming`, `superpowers:systematic-debugging`)
- Pass: ≥1 match
- Fail action: `/plugin install superpowers@claude-plugins-official` (marketplace: `anthropics/claude-plugins-official`)
- Why Critical: it is a primary routing destination (hard debugging, TDD, refactors, plans)

**Check 2 — gstack plugin** | Tier: Standard
- Detect: session-list contains any of `browse`, `qa`, `ship`, `review`, `design-review`
- Pass: ≥1 match
- Fail action: run `/ark-onboard` (installs gstack for claude + codex)
- Unlocks: gstack routing (spec/ship/investigate/design/docs)

**Check 3 — mattpocock skills installed** | Tier: Standard
- Detect (filesystem — these skills declare `disable-model-invocation: true`, so they never appear as ambient session triggers):
  req=0; for s in to-tickets setup-matt-pocock-skills; do [ -d "$HOME/.claude/skills/$s" ] && req=$((req+1)); done
  opt=0; for s in to-spec triage implement; do [ -d "$HOME/.claude/skills/$s" ] && opt=$((opt+1)); done
  { [ "$req" -eq 2 ] && [ "$opt" -ge 2 ]; } && echo "PASS: to-tickets+setup present, $opt/3 optional" || echo "FAIL: req=$req/2 opt=$opt/3"
- Pass: `to-tickets` + `setup-matt-pocock-skills` present, plus ≥2 of `to-spec`/`triage`/`implement`
- Fail action: `npx skills@latest add mattpocock/skills`, then `/setup-matt-pocock-skills`
- Unlocks: `/to-tickets` + `/triage` issue machinery and mattpocock as a routing destination

**Check 4 — oh-my-claudecode (OMC)** | Tier: Standard | Upgrade-style (never fails)
- Detect: `command -v omc` OR `~/.claude/plugins/cache/omc` exists; `ARK_SKIP_OMC=true` overrides to skip
- Pass: OMC present
- Upgrade action: install at https://github.com/anthropics/oh-my-claudecode — unlocks OMC routing (autopilot / ultrawork / team / autoresearch)

---

### Repo & Skills (Checks 5–6)

**Check 5 — exactly 6 skills** | Tier: Critical
```bash
n=$(find skills -mindepth 1 -maxdepth 1 -type d ! -name shared | wc -l | tr -d ' ')
want="ark-consult ark-health ark-onboard ark-update notebooklm-vault vault"
got=$(find skills -mindepth 1 -maxdepth 1 -type d ! -name shared -exec basename {} \; | sort | tr '\n' ' ')
[ "$n" = "6" ] && echo "PASS: 6 skills ($got)" || echo "FAIL: $n skill dirs — expected 6: $want"
```
- Pass: exactly 6 skill directories under `skills/` (`ark-consult`, `ark-health`, `ark-onboard`, `ark-update`, `notebooklm-vault`, `vault`), plus `shared/` + `AGENTS.md`
- Fail action: a v1 skill lingered through the delete phase, or a new one was added — reconcile against the roster

**Check 6 — plugin manifest freshness** | Tier: Standard | Warn-only
```bash
rg -q "consultant" .claude-plugin/plugin.json && rg -q "okf" .claude-plugin/plugin.json \
  && echo "PASS: manifest carries the v2 identity (consultant, okf, …)" \
  || echo "WARN: plugin manifest not refreshed to the v2 identity"
```
- Pass: `.claude-plugin/{plugin,marketplace}.json` `description`/`keywords` carry the v2 identity (consultant, routing, okf, github-issues, …) and no retired-skill names
- Warn: refresh the keywords/description arrays (there is no skill list to maintain — skills auto-discover from `skills/`)

---

### OKF Conventions (Checks 7–12)

Need the vault root from CLAUDE.md (default `vault/`). If CLAUDE.md is missing, report "cannot check".

**Check 7 — CLAUDE.md exists** | Tier: Critical
- Pass: `CLAUDE.md` in project root
- Fail action: create it with the two required fields above

**Check 8 — Python 3.10+** | Tier: Critical
```bash
v=$(python3 --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
python3 -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" 2>/dev/null \
  && echo "PASS: Python $v" || echo "FAIL: need Python >= 3.10 (have '$v')"
```
- Fail action: install Python 3.10+ (macOS: `brew install python@3.12`) — required for the OKF tooling

**Check 9 — OKF tooling present** | Tier: Critical
```bash
d="${VAULT_ROOT:-vault}/_meta/okf"
for f in okf_lint.py okf_cli.py convert_links.py normalize_frontmatter.py; do
  [ -f "$d/$f" ] || { echo "FAIL: missing $d/$f"; MISS=1; }
done; [ -z "$MISS" ] && echo "PASS: OKF tooling present"
```
- Pass: `_meta/okf/` holds `okf_lint.py`, `okf_cli.py`, `convert_links.py`, `normalize_frontmatter.py`, and `_meta/generate-index.py` exists
- Fail action: run `/ark-onboard` to copy the OKF tooling into the bundle

**Check 10 — OKF lint clean** | Tier: Critical
```bash
python3 "${VAULT_ROOT:-vault}/_meta/okf/okf_lint.py" --quiet; rc=$?
[ "$rc" = "0" ] && echo "PASS: okf_lint 0 errors" || echo "FAIL: okf_lint exit $rc"
```
- Pass: `okf_lint.py --quiet` exits 0 (warnings are allowed; errors are not)
- Fail action: fix the reported errors (usually a wikilink that should be a relative link, a missing `description`, or a malformed timestamp)

**Check 11 — okf_version declared** | Tier: Critical
```bash
grep -q 'okf_version: *"0.1"' "${VAULT_ROOT:-vault}/index.md" \
  && echo "PASS: okf_version 0.1" || echo "FAIL: bundle index.md missing okf_version"
```
- Pass: the bundle root `index.md` declares `okf_version: "0.1"`
- Fail action: run `/ark-onboard` OKF init or add the frontmatter key

**Check 12 — index fresh** | Tier: Standard | Warn-only
- Pass: `index.md` exists and no page is newer than it
- Warn: pages modified since generation — refresh: `python3 ${VAULT_ROOT:-vault}/_meta/generate-index.py`
- Fail: `index.md` absent

---

### GitHub Issues Conventions (Checks 13–16)

**Check 13 — gh CLI installed + authenticated** | Tier: Standard
```bash
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 \
  && echo "PASS: gh authed" || echo "FAIL: gh missing or not authenticated"
```
- Fail action: install `gh` and run `gh auth login`

**Check 14 — label taxonomy present** | Tier: Standard
```bash
have=$(gh label list --limit 100 2>/dev/null | cut -f1)
for l in needs-triage epic P1 consultant conventions vault onboarding; do
  echo "$have" | grep -qx "$l" || { echo "FAIL: missing label '$l'"; MISS=1; }
done; [ -z "$MISS" ] && echo "PASS: triage+type+priority+component families present"
```
- Pass: triage (`needs-triage`…), type (`epic`/`story`/`task`), priority (`P1`–`P3`), and component (`consultant`/`conventions`/`vault`/`onboarding`) labels exist
- Fail action: run `/ark-onboard` label bootstrap block

**Check 15 — docs/agents config present** | Tier: Standard
```bash
for f in issue-tracker triage-labels domain; do
  [ -f "docs/agents/$f.md" ] || { echo "FAIL: missing docs/agents/$f.md"; MISS=1; }
done; [ -z "$MISS" ] && echo "PASS: docs/agents present"
```
- Pass: `docs/agents/{issue-tracker,triage-labels,domain}.md` exist (written by `/setup-matt-pocock-skills` + the ark additions)
- Fail action: run `/setup-matt-pocock-skills` on this repo

**Check 16 — frozen trackers frozen** | Tier: Standard
```bash
tn="${VAULT_ROOT:-vault}/TaskNotes"; sl="${VAULT_ROOT:-vault}/Session-Logs"
ok=1
grep -rql "FROZEN" "$tn" 2>/dev/null || { echo "WARN: TaskNotes missing FROZEN banner"; ok=0; }
grep -rql "FROZEN" "$sl" 2>/dev/null || { echo "WARN: Session-Logs missing FROZEN banner"; ok=0; }
[ "$ok" = 1 ] && echo "PASS: legacy trackers frozen, no automation targets them"
```
- Pass: `TaskNotes/` and `Session-Logs/` carry FROZEN banners; no surviving skill/script writes to them (the active work record is GitHub Issues + `log.md`)
- Warn action: run `/ark-onboard` to (re-)apply the freeze banners

---

### NotebookLM Recall (Checks 17–19)

**Check 17 — NotebookLM CLI installed** | Tier: Full | Upgrade-style
```bash
command -v notebooklm >/dev/null 2>&1 && echo "PASS" || echo "UPGRADE: notebooklm not installed"
```
- Upgrade action: `pipx install notebooklm-cli` — unlocks synthesized recall via `/notebooklm-vault`

**Check 18 — NotebookLM config reachable** | Tier: Full | Requires Check 17
```bash
{ [ -f .notebooklm/config.json ] || [ -f "${VAULT_ROOT:-vault}/.notebooklm/config.json" ]; } \
  && echo "PASS: config found" || echo "FAIL: no .notebooklm/config.json (project or vault root)"
```
- Pass: `.notebooklm/config.json` present (project root or vault root) with a notebook ID
- Fail action: run `/notebooklm-vault setup`

**Check 19 — NotebookLM authenticated** | Tier: Full | Requires Check 17
```bash
notebooklm auth check --test >/dev/null 2>&1 && echo "PASS: authenticated" || echo "FAIL: auth check failed"
```
- Fail action: `notebooklm auth login`, then rerun `/ark-health`

### Vault-awareness Convention (Check 20)

**Check 20 — vault-awareness region + reminder hook** | Tier: Standard | Warn-only | Requires Check 7
```bash
# (a) managed region present in CLAUDE.md
grep -q 'ark:begin id=vault-awareness' CLAUDE.md 2>/dev/null && b=OK || b=MISSING
# (b) reminder hook installed: script executable AND registered in settings.json Stop
{ [ -x .claude/hooks/ark-vault-reminder-hook.sh ] \
  && grep -q 'ark-vault-reminder-hook.sh' .claude/settings.json 2>/dev/null; } && h=OK || h=MISSING
{ [ "$b" = OK ] && [ "$h" = OK ]; } && echo "PASS" || echo "WARN: block=$b hook=$h"
```
- Pass: the `vault-awareness` managed region is in `CLAUDE.md` **and** the reminder hook is executable + registered.
- Warn action: run `/ark-update` (converges the block) and `/ark-onboard` Block C.2 (installs the hook). Warn-only — does not demote the health tier.

---

## Workflow

1. **Run all checks in sequence.** Do not abort on failure.
   - Checks needing the vault root: if Check 7 failed (CLAUDE.md missing), record `skip` with "cannot check — CLAUDE.md missing".
   - Checks 18, 19: if Check 17 failed, record `skip` with "requires NotebookLM CLI (check 17)".
2. **Classify each result:**

| Symbol | Outcome | Condition |
|--------|---------|-----------|
| `OK` | Pass | Check passed |
| `!!` | Fail | Check failed — has a fix instruction |
| `~~` | Warning | Non-blocking (Check 6 manifest, Check 12 index staleness, Check 16 banner, Check 20 vault-awareness) |
| `--` | Available upgrade | Feature not installed, above current tier (Check 4 OMC, Check 17 NotebookLM CLI) |

3. **Assign tier** from the highest level where no Critical or Standard check fails. Warn/skip/upgrade never demote tier.
   - **Minimal:** no fail in ecosystem + repo checks (1–6)
   - **Quick:** no fail in 1–12 (OKF conventions healthy)
   - **Standard:** no fail in 1–16 (GitHub-Issues conventions in place)
   - **Full:** no fail in 1–19 (NotebookLM recall reachable)

4. **Emit scorecard** per the Output Format. Always end with `Run /ark-onboard to fix or upgrade`.

---

## Output Format

```
Ark Health Check -- {project_name}

Ecosystems (consultant routing destinations)
  OK  superpowers detected
  OK  gstack detected
  !!  mattpocock skills -- only 1/5 present
      Fix: npx skills@latest add mattpocock/skills && /setup-matt-pocock-skills
  --  OMC -- not installed
      Unlock: autopilot / ultrawork / team routing
      Install: https://github.com/anthropics/oh-my-claudecode

Repo & Skills
  OK  6 skills (ark-consult ark-health ark-onboard ark-update notebooklm-vault vault)
  OK  plugin manifest v2-clean

OKF Conventions
  OK  CLAUDE.md present
  OK  Python 3.12 available
  OK  OKF tooling present
  OK  okf_lint 0 errors
  OK  okf_version 0.1 declared
  ~~  index stale ({N} pages modified since generation)
      Refresh: python3 vault/_meta/generate-index.py

GitHub Issues
  OK  gh authenticated
  OK  label taxonomy present
  OK  docs/agents config present
  OK  legacy trackers frozen

NotebookLM
  OK  notebooklm CLI installed
  OK  config reachable
  OK  authenticated

Score: {tier} tier | {N} fix, {N} warning, {N} upgrades available
Run /ark-onboard to fix or upgrade
```

**Rules:**
- Always show all 5 section headers (Ecosystems, Repo & Skills, OKF Conventions, GitHub Issues, NotebookLM)
- Never omit a check — skipped checks render as `--  {name} -- cannot check (CLAUDE.md missing)`
- `!!` → indented `Fix:` line; `~~` → indented `Refresh:`/`Fix:`; `--` → indented `Unlock:` + `Install:`
- Singular/plural: `1 fix`, not `1 fixes`
- Always end with: `Run /ark-onboard to fix or upgrade`

---

## Design Decisions

- **No auto-fix.** `/ark-health` diagnoses and recommends only. All fixes go through `/ark-onboard`.
- **Authoritative check definitions.** This skill is the source of truth for the v2 invariant checks. If `/ark-onboard`'s copy drifts from here, this file wins.
- **Session-based plugin detection.** Ecosystems are detected by whether their skills appear in the current session — never by inspecting `~/.claude/plugins/`. mattpocock is the exception (its skills are `disable-model-invocation`, so it is detected on the filesystem).
- **Graceful degradation.** Never abort on CLAUDE.md absence. Report clearly and continue.
- **Two-core invariants.** The checks map directly to the v2 acceptance criteria: the consultant's four routing destinations, the 6-skill roster, an OKF-clean bundle, the GitHub-Issues convention layer, and NotebookLM recall.
