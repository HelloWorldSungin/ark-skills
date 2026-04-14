---
title: "Session 7: OMC ↔ /ark-workflow Dual-Mode Integration (v1.13.0)"
type: session-log
tags:
  - session-log
  - S007
  - skill
  - ark-workflow
  - omc
  - dual-mode
  - deep-interview
  - ralplan
  - autopilot
  - release
summary: "Shipped dual-mode /ark-workflow routing. Every chain variant now has Path A (Ark-native) and Path B (OMC-powered) when HAS_OMC=true. 19 variants across 7 chain files; 3 canonicalized shapes (vanilla + special-a + special-b). HAS_OMC probe + omc-integration reference doc + check_path_b_coverage.py CI. v1.12.0 → v1.13.0."
session: "S007"
status: complete
date: 2026-04-13
prev: "[[S006-Ark-Context-Warmup-Ship]]"
epic: "[[Arkskill-003-omc-integration]]"
source-tasks:
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-13
last-updated: 2026-04-13
---

# Session 7: OMC ↔ /ark-workflow Dual-Mode Integration (v1.13.0)

## Objective

Extend `/ark-workflow` with a second execution path powered by OMC
(oh-my-claudecode) while preserving the existing Ark-native default. Every
chain variant gains a `### Path B (OMC-powered)` block that front-loads
judgment, delegates planning + execution to OMC, and hands control back to
Ark for closeout. OMC remains optional.

## Context

Entry state: `/ark-context-warmup` had just shipped in v1.12.0 (S006). The
7-chain `/ark-workflow` infrastructure was stable, but every chain was a
step-by-step sequence with a human checkpoint between each skill. OMC's
autonomous-execution primitives (`/deep-interview`, `/omc-plan --consensus`,
`/autopilot`, `/ralph`, `/ultrawork`, `/team`) offered a lower-checkpoint-
density alternative — front-load judgment once, let the executor run, then
return control to Ark for review + ship + vault.

The task needed to satisfy three constraints that initially tensioned:
- Preserve Path A neutrality (never auto-remove user-in-the-loop flow).
- Discoverability (surface Path B so users who would benefit see it).
- Byte-identical coverage across 19 variants (no hand-audit).

## Work Done

### Phase 0 — Deep interview (pre-implementation)

Ran `/deep-interview` to drive ambiguity below 20%. Five rounds converged to
8%. Round 4 was a Contrarian challenge that validated two choices that had
looked marginal:

1. **OR-any signal rule.** Initially spec proposed "2 of 4 signals fires" to
   avoid over-surfacing. User held that ANY signal should recommend Path B,
   mitigated by the 3-button UX (`[Show me both]`). Over-surfacing is
   preferable to under-surfacing because the override cost is one click.
2. **Show-always for "discouraged" variants** (Migration Light, Performance
   Light, Ship Standalone). Spec initially proposed hiding Path B on these
   shapes. User held discoverability > neutrality — surface it, annotate it as
   unusual, trust the user to pick Path A.

### Phase 1 — Ralplan consensus (pre-implementation)

Ran `/ralplan` for 2 iterations:
- **Iteration 1:** Architect ITERATE (3 findings + 2 synthesis proposals);
  Critic ITERATE (13 required changes). Key critic findings: wrong script
  paths, wrong `probe()` signature in verification, Phase 2 at Agent Directive
  #2 ceiling (zero slack), missing pre-mortem, missing observability, missing
  `ARK_SKIP_OMC` rollback, `/autopilot`/`/ralph`/`/ultrawork`/`/team` handback
  boundaries were not separate contracts, missing byte-identity CI check.
- **Iteration 2:** Both APPROVE. Plan absorbed all 13 Critic required changes
  + 2 Architect synthesis proposals. Phase 2 split into 2a (3 files, 9
  vanilla variants) + 2b (2 files, 3 special variants). Four handback
  sub-contracts enumerated. `ARK_SKIP_OMC=true` wired in.

### Phase 2 — Implementation (executor = this session)

Five phases executed in order with commit-per-phase:

| Phase | Files | Commit |
|---|---|---|
| 1 Foundation | availability.py + SKILL.md + omc-integration.md + check_path_b_coverage.py | feat(ark-workflow): HAS_OMC probe + omc-integration reference foundation |
| 2a Vanilla batch | greenfield/bugfix/hygiene chains (9 blocks) | feat(ark-workflow): Phase 2a — Vanilla Path B blocks for 9 variants |
| 2b Special-case batch | hygiene (Audit-Only) + knowledge-capture (Light/Full) | feat(ark-workflow): Phase 2b — Special-A + Special-B Path B blocks |
| 3 Remaining vanilla | migration + performance + ship (7 blocks) | feat(ark-workflow): Phase 3 — Path B for migration/performance/ship |
| 4 Release artifacts | VERSION + plugin.json + marketplace.json + CHANGELOG.md | chore(release): v1.13.0 — OMC ↔ /ark-workflow dual-mode integration |
| 5 Vault artifacts | this epic + this session log + Execution-Philosophy-Dual-Mode insight + counter bump | chore(vault): S007 session log + Arkskill-003 epic + dual-mode insight |

## Decisions Made

- **Variant-inherited handback with enumerated special cases.** Principle
  renamed from "uniform handback boundary" in iteration 2 — "uniform"
  overclaimed the shape given 3 special cases (Knowledge-Capture substitutes
  `/claude-history-ingest` for `/deep-interview`; Hygiene Audit-Only ends at
  `/wiki-update` STOP). 16 of 19 variants inherit a single Vanilla template;
  3 use enumerated Special-A/Special-B templates.
- **Four handback sub-contracts.** `/autopilot` (skip internal Phase 5),
  `/ralph` (after loop-to-verified exit), `/ultrawork` (after last lane
  signal), `/team` (after `team-verify`, before `team-fix`). Documented in
  `references/omc-integration.md` § Section 4.
- **`ARK_SKIP_OMC=true` as emergency rollback.** User-facing env var that
  forces `HAS_OMC=false` regardless of detection. Wired into both the bash
  probe (`SKILL.md`) and documented in `references/omc-integration.md` §
  Section 3 as the rollback mechanism for downstream projects that adopted a
  grep-pinning recipe during v1.12.0 integration.
- **Byte-identity CI gate, not hand-audit.** `check_path_b_coverage.py`
  canonicalizes each Path B block (strips weight markers, `{weight}`
  placeholders, internal whitespace), hashes it, asserts 19 total blocks with
  ≤3 distinct canonicalized hashes. This means any future edit that drifts
  the Vanilla template breaks CI — without needing a human to diff 19
  sections.
- **Plan's `--expected-blocks 10` and `13` were arithmetic typos.** The plan
  summed "9 + 1 + 2 + 7 = 19" via 10, 13, 19 checkpoints (off by one in the
  first two). Executor corrected to 9, 12, 19. Final state (19) was unchanged.
- **Per-variant autopilot-flavor notes live OUTSIDE Path B blocks.** The
  "`/team` is suitable for Heavy migration" and "Path B is unusual for Light"
  annotations are paragraphs between the Path A last step and the Path B
  heading. Placing them inside the block would inflate the distinct-hash
  count past the ≤3 ceiling.
- **Special-B classifier uses `/wiki-ingest` as marker.** Initial classifier
  used `/deep-interview` absence, but Special-B's template says "substitutes
  for `/deep-interview`" in a parenthetical, causing mis-classification as
  vanilla. Fixed by keying on `/wiki-ingest` (unique to the reflective-
  capture step). Documented in `check_path_b_coverage.py`.
- **Three executor-level tweaks absorbed (user brief):** (1) canonicalizer
  strips `--(quick|thorough)` regex, not just `{weight}` placeholder;
  (2) Phase 2a verification explicitly asserts Hygiene Audit-Only has no Path
  B yet; (3) Phase 1 verification does an explicit `.gitignore` grep (not
  "presumably").
- **Open Question #1 fallback:** `OMC_EXECUTION_ONLY=1` env-var wrapper at
  chain step 3 until OMC exposes a first-class flag. Documented in
  `references/omc-integration.md` § Section 6 and the ADR follow-ups.

## Issues & Discoveries

- **Hook noise was misleading.** Some PostToolUse hook messages emitted
  "Edit operation failed" immediately after successful edits. Verified
  success each time via Grep/Read. Proceed based on actual file state, not
  hook message contents.
- **Planning arithmetic errors compound fast.** A single off-by-one in a
  verification command would have caused a Phase 2a CI failure that masked
  the real state. The byte-identity CI check caught it immediately — the
  coverage script said "total Path B blocks = 9, expected 10." Tightly
  scoped assertions + cheap re-runs > big verification batches.
- **Special-B template has `/deep-interview` as a substring.** The
  parenthetical "substitutes for `/deep-interview`" tripped substring
  classification. Primary lesson: machine classifiers on prose text must key
  on distinguishing markers, not absence of common markers.
- **Plan's "10 variants" vs actual 9** wasn't caught by either Architect or
  Critic in ralplan iteration 2. The byte-identity CI caught it mechanically
  within seconds of Phase 2a completion. Process lesson: prefer mechanical
  gates over human counting.

## Next Steps

Follow-ups out of scope for v1.13.0 (documented in the plan's ADR §
Follow-ups):

1. **Pin `/autopilot` execution-only mechanism.** Current fallback is
   `OMC_EXECUTION_ONLY=1` env var. Confirm whether OMC exposes a first-class
   flag (`--skip-phase-5`, `--execution-only`) or a session marker.
2. **Telemetry rotation policy** for `.ark-workflow/telemetry.log` (v1.14.x).
3. **Evaluate fifth Section 4 sub-contract** if `/ccg` enters Path B as its
   own execution engine variant.
4. **Downstream grep-pinning detection** — identify consumer CLAUDE.md files
   that hardcode `HAS_OMC=false` and notify maintainers.
5. **Smoke test Path B end-to-end** with a real OMC install on a Greenfield
   Heavy prompt. Validate State A (HAS_OMC=true) / State B (HAS_OMC=false) /
   State C (ARK_SKIP_OMC=true) produce the expected chain outputs.
