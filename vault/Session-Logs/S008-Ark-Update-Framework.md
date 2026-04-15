---
title: "Session 8: /ark-update Version-Driven Migration Framework (v1.14.0 Stream B)"
type: session-log
tags:
  - session-log
  - S008
  - skill
  - ark-update
  - migration
  - deep-interview
  - ralplan
  - autopilot
  - code-review
  - release
summary: "Shipped /ark-update — version-driven migration framework that converges projects to the current ark-skills target profile. 19-skill plugin, 237 tests, ~2000 LOC. Combined v1.14.0 release with Stream A (OMC detection)."
session: "S008"
status: complete
date: 2026-04-14
prev: "[[S007-OMC-Integration-Design]]"
epic: "[[Arkskill-004-ark-update-framework]]"
source-tasks:
  - "[[Arkskill-004-ark-update-framework]]"
created: 2026-04-14
last-updated: 2026-04-14
---

# Session 8: /ark-update Version-Driven Migration Framework (v1.14.0 Stream B)

## Objective

Ship a generalized, version-driven migration framework for ark-skills
downstream projects. Replace ad-hoc per-release upgrade scripts with a
declarative target profile plus pluggable per-version destructive
migrations. Idempotent, auditable, path-safe, POSIX-only. Stream B of the
combined v1.14.0 release (Stream A = OMC plugin detection in
`/ark-onboard` + `/ark-health`, already landed on branch).

## Context

Entry state (post-S007):
- v1.13.0 shipped dual-mode `/ark-workflow` + `/ark-context-warmup`.
- `/ark-onboard` already handled greenfield + repair; but **version drift**
  (plugin upgraded, project conventions out-of-date) was still a manual
  process — every v(N)→v(N+1) bump required an ad-hoc script.
- Stream A started in parallel: add OMC plugin detection to `/ark-onboard`
  and `/ark-health` Check 21. That landed first on the shared branch.

Goal: a version-driven sibling to `/ark-onboard repair`. "Plugin version
bumped? Run `/ark-update` to converge your project to the new target
profile." Additive conventions (managed CLAUDE.md regions, gitignore
entries, MCP server rows, templated files) apply via HTML-comment-marker
idempotency. Destructive migrations (deletions, restructurings) live in
`migrations/*.yaml` and run only once per project per version, tracked in
`.ark/migrations-applied.jsonl`.

## Work Done

### Phase 0 — Deep interview (pre-implementation)

`/deep-interview` on the framework — 5 rounds. Converged around:
- **Declarative target profile** (YAML) vs. imperative per-release scripts.
- **Two-phase engine**: Phase 1 (destructive replay) before Phase 2
  (target-profile convergence). Phase 1 is write-ordered (pending
  migrations applied oldest→newest); Phase 2 is idempotent.
- **Two-base-class op hierarchy**: `TargetProfileOp` (Phase 2,
  idempotent, convergence-oriented) vs. `DestructiveOp` (Phase 1,
  one-shot per version). Justified in code comment.
- **HTML-comment marker** (not `# ark:managed` line) so idempotency works
  inside CLAUDE.md without breaking markdown rendering.
- **POSIX-only for v1.0** — Windows bash/powershell deferred (codex P2-7).

### Phase 1 — Ralplan consensus (pre-implementation)

`/ralplan` iteration 1: Architect ITERATE (5 findings), Critic ITERATE
(8 findings). Iteration 2: both APPROVE. Plan covered Steps 0 through 11.

### Phase 2 — Codex plan review (pre-implementation)

Separate-lane `/codex` review on the ralplan. 8 findings applied directly
to the plan and spec before execution:

- **P1-1 — Path traversal.** Added `safe_resolve` + `PathTraversalError`
  gate; dual validation (load-time + dispatch-time).
- **P1-2 — Clean-run zero-write invariant.** `state.maybe_append_log_and_pointer`
  short-circuits on clean runs; no log append, no pointer rewrite.
- **P2-3 — Marker `version=` drift.** Stale version triggers rewrite+backup
  even when content matches template.
- **P2-4 — Log schema.** `failed_ops[]` array + optional `depends_on_op`
  field for destructive migration entries.
- **P2-5 — Per-op dry_run parity tests.** Every op test file includes a
  `test_dry_run_matches_apply` case.
- **P2-6 — Max-semver `installed_version`.** Derive from JSONL
  `(semver, phase)` dedup; never timestamp-sort.
- **P2-7 — POSIX-only.** Scripts assume bash/zsh on macOS/Linux/WSL2.
- **P2-8 — Repo-wide check-count phrasing.** Step 8 uses grep-based edit
  worklist (not hardcoded line numbers) to update all "N checks" phrasings.

### Phase 3 — Autopilot execution (Steps 0-11)

Full 11-step execution. All commits on branch `ark-update`:

| Step | Commit | Deliverable |
|---|---|---|
| 0 | `5874e2f` | Skill skeleton + POSIX-only declaration |
| 1 | `c414d10` | Shared infra (paths.py, state.py, markers.py) |
| 2 | `6e32b34` | Engine skeleton (migrate.py, plan.py, op base classes) |
| 3.1 | `64f8f39` | `ensure_claude_md_section` op |
| 3.2 | `9e18a5b` | `ensure_gitignore_entry` op |
| 3.3 | `492a95f` | `ensure_mcp_server` op (w/ `_ark_managed` sentinel + clobber guard) |
| 3.4 | `fa3a0a1` | `create_file_from_template` op (w/ symlink-target guard) |
| 3.5 | `09cb95b` | `ensure_routing_rules_block` op (subclass) |
| 4 | `27cb927` | Target profile backfill + templates |
| 5 | `e8e90bb` | CI validator `check_target_profile_valid.py` |
| 6.1-6.4 | `6bda5fe`, `05451bb`, `4ca8789`, `f0bb4f9` | 7 fixtures + convergence/idempotency/dry-run/refusal/destructive-replay/e2e/logging/summary/provenance tests + MANUAL_STAGE5.md |
| 7 | `a9958c8` | SKILL.md full wrapper + gate-flag resolution |
| 8 | `7b022ae` | Cross-refs in /ark-onboard + /ark-health (Check 22) |
| 9 | `a3777b3` | README skill table entry |
| 10 | `dfc24fe` | Stage-5 self-test gate PASSED |
| 11 | `cf0ec41`, `cf27568` | /codex + /ark-code-review + P1 fix |

### Phase 4 — Stage-5 ship gate (mandatory)

Full pytest: 214/214 pass. Manual runbook for 3 historical fixtures
(pre-v1.11, pre-v1.12, pre-v1.13):
- Fixture authenticity check (no git tags exist in repo; visual inspection
  attested each fixture represents believable pre-v(N) state).
- End-to-end via `migrate.py` CLI (not Claude harness). All 3 produce
  post-state byte-exact to `expected-post/`.
- Idempotency spot-check: second run on pre-v1.11 yielded
  "clean — nothing to do", zero file changes, no JSONL append (codex P1-2
  invariant held in the wild).

Evidence:
`vault/Session-Logs/2026-04-14-stage5-self-test-evidence.md`.

### Phase 5 — Step 11 code review (two-lane)

**`/ark-code-review` multi-agent synthesis** (code-reviewer, code-architect,
test-coverage-checker, silent-failure-hunter, test-analyzer): 1 P1 + 6 P2 +
5 P3. P1-A: gate-flag code paths wired in Step 7 but had zero test
coverage.

**Codex second-opinion** (manual fallback — `omc ask codex` wrapper
returned empty artifact across 3 invocation variants; reviewer agent
performed manual review in place): 2 P1 + 6 P2 + 5 P3. Codex's second P1
(non-atomic pointer/log writes) was rated P2 by /ark-code-review and
deferred to v1.1 ADR.

**P1 fix (`cf0ec41`)**: `tests/test_gate_flags.py` with 23 new tests
(9 unit `_read_gate_flags`, 8 unit `_iter_target_profile_entries`, 5 e2e
subprocess runs, 1 smoke). Pinned the actual behavior of `_read_gate_flags`
for edge-case env var values — strict `"1"` match; empty/"true"/"yes" all
return False; whitespace-stripped. Stale `test_convergence.py` docstring
corrected. SKILL.md centralized-vault detection comment clarified
(comment-only).

Re-verification: 237/237 passing + pre-v1.11 smoke convergence PASS.

Findings + triage:
`vault/Session-Logs/2026-04-14-step11-review-findings.md`.

## Decisions Made

1. **Declarative target profile over imperative per-release scripts.**
   Replayable, auditable, version-controlled; adding a new convention is
   one YAML entry.
2. **Two-base-class op hierarchy.** Phase 1 (destructive, one-shot) vs.
   Phase 2 (convergence, idempotent) have fundamentally different
   semantics. `DestructiveOp` is wired-but-empty in v1.0; first destructive
   migration ships at v1.x.y when needed.
3. **HTML-comment markers with `version=` attribute.** `<!-- ark:begin id=...
   version=... -->` lets the engine detect stale stamps even when content
   matches (codex P2-3).
4. **Gate flags degrade safely when unset.** `ARK_HAS_OMC` / `ARK_CENTRALIZED_VAULT`
   unset = unconditional application (backward-compat). Only exact
   `"1"` / `"0"` values recognized; other values degrade to "disabled."
5. **Ship with codex atomic-write P1 deferred, not fixed.** Blast radius
   bounded: JSONL is append-only with `(semver, phase)` dedup (no
   double-apply), pointer is advisory. Repair path exists via
   `/ark-onboard`. Document in v1.1 ADR-1.
6. **Combined v1.14.0 release PR.** Stream B lands after Stream A (already
   on branch). Stream B owns the release commit that bumps VERSION +
   plugin.json + marketplace.json + CHANGELOG for both streams.

## Open Questions

Captured as v1.1.0 ADR candidates (see
`2026-04-14-step11-review-findings.md` for full list):

- Atomic filesystem writes (ADR-1): pointer, log append, drift overwrites,
  empty-file-on-failure
- Schema versioning (ADR-2): engine-load check for `schema_version`
  bound
- Operational surface hardening (ADR-3): exit code for partial runs,
  `detect_drift` contract for malformed inputs, gitignore-source
  completeness
- Code-quality cleanup: deduplicate `_iter_target_profile_entries` between
  migrate.py and plan.py; remove dead `_check_gate`; P3 nits

## Issues & Discoveries

1. **`omc ask codex` wrapper did not produce artifact in this session.**
   Three invocation variants tried (`--cwd` flag unsupported; `codex
   review --base master -` stdin+base combo rejected; `omc ask codex -p
   "..."` background exit 0 but empty output file). Reviewer agent
   performed full manual code review as fallback. Action: future Stream
   runs verify wrapper config or prefer direct `codex` CLI. Logged
   against the OMC integration issues list.

2. **No git tags in repo.** Fixture authenticity check couldn't diff
   against `git show v1.10.1:CLAUDE.md` etc. because tags are not
   materialized in this worktree. Visual inspection sufficed; if we want
   stronger guarantees later, bootstrap tags from upstream master.

3. **Step 6 executor expanded scope.** Added `MarkerIntegrityError`
   hard-refusal + `_check_ark_not_gitignored` pre-mortem guard +
   `.bak.meta.json` provenance sidecar beyond fixture authoring.
   Judgment call — these were needed for the backup-provenance + refusal
   tests and matched plan acceptance criteria. Accepted.

## Next Steps

1. **Stage 9 — combined v1.14.0 release PR.** Bump `VERSION` 1.13.0 →
   1.14.0; bump `plugin.json`, `marketplace.json`; add CHANGELOG entry
   covering **both** Stream A (OMC detection, Check 21) **and** Stream B
   (`/ark-update` framework, Check 22). Single release commit. Open PR
   against `master` via `gh pr create` with verification checklist
   (Stage-5 gate evidence, review verdicts, test counts, stream
   coordination integrity).

2. **v1.1.0 ADRs.** Open GitHub issues or plan docs for ADR-1/ADR-2/ADR-3
   and the cleanup PR. Reference commit `cf27568` as source of findings.

3. **Real-world smoke test.** Run `/ark-update` against a downstream Ark
   project after v1.14.0 ships. Verify: SKILL.md wrapper preflight, env
   var export, migrate.py invocation, summary rendering, commit-message
   suggestion. Surface any friction in ADR follow-ups.

4. **Destructive migration pilot.** First time `/ark-update` ships a
   real `migrations/*.yaml` file, validate the Phase 1 replay + dedup
   + `depends_on_op` chain on a real project.
