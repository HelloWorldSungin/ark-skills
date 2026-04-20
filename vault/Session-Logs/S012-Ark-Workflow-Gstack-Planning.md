---
title: "Session 12: /ark-workflow gstack planning integration + Brainstorm scenario (v1.18.0 ship)"
type: session-log
tags:
  - session-log
  - S012
  - skill
  - ark-workflow
  - gstack-planning
  - brainstorm-scenario
  - session-capability-detection
  - review-authority-substitution
  - release
summary: "Shipped v1.18.0: wired gstack planning (/autoplan, /plan-*-review, /office-hours) into /ark-workflow and added Brainstorm scenario with Continuous Brainstorm pivot gate. Two /ccg review passes — design-level (6 reworks) and pre-push diff-level (4 fixes). 2 commits on branch gstack-improve, PR #21 open."
session: "S012"
status: complete
date: 2026-04-18
prev: "[[S011-Ark-Workflow-Context-Budget-Probe]]"
epic: "[[Arkskill-008-gstack-planning-brainstorm]]"
source-tasks:
  - "[[Arkskill-008-gstack-planning-brainstorm]]"
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-18
last-updated: 2026-04-20
---

# Session 12: /ark-workflow gstack planning integration + Brainstorm scenario (v1.18.0 ship)

## Objective

Integrate the previously-unused gstack planning skills (`/office-hours`, `/autoplan`, `/plan-ceo-review`, `/plan-design-review`, `/plan-eng-review`, `/plan-devex-review`) into `/ark-workflow` and add a `Brainstorm` scenario as the pre-triage entry for fuzzy ideas. Route all changes through two `/ccg` review passes to catch design and diff-level concerns before push.

## Context

Entry state:
- `/ark-workflow` v1.17.0 had no wired-up path for gstack planning skills. Chains used superpowers `/brainstorming`, OMC `/ccg`, and `/ask codex` — but the gstack planning family was invisible despite being routinely installed on user machines.
- User observation that kicked off the session: *"I feel like we are not utilizing the gstack planning workflow at all."*
- Exploratory task, not a bug report. Began with a design-space survey (pre-triage exploration, pre-implementation review, design exploration, post-planning handoff).

## Work Done

### 1. Design-space exploration

Mapped gstack planning skills into three buckets:
- **Pre-triage**: `/office-hours` (YC forcing questions, scope-challenging)
- **Pre-implementation**: `/plan-ceo-review`, `/plan-design-review`, `/plan-eng-review`, `/plan-devex-review`, `/autoplan` (bundle)
- **Non-linear / one-off**: `/design-shotgun`, `/design-consultation`

Evaluated four design dimensions (coupling, granularity, trigger logic, `/office-hours` placement) and three candidate shapes (mandatory phase, signal-gated Path C, scenario-gated conditionals). Chose **Shape 3 (scenario-gated conditionals) + `/office-hours` as new scenario** — fits Ark's existing conditional-pattern idiom, no new UI mental model, preserves per-scenario opt-out.

### 2. First `/ccg` review pass (design-level)

Before committing to Phase 2 chain edits, dispatched Codex (architecture/correctness) and Gemini (UX/alternatives) in parallel. Both returned `REWORK`.

**Codex HIGH concerns:**
1. `HAS_GSTACK` via filesystem probe is the wrong truth source — `/ark-health`/`/ark-onboard` define plugin availability as "skill loadable in current session," not filesystem inspection. Creates false positives (stale config after uninstall) AND false negatives (plugin routing works without CLI).
2. Brainstorm hard `STOP` leaves a zombie chain in `.ark-workflow/current-chain.md` (the persistent SoT). Next session would offer to "continue" a finished Brainstorm.
3. `/ccg` + `/autoplan` in Greenfield Heavy is duplicated ceremony — two overlapping committees with unclear conflict resolution.
4. Path B parity missing — Heavy autonomous path gets none of the new planning review surface.

**Gemini concerns:**
- "Review Hell": stacking 3 review rounds (`/ccg`→`/ccg`→`/autoplan`) kills momentum.
- "Ghost Tooling Noise": clippy degradation messages for users without gstack.
- "Outcome Disconnect": Brainstorm stopping then requiring re-invocation is bureaucratic.
- Alternative shape: **Replacement/Upgrading** — `/autoplan` REPLACES `/ccg` in Heavy (not stacks); Continuous Brainstorm interactive pivot (not hard STOP).

**Synthesis → 6 rework items absorbed into Phase 1 before Phase 2 chain edits.**

### 3. Phase 1 rework + Phase 2 chain edits

Phase 1 SKILL.md changes:
- Semantic probe for `HAS_GSTACK_PLANNING` reading the session skill-list (matches `/ark-health` pattern); `GSTACK_STATE_PRESENT` as filesystem advisory only, used to distinguish absent vs broken-install.
- Three-state condition resolver: healthy (include), absent (silent skip), broken-install (one notice per chain pointing to `/ark-health`).
- Brainstorm scenario row added; triggers deliberately exclude "explore"/"think through" (too generic).
- `(if developer-facing surface)` condition trigger added for `/plan-devex-review`.
- `(if UI-with-design-reference)` trigger extended to also gate `/plan-design-review`.
- Heavy planning authority substitution rule (new subsection).
- Path B gstack-independence (explicit product decision, new subsection).

Phase 1 `chains/brainstorm.md` (new file):
- Single variant with `/office-hours` + optional `/plan-ceo-review` + Continuous Brainstorm pivot gate at step 4.
- Path B with `/deep-interview` + `/ralplan` (OMC skills only, no gstack).
- Degradation section: Brainstorm is the one exception to silent-default — falls back to superpowers `/brainstorming` with an explicit notice because the user invoked the gstack-powered scenario.

Phase 2 chain edits:
- Greenfield Medium: conditional `/plan-design-review` + `/plan-devex-review` added after `/brainstorming` (additive — Medium uses `/ask codex`, no `/ccg` to replace). Handoff marker renumbered `after-step-3` → `after-step-5`.
- Greenfield Heavy: step 4 `/ccg` plan review annotated with substitution note → `/autoplan` when `HAS_GSTACK_PLANNING=true`. Step 2 `/ccg` spec review explicitly exempted.
- Migration Heavy: step 3 `/ccg` → `/plan-eng-review` substitution note.
- Performance Heavy: step 4 `/ccg` → `/plan-eng-review` substitution note.

Follow-ups resolved before first commit:
- Scope-retreat pivot (Greenfield → Brainstorm) documented in SKILL.md § When Things Change and with an escape-hatch note at the top of `chains/greenfield.md`.
- Medium spec-as-plan wording clarification — the `/plan-*-review` skills target the spec at Medium scale (no `/writing-plans` artifact exists at Medium).

Commit `4aa2c2b`: 9 files, +198/-25. Version bumped `1.17.0` → `1.18.0` across `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`; CHANGELOG entry prepended with full design narrative.

### 4. Second `/ccg` review pass (pre-push diff-level)

Dispatched Codex (contract/architecture vs. the actual diff) and Gemini (user-facing clarity) against commit `4aa2c2b`. Split verdict:

**Codex: `needs-rework`** (2 HIGH + 1 MEDIUM + 1 LOW)
1. **HIGH — Brainstorm contract mismatch ×2**:
   - Core `/ark-workflow` Step 7 says "does not invoke downstream skills itself," but Brainstorm's Y-branch said "invoke `/ark-workflow` internally." Direct contradiction.
   - Archive path: Brainstorm said `.ark-workflow/archive/{chain_id}.md`; `references/continuity.md` already defines `.ark-workflow/archive/YYYY-MM-DD-{scenario}.md`. Two different conventions for the same operation.
2. **MEDIUM — Substitution render rule missing** in SKILL.md Step 6. Chain files still literally contain `/ccg` with an italic note; agent rendering could still show `/ccg` to the user.
3. **LOW — Brainstorm Path B "exception to gstack-independence" note is misleading residue.** Brainstorm Path B uses OMC skills only; no exception exists.

**Gemini: `SHIP`** but flagged:
- Interactive `[Y/n]` pivot gate hangs in backgrounded/autonomous contexts.
- Substitution notes verbose in chain-file storage.
- Brainstorm trigger rigidity ("explore a new feature idea" won't match).

**Synthesis → 5 fixes applied in commit `3d382c2`:**
1. Archive path aligned with `references/continuity.md` (`YYYY-MM-DD-brainstorm.md`).
2. Y-branch reframed as **inline re-triage** (agent applies triage algorithm to spec) — not recursive skill invocation. Reconciles with Step 7 contract.
3. Substitution render rule added to SKILL.md Step 6: when gstack healthy, rewrite step text to substitute skill; drop note from user-facing render.
4. Misleading "Path B exception" note removed from `chains/brainstorm.md`.
5. Non-interactive mode fallback: default to `Y` in auto/CI/background contexts.

### 5. Push + PR

Pushed `gstack-improve` to origin, opened PR #21 with full summary, 8-item test plan, and known-follow-ups section (semantic probe misclassification risk, trigger rigidity, substitution verbosity — all deferred).

## Decisions Made

1. **Session-capability beats filesystem for plugin detection.** Established `HAS_GSTACK_PLANNING` via semantic skill-list probe; `GSTACK_STATE_PRESENT` filesystem check demoted to advisory. Matches the pattern already proven in `/ark-health` and `/ark-onboard`. Extracted as a compiled insight: [[Session-Capability-Plugin-Detection-Pattern]].

2. **Replace, don't stack review authorities.** When gstack planning is available, it replaces `/ccg` for the plan-review slot in Heavy chains — not adds on top. Running multi-model consensus and multi-persona alignment as sibling committees is review-ceremony stacking with unclear conflict resolution. Pick one authority per phase.

3. **Path B is gstack-independent by design.** `/autopilot`/`/team` have their own internal review phases; layering gstack would reintroduce stacked committees. Users who want gstack multi-persona review choose Path A.

4. **Continuous Brainstorm beats hard STOP.** Interactive `[Y/n]` pivot at spec-commit with archive-either-branch prevents zombie chains AND preserves momentum. Non-interactive mode defaults to Y.

5. **Brainstorm is pre-triage, not a Greenfield substep.** Scenario-level separation keeps the trigger surface clean — creation-intent phrases route to Brainstorm; "explore" alone does not. Mid-chain scope uncertainty in Greenfield has its own escape hatch (scope-retreat pivot).

6. **Three-state degradation UX.** Silent when gstack absent (no clippy noise), explicit only when install appears broken (agent surfaces `/ark-health` as the diagnostic). Brainstorm is the single exception — it emits an explicit fallback notice because the user explicitly invoked the gstack-powered scenario.

7. **Two `/ccg` passes, not one.** Design-level `/ccg` catches architectural concerns; diff-level `/ccg` catches contract bugs that only surface against the actual edits. Design-level alone missed 2 HIGH contract issues that only became visible in the diff (Brainstorm self-invocation contradicting Step 7, archive-path mismatch with `references/continuity.md`).

## Open Questions

- **Semantic probe silent-misclassification.** If the agent miscounts skill-list entries by bare name (e.g., misses a namespaced entry), operator state is silently wrong. Safer would be prefix-anchored detection (`superpowers:*`-style). Deferred.
- **Brainstorm trigger false-negatives.** "I want to explore building X" won't match Brainstorm today — lands in Greenfield. If users hit this in practice, widen the trigger list carefully.
- **Substitution note verbosity** in chain-file storage — agent-only rendering hint, but visually noisy for a human reader opening `chains/greenfield.md` directly. Consider structured frontmatter in a future pass.

## Next Steps

1. **PR #21 review + merge** (branch `gstack-improve` → master).
2. **Post-merge `omc update`** on a downstream project to exercise v1.18.0 live — can't be tested from the worktree because the plugin cache serves the previous version.
3. **Live-invocation smoke tests** from the PR's test plan:
   - `/ark-workflow "brainstorm a new plugin idea"` — scenario detection, pivot gate
   - `/ark-workflow "build auth middleware with JWT"` — Heavy substitution renders `/autoplan`
   - Broken-install state — one-notice-per-chain fires
4. **Follow-up release (v1.19 or later)** for the 3 deferred concerns above.

## Cross-links

- PR: https://github.com/HelloWorldSungin/ark-skills/pull/21
- Commits: `4aa2c2b` (v1.18.0 core), `3d382c2` (pre-push fixes)
- Parent epic: [[Arkskill-008-gstack-planning-brainstorm]]
- Referenced upstream: [[Arkskill-003-omc-integration]] (ark-workflow dual-mode framework)
- Extracted insight: [[Session-Capability-Plugin-Detection-Pattern]]
- Raw advisor outputs preserved at `.omc/artifacts/ask/` (design pass + pre-push pass)
