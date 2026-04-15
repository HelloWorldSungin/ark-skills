---
name: ralplan-ark-update
description: Consensus implementation plan for /ark-update generalized version-migration framework (Stream B of v1.14.0)
type: plan
status: READY_FOR_EXECUTION
consensus: APPROVE (Planner + Architect + Critic, iteration 2)
mode: deliberate
spec: .omc/specs/deep-interview-ark-update-framework.md
companion: .ark-workflow/handoffs/stream-a-omc-recommendations.md
worktree: /Users/sunginkim/.superset/worktrees/ark-skills/ark-update
branch: ark-update
ship_target: v1.14.0 (combined with Stream A)
---

# Ralplan — `/ark-update` Generalized Version-Migration Framework

**Planner output for Planner → Architect → Critic consensus loop.** Spec is the source of truth (`.omc/specs/deep-interview-ark-update-framework.md`, ambiguity 0.057, all dimensions ≥ 0.92). This plan translates the spec into an ordered build sequence with dependency graph, test strategy, pre-mortem, and ADR.

---

## Spec-level concerns (flag for Architect/Critic)

None. All 8 architectural questions are resolved with bounded reasoning and every resolution is defensible at the plan level. I'm not re-litigating any of them. Two soft flags for the Architect to confirm or revise — neither contradicts the spec:

1. **Routing-template.md provenance (acceptance criteria line re `ensure_routing_rules_block`).** The spec says "reused from `/ark-workflow`'s `references/routing-template.md`". That file exists. Options at plan time: (a) copy-at-build — duplicate file into `skills/ark-update/templates/routing-template.md` (drift risk between two copies), or (b) load-at-runtime — `template:` field points to `../ark-workflow/references/routing-template.md` (coupling risk; ark-update breaks if ark-workflow reorganizes). Plan picks (a) copy-at-build + a CI check in `check_target_profile_valid.py` that asserts byte-equality between the two copies. Architect may override.
2. **`$ARK_SKILLS_ROOT` discovery in `migrate.py` when invoked standalone.** SKILL.md wrappers use the three-case shell fallback. `migrate.py` is invokable standalone (per acceptance criterion). Plan picks: the shell wrapper in SKILL.md resolves `$ARK_SKILLS_ROOT` and passes it as `--skills-root` to `migrate.py`; when invoked directly from a dev shell, user must export `ARK_SKILLS_ROOT` or pass `--skills-root` explicitly. No in-process discovery duplication. Architect may override.

---

## RALPLAN-DR Summary

### Principles (the plan must honor)

1. **Declarative over imperative.** Engine behavior is fully determined by `target-profile.yaml` + `migrations/*.yaml`. No behavior lives in SKILL.md prose or Python conditionals keyed on strings.
2. **Strict inside/outside marker discipline.** Outside markers is sacred user territory. A test proves byte-equality before/after for every run on every fixture. Any op that ever touches outside-marker content is a bug, not a feature.
3. **Determinism for replay and CI.** Same inputs → same outputs → same log line. `--dry-run` is byte-reproducible across runs. Tests use snapshot sidecars because non-determinism kills snapshot tests.
4. **Graceful degradation at the op boundary.** A failing op writes `result: partial` and continues the run. Never abort mid-run except on the hard refusal classes (dirty tree w/o `--force`, malformed state file, mismatched markers).
5. **Committed state, not user state.** `.ark/` is project state. Tests assert `.gitignore` additions NEVER include `.ark/`.

### Decision Drivers (top 3 axes the plan optimizes)

1. **Testability first.** v1.0 is a framework. If we can't test it end-to-end against real historical-state fixtures, we haven't shipped. Stage-5 self-test is a ship gate, not a nice-to-have.
2. **Low diff surface for parallel streams.** Stream A owns `skills/ark-onboard/SKILL.md` top + `skills/ark-health/SKILL.md` near the check list. Stream B owns `skills/ark-onboard/SKILL.md` Repair section + one new `skills/ark-health/SKILL.md` check row. Sequence B's edits to land at the very end of its chain (smallest merge window).
3. **Op independence for parallel subagent fan-out.** Once `state.py` + `markers.py` are committed, the 5 ops can be implemented in parallel by fan-out subagents without conflicting.

**LOC envelope**: ~4000 lines total (impl ~2000, tests ~1500, fixtures + templates + YAML + markdown ~500). Aggressive for a v1.0 that ships zero destructive migrations in production. Justified by: (a) 4-tier test plan (unit / integration / e2e / observability) is non-negotiable per Principles and user workflow; (b) ship-gate fixture replay against historical plugin versions cannot ship under-tested; (c) engine module split matches brownfield pattern (`check_chain_integrity.py`, `check_path_b_coverage.py` — both modular + self-testing). Collapsing to a single ~500-LOC `converge.py` would fight repo conventions and make v1.1 destructive-migration work harder, not easier.

### Viable Options (≥2 per key axis)

#### Axis: Op implementation shape

| Option | Pros | Cons | Pick |
|---|---|---|---|
| **(A) Class hierarchy** — abstract `Operation` base class with `apply`/`dry_run`/`detect_drift`; 5 subclasses. | Type-checkable. Stable contract. Easy mocking in tests. IDE autocomplete. | More ceremony per op (~30 extra LOC each). Base class evolution drag. | **Pick A.** |
| (B) Registry dict `{op_name: {apply: fn, dry_run: fn, detect_drift: fn}}`. | Minimal ceremony. Lisp-y flexibility. | No static types → runtime-only errors. Tests have to redo contract validation per op. | Rejected — v1.0 needs static guarantees more than 30 LOC savings. |
| (C) Function-per-op with duck-typed dispatch. | Smallest surface. | No shared invariants (e.g., "every apply must return op-status dict"). Drift between ops inevitable. | Rejected — loses the typed-contract benefit and `__init__.py` registry gets ugly. |

#### Axis: `migrate.py` monolithic vs split

| Option | Pros | Cons | Pick |
|---|---|---|---|
| **(A) Split modules** — `migrate.py` (CLI entry), `state.py` (log/pointer), `markers.py` (region I/O), `plan.py` (dry-run builder), `ops/*.py`. | Testable per module. Parallel subagent fan-out possible. Changes isolated. | 5 files instead of 1. Minor import plumbing. | **Pick A.** Spec's implementation-notes appendix already specifies this layout. |
| (B) Monolithic `migrate.py`. | Easier to read top-to-bottom. | Untestable without mock-patching internals. Kills subagent parallelism. | Rejected — breaks driver 3 (op independence). |

#### Axis: Test fixture authoring

| Option | Pros | Cons | Pick |
|---|---|---|---|
| **(A) Manual fixtures** (hand-authored minimal project trees for pre-v1.11, pre-v1.12, pre-v1.13). | Ship v1.0 in a week. Fixtures are tiny and readable. Matches spec non-goal for v1.1 regeneration script. | Human effort to author. Can drift from actual git history. | **Pick A.** Spec explicitly defers regeneration-from-git to v1.1. |
| (B) Regenerate from git history automatically. | Always accurate against real past states. | Complex tooling. Spec non-goal. | Rejected — non-goal. |
| (C) Golden-file-in-repo-root. | One file per test. | Spec explicitly rules this out in favor of `expected-post/` sidecar. | Rejected by spec. |

#### Axis: `ensure_routing_rules_block` implementation

| Option | Pros | Cons | Pick |
|---|---|---|---|
| **(A) Subclass of `ensure_claude_md_section` with preset `id=routing-rules` + fixed template path.** | DRY. One code path for marker section logic. Matches spec's implementation-note tree. | Slight indirection in per-op unit tests. | **Pick A.** Matches spec tree. |
| (B) Independent top-level op with its own logic. | No base-class coupling. | Duplicates 90% of `ensure_claude_md_section`. | Rejected — violates DRY driver. |

#### Axis: Dry-run plan builder

| Option | Pros | Cons | Pick |
|---|---|---|---|
| **(A) Separate `plan.py` that ops contribute to.** | `--dry-run` is a first-class code path, not a boolean flag threaded through every op. Plan report format standardized centrally. | Extra module. | **Pick A.** |
| (B) `dry_run: bool` parameter threaded through `apply()`. | No extra module. | Every op has to remember to branch on the flag everywhere. Easy to ship a "dry-run that actually wrote". | Rejected — too error-prone for a migration tool. |

---

## Deliberate Mode — Pre-Mortem (3 failure scenarios)

### Scenario 1: Silent catastrophic overwrite of user-edited region (HIGHEST risk)

**Story.** User (e.g., ArkNode-AI) upgrades plugin to v1.15. Runs `/ark-update`. Inside `CLAUDE.md`'s `id=omc-routing` region, user had locally added 3 custom routing rules (outside the template but inside the markers). Engine classifies this as drift, writes `.ark/backups/CLAUDE.md.2026-04-22T14:03:00Z.bak`, and overwrites. User loses the 3 custom rules unless they realize the backup exists.

**Preventable?** The spec's resolution is explicit: Q4 chose always-overwrite-with-backup. So this is the chosen trade-off, not a bug. But it becomes a v1.0 failure if:
- (a) the backup isn't actually written (bug in `state.py`),
- (b) the run summary doesn't prominently list the drift event, or
- (c) users don't know to look inside markers.

**Mitigations in this plan:**
1. Test `test_drift_inside_markers` asserts backup file exists at expected path AND contains pre-overwrite bytes (not just "a file exists").
2. Run summary format MUST include a `## Drift events (review .ark/backups/)` section with per-file counts when non-zero, emitted via stderr and the post-run LLM message.
3. SKILL.md pre-run message includes a prominent "Local edits inside `<!-- ark:begin -->` markers will be overwritten with backup" warning.
4. `ensure_claude_md_section` op's `detect_drift` returns `drift_summary` that the run summary renders — not just a boolean.

### Scenario 2: Destructive migration partial-failure leaves project in half-state across versions

**Story.** Future v1.16 ships `migrations/v1.16.0.yaml` with 3 destructive ops. Op 2 fails (e.g., file permission). Per graceful-degradation rule, the engine continues to op 3, which depends on op 2's work and silently corrupts user files. Log records `result: partial`. User runs `/ark-update` again — engine sees v1.16.0 already applied (even partially), skips Phase 1, runs Phase 2, corruption persists.

**Preventable?** Spec says graceful-degradation is a hard requirement. So the fix is not "abort on failure" but "prevent downstream-op cascade failures." 

**Mitigations in this plan:**
1. In the destructive-migration log-entry format, add `failed_ops: [{op_index, op_type, error}]` — not just a count. Re-runs can surface this.
2. Op definitions in a destructive migration YAML support an optional `depends_on_op: <index>` field. If a dependency op failed, the dependent op is marked `skipped_due_to_dependency` instead of attempting and potentially cascading corruption. (This is additive to v1.0; the registry supports it but v1.0 ships with zero destructive migrations, so it's tested but not exercised in production yet.)
3. `migrations-applied.jsonl` with a `partial` entry surfaces in `/ark-health` Check 22+ as a warning (implement inside Stream B's Plugin Versioning section per Step 8 — owned by Stream B, not Stream A).
4. `--resume-partial` CLI flag added in a v1.1 follow-up; documented in ADR Follow-ups.

### Scenario 3: `.ark/` gets accidentally gitignored in downstream projects, silently breaking replay correctness

**Story.** Downstream project maintainer adds a catch-all pattern to `.gitignore` like `.ark*/` or `.a*`. Suddenly `.ark/migrations-applied.jsonl` stops being versioned. Collaborator B clones, runs `/ark-update`, engine sees no `.ark/` → treats as `installed_version=0.0.0` → re-applies every Phase 1 destructive migration → corruption in files that were already migrated.

**Preventable?**

**Mitigations in this plan:**
1. `ensure_gitignore_entry` op is ONLY for ADDING entries. The op deliberately has no "remove entry" counterpart in v1.0. So the plugin cannot accidentally add `.ark/` to `.gitignore`.
2. `check_target_profile_valid.py` CI validator asserts no `ensured_gitignore` entry matches `.ark` (exact or glob).
3. `migrate.py` startup bootstrap check: if `.ark/` directory missing AND `.gitignore` contains any pattern matching `.ark` or `.ark/`, REFUSE to run with message: "`.ark/` is gitignored but must be committed. Remove the pattern from `.gitignore` and commit before running /ark-update." 
4. `/ark-onboard` Repair section cross-reference (Stream B's edit) mentions this failure mode.
5. Stream A coordination: add a Check 22+ item in `/ark-health` that asserts `.ark/` is not gitignored.

---

## Deliberate Mode — Expanded Test Plan

### Tier 1 — Unit (per op, per helper)

| Test file | Coverage | Count |
|---|---|---|
| `tests/test_markers.py` | region extract/insert/replace; nested-marker refusal; mismatched-id refusal; multiple regions per file; regex edge cases | ~10 cases |
| `tests/test_state.py` | log append; log parse; log corruption → refuse; pointer rewrite; bootstrap when `.ark/` missing; advisory lockfile acquire/release; stale PID cleanup | ~10 cases |
| `tests/test_plan.py` | dry-run plan builder emits `would_apply` / `would_skip_idempotent` / `would_overwrite_drift` / `would_fail_precondition`; determinism (run twice → byte-identical) | ~5 cases |
| `tests/test_op_ensure_claude_md_section.py` | apply; idempotency; dry-run matches apply; detect-drift inside markers; no-touch outside markers; missing file creation; mismatched-id refusal | ~8 cases |
| `tests/test_op_ensure_gitignore_entry.py` | append when absent; no-op when present; `.gitignore` creation; trailing-newline normalization; **`test_dry_run_matches_apply` (zero-write dry_run returning same plan as apply)**; **path-traversal refusal** | ~7 cases |
| `tests/test_op_ensure_mcp_server.py` | merge into existing `.mcp.json`; create when missing; replace same-key entry; preserve other user servers; malformed `.mcp.json` → refusal; **`test_dry_run_matches_apply`**; **path-traversal refusal**; **malicious-JSON clobber refusal** (refuse entries that would overwrite pre-existing non-ark keys) | ~9 cases |
| `tests/test_op_create_file_from_template.py` | create when absent; no-op when present (never overwrite); template-not-found error; target-dir creation; **`test_dry_run_matches_apply`**; **path-traversal refusal** (absolute, `..`, symlink escape); **refuse symlink as target** | ~7 cases |
| `tests/test_op_ensure_routing_rules_block.py` | inherits `ensure_claude_md_section` contract; `id=routing-rules` correctly set; template path resolved; **`test_dry_run_matches_apply`** | ~4 cases |

### Tier 2 — Integration (engine-level, against fixtures)

| Test file | Coverage |
|---|---|
| `tests/test_convergence.py` | For each fixture: pre-state → run engine → compare to `expected-post/` sidecar snapshot (byte-exact). Fixtures: pre-v1.11, pre-v1.12, pre-v1.13, fresh, healthy-current, drift-inside-markers, drift-outside-markers. |
| `tests/test_idempotency.py` | Run engine twice on every fixture; second run must be **fully zero-write** — no `.ark/backups/` additions, no file mtime changes, NO log append, NO `.ark/plugin-version` rewrite. (Clean runs are no-ops per spec acceptance criteria — log append only occurs when `ops_ran > 0` or `result != "clean"`.) |
| `tests/test_dry_run.py` | `--dry-run` writes nothing to filesystem (snapshot entire fixture dir before/after → byte-equal). Deterministic: two `--dry-run` invocations produce byte-identical stdout. |
| `tests/test_destructive_replay.py` | (Scaffold for v1.0.) Given synthetic `migrations/v1.14.2.yaml` fixture + `migrations-applied.jsonl` at `v1.13.0`, engine computes pending=[v1.14.2], applies, appends log entry with `phase: destructive`. |
| `tests/test_refusal_modes.py` | Dirty tree → refuse w/o `--force`. Malformed CLAUDE.md → refuse, point to `/ark-onboard repair`. Malformed `.mcp.json` → refuse. Malformed `migrations-applied.jsonl` → refuse. Mismatched marker ID → refuse. `.ark/` in `.gitignore` → refuse (pre-mortem scenario 3 mitigation). |

### Tier 3 — End-to-end (real shell invocation)

| Test file | Coverage |
|---|---|
| `tests/test_e2e_shell.py` | Shell-out to `python3 scripts/migrate.py --project-root <fixture-copy> --dry-run`; parse stdout; assert status. Verifies CLI entry point, exit codes, stderr formatting. Uses `subprocess.run` with env override for `ARK_SKILLS_ROOT`. |
| `tests/test_e2e_skill_wrapper.py` | (Manual stage-5 self-test, not automated in CI.) Copy `pre-v1.11` fixture to tmpdir, invoke `/ark-update` via Claude Code harness, inspect result. Documented in `tests/MANUAL_STAGE5.md`. |

### Tier 4 — Observability (instrumentation tests)

| Test file | Coverage |
|---|---|
| `tests/test_logging.py` | Every engine run emits a structured log line to stderr with run-id, phase, ops_ran, duration_ms. Format stable across runs (regex-matchable). |
| `tests/test_run_summary.py` | Post-run summary rendered by SKILL.md wrapper includes: versions-applied, ops-ran-per-phase, drift-events, failures, backup-paths, suggested-commit-message. Test inspects the stdout JSON blob that SKILL.md pipes into its LLM message. |
| `tests/test_backup_provenance.py` | Every backup file in `.ark/backups/` has a sibling metadata file `<name>.meta.json` with `{op, region_id, run_id, pre_hash, reason}`. Allows future `/ark-restore` skill (v1.2+) to reverse operations cleanly. |

### CI integration

`scripts/check_target_profile_valid.py` runs in CI alongside existing `check_chain_integrity.py` and `check_path_b_coverage.py`. Blocks merge on schema violation, unknown `since:` version, unresolved template reference, or `ensured_gitignore` containing `.ark`-matching pattern.

---

## Build Sequence

**Convention:** Each step is atomic, committable, and testable. Steps with matching `parallel_group` can be fanned out to parallel subagents. Dependencies enforce ordering across groups.

### Step 0 — Pre-flight and skill skeleton

- **Goal:** Create `skills/ark-update/` directory with placeholder `SKILL.md` + empty subdirs so subsequent steps have a target tree.
- **Files created:**
  - `skills/ark-update/SKILL.md` (stub with frontmatter + context-discovery-exemption block copied verbatim from `skills/ark-onboard/SKILL.md:10-14` pattern, adapted)
  - `skills/ark-update/target-profile.yaml` (empty, `schema_version: 1`, empty arrays)
  - `skills/ark-update/migrations/.gitkeep`
  - `skills/ark-update/templates/.gitkeep`
  - `skills/ark-update/scripts/.gitkeep`
  - `skills/ark-update/scripts/ops/.gitkeep`
  - `skills/ark-update/tests/fixtures/.gitkeep`
- **Acceptance:** `ls skills/ark-update/` matches spec's "Engine architecture" tree. SKILL.md frontmatter parses. Context-discovery-exemption block is byte-equal (minus skill name) to the `/ark-onboard` version.
- **Dependencies:** none.
- **Parallel group:** (sequential — root of DAG)
- **Estimated LOC:** ~40 (mostly SKILL.md stub)

### Step 1 — Shared infra: `state.py` + `markers.py`

- **Goal:** Implement the two modules that every op depends on.
- **Files created:**
  - `skills/ark-update/scripts/state.py` — log append/parse, pointer r/w, `.ark/` bootstrap, advisory lockfile, backup-path computation
  - `skills/ark-update/scripts/markers.py` — region regex (per spec canonical syntax), extract/replace, nested-refusal, mismatched-id-refusal
  - `skills/ark-update/tests/test_state.py`
  - `skills/ark-update/tests/test_markers.py`
- **Acceptance:** Unit tests pass. Marker regex matches spec's canonical syntax line-for-line. Log format matches spec: `{version, applied_at, ops_ran, ops_skipped, failed_ops: list[{op_id, op_type, error}], result, phase}` — now authoritative per spec amendment. **Clean-run invariant: when `ops_ran == 0` AND `result == "clean"`, `state.py` MUST NOT append to `migrations-applied.jsonl` AND MUST NOT rewrite `.ark/plugin-version`. `test_state.py` asserts this explicitly.** `installed_version` computation: max successful semver across Phase-1 log entries, deduped by `(semver, phase)` — **never** derived from `applied_at` ordering (pre-mortem Scenario 2b: parallel-worktree merge safety under clock skew). `markers.py` module docstring documents `version=` attribute semantics: **emit-on-write, parse-on-read, drift-signal-in-v1.0** — "On write, engine emits the region's current `version:` attribute from `target-profile.yaml`. On read, engine parses `version=` from the begin-marker and populates `ManagedRegion.version: str`. **`TargetProfileOp.detect_drift()` treats `parsed_version != target_profile.version` as drift (triggers rewrite+backup), even if content is otherwise byte-identical** — this keeps markers honest about which managed-region version they carry." `ManagedRegion` dataclass in `markers.py` carries `version: str` field, populated on parse, serialized on write. **NEW helper module `skills/ark-update/scripts/paths.py` — `safe_resolve(project_root: Path, candidate: str | Path) -> Path` — enforces: relative-only, resolves under `project_root` (rejects `..` escape + absolute paths + symlinks whose resolved target escapes the root). All ops, all backup-path construction, and `check_target_profile_valid.py` use this helper. `test_paths.py` asserts traversal refusal cases.**
- **Dependencies:** Step 0.
- **Parallel group:** 1A (sequential — these modules block fan-out).
- **Estimated LOC:** ~300 impl + ~200 test.

### Step 2 — Engine skeleton: `migrate.py` + `plan.py` + two op base classes

- **Goal:** CLI entry point + dry-run plan builder + abstract base classes for both op families. Orchestrates Phase 1 → Phase 2 but ops catalog is empty at this stage (loads registry from `ops/__init__.py`).
- **Files created:**
  - `skills/ark-update/scripts/migrate.py` — argparse CLI, `--project-root`, `--dry-run`, `--force`, `--skills-root`, orchestrates state load → pending compute → Phase 1 replay → Phase 2 convergence → log append → exit code
  - `skills/ark-update/scripts/plan.py` — plan report builder, per-op `would_*` status, deterministic JSON output
  - `skills/ark-update/scripts/ops/__init__.py` — op registry + **two abstract base classes**:
    - **`TargetProfileOp`** (abstract) — carries the `apply()` / `dry_run()` / `detect_drift()` contract. All 5 v1.0 ops subclass this. `detect_drift` return type is the typed dict `{has_drift: bool, drift_summary: str | None, drifted_regions: list[str]}` (not ad-hoc stdout JSON — load-bearing for pre-mortem mitigation 1.4).
    - **`DestructiveOp`** (abstract, zero subclasses in v1.0) — separate base class with module docstring: "Reserved for destructive primitives (`rename_frontmatter_field`, `deprecate_file`, `remove_managed_region`). Do NOT subclass `TargetProfileOp` for destructive ops — their `detect_drift` semantics are incompatible. `TargetProfileOp.detect_drift` detects 'content differs from target template' (idempotency check). `DestructiveOp.detect_drift` (when implemented) will detect 'already-applied state' (version-gate). These are fundamentally different questions."
  - `skills/ark-update/tests/test_plan.py`
- **Acceptance:**
  1. `python3 skills/ark-update/scripts/migrate.py --project-root /tmp/nonexistent --dry-run` exits cleanly with "no target profile entries, nothing to do" report.
  2. `test_plan.py` passes.
  3. Both `TargetProfileOp` and `DestructiveOp` abstract classes exist with documented contracts; `DestructiveOp` is empty (no concrete subclasses) but defined.
  4. **YAML parser / target-profile loader recognizes the optional `depends_on_op: <op-id>` field on destructive-migration ops and stores it for runtime skip-cascade logic** (IN-SCOPE v1.0 per spec amendment + pre-mortem Scenario 2 mitigation 2.2). Not exercised in v1.0 (zero destructive migrations ship) but parser + field storage is wired.
  5. `TargetProfileOp.detect_drift` abstract signature returns the typed dict shape above.
  6. **Path safety: every `managed_regions[].file`, `ensured_files[].target`, `ensured_gitignore[].file`, `ensured_mcp_servers[].file` field is passed through `paths.safe_resolve(project_root, ...)` at parse time. Absolute paths, `..` escapes, and symlink-resolved escapes raise `PathTraversalError` → refusal with user-facing message pointing to `/ark-onboard repair`. Enforced at load time (parser) AND before every write (engine) — defense in depth.**
- **Dependencies:** Step 1.
- **Parallel group:** 1B (sequential — blocks Step 3 fan-out).
- **Estimated LOC:** ~250 impl + ~120 test.

### Step 3 — Implement 5 ops (PARALLEL FAN-OUT)

- **Goal:** Implement each op module + its unit tests. These are independent and can be fanned out to 5 parallel subagents.
- **Sub-steps (all in parallel_group 2):**
  - **3a:** `scripts/ops/ensure_claude_md_section.py` + `tests/test_op_ensure_claude_md_section.py`
  - **3b:** `scripts/ops/ensure_gitignore_entry.py` + `tests/test_op_ensure_gitignore_entry.py`
  - **3c:** `scripts/ops/ensure_mcp_server.py` + `tests/test_op_ensure_mcp_server.py`
  - **3d:** `scripts/ops/create_file_from_template.py` + `tests/test_op_create_file_from_template.py`
  - **3e:** `scripts/ops/ensure_routing_rules_block.py` (subclass) + `tests/test_op_ensure_routing_rules_block.py`
- **Acceptance:**
  1. Each op subclasses **`TargetProfileOp`** (not `DestructiveOp`) and exports `apply`, `dry_run`, `detect_drift` per the contract defined in `ops/__init__.py`.
  2. **`detect_drift()` returns the typed dict `{has_drift: bool, drift_summary: str | None, drifted_regions: list[str]}` — NOT a bare boolean, NOT ad-hoc stdout JSON.** This shape is load-bearing for pre-mortem Scenario 1 mitigation 1.4 (drift summary propagates into run summary and SKILL.md user-facing warning).
  3. **Each `test_op_*.py` file asserts the return-shape of `detect_drift` explicitly** — cases must check that `drift_summary` is a string when `has_drift=True` and is `None` when `has_drift=False`, and `drifted_regions` is a list (possibly empty).
  4. Per-op unit tests pass. Op registry in `__init__.py` can discover all 5.
- **Dependencies:** Step 2.
- **Parallel group:** 2 (5 subagents, one per op).
- **Estimated LOC:** ~150 impl + ~150 test × 5 = ~1500 total.

### Step 4 — Target profile backfill + templates

- **Goal:** Populate `target-profile.yaml` with managed-region entries for every v1.11/v1.12/v1.13 convention. Author template files.
- **Files created/modified:**
  - `skills/ark-update/target-profile.yaml` (now populated per spec illustrative schema)
  - `skills/ark-update/templates/omc-routing-block.md` (the canonical OMC routing block content; source: existing content from `skills/ark-workflow/references/omc-integration.md` section or extracted from README)
  - `skills/ark-update/templates/routing-template.md` (byte-copy of `skills/ark-workflow/references/routing-template.md` at the time of Step 4; CI validator in Step 5 hardens this check going forward)
  - `skills/ark-update/templates/setup-vault-symlink.sh` (if v1.11 centralized-vault convention requires it — confirm during step)
  - `skills/ark-update/templates/README.md` (~1 page) documenting: "Markers emit `version=X.Y.Z` where X.Y.Z comes from `target-profile.yaml:managed_regions[].version`. Bump the version field in the YAML when the template content changes structurally. v1.0 does not branch on this value; future enhancements may."
  - Additional templates as Step 4 research identifies from v1.11/v1.12/v1.13 changelogs
- **Acceptance:**
  1. `target-profile.yaml` lists a managed-region entry for every convention introduced in v1.11, v1.12, v1.13 (confirmed against `CHANGELOG.md`). Each entry's `since:` matches the CHANGELOG. Each `template:` reference resolves to a real file under `templates/`.
  2. **Byte-equality gate for `routing-template.md` runs as part of this step's acceptance (not deferred to Step 5):** `diff skills/ark-update/templates/routing-template.md skills/ark-workflow/references/routing-template.md` returns zero exit code. This gate runs before the step is marked complete. Step 5's CI validator hardens this check into `check_target_profile_valid.py` but Step 4 cannot land with drift already present.
  3. `templates/README.md` documents the `version=` semantics per the markers contract.
- **Dependencies:** Step 3 (needs op types defined to reference them by name in YAML).
- **Parallel group:** 3 (sequential after Step 3; can parallelize template file authoring within this step via 2–3 subagents).
- **Estimated LOC:** ~80 YAML + ~200 template content.

### Step 5 — CI validator

- **Goal:** Implement `check_target_profile_valid.py` mirroring `check_chain_integrity.py` style.
- **Files created:**
  - `skills/ark-update/scripts/check_target_profile_valid.py`
  - Test or self-test within the script (per `check_chain_integrity.py` pattern)
  - Register in CI config if applicable (repo's existing CI is likely GitHub Actions — Architect should confirm path)
- **Acceptance:** Script validates:
  1. `target-profile.yaml` conforms to schema (schema_version, required fields per entry-type, op-type-name matches registered op)
  2. Every `since:` value appears in repo's `CHANGELOG.md`
  3. Every `template:` reference resolves to a file under `templates/`
  4. `ensured_gitignore[]` contains no pattern matching `.ark` (pre-mortem scenario 3)
  5. `templates/routing-template.md` is byte-equal to `skills/ark-workflow/references/routing-template.md` (drift guard — Step 4 gates initial state, this step enforces forward)
  6. **Schema validator accepts `failed_ops: list[{op_id, op_type, error}]` in `migrations-applied.jsonl` log entries** (IN-SCOPE v1.0; populated on partial runs).
  7. **Schema validator accepts optional `depends_on_op: <op-id>` field on destructive-migration op entries in `migrations/*.yaml`** (IN-SCOPE v1.0; not exercised until first destructive migration ships).
- **Dependencies:** Step 4.
- **Parallel group:** 4.
- **Estimated LOC:** ~150.

### Step 6 — Historical fixtures + convergence tests (Stage-5 self-test material)

- **Goal:** Author manual fixtures for pre-v1.11, pre-v1.12, pre-v1.13, fresh, healthy-current, drift-inside-markers, drift-outside-markers. Author expected-post sidecars. Wire `test_convergence.py`, `test_idempotency.py`, `test_dry_run.py`, `test_refusal_modes.py`.
- **Files created:**
  - 7 fixture directories under `skills/ark-update/tests/fixtures/` with realistic mini-project content (CLAUDE.md, `.gitignore`, `.mcp.json` as applicable per the historical state)
  - 7 matching `expected-post/` sidecar directories
  - `skills/ark-update/tests/test_convergence.py`
  - `skills/ark-update/tests/test_idempotency.py`
  - `skills/ark-update/tests/test_dry_run.py`
  - `skills/ark-update/tests/test_refusal_modes.py`
  - `skills/ark-update/tests/test_destructive_replay.py` (with synthetic v1.14.2 YAML)
  - `skills/ark-update/tests/test_e2e_shell.py`
  - `skills/ark-update/tests/test_logging.py`, `test_run_summary.py`, `test_backup_provenance.py`
  - `skills/ark-update/tests/MANUAL_STAGE5.md` (runbook for the manual Stage-5 self-test)
- **Acceptance:**
  1. All 7 fixtures run through engine and produce `expected-post/` byte-exact.
  2. Idempotency: second run on any fixture produces zero file changes (except log append with `ops_ran: 0`).
  3. Dry-run on any fixture writes nothing and is deterministic.
  4. Drift-outside-markers fixture: byte-equality check across entire fixture minus `.ark/` before/after → passes.
  5. Drift-inside-markers fixture: backup written, run summary lists drift event, file content overwritten, **backup bytes byte-equal to pre-overwrite file content** (pre-mortem mitigation 1.1 — assert `read_bytes(backup) == pre_overwrite_bytes`, not just file existence). **Also: stale-`version=` drift fixture — region content matches template but marker `version=` is below target; engine MUST rewrite+backup even though content is identical, restoring marker-version honesty (P2-3 fix).**
  6. All refusal-mode tests pass.
  7. **`MANUAL_STAGE5.md` includes a "Fixture authenticity check" substep BEFORE the convergence runbook:**
     > **Fixture authenticity check.** For each of `pre-v1.11/`, `pre-v1.12/`, `pre-v1.13/`, run:
     > ```
     > diff <fixture-path>/CLAUDE.md <(git show v1.10.1:CLAUDE.md)   # for pre-v1.11
     > diff <fixture-path>/CLAUDE.md <(git show v1.11.0:CLAUDE.md)   # for pre-v1.12
     > diff <fixture-path>/CLAUDE.md <(git show v1.12.0:CLAUDE.md)   # for pre-v1.13
     > ```
     > and visually inspect. Not byte-equality (fixtures may be minimalized) but structural realism — "does the fixture represent a believable pre-v(N) project shape?" Reviewer signs off that differences are intentional (e.g., trimmed to minimum relevant content) before Stage-5 proceeds.
     Cost: ~10 minutes. Benefit: eliminates "fixtures test engine against author's memory of past state, not actual past state" failure mode.
- **Dependencies:** Step 5 (validator must pass first so target-profile is known correct).
- **Parallel group:** 5 (fixture authoring can fan out to 3 subagents — one per pre-vN historical fixture; other fixtures are smaller and can be done sequentially in the controller).
- **Estimated LOC:** ~400 fixture content + ~500 test code.

### Step 7 — SKILL.md full wrapper

- **Goal:** Flesh out `skills/ark-update/SKILL.md` from Step-0 stub into full LLM-facing wrapper.
- **Files modified:**
  - `skills/ark-update/SKILL.md`
- **Must include:**
  - Context-discovery exemption block (copied from Step 0; verify byte-pattern against `/ark-onboard` precedent)
  - `ARK_SKILLS_ROOT` resolution block (copied verbatim from `skills/ark-context-warmup/SKILL.md:31-49`)
  - Usage: `/ark-update`, `/ark-update --dry-run`, `/ark-update --force`
  - Workflow: pre-flight git check → call `migrate.py` → render summary → suggest commit message
  - Pre-run warning about inside-marker overwrite with backup (pre-mortem mitigation 1.3)
  - Post-run summary rendering spec (drift events section, failures section, suggested commit message)
  - Refusal-mode handoffs (point to `/ark-onboard repair` for malformed files)
- **Acceptance:** Skill runs end-to-end on the healthy-current fixture via Claude Code harness (stage-5 self-test, manually). SKILL.md frontmatter parses. Exemption block matches pattern.
- **Dependencies:** Step 6 (need engine working to wire wrapper).
- **Parallel group:** 6.
- **Estimated LOC:** ~200 markdown.

### Step 8 — Cross-references in `/ark-onboard` and `/ark-health` (STREAM-A COORDINATION TOUCHPOINT)

- **Goal:** Add version-drift cross-references to sibling skills. This is Stream B's ONLY edit to Stream A's files. **Edit anchors are specified precisely to minimize merge-conflict risk with Stream A.**
- **Files modified:**
  - **`skills/ark-onboard/SKILL.md`** — cross-reference paragraph location:
    - Insertion point: at the end of `## Path: Partial Ark (Repair)` section (starts at line 2253), immediately before the next `## ` or `# ` heading. The `### Centralized-Vault Repair` subsection at line 2257 is INCLUDED within the Repair section; insertion goes AFTER the entire Repair section's final subsection.
    - Wrap the added paragraph with HTML-comment anchors for grep-based merge-conflict detection:
      ```
      <!-- stream-b: /ark-update cross-reference begin -->
      For version drift (plugin updated but project conventions out of date), run `/ark-update` — it replays additive conventions from the current target profile. /ark-update also refuses to run on malformed CLAUDE.md / `.mcp.json` / `.ark/migrations-applied.jsonl` and points back here; this coexistence is intentional. Note: if `.ark/` is gitignored in your project, remove the pattern and commit before running /ark-update.
      <!-- stream-b: /ark-update cross-reference end -->
      ```
    - Verification command: `grep -c "stream-b: /ark-update cross-reference" skills/ark-onboard/SKILL.md` returns `2`.
  - **`skills/ark-health/SKILL.md`** — new check section (NOT a row appended to Integrations):
    - **Create a new `### Plugin Versioning (Checks 22+)` section** at the end of the diagnostic checklist. Rationale: preserves `### Integrations (Checks 12–20)` section integrity and gives plugin-versioning concerns their own logical home (Critic-directed).
    - Check content: "ark-skills version current?" comparing `.ark/plugin-version` vs `$ARK_SKILLS_ROOT/VERSION`, warn-only, surfacing "upgrade available: run /ark-update". Also asserts `.ark/` not gitignored (pre-mortem Scenario 3 mitigation 3.5).
    - **Check-count phrasing update (repo-wide grep, NOT line-specific):** `skills/ark-health/SKILL.md` contains hardcoded check counts at `:8`, `:16`, `:18`, `:99`, `:529`, `:559`, `:595`, `:619`, `:621` (grepped during plan drafting — Stream B implementer MUST re-grep at edit time). ALL `"N diagnostic checks"`, `"N checks"`, `"Check N"`, and `"checks 7–N"` phrasings in both `skills/ark-health/SKILL.md` AND `skills/ark-onboard/SKILL.md` must be updated to match the final post-merge check count (Stream A's Check 21 + Stream B's Check 22, = 22 checks).
    - **Scorecard output section update**: `skills/ark-onboard/SKILL.md:2581` scorecard output text must also update its check count to match.
- **Acceptance:**
  1. `grep -c "stream-b: /ark-update cross-reference" skills/ark-onboard/SKILL.md` returns `2`.
  2. `git diff skills/ark-onboard/SKILL.md` shows only the Repair-section bookended addition, the scorecard count bump at line 2581, and any other check-count phrasing updates — no unrelated edits.
  3. `git diff skills/ark-health/SKILL.md` shows one new `### Plugin Versioning (Checks 22+)` section + all check-count phrasing updates surfaced by the repo-wide grep below.
  4. **Repo-wide grep returns 0 stale references:** `grep -nE '\b(19|20|21) (diagnostic )?checks?\b|\bCheck (19|20|21)\b|checks 7[–-](19|20|21)\b' skills/ark-health/SKILL.md skills/ark-onboard/SKILL.md` returns no matches (all legacy counts updated). `grep -nE '\b22 (diagnostic )?checks?\b|\bCheck 22\b|checks 7[–-]22\b' skills/ark-health/SKILL.md skills/ark-onboard/SKILL.md` returns the expected consistent set across both files.
- **Dependencies:** Step 7.
- **Parallel group:** 7 (sequential; must land last for merge safety).
- **Estimated LOC:** ~30 across both files.

### Step 9 — README update

- **Goal:** Add `/ark-update` to the skill table in `README.md`.
- **Files modified:** `README.md`
- **Acceptance:** New row under "Workflow Orchestration" or "Onboarding" (Architect to pick) reading: "`/ark-update` — Generalized version-migration framework. Replays destructive migrations + converges project to target profile."
- **Dependencies:** Step 8.
- **Parallel group:** 8.
- **Estimated LOC:** ~1 markdown table row.

### Step 10 — Stage-5 self-test gate (SHIP GATE, NOT OPTIONAL)

- **Goal:** Run historical fixtures through the shipped framework. This is a gate — spec explicitly forbids skipping.
- **Actions:**
  1. Run `python3 skills/ark-update/tests/` (all test tiers) — must pass 100%.
  2. Execute manual stage-5 runbook (`tests/MANUAL_STAGE5.md`): copy each of pre-v1.11 / pre-v1.12 / pre-v1.13 fixtures to `/tmp/`, invoke `/ark-update` via the Claude Code harness end-to-end, inspect post-state matches expected-post.
  3. Verify: no `.ark/backups/*` written on healthy-current fixture (idempotency proof in the wild).
  4. Capture evidence in session log (for `/wiki-update` stage later).
- **Acceptance:** All automated tests pass. Manual stage-5 runbook completes with three pre-vN fixtures successfully converged. Evidence captured.
- **Dependencies:** Step 9.
- **Parallel group:** 9 (sequential — gate).

### Step 11 — `/codex review` + `/ark-code-review` (separate-lane review passes)

- **Goal:** External review passes per user's saved workflow preferences.
- **Actions:**
  1. `/codex review` on the shipped framework (separate from the ralplan `/codex review` at the plan stage).
  2. `/ark-code-review` post-implementation.
- **Acceptance:** Both review passes complete. Any findings triaged into either in-scope fixes (loop back to Step 3–7 as needed) or v1.1 follow-ups (added to ADR).
- **Dependencies:** Step 10.
- **Parallel group:** 10.

---

## File Inventory

### Stream B creates (new)

| Path | Purpose | Acceptance criterion traceability |
|---|---|---|
| `skills/ark-update/SKILL.md` | LLM wrapper | "Framework (skill installation)" row 1 |
| `skills/ark-update/target-profile.yaml` | Declarative target profile | Row 2 |
| `skills/ark-update/migrations/.gitkeep` | Empty in v1.0 | Row 6 |
| `skills/ark-update/templates/omc-routing-block.md` | OMC block template | Row 5 |
| `skills/ark-update/templates/routing-template.md` | Routing rules template | Row 5, "Engine correctness Phase 2" `ensure_routing_rules_block` |
| `skills/ark-update/templates/setup-vault-symlink.sh` | Centralized-vault template (if applicable) | Row 5 |
| `skills/ark-update/scripts/migrate.py` | Engine CLI entry | Row 3 |
| `skills/ark-update/scripts/state.py` | Log + pointer + bootstrap + lockfile | "State management" rows |
| `skills/ark-update/scripts/markers.py` | Region I/O | "Drift detection" rows |
| `skills/ark-update/scripts/plan.py` | Dry-run plan builder | "Dry-run semantics" rows |
| `skills/ark-update/scripts/ops/__init__.py` | Op registry + `TargetProfileOp` + `DestructiveOp` base classes | Row 4 |
| `skills/ark-update/scripts/ops/ensure_claude_md_section.py` | Op 1 | Row 4 |
| `skills/ark-update/scripts/ops/ensure_gitignore_entry.py` | Op 2 | Row 4 |
| `skills/ark-update/scripts/ops/ensure_mcp_server.py` | Op 3 | Row 4 |
| `skills/ark-update/scripts/ops/create_file_from_template.py` | Op 4 | Row 4 |
| `skills/ark-update/scripts/ops/ensure_routing_rules_block.py` | Op 5 (subclass) | Row 4 |
| `skills/ark-update/scripts/check_target_profile_valid.py` | CI validator | "Testing" last row |
| `skills/ark-update/tests/fixtures/pre-v1.11/**` | Historical fixture + `expected-post/` | "Testing" fixture rows |
| `skills/ark-update/tests/fixtures/pre-v1.12/**` | Historical fixture + `expected-post/` | " |
| `skills/ark-update/tests/fixtures/pre-v1.13/**` | Historical fixture + `expected-post/` | " |
| `skills/ark-update/tests/fixtures/fresh/**` | Bootstrap fixture | " |
| `skills/ark-update/tests/fixtures/healthy-current/**` | Idempotency fixture | " |
| `skills/ark-update/tests/fixtures/drift-inside-markers/**` | Drift fixture | "Drift detection" rows |
| `skills/ark-update/tests/fixtures/drift-outside-markers/**` | Zero-touch fixture | "Drift detection" row 5 |
| `skills/ark-update/tests/test_markers.py` | Unit | Tier 1 |
| `skills/ark-update/tests/test_state.py` | Unit | Tier 1 |
| `skills/ark-update/tests/test_plan.py` | Unit | Tier 1 |
| `skills/ark-update/tests/test_op_*.py` (5 files) | Per-op unit | "Testing" per-op row |
| `skills/ark-update/tests/test_convergence.py` | Integration | "Testing" row |
| `skills/ark-update/tests/test_idempotency.py` | Integration | " |
| `skills/ark-update/tests/test_dry_run.py` | Integration | " |
| `skills/ark-update/tests/test_refusal_modes.py` | Integration | "Boundary with /ark-onboard and /ark-health" refusal rows |
| `skills/ark-update/tests/test_destructive_replay.py` | Integration scaffold | "Engine correctness Phase 1" rows |
| `skills/ark-update/tests/test_e2e_shell.py` | E2E | Tier 3 |
| `skills/ark-update/tests/test_logging.py` | Observability | Tier 4 |
| `skills/ark-update/tests/test_run_summary.py` | Observability | Tier 4 |
| `skills/ark-update/tests/test_backup_provenance.py` | Observability | Tier 4 |
| `skills/ark-update/tests/MANUAL_STAGE5.md` | Manual runbook | Spec's "Stage 5 self-test" |

### Stream B modifies (existing)

| Path | Edit scope | Stream A overlap risk |
|---|---|---|
| `skills/ark-onboard/SKILL.md` | Repair section ONLY — add `/ark-update` cross-reference paragraph | LOW (Stream A edits Healthy Step 3 + Greenfield Step 18; different sections) |
| `skills/ark-health/SKILL.md` | Add ONE new check row at check-22+ boundary + bump "21 checks" header count at `:8`, `:18`, and `skills/ark-onboard/SKILL.md:2581` (scorecard) | MEDIUM (Stream A ships Check 21 first; Stream B's check numbering depends on landing order) |
| `README.md` | Add one skill-table row | LOW (Stream A may or may not touch README; coordinate at merge) |

### Stream B does NOT modify (explicitly)

- `VERSION`
- `CHANGELOG.md`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

These are the combined v1.14.0 release-PR owner's responsibility (whichever stream lands last).

---

## Parallelization Opportunities

```
Step 0 (sequential)
   |
Step 1 — state.py + markers.py (sequential; blocks fan-out)
   |
Step 2 — migrate.py + plan.py skeleton (sequential; blocks fan-out)
   |
Step 3 — 5 ops [PARALLEL: 5 subagents]
   ├── 3a: ensure_claude_md_section
   ├── 3b: ensure_gitignore_entry
   ├── 3c: ensure_mcp_server
   ├── 3d: create_file_from_template
   └── 3e: ensure_routing_rules_block
   |
Step 4 — target profile + templates [PARALLEL: 2–3 subagents for template authoring]
   |
Step 5 — CI validator (sequential)
   |
Step 6 — fixtures + integration tests [PARALLEL: 3 subagents for historical fixtures pre-v1.11/12/13]
   |
Step 7 — SKILL.md full wrapper (sequential)
   |
Step 8 — cross-references to /ark-onboard + /ark-health (STREAM-A COORDINATION; sequential; MUST LAND LAST)
   |
Step 9 — README (sequential)
   |
Step 10 — Stage-5 self-test GATE (sequential; blocks ship)
   |
Step 11 — /codex + /ark-code-review (separate lanes, but both required before ship)
```

**Max parallelism per step:** Step 3 (5 subagents) and Step 6 (3 subagents) are the fan-out wins. Step 4 can fan out by 2–3 for template authoring. Rest is sequential because the DAG demands it or LOC is too small to benefit.

**Expected wall-clock:** Sequential critical path is Steps 0 → 1 → 2 → 4 → 5 → 7 → 8 → 9 → 10 → 11. Steps 3 and 6 compress from 5× and 3× serial effort respectively. Rough estimate: ~40% wall-clock savings from fan-out vs fully serial.

---

## Commit Convention

One commit per build step, conventional prefix `feat(ark-update): Step N — <step goal>`.

**Exceptions for fan-out steps:**
- **Step 3** (5-subagent op fan-out) produces **5 commits** — one per op (e.g., `feat(ark-update): Step 3.1 — ensure_claude_md_section op`, `feat(ark-update): Step 3.2 — ensure_gitignore_entry op`, etc.). This granularity allows `git bisect` during Stage-5 self-test to pinpoint a broken op.
- **Step 6** (3-subagent historical-fixture fan-out) produces **3 commits** — one per pre-vN fixture (e.g., `feat(ark-update): Step 6.1 — pre-v1.11 fixture + convergence assertions`).
- All other steps: **1 commit each.**

**Total commit count:** 11 steps + 4 fan-out sub-commits (4 extras for Step 3, 2 extras for Step 6) = **~17 commits** on Stream B's branch.

**Do NOT bump `VERSION` / `CHANGELOG.md` / `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json` in ANY commit.** The combined v1.14.0 release PR is owned by whichever stream (A or B) lands last, and that stream bumps all four in a single release-prep commit on the combined branch.

---

## Stream-A Coordination Touchpoints

| File | Stream A edit | Stream B edit | Conflict risk | Mitigation |
|---|---|---|---|---|
| `skills/ark-onboard/SKILL.md` | Healthy Step 3 upgrade entry + Greenfield Step 18 | Repair section cross-reference to `/ark-update` | LOW (different sections) | Stream B edits this file LAST in its chain (Step 8). At merge, grep-diff to confirm no section-overlap. If overlap detected, hand-merge using both stream's handoff specs as source of truth. |
| `skills/ark-health/SKILL.md` | New Check 21 (OMC plugin detection) | New Check 22+ (version drift) | MEDIUM (both adding check rows; row numbering depends on landing order) | Stream B's Step 8 reads the current state of `/ark-health` AT EDIT TIME and picks the next available check number. If Stream A hasn't landed yet, Stream B uses Check 21 provisionally and flags this in the commit message. At combined-PR time, whichever lands second renumbers if needed. |
| `README.md` | Possibly (per Stream A plan) | Add `/ark-update` row | LOW | Both add rows; ordering is alphabetical or category-grouped. Merge is trivial. |
| `VERSION`, `CHANGELOG.md`, `.claude-plugin/*` | Combined PR only | Combined PR only | N/A | Release PR owner handles. |

**Merge strategy:** Both streams keep their own branches off `master`. At ship time:
1. Land whichever finishes Stage 5 self-test first.
2. Rebase the second stream onto the first's landing commit.
3. Resolve the predictable Step-8 conflicts (`skills/ark-onboard/SKILL.md` Repair cross-reference row + `skills/ark-health/SKILL.md` check numbering).
4. Run combined Stage-5 gate again on the rebased branch to catch integration surprises.
5. Open combined v1.14.0 PR bumping VERSION + CHANGELOG + plugin.json + marketplace.json.

---

## Stage-5 Self-Test Gate (EXPANDED)

Per spec handoff: "shipping an untested framework is shipping broken code." This stage is a HARD ship gate.

### What must pass

1. `pytest skills/ark-update/tests/` → 100% pass across all tiers (unit, integration, e2e, observability).
2. Manual runbook `tests/MANUAL_STAGE5.md` walked through on a real shell:
   - For each of `pre-v1.11`, `pre-v1.12`, `pre-v1.13`:
     - Copy fixture to `/tmp/stage5-<name>/`.
     - `cd /tmp/stage5-<name>`.
     - Invoke `/ark-update` via Claude Code harness (SKILL.md path, not direct `migrate.py` path).
     - Verify post-state matches `expected-post/` byte-exact.
     - Verify `.ark/migrations-applied.jsonl` has expected Phase-2 entries.
     - Verify `.ark/plugin-version` equals `$ARK_SKILLS_ROOT/VERSION`.
     - Verify no `.ark/backups/*` except for fixtures where drift was pre-seeded.
3. Evidence capture:
   - Attach pre/post dir trees to session log.
   - Attach engine stdout/stderr to session log.
   - Record any deviations from spec in an "Observed in self-test" section of the session log.

### What blocks the ship

- Any test failure.
- Any fixture post-state deviating from `expected-post/`.
- Any `.ark/backups/` write on a fixture that wasn't drift-seeded.
- Any refusal-mode behavior that doesn't match the spec's refusal classes.
- Any warning from `check_target_profile_valid.py`.

---

## ADR — Architecture Decision Record

### Decision

Build `/ark-update` as a declarative two-phase migration framework: Python engine (`migrate.py`) consuming `target-profile.yaml` + `migrations/vX.Y.Z.yaml`, invoked by a thin SKILL.md wrapper. HTML-comment markers (`<!-- ark:begin id=X version=Y -->`...`<!-- ark:end id=X -->`) scope what the engine owns. Inside markers: engine always overwrites with backup to `.ark/backups/`. Outside markers: engine never touches. State lives in committed `.ark/migrations-applied.jsonl` (authoritative append-only log) + `.ark/plugin-version` (cached pointer). v1.0 ships 5 target-profile ops + empty destructive-migrations directory.

### Drivers

1. **Testability.** A framework that can't be tested end-to-end against real historical fixtures isn't shippable. Declarative YAML + deterministic Python + snapshot fixtures is the cheapest path to testable.
2. **User trust.** Migration tools destroy data when wrong. Inside/outside marker discipline + always-overwrite-with-backup gives user a clear mental model AND a safety net.
3. **Op independence for parallel build.** 5 independent ops × per-op unit tests = clean parallelism during implementation AND clean separation of concerns at runtime.
4. **Low surface area for v1.0.** 5 ops beats 8. Destructive-3 deferred until a real destructive release needs them. YAGNI applied at the scope level, not the code level.
5. **Stream-A merge compatibility.** This plan sequences file-edit steps to minimize conflict with Stream A's edits to the same files. Step 8 (cross-references) is last in Stream B's chain, by design.

### Alternatives considered (at the plan level, not at the spec level — spec already resolved 8 architectural questions)

| Alternative | Why rejected |
|---|---|
| Registry-dict ops vs class hierarchy | Registry lacks static type guarantees. For migration tooling where bugs corrupt user files, trading ~30 LOC/op for compile-time contract enforcement is wrong optimization. |
| Monolithic `migrate.py` | Kills parallel subagent fan-out. Makes per-module testing impossible without mock-patching internals. |
| Regeneration-from-git fixture authoring | Spec non-goal. Adds complex tooling for marginal fixture accuracy. Manual fixtures for 3 historical states is ~1 day of work. |
| Independent `ensure_routing_rules_block` (not subclass) | Duplicates 90% of `ensure_claude_md_section` logic. Spec's tree specifies subclass. |
| Threaded `dry_run: bool` parameter | Any op that forgets to branch on the flag writes in a dry-run. Too error-prone for a migration tool. Separate `plan.py` code path is safer. |
| Copy-at-build vs runtime-load for `routing-template.md` | Runtime-load couples `/ark-update` to `/ark-workflow`'s directory structure. Copy-at-build + CI byte-equality check is explicit, discoverable, and decouples the two skills. |

### Why chosen

Hybrid target-profile + destructive-only per-version migrations is the simplest model that satisfies the observed pattern (~95% of historical releases were additive) while leaving a well-defined path for the rare destructive release. Declarative YAML + Python engine is the simplest model that satisfies determinism + testability + CI-validator integration. HTML markers are the simplest model that satisfies inside/outside discipline without hash state or three-way merge. Always-overwrite-with-backup is the simplest user-facing model (users only need to know "look inside the markers and backups/").

### Consequences

**Positive:**
- Engine is fully testable via fixtures.
- Most future releases ship ZERO new code in ark-update — they just add entries to `target-profile.yaml`.
- Framework is deterministic → CI-friendly → snapshot-testable.
- Inside/outside rule is the only invariant users need to remember.

**Negative (accepted trade-offs):**
- User edits inside markers get overwritten with backup (not merged, not prompted). Mitigated by prominent pre-run warning + drift-events in run summary (pre-mortem scenario 1).
- No per-op rollback. Commit-before-run + per-file backups are the only recovery mechanisms. Mitigated by commit-protocol guidance in SKILL.md.
- Partial destructive-migration failures can leave half-applied state. Mitigated by `failed_ops[]` in log entries + `depends_on_op` field in YAML (pre-mortem scenario 2).
- Manual fixture authoring can drift from real git history. Accepted for v1.0; regeneration deferred to v1.1.
- `routing-template.md` is copied between `/ark-workflow` and `/ark-update`. Mitigated by CI byte-equality assertion in `check_target_profile_valid.py`.
- Simultaneous `/ark-update` runs on parallel branches can produce merge conflicts on `.ark/migrations-applied.jsonl`. **Merge semantics: append-and-dedup by `(semver, phase)` — `installed_version` is the max successful semver across Phase-1 entries, NEVER the tail of the file and NEVER a timestamp sort. Clock skew / non-monotonic `applied_at` is tolerated because `applied_at` is advisory only.** Documented in SKILL.md troubleshooting section.
- **POSIX-only target (v1.0).** `/ark-update` targets macOS, Linux, and WSL2 bash environments. Native Windows cmd/powershell is NOT supported in v1.0 (`ARK_SKILLS_ROOT` resolver uses shell arithmetic; `MANUAL_STAGE5.md` fixture-authenticity step uses process substitution `<(git show ...)`). SKILL.md declares this explicitly; test documentation repeats the constraint. Windows-native support is a v1.1 follow-up if user demand exists.

### Follow-ups (not in v1.0; tracked for v1.1+)

1. **Destructive-op catalog expansion.** `rename_frontmatter_field`, `deprecate_file`, `remove_managed_region` — implement when first destructive release needs them.
2. **Regeneration-from-git fixture script.** Auto-generate pre-vN fixtures from repo history.
3. **`--resume-partial` flag.** Retry failed ops from a `partial` log entry without re-running clean ops.
4. **Interactive drift resolution.** Opt-in `--interactive` flag for users who want per-conflict Y/N prompting (spec explicitly defers).
5. **`/ark-restore` skill.** Reverse a run using `.ark/backups/*.meta.json` provenance sidecars (introduced by pre-mortem mitigation 1.4).
6. **Three-way merge for inside-markers drift.** Only if v1.0 tells us interactive + overwrite are insufficient in practice.

---

## Final Checklist (for Architect/Critic review)

- [x] Spec read in full before planning — ambiguity 0.057, READY_FOR_PLAN.
- [x] 11 build steps with concrete file paths, acceptance criteria, dependencies, parallel groups.
- [x] File inventory cross-references every "Acceptance Criteria" row in the spec.
- [x] Parallelization: Steps 3 (5x) and 6 (3x) fan out to subagents.
- [x] Stream-A coordination: Step 8 sequenced last; merge-strategy documented.
- [x] Pre-mortem: 3 scenarios, each with concrete mitigations wired into plan steps.
- [x] Expanded test plan: 4 tiers (unit/integration/e2e/observability) with per-file coverage.
- [x] Stage-5 self-test is a ship gate, not optional.
- [x] ADR at bottom: Decision / Drivers / Alternatives / Why chosen / Consequences / Follow-ups.
- [x] No VERSION / CHANGELOG / plugin.json / marketplace.json edits in Stream B commits.
- [x] No destructive ops planned for v1.0 (YAGNI per spec non-goals).
- [x] No interactive drift resolution in v1.0 (spec non-goal).
- [x] No `/ark-update` → `/ark-onboard repair` auto-chain (spec non-goal).
- [x] Spec-level concerns flagged at top (two soft flags; neither contradicts spec).

---

## Consensus

- **Planner**: APPROVE (iteration 2, authored all 9 iteration-1 Critic fixes + bonus note)
- **Architect**: APPROVE (iteration 2, verified all 9 fixes landed with file:line evidence; cross-section consistency confirmed; no new contradictions)
- **Critic**: APPROVE (iteration 2, ADR adopted without modification; 4 polish items dispositioned; mechanical edits applied via post-verdict cleanup pass)
- **Codex review (/oh-my-claudecode:ask codex)**: PASS after 8 fixes applied (2 P1 + 6 P2). Fixes closed: (P1-1) path-traversal validation via `paths.safe_resolve` + `PathTraversalError`, enforced at load + before every write; (P1-2) clean-run zero-write invariant — no log append, no pointer rewrite on `ops_ran=0 && result=clean`; (P2-3) marker `version=` promoted from reserved-for-future to drift-signal-in-v1.0 (mismatch triggers rewrite+backup); (P2-4) spec amended to include `failed_ops[]` and `depends_on_op` as authoritative schema fields; (P2-5) `test_dry_run_matches_apply` mandatory across all 5 per-op test files; (P2-6) `installed_version` derived as max successful semver, never by `applied_at` ordering — clock-skew safe; (P2-7) POSIX-only declared for v1.0 (macOS/Linux/WSL2 bash; native Windows deferred); (P2-8) check-count phrasing update uses repo-wide grep assertion instead of line-specific gates. Artifact: `.omc/artifacts/ask/codex-review-*-2026-04-14T21-44-20-126Z.md`.

**Status:** `READY_FOR_EXECUTION`. All three consensus agents + codex independent review have passed. Next gate: Stage 4 `/autopilot` (detects plan, skips Phase 0+1, enters at Phase 2 Execution).
