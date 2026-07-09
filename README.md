# Ark Skills Plugin

Claude Code plugin providing 6 shared skills to all ArkNode projects, built around two co-equal cores: a **workflow consultant** that plans and routes each task to one execution ecosystem, and a **conventions layer** that converges projects onto shared OKF knowledge bundles + GitHub-Issues task management. A context-discovery pattern adapts every skill to the active project at runtime.

## Installation

```bash
# Add the marketplace
/plugin marketplace add HelloWorldSungin/ark-skills

# Install the plugin (user-scoped — available in all projects)
/plugin install ark-skills@ark-skills

# Verify skills are available
/ark-health
```

### Prerequisites

**Required for all skills:** None — skills are instruction-only.

**Optional — enhances task tracking, retrieval, and routing:**

| Dependency | Skills Enhanced | Install |
|------------|----------------|---------|
| [`gh` CLI](https://cli.github.com) | `/ark-consult`, `/ark-onboard` (GitHub-Issues task management) | `brew install gh` + `gh auth login` |
| [mattpocock/skills](https://github.com/mattpocock/skills) | `/ark-consult` (issue machinery + a routing destination) | `npx skills@latest add mattpocock/skills` + `/setup-matt-pocock-skills` |
| [NotebookLM CLI](https://github.com/nichochar/notebooklm-cli) | `/notebooklm-vault` (synthesized recall) | `pipx install notebooklm-cli` + `notebooklm login` |

Routing destinations for `/ark-consult` (install per your workflow): superpowers, gstack, oh-my-claudecode.

## Available Skills

| Skill | Core | Description |
|-------|------|-------------|
| `/ark-consult` | Workflow consultant | Stateless planning phase for any non-trivial task: triages, recommends exactly ONE execution ecosystem from a routing matrix, files a GitHub epic as the plan of record, and hands off. |
| `/vault` | Conventions | Write-side OKF knowledge ops for the bundle at `vault/`: end-of-session distillation, document ingestion, `log.md` append, index regen. |
| `/notebooklm-vault` | Conventions | Synthesized-recall backend: syncs the OKF bundle to NotebookLM and answers factual/historical queries. |
| `/ark-onboard` | Conventions | Interactive setup wizard: OKF bundle init, label bootstrap, mattpocock setup, CLAUDE.md rows. |
| `/ark-health` | Conventions | Diagnostic scorecard for the v2 invariants. |
| `/ark-update` | Conventions | Version-driven migration framework; converges downstream projects onto the current target profile (execution deferred per-project). |

## Skill Documentation

**`/ark-consult`** — Given a non-trivial task, triages it, asks at most two clarifying questions, and recommends exactly ONE execution ecosystem (gstack / superpowers / mattpocock / oh-my-claudecode) from a 12-archetype routing matrix with reasoning. Files a GitHub epic (epic + component + priority labels; children as task-list checkboxes, optionally cut via mattpocock `/to-tickets`), then invokes the chosen ecosystem's entry skill and stops. Never chains two ecosystems, never orchestrates post-handoff, never writes local state — the GitHub epic is the only state (resume = `gh issue view <epic>`).

**`/vault`** — Write-side knowledge operations for the OKF bundle: distills durable insights from a session (knowledge only — no session logs, no task tracking), ingests external documents, appends work-record lines to `log.md`, and always finishes by regenerating the index and passing `okf_lint.py`. Reading the vault is script-based (`okf_cli.py`) or via NotebookLM.

**`/notebooklm-vault`** — Bridges the OKF bundle with Google NotebookLM for synthesized cross-session recall. Sub-commands: `setup`, `ask`, `session-continue` (resumes from the `log.md` tail + the referenced GitHub epic), `bootstrap`, `audio`, `report`, `conflict-check`, `status`.

**`/ark-onboard`** — Interactive setup wizard converging a project onto the v2 conventions: OKF bundle init, GitHub-Issues label taxonomy + `docs/agents/` conventions, mattpocock setup, and CLAUDE.md rows. Handles greenfield, migration, repair, and healthy states. Exempt from context-discovery.

**`/ark-health`** — Runs the v2 invariant checks across five areas (routing-destination ecosystems, the 6-skill roster, OKF conventions, GitHub-Issues conventions, NotebookLM recall) and produces a scored scorecard with fixes. No auto-fix — points to `/ark-onboard` for remediation. Exempt from context-discovery.

**`/ark-update`** — Version-driven migration framework. Converges downstream projects onto the current target profile; its v2.0.0 profile declares two pending migrations (OKF conversion + GitHub-Issues adoption), executed per-project later. Distinct from `/ark-onboard` repair (failure-driven).

## Context-Discovery Pattern

Every skill uses **context-discovery** — no skill contains hardcoded project names or vault paths. When invoked, each skill reads the project's `CLAUDE.md`, follows the monorepo hub link if present, and extracts the project name, vault root, and project docs path. See `CLAUDE.md` in this repo for the full procedure.

**Exemption:** `/ark-onboard` and `/ark-health` are exempt — they must work when CLAUDE.md is missing, broken, or incomplete.

## Architecture

```
ark-skills (Claude Code plugin)
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata
│   └── marketplace.json      # Repo-level plugin registry
├── skills/                   # 6 shared skills
│   ↓ context-discovery
│   Project CLAUDE.md → vault root, project docs path
├── docs/agents/              # GitHub-Issues conventions (issue-tracker, triage-labels, domain)
└── vault/                    # OKF v0.1 knowledge bundle (_meta/okf tooling, index.md, log.md)
        ↓
   NotebookLM sync (synthesized recall)
   GitHub Issues (work record)
```

## New Project Onboarding

Run `/ark-onboard` for interactive guided setup. It detects your project state and walks you through the appropriate path (greenfield / migration / repair / healthy).

## Repository Structure

| Directory | Purpose |
|-----------|---------|
| `.claude-plugin/` | Plugin manifest (plugin.json, marketplace.json) |
| `skills/` | 6 shared skill definitions (SKILL.md files) |
| `docs/agents/` | GitHub-Issues conventions (issue-tracker, triage-labels, domain) |
| `docs/` | Design specs, plans, historical archives |
| `vault/` | The plugin's own OKF v0.1 knowledge bundle |

## Development

### Modifying Skills

1. Edit `skills/<skill-name>/SKILL.md`.
2. Test by invoking the skill from a project.
3. Verify no hardcoded references: `rg -n "ArkPoly|ArkSignal|trading-signal-ai|CT100|192\.168" skills/`.
4. Commit and push (bump `VERSION`, `plugin.json`, `marketplace.json`, `CHANGELOG.md` in the same commit).

### Verification Checks

```bash
# Exactly 6 skills
find skills -mindepth 1 -maxdepth 1 -type d ! -name shared | wc -l  # → 6

# OKF bundle lints clean
python3 vault/_meta/okf/okf_lint.py --quiet; echo $?  # → 0

# Every skill references context-discovery (except the two exempt onboarding skills)
rg -L "Project Discovery|CLAUDE.md|Context-Discovery" skills/*/SKILL.md
```
