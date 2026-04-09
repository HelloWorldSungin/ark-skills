# Optimal Workflow Design — Weight-Class Skill Orchestration

**Date:** 2026-04-08
**Status:** Draft
**Author:** Sungin + Claude

## Overview

A situational workflow system that adapts ceremony to task size. Every task is triaged into a weight class (light / medium / heavy), which determines which skills from ArkSkill, gstack, and superpowers run and in what order. Designed for solo use across mixed projects (backend, frontend, infra).

## Design Decisions

- **Weight-class triage** over static checklists — ceremony scales with risk and complexity
- **Vault updates woven into every cycle** — not a separate maintenance activity
- **Session handoff at design→implementation boundary** — fresh context for implementation (medium+)
- **`/notebooklm-vault` sync excluded** — runs on a separate server, not part of local workflows
- **`/document-release` conditional** — only when project has standard docs outside `docs/superpowers/`
- **Session logs are retrospective** — written at the end, capturing decisions and rationale

---

## Triage System

Every task starts with a 10-second classification. The highest column in any factor wins.

| Factor | Light | Medium | Heavy |
|--------|-------|--------|-------|
| **Files touched** | 1-3 | 4-10 | 10+ |
| **Risk** | Low (internal, non-breaking) | Moderate (API changes, schema) | High (infra, auth, data migration) |
| **Has UI?** | No | Maybe | Yes, user-facing |
| **Duration** | < 30 min | 30 min - few hours | Half day+ |
| **Decision density** | Obvious fix | Some trade-offs | Architecture choices |

### Phase Matrix

| Phase | Light | Medium | Heavy |
|-------|-------|--------|-------|
| **Design** | skip | `/brainstorming` → `/codex` review spec | `/brainstorming` → `/writing-plans` → `/codex` review spec + plan |
| **Session Handoff** | skip | Commit spec → fresh session | Commit spec + plan → fresh session |
| **Implement** | direct code | `/TDD` | `/TDD` + `/subagent-driven-development` |
| **Checkpoint** | skip | skip | `/checkpoint` (optional, if pausing mid-implementation) |
| **Review** | self-review | `/ark-code-review --quick` → `/simplify` | `/ark-code-review --thorough` + `/codex` → `/simplify` |
| **Browser QA** | skip | `/qa` (if UI) | `/qa` + `/design-review` (if UI) |
| **Ship** | `/ship` → `/land-and-deploy` | `/ship` → `/land-and-deploy` | `/ship` → `/land-and-deploy` → `/canary` |
| **Document** | `/wiki-update` | `/wiki-update` + session log | `/wiki-update` + session log + `/claude-history-ingest` |
| **New Concepts** | skip | `/wiki-ingest` if new page needed | `/wiki-ingest` if new page needed |
| **Vault Links** | skip | `/cross-linker` | `/cross-linker` |
| **Project Docs** | `/document-release`* | `/document-release`* | `/document-release`* |
| **Security** | skip | skip | `/cso` (if infra/auth) |

*Only if project has standard docs (README, ARCHITECTURE, CONTRIBUTING, CHANGELOG) outside `docs/superpowers/`.

---

## Scenario Workflows

### Scenario 1: Greenfield Feature

*Building something new from scratch.*

**Design & Planning (Session 1):**

1. **Triage** — classify as medium or heavy (light greenfield is rare)
2. `/brainstorming` — explore intent, propose approaches, write spec
3. `/codex` — review the spec, challenge assumptions
4. `/writing-plans` (heavy only) — break into phased implementation plan
5. `/codex` (heavy only) — review the plan
6. Commit spec + plan → **end session**

**Implementation (Session 2 — fresh context):**

7. Read spec + plan from disk
8. `/executing-plans` — execute with review checkpoints
9. `/TDD` — write tests first, implement against them
10. `/subagent-driven-development` (heavy only) — parallelize independent modules
11. `/checkpoint` (heavy, optional) — if pausing mid-implementation, save state and resume in fresh Session 3
12. `/ark-code-review` — review the diff (`--quick` for medium, `--thorough` for heavy)
13. `/codex` (heavy only) — independent code review
14. `/simplify` — clean up reviewed code
15. `/qa` (if UI) — browser-based QA testing
16. `/design-review` (heavy + UI) — visual polish and consistency
17. `/ship` → `/land-and-deploy` → `/canary` (heavy only)

**Document (end of implementation session):**

18. `/wiki-update` — sync changes to vault
19. `/wiki-ingest` — if new component/concept needs its own vault page
20. `/cross-linker` — connect new/updated pages
21. `/document-release` — if standard project docs exist outside `docs/superpowers/`
22. Session log — capture decisions and rationale
23. `/claude-history-ingest` (heavy only) — mine session for compiled insights

---

### Scenario 2: Bug Investigation & Fix

*Something's broken, find and fix it.*

1. **Triage** — most bugs start light, re-triage if deeper than expected
2. `/investigate` — systematic root cause analysis (no fixes without understanding)
3. **Re-triage** if the bug is deeper than expected
4. `/TDD` (medium+) — write a failing test that reproduces the bug
5. Fix — direct code for light, structured for medium+
6. `/ark-code-review --quick` (medium+) → `/simplify`
7. `/qa` (medium+, if UI) — verify the fix in browser
8. `/ship` → `/land-and-deploy`
9. `/wiki-update` — document what broke and why
10. Session log — if surprising root cause (always for medium+)

---

### Scenario 3: Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump.*

1. `/review` — pre-landing PR diff review
2. `/ship` → `/land-and-deploy`
3. `/canary` (if risky change) — post-deploy monitoring
4. `/wiki-update`

---

### Scenario 4: Knowledge Capture

*Catch up the vault with what's happened.*

1. `/wiki-status` — see what's stale, get vault statistics
2. `/wiki-lint` — find broken links, missing frontmatter, tag violations
3. `/wiki-update` — sync recent changes into vault pages
4. `/wiki-ingest` — if external documents need distilling into vault
5. `/cross-linker` — discover and add missing wikilinks
6. `/tag-taxonomy` — normalize tags against canonical taxonomy
7. `/claude-history-ingest` — mine recent sessions for compiled insights
8. Session log — summarize what was captured

---

### Scenario 5: Codebase Hygiene

*Cleanup, refactor, security audit.*

1. **Triage** — size the cleanup
2. `/codebase-maintenance` — audit dead code, drifted skills, vault sync
3. `/cso` (if security-relevant) — infrastructure and dependency audit
4. `/TDD` (medium+ refactoring) — tests before restructuring
5. Implement cleanup
6. `/ark-code-review` → `/simplify` — review the cleanup diff
7. `/ship` → `/land-and-deploy`
8. `/wiki-update` + session log

---

## Vault Drift Prevention

Vault drift is managed through two layers:

**Per-cycle (every workflow):**
- `/wiki-update` runs in the Document phase — checks if files touched in the current work overlap with existing vault pages
- `/wiki-ingest` as fallback — if a new component/concept was introduced and `/wiki-update` didn't create a page for it
- `/cross-linker` — reconnects pages after updates

**Periodic audit (Scenario 4 — Knowledge Capture):**
- Run when vault feels stale or before retros
- Full vault health check: `/wiki-status` → `/wiki-lint` → `/wiki-update` → `/cross-linker` → `/tag-taxonomy`

---

## Session Management

**Design → Implementation handoff (medium+):**
- Spec and plan are committed to `docs/superpowers/specs/` during Session 1
- Session 1 ends after spec/plan are reviewed and committed
- Session 2 starts fresh, reads spec + plan from disk
- No `/checkpoint` needed — committed files are the handoff artifact

**Mid-implementation pause (heavy, optional):**
- When a heavy task spans multiple sessions or context gets large
- `/checkpoint` saves git state, decisions made, remaining work
- Fresh session reads checkpoint to resume exactly where you left off

---

## Skill Inventory Reference

### Superpowers (process/meta)
| Skill | Role in Workflow |
|-------|-----------------|
| `/brainstorming` | Design phase — explore intent, write spec |
| `/writing-plans` | Design phase (heavy) — phased implementation plan |
| `/executing-plans` | Implementation — execute plan with checkpoints |
| `/TDD` | Implementation — tests before code |
| `/subagent-driven-development` | Implementation (heavy) — parallelize modules |
| `/simplify` | Review — clean up post-review |
| `/verification-before-completion` | Implicit — verify before claiming done |
| `/dispatching-parallel-agents` | Implementation (heavy) — parallel independent tasks |
| `/systematic-debugging` | Bug investigation — root cause analysis |
| `/requesting-code-review` | Review phase — trigger review |
| `/receiving-code-review` | Review phase — process feedback |
| `/finishing-a-development-branch` | Ship phase — integration decisions |
| `/using-git-worktrees` | Implementation — isolated feature work |
| `/checkpoint` | Mid-implementation pause (heavy) |

### gstack (external tooling)
| Skill | Role in Workflow |
|-------|-----------------|
| `/codex` | Design — review spec/plan; Review — independent code review |
| `/investigate` | Bug investigation — root cause analysis |
| `/qa` | Browser QA — test UI in browser |
| `/design-review` | Browser QA (heavy + UI) — visual consistency |
| `/review` | Ship — pre-landing PR diff review |
| `/ship` | Ship — create PR, bump version, push |
| `/land-and-deploy` | Ship — merge, wait for CI, verify production |
| `/canary` | Ship (heavy) — post-deploy monitoring |
| `/cso` | Security — infrastructure and dependency audit |
| `/document-release` | Document — update standard project docs |
| `/codebase-maintenance` (via ArkSkill) | Hygiene — audit dead code, drifted skills |
| `/checkpoint` | Mid-implementation pause |
| `/retro` | Periodic — weekly engineering retrospective |
| `/benchmark` | QA (if performance-sensitive) — regression detection |

### ArkSkill (custom)
| Skill | Role in Workflow |
|-------|-----------------|
| `/ark-code-review` | Review — multi-agent code review |
| `/ark-tasknotes` | Task management — create/manage tickets |
| `/codebase-maintenance` | Hygiene — repo cleanup, vault sync, skill health |
| `/wiki-update` | Document — sync changes to vault |
| `/wiki-ingest` | Document — distill new concepts into vault pages |
| `/wiki-lint` | Knowledge capture — audit vault health |
| `/wiki-status` | Knowledge capture — vault statistics |
| `/wiki-setup` | One-time — initialize new vault |
| `/wiki-query` | Ad-hoc — answer questions from vault |
| `/cross-linker` | Document — discover missing wikilinks |
| `/tag-taxonomy` | Knowledge capture — normalize tags |
| `/claude-history-ingest` | Document (heavy) — mine sessions for insights |
| `/data-ingest` | Knowledge capture — process logs/transcripts |
| `/notebooklm-vault` | Server-side — excluded from local workflow |
