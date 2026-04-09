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
- **Distributed as skill + routing rules** — single source of truth in `/ark-workflow` skill, routing rules trigger it automatically

---

## Triage System

Every task starts with a 10-second classification. **Risk is the primary signal** — a one-file auth change is heavy regardless of file count or duration. Use the other factors as tiebreakers when risk is ambiguous.

| Factor | Light | Medium | Heavy |
|--------|-------|--------|-------|
| **Risk** | Low (internal, non-breaking) | Moderate (API changes, schema) | High (infra, auth, data migration, secrets, permissions) |
| **Decision density** | Obvious fix | Some trade-offs | Architecture choices |
| **Files touched** | 1-3 | 4-10 | 10+ |
| **Duration** | < 30 min | 30 min - few hours | Half day+ |
| **Has UI?** | No | Maybe | Yes, user-facing changes |

**Re-triage rule:** If a task reveals more complexity mid-flight (e.g., a "light" bug turns out to involve auth), escalate to the appropriate class and pick up the remaining phases from there. Don't restart — just add the phases you would have run.

### Phase Matrix

This matrix is a **summary**. The scenario workflows below are authoritative when they diverge.

| Phase | Light | Medium | Heavy |
|-------|-------|--------|-------|
| **Design** | skip | `/brainstorming` → `/codex` review spec | `/brainstorming` → `/writing-plans` → `/codex` review spec + plan |
| **Session Handoff** | skip | Commit spec → fresh session | Commit spec + plan → fresh session |
| **Implement** | direct code | `/executing-plans` with `/TDD` per step | `/executing-plans` with `/TDD` per step + `/subagent-driven-development` for independent modules |
| **Checkpoint** | skip | skip | `/checkpoint` (optional, if pausing mid-implementation) |
| **Review** | self-review | `/ark-code-review --quick` → `/simplify` | `/ark-code-review --thorough` + `/codex` → `/simplify` |
| **Browser QA** | skip | `/qa` (if UI) | `/qa` + `/design-review` (if UI) |
| **Ship** | `/ship` → `/land-and-deploy` | `/ship` → `/land-and-deploy` | `/ship` → `/land-and-deploy` |
| **Post-deploy** | skip | `/canary` (if deploy risk†) | `/canary` (if deploy risk†) |
| **Document** | `/wiki-update` | `/wiki-update` + session log | `/wiki-update` + session log + `/claude-history-ingest` |
| **New Concepts** | skip | `/wiki-ingest` if new page needed | `/wiki-ingest` if new page needed |
| **Vault Links** | skip | `/cross-linker` | `/cross-linker` |
| **Project Docs** | `/document-release`* | `/document-release`* | `/document-release`* |
| **Security** | `/cso` (if security-relevant‡) | `/cso` (if security-relevant‡) | `/cso` (if security-relevant‡) |

*Only if project has standard docs (README, ARCHITECTURE, CONTRIBUTING, CHANGELOG) outside `docs/superpowers/`.

†**Deploy risk triggers for `/canary`:** config changes affecting production, infra changes, auth/permissions changes, data migrations, dependency upgrades with breaking changes. Not gated on weight class — a light config change can be high deploy risk.

‡**Security-relevant triggers for `/cso`:** auth/permissions changes, secrets handling, dependency upgrades, data exposure risks, infrastructure changes, new external API integrations. Any weight class can trigger this.

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
8. `/executing-plans` — execute the plan with review checkpoints; within each plan step, use `/TDD` (write tests first, then implement against them)
9. `/subagent-driven-development` (heavy only) — parallelize independent modules that don't share state
10. `/checkpoint` (heavy, optional) — if pausing mid-implementation, save state and resume in fresh Session 3
11. `/ark-code-review` — review the diff (`--quick` for medium, `--thorough` for heavy)
12. `/codex` (heavy only) — independent code review
13. `/simplify` — clean up reviewed code
14. `/qa` (if UI) — browser-based QA testing
15. `/design-review` (heavy + UI) — visual polish and consistency
16. `/ship` → `/land-and-deploy` → `/canary` (if deploy risk)

**Document (end of implementation session):**

17. `/wiki-update` — sync changes to vault
18. `/wiki-ingest` — if new component/concept needs its own vault page
19. `/cross-linker` — connect new/updated pages
20. `/document-release` — if standard project docs exist outside `docs/superpowers/`
21. Session log — capture decisions and rationale
22. `/claude-history-ingest` (heavy only) — mine session for compiled insights

---

### Scenario 2: Bug Investigation & Fix

*Something's broken, find and fix it.*

1. **Triage** — most bugs start light, re-triage if deeper than expected
2. `/investigate` — systematic root cause analysis (no fixes without understanding)
3. **Re-triage** if the bug is deeper than expected — pick up additional phases from the new weight class
4. `/TDD` (medium+) — write a failing test that reproduces the bug; if not reproducible (race condition, prod-only data), document why and proceed with fix + monitoring
5. Fix — direct code for light, structured for medium+
6. `/ark-code-review --quick` (medium+) → `/simplify`
7. `/qa` (medium+, if UI) — verify the fix in browser
8. `/cso` (if fix touches security-relevant code) — verify no new exposure
9. `/ship` → `/land-and-deploy` → `/canary` (if deploy risk)
10. `/wiki-update` — document what broke and why
11. Session log — if surprising root cause (always for medium+)

---

### Scenario 3: Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump.*

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant) — check the diff for exposure
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk) — post-deploy monitoring
5. `/wiki-update`

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
3. `/cso` (if security-relevant) — infrastructure, dependency, and secrets audit
4. `/TDD` (medium+ refactoring) — tests before restructuring
5. Implement cleanup
6. `/ark-code-review` → `/simplify` — review the cleanup diff
7. `/ship` → `/land-and-deploy` → `/canary` (if deploy risk)
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
- Spec and plan are committed to `docs/superpowers/specs/` on the feature branch (or `master` if working directly)
- Session 1 ends after spec/plan are reviewed by `/codex` and committed
- Session 2 starts fresh, reads spec + plan from disk
- No `/checkpoint` needed — committed files are the handoff artifact
- **Cleanup:** Spec files are permanent project history — they stay committed. If a task is abandoned, note "Status: Abandoned" in the spec frontmatter rather than deleting it

**Mid-implementation pause (heavy, optional):**
- When a heavy task spans multiple sessions or context gets large
- `/checkpoint` saves git state, decisions made, remaining work
- Fresh session reads checkpoint to resume exactly where you left off

---

## Session Log vs. Auto-Capture Clarification

Three layers of knowledge capture work together — they are complementary, not redundant:

| Layer | Mechanism | When | Signal |
|-------|-----------|------|--------|
| **Raw history** | `ark-history-hook.sh` (Stop hook) | Automatic, every session end | Lossless but noisy — indexes full conversations into MemPalace ChromaDB |
| **Session log** | Manual retrospective in `vault/Session-Logs/` | End of medium+ tasks (or light if surprising) | High-signal summary — decisions, rationale, what was built and why |
| **Compiled insights** | `/claude-history-ingest compile` | End of heavy tasks or periodic | Distilled patterns — mines raw history into thematic vault pages |

The Stop hook ensures **no raw context is ever lost**, even if you forget to write a session log. The session log is your **editorial layer** — the curated "what mattered" summary. Compiled insights emerge later by mining across multiple sessions for patterns.

This means Codex's concern about retrospective memory loss is mitigated: the raw history is always preserved automatically, and the session log captures the high-level framing while it's still fresh at the end of the work session.

---

## When Things Go Wrong

Workflows don't always follow the happy path. Here's how to handle common failure modes:

**Failed QA (`/qa` finds bugs):**
- Fix the bugs in the current session
- Re-run `/qa` to verify
- If fixes are substantial, re-run `/ark-code-review` on the new changes

**Failed deploy (`/land-and-deploy` fails):**
- Check CI logs for the failure
- If it's a test failure: fix and re-run `/ship`
- If it's an infra issue: investigate before retrying
- Do not force-merge past failing CI

**Review disagreement (`/ark-code-review` vs `/codex` conflict):**
- Read both opinions. They see different things.
- If both flag the same area, it's almost certainly a real issue
- If they disagree, use your judgment — you have the context they don't
- Document the resolution in the session log

**Flaky tests:**
- Do not skip or retry blindly — `/investigate` the flake
- If it's a known flake unrelated to your changes, note it and proceed
- If it's new, treat it as a bug in the current cycle

**Spec invalidated during implementation:**
- If the spec's assumptions turn out to be wrong mid-build, stop implementing
- Update the spec, re-run `/codex` review on the updated spec
- Resume implementation from the updated spec (this is a re-triage moment)

**Partial canary failure (`/canary` detects issues):**
- Investigate the specific failure signal
- If it's your change: rollback or hotfix (new light-class bug cycle)
- If it's pre-existing: document it and proceed

**Vault tooling failure (wiki skills error):**
- Vault documentation is important but not blocking — don't let a `/wiki-update` failure hold up a ship
- Note the failure, fix it in the next Knowledge Capture cycle

---

## Skill Inventory Reference

### Superpowers (process/meta)

Skills explicitly placed in scenario workflows:

| Skill | Role in Workflow |
|-------|-----------------|
| `/brainstorming` | Design phase — explore intent, write spec |
| `/writing-plans` | Design phase (heavy) — phased implementation plan |
| `/executing-plans` | Implementation — execute plan with checkpoints; `/TDD` runs within each plan step |
| `/TDD` | Implementation — tests before code, runs inside `/executing-plans` |
| `/subagent-driven-development` | Implementation (heavy) — parallelize independent modules |
| `/simplify` | Review — clean up post-review, pre-ship |
| `/systematic-debugging` | Bug investigation — root cause analysis (used by `/investigate`) |

Skills that operate implicitly (always active, not explicitly invoked):

| Skill | Role in Workflow |
|-------|-----------------|
| `/verification-before-completion` | Runs type-check/lint before claiming any task is done |
| `/dispatching-parallel-agents` | Used internally by `/subagent-driven-development` |
| `/requesting-code-review` | Triggered when `/ark-code-review` is invoked |
| `/receiving-code-review` | Triggered when processing review feedback |
| `/finishing-a-development-branch` | Triggered during `/ship` — guides merge/PR decisions |
| `/using-git-worktrees` | Optional — use when you want to isolate feature work from current branch |

### gstack (external tooling)
| Skill | Role in Workflow |
|-------|-----------------|
| `/codex` | Design — review spec/plan; Review — independent code review |
| `/investigate` | Bug investigation — systematic root cause analysis |
| `/qa` | Browser QA — test UI in browser |
| `/design-review` | Browser QA (heavy + UI) — visual consistency |
| `/review` | Ship — pre-landing PR diff review |
| `/ship` | Ship — create PR, bump version, push |
| `/land-and-deploy` | Ship — merge, wait for CI, verify production |
| `/canary` | Post-deploy — monitoring when deploy risk is present (any weight class) |
| `/cso` | Security — infra, dependency, secrets audit (any weight class, when security-relevant) |
| `/document-release` | Document — update standard project docs (outside `docs/superpowers/`) |
| `/checkpoint` | Mid-implementation pause (heavy) — save and resume working state |
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
| `/ark-workflow` | **Entry point** — triage, scenario detection, skill chain orchestration |

---

## Distribution Strategy

### The Skill: `/ark-workflow`

A new skill at `skills/ark-workflow/SKILL.md` that serves as the entry point for any task. Since ark-skills is a Claude Code plugin, this skill is automatically available in every project.

**What it does:**

1. **Project Discovery** — reads the current project's CLAUDE.md (per context-discovery pattern) to determine vault path, task prefix, whether standard docs exist, whether the project has UI, etc.
2. **Scenario Detection** — identifies which scenario applies (greenfield, bugfix, ship, knowledge capture, hygiene) based on user input or context
3. **Triage** — classifies the task as light/medium/heavy using the triage factors, with risk as primary signal
4. **Skill Chain Output** — presents the specific ordered list of skills to run for this task, with conditions resolved (e.g., "this project has no UI, skipping /qa" or "standard docs found at README.md, including /document-release")
5. **Phase Guidance** — for medium+, indicates the session handoff point ("commit spec + plan here, then start a fresh session")

**What it does NOT do:**
- Does not invoke the downstream skills itself — it outputs the chain for the user/Claude to follow
- Does not replace `/brainstorming` — if the chain starts with `/brainstorming`, that skill runs next
- Does not store state — the workflow is stateless; the spec and plan files are the state

### CLAUDE.md Routing Rules

A routing rules template that projects can add to their CLAUDE.md. This enables automatic detection — when Claude sees task patterns, it suggests invoking `/ark-workflow` instead of jumping straight into code.

```markdown
## Skill routing — Ark Workflow

When starting any non-trivial task, invoke `/ark-workflow` first to triage and get the
skill chain. Pattern triggers:

- "build", "create", "add feature", "new component" → /ark-workflow (greenfield)
- "fix", "bug", "broken", "error", "investigate" → /ark-workflow (bugfix)
- "ship", "deploy", "push", "PR", "merge" → /ark-workflow (ship)
- "document", "vault", "catch up", "knowledge" → /ark-workflow (knowledge capture)
- "cleanup", "refactor", "audit", "hygiene", "dead code" → /ark-workflow (hygiene)

For trivial tasks (single obvious change, no ambiguity), skip triage and work directly.
```

### Adding to a New Project

When setting up a new project in the Ark ecosystem:

1. The `/ark-workflow` skill is already available (ark-skills plugin is global)
2. Add the routing rules block to the project's CLAUDE.md
3. Run `/wiki-setup` if the project needs a vault (the workflow's Document phase depends on it)

No per-project configuration needed beyond the routing rules — context-discovery handles the rest at runtime.
