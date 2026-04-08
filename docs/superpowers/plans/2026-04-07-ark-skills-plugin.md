# Ark Skills Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Claude Code plugin that provides 14 shared skills (3 generalized, 1 new, 10 adapted from obsidian-wiki) available to all Ark projects via user-scoped skill distribution.

**Architecture:** This repo (`create-ark-skills`) is a Claude Code plugin. Skills use a context-discovery pattern — each reads the active project's `CLAUDE.md` at runtime to find vault paths, task prefixes, and deployment targets. No hardcoded project references. obsidian-wiki skills are copied and adapted to work with Ark vault conventions (domain-specific folders, Ark frontmatter schema, `index.md`/`summary:`/`taxonomy.md` artifacts from the vault restructuring).

**Tech Stack:** Claude Code plugin (markdown skills), TypeScript (linear-updater refactor), Python (index generation scripts in vaults), Obsidian (vault structure), tasknotes MCP (HTTP endpoint in Obsidian plugin)

**Spec:** `docs/superpowers/specs/2026-04-07-ark-skills-plugin-design.md`

**Constraints:**
- All skills must use context-discovery from CLAUDE.md — zero hardcoded project names, vault paths, or task prefixes
- Vault TaskNotes structure, frontmatter schema, and Linear sync: ZERO changes
- obsidian-wiki `.env`, `.manifest.json`, `log.md`, `provenance:` conventions are NOT used — replaced by Ark conventions
- All 10 obsidian-wiki skills are copies with adaptation (Codex review found cross-linker also depends on `.env` and `log.md`)

---

## Phase 0: Plugin Scaffolding

### Task 0: Create Plugin Directory Structure

**Files:**
- Create: `skills/` (directory)
- Create: `skills/ark-code-review/` (directory)
- Create: `skills/codebase-maintenance/` (directory)
- Create: `skills/codebase-maintenance/references/` (directory)
- Create: `skills/notebooklm-vault/` (directory)
- Create: `skills/notebooklm-vault/scripts/` (directory)
- Create: `skills/ark-tasknotes/` (directory)
- Create: `skills/wiki-setup/` (directory)
- Create: `skills/wiki-ingest/` (directory)
- Create: `skills/wiki-update/` (directory)
- Create: `skills/wiki-query/` (directory)
- Create: `skills/wiki-lint/` (directory)
- Create: `skills/wiki-status/` (directory)
- Create: `skills/cross-linker/` (directory)
- Create: `skills/tag-taxonomy/` (directory)
- Create: `skills/claude-history-ingest/` (directory)
- Create: `skills/data-ingest/` (directory)

- [ ] **Step 1: Create all skill directories**

```bash
mkdir -p skills/{ark-code-review,codebase-maintenance/references,notebooklm-vault/scripts,ark-tasknotes,wiki-setup,wiki-ingest,wiki-update,wiki-query,wiki-lint,wiki-status,cross-linker,tag-taxonomy,claude-history-ingest,data-ingest}
```

- [ ] **Step 2: Verify structure**

```bash
find skills -type d | sort
```

Expected: 16 directories (skills/ + 14 skill dirs + 2 subdirs for references/ and scripts/).

- [ ] **Step 3: Commit**

```bash
git add skills/
git commit -m "feat: create plugin skill directory structure"
```

---

### Task 1: Write Plugin CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

This is the plugin-level instruction file. It defines the context-discovery pattern that all skills reference.

- [ ] **Step 1: Write CLAUDE.md**

Write to `CLAUDE.md`:

```markdown
# Ark Skills Plugin

Shared skills for all ArkNode projects. This repo is registered as a Claude Code plugin — all skills in `skills/` are user-scoped and available to every project.

## Context-Discovery Pattern

Every skill in this plugin uses **context-discovery** to find project-specific values at runtime. No skill contains hardcoded project names, vault paths, or task prefixes.

### How It Works

When a skill says "Run Project Discovery," follow this procedure:

1. Read the `CLAUDE.md` in the current working directory
2. If it's a monorepo hub (contains a "Projects" table linking to sub-project CLAUDEs), follow the link for the active project based on your current working directory
3. Extract these fields from the most specific CLAUDE.md:

| Field | Where to Find | Example |
|-------|--------------|---------|
| Project name | Header or table | `trading-signal-ai` |
| Task prefix | "Task Management" row, includes trailing dash | `ArkSignal-` |
| Vault root | Parent of project docs and TaskNotes | `vault/` |
| Project docs path | "Obsidian Vault" row — project-specific content | `vault/Trading-Signal-AI/` |
| TaskNotes path | "Task Management" row — sibling of project docs, NOT nested under it | `vault/TaskNotes/` |
| Counter file | `{tasknotes_path}/meta/{task_prefix}counter` — prefix includes dash | `vault/TaskNotes/meta/ArkSignal-counter` |
| Deployment targets | Infrastructure section | CT100, CT110, CT120 (if defined) |
| NotebookLM config | `.notebooklm/config.json` in **project repo** (tracked config) | notebook keys, persona |

**Path layout:** `vault/` is the root containing BOTH `vault/{ProjectDocs}/` and `vault/TaskNotes/` as siblings:
```
vault/                          # {vault_root}
├── Trading-Signal-AI/          # {project_docs_path} — project knowledge
│   ├── Session-Logs/
│   ├── Research/
│   └── ...
└── TaskNotes/                  # {tasknotes_path} — task tracking (sibling, NOT nested)
    ├── Tasks/
    ├── Archive/
    └── meta/ArkSignal-counter
```

**Counter file convention:** Task prefix always includes the trailing dash (e.g., `ArkSignal-`). Counter filename is `{task_prefix}counter` → `ArkSignal-counter`. No double dash.

4. If a required field is missing, tell the user: "CLAUDE.md is missing [field]. Add it before running this skill."

### Vault Artifacts (Post-Restructuring)

All Ark vaults have these standard artifacts from the vault restructuring:

| Artifact | Path | Purpose |
|----------|------|---------|
| Vault schema | `_meta/vault-schema.md` | Self-documenting vault structure |
| Tag taxonomy | `_meta/taxonomy.md` | Canonical tag vocabulary |
| Index generator | `_meta/generate-index.py` | Regenerates `index.md` |
| Machine index | `index.md` | Flat catalog of all pages with summaries |
| Summaries | `summary:` frontmatter | <=200 char description on every page |

### Ark Frontmatter Schema

Ark vaults use `type:` (not `category:`), `source-sessions:` and `source-tasks:` (not `sources:`). They do NOT use `provenance:` markers. See each vault's `_meta/vault-schema.md` for the complete frontmatter spec.

## Available Skills

### Core (generalized from existing)
- `/ark-code-review` — Multi-agent code review with fan-out architecture
- `/codebase-maintenance` — Repo cleanup, vault sync, skill health
- `/notebooklm-vault` — NotebookLM vault context and sync

### Task Automation
- `/ark-tasknotes` — Agent-driven task creation via tasknotes MCP

### Vault Maintenance (adapted from obsidian-wiki)
- `/wiki-query` — Query vault knowledge with tiered retrieval
- `/wiki-lint` — Audit vault health (links, frontmatter, tags, index)
- `/wiki-status` — Vault statistics and insights
- `/wiki-update` — Sync project knowledge into vault, regenerate index
- `/wiki-setup` — Initialize new Ark vault with standard structure
- `/wiki-ingest` — Distill documents into vault pages
- `/tag-taxonomy` — Validate and normalize tags against taxonomy
- `/cross-linker` — Discover and add missing wikilinks
- `/claude-history-ingest` — Mine Claude conversations into compiled insights
- `/data-ingest` — Process logs, transcripts, exports into vault pages
```

- [ ] **Step 2: Verify no hardcoded project references**

```bash
grep -i "arksignal\|arkpoly\|trading-signal-ai\|arknode-poly\|CT100\|CT110\|CT120\|192\.168" CLAUDE.md
```

Expected: Only appears in the "Example" column of the table, not in instructions.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add plugin CLAUDE.md with context-discovery pattern"
```

---

## Phase 1: Skill Generalization

### Task 2: Generalize ark-code-review

**Files:**
- Read: `ArkNode-Poly/.claude/skills/ark-code-review/SKILL.md` (638 lines, base version)
- Read: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/ark-code-review/SKILL.md` (770 lines, extended version)
- Create: `skills/ark-code-review/SKILL.md`

The Poly version is the simpler base. The AI version adds infrastructure-specific follow-up actions (CT100/CT110/CT120 deployment checks). The generalized version keeps the multi-agent orchestration pattern but replaces all project-specific references with context-discovery.

- [ ] **Step 1: Read both source skills**

Read the full content of both SKILL.md files to understand the differences.

- [ ] **Step 2: Copy Poly version as base**

```bash
cp ArkNode-Poly/.claude/skills/ark-code-review/SKILL.md skills/ark-code-review/SKILL.md
```

- [ ] **Step 3: Add context-discovery preamble**

Add this section at the very top of `skills/ark-code-review/SKILL.md`, before the existing content:

```markdown
## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, task prefix, vault path, TaskNotes path
2. Read the vault's `_meta/vault-schema.md` to understand the vault structure
3. Use discovered values throughout — never hardcode project names or paths
```

- [ ] **Step 4: Replace hardcoded vault paths**

Search and replace in `skills/ark-code-review/SKILL.md`:
- Replace `vault/TaskNotes/Tasks/Epic/*.md` with `{tasknotes_path}/Tasks/Epic/*.md` (TaskNotes is a sibling of project docs, NOT nested under vault_path)
- Replace any `vault/ArkNode-Poly/` references with `{project_docs_path}/`
- Replace `ArkPoly-` prefix references with `{task_prefix}` (from Project Discovery)
- Replace ALL literal `master` in git commands (e.g., `git diff master...HEAD`, `git log master..HEAD`) with a dynamic base branch detection:
  ```markdown
  Detect the base branch: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'` (fallback to `master`)
  ```
  This applies to every `git diff`, `git log`, and `git merge` command in the skill.

- [ ] **Step 5: Make deployment follow-ups conditional**

Find the section about follow-up actions after code review. Add this conditional wrapper:

```markdown
### Post-Review Actions

**If the project's CLAUDE.md defines deployment targets:**
- Check deployed commit drift on each target
- Verify service health endpoints
- Run staging smoke tests

**If no deployment targets are defined:** Skip deployment checks.
```

- [ ] **Step 6: Generalize test path patterns**

Replace any hardcoded test patterns like `tests/test_<module>.py` with:

```markdown
### Test Discovery
Discover the project's test structure by scanning for:
- `tests/` directory structure
- Test runner config (pytest.ini, jest.config.*, vitest.config.*)
- Test naming patterns used in the project
```

- [ ] **Step 7: Verify no hardcoded references remain**

```bash
grep -in "arkpoly\|arksignal\|ArkNode-Poly\|trading-signal-ai\|CT100\|CT110\|CT120\|192\.168\|polymarket\|hyperliquid" skills/ark-code-review/SKILL.md
```

Expected: Zero matches.

- [ ] **Step 8: Commit**

```bash
git add skills/ark-code-review/SKILL.md
git commit -m "feat: generalize ark-code-review skill with context-discovery"
```

---

### Task 3: Generalize codebase-maintenance

**Files:**
- Read: `ArkNode-Poly/.claude/skills/codebase-maintenance/SKILL.md` (131 lines)
- Read: `ArkNode-Poly/.claude/skills/codebase-maintenance/references/cleanup-checklist.md`
- Read: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/codebase-maintenance/SKILL.md` (192 lines)
- Create: `skills/codebase-maintenance/SKILL.md`
- Create: `skills/codebase-maintenance/references/cleanup-checklist.md`

- [ ] **Step 1: Read both source skills and reference files**

Read all source files to understand differences. The AI version has 6 workflow files and infrastructure-specific items (CT100/CT110/CT120, dashboard sync, deploy script sync). The Poly version is simpler.

- [ ] **Step 2: Copy Poly version as base**

```bash
cp ArkNode-Poly/.claude/skills/codebase-maintenance/SKILL.md skills/codebase-maintenance/SKILL.md
cp ArkNode-Poly/.claude/skills/codebase-maintenance/references/cleanup-checklist.md skills/codebase-maintenance/references/cleanup-checklist.md
# Copy ALL workflow files — SKILL.md routes to these, they MUST exist
mkdir -p skills/codebase-maintenance/workflows
cp ArkNode-Poly/.claude/skills/codebase-maintenance/workflows/cleanup-code.md skills/codebase-maintenance/workflows/ 2>/dev/null || true
cp ArkNode-Poly/.claude/skills/codebase-maintenance/workflows/sync-vault.md skills/codebase-maintenance/workflows/ 2>/dev/null || true
cp ArkNode-Poly/.claude/skills/codebase-maintenance/workflows/sync-skills.md skills/codebase-maintenance/workflows/ 2>/dev/null || true
cp ArkNode-Poly/.claude/skills/codebase-maintenance/workflows/full-cleanup.md skills/codebase-maintenance/workflows/ 2>/dev/null || true
# If Poly version doesn't have some workflows, check AI version
for wf in cleanup-code sync-vault sync-skills full-cleanup; do
  [ ! -f "skills/codebase-maintenance/workflows/${wf}.md" ] && \
    cp "ArkNode-AI/projects/trading-signal-ai/.claude/skills/codebase-maintenance/workflows/${wf}.md" "skills/codebase-maintenance/workflows/" 2>/dev/null || true
done
```

Verify all required workflow files exist:
```bash
ls skills/codebase-maintenance/workflows/
```
Expected: `cleanup-code.md`, `sync-vault.md`, `sync-skills.md`, `full-cleanup.md`

- [ ] **Step 3: Add context-discovery preamble**

Add at the top of `skills/codebase-maintenance/SKILL.md`:

```markdown
## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, vault path, deployment targets (if any), code scan paths
2. If CLAUDE.md defines deployment targets, include infrastructure audit steps
3. If CLAUDE.md defines a monitoring dashboard, include dashboard sync steps
```

- [ ] **Step 4: Replace hardcoded references**

In `skills/codebase-maintenance/SKILL.md`:
- Replace `vault/ArkNode-Poly/` with `{vault_path}/`
- Replace `vault/ArkNode-Poly/Session-Logs/` with `{vault_path}/Session-Logs/`
- Replace `~/.superset/vaults/ArkNode-Poly/` with the discovered vault location
- Replace hardcoded code scan paths (`arknode-core/`, `agents/`, `orchestrator/`) with: "Scan directories listed in the project's CLAUDE.md or discovered from the project structure"

In `skills/codebase-maintenance/references/cleanup-checklist.md`:
- Remove any CT100/CT110/CT120 specific items
- Make infrastructure items conditional

- [ ] **Step 5: Add vault maintenance step (post-restructuring)**

Add this section to the vault sync workflow:

```markdown
### Vault Maintenance (after any vault changes)

1. Regenerate `index.md`:
   ```bash
   cd {vault_path} && python3 _meta/generate-index.py
   ```
2. Validate tags against `_meta/taxonomy.md`
3. Check for broken wikilinks (quick lint pass)
4. Commit vault changes:
   ```bash
   cd {vault_path} && git add -A && git commit -m "chore: vault maintenance sync"
   ```
```

- [ ] **Step 6: Verify no hardcoded references**

```bash
grep -rn "arkpoly\|arksignal\|ArkNode-Poly\|trading-signal-ai\|CT100\|CT110\|CT120\|192\.168" skills/codebase-maintenance/
```

Expected: Zero matches.

- [ ] **Step 7: Commit**

```bash
git add skills/codebase-maintenance/
git commit -m "feat: generalize codebase-maintenance skill with context-discovery"
```

---

### Task 4: Generalize notebooklm-vault

**Files:**
- Read: `ArkNode-Poly/.claude/skills/notebooklm-vault/SKILL.md` (435 lines)
- Read: `ArkNode-Poly/.claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh`
- Read: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/notebooklm-vault/SKILL.md` (525 lines)
- Create: `skills/notebooklm-vault/SKILL.md`
- Create: `skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh`

- [ ] **Step 1: Read both source skills and sync scripts**

Read all source files. Key differences: AI version has dual notebooks (trading + infra), Poly has single notebook. AI version has `--sessions-only` and `--infra-only` flags.

- [ ] **Step 2: Copy Poly version as base**

```bash
cp ArkNode-Poly/.claude/skills/notebooklm-vault/SKILL.md skills/notebooklm-vault/SKILL.md
cp ArkNode-Poly/.claude/skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh
```

- [ ] **Step 3: Add context-discovery preamble**

Add at the top of `skills/notebooklm-vault/SKILL.md`:

```markdown
## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:
1. Read the project's CLAUDE.md to find: project name, vault root, project docs path
2. Read the **project repo's** `.notebooklm/config.json` for notebook configuration (this is the tracked, authoritative source). The vault repo holds `.notebooklm/sync-state.json` (runtime state, not config).
3. Determine notebook structure: single notebook (one key) or multi-notebook (trading + infra)
4. For tiered retrieval: read vault's `index.md` and use `summary:` fields to scan before reading full pages
```

- [ ] **Step 4: Replace hardcoded references**

In `skills/notebooklm-vault/SKILL.md`:
- Replace `"ArkNode - Polymarket AI Bot"` with: "the notebook name from `.notebooklm/config.json`"
- Replace `vault/ArkNode-Poly/` with `{vault_path}/`
- Replace `~/.superset/vaults/ArkNode-Poly/` with the discovered vault location
- Replace `ArkPoly-` with `{task_prefix}`
- Replace `vault/TaskNotes/meta/ArkPoly-counter` with `{vault_path}/TaskNotes/meta/{task_prefix}counter`

- [ ] **Step 5: Add tiered retrieval section**

Add this section to the vault querying workflow:

```markdown
### Tiered Retrieval (Post-Restructuring)

When querying vault knowledge:
1. **Tier 1 — Index scan:** Read `index.md` to find relevant pages by category and summary
2. **Tier 2 — Summary scan:** Read `summary:` frontmatter of candidate pages (cheap, <=200 chars each)
3. **Tier 3 — Full read:** Only open full page content for the top 3-5 most relevant candidates
4. **Navigation context:** Read `_meta/vault-schema.md` to understand folder structure before exploring
```

- [ ] **Step 6: Make multi-notebook logic conditional**

Wrap dual-notebook sections with:

```markdown
### Notebook Querying

Read `.notebooklm/config.json` to determine notebook structure:
- **Single notebook:** Query the one configured notebook
- **Multiple notebooks:** Query each notebook, merge results, note which notebook each answer came from
```

- [ ] **Step 7: Parameterize sync script**

In `skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh`:
- Replace hardcoded notebook names with config-driven lookups
- Replace hardcoded vault paths with environment variable reads
- Make `--sessions-only` and `--infra-only` flags conditional on config having those notebook keys

- [ ] **Step 8: Verify no hardcoded references**

```bash
grep -rn "arkpoly\|arksignal\|ArkNode-Poly\|trading-signal-ai\|Polymarket\|CT100\|CT110\|CT120\|192\.168" skills/notebooklm-vault/
```

Expected: Zero matches.

- [ ] **Step 9: Commit**

```bash
git add skills/notebooklm-vault/
git commit -m "feat: generalize notebooklm-vault skill with context-discovery and tiered retrieval"
```

---

## Phase 2a: Wiki Skills — Light Adaptation

All skills in this phase follow the same adaptation pattern:
1. Read the upstream skill from `obsidian-wiki/.skills/{name}/SKILL.md`
2. Replace `.env`/`OBSIDIAN_VAULT_PATH` with context-discovery from CLAUDE.md
3. Replace `.manifest.json` references with "not used" or remove
4. Replace `log.md` logging with commit messages
5. Leverage new vault artifacts: `index.md`, `summary:`, `_meta/vault-schema.md`, `_meta/taxonomy.md`
6. Use Ark frontmatter (`type:`, `source-sessions:`) instead of wiki frontmatter (`category:`, `sources:`, `provenance:`)

### Task 5: Adapt wiki-query

**Files:**
- Read: `obsidian-wiki/.skills/wiki-query/SKILL.md` (~95 lines)
- Create: `skills/wiki-query/SKILL.md`

- [ ] **Step 1: Read upstream skill**

Read `obsidian-wiki/.skills/wiki-query/SKILL.md` to understand the workflow.

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-query/SKILL.md`:

```markdown
---
name: wiki-query
description: Query vault knowledge with tiered retrieval using index.md and summary fields
---

# Wiki Query

Answer questions by searching the project's Obsidian vault for knowledge.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand vault structure
3. Read `{vault_path}/index.md` to get the full page catalog with summaries

## Workflow

### Step 1: Classify Query

Determine query type:
- **Factual lookup** — "What is X?", "How does Y work?"
- **Relationship** — "How does X relate to Y?"
- **Synthesis** — "What have we learned about X?"
- **Gap** — "What don't we know about X?"

### Step 2: Tiered Retrieval

**Tier 1 — Index scan (always):**
Read `index.md`. Search for pages matching the query by title, tags, and summary. Build a candidate list of 5-10 pages.

**Tier 2 — Summary scan (if needed):**
For each candidate, read the `summary:` field from frontmatter. Filter to the 3-5 most relevant pages based on summary content.

**Tier 3 — Full read (selective):**
Read full content of the top 3 candidates only. Follow up to 1 wikilink hop for additional context.

### Step 3: Synthesize Answer

Compose the answer with citations using `[[page-name]]` wikilink notation. Include:
- Direct answer to the question
- Supporting evidence from vault pages
- Related pages for further reading
- If the vault doesn't contain the answer, say so explicitly

### Quick Mode

If the user says "quick answer" or "just scan": use only Tier 1 (index scan). Return matching page titles and summaries without reading full pages.
```

- [ ] **Step 3: Verify no upstream dependencies remain**

```bash
grep -i "\.env\|OBSIDIAN_VAULT_PATH\|manifest\|log\.md\|provenance\|category:" skills/wiki-query/SKILL.md
```

Expected: Zero matches.

- [ ] **Step 4: Commit**

```bash
git add skills/wiki-query/SKILL.md
git commit -m "feat: add wiki-query skill adapted for Ark vaults"
```

---

### Task 6: Adapt wiki-status

**Files:**
- Read: `obsidian-wiki/.skills/wiki-status/SKILL.md` (~235 lines)
- Create: `skills/wiki-status/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-status/SKILL.md`:

```markdown
---
name: wiki-status
description: Show vault statistics, page counts, and health insights
---

# Wiki Status

Show current state of the project's Obsidian vault — page counts, category breakdown, and optional structural insights.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/index.md` for the machine-readable page catalog

## Workflow

### Step 1: Read Index

Read `{vault_path}/index.md`. Parse the frontmatter to get:
- Total page count (from the `summary:` field)
- Generation timestamp (from the `generated:` field)

### Step 2: Report Basic Stats

Count pages per category/type from the index sections. Report:

```
Vault Status: {project_name}
Generated: {timestamp}
Total pages: {count}

By type:
  session-log: N
  epic: N
  story: N
  bug: N
  task: N
  research: N
  compiled-insight: N
  reference: N
  ...
```

### Step 3: Check Index Freshness

```bash
cd {vault_path}
# Count .md files on disk (excluding .obsidian, .git, _Templates, _meta)
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' | wc -l
```

Compare to index page count. If they differ by more than 5, warn: "Index is stale. Run `python3 _meta/generate-index.py` to regenerate."

### Step 4: Insights Mode (Optional)

If the user asks for "insights", "hubs", or "what's central":

1. **Anchor pages:** Find the 10 pages with the most incoming wikilinks
2. **Orphan count:** Find pages with zero incoming wikilinks (excluding index.md and 00-Home.md)
3. **Summary coverage:** Count pages with vs without `summary:` field
4. **Tag coverage:** Count pages with vs without `tags:` field

Report findings as a structured table.
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-status/SKILL.md
git commit -m "feat: add wiki-status skill adapted for Ark vaults"
```

---

### Task 7: Adapt wiki-update

**Files:**
- Read: `obsidian-wiki/.skills/wiki-update/SKILL.md` (~188 lines)
- Create: `skills/wiki-update/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-update/SKILL.md`:

```markdown
---
name: wiki-update
description: Sync project knowledge into vault and regenerate index
---

# Wiki Update

Sync the current project's knowledge into its Obsidian vault. This covers documenting new architecture decisions, research findings, and operational changes.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand folder structure
3. Read `{vault_path}/index.md` to know what's already documented

## Workflow

### Step 1: Understand What Changed

Scan the project for recent changes:
```bash
git log --oneline -20
git diff HEAD~5 --stat
```

Also check:
- Recent session logs in `{vault_path}/Session-Logs/`
- Open TaskNotes in `{vault_path}/TaskNotes/Tasks/`
- Any new or modified architecture docs

### Step 2: Decide What to Document

Extract knowledge worth documenting:
- Architecture decisions and their rationale
- New patterns, abstractions, or conventions
- Research findings and experimental results
- Lessons learned from incidents or debugging

Do NOT document: boilerplate changes, minor bug fixes, config tweaks, routine dependency updates.

### Step 3: Write or Update Vault Pages

For each piece of knowledge:
1. Check if an existing page covers this topic (search `index.md`)
2. If yes: read the page, merge new information, update `last-updated:` and `summary:`
3. If no: create a new page in the appropriate domain folder (see vault-schema.md)
4. Use Ark frontmatter schema:
   ```yaml
   ---
   title: "Page Title"
   type: research|reference|guide|compiled-insight
   tags: [domain-tags from _meta/taxonomy.md]
   summary: "<=200 char description"
   created: YYYY-MM-DD
   last-updated: YYYY-MM-DD
   ---
   ```
5. Add wikilinks to related pages (minimum 2-3 per page)

### Step 4: Regenerate Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

Verify the new pages appear in `index.md`.

### Step 5: Commit Vault Changes

```bash
cd {vault_path}
git add -A
git commit -m "docs: sync project knowledge — {brief description of what was updated}"
git push
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-update/SKILL.md
git commit -m "feat: add wiki-update skill adapted for Ark vaults"
```

---

### Task 8: Adapt tag-taxonomy

**Files:**
- Read: `obsidian-wiki/.skills/tag-taxonomy/SKILL.md` (~163 lines)
- Create: `skills/tag-taxonomy/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/tag-taxonomy/SKILL.md`:

```markdown
---
name: tag-taxonomy
description: Validate and normalize tags against the vault's canonical taxonomy
---

# Tag Taxonomy

Enforce consistent tagging across the vault using the canonical vocabulary in `_meta/taxonomy.md`.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/taxonomy.md` for the canonical tag list

## Modes

### Mode 1: Tag Audit

Scan all pages, extract `tags:` from frontmatter, and report:
- **Unknown tags:** Tags not in `_meta/taxonomy.md`
- **Alias tags:** Tags that should be normalized (e.g., `walkforward` → `walk-forward`)
- **Over-tagged pages:** Pages with more than 5 tags
- **Untagged pages:** Pages missing `tags:` field

```bash
cd {vault_path}
python3 -c "
import re, os
from collections import Counter
tags = Counter()
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.obsidian','.git','.claude-plugin','.github','.notebooklm','_Templates'}]
    for f in files:
        if not f.endswith('.md'): continue
        try: content = open(os.path.join(root, f), encoding='utf-8').read()
        except: continue
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not m: continue
        in_tags = False
        for line in m.group(1).split('\n'):
            if re.match(r'^tags:', line):
                in_tags = True
                inline = re.match(r'^tags:\s*\[(.+)\]', line)
                if inline:
                    for t in inline.group(1).split(','): tags[t.strip().strip('\"').strip(\"'\")] += 1
                    in_tags = False
                continue
            if in_tags:
                item = re.match(r'^  - (.+)', line)
                if item: tags[item.group(1).strip()] += 1
                else: in_tags = False
for tag, count in tags.most_common(): print(f'{count:4d}  {tag}')
"
```

Compare output against `_meta/taxonomy.md`. Flag discrepancies.

### Mode 2: Tag Normalization

After audit, fix non-canonical tags:
1. For each page with alias tags, replace with canonical form
2. For unknown tags used on 2+ pages, suggest adding to taxonomy
3. For unknown tags on 1 page, suggest replacing with existing canonical tag

### Mode 3: Add New Tag

When a new tag is needed:
1. Check if an existing tag covers the concept
2. Determine section (Structural, Domain, Component, Session)
3. Add to `_meta/taxonomy.md` with name, purpose, and any aliases
4. Commit the taxonomy update
```

- [ ] **Step 3: Commit**

```bash
git add skills/tag-taxonomy/SKILL.md
git commit -m "feat: add tag-taxonomy skill adapted for Ark vaults"
```

---

### Task 9: Adapt cross-linker

**Files:**
- Read: `obsidian-wiki/.skills/cross-linker/SKILL.md` (~152 lines)
- Create: `skills/cross-linker/SKILL.md`

**NOTE:** Codex review found the upstream skill depends on `.env`, `OBSIDIAN_VAULT_PATH`, and `log.md` — cannot be symlinked. Must be copied and adapted like the other 9.

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/cross-linker/SKILL.md`:

```markdown
---
name: cross-linker
description: Discover and add missing wikilinks between vault pages
---

# Cross-Linker

Scan vault pages for unlinked mentions of other pages and add missing wikilinks.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_root}/index.md` for the full page inventory

## Workflow

### Step 1: Build Page Registry

Glob all `.md` files (exclude `.obsidian/`, `.git/`, `_Templates/`, `_meta/`).
Extract per page: filename, title, aliases (if any), tags, summary.

### Step 2: Scan for Missing Links

For each page:
1. Read full content
2. Extract existing `[[wikilinks]]`
3. Search for unlinked mentions: filenames, titles without `[[...]]` wrapper
4. Skip: self-references, common words, code blocks, frontmatter
5. Match case-insensitively

### Step 3: Score and Filter

- **Exact name match in text:** High confidence — apply
- **Shared tags (2+) but no link:** Medium confidence — apply
- **Partial name match:** Low confidence — skip

### Step 4: Apply Links

**Inline (preferred):** Find first natural mention, wrap in `[[page-name]]`
**Related section (fallback):** If term not naturally mentioned but semantically related, add `## Related` section with links

### Step 5: Report

```
Cross-Linker Report:
  Pages scanned: N
  Links added: M
  Pages modified: P
  Orphans remaining: Q
```

### Step 6: Commit

```bash
cd {vault_root}
git add -A
git commit -m "docs: add N missing wikilinks from cross-linker pass"
```
```

- [ ] **Step 3: Verify no upstream dependencies**

```bash
grep -i "\.env\|OBSIDIAN_VAULT_PATH\|log\.md\|provenance\|category:" skills/cross-linker/SKILL.md
```

Expected: Zero matches.

- [ ] **Step 4: Commit**

```bash
git add skills/cross-linker/SKILL.md
git commit -m "feat: add cross-linker skill adapted for Ark vaults"
```

---

## Phase 2b: Wiki Skills — Heavy Adaptation

### Task 10: Adapt wiki-setup

**Files:**
- Read: `obsidian-wiki/.skills/wiki-setup/SKILL.md` (~127 lines)
- Read: `Arknode-AI-Obsidian-Vault/_meta/vault-schema.md` (for reference)
- Read: `Arknode-AI-Obsidian-Vault/_Templates/` (for template list)
- Create: `skills/wiki-setup/SKILL.md`

- [ ] **Step 1: Read upstream skill and existing vault structure**

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-setup/SKILL.md`:

```markdown
---
name: wiki-setup
description: Initialize a new Ark project vault with standard structure and artifacts
---

# Wiki Setup

Initialize a new Obsidian vault for an Ark project with the standard folder structure, templates, metadata, and tooling.

## Prerequisites

- A git repo for the new vault
- A project name and task prefix (e.g., `ArkNewProject-`)

## Workflow

### Step 1: Get Project Info

Ask the user for:
- **Project name** — e.g., `my-new-project`
- **Task prefix** — e.g., `ArkNew-`
- **Vault path** — where to create the vault (default: current directory)

### Step 2: Create Directory Structure

```bash
mkdir -p {vault_path}/{_Templates,_Attachments,_meta,TaskNotes/{Tasks/{Epic,Story,Bug,Task},Archive/{Epic,Story,Bug,Enhancement},Templates,Views,meta}}
```

### Step 3: Create 00-Home.md

Write `{vault_path}/00-Home.md`:
```yaml
---
title: "{Project Name} Knowledge Base"
type: moc
tags:
  - home
  - dashboard
summary: "Navigation hub for {Project Name}: links to project areas and key resources."
created: {today}
last-updated: {today}
---
```

With navigation links to key sections.

### Step 4: Create Templates

Create these templates in `{vault_path}/_Templates/`:
- `Session-Template.md` — session log with `prev:`, `epic:`, `session:` frontmatter
- `Compiled-Insight-Template.md` — for synthesized knowledge with `source-sessions:`, `source-tasks:`
- `Bug-Template.md` — bug report with `task-id:`, `status:`, `priority:`, `component:`
- `Task-Template.md` — generic task
- `Research-Template.md` — research findings
- `Service-Template.md` — service/infrastructure documentation

Use the templates from `Arknode-Poly-Obsidian-Vault/_Templates/` as reference for exact format.

### Step 5: Create Metadata Files

**`_meta/vault-schema.md`:**
Document the vault's folder structure, frontmatter conventions, and navigation patterns. Model after the existing vault schemas (read `Arknode-AI-Obsidian-Vault/_meta/vault-schema.md` for format).

**`_meta/taxonomy.md`:**
Initialize with structural tags (`session-log`, `task`, `compiled-insight`, `home`, `moc`) and project-specific domain tags. Leave room for organic growth.

**`_meta/generate-index.py`:**
Copy from an existing vault:
```bash
cp Arknode-AI-Obsidian-Vault/_meta/generate-index.py {vault_path}/_meta/generate-index.py
```

### Step 6: Create Task Counter

Write `{vault_path}/TaskNotes/meta/{task_prefix}counter` with content `1`.

### Step 7: Create Project Management Guide

Write `{vault_path}/TaskNotes/00-Project-Management-Guide.md` documenting:
- Task ID format: `{task_prefix}NNN`
- Counter file location
- Status values: backlog, todo, in-progress, done
- Task types: epic, story, bug, task

### Step 8: Generate Initial Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

### Step 9: Initialize Git and Commit

```bash
cd {vault_path}
git init
git add -A
git commit -m "feat: initialize {project_name} vault with Ark structure"
```

### Step 10: Remind User

Tell the user:
1. Add vault to the project's CLAUDE.md (vault path, task prefix, TaskNotes path)
2. Configure tasknotes MCP in `.claude/settings.json`
3. Add vault to linear-updater config (requires code change if third+ vault)
4. Set up NotebookLM sync if desired
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-setup/SKILL.md
git commit -m "feat: add wiki-setup skill for Ark vault initialization"
```

---

### Task 11: Adapt wiki-ingest

**Files:**
- Read: `obsidian-wiki/.skills/wiki-ingest/SKILL.md` (~172 lines)
- Create: `skills/wiki-ingest/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-ingest/SKILL.md`:

```markdown
---
name: wiki-ingest
description: Distill documents into vault pages using Ark folder structure and frontmatter
---

# Wiki Ingest

Ingest documents (markdown, text, PDF, images) into the project's Obsidian vault by distilling knowledge into interconnected pages.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand folder structure and content placement
3. Read `{vault_path}/index.md` to know what's already documented

## Workflow

### Step 1: Read Source

Accept source material in any format:
- Markdown (`.md`), plain text (`.txt`)
- PDF (`.pdf`) — use Read tool with pages parameter
- Images (`.png`, `.jpg`, `.webp`) — use Read tool for visual content
- Web pages — use WebFetch

### Step 2: Extract Knowledge

Identify:
- Concepts and definitions
- Architecture decisions and rationale
- Procedures and workflows
- Entities (people, services, systems)
- Relationships between entities
- Open questions and unknowns

### Step 3: Determine Placement

Use `_meta/vault-schema.md` to decide where pages belong. Ark vaults use **domain-specific folders**, not generic categories:

| Content Type | Placement |
|-------------|-----------|
| Architecture decisions | `{project_area}/Architecture/` |
| Research findings | `{project_area}/Research/` |
| Operational guides | `{project_area}/Operations/` |
| Cross-cutting insights | `{project_area}/Research/Compiled-Insights/` |
| Infrastructure docs | `Infrastructure/` (if applicable) |

Do NOT create `concepts/`, `entities/`, `skills/`, `references/`, or `synthesis/` folders — these are obsidian-wiki conventions, not Ark conventions.

### Step 4: Write Pages

For each piece of knowledge:

1. Check `index.md` for existing pages on this topic
2. If exists: read the page, merge new info, update `last-updated:` and `summary:`
3. If new: create page with Ark frontmatter:
   ```yaml
   ---
   title: "Page Title"
   type: research|reference|guide|compiled-insight|architecture
   tags: [use canonical tags from _meta/taxonomy.md]
   summary: "<=200 char description of what this page contains"
   source-sessions: []
   source-tasks: []
   created: YYYY-MM-DD
   last-updated: YYYY-MM-DD
   ---
   ```
4. Add 2-3 wikilinks to related existing pages
5. Do NOT add `provenance:` markers — Ark vaults don't use them

### Step 5: Update Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

### Step 6: Commit

```bash
cd {vault_path}
git add -A
git commit -m "docs: ingest {source_description} — {N} pages created/updated"
git push
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-ingest/SKILL.md
git commit -m "feat: add wiki-ingest skill adapted for Ark vault structure"
```

---

### Task 12: Adapt wiki-lint

**Files:**
- Read: `obsidian-wiki/.skills/wiki-lint/SKILL.md` (~162 lines)
- Create: `skills/wiki-lint/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/wiki-lint/SKILL.md`:

```markdown
---
name: wiki-lint
description: Audit vault health — broken links, missing frontmatter, stale index, tag violations
---

# Wiki Lint

Audit the project's Obsidian vault for structural issues and produce a health report.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/taxonomy.md` for canonical tag list
3. Read `{vault_path}/index.md` for page inventory

## Lint Checks

Run all checks in sequence. Report findings as a structured list.

### Check 1: Broken Wikilinks

```bash
cd {vault_path}
grep -roh '\[\[[^]]*\]\]' --include="*.md" . | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u | while read link; do
  base=$(echo "$link" | sed 's/#.*//')
  [ -z "$base" ] && continue
  found=$(find . -name "${base}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "BROKEN: [[${link}]]"
done
```

### Check 2: Orphaned Pages

Find pages with zero incoming wikilinks (excluding index.md, 00-Home.md, templates):

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  basename=$(basename "$f" .md)
  incoming=$(grep -rl "\[\[$basename" --include="*.md" . 2>/dev/null | grep -v "$f" | wc -l | tr -d ' ')
  [ "$incoming" -eq 0 ] && echo "ORPHAN: $f"
done
```

### Check 3: Missing Frontmatter

Check all pages have required fields: `title`, `type` (or `task-type`), `tags`

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  head -1 "$f" | grep -q "^---" || echo "NO FRONTMATTER: $f"
done
```

### Check 4: Missing Summary

Check for `summary:` field on all pages. Report count of pages without it.

### Check 5: Tag Violations

Compare all tags in use against `_meta/taxonomy.md`. Flag:
- Tags not in taxonomy
- Alias tags that should be normalized

### Check 6: Index Freshness

Compare page count in `index.md` vs actual `.md` files on disk. If they differ, the index is stale.

### Check 7: Summary Length

Find pages where `summary:` exceeds 200 characters.

## Report Format

```
Wiki Lint Report: {project_name}
================================
Broken wikilinks: N
Orphaned pages: N
Missing frontmatter: N
Missing summary: N
Tag violations: N
Index stale: yes/no
Summary too long: N

Details:
[list each issue with file path]
```

## Skipped Checks (not applicable to Ark vaults)

- Provenance drift — Ark vaults don't use `provenance:` markers
- Stale content by timestamp — no source-tracking manifest
- Contradiction detection — too expensive for routine lint
```

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-lint/SKILL.md
git commit -m "feat: add wiki-lint skill adapted for Ark vaults"
```

---

### Task 13: Adapt claude-history-ingest

**Files:**
- Read: `obsidian-wiki/.skills/claude-history-ingest/SKILL.md` (~243 lines)
- Create: `skills/claude-history-ingest/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/claude-history-ingest/SKILL.md`:

```markdown
---
name: claude-history-ingest
description: Mine Claude Code conversation history and memory files into compiled vault insights
---

# Claude History Ingest

Extract knowledge from Claude Code conversation history (`~/.claude/`) and distill into compiled insight pages in the project's vault.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/_Templates/Compiled-Insight-Template.md` for output format

## Workflow

### Step 1: Survey Claude History

```bash
# Find project-specific Claude data
ls ~/.claude/projects/*/
ls ~/.claude/projects/*/memory/*.md 2>/dev/null
```

Identify:
- **Memory files** (highest value) — `~/.claude/projects/*/memory/*.md`
- **MEMORY.md indexes** — `~/.claude/projects/*/MEMORY.md`
- **Conversation JSONL** — `~/.claude/projects/*/*.jsonl` (large, lower signal-to-noise)

### Step 2: Read Memory Files First

Parse YAML frontmatter from memory files. Prioritize by type:
- `type: user` → knowledge about the developer
- `type: feedback` → workflow preferences and corrections
- `type: project` → project decisions and context
- `type: reference` → external resource pointers

### Step 3: Parse Conversations (Optional)

If the user wants deeper mining, parse JSONL files:
- Extract `user` and `assistant` messages only
- Skip `thinking`, `tool_use`, `progress` entries
- Focus on messages containing decisions, discoveries, or lessons

### Step 4: Cluster by Topic

Group findings by topic across all sources. Common clusters:
- Architecture decisions
- Debugging lessons
- Workflow patterns
- Performance discoveries
- Failed approaches

### Step 5: Write Compiled Insight Pages

For each cluster, create a page in `{vault_path}/{project_area}/Research/Compiled-Insights/`:

Use the Compiled-Insight-Template:
```yaml
---
title: "{Insight Title}"
type: compiled-insight
tags:
  - compiled-insight
  - {domain-tag from taxonomy}
summary: "{<=200 char finding summary}"
source-sessions: []
source-tasks: []
created: {today}
last-updated: {today}
---
```

Write:
- **Key Finding** — one-paragraph conclusion
- **Evidence** — specific data points from conversations
- **Context** — what prompted the investigation
- **Implications** — what to do differently based on this knowledge

### Step 6: Update Index and Commit

```bash
cd {vault_path}
python3 _meta/generate-index.py
git add -A
git commit -m "docs: ingest Claude history — {N} compiled insights created"
git push
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/claude-history-ingest/SKILL.md
git commit -m "feat: add claude-history-ingest skill adapted for Ark vaults"
```

---

### Task 14: Adapt data-ingest

**Files:**
- Read: `obsidian-wiki/.skills/data-ingest/SKILL.md` (~138 lines)
- Create: `skills/data-ingest/SKILL.md`

- [ ] **Step 1: Read upstream skill**

- [ ] **Step 2: Write adapted skill**

Write to `skills/data-ingest/SKILL.md`:

```markdown
---
name: data-ingest
description: Process logs, transcripts, chat exports, and data dumps into vault pages
---

# Data Ingest

Ingest arbitrary text data (chat exports, logs, transcripts, research papers) into the project's Obsidian vault.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/index.md` to check for existing coverage

## Workflow

### Step 1: Identify Source Format

Detect format from file extension and content:
- JSON/JSONL — structured data, chat exports
- Markdown — documentation, notes
- Plain text — logs, transcripts
- CSV/TSV — tabular data
- HTML — web clippings
- Images — use Read tool with vision
- Chat exports — ChatGPT, Slack, Discord

### Step 2: Extract Knowledge

Focus on substance:
- Topics discussed, decisions made, facts learned
- Procedures and workflows
- Entities and relationships
- For conversations: distill the knowledge, not the dialogue

### Step 3: Cluster and Deduplicate

Group by topic (not by source file). Check `index.md` for existing pages on the same topics. Merge with existing knowledge rather than creating duplicates.

### Step 4: Write Vault Pages

Place in appropriate domain folders per `_meta/vault-schema.md`.

For synthesized findings, use Compiled-Insight-Template:
```yaml
---
title: "{Title}"
type: compiled-insight
tags: [compiled-insight, {domain-tags}]
summary: "<=200 char description"
source-sessions: []
source-tasks: []
created: {today}
last-updated: {today}
---
```

For reference material, use:
```yaml
---
title: "{Title}"
type: reference
tags: [{domain-tags}]
summary: "<=200 char description"
created: {today}
last-updated: {today}
---
```

Add 2-3 wikilinks per page. Do NOT use `provenance:` markers.

### Step 5: Update Index and Commit

```bash
cd {vault_path}
python3 _meta/generate-index.py
git add -A
git commit -m "docs: ingest {source_description} — {N} pages created/updated"
git push
```
```

- [ ] **Step 3: Commit**

```bash
git add skills/data-ingest/SKILL.md
git commit -m "feat: add data-ingest skill adapted for Ark vaults"
```

---

## Phase 3: ark-tasknotes

### Task 15: Write ark-tasknotes Skill

**Files:**
- Read: `tasknotes/src/services/MCPService.ts` (actual MCP tool definitions)
- Read: `Arknode-AI-Obsidian-Vault/TaskNotes/00-Project-Management-Guide.md` (task conventions)
- Create: `skills/ark-tasknotes/SKILL.md`

- [ ] **Step 1: Read MCP service and task conventions**

Read `tasknotes/src/services/MCPService.ts` to verify tool names and parameter schemas. Read the project management guide for frontmatter conventions.

- [ ] **Step 2: Write the skill**

Write to `skills/ark-tasknotes/SKILL.md`:

```markdown
---
name: ark-tasknotes
description: Agent-driven task creation and management via tasknotes MCP or direct markdown write
---

# Ark TaskNotes

Create and manage TaskNote tickets automatically during development workflows. Tasks sync to Linear via linear-updater.

## Project Discovery

1. Read the project's CLAUDE.md to find: task prefix, vault path, TaskNotes path
2. Verify MCP is available: call `tasknotes_health_check`
3. If MCP unavailable (Obsidian not running), fall back to direct markdown write
4. Read `{vault_path}/TaskNotes/meta/{task_prefix}counter` for next available ID

## When to Create Tasks

| Trigger | Task Type | Priority |
|---------|-----------|----------|
| Bug discovered during code review | Bug | Based on severity |
| Feature completed, needs verification | Story | medium |
| Tech debt identified during maintenance | Task | low-medium |
| Incident debugged, root cause found | Bug | Based on impact |
| Research finding needs follow-up | Story | medium |

## Workflow

### Step 1: Check for Duplicates

Before creating, search for existing tasks on the same topic:

**If MCP available:**
```
tasknotes_query_tasks({
  conjunction: "and",
  children: [{
    type: "condition",
    id: "1",
    property: "status",
    operator: "is_not",
    value: "done"
  }],
  sortKey: "due",
  sortDirection: "asc"
})
```

Review results. If a matching task exists, update it instead of creating a duplicate.

**If MCP unavailable:**
```bash
grep -rl "{keyword}" {vault_path}/TaskNotes/Tasks/ --include="*.md" | head -5
```

### Step 2: Get Next Task ID

```bash
COUNTER=$(cat {vault_path}/TaskNotes/meta/{task_prefix}counter)
TASK_ID="{task_prefix}$(printf '%03d' $COUNTER)"
echo "Next task ID: $TASK_ID"
```

### Step 3: Create the Task

**Option A: MCP + post-edit (preferred when Obsidian is running)**

1. Create via MCP:
```
tasknotes_create_task({
  title: "{task title}",
  status: "backlog",
  priority: "{low|medium|high|urgent}",
  tags: ["{task_type}"],
  projects: ["{project_name}"],
  details: "{description with context}"
})
```

2. The MCP returns the file path. Edit the created file to add Ark-specific frontmatter:
```yaml
task-id: "{TASK_ID}"
task-type: "{epic|story|bug|task}"
work-type: "{development|research|deployment|docs|infrastructure}"
component: "{module_name}"
urgency: "{blocking|high|normal|low}"
summary: "<=200 char description"
```

**Option B: Direct markdown write (fallback when Obsidian is not running)**

Determine the subdirectory from task type:
- epic → `TaskNotes/Tasks/Epic/`
- story → `TaskNotes/Tasks/Story/`
- bug → `TaskNotes/Tasks/Bug/`
- task → `TaskNotes/Tasks/Task/`

Write the file `{TASK_ID}-{slug}.md`:
```yaml
---
title: "{task title}"
tags:
  - task
  - {task_type}
task-id: "{TASK_ID}"
task-type: "{epic|story|bug|task}"
status: backlog
priority: "{low|medium|high|critical}"
project: "{project_name}"
work-type: "{development|research|deployment|docs}"
component: "{module_name}"
urgency: "{blocking|high|normal|low}"
created: "{today}"
summary: "<=200 char description"
---

# {task title}

## Description

{detailed description}

## Related

- [[related-task-or-page]]
```

### Step 4: Increment Counter

```bash
echo $((COUNTER + 1)) > {vault_path}/TaskNotes/meta/{task_prefix}counter
```

### Step 5: Announce and Commit

Tell the user: "Created {task_type} {TASK_ID}: {title}"

```bash
cd {vault_path}
git add TaskNotes/
git commit -m "task: create {TASK_ID} — {title}"
git push
```

## Guardrails

- **Never auto-close tasks** — only create and update to in-progress
- **Critical/blocking tasks:** Ask user for confirmation before creating
- **Announce creation:** Always tell the user what was created (no silent side-effects)
- **Verify vault identity:** Before creating, check that `TaskNotes/meta/{task_prefix}counter` exists. If missing, alert user that the vault may be misconfigured.

## MCP Tool Reference

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `tasknotes_health_check` | Verify MCP is running | none |
| `tasknotes_create_task` | Create task | `title` (req), `status`, `priority`, `tags`, `projects`, `details` |
| `tasknotes_update_task` | Update task | task file path, properties to update |
| `tasknotes_query_tasks` | Search tasks | `conjunction`, `children` (filter conditions), `sortKey` |
| `tasknotes_get_task` | Get by file path | file path (NOT task-id) |
| `tasknotes_list_tasks` | List with pagination | page, limit |
| `tasknotes_toggle_status` | Cycle status | task file path |
| `tasknotes_get_stats` | Task statistics | none |
```

- [ ] **Step 3: Commit**

```bash
git add skills/ark-tasknotes/SKILL.md
git commit -m "feat: add ark-tasknotes skill for agent-driven task automation"
```

---

## Phase 4: Documentation

### Task 16: Write Onboarding Guide

**Files:**
- Create: `docs/onboarding-guide.md`

- [ ] **Step 1: Write the guide**

Write to `docs/onboarding-guide.md`:

```markdown
# New Project Onboarding Guide

How to add a new project to the Ark ecosystem with shared skills, vault, and Linear sync.

## Prerequisites

- SSH key with access to the HelloWorldSungin GitHub org
- SSH key on CT110 for vault sync and linear-updater deployment
- Linear API key for the target team
- Google NotebookLM access (for notebook sync)
- Obsidian installed with tasknotes plugin

## Step 1: Create Obsidian Vault

Run the `/wiki-setup` skill from this plugin. It will:
1. Create the standard Ark vault structure
2. Initialize TaskNotes with your task prefix
3. Create metadata files (_meta/vault-schema.md, taxonomy.md, generate-index.py)
4. Generate initial index.md

## Step 2: Install This Plugin

Add `create-ark-skills` as a Claude Code plugin. All 14 shared skills become available.

```bash
# In Claude Code settings, add this repo as a plugin
```

## Step 3: Configure Project CLAUDE.md

Add these fields to your project's CLAUDE.md:

```markdown
| Topic | Location |
|-------|----------|
| **Obsidian Vault** | `vault/{Project-Name}/` (symlink to vault repo) |
| **Session Logs** | `vault/{Project-Name}/Session-Logs/` |
| **Task Management** | `vault/TaskNotes/` — prefix: `{YourPrefix}-`, project: `{project-name}` |
```

## Step 4: Configure TaskNotes MCP

In Obsidian:
1. Enable `enableAPI: true` in tasknotes plugin settings
2. Enable `enableMCP: true`
3. Set `apiPort` (default 8080; use a unique port if running multiple vaults)

In your project's `.claude/settings.json`:
```json
{
  "mcpServers": {
    "tasknotes": {
      "type": "url",
      "url": "http://localhost:{port}/mcp"
    }
  }
}
```

## Step 5: Add Vault to linear-updater

**PREREQUISITE:** Task 17 (Phase 5) must be completed first — the dynamic vault config refactor must be deployed before a third vault can be added.

After the refactor is deployed:
1. Add your vault to the `VAULTS` env var: `VAULTS=ai:/path/ai,poly:/path/poly,newproject:/path/new`
2. Restart linear-updater on CT110
3. Verify sync: create a test task, wait 5 minutes, check Linear

## Step 6: Set Up NotebookLM Sync

1. Create `.notebooklm/config.json` in your vault repo:
```json
{
  "notebooks": {
    "main": {
      "name": "Your Notebook Name",
      "id": "notebook-id-from-notebooklm"
    }
  },
  "persona": "expert",
  "mode": "detailed",
  "response_length": "longer"
}
```

2. Add sync timer on CT110 (copy existing timer, update paths)

## Step 7: Run Baseline Lint

Invoke `/wiki-lint` to verify vault structure is healthy.

## Verification Checklist

- [ ] Vault created with standard structure
- [ ] Plugin installed, skills available
- [ ] CLAUDE.md has vault path, task prefix, TaskNotes path
- [ ] TaskNotes MCP reachable (run `tasknotes_health_check`)
- [ ] linear-updater picks up vault changes
- [ ] NotebookLM sync running
- [ ] wiki-lint passes clean
```

- [ ] **Step 2: Commit**

```bash
git add docs/onboarding-guide.md
git commit -m "docs: add new project onboarding guide"
```

---

### Task 17: Write README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

Write to `README.md` covering:

**Sections to include:**

1. **Header & Overview** — What this repo is (Claude Code plugin for shared Ark skills), what problem it solves (skill duplication across projects)

2. **Quick Setup** — Step-by-step to install the plugin:
   - Clone this repo (with `--recurse-submodules`)
   - Register as a Claude Code plugin
   - Verify skills are available (invoke `/wiki-status` from any project)

3. **Available Skills** — Table of all 14 skills with:
   - Skill name (slash command)
   - Category (Core / Task Automation / Vault Maintenance)
   - One-line description
   - Source (generalized, adapted from obsidian-wiki, or new)

4. **Skill Documentation** — For each skill category, describe:
   - **Core Skills** (`/ark-code-review`, `/codebase-maintenance`, `/notebooklm-vault`): what they do, what context-discovery fields they need, common invocations
   - **Task Automation** (`/ark-tasknotes`): MCP integration, Obsidian requirements, fallback behavior
   - **Vault Maintenance** (10 wiki skills): tiered retrieval, index regeneration, lint checks, tag validation, ingestion workflows

5. **Context-Discovery Pattern** — How skills find project-specific values from CLAUDE.md (reference the plugin CLAUDE.md, explain the monorepo precedence rules)

6. **Architecture** — Brief diagram showing:
   ```
   Claude Code Plugin (this repo)
     └── skills/ (14 shared skills)
           ↓ context-discovery
   Project CLAUDE.md → vault path, task prefix, deployment targets
           ↓
   Obsidian Vault → TaskNotes → linear-updater → Linear
                  → NotebookLM sync
   ```

7. **New Project Onboarding** — Link to `docs/onboarding-guide.md` with a 1-paragraph summary

8. **Repository Structure** — Explain the submodules:
   - `ArkNode-AI/`, `ArkNode-Poly/` — project repos (skill sources for generalization)
   - `Arknode-AI-Obsidian-Vault/`, `Arknode-Poly-Obsidian-Vault/` — vault repos
   - `obsidian-wiki/` — upstream skill reference
   - `tasknotes/` — MCP server reference
   - `linear-updater/` — Linear sync service

9. **Development** — How to modify skills:
   - Edit SKILL.md files in `skills/`
   - Test by invoking from a project
   - Verify with grep checks (no hardcoded references)
   - Commit and push

10. **Vault Artifacts** — Explain what the vault restructuring added and how skills leverage it (index.md, summary:, vault-schema.md, taxonomy.md, generate-index.py)

- [ ] **Step 2: Verify no placeholder content**

```bash
grep -in "TODO\|TBD\|PLACEHOLDER\|coming soon" README.md
```

Expected: Zero matches.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with setup, skills reference, and architecture"
```

---

## Phase 5: linear-updater Extensibility

### Task 18: Refactor linear-updater for Dynamic Vault Config

**Files:**
- Modify: `linear-updater/src/config.ts`
- Modify: `linear-updater/.env.example`

- [ ] **Step 1: Read current config.ts**

Read `linear-updater/src/config.ts` to understand the current hardcoded vault config.

Current code (lines 43-55):
```typescript
vaults: [
  { name: "ai", path: requireEnv("VAULT_AI_PATH") },
  { name: "poly", path: requireEnv("VAULT_POLY_PATH") },
],
```

- [ ] **Step 2: Refactor to dynamic vault list**

Edit `linear-updater/src/config.ts`. Replace the hardcoded vault array with a dynamic parser:

```typescript
function parseVaults(): VaultConfig[] {
  // Check for new dynamic format first
  const vaultsStr = process.env.VAULTS;
  if (vaultsStr) {
    return vaultsStr.split(",").map((entry) => {
      const colonIdx = entry.indexOf(":");
      if (colonIdx === -1) {
        throw new Error(`Invalid vault entry: "${entry}". Expected format: name:/path`);
      }
      const name = entry.slice(0, colonIdx).trim();
      const path = entry.slice(colonIdx + 1).trim();
      if (!name || !path) {
        throw new Error(`Invalid vault entry: "${entry}". Expected format: name:/path`);
      }
      return { name, path };
    });
  }

  // Legacy format: require BOTH vars (preserves current fail-fast behavior)
  const legacyAi = process.env.VAULT_AI_PATH;
  const legacyPoly = process.env.VAULT_POLY_PATH;

  if (legacyAi && legacyPoly) {
    return [
      { name: "ai", path: legacyAi },
      { name: "poly", path: legacyPoly },
    ];
  }

  if (legacyAi || legacyPoly) {
    throw new Error(
      "Legacy vault config requires BOTH VAULT_AI_PATH and VAULT_POLY_PATH. " +
      "For flexible vault configuration, use VAULTS=name:/path,name2:/path2 instead."
    );
  }

  throw new Error(
    "No vault configuration found. Set VAULTS=name:/path,... or legacy VAULT_AI_PATH + VAULT_POLY_PATH"
  );
  });
}
```

Then update `loadConfig()` to use it:

```typescript
vaults: parseVaults(),
```

- [ ] **Step 3: Update .env.example**

Add to `linear-updater/.env.example`:

```bash
# Vault configuration (choose ONE format):

# Option 1: Legacy (two vaults)
VAULT_AI_PATH=./vaults/Arknode-AI-Obsidian-Vault
VAULT_POLY_PATH=./vaults/Arknode-Poly-Obsidian-Vault

# Option 2: Dynamic (any number of vaults)
# VAULTS=ai:./vaults/Arknode-AI-Obsidian-Vault,poly:./vaults/Arknode-Poly-Obsidian-Vault
```

- [ ] **Step 4: Test with existing config**

```bash
cd linear-updater
npm test
```

Expected: All existing tests pass (backward compatibility via legacy format).

- [ ] **Step 5: Commit**

```bash
cd linear-updater
git add src/config.ts .env.example
git commit -m "feat: support dynamic vault list in config (backward compatible)"
```

---

## Phase 6: Cleanup

### Task 19: Remove Duplicate Skills and Update Project CLAUDEs

**Files:**
- Delete: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/ark-code-review/`
- Delete: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/codebase-maintenance/`
- Delete: `ArkNode-AI/projects/trading-signal-ai/.claude/skills/notebooklm-vault/`
- Delete: `ArkNode-Poly/.claude/skills/ark-code-review/`
- Delete: `ArkNode-Poly/.claude/skills/codebase-maintenance/`
- Delete: `ArkNode-Poly/.claude/skills/notebooklm-vault/`
- Modify: `ArkNode-AI/projects/trading-signal-ai/CLAUDE.md`
- Modify: `ArkNode-Poly/CLAUDE.md`

**IMPORTANT:** This task modifies submodules. Each submodule must be committed separately.

- [ ] **Step 1: Verify shared skills work first**

Before deleting anything, test each shared skill from both projects:

```bash
# From ArkNode-AI/projects/trading-signal-ai/, verify skills are available
# Invoke /ark-code-review --quick to verify context-discovery works
# Invoke /wiki-status to verify vault path discovery works
```

- [ ] **Step 2: Remove duplicates from trading-signal-ai**

```bash
cd ArkNode-AI/projects/trading-signal-ai
rm -rf .claude/skills/ark-code-review
rm -rf .claude/skills/codebase-maintenance
rm -rf .claude/skills/notebooklm-vault
```

- [ ] **Step 3: Update trading-signal-ai CLAUDE.md**

Add a note to `ArkNode-AI/projects/trading-signal-ai/CLAUDE.md`:

```markdown
## Shared Skills

The following skills are provided by the `create-ark-skills` Claude Code plugin (user-scoped):
- `/ark-code-review`, `/codebase-maintenance`, `/notebooklm-vault`
- `/ark-tasknotes`, `/wiki-query`, `/wiki-lint`, `/wiki-status`, `/wiki-update`
- `/wiki-setup`, `/wiki-ingest`, `/tag-taxonomy`, `/cross-linker`
- `/claude-history-ingest`, `/data-ingest`
```

- [ ] **Step 4: Commit trading-signal-ai changes**

```bash
cd ArkNode-AI
git add projects/trading-signal-ai/.claude/skills/ projects/trading-signal-ai/CLAUDE.md
git commit -m "chore: remove duplicate skills, reference shared plugin"
```

- [ ] **Step 5: Remove duplicates from ArkNode-Poly**

```bash
cd ArkNode-Poly
rm -rf .claude/skills/ark-code-review
rm -rf .claude/skills/codebase-maintenance
rm -rf .claude/skills/notebooklm-vault
```

- [ ] **Step 6: Update ArkNode-Poly CLAUDE.md**

Add the same shared skills note to `ArkNode-Poly/CLAUDE.md`.

- [ ] **Step 7: Commit ArkNode-Poly changes**

```bash
cd ArkNode-Poly
git add .claude/skills/ CLAUDE.md
git commit -m "chore: remove duplicate skills, reference shared plugin"
```

- [ ] **Step 8: Update parent repo submodule refs**

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/HelloWorldSungin/create-ark-skills
git add ArkNode-AI ArkNode-Poly
git commit -m "chore: update submodule refs after duplicate skill cleanup"
```

---

## Task Dependency Map

```
Phase 0 (scaffolding):
  Task 0 (dirs) → Task 1 (CLAUDE.md) → all subsequent tasks

Phase 1 (generalization, parallel):
  Task 2 (ark-code-review)
  Task 3 (codebase-maintenance)
  Task 4 (notebooklm-vault)

Phase 2a (light adaptation, parallel):
  Task 5, 6, 7, 8, 9 (all independent)

Phase 2b (heavy adaptation, parallel):
  Task 10, 11, 12, 13, 14 (all independent)

Phase 3:
  Task 15 (ark-tasknotes, independent)

Phase 4 (docs, after skills verified + Phase 5 complete):
  Task 16 (onboarding guide)
  Task 17 (README.md)

Phase 5:
  Task 18 (linear-updater, independent — but must complete before Phase 4)

Phase 6:
  Task 19 (cleanup, MUST be last — depends on all skills being working)
```

Tasks within each phase are independent and can be parallelized. Phases 1, 2a, 2b, 3, and 5 can all run in parallel. Phase 4 (docs, including onboarding guide and README) should wait until skills are verified AND Phase 5 is complete (onboarding references the dynamic vault config). Phase 6 must be last.

---

## Verification Checklist

After all tasks complete:

### Static checks (grep)
- [ ] All 14 skill directories exist with SKILL.md: `find skills -name SKILL.md | wc -l` → 14
- [ ] Zero hardcoded project references: `grep -rn "ArkPoly\|ArkSignal\|trading-signal-ai\|arknode-poly\|CT100\|CT110\|CT120\|192\.168\|Polymarket" skills/`
- [ ] Zero `.env` or `OBSIDIAN_VAULT_PATH` references: `grep -rn "\.env\|OBSIDIAN_VAULT_PATH" skills/`
- [ ] Zero `.manifest.json` or `log.md` references: `grep -rn "manifest\.json\|log\.md" skills/`
- [ ] Zero `category:` or `provenance:` references: `grep -rn "category:\|provenance:" skills/`

### Structural checks (file dependencies)
- [ ] codebase-maintenance has all workflow files: `ls skills/codebase-maintenance/workflows/` → cleanup-code.md, sync-vault.md, sync-skills.md, full-cleanup.md
- [ ] All skills reference "Project Discovery" or "CLAUDE.md": `grep -rL "Project Discovery\|CLAUDE.md" skills/*/SKILL.md` → empty (no misses)
- [ ] Path model uses correct variables: `grep -rn "vault_path}/TaskNotes" skills/` → zero matches (should use `tasknotes_path`, not `vault_path/TaskNotes`)

### Functional checks (invoke from each project)
- [ ] From ArkNode-AI/projects/trading-signal-ai/: invoke `/wiki-status`, verify it discovers the vault and reads index.md
- [ ] From ArkNode-Poly/: invoke `/wiki-status`, verify same
- [ ] From ArkNode-Poly/: invoke `/ark-tasknotes` dry-run, verify it finds the counter file and correct prefix
- [ ] Plugin CLAUDE.md exists with context-discovery pattern
- [ ] README.md exists with setup instructions and skill documentation
- [ ] Onboarding guide exists at `docs/onboarding-guide.md`
- [ ] linear-updater: `cd linear-updater && npm test` passes
- [ ] Duplicate skills removed from both projects
- [ ] Both project CLAUDEs reference the shared plugin
