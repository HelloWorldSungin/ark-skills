---
title: "Session: /ark-workflow v2 Rewrite"
type: session-log
tags:
  - session-log
  - skill
  - plugin
  - workflow
  - refactor
summary: "Rewrote /ark-workflow SKILL.md to address 22 gaps: 7 scenarios, risk+density triage, batch triage, continuity mechanism, cross-session resume. Shipped 1.6.0 in 6 phases."
prev: "[[S002-Ark-Workflow-Skill]]"
epic: ""
session: "S003"
source-tasks: []
created: 2026-04-09
last-updated: 2026-04-09
---

# Session: /ark-workflow v2 Rewrite

## Objective

Rewrite `skills/ark-workflow/SKILL.md` to address 22 identified gaps (12 initial + 10 from two rounds of `/codex` review) that were causing incorrect triage for real-world usage patterns. The most impactful gap: multi-item batches (3-5 numbered items) got a single chain instead of per-item triage, and bug-like items inside Hygiene batches skipped root cause investigation.

## Context

- **Spec:** `docs/superpowers/specs/2026-04-09-ark-workflow-v2-design.md` (950 lines)
- **Plan:** `docs/superpowers/plans/2026-04-09-ark-workflow-v2.md` (1515 lines, 6 phases)
- **Prior audit + review** was done in earlier sessions (not mine). This session only executed the plan.
- **Branch:** `master` (direct, per phased-execution checkpoints)
- **Starting state:** `SKILL.md` at 391 lines, version 1.4.2. During the session, ended up at 858 lines, version 1.6.0 (1.5.0 was already taken earlier today by the `/ark-tasknotes status` feature in `ba01e77`).

## Work Done

### Phase 1 — Frontmatter + Project Discovery early-exit (`5c53b8e`)

Expanded the description trigger list to include "upgrade", "migrate", "slow", "optimize", "benchmark" so the new Migration and Performance scenarios auto-trigger. Added Step 8 to Project Discovery that short-circuits Knowledge Capture requests when `HAS_VAULT=false` — no point proceeding to triage if the chain can't run.

### Phase 2 — Scenario Detection (7) + Triage rewrite (`86aac84`)

Expanded scenarios from 5 to 7, adding **Migration** (upgrade, bump, migrate) and **Performance** (slow, optimize, benchmark, latency, profile) as first-class scenarios. Split security routing into two paths:

- **Security audit** → `Hygiene: Audit-Only` (findings only, no implementation/ship)
- **Security hardening** → `Hygiene` (L/M/H) with `/cso` promoted to step 1 and any later `/cso` deduped

Replaced the old factor-matrix triage ("light/medium/heavy based on risk + density + files + duration + UI") with **risk-primary + decision-density escalation**:

- Risk sets the floor (Low→Light, Moderate→Medium, High→Heavy)
- Decision density can escalate Light→Medium or anything→Heavy, but never downgrade
- File count and duration are informational only

This fixes the "20-file trivial rename = Heavy" misclassification (risk is Low, density is Obvious → Light) and the "1-file auth change = Light" misclassification (risk is High → Heavy regardless of density).

### Phase 3 — Batch Triage + Continuity (`5df78a2`)

Added two entirely new sections.

**Batch Triage** — activates when the prompt describes multiple distinct tasks (numbered, bulleted, or prose with "and also"). 4-step algorithm:
1. Root cause consolidation scan (ask user before consolidating — don't auto-group)
2. Per-item scenario + weight classification
3. Dependency detection heuristic (with user confirmation, not code analysis)
4. Grouping into parallel/sequential/separate-session chains

**Continuity** — hybrid TodoWrite + chain state file for durability:
- TodoWrite tasks per chain step for interactive reminders
- `.ark-workflow/current-chain.md` at project root with frontmatter (`scenario`, `weight`, `batch`, `created`, `handoff_marker`, `handoff_instructions`) + numbered checklist + Notes section
- After each step: check off the file, complete the TodoWrite task, announce "Next: [skill]", mark next task `in_progress`
- Cross-session resume: session-start check reads the file, rehydrates TodoWrite from unchecked items, handles `handoff_marker` for design→implementation breaks, flags chains >7 days as potentially stale
- Context recovery after compaction: re-read the chain file

### Phase 4 — Workflow Steps + 19 skill chain variants (`c2464c5`)

Added **Step 6.5 (Activate Continuity)** to the Workflow algorithm. Rewrote every skill chain across 7 scenarios:

- **Greenfield** L/M/H (3)
- **Bugfix** L/M/H (3) — Heavy now has explicit `/checkpoint` + pivot-to-Greenfield instructions
- **Ship** standalone (1)
- **Knowledge Capture** Light/Full (2) — split where Light is "sync recent" and Full is "catch up + rebuild tags + ingest"
- **Hygiene** Audit-Only/L/M/H (4) — `/investigate` added as conditional for bug-like items, Audit-Only ends with STOP + user choice
- **Migration** L/M/H (3) — Heavy has mandatory `/canary`
- **Performance** L/M/H (3) — Heavy has mandatory `/canary`, `/benchmark` on Medium and Heavy

Total: **19 chain variants**. Renamed `/TDD` → `/test-driven-development` across every chain (7 occurrences in the old version; ended with 0 `/TDD` and 12 `/test-driven-development` references).

### Phase 5 — Conditions, Handoff, Re-triage, Routing, .gitignore (`a7926ad`)

Tightened every remaining section:

- **Condition Resolution** — explicit trigger lists for security-relevant (both read AND write auth paths), deploy risk (includes DB schema changes even when non-breaking), investigation triggers (new), UI, standard docs
- **Session Handoff** — per-Heavy-scenario handoff points; dropped the unreliable "10 tool calls since last file read" trigger in favor of output-quality signals
- **Re-triage** — split into weight escalation and scenario shift with pivot examples (Bugfix → Greenfield, Performance → Migration, Hygiene → Bugfix)
- **When Things Go Wrong** — added entries for hygiene-reveals-bugs, migration-breaks-tests, batch-item-blocks-others
- **Routing Rules Template** — CLAUDE.md copy-paste block now includes session-resume, updated triggers for 7 scenarios, and after-each-step protocol
- **`.gitignore`** — added `.ark-workflow/` so chain state never pollutes repos

### Phase 6 — Verification + version bump (`f690ebf`)

Ran all structural and content verifications from the plan. Walked through smoke tests mentally:

- **Session A** (5 bugfix items — transaction isolation, ghost runs, payload drop, retry storms, MCP shutdown): all correctly Bugfix, weights Medium/Light/Medium/Heavy/Light, Heavy flagged for separate session
- **Session B** (file permissions + SSE tunnel + dashboard blocking): mixed scenarios — Bugfix Heavy, Bugfix Medium, Performance Light. The Performance item correctly routes to Performance, not Hygiene
- **Session C** (TS build break + ESLint cleanup): Bugfix Medium vs Hygiene Light — scenario split preserved
- **Security audit** → Hygiene Audit-Only → `/cso` → findings → STOP
- **Security hardening** → Hygiene Heavy with `/cso` at step 1, later `/cso` deduped
- **Decision-density escalation** ("redesign caching layer", low risk, architecture density) → Heavy
- **Cross-session resume** mental walkthrough: Session 2 reads `.ark-workflow/current-chain.md`, rehydrates TodoWrite, resumes from unchecked step

Bumped VERSION, plugin.json, marketplace.json from 1.5.0 → **1.6.0** (not 1.5.0 as the plan stated — `ba01e77` earlier today had already shipped 1.5.0 for the `/ark-tasknotes status` feature, and the user's "always bump on every push" rule doesn't allow reusing a version). Updated CHANGELOG.

## Commits

| Phase | Commit | Description |
|---|---|---|
| Docs | `f664ddd` | v2 spec + plan committed before implementation |
| 1 | `5c53b8e` | Frontmatter triggers + Project Discovery early-exit |
| 2 | `86aac84` | 5→7 scenarios + risk-primary/density triage |
| 3 | `5df78a2` | Batch Triage + Continuity sections (+209 lines) |
| 4 | `c2464c5` | 19 skill chain variants across 7 scenarios |
| 5 | `a7926ad` | Conditions/Handoff/Re-triage/Routing + .gitignore |
| 6 | `f690ebf` | Version bump 1.5.0→**1.6.0** + CHANGELOG |

## Key Decisions

- **Risk-primary triage with density escalation** instead of the old factor-matrix. The old matrix conflated four signals (risk, density, files, duration) and produced ambiguous results. The new rule makes the floor explicit: risk alone determines the minimum class, density can only push up.

- **Security routing split into two paths.** "Audit our auth" and "harden our auth" are fundamentally different requests — one wants findings, the other wants fixes. Conflating them produced chains that either over-promised remediation on audit requests or skipped findings on hardening requests. Separate paths + `/cso` dedup rule means `/cso` runs exactly once no matter the path.

- **Batch triage asks for confirmation, doesn't auto-consolidate.** Multiple bug reports may share a root cause, but the user's framing matters — we ask before collapsing #1/#2/#3 into a single investigation.

- **Hybrid continuity: TodoWrite + file.** TodoWrite is session-scoped and ephemeral; the chain file persists across sessions and survives context compaction. Neither alone is sufficient. The rehydration protocol reads the file on session start and re-creates TodoWrite tasks from unchecked items.

- **Version bump to 1.6.0, not 1.5.0.** The plan said 1.5.0, but `ba01e77` had already bumped to 1.5.0 earlier today. Followed the "always bump on push" rule and used 1.6.0. Surfaced this deviation to the user before committing.

## Open Items / Follow-ups

- **File size:** `SKILL.md` is now 858 lines. Proposed a split into main + `chains/` + `references/` directories (~55% context reduction on the common triage path). **Deferred** as a Hygiene Medium follow-up — see `TODO.md` at the repo root. Rationale: let 1.6.0 run in practice first to surface any latent v2 bugs before restructuring on top.

- **Pre-existing S002 collision:** `vault/Session-Logs/` has two S002 files (`S002-Ark-Workflow-Skill.md` and `S002-Vault-Retrieval-Tiers-Phase1.md`). This session uses **S003** to avoid extending the collision. Renumbering S002 is out of scope here.

- **Smoke tests were mental, not executed.** The skill is markdown, so there's no test harness. Real validation comes from the next few `/ark-workflow` invocations in practice.

## Files Changed

- `skills/ark-workflow/SKILL.md` (391 → 858 lines)
- `.gitignore` (added `.ark-workflow/`)
- `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (1.5.0 → 1.6.0)
- `CHANGELOG.md` (new 1.6.0 entry)
- `docs/superpowers/specs/2026-04-09-ark-workflow-v2-design.md` (new)
- `docs/superpowers/plans/2026-04-09-ark-workflow-v2.md` (new)
- `TODO.md` (new — captures the split-refactor follow-up)
