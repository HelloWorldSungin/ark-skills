---
tags:
  - task
title: "OMC ↔ /ark-workflow Dual-Mode Integration"
task-id: "Arkskill-003"
status: done
priority: high
project: "ark-skills"
work-type: development
task-type: epic
urgency: normal
session: "S007"
created: "2026-04-13"
last-updated: "2026-04-13"
source-sessions:
  - "[[S007-OMC-Integration-Design]]"
---

# Arkskill-003: OMC ↔ /ark-workflow Dual-Mode Integration

## Summary

Integrate oh-my-claudecode (OMC) into `/ark-workflow` via a dual-mode routing
pattern. Every chain now emits both a `## Path A` (Ark-native, step-by-step,
user-in-the-loop) and a `### Path B (OMC-powered)` block when `HAS_OMC=true`.
Path B front-loads judgment (`/deep-interview`), runs consensus planning
(`/omc-plan --consensus`), executes autonomously (`/autopilot` / `/ralph` /
`/ultrawork` / `/team`), then hands control back to Ark at `<<HANDBACK>>` for
closeout (code review, ship, vault, session log).

OMC remains optional. When `HAS_OMC=false` OR `ARK_SKIP_OMC=true`, chains emit
Path A only plus a one-line install hint. Zero behavioral change for OMC-less
installs.

## Spec & Plan

- Deep-interview spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md`
  (8% ambiguity, Round 4 Contrarian challenge clarified OR-any discoverability
  bias, show-always for "discouraged" variants).
- Implementation plan: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md`
  (ralplan consensus iteration 2, Architect APPROVE + Critic APPROVE).

## Implementation — DONE (v1.13.0)

### Phase 1 — Foundation (4 files)

- [x] `skills/ark-context-warmup/scripts/availability.py` — `has_omc` probe
  parameter added (`omc_cli_path`, `omc_cache_dir` keyword-only); mirrors the
  notebooklm idiom and returns `has_omc: bool` + `has_omc_skip_reason`.
- [x] `skills/ark-workflow/SKILL.md` — `HAS_OMC` bash probe in Project
  Discovery; Step 6 (continued) subsection with 3-button UX + 4-signal OR-any
  rule + checkpoint-density estimate + telemetry contract.
- [x] `skills/ark-workflow/references/omc-integration.md` (NEW) — Section 0
  canonical constants, two-philosophies axis, per-chain skill map, 4-signal
  detector spec + verbatim keyword list, variant-inherited handback with four
  sub-contracts (`/autopilot`, `/ralph`, `/ultrawork`, `/team`), per-variant
  expected-closeout table, 3 Path B block templates.
- [x] `skills/ark-context-warmup/scripts/check_path_b_coverage.py` (NEW) — CI
  check: 19 blocks, ≤3 distinct canonicalized shapes, every block must contain
  `<<HANDBACK>>` + `/deep-interview` OR `/claude-history-ingest`. Canonicalizer
  strips `--(quick|thorough)` weight markers so Light/Medium/Heavy vanilla
  blocks all hash to a single shape.

### Phase 2a — Vanilla Path B blocks (3 files, 9 variants)

- [x] `skills/ark-workflow/chains/greenfield.md` — Light/Medium/Heavy
- [x] `skills/ark-workflow/chains/bugfix.md` — Light/Medium/Heavy
- [x] `skills/ark-workflow/chains/hygiene.md` — Light/Medium/Heavy (NOT
  Audit-Only — that's Phase 2b)

### Phase 2b — Special templates (2 files, 3 variants)

- [x] `skills/ark-workflow/chains/hygiene.md` — Audit-Only gets Special-A
  (findings-only; closeout is `/wiki-update` → STOP)
- [x] `skills/ark-workflow/chains/knowledge-capture.md` — Light + Full gets
  Special-B (`/claude-history-ingest` substitutes for `/deep-interview` because
  capture is reflective, not prospective)

### Phase 3 — Remaining vanilla blocks (3 files, 7 variants)

- [x] `skills/ark-workflow/chains/migration.md` — Light/Medium/Heavy (Heavy
  annotates `/team` as suitable autopilot variant)
- [x] `skills/ark-workflow/chains/performance.md` — Light/Medium/Heavy
  (Medium + Heavy annotate `/ralph` as suitable for benchmark-driven)
- [x] `skills/ark-workflow/chains/ship.md` — Standalone (discouraged but shown
  per discoverability-over-neutrality)

### Phase 4 — v1.13.0 release artifacts (4 files)

- [x] `VERSION` 1.12.0 → 1.13.0
- [x] `.claude-plugin/plugin.json` version bump
- [x] `.claude-plugin/marketplace.json` plugins[0].version bump
- [x] `CHANGELOG.md` v1.13.0 entry (Added, Changed, Degradation contract,
  Observability, Commit convention, Plan)

### Phase 5 — Upstream vault artifacts (3 files)

- [x] This epic
- [x] `vault/Session-Logs/S007-OMC-Integration-Design.md`
- [x] `vault/Compiled-Insights/Execution-Philosophy-Dual-Mode.md`
- [x] `vault/TaskNotes/meta/Arkskill-counter` incremented 3 → 4

## Tests

- `check_path_b_coverage.py --chains ... --expected-blocks 19` → `OK: 19 Path B
  block(s); 3 distinct canonicalized shape(s)`.
- `check_chain_integrity.py --chains ...` → `OK: 7 chain files check clean`.
- Python probe unit test: `has_omc` key present, True when CLI set, False with
  `has_omc_skip_reason` when neither CLI nor cache-dir present.
- Bash probe test: `HAS_OMC=true` when OMC installed; `ARK_SKIP_OMC=true`
  overrides to false.

## Next Steps

Follow-ups captured in the plan's ADR § Follow-ups:

1. Pin `/autopilot` execution-only mechanism (flag vs. env var). Current
   fallback: `OMC_EXECUTION_ONLY=1` env-var wrapper. ADR follow-up after
   real-world Path B smoke test.
2. Telemetry rotation policy for `.ark-workflow/telemetry.log` (currently
   unbounded append; v1.14.x).
3. Evaluate a fifth Section 4 sub-contract if `/ccg` (tri-model consensus)
   enters Path B as its own execution engine.
4. Downstream grep-pinning detection — find consumer CLAUDE.md files that
   hardcode `HAS_OMC=false`; proactively notify maintainers.
