---
tags:
  - task
title: "gstack v1.5.1.0 integration into /ark-workflow (Waves 1+2)"
task-id: "Arkskill-009"
status: in-progress
priority: high
project: "ark-skills"
work-type: feature
task-type: epic
urgency: normal
session: "S013"
created: "2026-04-22"
last-updated: "2026-04-22"
source-sessions:
  - "[[S013-Gstack-v1-5-1-0-Integration-Wave1]]"
parent:
  - "[[Arkskill-008-gstack-planning-brainstorm]]"
---

# Arkskill-009: gstack v1.5.1.0 integration into /ark-workflow (Waves 1 + 2)

## Summary

gstack upgraded from v0.18.3.0 to v1.5.1.0 — major jump with new features directly relevant to `/ark-workflow` continuity and observability. This epic integrates a selected subset without duplicating state, breaking the atomic chain-file lock, or violating the "Path B is gstack-independent" doctrine from S012.

Two-wave release (Approach B, chosen over a single-bundle Approach A):

- **Wave 1 (v1.20.0)** — cleanup + continuous-checkpoint Step 6.5 wiring + `/context-save` compaction-recovery menu option (d). **Shipped.**
- **Wave 2 (v1.21.0)** — `/benchmark-models` calibration run + data-driven chain-file substitution edits. **Deferred, separately scoped.**

## Core design decisions (from spec `docs/superpowers/specs/2026-04-22-gstack-v1.5.1.0-integration.md`)

### Premises (all user-accepted during /office-hours)

- **P1 lock boundary** — continuous-checkpoint WIP commits land AFTER the atomic check-off helper returns, structurally outside the chain-file lock. No coordination code required.
- **P2 opt-in** — default `checkpoint_mode` is `explicit`; the continuous-checkpoint block silently no-ops for the majority path. Only users who have explicitly set `checkpoint_mode: continuous` in gstack config see WIP commits.
- **P3 additive option (d)** — `/context-save --no-stage` joins the compaction-recovery menu as a lighter exit. Does NOT replace `/wiki-handoff`; different contract (markdown-only to `~/.gstack/`, skips vault schema validation by design). Explicitly opts OUT of the Wiki-handoff invariant.
- **P4 one-time calibration** — `/benchmark-models` in Wave 2 produces a vault artifact; Wave 2 substitution rule edits stay heuristic (no continuous adaptive substitution). That is a v2 problem.
- **P5 Path B untouched** — none of these four changes touch Path B chain definitions. The "Path B is gstack-independent" product decision from S012 stays intact.
- **P6 two-wave release** — cleanup lands alongside the calibration data that justifies it; one ships without the other would be either half-change or dead artifact.

### Wave 1 atomic commits (shipped in S013)

| Commit | SHA | Scope |
|--------|-----|-------|
| 1 | `ec7d4c3` | Rename 8 stale `/checkpoint` references to `/context-save` |
| 2 | `a73e775` | Wire continuous-checkpoint into Step 6.5 check-off with `GSTACK_CONFIG` resolver |
| 3 | `51b1bfc` | Add `/context-save --no-stage` as compaction-recovery option (d) |
| 4 | `c4d8561` | Bump VERSION to 1.20.0, sync plugin manifests, add CHANGELOG entry |

### Wave 2 scope (deferred)

- Calibration against 6 `/ccg` substitution points (Greenfield / Migration / Performance Heavy — plan + spec reviews)
- Bound: 1 hand-authored synthetic prompt per substitution point (6 prompts total, ~150 LOC each). Matches the shape of real prompts without leaking project content. No template engine, no "calibration-as-a-service" scope creep.
- Land report at `vault/Compiled-Insights/Model-Calibration-2026-04.md`
- Revise 1-2 substitution targets where Codex or Gemini wins on cost/quality for specific prompt shapes, or document a "calibration validated all current substitutions" null result.

## Wave 1 review posture

- **Design `/ccg` pass** — spec approved and committed at `7e2c043` before implementation.
- **Pre-push `/ccg` pass** — deferred to be run inline with /ship for this migration-medium chain. Code review (`/ark-code-review --quick`) and security review (`/cso`) both APPROVE with 0 blockers. Security review flagged one LOW defense-in-depth suggestion (move `{N}` out of the `printf` format string into an argument) — informational, not ship-blocking.

## Files touched (Wave 1)

- `skills/ark-workflow/SKILL.md` — +54 (GSTACK_CONFIG resolver; § Continuous Checkpoint Integration subsection; continuous-checkpoint bash snippet in per-step block; `(d)` branch in answer-handling; answer-set shape updates; `/checkpoint`→`/context-save` rename)
- `skills/ark-workflow/scripts/context_probe.py` — +12 (option (d) in both mid-chain and entry menu renderers)
- `skills/ark-workflow/scripts/integration/test_continuous_checkpoint.bats` — NEW, +177 (9 tests covering every row of the failure-mode table)
- `skills/ark-workflow/scripts/test_step_boundary_render.py` — +3 tests for option (d)
- `skills/ark-workflow/scripts/test_context_probe.py`, `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` — regression updates for new answer-set shape
- `skills/ark-workflow/chains/bugfix.md` / `chains/greenfield.md` / `chains/hygiene.md` / `references/troubleshooting.md` — `/checkpoint`→`/context-save` rename (5 lines)
- `VERSION`, `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — 1.19.1 → 1.20.0

## Follow-ups (deferred)

- **Defense-in-depth (LOW)** — move `{N}` out of the `printf` format string in the continuous-checkpoint snippet. Current substitution is a bare integer and safe; change is pure defense-in-depth against a future edit that might accidentally land a `%`-bearing value there.
- **Prose doc polish (LOW)** — SKILL.md:368 references "the same proceed/reset/(c) handling" for the entry-menu context; option (d) handling is documented elsewhere but a stale phrase lingers here.
- **Wave 2** — the whole of v1.21.0 is follow-up on this epic.

## Cross-links

- Session: [[S013-Gstack-v1-5-1-0-Integration-Wave1]]
- Parent epic: [[Arkskill-008-gstack-planning-brainstorm]]
- Prior session: [[S012-Ark-Workflow-Gstack-Planning]]
- Design spec: `docs/superpowers/specs/2026-04-22-gstack-v1.5.1.0-integration.md`
