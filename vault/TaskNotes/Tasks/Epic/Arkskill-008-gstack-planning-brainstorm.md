---
tags:
  - task
title: "/ark-workflow gstack planning integration + Brainstorm scenario (v1.18.0)"
task-id: "Arkskill-008"
status: done
priority: high
project: "ark-skills"
work-type: feature
task-type: epic
urgency: normal
session: "S012"
created: "2026-04-18"
last-updated: "2026-04-20"
source-sessions:
  - "[[S012-Ark-Workflow-Gstack-Planning]]"
parent:
  - "[[Arkskill-003-omc-integration]]"
---

# Arkskill-008: /ark-workflow gstack planning integration + Brainstorm scenario

## Summary

Integrated the previously-unused gstack planning skills (`/office-hours`, `/autoplan`, `/plan-ceo-review`, `/plan-design-review`, `/plan-eng-review`, `/plan-devex-review`) into `/ark-workflow`, and added a new **Brainstorm** scenario as the pre-triage entry for fuzzy ideas. Designed through two `/ccg` review passes (design-level + pre-push diff-level).

Shipped v1.18.0 on branch `gstack-improve` in 2 commits (`4aa2c2b` + `3d382c2`); PR #21 open against master.

## Core design decisions

- **Session-capability detection** — `HAS_GSTACK_PLANNING` is an agent-executed semantic probe that reads the session skill-list, matching the detection pattern already used by `/ark-health` and `/ark-onboard`. `GSTACK_STATE_PRESENT` is a filesystem advisory (`$HOME/.gstack/config.yaml`) used only to distinguish absent vs broken-install. See [[Session-Capability-Plugin-Detection-Pattern]].
- **Three-state UX** — healthy (include), absent (silent skip), broken-install (one notice per chain pointing to `/ark-health`). Silent-by-default prevents clippy noise.
- **Heavy Path A planning authority substitution** — gstack **replaces** `/ccg` plan review (not stacks on top). Greenfield Heavy → `/autoplan`, Migration/Performance Heavy → `/plan-eng-review`. Spec-review `/ccg` stays (different purpose). Prevents the "Review Hell" anti-pattern Gemini called out.
- **Path B gstack-independence** — documented as explicit product decision. Path B's `/autopilot`/`/team` engines include internal review phases; layering gstack planning would reintroduce stacked-committee ceremony.
- **Brainstorm scenario** — creation-intent triggers only (drops "explore"/"think through" — too generic). Continuous Brainstorm pivot gate at step 4 (`[Y/n]`) archives the chain file on either branch; Y triggers inline re-triage, N stops. Eliminates zombie-chain state.
- **Greenfield Medium additive** — `/plan-design-review` + `/plan-devex-review` (conditional on UI-with-design-ref / developer-facing-surface triggers). Medium uses `/ask codex`, not `/ccg`, so this is additive not substitutive.
- **Scope-retreat pivot** — Greenfield → Brainstorm mid-chain when scope uncertainty surfaces. Documented in SKILL.md § When Things Change.

## Review posture

- **First `/ccg` pass** (design-level before Phase 2 chain edits): Codex flagged 9 concerns, 6 HIGH/MEDIUM reworked (filesystem detection, zombie chain, `/ccg`+`/autoplan` redundancy, Path B parity, degradation asymmetry, trigger rigidity); 3 LOW accepted. Gemini flagged "Review Hell" and bureaucratic Brainstorm STOP — both absorbed into the rework.
- **Second `/ccg` pass** (pre-push diff-level against `4aa2c2b`): Codex flagged 2 HIGH contract bugs (archive path mismatch with `references/continuity.md`; recursive `/ark-workflow` self-invocation contradicting Step 7) + 1 MEDIUM (substitution render rule missing from SKILL.md Step 6). Gemini red-flagged interactive pivot hanging in backgrounded contexts. All 4 addressed in follow-up commit `3d382c2`.

## Files touched

- `skills/ark-workflow/SKILL.md` — +98 lines (semantic probe, Brainstorm scenario row, condition triggers, Heavy substitution rule, Path B independence note, render rule, scope-retreat pivot)
- `skills/ark-workflow/chains/brainstorm.md` — NEW (+49 lines)
- `skills/ark-workflow/chains/greenfield.md` — +36 lines (Medium additive, Heavy substitution note, scope-retreat escape hatch, Medium spec-as-plan wording)
- `skills/ark-workflow/chains/migration.md` — +1 (Heavy substitution note)
- `skills/ark-workflow/chains/performance.md` — +1 (Heavy substitution note)
- `CHANGELOG.md`, `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

## Follow-ups (non-blocking — deferred)

- Semantic probe silent-misclassification risk — prose-only, relies on agent counting skill-list entries by bare name; prefix-anchored detection (like `/ark-health`'s `superpowers:*`) would be safer.
- Brainstorm trigger rigidity — "explore a new feature idea" won't match by design; revisit if false-negatives come up.
- Substitution note verbosity in chain-file storage (agent-only rendering hint, but visually noisy inline).

## Cross-links

- Session: [[S012-Ark-Workflow-Gstack-Planning]]
- Parent epic: [[Arkskill-003-omc-integration]]
- Insight: [[Session-Capability-Plugin-Detection-Pattern]]
- PR: https://github.com/HelloWorldSungin/ark-skills/pull/21
