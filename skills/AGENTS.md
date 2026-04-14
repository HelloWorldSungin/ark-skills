<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-13 | Updated: 2026-04-13 -->

# skills

## Purpose

The 18 Claude Code skills published by this plugin. Each subdirectory is one skill; each skill has a `SKILL.md` whose YAML frontmatter defines the trigger string that makes Claude Code invoke it. Skills fall into five categories: workflow orchestration, core workflows, task automation, onboarding, and vault maintenance.

## Subdirectories

### Workflow Orchestration

| Directory | Purpose |
|-----------|---------|
| `ark-workflow/` | Task triage and skill chain orchestration — entry point for all non-trivial work. |
| `ark-context-warmup/` | Context loader that runs as step 0 of every `/ark-workflow` chain. Also invokable standalone. |

### Core

| Directory | Purpose |
|-----------|---------|
| `ark-code-review/` | Multi-agent code review with fan-out architecture (epic/plan/full modes). |
| `codebase-maintenance/` | Repo cleanup, vault doc sync, skill health sweep before merge. |
| `notebooklm-vault/` | NotebookLM-backed persistent context (bootstrap, ask, session-continue, conflict-check). |

### Task Automation

| Directory | Purpose |
|-----------|---------|
| `ark-tasknotes/` | Agent-driven task creation and status via the tasknotes MCP or direct markdown write. |

### Onboarding & Health

| Directory | Purpose |
|-----------|---------|
| `ark-onboard/` | Interactive setup wizard — greenfield, vault migration, partial repair. **Exempt from context-discovery.** |
| `ark-health/` | 19-check diagnostic scorecard for the Ark ecosystem. **Exempt from context-discovery.** |

### Vault Maintenance

| Directory | Purpose |
|-----------|---------|
| `wiki-query/` | Tiered vault retrieval (T1 NotebookLM → T2 MemPalace → T3 Obsidian-CLI → T4 index.md). |
| `wiki-lint/` | Audit vault health (links, frontmatter, tags, index staleness). |
| `wiki-status/` | Vault statistics and page-count insights. |
| `wiki-update/` | End-of-session handoff: session log, TaskNote sync, compiled insights, index regen. |
| `wiki-setup/` | Initialize a new Ark vault with the standard structure and artifacts. |
| `wiki-ingest/` | Distill source documents into vault pages. |
| `tag-taxonomy/` | Validate and normalize tags against `_meta/taxonomy.md`. |
| `cross-linker/` | Discover and add missing wikilinks between pages. |
| `claude-history-ingest/` | Mine Claude conversations into compiled insights via MemPalace. Ships a hook installer. |
| `data-ingest/` | Process logs, transcripts, chat exports into vault pages. |

### Shared

| Directory | Purpose |
|-----------|---------|
| `shared/` | Cross-skill utilities. Currently: `mine-vault.sh` (first-time MemPalace vault index). |

## For AI Agents

### SKILL.md Anatomy

Every skill directory must contain a `SKILL.md` with this shape:

```markdown
---
name: skill-name
description: One-sentence trigger. Include "Use when…" and "Do NOT use for…" so the router picks correctly.
---

# Human-readable title

## Project Discovery          # (omit for ark-onboard / ark-health)
{context-discovery per CLAUDE.md}

## Workflow
Step 1 …
Step 2 …
```

The `description` is the only text Claude Code sees when deciding whether to invoke the skill. Write it like marketing copy for the trigger conditions, not a summary of what the skill does internally.

### Subdirectory Conventions

Within a skill directory:

| Subdirectory | Contains |
|--------------|----------|
| `scripts/` | Executable helpers invoked by the skill (bash/python). Keep them idempotent. |
| `references/` | Long reference tables or prompts the skill links to instead of inlining. |
| `chains/` | Pre-scripted skill sequences (used by `ark-workflow`). |
| `hooks/` | Hook installers (used by `claude-history-ingest`). |
| `fixtures/` | Sample inputs for manual testing. |

Python `__pycache__/` is gitignored and must never be committed.

### Adding a New Skill

1. Create `skills/<kebab-name>/SKILL.md` with the frontmatter shown above.
2. Register it in the top-level `README.md` "Available Skills" table and in `CLAUDE.md`'s "Available Skills" section.
3. Bump `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and add a `CHANGELOG.md` entry in the same commit.
4. If the skill reads the vault, follow the four-tier retrieval order documented in the root `CLAUDE.md` and log any unavailable tier before falling back.

### Modifying an Existing Skill

- **Re-read the full `SKILL.md` before editing** — these files are long and context-sensitive. Edits that break the frontmatter's `description` field silently change trigger behavior.
- If you change a trigger string, verify no other skill's description references the same phrases (grep `skills/**/SKILL.md`).
- If you change a helper in `scripts/`, test it directly before relying on the skill to exercise it.

### Common Patterns

- **Early exits for missing prerequisites.** Skills that depend on a vault check `HAS_VAULT` and bail out with an actionable message (e.g. "Run `/wiki-setup` first") rather than proceeding with half-state.
- **Four-tier retrieval with logged fallbacks.** Never silently drop to a lower tier — tell the user which tier failed and why.
- **Context-discovery over hardcoded paths.** If you find yourself typing a specific vault path or task prefix inside a skill file, stop and route it through `CLAUDE.md` instead.

## Dependencies

### Internal

- All skills read the top-level `CLAUDE.md` for the context-discovery pattern and vault retrieval tier definitions.
- Several skills reference `skills/shared/mine-vault.sh` for MemPalace initialization.

### External

See the parent `AGENTS.md` for the optional external dependency matrix (MemPalace, NotebookLM CLI, Obsidian CLI, tasknotes MCP).

<!-- MANUAL: -->
