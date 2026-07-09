<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-13 | Updated: 2026-07-06 -->

# skills

## Purpose

The Claude Code skills published by this plugin. Each subdirectory is one skill; each skill has a `SKILL.md` whose YAML frontmatter defines the trigger string that makes Claude Code invoke it. As of the v2.0.0 restructure, 6 skills remain, falling into two categories: core (workflow consultant + conventions layer) and onboarding & health.

## Subdirectories

### Core

| Directory | Purpose |
|-----------|---------|
| `ark-consult/` | Stateless workflow consultant — the planning phase for any non-trivial task. Recommends exactly one execution ecosystem (gstack / superpowers / mattpocock / oh-my-claudecode) and hands off. Replaces the retired chain-orchestrator skill. |
| `vault/` | Write-side knowledge operations for the OKF vault bundle at `vault/` — durable insights, research, decisions, reference pages. Not session logs, not task tracking. |
| `notebooklm-vault/` | NotebookLM-backed persistent context (bootstrap, ask, session-continue, conflict-check). |

### Onboarding & Health

| Directory | Purpose |
|-----------|---------|
| `ark-onboard/` | Interactive setup wizard — greenfield, vault migration, partial repair. **Exempt from context-discovery.** |
| `ark-health/` | Diagnostic scorecard for the Ark ecosystem. **Exempt from context-discovery.** |
| `ark-update/` | Version-driven migration framework. Converges downstream projects to the current ark-skills target profile via additive replays + pending destructive migrations. Distinct from `/ark-onboard` repair (failure-driven). |

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
| `fixtures/` | Sample inputs for manual testing. |

Python `__pycache__/` is gitignored and must never be committed.

### Adding a New Skill

1. Create `skills/<kebab-name>/SKILL.md` with the frontmatter shown above.
2. Register it in the top-level `README.md` "Available Skills" table and in `CLAUDE.md`'s "Available Skills" section.
3. Bump `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and add a `CHANGELOG.md` entry in the same commit.
4. If the skill reads the vault, follow the retrieval order documented in the root `CLAUDE.md` and log any unavailable tier before falling back.

### Modifying an Existing Skill

- **Re-read the full `SKILL.md` before editing** — these files are long and context-sensitive. Edits that break the frontmatter's `description` field silently change trigger behavior.
- If you change a trigger string, verify no other skill's description references the same phrases (grep `skills/**/SKILL.md`).
- If you change a helper in `scripts/`, test it directly before relying on the skill to exercise it.

### Common Patterns

- **Early exits for missing prerequisites.** Skills that depend on a vault check `HAS_VAULT` and bail out with an actionable message (e.g. "Run `/ark-onboard` first") rather than proceeding with half-state.
- **Retrieval with logged fallbacks.** Never silently drop to a lower tier — tell the user which tier failed and why.
- **Context-discovery over hardcoded paths.** If you find yourself typing a specific vault path or task prefix inside a skill file, stop and route it through `CLAUDE.md` instead.

### Composition Guardrails

Top-level orchestrators may sequence other orchestrating skills only through explicit chain steps, with conditions resolved before presentation. Do not rely on implicit nested routing. Avoid compound-to-compound calls unless the target has a bounded mode/argument and a documented handback point.

`ark-consult` is the only remaining top-level orchestrator; it is explicitly prohibited from any post-handoff orchestration (see `skills/ark-consult/SKILL.md`) — it recommends one ecosystem, files the plan, and hands off, with no further steps of its own. There are currently no compound-to-compound calls between surviving skills to guard against; revisit this section if that changes.

## Dependencies

### Internal

- All skills read the top-level `CLAUDE.md` for the context-discovery pattern and vault retrieval definitions.

### External

Optional integrations: the `gh` CLI (GitHub Issues task management), the `notebooklm` CLI (synthesized recall), and mattpocock/skills (`/to-tickets`, `/triage`). See the parent `AGENTS.md` for details.

<!-- MANUAL: -->
