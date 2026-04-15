---
tags:
  - task
title: "/ark-workflow Path B Uniformity Refactor"
task-id: "Arkskill-006"
status: done
priority: high
project: "ark-skills"
work-type: refactor
task-type: epic
urgency: normal
session: "S010"
created: "2026-04-15"
last-updated: "2026-04-15"
source-sessions:
  - "[[S010-Path-B-Uniformity-Refactor]]"
parent:
  - "[[Arkskill-003-omc-integration]]"
---

# Arkskill-006: /ark-workflow Path B Uniformity Refactor

## Summary

Audit the v1.13.0 dual-mode `/ark-workflow` Path B routing (shipped under
[[Arkskill-003-omc-integration]]), then collapse its engine specializations
into a uniform `/autopilot` choice across all chain variants except
Migration Heavy (which keeps `/team`). Implemented audit recommendations
R1, R2, R4, R10, R11, R15, R16, R17 across 7 atomic commits on branch
`ark-workflow-improve-OMC`; shipped in v1.16.0 via PR #18 (renumbered from
Arkskill-004 during rebase onto master's Arkskill-004-ark-update-framework).

Resolves audit R5 (uniform operator mental model vs best-specialized per
scenario — picked uniformity). Renders R8 and R9 obsolete.

## Audit artifact

- [`.ark-workflow/audits/omc-routing-audit-2026-04-14.md`](../../../../.ark-workflow/audits/omc-routing-audit-2026-04-14.md)
  (22KB) — 18 recommendations plus Codex adversarial review; implementation
  addendum at the bottom records commit SHAs + verification results.

## Implementation outline

| # | Ref | Commit | Scope |
|---|-----|--------|-------|
| — | WIP prereq | `0856b8e` | `/codex → /ask codex \| /ccg` call-site rename across 5 chain files + `troubleshooting.md` (landing before R-refactor for clean separation) |
| 1 | R1 | `b3926c3` | `omc-integration.md §4.1` rewrite + §6 rewrite; delete §4.2 (/ralph) and §4.3 (/ultrawork); renumber §4.4→§4.2, §4.5→§4.3; retire fictional `OMC_EXECUTION_ONLY` env var |
| 2 | R2 | `1b5b8ae` | Engine collapse in chains (greenfield Heavy /ultrawork → /autopilot; performance Med+Heavy /ralph → /autopilot); propagate step-3 wording to all 15 Vanilla blocks; coverage script + tests (fixes pre-existing 19 vs 18 drift) |
| 3 | R15+R16+R17 | `bf0187d` | "Verbatim" → "Superset of" keyword list; Signal #3 Multi-module LLM-judgment parenthetical; Ship Standalone Path B block removal (chain + tables + coverage script updates to 17/4) |
| 4 | R4 | `3294d9e` | `check_chain_drift.py` + pytest harness (banned patterns: `OMC_EXECUTION_ONLY`, `Phase 5 (docs/ship)`, `internal Phase 4 (execution)`, `/ultrawork` or `/ralph` as chain step-3 engines) |
| 5 | R10 | `5856c2c` | `/external-context` as pre-step 1 in Migration Medium + Heavy Path B; hash-count vs shape-count distinction documented |
| 6 | R11 + addendum | `8207174` | `/visual-verdict` closeout for Greenfield Medium + Heavy (conditional on UI with design reference); SKILL.md Condition Resolution entry; audit addendum; `.gitignore` rule change to track audit reports |

## Verification results

- **V1** — static verification of autopilot/SKILL.md:41, 42, 173-189
  confirmed the auto-skip premise; full runtime probe deferred (would
  hijack the agent session; low-risk per memory classification and
  reversible via `git revert`).
- **V2** — `check_path_b_coverage.py`: 17 blocks; 5 raw-text canonicalized
  hashes; 4 classifier shapes (vanilla 14, team 1, special-a 1,
  special-b 1). PASS.
- **V3** — `check_chain_drift.py`: zero banned patterns across 8 target
  files (7 chain files + `omc-integration.md`). PASS.
- **Test suite** — 179/179 tests in `skills/ark-context-warmup/scripts/`
  pass (including 14 new drift-lint tests and 24 coverage tests).

## Shape count vs hash count — key insight

The classifier in `check_path_b_coverage.py` keys on engine + closeout
markers (`/autopilot`, `/team`, `/wiki-ingest`, `STOP`, `/ark-code-review`,
`/claude-history-ingest`) — NOT step count. The R10 `/external-context`
pre-step lengthens Migration Medium + Heavy block bodies by one line,
yielding distinct raw-text canonicalized hashes from the common vanilla
and /team forms. Classifier-visible shapes remain 4; raw-text hash count
is 5.

This distinction is documented in `omc-integration.md §4` footnote and
in the coverage script's docstring. Future pre-step additions would
raise the raw-text hash ceiling further unless canonicalization is
extended to strip step-count variance.

## Follow-up (not in 2026-04-15 scope)

- **R3** (Medium, M effort): back-port v1.14.0's `HAS_CODEX` /
  `HAS_GEMINI` probe to ark-workflow's 10 fan-out call sites.
- **R6** (Medium, S effort): cancellation / rollback UX doc for Path B.
- **R7** (Medium, S effort): explicit failure signaling for
  `<<HANDBACK>>` marker.
- **R12** (Medium, S effort): optional `/ultraqa --tests` pre-gate for
  Light/Medium closeouts.
- **R13** (Medium, M effort): telemetry completion NDJSON line.
- **R14** (Low, S effort): "codex for code, ccg for plans" rule ADR.
- **R18** (Low, S effort): `/ccg` vs `/plan --critic codex` ADR.
- **VERSION bump + CHANGELOG + push to master** — batch with R3 for the
  next release cycle.
- **v1.14.0 session log backfill** — commit `0376ebc` shipped without
  its own session log; should be backfilled for continuity.
- **CI wiring** — add `.github/workflows/ci.yml` invoking pytest under
  `skills/ark-context-warmup/scripts/` so both drift lint and coverage
  check run automatically.

## Decisions that became obsolete

- **R8** (route Light variants to `/omc-plan --direct` instead of
  `/deep-interview`) — redundant under uniformity; the front-end stays
  `/deep-interview` across all variants.
- **R9** (document `/ai-slop-cleaner` as alternate engine for Hygiene
  Light on explicit-deslop prompts) — Signal #1 keyword detector handles
  user-intent specialization without chain-level branching.
