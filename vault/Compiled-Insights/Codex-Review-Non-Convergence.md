---
title: "Codex Review Does Not Converge Across Passes"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - code-review
  - codex
  - workflow
summary: "codex review --base master samples different code paths on each invocation. Successive passes drop earlier findings and surface new ones. Never rerun hoping for a clean gate — fix current-pass P1s, accept non-blocking P2/P3s with justification, stop."
source-sessions:
  - "[[S006-Ark-Context-Warmup-Ship]]"
source-tasks:
  - "[[Arkskill-002-ark-context-warmup]]"
created: 2026-04-13
last-updated: 2026-04-13
---

# Codex Review Does Not Converge Across Passes

## The Pattern

`codex review --base master -c 'model_reasoning_effort="high"'` is a stochastic reviewer. It samples different code paths on each invocation. Running it repeatedly does not drive findings toward zero — each pass drops the prior set and surfaces new ones from unexplored paths.

## Evidence (S006, `/ark-context-warmup` v1.12.0 ship)

Five successive passes over the same diff (plus the incremental fixes), scoped to the base branch:

| Pass | Findings |
|---|---|
| 1 (initial gate) | 3 P1 + 3 P2 (YAML task_summary, notebook_id KeyError, template env interp, empty-fields, wiki schema, py3.9 syntax) |
| 2 (after P1s fixed) | 1 new P1 (precondition script paths) + 2 new P2s (rejection triggers, config fallback) — the original 6 are silent |
| 3 (after pass 2 P1 fixed) | 1 new P1 (shell escaping) + 2 new P2s (cache YAML, backlog status) — pass 2's P2s dropped |
| 4 (after pass 3 P1 fixed) | 1 new P1 (wiki two-layer interp) + 3 new P2/P3s (tasknotes availability, component D3, Step 6.5, pivot) — pass 3's P2s surface again |
| 5 (after pass 4 P1 fixed) | 1 real P1 (index.md table parser) + 2 verified-false P2s (`sort -V` macOS, py3.9 annotations) + 1 cosmetic P2 (brief formatting) |

Total surfaced: 6 + 3 + 3 + 4 + 4 = 20 unique findings over 5 passes. Had only the first pass been run, the latest table-form index parsing P1 would have shipped broken. Had passes been run indefinitely, the session never would have closed.

## Operational Rule

1. Run codex once at the start of a review cycle. Fix every P1 with a regression test (TDD).
2. Run codex once more to confirm the P1s are gone and to surface any next-layer findings. Fix those P1s too if they're contained.
3. If pass 3 surfaces a new P1 that requires broad contract changes (e.g., shell-escape convention across 3 SKILL.md files + test updates), fix it anyway.
4. **Stop after pass 3 unless a P1 points at a genuine ship blocker you can verify empirically.** Verify each new finding independently before committing to fixes — codex has produced verified-false P1s (e.g., `sort -V` on macOS Apple sort 2.3 works; `dict | None` under `from __future__ import annotations` is legal on 3.9 per PEP 563).
5. Non-blocking P2s that resurface can be dismissed in the PR body with one-line justification per the ship criterion.

## Anti-Pattern

Chasing a clean GATE: PASS by re-running codex indefinitely. The tool is adversarial — if it finds nothing this pass, that's a probabilistic artifact, not a signal that the code is perfect. Ship criterion should be "no current-pass P1s + verified" not "zero findings across any sampling."

## See Also

- [[Development-Workflow-Patterns]] — broader review rhythms (brainstorm → spec → codex → plan → implement)
- [[Dogfooding-Driven-Skill-Development]] — the `/ship` flow tested here surfaced a real pre-landing review finding (backlog enum completeness) that 5 codex passes missed
- The user's memory at `~/.claude/projects/.../memory/feedback_workflow.md` already notes "Use /codex to review specs before implementation" — this insight extends that: codex also works for post-implementation audit, but treat successive passes as sampling, not convergence
