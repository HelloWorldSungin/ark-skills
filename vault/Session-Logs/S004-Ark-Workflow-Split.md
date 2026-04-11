---
title: "Session: /ark-workflow Progressive-Disclosure Split (1.7.0)"
type: session-log
tags:
  - session-log
  - skill
  - plugin
  - workflow
  - refactor
  - progressive-disclosure
summary: "Split the 858-line ark-workflow SKILL.md into a 270-line router + 7 chain files + 4 reference files. All 22 v2 gaps + 19 chain variants preserved; 13/13 smoke tests pass."
prev: "[[S003-Ark-Workflow-v2-Rewrite]]"
epic: ""
session: "S004"
source-tasks: []
created: 2026-04-10
last-updated: 2026-04-10
---

# Session: /ark-workflow Progressive-Disclosure Split (1.7.0)

## Goal

Reduce per-invocation context load on the common path of `/ark-workflow` by ≥ 50% by splitting the monolithic v2 `SKILL.md` (858 lines after the v2 rewrite shipped in S003/1.6.0) into a progressive-disclosure layout: a small router in `SKILL.md` + per-scenario chain files in `chains/` + pay-per-use protocols in `references/`.

## Outcome

**Line counts:**

| File | Lines |
|---|---|
| `SKILL.md` (main router) | 858 → **270** (−68.5%) |
| `chains/greenfield.md` | 64 |
| `chains/bugfix.md` | 42 |
| `chains/ship.md` | 10 |
| `chains/knowledge-capture.md` | 23 |
| `chains/hygiene.md` | 50 |
| `chains/migration.md` | 55 |
| `chains/performance.md` | 56 |
| `chains/` total | 300 |
| `references/batch-triage.md` | 87 |
| `references/continuity.md` | 75 |
| `references/routing-template.md` | 49 |
| `references/troubleshooting.md` | 52 |
| `references/` total | 263 |
| **Total `skills/ark-workflow/` footprint** | 858 → **833** (−25, net shrink) |

**Common-path context load** (router + one chain file):

| Scenario | Main + chain | vs 858 baseline |
|---|---|---|
| Ship (best) | 280 | −67.4% |
| Knowledge Capture | 293 | −65.8% |
| Bugfix | 312 | −63.6% |
| Hygiene | 320 | −62.7% |
| Migration | 325 | −62.1% |
| Performance | 326 | −62.0% |
| Greenfield (worst) | 334 | −61.1% |
| **Average** | **313** | **−63.5%** |

Hard cap `SKILL.md ≤ 400 lines`: **PASS (270)**. Common-path avg cap `≤ 386`: **PASS (313)**.

**Behavioral parity:**
- 22/22 v2 gaps preserved — Appendix D checklist: **21 strict PASS, 1 acknowledged drift (C6)**
- 19/19 chain variants preserved — Appendix E per-variant H2 assertions: **20/20 PASS** (includes ship.md no-H2 assertion)
- **10 `/test-driven-development`** references preserved in `chains/` (2 baseline references at SKILL.md L282 and L751 were intentionally dropped by Phase 3 — the slimmed Step 6.5 and the dropped Condition Resolution example block; see plan Spec Clarification § 4)
- **0 `/TDD`** references remain
- 9 baseline `handoff_marker` semantic occurrences all preserved 1:1 (inline chain markers, yaml examples, prose), plus 3 new cross-reference pointers added by progressive-disclosure restructuring — documented below as Acknowledged C6 drift

**Parity diffs (all from clean state, Phase 5):**
- `chains/*` reconstruction vs baseline L410-712: **PASS** (after whitespace normalization, 7 scenarios, 19 variants round-trip byte-identically)
- `references/batch-triage.md` vs baseline L163-249 (with H1↔H2 demote reversed): **PASS**
- `references/troubleshooting.md` vs concat L761-774 + L776-789 + L791-812 (with added H1 stripped): **PASS**
- `references/routing-template.md` inner 5-backtick fenced block vs baseline L818-856: **PASS** (the actual copy-paste content humans put in their CLAUDE.md files is byte-verified)
- `references/continuity.md`: content-presence grep PASS (11/11 checks) — the only grep-only reference by design, since it has intentional new H2 scaffolding (Batch Triage Chain File Format, Cross-Session Continuity, Handoff Markers, Stale Chain Detection, Context Recovery After Compaction, Archive on Completion) per the plan's spec example body

**Smoke tests (13/13 PASS):**

1. **Session A batch** (5 Bugfix items) — Group lines match `SKILL.md` L242-244 verbatim: Group A (parallel) #2 #5; Group B (sequential) #3; Group C (pending dep confirmation) #1→#4. Session recommendation paraphrased from L248.
2. **Session B batch** (file perms + SSE + dashboard slow) — multi-scenario: loads both `chains/bugfix.md` (Heavy + Medium) and `chains/performance.md` (Light).
3. **Session C batch** (TS build break + ESLint cleanup) — scenario split preserved: Bugfix Medium + Hygiene Light, NOT consolidated into one chain.
4. **Security audit** ("audit our auth subsystem") — Hygiene: Audit-Only, chain ends at **STOP**. No `/ship`, no `/canary`, no further steps.
5. **Security hardening** ("harden our auth subsystem") — Hygiene Heavy with `/cso` prepended as step 1 and original step 4 `/cso` deduped. Result: 11 contiguous steps, `/cso` exactly once.
6. **Decision-density escalation** ("redesign the caching layer") — Low risk + Architecture density → **Heavy** (example preserved verbatim in Triage table L128).
7. **Cross-session resume** — `handoff_marker` happy path: agent announces session transition and rehydrates TodoWrite from unchecked items per `references/continuity.md` § Handoff Markers.
8. **Standalone Ship** — `chains/ship.md`, 6 steps, no weight class, no design phase, no H2.
9. **Knowledge Capture Full** — picks Full (not Light), all 8 steps present ending in session log.
10. **Migration Medium** — Medium picked, `/test-driven-development` at step 3 writes tests for new API surface before migrating.
11. **Performance Heavy** — Heavy picked, `handoff_marker: after-step-5`, `/canary` **mandatory** at step 13 (not conditional).
12. **Mixed batch** (bug + README update) — loads both `chains/bugfix.md` and `chains/knowledge-capture.md`; sequencing puts KC after Bugfix per dependency.
13. **Stale chain detection** — `>7 days` old triggers "Is this still active, or should I archive it?" prompt; never auto-deletes.

## Decisions & Deviations

- **Dropped Condition Resolution "Example resolved output" block** (14 lines, illustrative only). Spec-authorized.
- **`references/continuity.md` uses content-presence grep** (11 checks) instead of line-by-line parity diff. This is the only reference file with intentional restructure (new H2 scaffolding + new `## Archive on Completion` rule per the plan's spec example body). Plan's Spec Clarification § 3 explicitly called out this deviation.
- **`references/routing-template.md` parity is split:** line-by-line diff for the inner 5-backtick fenced block (the actual copy-paste content), content-presence grep for the outer wrapper (added H1, preamble, `---` separators, closing note). This catches any byte drift in the content humans actually put in their CLAUDE.md files.
- **TDD count is 10, not 12** (plan Spec Clarification § 4). Two intentional drops: slimmed Step 6.5 + dropped Condition Resolution example block. Both drops were explicitly authorized elsewhere in the spec; the spec's Gap 2 arithmetic just didn't subtract them.
- **File Map appendix uses `chains/greenfield.md`** (prefixed filenames) instead of bare `greenfield.md`. This minor deviation from the plan's prescribed body was required to satisfy the plan's own Step 15 grep check `grep -q "chains/${f}.md"` — the plan had an internal inconsistency between its example body and its verification check.
- **Workflow Step 4 uses "Dedup rule"** (capitalized) instead of "dedup rule". Required to satisfy the plan's grep check `grep -q "Dedup rule"` and to match `## Dedup rule` in `chains/hygiene.md`.

## Acknowledged C6 drift (non-blocker, flagged for /codex review)

**Finding:** Appendix D gap check C6 expects total `handoff_marker` occurrences to match baseline. Baseline = 9; new layout = 12 (+3 drift).

**Root cause:** All 9 baseline semantic occurrences map 1:1 to the new layout. The 3 extra occurrences all come from plan-prescribed content added by progressive-disclosure restructuring:

| Location | Prose | Plan source |
|---|---|---|
| `SKILL.md` L215 | "`handoff_marker` semantics... see `references/continuity.md`" | Phase 3 Step 7 slimmed Step 6.5 body |
| `SKILL.md` L254 | "chain files specify inline `handoff_marker` values" | Phase 3 Step 11 `## When Things Change` body |
| `references/continuity.md` L47 | `**Setting handoff_marker:**` bold label | Phase 2 Step 5 continuity.md body |

**Assessment:** Undocumented plan-spec inconsistency. The plan prescribes content that causes the drift, then expects no drift. Analogous to Spec Clarification § 4 for `/test-driven-development` (12→10), which the plan did document. The 3 new occurrences are cross-reference pointers that help the router navigate the progressive-disclosure layout — they enhance navigability, not behavior. **No behavioral regression.**

**Resolution:** Accept the drift as non-blocker. Flagged for `/codex` review at end of Phase 5. Future spec revision should update C6 to expect 12 (with the same explanation).

## Follow-ups (filed, not in scope)

- Heavy Hygiene lacks a front-loaded design phase (latent v2 gap from plan spec § Follow-ups #1). Out of scope for this pure refactor.
- Spec § 2 Gap 2 should be updated from 12 to 10 to reflect the two intentional drops (documented in plan Spec Clarification § 4).
- Spec § 2 Gap C6 should be updated from 9 to 12 to account for the 3 cross-reference pointers added by progressive-disclosure restructuring (this session's finding).

## Diff

```
6ebb297 docs: retire ark-workflow split TODO item
2d2e090 chore: bump 1.6.0 → 1.7.0 + CHANGELOG
c85f263 refactor(ark-workflow): slim main SKILL.md to router
0996c0a refactor(ark-workflow): extract references/
e7ed96a refactor(ark-workflow): extract chains/ (7/7)
0726801 refactor(ark-workflow): extract chains/ (5/7)
```

6 phase commits on `refactor/ark-workflow-split` (this session log = commit 7).
