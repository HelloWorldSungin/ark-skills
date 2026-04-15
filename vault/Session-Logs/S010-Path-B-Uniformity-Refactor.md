---
title: "Session 8: Path B Uniformity Refactor (audit + 7-commit implementation)"
type: session-log
tags:
  - session-log
  - S010
  - skill
  - ark-workflow
  - omc
  - path-b
  - uniformity
  - refactor
  - audit
  - drift-lint
summary: "Audited /ark-workflow Path B routing; implemented 2026-04-14 uniformity decision in 7 atomic commits on branch ark-workflow-improve-OMC. All chain Path B engines collapsed to /autopilot except Migration Heavy (/team). Added chain drift lint (R4). 17 blocks / 4 classifier shapes / 5 raw-text hashes. Shipped in v1.16.0 via PR #18 (renumbered from S008 during rebase onto master's S008/S009)."
session: "S010"
status: complete
date: 2026-04-15
prev: "[[S007-OMC-Integration-Design]]"
epic: "[[Arkskill-006-path-b-uniformity]]"
source-tasks:
  - "[[Arkskill-006-path-b-uniformity]]"
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-15
last-updated: 2026-04-15
---

# Session 8: Path B Uniformity Refactor

## Objective

Audit the 2026-04-13-shipped dual-mode `/ark-workflow` routing (S007,
v1.13.0) for OMC engine misfits, then implement the resulting uniformity
decision across all chain files + reference docs + CI lint. The audit had
been prepared earlier on this branch; this session converted its findings
into atomic commits landing R1, R2, R4, R10, R11, R15, R16, R17 (with
R3/R6/R7/R12/R13/R14/R18 deferred and R5/R8/R9 resolved or obsolete).

## Context

Entry state:
- `0376ebc` (v1.14.0) had shipped `/ark-code-review --thorough` vendor
  fan-out via `omc ask`, but on this branch it remained unpushed. That
  work was NOT given its own session log — should be backfilled later.
- An OMC routing audit had been written to
  `.ark-workflow/audits/omc-routing-audit-2026-04-14.md` (22KB).
  The audit surfaced 18 recommendations via both Claude's draft and a
  Codex adversarial review, with the most important being R5 — a meta-
  question of whether Path B was optimizing for a uniform operator mental
  model or best-specialized engine per chain.
- User answered R5 on 2026-04-14 in favor of **uniformity**, captured in
  auto-memory (`project_ark_workflow_uniform_path_b.md`).
- Unstaged WIP existed: `/codex → /ask codex | /ccg` call-site rename
  across 5 chain files + `troubleshooting.md`.

## Work Done

### Pre-R1: WIP commit (`0856b8e`)

Landed the unstaged `/codex → /ask codex | /ccg` rename as its own commit
before any R-refactor work. Aligns the chain files with v1.14.0's
external-second-opinion conventions (single-advisor `/ask codex`,
multi-advisor `/ccg`). No behavior change; pure doc rename.

### R1 — Doc drift correction (`b3926c3`)

Rewrote `omc-integration.md` §4.1 to reflect the correct autopilot phase
layout (Expansion=0, Planning=1, Execution=2, QA=3, Validation=4,
Cleanup=5, per autopilot SKILL.md:39-72). Deleted §4.2 (/ralph handback)
and §4.3 (/ultrawork handback) since no chain routes to those engines
as step-3 under uniformity. Renumbered §4.4 (/team) → §4.2, §4.5 (crash
recovery) → §4.3. Updated `chains/migration.md` cross-references for the
§4.4 → §4.2 renumber.

Rewrote §6 to retire the fictional `OMC_EXECUTION_ONLY=1` env var. Grep
of OMC v4.11.5 source returned zero matches for the proposed env var.
New §6 frames Ark's closeout `/ark-code-review` as intentional
defense-in-depth (second-layer Ark-conventions review on top of
autopilot's internal Phase 4 Validation), not accidental duplication.

### R2 — Engine collapse to uniform /autopilot (`1b5b8ae`)

- `chains/greenfield.md` Heavy Path B step 3: `/ultrawork` → `/autopilot`.
  Added a `*Note:*` above the Path B block (outside canonicalization)
  preserving the internal-/ultrawork-Phase-2 parallelism context.
- `chains/performance.md` Medium + Heavy Path B step 3: `/ralph` →
  `/autopilot`. Similar `*Note:*` pattern for internal /ralph context.
- `chains/bugfix.md` Heavy Path B already used `/autopilot` (from the
  WIP); no chain-block edit needed. Only the `omc-integration.md §2`
  rationale row ("/autopilot or /ralph") was cleaned.
- Propagated new step-3 wording ("full pipeline; auto-skips Phase 0+1
  when it detects the pre-placed artifacts from steps 1+2") to all 15
  Vanilla Path B blocks + §5 Template Vanilla. Special-A (Hygiene
  Audit-Only) and Special-B (Knowledge-Capture Light) step-3 wordings
  updated in parallel, preserving their unique semantic suffixes
  ("produces findings document" / "runs /wiki-ingest + /cross-linker +
  /tag-taxonomy").
- `omc-integration.md` §1 Two Philosophies paragraph updated to reflect
  /autopilot-or-/team binary choice.
- `check_path_b_coverage.py` — `ALLOWED_SHAPES` → `{vanilla: 15, team: 1,
  special-a-hygiene-audit-only: 1, special-b-knowledge-capture: 1}` (sum
  18 for R2 intermediate state, before R17). Removed `has_ralph` and
  `has_ultrawork` branches from `_classify_shape` and
  `_classification_flags`. `--max-distinct-shapes` default 6 → 4.
- `test_check_path_b_coverage.py` fixed pre-existing 19-vs-18 drift
  (test file asserted 19 blocks in 7 places while script default was 18).
  Renamed `test_allowed_shapes_sum_to_19` →
  `test_allowed_shapes_sum_to_18`; same for shapes test. Deleted
  `test_ralph_block` and `test_ultrawork_block`; added new
  `test_ralph_mention_inside_vanilla_still_classifies_as_vanilla` as the
  critical invariant that descriptive internal-engine mentions in vanilla
  blocks don't leak back into the classifier.

### R15 + R16 + R17 — Housekeeping bundle (`bf0187d`)

- **R15**: `omc-integration.md:111` "Verbatim keyword list" → "Superset
  of canonical omc-reference list" + documented the 3 Ark-added
  non-canonical keywords (`team` / `/team`, `ultrawork`, `deep-interview`
  hyphenated form).
- **R16**: Signal #3 Multi-module scope gained a parenthetical:
  "LLM-judgment call during triage — no mechanical counter exists in
  SKILL.md or any helper script; grep-verified".
- **R17**: Deleted the entire Ship Standalone Path B block from
  `chains/ship.md` (lines 13-24). Removed the Ship Standalone row from
  `omc-integration.md` §2 and §4 tables; dropped the "(Ship Standalone
  always uses --thorough.)" caveat from §5 Template Vanilla. Script
  updates landed in the same commit: `ALLOWED_SHAPES[vanilla]` 15 → 14
  (sum 17), `--expected-blocks` default 18 → 17, shape-distribution
  conditional `== 18` → `== 17`.
- Ordering rationale: R17 landed BEFORE R4 (drift lint) so the lint ran
  against a clean state (ship.md's stale `Phase 5 (docs/ship)` line
  would have tripped the drift regex otherwise).

### R4 — Chain drift lint (`3294d9e`)

New `skills/ark-context-warmup/scripts/check_chain_drift.py` (CLI) +
`test_check_chain_drift.py` (pytest harness). Banned patterns:
1. Literal `OMC_EXECUTION_ONLY` anywhere
2. `Phase 5 (docs/ship)` (stale phase claim)
3. `internal Phase 4 (execution)` (stale phase claim)
4. Step-3 anchored regex `^3\. \`/(ultrawork|ralph)\`` (MULTILINE) —
   flags only when the numbered-list step-3 line's FIRST backtick-wrapped
   engine is `/ultrawork` or `/ralph`. Descriptive mentions inside
   vanilla step-3 lines (e.g., "Execution via internal /ralph") are
   deliberately whitelisted since the first engine is `/autopilot`.

False-positive guard test (`test_internal_ralph_mention_inside_vanilla_
still_classifies_as_vanilla`) pins this invariant.

### R10 — /external-context pre-step (`5856c2c`)

Added `/external-context` as new pre-step 1 in Migration Medium + Heavy
Path B blocks (fan-out doc-specialist agents to gather authoritative
framework migration guides before `/deep-interview`). Renumbered all
subsequent steps (step 4 engine, step 5 `<<HANDBACK>>`, step 6 Ark
closeout). Migration Heavy retains `/team` engine.

**Hash-count vs shape-count discovery**: adding the pre-step made
Migration Medium and Heavy block bodies one line longer than other
variants, yielding distinct raw-text canonicalized hashes (hash count
went 4 → 5). `_classify_shape` still returns "vanilla" / "team" for
these blocks because the classifier keys on engine + closeout markers,
not step count. Bumped `--max-distinct-shapes` default 4 → 5 and
documented the distinction in `omc-integration.md` §4 footnote + the
script's docstring.

### R11 — /visual-verdict closeout + audit addendum (`8207174`)

- `chains/greenfield.md` Medium Path A: added `/visual-verdict (if UI
  with design reference)` as new step 8 (after `/qa (if UI)`);
  renumbered subsequent steps.
- `chains/greenfield.md` Heavy Path A: added `/visual-verdict (if UI
  with design reference)` as new step 13 (after `/design-review (if UI)`);
  renumbered subsequent steps.
- Light Path A intentionally untouched (no /qa or /design-review steps;
  design reference unlikely for Light variants).
- `SKILL.md` Condition Resolution gained a "UI-with-design-reference
  trigger (for /visual-verdict)" entry documenting the detection signals
  (`design/`, `mocks/`, `DESIGN.md`, Figma export, or explicit reference
  in the task prompt) and the graceful-skip behavior.
- Path B blocks unchanged (/visual-verdict is a closeout skill, not an
  engine).
- Appended "Implementation addendum — 2026-04-15" to the audit report
  with the commit-SHA table, V1/V2/V3 verification results, status of
  all 18 recommendations, and 5 scope refinements surfaced during
  implementation.
- `.gitignore` updated from `.ark-workflow/` to `.ark-workflow/*` +
  `!.ark-workflow/audits` + `!.ark-workflow/audits/**` so audit reports
  are trackable while chain state remains ignored.

## Decisions Made

1. **Commit ordering: R15+R16+R17 before R4** — so the drift lint landed
   against a clean post-R17 state instead of pre-R17 drift. Avoided a
   temporary test_real_repo_files_pass failure window.
2. **V1 runtime probe deferred** — full `/autopilot` invocation would
   hijack the session agent. Static verification of autopilot SKILL.md:
   41, 42, 173-189 suffices for the premise; runtime probe noted as a
   follow-up with low-but-nonzero risk. Refactor is reversible via `git
   revert` if a future probe exposes deviation.
3. **Hash count ≠ shape count** — `/external-context` R10 pre-step adds
   distinct raw-text hashes without changing classifier-visible shapes.
   Kept `max-distinct-shapes=5` for R10's intermediate state rather than
   extending canonicalization to strip step-count variance.
4. **V2 expected count corrected to 4 shapes (not 2)** — the initial
   prompt's "2 shapes" estimate didn't account for Special-A's `STOP`
   marker and Special-B's `/wiki-ingest` marker remaining classifier-
   distinct independent of engine uniformity. Fixed via AskUserQuestion
   during planning; plan reflects 4 classifier shapes from the start.
5. **Bugfix.md R2 chain-block no-op** — the pre-existing WIP had already
   landed `/autopilot` at Bugfix Heavy step 3. Only the
   `omc-integration.md §2` rationale row needed cleanup. Documented in
   R2 commit message for reviewer clarity.
6. **Pre-existing test drift bundled into R2** — `test_check_path_b_
   coverage.py` had been asserting 19 blocks while the script defaulted
   to 18. Fixed atomically with R2's engine collapse rather than
   leaving the inconsistency.
7. **Audit reports tracked, chain state remains ignored** — changed
   `.gitignore` rule to allow `.ark-workflow/audits/` while keeping
   `current-chain.md` and `telemetry.log` local-only.

## Open Questions

1. **Full runtime probe of autopilot auto-skip** — static prescription
   confirmed; runtime behavior assumed matches. Worth running as a
   follow-up with a trivial task pre-placed with artifacts.
2. **v1.14.0 session log backfill** — commit `0376ebc` ("External Second
   Opinion via omc ask") shipped before this session but without its own
   session log. Should be backfilled for continuity.
3. **CI infrastructure not yet wired** — the drift lint and coverage
   check ship as pytest tests. When `.github/workflows/` is eventually
   added (separate session), both scripts should be invoked there.

## Next Steps

In priority order:

1. **Push the 7 uniformity commits** to master (after user review).
   Branch is `ark-workflow-improve-OMC`; currently 8 commits ahead of
   master (1 was v1.14.0's `0376ebc` which is already stable).
2. **Version bump + CHANGELOG** — batch with R3 (HAS_CODEX/HAS_GEMINI
   back-port) for the next release cycle. Per user instruction, not
   done this session.
3. **R3, R6, R7, R12, R13, R14, R18** — deferred. See audit addendum.
4. **v1.14.0 session log backfill** — separate session; name it
   `S008.5-v1.14.0-external-second-opinion.md` or similar.
5. **CI wiring** — add `.github/workflows/ci.yml` invoking the pytest
   suite under `skills/ark-context-warmup/scripts/`.
