---
tags:
  - task
title: "/ark-update Version-Driven Migration Framework"
task-id: "Arkskill-004"
status: ready-to-ship
priority: high
project: "ark-skills"
work-type: development
task-type: epic
urgency: normal
session: "S008"
created: "2026-04-14"
last-updated: "2026-04-14"
source-sessions:
  - "[[S008-Ark-Update-Framework]]"
---

# Arkskill-004: /ark-update Version-Driven Migration Framework

## Summary

Ship `/ark-update` — a generalized, version-driven migration framework that
converges downstream Ark projects to the current ark-skills target profile.
Replaces ad-hoc per-release upgrade scripts with a declarative target profile
plus pluggable per-version destructive migrations. Idempotent via HTML-comment
markers. State persisted in `.ark/plugin-version` and
`.ark/migrations-applied.jsonl`. Drift inside managed regions is backed up
with a `.bak.meta.json` provenance sidecar. POSIX-only for v1.0.

Distinct from `/ark-onboard repair` (failure-driven): `/ark-update` is the
version-driven sibling. Refuses on malformed CLAUDE.md / `.mcp.json` /
`.ark/migrations-applied.jsonl` and hands off to `/ark-onboard` repair.

Part of the **combined v1.14.0 release** with Stream A (OMC plugin detection
in `/ark-onboard` + `/ark-health` Check 21).

## Spec & Plan

- Deep-interview spec: `.omc/specs/deep-interview-ark-update-framework.md`
- Ralplan consensus: `.omc/plans/ralplan-ark-update.md` (Architect + Critic APPROVE)
- Codex plan review: 8 findings applied (P1-1 path safety, P1-2 clean-run
  zero-write, P2-3 marker version drift, P2-4 failed_ops/depends_on_op,
  P2-5 per-op dry_run coverage, P2-6 max-semver installed_version,
  P2-7 POSIX-only, P2-8 repo-wide grep for check-count phrasing)

## Stream Architecture

This is **Stream B** of the v1.14.0 combined release. **Stream A**
(OMC plugin detection in `/ark-onboard` Healthy Step 3 + Greenfield Step 18
+ scorecard, `/ark-health` Check 21) is landed on the same branch via
commits `28030b3`, `1535214`, `47d7190`. Stream B lands last and owns the
combined release PR.

## Implementation — DONE (v1.14.0)

### Step 0 — Skill skeleton (`5874e2f`)
Directory layout, SKILL.md stub, target-profile.yaml placeholder,
POSIX-only declaration.

### Step 1 — Shared infrastructure (`c414d10`)
- `scripts/paths.py` — `safe_resolve` + `PathTraversalError` (codex P1-1)
- `scripts/state.py` — log append, pointer write, lock, backup path,
  clean-run invariant, max-semver installed_version (codex P2-6)
- `scripts/markers.py` — HTML-comment region extract/replace/insert with
  version= drift signal (codex P2-3)

### Step 2 — Engine skeleton (`6e32b34`)
- `scripts/migrate.py` — CLI entry point, Phase 1 (destructive replay) +
  Phase 2 (target profile) orchestration
- `scripts/plan.py` — dry-run plan builder
- `scripts/ops/__init__.py` — `TargetProfileOp` + `DestructiveOp` base
  classes, `OP_REGISTRY`

### Step 3 — Op implementations
- 3.1 `ensure_claude_md_section` (`64f8f39`)
- 3.2 `ensure_gitignore_entry` (`9e18a5b`)
- 3.3 `ensure_mcp_server` with `_ark_managed` sentinel + clobber refusal (`492a95f`)
- 3.4 `create_file_from_template` with symlink-target guard (`fa3a0a1`)
- 3.5 `ensure_routing_rules_block` as subclass of `ensure_claude_md_section` (`09cb95b`)

### Step 4 — Target profile backfill + templates (`27cb927`)
Populated target-profile.yaml: managed_regions (omc-routing since 1.13.0,
routing-rules at 1.12.0), ensured_gitignore (.ark-workflow/ since 1.13.0),
ensured_files (setup-vault-symlink gated on centralized-vault since 1.11.0),
ensured_mcp_servers.

### Step 5 — CI validator (`e8e90bb`)
`scripts/check_target_profile_valid.py` — schema validator + drift guard
ensuring `templates/routing-template.md` stays byte-equal to
`skills/ark-workflow/references/routing-template.md`.

### Step 6 — Historical fixtures + convergence tests (4 commits: `6bda5fe`, `05451bb`, `4ca8789`, `f0bb4f9`)
Seven fixtures (pre-v1.11, pre-v1.12, pre-v1.13, fresh, healthy-current,
drift-inside-markers, drift-outside-markers) × convergence, idempotency,
dry-run, refusal-mode, destructive-replay, e2e-shell, logging, run-summary,
backup-provenance tests. `tests/MANUAL_STAGE5.md` runbook for the ship gate.

### Step 7 — SKILL.md full wrapper + gate-flag resolution (`a9958c8`)
210-LOC SKILL.md — preflight git check, ARK_SKILLS_ROOT resolution,
HAS_OMC probe, centralized-vault detection, env-var passing to migrate.py,
pre-run warning for inside-marker overwrite, post-run summary rendering,
refusal-mode handoffs to `/ark-onboard repair`.

### Step 8 — Cross-references in /ark-onboard and /ark-health (`7b022ae`)
- `/ark-onboard` Repair section: anchored `/ark-update` cross-reference
  paragraph (`<!-- stream-b: ... begin/end -->`)
- `/ark-health` new `### Plugin Versioning (Checks 22+)` section with
  Check 22 (`ark-skills version current?`, warn-only, asserts `.ark/`
  not gitignored)
- Repo-wide check-count phrasing updated: Stream A added Check 21, Stream
  B added Check 22 → final count 22 consistent across both SKILLs
  (codex P2-8)

### Step 9 — README entry (`a3777b3`)
`/ark-update` row added to skill table under Onboarding. Skill count
18 → 19. `/ark-health` paragraph updated 20 → 22 checks.

### Step 10 — Stage-5 self-test gate (`dfc24fe`)
MANDATORY hard ship gate. Full pytest (214 pass). Fixture authenticity
check + end-to-end convergence via migrate.py CLI on pre-v1.11 / pre-v1.12
/ pre-v1.13. Idempotency spot-check. Evidence captured in
`vault/Session-Logs/2026-04-14-stage5-self-test-evidence.md`.

### Step 11 — Codex + /ark-code-review + P1 fix (`cf0ec41`, `cf27568`)
Two-lane review surfaced one consensus P1 blocker (gate-flag tests
missing). Fix landed in `cf0ec41`: `tests/test_gate_flags.py` with 23 new
tests pinning `ARK_HAS_OMC` and `ARK_CENTRALIZED_VAULT` behavior
(214 → 237 tests). One codex-only P1 (non-atomic pointer/log writes)
deferred to v1.1 ADR (bounded blast radius; /ark-code-review rated P2).
Findings + triage captured in
`vault/Session-Logs/2026-04-14-step11-review-findings.md`.

## Tests

- `python3 -m pytest skills/ark-update/tests/ -v` → **237 passed in ~9s**
- Unit: paths (9), state (26), markers (23), plan (14), 5 op tests (43)
- Integration: convergence, idempotency, dry-run, refusal-modes,
  destructive-replay, e2e-shell, logging, run-summary, backup-provenance,
  gate-flags, CI validator
- Manual Stage-5: 3 historical fixtures converged via CLI; idempotency
  spot-check zero-write confirmed

## Metrics

- **~2000 LOC** new scripts + tests (migrate.py ~700, ops ~900, state/markers/paths ~500, tests ~900, SKILL.md 210, templates ~60)
- **22 commits** on branch `ark-update` (Stream B Steps 0-11 + Step 11 P1 fix + Step 11 docs marker)
- **237 tests** passing
- **7 historical fixtures** + `expected-post/` sidecars
- **5 ops** (2 base classes: TargetProfileOp + DestructiveOp scaffold)
- **Schema version 1** with designated follow-up for engine-load validation (P2-1)

## Codex/Review Follow-ups (v1.1.0 ADRs)

See `vault/Session-Logs/2026-04-14-step11-review-findings.md` for full
triage. Deferred items grouped as ADR candidates:

- **ADR-1 Atomic filesystem writes** — covers non-atomic pointer/log,
  drift overwrites, empty-file-on-failure
- **ADR-2 Schema versioning** — engine-load check for `schema_version`
- **ADR-3 Operational surface hardening** — exit code for partial runs,
  `detect_drift` contract for malformed inputs, gitignore-source
  completeness
- **Code-quality cleanup** — deduplicate `_iter_target_profile_entries`,
  remove dead `_check_gate`, P3 nits

## Next Steps

1. Stage 8 — `/wiki-update` session log (this doc is the epic side)
2. Stage 9 — combined v1.14.0 release PR: bump VERSION 1.13.0 → 1.14.0,
   plugin.json + marketplace.json, CHANGELOG covering both streams,
   single release commit, open PR against master
