---
title: "SKILL.md Shrink-to-Core via References Extraction"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - plugin
summary: "Cut SKILL.md verbosity by relocating long bash, prompts, templates, and report skeletons to references/*.md load-on-demand. v1.21.0 audit hit a 30% aggregate reduction (49–58% per-skill on slimmed targets) with zero behavior change. Verbosity reduction is not capability deletion — preserve all ark-specific IP inline only when its scannability matters at invocation time."
source-sessions: []
source-tasks: []
created: 2026-04-24
last-updated: 2026-04-24
---

# SKILL.md Shrink-to-Core via References Extraction

## Summary

The v1.21.0 release shipped a Layer-3 audit that cut SKILL.md aggregate verbosity 30% (7,707 → 5,388 LOC) without removing capability. The slim mechanism is consistent across four skills:

| Skill | Before | After | Reduction |
|------|--------|-------|-----------|
| `/ark-health` | 743 | 378 | 49% |
| `/codebase-maintenance` | 156 | 156 | — (already lean) |
| `/ark-code-review` | 784 | 357 | 54% |
| `/ark-onboard` | 2650 | 1122 | 58% |

Everything that moved went to `references/*.md` files that the skill loads on demand by linking to them inline. Nothing was deleted; the at-invocation context footprint dropped proportionally.

The audit's deeper finding is the rule: **verbosity reduction is not capability deletion.** The original design-doc rationale framed slim as "remove overlap with upstream" (e.g., `omc-doctor`). Evidence during execution contradicted that — `omc-doctor` and `/ark-health` are disjoint domains, no upstream replicates `/ark-code-review`'s multi-agent fan-out, and so on. The actual lever is moving load-on-demand bulk out of the always-loaded SKILL.md, not deleting ark-specific IP.

## What goes inline vs. what moves to references/

| Stays inline | Moves to `references/` |
|--------------|------------------------|
| Workflow steps the agent must follow in order | Long bash implementations (>30-50 LOC) for individual checks |
| Frontmatter description (the routing signal) | Agent prompts (multi-paragraph fan-out templates) |
| Decision rules (when to fail vs warn, scope rules) | Per-mode report skeletons |
| Operational rules (trust boundaries, opt-outs) | File templates the skill writes verbatim |
| Skip / early-exit logic | Repair scenarios (5+ branches with detailed bash) |
| Concrete examples that disambiguate ambiguity | State-detection bash + flag derivation |

Threshold: if the agent can do the right thing knowing *what* a step does and *when* it runs, but the *how* is bulk implementation, that's a `references/` candidate. If the agent needs the bash to be in front of it because the bash IS the decision, keep it inline.

## The audit method

1. **Invocation audit first** (Codex-recommended ordering): capture three signals before slimming any skill —
   - **G1 — mentions** across `~/.claude/projects/` transcript history + session logs (raw context-window pressure).
   - **G2 — programmatic Skill-tool fires** (chain workhorse signal — what `/ark-workflow` actually invokes).
   - **G3 — session-log authorial mentions** (direct-invocation signal — what the human types `/skill` for).

2. **Order skills from low-direct-fire to high-direct-fire.** v1.21.0 audited `/ark-health` first (lower direct invocation, easier rollback if slim went sideways) and `/ark-onboard` last (highest direct invocation, biggest risk surface).

3. **Verify-then-slim discipline.** Each phase gates on independent `codex` review before merging. Findings on this audit:
   - Phase 1 `/ark-health`: clean.
   - Phase 3 `/ark-code-review`: 2 [P2] NITs (missing `--epic` Code Reviewer prompt variant; inaccurate agent-roster mode-applicability column). Both fixed before continuing.
   - Phase 4 `/ark-onboard`: 3 [P1]s — reference-pointer integrity (backtick-wrapped headings didn't match literal `§` lookups), Greenfield Step 1 wizard UX regression (compressed prompts), design-bullet/step-marker inconsistency. All fixed before release.

The Phase-4 P1s would have been catastrophic — wizard UX is the high-direct-fire user contract — and weren't caught by self-review. This validates the [[Codex-Review-Non-Convergence]] insight at audit scale, not just per-PR scale.

## Reference-pointer integrity

`references/` files are linked from SKILL.md by literal section markers. The Phase-4 [P1] surfaced a real failure mode: a SKILL.md that says "see `references/templates.md` § Greenfield Step 1" doesn't match a heading written as `## \`Greenfield Step 1\`` (backtick-wrapped) or `## Greenfield Step 1 (Greenfield)` (parenthetical). The lookup is a literal `§` text-match in practice, so any decoration on the heading breaks it.

**Lint rule** worth wiring into `/wiki-lint` or a future skill-lint:

- Every `§` reference in a SKILL.md must resolve to a literal `## <text>` heading in the named `references/` file.
- Heading text must be plain — no backticks, no parentheticals, no trailing emoji.
- A broken `§` reference is a P1, same severity as a broken wikilink in the vault.

## Aggregate impact

- **Before:** 7,707 LOC across all SKILL.md files.
- **After:** 5,388 LOC inline + ~1,750 LOC in `references/*.md` (loaded on demand).
- **Aggregate at-invocation reduction:** 30% (hit the design-doc stretch target).
- **Behavior change:** zero. Every external interface unchanged; only internal layout shifted.

## What stayed out of scope

- **L1 chain-manifest decoupling** (Open Question 10 in the design doc). `/ark-workflow` has accumulated ~5k LOC over six weeks because chain-resolution is inline and references upstream plugin names. Externalizing chain manifests is the right fix but deferred to v1.22+ — not part of v1.21.0.
- **Low-signal L2 skills** surfaced by the invocation audit (`/wiki-lint`, `/data-ingest`, `/wiki-handoff`, `/tag-taxonomy`, `/cross-linker`, `/wiki-status` at G2=0, low G3). Future audit pass.

## Evidence

- `CHANGELOG.md` v1.21.0 per-skill outcomes table (verbatim): 743→378 / 156→156 / 784→357 / 2650→1122.
- `CHANGELOG.md` v1.21.0 deferred section names L1 chain-manifest decoupling and the low-signal L2 candidates.
- `CHANGELOG.md` v1.21.4 deferred section: "relocating the new Check 14a/14b/14c/14d/16b bash blocks into `references/check-implementations.md` to honor the v1.21.0 Shrink-to-Core direction. Tracked as Arkskill-011." — confirms the pattern is a continuing convention, not a one-off audit.
- Commits `9409555` (v1.21.0 release) and `de6a605` (Arkskill-011 task creation).
- Codex review findings on Phase 3 (`e32c198`) and Phase 4 (`a2e54dd`) before merging.

## Implications

- **New checks / prompts / templates over ~30-50 LOC default to `references/`,** not inline. The default should be load-on-demand. v1.21.4 explicitly noted this rule was violated by Check 14a/b/c/d/16b additions and tracked the cleanup.
- **G1/G2/G3 invocation audit is the right pre-slim tool** for any skill whose verbosity has crept up. Without it, you slim by gut and risk regressing high-direct-fire surfaces (the Phase-4 wizard UX P1).
- **Verify each phase with an independent reviewer before merging** the next phase. Slim changes don't show up in tests — only adversarial prompt-eyeball review catches the prompt drift, missing variant, or subtle UX regression.
- **Treat `§` reference-pointer breakage as P1.** Plain-text heading discipline in `references/` is non-negotiable.
- **The 30% number isn't the goal — the at-invocation footprint is.** What matters is that the skill is scannable at fire time and bulk content loads only when the agent traverses to it. Cross-reference [[Session-Habits-For-Context-Longevity]] for why this matters at the session level.
