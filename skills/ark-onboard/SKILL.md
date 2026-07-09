---
name: ark-onboard
description: Interactive setup wizard — converges a project onto the ark-skills v2 conventions (OKF knowledge bundle + GitHub-Issues task management + mattpocock issue machinery). Handles greenfield, migration, repair, and healthy states.
---

# Ark Onboard

Interactive setup wizard that converges a project onto the ark-skills **v2 conventions layer**:

1. an **OKF v0.1 knowledge bundle** at `vault/` (in-bundle tooling under `_meta/okf/`, `index.md` declaring `okf_version`, relative-markdown links),
2. **GitHub Issues** task management (label taxonomy + `docs/agents/` conventions + frozen legacy trackers), and
3. **mattpocock/skills** as the issue machinery (`/to-tickets`, `/triage`) and the consultant's routing destinations (superpowers, gstack, OMC).

This skill diagnoses via `/ark-health` and applies fixes. `/ark-health` is the source of truth for the invariant definitions — this skill executes the remediations.

## Context-Discovery Exemption

Exempt from normal context-discovery — it must work when CLAUDE.md is missing, broken, or incomplete. It creates or repairs CLAUDE.md itself.

## Required CLAUDE.md Fields (v2)

| Field | Format | Example |
|-------|--------|---------|
| Project name | any string (header or table) | `trading-signal-ai` |
| Vault root | path to the OKF bundle, ending `/` | `vault/` |
| Task Management | GitHub Issues via `gh` (see `docs/agents/issue-tracker.md`) | — |

Task-prefix / TaskNotes-counter fields are retired (TaskNotes is frozen; task tracking is GitHub Issues).

---

## Entry Flow

```
User runs /ark-onboard
    |
    v
[1] Check ecosystems (superpowers, gstack, mattpocock, OMC) via /ark-health checks 1–4
    |
    v
[2] Missing critical ecosystem? --> show install command, PAUSE for user
    gstack repo on disk?         --> gstack Setup (claude + codex) — see below
    |
    v
[3] Run state detection (references/state-detection.md)
    |
    v
[4] Route by state:
    No Vault      --> Greenfield path (OKF bundle init + conventions)
    Non-OKF Vault --> Migration path (OKF-convert + conventions)
    Partial       --> Repair path (fix failing /ark-health checks)
    Healthy       --> Show scorecard --> surface upgrades
    |
    v
[5] Run full /ark-health diagnostic
    |
    v
[6] Show before/after scorecard + follow-up reminders
```

---

## gstack Setup (claude + codex only)

Run during Entry-Flow Step 2 when a gstack repo is present on disk. gstack installs **per-host** (`setup --host <name>`, one host per skill dir). This project's policy is **claude + codex only** — installing for gemini or cursor floods that agent's context window (~48% on a fresh session). The host list is deliberate policy, not a default to "improve" toward `--host auto`.

**Guardrail (read before touching `~/.claude/skills/gstack`):** that directory is gstack's shared **runtime root** (`bin/`, `browse/dist`, `gstack-upgrade`, `ETHOS.md`, `review/`), referenced by 50+ skills. It is NOT a duplicate-platform copy — deleting it breaks every gstack skill. Never delete it; never run `setup --host auto` (that also targets kiro/droid/opencode).

This block is **idempotent and self-repairing**: it only runs `setup` for a host whose install is missing or partial. **Confirm first** — ask `Run gstack setup now? Targets: claude, codex [Y/n]` — then execute:

```bash
CLAUDE_ROOT="$HOME/.claude/skills/gstack"
CODEX_ROOT="$HOME/.codex/skills/gstack"
GSTACK_REPO=""
[ -d "$CLAUDE_ROOT" ] && GSTACK_REPO="$(cd "$CLAUDE_ROOT" 2>/dev/null && pwd -P || true)"
[ -x "$GSTACK_REPO/setup" ] || GSTACK_REPO="$HOME/.gstack/repos/gstack"

if [ ! -x "$GSTACK_REPO/setup" ]; then
  echo "gstack repo not found — install gstack first, then re-run /ark-onboard."
else
  if [ ! -x "$CLAUDE_ROOT/bin/gstack-config" ] || [ ! -f "$HOME/.claude/skills/_gstack-command/SKILL.md" ]; then
    ( cd "$GSTACK_REPO" && ./setup --host claude )
  fi
  if { command -v codex >/dev/null 2>&1 || [ -d "$HOME/.codex" ]; } && \
     { [ ! -x "$CODEX_ROOT/bin/gstack-config" ] || \
       [ -z "$(find -L "$HOME/.codex/skills" -maxdepth 1 -name 'gstack-*' -type d -print -quit 2>/dev/null)" ]; }; then
    ( cd "$GSTACK_REPO" && ./setup --host codex )
  fi
fi
# NEVER --host auto / gemini / cursor.
```

To remove an over-broad install picked up elsewhere: `rm -rf ~/.cursor/skills/gstack ~/.gemini/skills/gstack`. `/ark-health` Check 2-family flags both failure modes.

---

## Shared bootstrap blocks

The greenfield, migration, and repair paths all reuse these three blocks.

### Block A — OKF bundle init

Reference: the **OKF v0.1 SPEC** — https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md. OKF is deliberately domain-agnostic: the only hard requirement is a non-empty `type:` on every non-reserved `.md`; `index.md` and `log.md` are optional reserved files; concept files and subdirectories are arbitrary ("the directory structure is independent of the domain"). Seed the OKF-conformant **core** first, then add the Ark **recommended layer** (house style — convention, not OKF-required). The OKF tooling *scripts* are copied from the ark-skills plugin's own bundle (`<plugin>/vault/`) — that is tooling, not structure.

**Core (OKF-conformant — always):**

1. Copy the OKF tooling into `vault/_meta/okf/`: `okf_lint.py`, `okf_cli.py`, `convert_links.py`, `normalize_frontmatter.py`; and `vault/_meta/generate-index.py` (from `<plugin>/vault/`).
2. Create `vault/index.md` declaring `okf_version: "0.1"` in its frontmatter (the SPEC marks this optional; ark tooling + `/ark-health` Check 11 require it — stricter than spec, intentionally).
3. Create an empty `vault/log.md` (the in-bundle work-record mirror; see `/vault`).
4. Wire the pre-push lint hook (`vault/_meta/githooks/pre-push` + `git config core.hooksPath`).

**Ark recommended layer (convention, not OKF-required — default on; offer to skip for a minimal bundle):**

5. Create the Ark starter folders: `vault/{_Templates,_Attachments}`, `vault/Research`, `vault/Compiled-Insights`.
6. Copy the OKF page templates into `vault/_Templates/` (Research, Compiled-Insight, Service, etc.) and write `vault/_meta/vault-schema.md` + `vault/_meta/taxonomy.md`.
7. Create `vault/00-Home.md` (navigation MOC). These folders are the Ark house style and the write targets `/vault` expects (`Research/`, `Compiled-Insights/`, `_Templates/`); an OKF consumer does not require them.

**Finish (both tiers):** `python3 vault/_meta/generate-index.py` then `python3 vault/_meta/okf/okf_lint.py --quiet` (must exit 0). The core alone is already conformant; adding the layer keeps it conformant.

### Block B — GitHub Issues conventions

**Precondition:** `gh auth status` OK and `git remote -v` points at the GitHub repo.

1. Bootstrap the label taxonomy (idempotent — `gh label create ... || gh label edit ...`):
   - **triage:** `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`
   - **type:** `epic`, `story`, `task`
   - **priority:** `P1`, `P2`, `P3`
   - **component:** `consultant`, `conventions`, `vault`, `onboarding` (adjust the component set per project)
   ```bash
   gh label create needs-triage -c "#e99695" -d "Maintainer needs to evaluate" 2>/dev/null || true
   gh label create epic -c "#3e4b9e" -d "Parent issue with a task-list body" 2>/dev/null || true
   gh label create P1 -c "#b60205" -d "Urgent — do first" 2>/dev/null || true
   gh label create consultant -c "#c5def5" -d "ark-consult workflow consultant" 2>/dev/null || true
   # …repeat for every label in the four families…
   ```
2. Run `/setup-matt-pocock-skills` on the repo (tracker = GitHub; map its 5 canonical triage roles onto the labels above; single-context domain docs). It writes `docs/agents/{issue-tracker,triage-labels,domain}.md` + an `## Agent skills` CLAUDE.md block. Then merge the ark-specific proactive-behavior conventions into `docs/agents/issue-tracker.md` (the four behaviors, AI disclaimer, `log.md` dual-write rule).
3. Freeze any legacy trackers present: prepend a `> **FROZEN <date>** — active tracking moved to GitHub Issues` banner to the entry doc of `vault/TaskNotes/` and `vault/Session-Logs/` (no file moves; survivors re-filed as issues manually).

### Block C — CLAUDE.md rows

Create CLAUDE.md if missing, or add the missing rows. The Project Configuration table:

```markdown
## Project Configuration

| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/` |
| **Task Management** | GitHub Issues via `gh` CLI — see `docs/agents/issue-tracker.md` for the label families and `gh` crib |
```

Never add task-prefix / TaskNotes-counter rows (retired). The mattpocock setup (Block B step 2) adds the `## Agent skills` block automatically.

### Block C.1 — vault-awareness region (v2.2.0)

CLAUDE.md also carries the ark-managed **vault-awareness** region: it tells agents to
consult the OKF vault before non-trivial work and to distill via `/vault` at session end.
It is a managed region owned by `/ark-update` (`vault-awareness` in `target-profile.yaml`),
so seed it by running the convergence once. First resolve `$ARK_SKILLS_ROOT` (the ark-skills
plugin root) exactly as **`/ark-update` Step 1** does — prefer `$CLAUDE_PLUGIN_DIR`, else the
`.claude-plugin/marketplace.json` anchor in CWD, else the newest install under
`~/.claude/plugins/cache`. Then run the convergence (inserts the block marker-wrapped and
version-stamped from the target profile; idempotent, safe to re-run):

```bash
python3 "$ARK_SKILLS_ROOT/skills/ark-update/scripts/migrate.py" \
    --project-root "$(pwd)" --skills-root "$ARK_SKILLS_ROOT"
```

If `AGENTS.md` exists, mirror the region into it: copy the whole
`<!-- ark:begin id=vault-awareness … -->` … `<!-- ark:end id=vault-awareness -->` block
(markers included) from the CLAUDE.md region you just seeded, and append it to `AGENTS.md`.
Do **not** create `AGENTS.md` if it is absent — the managed region converges CLAUDE.md only.

### Block C.2 — vault-reminder Stop hook (v2.2.0)

Install the gentle end-of-session reminder that suggests `/vault` (suggestion-only: it never
writes to the vault and never blocks the stop; it fires at most once per session).

1. Copy the hook into the project and make it executable:

   ```bash
   mkdir -p .claude/hooks
   cp "$ARK_SKILLS_ROOT/skills/ark-onboard/assets/ark-vault-reminder-hook.sh" \
       .claude/hooks/ark-vault-reminder-hook.sh
   chmod +x .claude/hooks/ark-vault-reminder-hook.sh
   ```

2. Register it under `hooks.Stop` in `.claude/settings.json`, **merging** into any existing
   Stop array — never clobber hooks already present:

   ```json
   {
     "hooks": {
       "Stop": [
         { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/ark-vault-reminder-hook.sh\"" } ] }
       ]
     }
   }
   ```

   If `settings.json` or its `hooks.Stop` array is missing, create it; if a Stop array already
   exists, append this entry to it (do not overwrite sibling hooks).

---

## Path: No Vault (Greenfield)

Confirm the vault path, then run **Block A** (OKF init) → **Block B** (GitHub Issues) → **Block C** (CLAUDE.md). Then:

1. Verify Python 3.10+ (`python3 -c "import sys;sys.exit(sys.version_info<(3,10))"`).
2. Offer to externalize the vault (symlink to a centralized location) — see `references/externalize-vault-plan.md`. Optional; skip for a simple embedded vault.
3. `git init` (if needed) + initial commit of the bundle skeleton + CLAUDE.md + `docs/agents/`.
4. Run the final `/ark-health` diagnostic and show the scorecard.

## Path: Non-OKF Vault (Migration)

An existing vault that is not yet an OKF bundle.

1. Pre-commit the existing state (safety).
2. OKF-convert (per the playbook's 7-step recipe): copy `_meta/okf` tooling → survey → `normalize_frontmatter.py --apply` → `convert_links.py --apply` (wikilinks → relative markdown) → hand-write missing `description:` values → `generate-index.py` → `okf_lint.py` to 0 errors. Add `okf_version: "0.1"` to `index.md`.
3. Run **Block B** (GitHub Issues) and **Block C** (CLAUDE.md).
4. Freeze any `Session-Logs/` and `TaskNotes/` trees with banners.
5. Final commit + `/ark-health` scorecard.

## Path: Partial (Repair)

1. Run the full `/ark-health` diagnostic.
2. For each failing check, apply the matching remediation:
   - OKF lint errors → fix the reported pages, re-run `okf_lint.py --quiet`.
   - Missing `okf_version` → add it to `index.md`.
   - Missing labels → re-run **Block B** step 1.
   - Missing `docs/agents/` → re-run `/setup-matt-pocock-skills` (**Block B** step 2).
   - Missing frozen banners → apply **Block B** step 3.
   - gstack runtime-root broken → re-run the gstack Setup block.
   - Centralized-vault issues → `references/centralized-vault-repair.md`.
3. Re-run `/ark-health`; show before/after scorecard.

## Path: Healthy

Run `/ark-health`, show the scorecard, and surface upgrade opportunities (NotebookLM recall if not configured).

---

## Design Decisions

- **`/ark-health` owns the check definitions; `/ark-onboard` owns the fixes.** If they drift, `/ark-health` wins.
- **Idempotent bootstrap.** Blocks A–C are safe to re-run; label creation and setup steps no-op when already present.
- **Freeze, don't migrate.** Legacy `TaskNotes/`/`Session-Logs/` get banners; their content is re-filed as GitHub issues manually, never by a script.
- **No legacy memory-CLI, TaskNotes-MCP, or obsidian-plugin install.** v2 retrieval is NotebookLM (synthesized) + `okf_cli.py` (navigation); task tracking is GitHub Issues.
- **Downstream convergence is deferred.** Running this profile against other ArkNode projects ships later per-project via `/ark-update`.
