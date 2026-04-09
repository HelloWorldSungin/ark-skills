# Onboarding Skills Design

Two new skills to smooth the new-user experience for team members joining the Ark ecosystem.

## Problem

New team members who install `ark-skills` face two silent failure modes:

1. **Missing dependencies = degraded experience they don't know about.** They use `/wiki-query` and get T4 (index scan) without realizing T1/T2 would give 5x better answers with MemPalace or NotebookLM installed.
2. **CLAUDE.md misconfigured or missing entirely.** They install the plugin but never create the project-level CLAUDE.md, so every skill fails with "missing field" errors.

Both are discovery problems — the user doesn't know what they're missing.

## Target User

Team members who already know Obsidian and Claude Code but have zero Ark-specific knowledge. They can follow CLI instructions but won't read a 400-line onboarding guide.

## Solution

Two skills sharing a common diagnostic engine:

- **`/ark-onboard`** — Interactive wizard for first-time setup. Handles greenfield projects, existing non-Ark vaults, and partial setups.
- **`/ark-health`** — Diagnostic check you run anytime. Reports what's working, what's broken, and what could be unlocked.

---

## Shared Diagnostic Engine

A diagnostic checklist defined once in a shared reference section within each SKILL.md. Both skills reference identical check definitions — one source of truth for what "healthy" means. Claude runs bash commands inline for each check.

### Context-Discovery Exemption

**These two skills are exempt from the normal context-discovery contract.** Every other Ark skill reads CLAUDE.md and errors on missing fields. `/ark-onboard` and `/ark-health` are the skills that *create and validate* the CLAUDE.md — they must work when it's missing, broken, or incomplete. When CLAUDE.md is absent, the wizard enters greenfield mode. When fields are missing, the health check reports them as failures with fix instructions.

### Vault Path Terminology

The current docs use "Obsidian Vault" to mean different things in different contexts. This spec normalizes:

| Term | Meaning | Example |
|------|---------|---------|
| **Vault root** | Top-level directory containing all vault content | `vault/` |
| **Project docs path** | Subdirectory for project-specific knowledge (may equal vault root for standalone projects) | `vault/Trading-Signal-AI/` |
| **TaskNotes path** | Sibling of project docs under vault root, never nested | `vault/TaskNotes/` |

For **standalone projects**, vault root = project docs path (e.g., `vault/` contains `_meta/`, `_Templates/`, `TaskNotes/`, `00-Home.md` directly).

For **shared/monorepo vaults**, vault root contains project docs as a subdirectory (e.g., `vault/` contains `Trading-Signal-AI/` and `TaskNotes/` as siblings).

The diagnostic checks must handle both layouts. Check #7 (vault structure) looks for Ark artifacts relative to vault root, not relative to project docs path.

### Required CLAUDE.md Fields (Normalized)

| Field | Table Row | Format | Derived? |
|-------|-----------|--------|----------|
| Project name | Header or table | String | No — user provides |
| Vault root | "Obsidian Vault" row | Backtick-enclosed relative path | No — user provides |
| Task prefix | "Task Management" row | String ending with `-` | No — user provides |
| TaskNotes path | "Task Management" row | Backtick-enclosed relative path | No — user provides |
| Counter file | — | `{tasknotes_path}/meta/{task_prefix}counter` | **Yes — derived** |
| Project docs path | — | Same as vault root (standalone) or subdirectory (monorepo) | **Yes — derived or explicit** |

Only the first 4 are required in CLAUDE.md. Counter file and project docs path are computed by skills.

### Project State Detection

Classify project state **before** asking for tier. The tier question only applies to No Vault and Non-Ark states. Partial/Healthy states already have an implicit tier based on what's present.

| State | Detection | Wizard Path |
|-------|-----------|-------------|
| **No vault** | CLAUDE.md missing, or vault root field missing, or vault root path doesn't exist | Full setup — create vault from scratch (absorbs `/wiki-setup`) |
| **Non-Ark vault** | Vault dir exists but missing 3+ of: `_meta/vault-schema.md`, `_meta/taxonomy.md`, `index.md`, `TaskNotes/meta/` | Migration — add Ark scaffolding around existing content |
| **Partial Ark vault** | Has Ark structure (3+ artifacts present) but some checks fail | Repair — fix what's broken, skip what's working |
| **Healthy Ark vault** | All Critical + Standard checks pass | Report — show status, surface Full tier upgrades |

Note: "Non-Ark vault" requires missing 3+ artifacts, not just 2, to avoid false positives on Ark vaults that are merely incomplete (those are "Partial").

### Diagnostic Checklist (19 checks)

**Plugins**

| # | Check | Pass Criteria | Tier |
|---|-------|--------------|------|
| 1 | superpowers plugin | Brainstorming, writing-plans, TDD skills available. Install: `/plugin install superpowers@claude-plugins-official` (marketplace: `anthropics/claude-plugins-official`) | Critical |
| 2 | gstack plugin | Browse, QA, ship skills available. Best-effort detection: check if gstack skills are loadable in the current session. Note: plugin detection relies on skill availability, not filesystem inspection of `~/.claude/plugins/`. | Standard |
| 3 | obsidian plugin | Obsidian CLI skill available. Install: `/plugin install obsidian@obsidian-skills` (marketplace: `kepano/obsidian-skills`) | Standard |

*ark-skills self-check omitted — if these skills are running, the plugin is already installed.*

**Project Configuration**

| # | Check | Pass Criteria | Tier |
|---|-------|--------------|------|
| 4 | CLAUDE.md exists | File found in project root | Critical |
| 5 | CLAUDE.md fields | All 4 required fields present with correct format (vault root, project name, task prefix, TaskNotes path) | Critical |
| 6 | Task prefix format | Ends with `-`, counter file path resolves | Critical |

**Vault Structure**

| # | Check | Pass Criteria | Tier |
|---|-------|--------------|------|
| 7 | Vault directory exists | Vault root path from CLAUDE.md resolves to real directory | Critical |
| 8 | Vault structure | Has `_meta/`, `_Templates/`, `TaskNotes/`, and either `00-Home.md` (standalone) or project docs subdirectory (monorepo) | Critical |
| 9 | Python 3.10+ | `python3 --version` >= 3.10. Required for index generation even at Quick tier. | Critical |
| 10 | Index status | `index.md` exists. Staleness is a **warning** (not failure): compare `index.md` mtime against newest `.md` file excluding `TaskNotes/Archive/`, `_Templates/`, `_Attachments/`. | Standard |
| 11 | Task counter | Counter file exists at `{tasknotes_path}/meta/{task_prefix}counter`, contains integer | Standard |

**Integrations**

| # | Check | Pass Criteria | Tier |
|---|-------|--------------|------|
| 12 | Obsidian vault plugins | `tasknotes/main.js` and `obsidian-git/main.js` exist in `.obsidian/plugins/` | Standard |
| 13 | TaskNotes MCP | `mcpServers.tasknotes` entry in `.claude/settings.json`. Note: if Obsidian plugins require manual install, this is a known handoff — wizard documents it and pauses for user action. | Standard |
| 14 | MemPalace installed | `mempalace` CLI on PATH. If missing, show: `pipx install "mempalace>=3.0.0,<4.0.0"`. If pipx unavailable, show pip fallback. If install fails, log error and continue — Full tier degrades gracefully. | Full |
| 15 | MemPalace wing indexed | `mempalace status` shows wing for this project | Full |
| 16 | History auto-index hook | `~/.claude/hooks/ark-history-hook.sh` exists AND hook registered in project-local `.claude/settings.json` (Stop hook entry containing `ark-history-hook`). Install: `bash skills/claude-history-ingest/hooks/install-hook.sh`. Requires MemPalace (check #14). | Full |
| 17 | NotebookLM CLI installed | `notebooklm` CLI on PATH. If missing, show: `pipx install notebooklm-cli`. If install fails, log error and continue. | Full |
| 18 | NotebookLM config | `.notebooklm/config.json` exists with non-empty notebook ID | Full |
| 19 | NotebookLM authenticated | `notebooklm auth check --test` passes. If auth fails, show re-auth command and continue — user can complete later. | Full |

Each check returns: `pass`, `fail`, or `available upgrade` (for checks above the user's chosen tier).

---

## `/ark-onboard` — Setup Wizard

### Entry Flow

```
User runs /ark-onboard
    ↓
Check plugins (superpowers, gstack, obsidian)
    ↓
Missing critical? → Show install commands, wait for user to install
Missing standard? → Note for later, continue
    ↓
Run Critical checks → detect project state
    ↓
State = No Vault or Non-Ark?
    → Ask: "What setup level?" → Quick / Standard / Full
State = Partial Ark?
    → Show what's failing, offer repair + optional tier upgrade
State = Healthy?
    → Show scorecard, surface Full tier upgrades
    ↓
Execute steps for detected state + chosen tier
    ↓
Run full diagnostic → show before/after scorecard
```

### Tier Definitions

| Tier | What Gets Set Up | Time | Skills Unlocked |
|------|-----------------|------|-----------------|
| **Quick** | CLAUDE.md + vault structure + Python check + index generation | ~5 min | All zero-dep skills: `wiki-lint`, `wiki-status`, `wiki-update`, `wiki-ingest`, `data-ingest`, `tag-taxonomy`, `cross-linker`, `ark-code-review --quick` |
| **Standard** | Quick + TaskNotes MCP + Obsidian plugins | ~10 min | + `ark-tasknotes`, `codebase-maintenance`, `ark-code-review --full` |
| **Full** | Standard + MemPalace + history hook + NotebookLM CLI + vault mining | ~25 min | + `wiki-query` T1/T2, `claude-history-ingest` (auto-indexing), `notebooklm-vault` |

Note: "Skills Unlocked" counts are approximate and based on the current plugin inventory at time of writing. The scorecard derives the actual count by checking which skills are loadable, not from a hardcoded number.

### Path: No Vault (Greenfield)

This absorbs the current `/wiki-setup` workflow. `/ark-onboard` becomes the single entry point for new projects.

1. Ask project name, task prefix, vault path (default: `./vault/`), and vault layout (standalone vs monorepo)
2. Verify Python 3.10+ is available (required for index generation)
3. Create full vault structure: `_meta/`, `_Templates/`, `TaskNotes/`, `00-Home.md`, `.obsidian/`, `.notebooklm/`
4. Create metadata files: `vault-schema.md`, `taxonomy.md`, `generate-index.py`
5. Create task counter, project management guide, 6 page templates
6. Create `.gitignore` for vault (workspace.json, plugin data.json, sync-state.json)
7. Create/update CLAUDE.md with all 4 required fields
8. If Standard+: ask for reference vault path to copy plugin binaries. If no reference: tell user to install TaskNotes + Obsidian Git manually from Obsidian Community Plugins browser after opening vault. **Pause here** — this is a manual handoff point. Resume when user confirms plugins are installed.
9. If Standard+: generate TaskNotes `data.json` with API + MCP enabled, configure `mcpServers.tasknotes` in `.claude/settings.json`
10. If Full: check for MemPalace (`which mempalace`). If missing, show install command and wait. If install fails (no pipx, network error, etc.), warn and skip — Full tier degrades to Standard for this check.
11. If Full: run `mine-vault.sh` to index vault into MemPalace
12. If Full: install history auto-index hook — run `bash skills/claude-history-ingest/hooks/install-hook.sh`. This copies the hook script to `~/.claude/hooks/`, registers a Stop hook in project-local `.claude/settings.json`, and initializes MemPalace state. After install, Claude sessions in this project auto-index into MemPalace on exit.
13. If Full: check for NotebookLM CLI. If missing, show install command. Walk through `notebooklm login` auth. If auth fails, warn and skip — user can complete later.
14. If Full: create `.notebooklm/config.json` template with placeholder notebook ID
15. Generate index (`python3 _meta/generate-index.py`)
16. Initialize git in vault directory and create initial commit
17. Run full diagnostic, show scorecard
18. Remind user of follow-up steps not handled by wizard: open vault in Obsidian, verify plugins, fill in NotebookLM notebook ID (if Full), add vault to linear-updater (if applicable)

### Path: Non-Ark Vault (Migration)

Key principle: **structure is additive only.** New folders and files are created alongside existing content. Existing notes are never moved or renamed.

**Frontmatter changes are explicit and reversible:** Frontmatter backfill modifies existing files. This is treated as a content change, not a structural change. The wizard commits all existing content first, then applies frontmatter changes in a separate commit so they can be reverted with `git revert`.

1. Scan existing vault content — count pages, detect existing frontmatter patterns (YAML keys present, tag formats used), report folder structure
2. Ask project name, task prefix (vault path already known)
3. **Commit existing vault state** — `git add -A && git commit -m "checkpoint: pre-Ark migration"` so all changes are reversible
4. Add Ark scaffolding non-destructively: create `_meta/`, `_Templates/`, `TaskNotes/` alongside existing folders. Never move or rename existing directories.
5. Generate `vault-schema.md` describing the actual structure found (existing folders + new Ark folders)
6. Scan existing tags across all pages → propose canonical taxonomy. Merge existing tags into taxonomy rather than replacing them.
7. Offer frontmatter backfill:
   - Show 3 sample pages with proposed changes (adding `type:`, `summary:`, `tags:` where missing)
   - Ask user to confirm the pattern
   - Apply in bulk, then commit separately: `git commit -m "feat: backfill Ark frontmatter on N pages"`
   - User can revert this commit if results are wrong
   - Skip pages with non-standard formats (no YAML frontmatter, fenced code blocks at top, non-UTF8)
8. Create/update CLAUDE.md with required fields
9. Standard/Full tier steps same as greenfield (steps 8-13)
10. Generate index, run diagnostic, show scorecard

### Path: Partial Ark (Repair)

1. Run diagnostic, show what's failing
2. Fix each failing check in order (create missing counter, regenerate stale index, add missing CLAUDE.md fields, etc.)
3. Offer tier upgrade if current tier < desired tier
4. Run diagnostic again, show before/after scorecard

### Scorecard Output

Displayed at the end of every wizard path:

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

`--` items are available upgrades, not failures. `/ark-health` continues to surface them.

---

## `/ark-health` — Ongoing Diagnostic

### Behavior

1. Run all 19 diagnostic checks (regardless of tier — checks everything)
2. Classify each as `pass`, `fail`, `warn`, or `available upgrade`
3. Output scorecard
4. For each `fail`: one-line actionable fix instruction
5. For each `warn`: one-line explanation (e.g., stale index)
6. For each `available upgrade`: one-line pitch explaining what it unlocks + install command

### Example Output

```
Ark Health Check -- my-project

Plugins
  OK  superpowers v5.0.7
  OK  obsidian v1.0.1
  !!  gstack -- not detected
      Unlock: /browse, /qa, /ship, /review, /design-review + more
      Check: /plugin marketplace list for gstack source

Project Configuration
  OK  CLAUDE.md exists and has required fields
  OK  Task prefix: MyProject- (counter at 7)

Vault Structure
  OK  Vault healthy (42 pages, standalone layout)
  ~~  Index stale (5 pages modified since last generation)
      Refresh: cd vault && python3 _meta/generate-index.py
  OK  Python 3.12 available

Integrations
  OK  Obsidian vault plugins installed
  !!  TaskNotes MCP -- not in .claude/settings.json
      Fix: Add mcpServers.tasknotes to .claude/settings.json (port 8080)
  --  MemPalace -- not installed
      Unlock: T2 retrieval for /wiki-query (deep synthesis, experiential recall)
      Install: pipx install "mempalace>=3.0.0,<4.0.0"
  --  History hook -- not installed (requires MemPalace)
      Unlock: Auto-index Claude sessions into MemPalace on exit
      Install: bash skills/claude-history-ingest/hooks/install-hook.sh
  --  NotebookLM -- not installed
      Unlock: T1 retrieval (fastest answers) + /notebooklm-vault
      Install: pipx install notebooklm-cli

Score: Standard tier | 1 fix, 1 warning, 3 upgrades available
Run /ark-onboard to fix or upgrade
```

Note: the scorecard no longer uses a "X/Y skills unlocked" count. The old metric was not grounded in the actual plugin inventory (which changes as skills are added). Instead, it reports the tier label and counts of actionable items.

### Design Decisions

- **No auto-fix.** `/ark-health` only diagnoses and recommends. Fixes go through `/ark-onboard` (which detects "Partial Ark" state and runs repair). Keeps health check safe as a quick sanity command.
- **Always points to `/ark-onboard`** for remediation. Single entry point for all changes.
- **Index staleness is a warning, not a failure.** Index goes stale during normal use after any note edit. The health check reports it as `~~` (warning) with a refresh command, not `!!` (failure). Staleness excludes `TaskNotes/Archive/`, `_Templates/`, and `_Attachments/` from the comparison.
- **Tier label** gives the user vocabulary to discuss their setup level.
- **Shared checklist, not shared script.** Both SKILL.md files reference the same 19 checks defined in the Diagnostic Checklist section above. This is instruction duplication (Claude reads both), not code duplication. If checks drift between the two files, `/ark-health` is authoritative — it's the diagnostic source of truth.

---

## Relationship to Existing Skills

| Existing Skill | Change |
|----------------|--------|
| `/wiki-setup` | Functionality absorbed into `/ark-onboard` greenfield path. `/wiki-setup` remains available but onboarding guide and `/ark-onboard` become the recommended entry point. |
| `/wiki-status` | Unchanged. Stays focused on vault page counts, anchor pages, orphans. `/ark-health` covers the broader ecosystem. |
| `/wiki-lint` | Unchanged. Stays focused on vault content quality (broken links, frontmatter, tags). |
| `/ark-workflow` | When built, should run `/ark-health` checks at the start of any workflow and warn if critical checks fail. |

---

## New Files

| File | Purpose |
|------|---------|
| `skills/ark-onboard/SKILL.md` | Setup wizard skill definition |
| `skills/ark-health/SKILL.md` | Health check skill definition |

No shared shell scripts. Both skills embed the diagnostic checklist as instructions — Claude runs bash commands inline for each check.

---

## Verification

After implementing both skills:

1. **Greenfield test:** In a fresh empty repo, run `/ark-onboard` with Quick tier. Verify vault created, CLAUDE.md populated, Python checked, index generated, `/wiki-status` works.
2. **Migration test:** In a repo with an existing non-Ark Obsidian vault, run `/ark-onboard`. Verify: pre-migration commit created, existing content untouched, Ark scaffolding added, frontmatter backfill in separate commit, git revert of backfill works cleanly.
3. **Health check test:** In a partially configured project (missing TaskNotes MCP), run `/ark-health`. Verify it detects the gap, shows the fix command, and index staleness shows as warning not failure.
4. **Full tier test:** Run `/ark-onboard` with Full tier. Verify MemPalace, history hook, and NotebookLM checks pass after guided installation. Verify graceful degradation when install fails (skip and continue).
5. **Hook test:** After Full tier setup, verify `~/.claude/hooks/ark-history-hook.sh` exists, `.claude/settings.json` has Stop hook entry, and `mempalace status` shows the project wing.
6. **Plugin detection test:** In a project missing gstack, run `/ark-health`. Verify it surfaces as an available upgrade.
7. **Monorepo test:** In a monorepo with shared vault and sub-project CLAUDEs, run `/ark-health` from a sub-project directory. Verify it correctly resolves vault root vs project docs path.
8. **No CLAUDE.md test:** In a project with no CLAUDE.md at all, run `/ark-onboard`. Verify it enters greenfield mode without crashing (context-discovery exemption works).

---

## Appendix: Codex Review Findings

Independent review by OpenAI Codex on 2026-04-08. All 15 findings addressed in this spec revision. One additional finding (hooks) caught during user review.

| # | Finding | Resolution |
|---|---------|------------|
| 1 | ark-skills self-check is tautological | Removed — if these skills are running, the plugin is installed |
| 2 | Context-discovery conflict | Added "Context-Discovery Exemption" section — these two skills are exempt |
| 3 | Vault path model inconsistent | Added "Vault Path Terminology" section normalizing vault root vs project docs path vs TaskNotes path |
| 4 | Healthy classification circular | Reordered: Critical checks run first to detect state, tier question only for greenfield/migration |
| 5 | Check counts broken | Fixed to 19 checks. Removed hardcoded "X/Y skills" metric in favor of tier label + actionable counts |
| 6 | Gstack check brittle | Changed to best-effort skill availability detection, noted it's not filesystem inspection |
| 7 | Python not in Quick tier | Moved Python check to Critical tier — required for index generation at all tiers |
| 8 | Index freshness noisy | Changed from failure to warning (`~~`). Added exclusion list for Archive, Templates, Attachments |
| 9 | Frontmatter backfill is destructive | Reworded migration principle: structure is additive, frontmatter changes are explicit. Pre-migration commit + separate backfill commit for easy revert. Skip non-standard pages. |
| 10 | Migration detector naive | Changed from 2-signal to 3+-signal detection (vault-schema, taxonomy, index, TaskNotes/meta) |
| 11 | Duplicated checks = drift | Acknowledged. `/ark-health` is authoritative source of truth. Documented in design decisions. |
| 12 | Full tier underspecified | Added failure modes for each install step: pipx fallback, network error handling, skip-and-continue |
| 13 | Standard not deterministic | Documented Obsidian plugin install as explicit manual handoff point with pause |
| 14 | Wiki-setup absorption gaps | Added git init, .gitignore, follow-up reminder step for linear-updater and NotebookLM |
| 15 | CLAUDE.md fields ambiguous | Added "Required CLAUDE.md Fields (Normalized)" table distinguishing user-provided vs derived fields |
| 16 | (User review) History hook not covered | Added check #16 for `ark-history-hook.sh` installation and Stop hook registration. Added step 12 in greenfield wizard. Hook requires MemPalace (check #14) as prerequisite. |
