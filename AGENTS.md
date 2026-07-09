<!-- Generated: 2026-04-13 | Updated: 2026-04-13 -->

# ark-skills

## Purpose

Claude Code plugin that centralizes 6 shared skills for ArkNode projects across two co-equal cores: a workflow consultant (`/ark-consult`) and a conventions layer (`/vault`, `/notebooklm-vault`, `/ark-onboard`, `/ark-health`, `/ark-update`) for OKF knowledge bundles + GitHub-Issues task management. Installed user-scoped via `/plugin install ark-skills@ark-skills`, so every skill in `skills/` is available in every project on the machine.

The distinguishing design choice is **context-discovery**: no skill hardcodes project names, vault paths, or task prefixes. Each skill reads the active project's `CLAUDE.md` at runtime to find those values. See the top-level `CLAUDE.md` in this repo for the full pattern.

## Key Files

| File | Description |
|------|-------------|
| `CLAUDE.md` | Project instructions + context-discovery pattern. Authoritative source — read this first. |
| `README.md` | Install instructions, optional dependencies (`gh` CLI, mattpocock/skills, NotebookLM CLI), full skill catalog. |
| `CHANGELOG.md` | Release history. Keep-a-Changelog format, bumped every push to master. |
| `TODO.md` | Open work items. |
| `VERSION` | Plain semver string. Must stay in sync with `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. |
| `.gitignore` | Git exclusions. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `skills/` | The 6 skills published by this plugin. Each subdirectory has its own `SKILL.md`. See `skills/AGENTS.md`. |
| `docs/` | Plugin documentation (onboarding guide, vault audit, superpowers plans/specs). See `docs/AGENTS.md`. |
| `vault/` | **Obsidian vault — user content, not code.** Do not modify programmatically except through the plugin's own vault skills. |
| `.claude-plugin/` | Plugin manifest (`plugin.json`) and marketplace descriptor (`marketplace.json`). Bump version here on every release. |
| `.claude/` | Local Claude Code settings (`settings.json`). |
| `.omc/` | Transient OMC session state — do not commit changes here or depend on paths inside. |
| `.context/` | Session pointers (e.g. `codex-session-id`). Transient. |

## For AI Agents

### Working In This Directory

- **Never invent a project name, vault path, or task prefix inside a skill.** All such values come from context-discovery against the consuming project's `CLAUDE.md`. If you need a value a CLAUDE.md doesn't provide, the skill should fail loudly with a message telling the user what field to add.
- **Version bumps are non-negotiable on every push to master.** Update all four in one commit: `VERSION`, `.claude-plugin/plugin.json` (`version` field), `.claude-plugin/marketplace.json` (`plugins[0].version`), and add a `CHANGELOG.md` entry.
- **Do not programmatically modify `vault/`.** That is user-authored content; the plugin's vault skills operate on the consuming project's vault, not this repo's vault.
- The top-level `CLAUDE.md` defines vault retrieval: NotebookLM (synthesized recall) → `okf_cli.py` (navigation/full-text). New vault-reading skills must follow this order and log fallbacks.
- `/ark-onboard` and `/ark-health` are explicitly exempt from context-discovery — they must work when `CLAUDE.md` is missing or broken. Preserve that exemption.

### Testing Requirements

There is no programmatic test suite for this plugin — skills are instruction files, not executable code. Verification is behavioral:

1. Read the modified `SKILL.md` end-to-end and confirm the instructions are internally consistent.
2. Run the skill via `/skill-name` in a project that has a real `CLAUDE.md` and vault, and confirm it produces the expected artifacts.
3. For skills with executable helpers in `scripts/`, run those directly and check output.

### Common Patterns

- **Skills are markdown files with YAML frontmatter.** The `description` field is the trigger string — it must include both "when to use" and "when NOT to use" for the router to pick correctly.
- Every skill that touches a project's vault starts with a **Project Discovery** section that invokes the context-discovery pattern.
- Helper scripts live in `skills/<name>/scripts/`, reference docs in `skills/<name>/references/`, and pre-scripted workflows in `skills/<name>/chains/`.

## Dependencies

### External

The plugin itself has no hard runtime dependencies. Individual skills optionally use:

- **`gh` CLI** — GitHub-Issues task management (`/ark-consult`, `/ark-onboard`).
- **mattpocock/skills** — issue machinery (`/to-tickets`, `/triage`) and a routing destination for `/ark-consult`.
- **NotebookLM CLI** (`pipx install notebooklm-cli`) — synthesized recall, `/notebooklm-vault`.

<!-- MANUAL: Manually added notes below this line are preserved on regeneration. -->
