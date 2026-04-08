# Ark Skills Plugin — Unified Design Spec

## Context

ArkNode-AI (trading-signal-ai) and ArkNode-Poly are two active projects that share duplicate Claude Code skills (ark-code-review, codebase-maintenance, notebooklm-vault), each with their own Obsidian vault synced to NotebookLM and Linear. The current duplication causes drift between skill versions and makes onboarding new projects tedious. Additionally, the tasknotes Obsidian plugin's MCP server capabilities are unused (manual ticket creation only), and the vaults lack structured maintenance workflows that obsidian-wiki provides.

This spec covers three interconnected goals:
1. **Shared skills infrastructure** — this repo as a Claude Code plugin with user-scoped skills
2. **Vault audit & restructuring recommendations** — assess both vaults, recommend obsidian-wiki adoption
3. **Agent-driven tasknotes automation** — Claude Code agents create/update tasks via MCP server

---

## 1. Plugin Architecture

### Distribution Model

This repo (`create-ark-skills`) is registered as a **Claude Code plugin**. All skills in the `skills/` directory become **user-scoped skills** available to every project.

### Context-Discovery Pattern

Skills are generalized — no hardcoded project names, vault paths, or task prefixes. Each skill begins with a **Project Discovery** section that instructs the agent to read the current project's `CLAUDE.md` to extract:

- Project name and identifier
- Task ID prefix (e.g., `ArkSignal-`, `ArkPoly-`)
- Vault path (symlink or absolute)
- Deployment targets (containers, IPs, services) — if applicable
- NotebookLM notebook config (single vs. multi-notebook)
- Infrastructure details (database, monitoring) — if applicable

Skills adapt their behavior based on what the project declares. Infrastructure-specific sections (container drift checks, dashboard sync) only activate when the project's CLAUDE.md defines deployment targets.

**Discovery precedence for monorepos:** ArkNode-AI's root `CLAUDE.md` is a hub that points to sub-project CLAUDEs (e.g., `projects/trading-signal-ai/CLAUDE.md`). Skills must follow this precedence:
1. Read the CLAUDE.md in the current working directory (cwd)
2. If it's a hub (links to sub-project CLAUDEs), follow the link matching the active project
3. Extract config from the most specific CLAUDE.md (e.g., trading-signal-ai's CLAUDE.md declares `prefix: ArkSignal-`, `vault: vault/Trading-Signal-AI/`, `task management: vault/TaskNotes/`)
4. If a required field is missing, surface an error rather than guessing

### Repository Structure

```
create-ark-skills/
├── skills/                              # User-scoped shared skills
│   ├── ark-code-review/                 # Multi-agent code review
│   │   └── SKILL.md
│   ├── codebase-maintenance/            # Audit, sync, heal
│   │   ├── SKILL.md
│   │   └── references/
│   ├── notebooklm-vault/               # NotebookLM vault context & sync
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── ark-tasknotes/                   # NEW: Agent-driven task automation
│   │   └── SKILL.md
│   │
│   │  # --- obsidian-wiki skills (adapted) ---
│   ├── wiki-setup/                      # Initialize vault structure
│   │   └── SKILL.md
│   ├── wiki-ingest/                     # Distill documents into wiki pages
│   │   └── SKILL.md
│   ├── wiki-update/                     # Sync project knowledge into vault
│   │   └── SKILL.md
│   ├── wiki-query/                      # Query vault knowledge
│   │   └── SKILL.md
│   ├── wiki-lint/                       # Audit vault health
│   │   └── SKILL.md
│   ├── wiki-status/                     # Ingestion delta & insights
│   │   └── SKILL.md
│   ├── cross-linker/                    # Auto-insert missing wikilinks
│   │   └── SKILL.md
│   ├── tag-taxonomy/                    # Normalize tag vocabulary
│   │   └── SKILL.md
│   ├── claude-history-ingest/           # Mine Claude conversations
│   │   └── SKILL.md
│   └── data-ingest/                     # Process logs, transcripts, exports
│       └── SKILL.md
│
├── docs/
│   ├── vault-audit.md                   # Vault structure audit & recommendations
│   └── onboarding-guide.md             # New project onboarding checklist
│
├── CLAUDE.md                            # Plugin-level instructions
├── .gitmodules                          # Submodule references
│
│  # --- obsidian-wiki skills: COPIED and ADAPTED from the submodule.
│  #     Post-vault-restructuring audit found that 9 of 10 skills need real
│  #     adaptation (category structure, frontmatter schema, .env replacement).
│  #     Only cross-linker can be symlinked. Submodule kept as upstream reference. ---
│
│  # --- Submodules (reference/audit, not skills source) ---
├── ArkNode-AI/
├── ArkNode-Poly/
├── Arknode-AI-Obsidian-Vault/
├── Arknode-Poly-Obsidian-Vault/
├── linear-updater/
├── tasknotes/
└── obsidian-wiki/
```

**Total: 14 shared skills** (3 generalized from existing + 1 new tasknotes + 10 from obsidian-wiki)

**Note on `claude-history-ingest`:** This skill reads `~/.claude/` to mine past Claude conversations into vault knowledge. This is intentional and expected — it reads conversation history, not skill definitions. No filesystem boundary issues.

### Obsidian-Wiki Skill Adaptation (Post-Vault-Restructuring)

The vault restructuring (completed 2026-04-07) added `_meta/vault-schema.md`, `_meta/taxonomy.md`, `_meta/generate-index.py`, `index.md`, `summary:` frontmatter on all 495 pages, and `Compiled-Insight-Template.md`. These new artifacts change how the obsidian-wiki skills must operate.

**Key incompatibilities with upstream obsidian-wiki:**
1. **Category structure:** obsidian-wiki expects `concepts/`, `entities/`, `skills/`. Ark vaults use domain-specific folders (`Infrastructure/`, `Trading-Signal-AI/`, `ArkNode-Poly/Architecture/`). Skills must respect existing folder structure.
2. **Frontmatter schema:** obsidian-wiki expects `sources:`, `provenance:`, `category:`. Ark vaults use `source-sessions:`, `source-tasks:`, `type:`. Skills must understand Ark conventions.
3. **`.env` dependency:** obsidian-wiki skills read `OBSIDIAN_VAULT_PATH` from `.env`. Ark skills use context-discovery from CLAUDE.md. Every skill needs this swapped.
4. **`.manifest.json` not used:** Delta ingestion tracking deferred per audit recommendation. Skills must work without it.

**Per-skill adaptation level:**

| Skill | Adaptation | What Changes |
|-------|-----------|-------------|
| `wiki-query` | Copy + adapt | Use `index.md` + `summary:` for tiered retrieval; read CLAUDE.md not `.env`; read `vault-schema.md` first for navigation |
| `wiki-lint` | Copy + adapt | Validate `summary:` exists (<=200 chars); validate tags against vault's `_meta/taxonomy.md`; check `index.md` is current; skip `provenance:` checks |
| `wiki-status` | Copy + light adapt | Read `index.md` for vault stats; replace `.env` with context-discovery |
| `tag-taxonomy` | Copy + adapt | Validate against vault's own `_meta/taxonomy.md` (not generic wiki tags); flag tags not in taxonomy |
| `wiki-update` | Copy + adapt | Regenerate `index.md` via `_meta/generate-index.py`; update `vault-schema.md` if structure changes; add `summary:` to new pages |
| `wiki-setup` | Copy + heavy adapt | Create Ark vault structure: TaskNotes/ with templates, `_meta/` with schema + taxonomy + generate-index.py, `_Templates/` with Compiled-Insight template, `00-Home.md` |
| `wiki-ingest` | Copy + heavy adapt | Place pages in existing domain folders (not generic categories); use Ark frontmatter schema; add `summary:` field; skip `provenance:` |
| `claude-history-ingest` | Copy + adapt | Use Compiled-Insight-Template for synthesis; add `summary:` to output; place in Research/Compiled-Insights/ |
| `data-ingest` | Copy + adapt | Same as claude-history-ingest |
| `cross-linker` | Copy + adapt | Upstream depends on `.env` and `log.md` — must be adapted like the others |

**Drift management:** Since 9 of 10 skills are copies, periodically diff against upstream `obsidian-wiki/.skills/` for workflow improvements that can be ported. The upstream is reference, not source of truth.

---

## 2. Skill Generalization

### 2a. ark-code-review

**Source:** trading-signal-ai (770 lines) and ArkNode-Poly (638 lines)

**Changes needed:**
- Replace hardcoded `ArkSignal-`/`ArkPoly-` with context-discovery: "read project's task prefix from CLAUDE.md"
- Replace `vault/Trading-Signal-AI/Session-Logs/` and `vault/ArkNode-Poly/` with: "read vault path from CLAUDE.md"
- Make epic-review mode vault-agnostic — discover epic file location from vault structure
- Remove project-specific test path patterns (e.g., `tests/ark_train/`); instruct agent to discover test structure
- Make deployment follow-up actions conditional on CLAUDE.md declaring deployment targets
- Keep the multi-agent orchestration pattern (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) — this is project-agnostic

### 2b. codebase-maintenance

**Source:** trading-signal-ai (192 lines + 6 workflows + 2 references) and ArkNode-Poly (131 lines + 1 reference)

**Changes needed:**
- Remove hardcoded CT100/CT110/CT120 IPs and container names
- Make infrastructure audit sections conditional: "if CLAUDE.md defines deployment targets, check deployed commit drift"
- Make dashboard sync conditional: "if CLAUDE.md defines a monitoring dashboard, verify dashboard-code alignment"
- Generalize cleanup checklist — keep universal items (dead code, unused imports, broken tests), make infra items conditional
- Move ArkNode-AI-specific workflow files (sync-dashboard.md, sync-deploy-scripts.md) to project-level guidance in trading-signal-ai's CLAUDE.md
- Keep universal workflows: cleanup-code.md, sync-vault.md, sync-skills.md
- **Post-restructuring:** Add vault maintenance step: regenerate `index.md` via `_meta/generate-index.py`, run wiki-lint for broken links, validate tags against `_meta/taxonomy.md`

### 2c. notebooklm-vault

**Source:** trading-signal-ai (525 lines + sync script) and ArkNode-Poly (435 lines + sync script)

**Changes needed:**
- Replace notebook name hardcoding with: "read notebook config from the **project repo's** `.notebooklm/config.json`" (this is the tracked, authoritative config. The vault repo holds `.notebooklm/sync-state.json` which is runtime state, not config)
- Generalize vault directory discovery — don't assume `vault/Trading-Signal-AI/` vs `vault/ArkNode-Poly/`
- Make dual-notebook logic conditional: "if config has multiple notebooks, query each"
- Parameterize sync script for configurable notebook keys
- Replace project-specific obsidian search examples with generic patterns
- Make TaskNote sync behavior configurable (AI vault syncs TaskNotes to NotebookLM; Poly doesn't)
- **Post-restructuring:** Leverage `index.md` and `summary:` fields for efficient vault querying — scan summaries first, open full pages only when needed (tiered retrieval). Reference `vault-schema.md` for navigation context.

---

## 3. Agent-Driven TaskNotes Automation

### 3a. Integration Architecture

```
Claude Code agent (during any workflow)
        │
        ▼
ark-tasknotes skill instructs agent to use MCP tools
        │
        ▼
tasknotes MCP endpoint (HTTP POST /mcp on Obsidian plugin)
        │
        ▼
Creates/updates .md files in project's vault TaskNotes/
        │
        ▼
linear-updater polls vault repo (5-min interval)
        │
        ▼
Syncs to Linear (creates/updates issues)
```

**Important:** The tasknotes MCP server is NOT a standalone Node process. It is an HTTP endpoint (`/mcp`) inside the Obsidian plugin itself, gated by `enableMCP` and `enableAPI` settings. **Obsidian must be running** with the tasknotes plugin active for MCP to work. Each MCP request is stateless — a new `McpServer` instance is created per request via `StreamableHTTPServerTransport`.

### 3b. Per-Project MCP Configuration

Each project's Obsidian vault must have the tasknotes plugin configured with:
- `enableAPI: true` — starts the HTTP API server (default port 8080)
- `enableMCP: true` — enables the `/mcp` endpoint
- `apiAuthToken` (optional) — Bearer token for authentication

Each project's `.claude/settings.json` registers an MCP endpoint pointing to its vault's Obsidian instance:

```json
{
  "mcpServers": {
    "tasknotes": {
      "type": "url",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

**Per-project routing:** Since each project's vault runs in its own Obsidian instance (potentially on different ports), the port in the URL differentiates which vault is targeted. Alternatively, if vaults share one Obsidian instance, the MCP server operates on whichever vault is currently open.

### 3c. ark-tasknotes Skill Design

The skill defines:

**When agents auto-create tasks:**
- Bug discovered during code review → creates Bug ticket with repro steps
- Feature completed → creates follow-up Story for testing/deployment verification
- Tech debt identified during codebase-maintenance → creates Task
- Incident debugged → creates Bug with root cause and fix details

**Task creation conventions:**
- `tasknotes_create_task` accepts: `title` (required), `status`, `priority`, `due`, `scheduled`, `tags`, `contexts`, `projects`, `recurrence`, `timeEstimate`, `details`
- It does NOT accept `task-id`, `task-type`, `work-type`, or `component` — `tasknotes_update_task` also cannot add these custom fields (it only supports the same limited schema). The skill must directly edit the markdown file after creation to add Ark-specific frontmatter
- Task ID prefix discovered from project CLAUDE.md
- Auto-increment task ID by reading `TaskNotes/meta/{Prefix}-counter` (e.g., `ArkSignal-counter`, `ArkPoly-counter`) — each project prefix has its own counter file
- Cross-reference related tasks via `related:` wikilinks (added via post-creation edit)
- New tasks default to `status: backlog` unless explicitly urgent

**Guardrails:**
- Never auto-close tasks — only create and update to in-progress
- Critical/blocking tasks require user confirmation before creation
- Duplicate detection — query existing tasks via MCP before creating
- Agent announces task creation to user (no silent side-effects)

**MCP tool usage patterns (actual tool names from MCPService.ts):**
- `tasknotes_create_task` — create new task (title required; status, priority, due, tags, projects, details optional)
- `tasknotes_update_task` — update task properties
- `tasknotes_query_tasks` — advanced filtering with AND/OR logic, sorting, grouping (replaces simple search)
- `tasknotes_get_task` — get task by file path (NOT task-id)
- `tasknotes_list_tasks` — list tasks with pagination
- `tasknotes_toggle_status` — cycle task status
- `tasknotes_get_stats` — task statistics (counts by status, priority, overdue)
- `tasknotes_health_check` — verify MCP server is running

**Limitation:** The MCP `create_task` tool uses a simplified schema. Custom frontmatter fields used by the Ark ecosystem (task-id, task-type, work-type, component, urgency, severity) are not natively supported. The skill must either:
1. Create via MCP, then edit the markdown file to add custom frontmatter, OR
2. Write the markdown file directly with full frontmatter, bypassing MCP for creation but using MCP for queries and status updates

### 3d. Error Handling & Failure Modes

Task creation is the only stateful operation in this system. The skill must handle:

- **Obsidian not running / MCP disabled:** `tasknotes_health_check` returns error → skill falls back to direct markdown file write with correct frontmatter
- **Counter races:** Two agents incrementing `TaskNotes/meta/{Prefix}-counter` simultaneously → use file locking or accept occasional gaps (IDs don't need to be strictly sequential)
- **Duplicate tasks from polling lag:** linear-updater's 5-min poll means a task created and immediately synced could appear as "new" on next poll → linear-updater already handles this via SQLite state tracking (task-id mapping)
- **Partial failure (vault write succeeds, Linear sync fails):** linear-updater retries on next poll cycle; no manual intervention needed
- **Auth failure on /mcp:** Surface the error to user with instructions to check `apiAuthToken` setting in Obsidian
- **Wrong vault targeted:** Skill verifies vault identity by checking `TaskNotes/meta/{Prefix}-counter` exists before creating tasks; if missing, alert user that MCP may point to wrong vault

---

## 4. Vault Audit & Restructuring Recommendations

### 4a. Current State Comparison

| Aspect | AI Vault (321 files) | Poly Vault (181 files) |
|--------|---------------------|----------------------|
| Templates | 4 (Container, Model, Service, Session) | 6 (adds Bug, Research, Task) |
| Archive structure | Flat | Categorized (Bug/, Epic/, Story/, Enhancement/) |
| Plugins | obsidian-git, tasknotes, local-rest-api, **livesync** | obsidian-git, tasknotes, local-rest-api (no livesync) |
| Active tasks | ~68 | ~37 |
| Session logs | In Trading-Signal-AI/ | 24 in ArkNode-Poly/Session-Logs/ |
| Architecture docs | Scattered in Infrastructure/ | Dedicated Architecture/ section |
| Task prefix | ArkSignal- | ArkPoly- |

### 4b. Inconsistencies to Resolve

1. **Templates**: AI vault missing Bug-Template, Research-Template, Task-Template that Poly has. Standardize to 6 templates.
2. **Archive structure**: AI vault uses flat archive; Poly uses categorized. Adopt Poly's categorized approach.
3. **LiveSync plugin**: Missing from Poly vault. Either add it or document why it's excluded.
4. **Architecture documentation**: AI vault scatters infra docs across Infrastructure/. Consider dedicated Architecture/ section like Poly.

### 4c. obsidian-wiki Assessment

**What the vaults already do well:**
- Compiled knowledge in Architecture/, Research/, Operations/ (partial three-layer pattern)
- Consistent TaskNotes schema with Obsidian Bases views
- Session logging with structured frontmatter
- NotebookLM sync for cross-session AI context

**Gaps the obsidian-wiki skills would fill:**
- **No manifest tracking** — no `.manifest.json` to track what's been ingested vs. what's new
- **No delta ingestion** — can't tell what knowledge has changed since last session
- **No automated cross-linking** — wikilinks are manually maintained
- **No lint/audit workflow** — no way to find broken links, orphaned pages, contradictions
- **No tag taxonomy enforcement** — tags drift between vaults
- **Session logs not compiled** — raw session logs accumulate but aren't synthesized into knowledge pages

**Decision:** The 10 obsidian-wiki skills are included as shared skills in the plugin (tooling decision).

### 4d. Vault Audit Results (completed)

Full audit at `docs/vault-audit.md`. Key findings:

- **Three-layer assessment:** Strong wiki layer (5.1 links/file, 99.1% frontmatter coverage, zero orphans in AI vault). Missing raw sources layer and explicit schema layer.
- **Core problem:** Session log knowledge burial — 103 AI vault session logs with hard-won insights (TFT verdict, condition filter alpha, spot-to-perp outcomes) buried in chronological journals, inaccessible to retrieval.
- **LLM fitness gaps:** No `summary:` frontmatter for tiered retrieval, no machine-readable index, no vault schema doc.
- **Current strengths to preserve:** TaskNotes schema, session log chaining, MOC hierarchy, cross-linking density, canvas diagrams.
- **Recommendation:** Incremental adoption (Option B) with targeted session log extraction (Option C partial). No full restructure needed.

### 4e. Vault Restructuring (executing in parallel)

Implementation plan at `docs/superpowers/plans/2026-04-07-vault-restructure.md`. Currently executing in a separate session. Three phases:

1. **Phase 1:** Session log knowledge extraction — compile 5 insight pages from AI vault's 103 session logs
2. **Phase 2:** LLM navigation improvements — add `summary:` frontmatter, generate `index.md`, write `_meta/vault-schema.md`
3. **Phase 3:** Automated maintenance — run wiki-lint, create tag taxonomy, cross-linker pass

**Implication for this plugin:** The obsidian-wiki skills (wiki-lint, cross-linker, tag-taxonomy) should be integrated into the plugin after the vault restructuring is complete, so they operate on well-structured vaults with established conventions (summaries, taxonomy, schema docs).

---

## 5. New Project Onboarding

When a new project joins the ecosystem:

1. **Create Obsidian vault** — use wiki-setup skill to initialize standard structure (TaskNotes/, _Templates/, _Attachments/, 00-Home.md)
2. **Install this plugin** — add create-ark-skills as a Claude Code plugin; all 14 shared skills become available
3. **Configure project CLAUDE.md** — declare project name, task prefix, vault path, deployment targets (if any), notebook config
4. **Configure tasknotes MCP** — add tasknotes MCP server to project's `.claude/settings.json` pointing to new vault
5. **Add vault to linear-updater** — **requires code changes**: `linear-updater/src/config.ts` is currently hardcoded for exactly 2 vaults (`VAULT_AI_PATH` and `VAULT_POLY_PATH`). To support a third project, `loadConfig()` must be refactored to read a dynamic vault list (e.g., `VAULT_PATHS` as comma-separated or a config file). This is a prerequisite code change, not just `.env` config
6. **Set up NotebookLM sync** — create `.notebooklm/config.json` in project with notebook IDs; add sync timer on CT110
7. **Run wiki-lint** — baseline audit of vault structure

**Prerequisites (access requirements):**
- SSH key with access to the HelloWorldSungin GitHub org (5 of 7 submodules in this repo are private over SSH)
- SSH key on CT110 for vault sync and linear-updater deployment
- Linear API key for the target team
- Google NotebookLM access for the target notebook

`docs/onboarding-guide.md` will contain the detailed step-by-step with exact config examples.

---

## 6. Verification Plan

### Skills work across projects:
- Invoke each shared skill from both ArkNode-AI and ArkNode-Poly
- Verify context-discovery correctly reads each project's CLAUDE.md
- Confirm no hardcoded project-specific references remain

### TaskNotes automation:
- Configure tasknotes MCP server for one project
- Invoke ark-tasknotes skill to create a test task
- Verify task appears in vault with correct frontmatter (including custom fields like task-id, task-type)
- Verify linear-updater picks up the new task and syncs to Linear
- Test failure path: invoke skill with Obsidian closed, verify fallback to direct markdown write
- Test duplicate detection: create same task twice, verify dedup works

### Vault maintenance:
- Run wiki-lint on both vaults, compare results
- Run cross-linker on one vault, verify new wikilinks are appropriate
- Run wiki-status to see ingestion delta

### New project onboarding:
- Follow onboarding guide for a mock project
- Verify all skills function correctly with minimal config

---

## 7. Implementation Phases

### Phase 1: Plugin scaffolding & skill generalization
- Create plugin structure (skills/ directory, CLAUDE.md)
- Generalize ark-code-review, codebase-maintenance, notebooklm-vault
- Remove project-specific hardcoding, add context-discovery sections

### Phase 2a: obsidian-wiki skill adaptation (light)
- Copy and adapt 4 skills with light adaptation: wiki-query, wiki-status, wiki-update, tag-taxonomy
- Symlink cross-linker (no adaptation needed)
- Key changes: replace `.env` with context-discovery, leverage `index.md`/`summary:`/`vault-schema.md`/`taxonomy.md`
- Test on both vaults

### Phase 2b: obsidian-wiki skill adaptation (heavy)
- Copy and adapt 5 skills with heavy adaptation: wiki-setup, wiki-ingest, wiki-lint, claude-history-ingest, data-ingest
- Key changes: use Ark folder structure instead of generic categories, use Ark frontmatter schema, use Compiled-Insight template for synthesis, skip provenance/manifest checks
- Test on both vaults

### Phase 3: ark-tasknotes skill
- Design and implement the new tasknotes automation skill
- Handle MCP limitation: create via MCP then edit markdown for custom frontmatter, OR direct markdown write with MCP for queries only
- Document Obsidian plugin config requirements (enableAPI, enableMCP, port)
- Implement fallback for Obsidian-not-running scenario
- Test end-to-end: skill → MCP → vault → linear-updater → Linear

### Phase 4: Vault audit & documentation
- Produce detailed vault-audit.md
- Write onboarding-guide.md with SSH/access prerequisites
- Standardize vault inconsistencies (templates, archive structure)

### Phase 5: linear-updater extensibility
- Refactor `linear-updater/src/config.ts` to support dynamic vault list instead of hardcoded 2-vault config
- Update `.env.example` with new vault config format
- Test with existing 2 vaults to ensure no regression

### Phase 6: Cleanup
- Remove duplicate skills from trading-signal-ai and ArkNode-Poly
- Update both projects' CLAUDE.md to reference shared skills
- Verify nothing breaks
