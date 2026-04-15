---
name: ark-update-framework
description: Generalized version-migration framework for ark-skills — declarative target-profile + optional per-version destructive migrations, Python engine, HTML-marker idempotency
type: spec
status: READY_FOR_PLAN
ambiguity: 0.057
---

# Deep Interview Spec: /ark-update Generalized Version-Migration Framework

## Metadata
- Interview ID: stream-b-ark-update-2026-04-14
- Rounds: 5
- Final Ambiguity Score: 5.7%
- Type: brownfield
- Generated: 2026-04-14
- Threshold: 20%
- Status: PASSED (all dimensions ≥ 0.92, early-exit rule applied)
- Worktree: `/Users/sunginkim/.superset/worktrees/ark-skills/ark-update`
- Branch: `ark-update`
- Companion stream: `.ark-workflow/handoffs/stream-a-omc-recommendations.md`
- Ship target: combined v1.14.0 release with Stream A

## Clarity Breakdown (final)

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.97 | 0.35 | 0.340 |
| Constraint Clarity | 0.93 | 0.25 | 0.233 |
| Success Criteria Clarity | 0.92 | 0.25 | 0.230 |
| Context Clarity (brownfield) | 0.93 | 0.15 | 0.140 |
| **Total Clarity** | | | **0.943** |
| **Ambiguity** | | | **0.057** |

---

## Goal

Build `/ark-update` as a **declarative, two-phase, replayable version-migration framework** for the ark-skills Claude Code plugin. Every downstream project that installed ark-skills at an older version (or needs to catch up to the current HEAD) can run `/ark-update` to:

1. **Phase 1 — Replay pending destructive migrations** (rare; per-version YAML files under `skills/ark-update/migrations/vX.Y.Z.yaml`). These handle renames, deletions, and one-time transforms that can't be expressed additively.
2. **Phase 2 — Converge project to the target profile** (every run; single file `skills/ark-update/target-profile.yaml`). This is the authoritative declaration of "what a HEAD-conformant ark-skills-using project looks like" — CLAUDE.md managed sections, required `.gitignore` entries, expected `.mcp.json` servers, template files that should exist.

The engine is written in Python (`scripts/migrate.py`). The `SKILL.md` is a thin LLM-facing wrapper that handles planning, progress rendering, user prompts, and the `/ark-update` command surface. Idempotency is guaranteed by HTML comment markers that delimit every ark-managed region in user files; inside markers the engine owns content and overwrites with backup, outside markers the engine never touches.

**One-sentence statement:** `/ark-update` is a version-driven skill that runs a Python engine to replay pending destructive migrations then converge the project to a declarative target profile, using HTML-comment markers to scope what the engine owns.

---

## Constraints (hard requirements)

### Architectural
- **Declarative first**: no LLM-interpreted prose playbooks in the hot path. The engine is deterministic Python; LLM only plans, renders progress, and prompts.
- **HTML comment markers are the ONLY idempotency mechanism**: `<!-- ark:begin id=<stable-id> version=<semver> -->` ... `<!-- ark:end id=<stable-id> -->`. Every managed region carries a stable ID (for ownership) and a version (for drift-detection context).
- **Strict inside/outside rule**: inside markers, engine overwrites on every run with backup of prior content. Outside markers, engine never reads, writes, or inspects.
- **Two-phase engine**: Phase 1 (destructive replay, version-gated) → Phase 2 (target-profile convergence, always runs). Phase 2 is idempotent; Phase 1 is one-shot per version.
- **State is committed, not gitignored**: `.ark/migrations-applied.jsonl` and `.ark/plugin-version` are project state, not user state. Collaborators stay in sync. PR diffs show migration events.

### Plugin conventions (honored from root CLAUDE.md)
- **Context-discovery exemption**: `/ark-update` inherits the same exemption as `/ark-onboard` and `/ark-health`. It must run when CLAUDE.md is missing, partial, or broken — but see Q5 resolution (refusal-to-run on specific broken-file classes, with handoff to `/ark-onboard repair`).
- **No hardcoded project names / vault paths / task prefixes**: all project-specific values resolved from the downstream project's CLAUDE.md at runtime, with graceful fallback when exempt-paths apply.
- **Graceful degradation**: a single failing op never aborts the whole run. Record the failure in the log, surface it in the run summary, continue with subsequent ops.
- **Git safety**: check repo state before any write; refuse to run on a dirty working tree unless `--force` is passed. Instruct user to commit before and after `/ark-update`.

### Engineering standards (honored from user workflow preferences in memory)
- `/codex review` on this spec before implementation.
- `/codex review` on the ralplan consensus plan before execution.
- `/ark-code-review` after implementation.
- Testing is REQUIRED, not optional. Two test lanes minimum (convergence + destructive replay) plus per-op unit tests.

### Ship coordination
- Do NOT bump VERSION / CHANGELOG / plugin.json / marketplace.json during Stream B commits. The v1.14.0 release PR is combined with Stream A and owned by whichever stream lands last.

---

## Non-Goals (explicitly excluded from v1.0)

- **Destructive operation primitives**: `rename_frontmatter_field`, `deprecate_file`, `remove_managed_region`. Deferred until an actual destructive release needs them. YAGNI.
- **LLM-interpreted prose playbooks**: no `migrations/v1.14.md` markdown files. The engine is declarative-only; the only markdown is SKILL.md (LLM wrapper) and template files that target-profile ops reference.
- **Three-way merge of user edits**: rejected in Q4. Inside-markers drift gets overwritten with backup, not merged.
- **Per-op rollback**: commit-based rollback at the run level + per-file backups for mid-run restoration. No op-level undo machinery.
- **Automatic invocation from `/ark-onboard repair`**: repair and update coexist independently. User invokes `/ark-update` explicitly when prompted by `/ark-health`.
- **Automatic detection of plugin upgrades**: `/ark-update` does not watch for new plugin versions. `/ark-health` gets a new version-drift check that recommends the user run it.
- **Migration authoring for past additive releases**: v1.11/v1.12/v1.13 do NOT get per-version migration files. Their conventions flow into `target-profile.yaml` with `since: 1.11.0` / `since: 1.12.0` / `since: 1.13.0` metadata. Phase 2 convergence handles the backfill.
- **Hot-patch semver handling beyond `> installed_version`**: v1.13.1 between v1.13.0 and v1.14.0 is handled by the standard sort+filter rule. No special patch-release path.
- **Support for non-semver version schemes**: plugin VERSION is assumed to be a valid semver.
- **Running `/ark-update` without the plugin installed**: the skill requires `$ARK_SKILLS_ROOT` to resolve to an installed plugin (the existing resolution pattern in `ark-context-warmup` applies).

---

## Acceptance Criteria

Each criterion is testable against the shipped artifact.

### Framework (skill installation)

- [ ] `skills/ark-update/SKILL.md` exists with context-discovery exemption, two-phase workflow, and command surface (`/ark-update`, `/ark-update --dry-run`, `/ark-update --force`).
- [ ] `skills/ark-update/target-profile.yaml` exists, schema-valid, and declares managed regions for every convention added in v1.11/v1.12/v1.13 that belongs in the target profile.
- [ ] `skills/ark-update/scripts/migrate.py` is the sole engine entry point. Invokable standalone for testing: `python3 scripts/migrate.py --project-root <path> --dry-run`.
- [ ] `skills/ark-update/scripts/ops/` directory contains 5 op modules: `ensure_claude_md_section.py`, `ensure_gitignore_entry.py`, `ensure_mcp_server.py`, `create_file_from_template.py`, `ensure_routing_rules_block.py`. Each exports `apply`, `dry_run`, `detect_drift`.
- [ ] `skills/ark-update/templates/` directory contains the template files referenced by target-profile entries (e.g., `omc-routing-block.md`, routing-rules-template content reused from `/ark-workflow`'s `references/routing-template.md`).
- [ ] `skills/ark-update/migrations/` directory exists and is empty in v1.0 (no destructive migrations yet).

### Engine correctness (Phase 1 — destructive replay)

- [ ] Given `.ark/migrations-applied.jsonl` with last entry `version: 1.13.0`, and `migrations/v1.14.2.yaml` (hypothetical destructive migration) in the plugin, engine computes `pending = [v1.14.2]`.
- [ ] Pending migrations are applied in strict semver sort order.
- [ ] After a migration applies cleanly, an entry is appended to the log: `{"version": "<v>", "applied_at": "<iso>", "ops_ran": <n>, "ops_skipped": <m>, "result": "clean", "phase": "destructive"}`.
- [ ] `.ark/plugin-version` is rewritten to the latest applied version after log append.
- [ ] If a destructive migration op fails, the log entry records `"result": "partial"` with per-op status, and subsequent ops in the same migration still run (graceful degradation).

### Engine correctness (Phase 2 — target-profile convergence)

- [ ] Every run invokes all ops declared in `target-profile.yaml` regardless of installed version. This is the idempotency guarantee.
- [ ] `ensure_claude_md_section`: if the section with `id=<X>` doesn't exist in CLAUDE.md, insert it with markers. If it exists but content differs from target, backup existing to `.ark/backups/CLAUDE.md.<UTC-ts>.bak` and overwrite. If content matches, no-op.
- [ ] `ensure_gitignore_entry`: append `<entry>` line to `.gitignore` if absent. If present, no-op. No markers needed (gitignore is append-safe).
- [ ] `ensure_mcp_server`: merge entry into `.mcp.json` at the specified JSON path. If `.mcp.json` missing, create it. If entry with same key exists, replace. Preserve other user-added servers.
- [ ] `create_file_from_template`: if target path doesn't exist, copy template from `$ARK_SKILLS_ROOT/skills/ark-update/templates/<name>` to `<target-path>`. If target exists, no-op (never overwrites — out of scope for v1.0).
- [ ] `ensure_routing_rules_block`: specialized `ensure_claude_md_section` with the canonical routing-template.md. Markers: `id=routing-rules`.
- [ ] After convergence, append log entry: `{"version": "<plugin-version>", "applied_at": "<iso>", "ops_ran": <n>, "ops_skipped": <m>, "result": "clean", "phase": "convergence"}`.

### Drift detection (inside markers)

- [ ] Engine reads region content delimited by `<!-- ark:begin id=X ... -->` ... `<!-- ark:end id=X -->`.
- [ ] If current region content byte-identical to target template content → no-op, no backup written.
- [ ] If current region content differs → write `.ark/backups/<file>.<UTC-ts>.bak` of entire file BEFORE overwrite, then overwrite markers+content.
- [ ] Run summary lists every drift event: `drift: <file>:<region-id> (backup: .ark/backups/...)`.
- [ ] Regions outside markers in the same file are byte-identical before and after the run (zero-touch guarantee).

### Dry-run semantics

- [ ] `--dry-run` flag produces a plan report (which ops would run, which ones would skip, which would overwrite with drift), writes NOTHING (no log append, no `.ark/` mutation, no backup, no file edit).
- [ ] Plan report is deterministic: running `--dry-run` twice produces byte-identical output.
- [ ] Plan report format includes per-op `would_apply` / `would_skip_idempotent` / `would_overwrite_drift` / `would_fail_precondition` status.

### State management

- [ ] `.ark/` directory created on first successful run. Contains `migrations-applied.jsonl`, `plugin-version`, `backups/`.
- [ ] Missing `.ark/` directory treated as `installed_version=0.0.0` (bootstrap); every historical destructive migration is pending, full target-profile convergence runs.
- [ ] Concurrent runs are serialized by an advisory lockfile at `.ark/lock` (PID-based, auto-cleaned on stale PID like `notebooklm-vault-sync.sh`).
- [ ] Malformed `migrations-applied.jsonl` (unparseable JSONL line) triggers refusal to run with instruction: "run /ark-onboard repair" — NOT silent recovery.

### Boundary with /ark-onboard and /ark-health

- [ ] `skills/ark-onboard/SKILL.md` Repair section cross-references `/ark-update` for version-drift diagnosis.
- [ ] `skills/ark-health/SKILL.md` adds a new check (post-Stream-A numbering): "ark-skills version current?" — compares `.ark/plugin-version` vs `$ARK_SKILLS_ROOT/VERSION`, warn-only, surfaces `"upgrade available: run /ark-update"` when drift detected. (Stream A's Check 21 ships first; this is likely Check 22 or Check 23 depending on coordination.)
- [ ] `/ark-update` refuses to run on broken files: malformed CLAUDE.md (can't parse frontmatter), unparseable `.mcp.json`, malformed `.ark/migrations-applied.jsonl`. Refusal message points to `/ark-onboard repair`.

### Testing

- [ ] `skills/ark-update/tests/fixtures/pre-v1.11/` — minimal project state as of pre-v1.11 (no vault layout row, no centralized script, no OMC block, no .ark/).
- [ ] `skills/ark-update/tests/fixtures/pre-v1.12/` — project as of pre-v1.12 (has v1.11 conventions, no warmup routing rule, no .ark/).
- [ ] `skills/ark-update/tests/fixtures/pre-v1.13/` — project as of pre-v1.13 (has v1.11+v1.12, no `.ark-workflow/` gitignore, no OMC routing block, no .ark/).
- [ ] `skills/ark-update/tests/fixtures/fresh/` — no project state at all (bootstrap test).
- [ ] `skills/ark-update/tests/fixtures/healthy-current/` — project already at HEAD (idempotency test; run should be zero-write no-op).
- [ ] `skills/ark-update/tests/fixtures/drift-inside-markers/` — project at HEAD but user edited inside a managed region (drift test; run should backup + overwrite, summary lists drift).
- [ ] `skills/ark-update/tests/fixtures/drift-outside-markers/` — project at HEAD, user edits OUTSIDE markers (zero-touch test; run should not modify those regions).
- [ ] `skills/ark-update/tests/test_convergence.py` — asserts post-run state for each fixture matches its `expected-post/` snapshot.
- [ ] `skills/ark-update/tests/test_idempotency.py` — runs engine twice, asserts second run is zero-write.
- [ ] `skills/ark-update/tests/test_dry_run.py` — asserts `--dry-run` writes nothing and is deterministic.
- [ ] `skills/ark-update/tests/test_op_<name>.py` — per-op unit tests (5 files). Each covers: `test_apply`, `test_idempotency`, `test_dry_run_matches_apply`, `test_detect_drift_inside_markers`, `test_no_touch_outside_markers`.
- [ ] `skills/ark-update/scripts/check_target_profile_valid.py` — CI validator; asserts `target-profile.yaml` conforms to schema, all `since:` fields match real plugin versions in CHANGELOG, all template references resolve to files under `templates/`. Mirrors the pattern of `check_path_b_coverage.py` / `check_chain_integrity.py`.
- [ ] Test fixtures use the `.expected-post/` sidecar pattern for snapshot assertions — NOT golden-file-in-repo-root.

### Documentation and cross-references

- [ ] `skills/ark-onboard/SKILL.md` Repair section has a paragraph: "For version drift (plugin updated but project conventions out of date), run `/ark-update` — it replays additive conventions from the current target profile."
- [ ] `skills/ark-health/SKILL.md` has a new check row documenting the version-drift check.
- [ ] `README.md` skill table includes `/ark-update` with a one-line description.
- [ ] `CHANGELOG.md` v1.14.0 entry describes `/ark-update` alongside Stream A's additions.

---

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| "A migration is an instruction the LLM reads and executes." | Q2 — offered LLM-playbooks, declarative-engine, hybrid, bash options. | Declarative YAML + Python engine. LLM is thin wrapper only. Chosen for determinism, testability, cheap replays, snapshot-friendly. |
| "Installed version lives in CLAUDE.md frontmatter." | Q1 — offered CLAUDE.md field, plain pointer file, migration log, hybrid. | Append-only log (authoritative) + cached pointer (convenience). Both committed. CLAUDE.md rejected because users edit it constantly and /ark-update may need to run when CLAUDE.md is the broken file. |
| "The engine prompts users when it detects drift inside managed sections." | Q4 — offered always-overwrite-with-backup, interactive diff+prompt, three-way merge, hash-based no-markers. | Strict HTML markers + always-overwrite with backup. Rejected interactive mode because it breaks batch/CI use and adds Y/N friction per conflict. Rejected three-way merge as over-engineered for v1.0. Rejected hash-based for inability to detect section deletion cleanly. |
| "Every plugin release ships a per-version migration file." | Contrarian challenge Q4-meta — asked if 'version delta' was the right unit at all. | **Contrarian landed.** Hybrid target-profile + destructive-only per-version migrations adopted. ~95% of historical bumps were additive, eliminated the per-version-file-per-release toil. Destructive migrations only authored when actually needed. |
| "Ops catalog should include all 8 primitives listed in the handoff." | Q3 — scope question: MVP (3) vs Standard (5) vs Full (8). | Standard: 5 target-profile ops only. Destructive 3 deferred to future release. Smaller surface, faster v1.0, can add when needed. |
| "/ark-update chains into /ark-onboard repair automatically when it detects broken files." | Q5 — derivable from already-pinned decisions. | Coexist, not chained. /ark-update refuses to run on specific broken-file classes and points user to `/ark-onboard repair`. /ark-onboard repair never calls /ark-update (stays failure-driven). /ark-health surfaces version drift as a new check. |
| "Per-op rollback is necessary for safety." | Q6 — derivable. | Rejected. Commit-based rollback (git commit before + after) + per-file `.ark/backups/<file>.<UTC-ts>.bak` for mid-run restoration. Users can `cp` a backup to restore any single file. No op-level undo machinery in v1.0. |
| "Migration fixtures should be regenerated from git history automatically." | Q8 — derivable. | Rejected as v1.0 scope. Manual fixture authoring is acceptable for the 3 historical pre-vN states. Regeneration script is a v1.1 enhancement if needed. |

---

## Technical Context (brownfield facts established)

From parallel codebase exploration at interview time:

### Plugin state
- Current VERSION: `1.13.0` (file `VERSION` at repo root)
- Plugin manifests: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Branch `ark-update` at commit `134b7ba` (clean; Stream A hasn't landed yet).

### Existing skill conventions applicable to `/ark-update`
- **`ARK_SKILLS_ROOT` discovery pattern** (`skills/ark-context-warmup/SKILL.md:31-49`): three-case fallback via `CLAUDE_PLUGIN_DIR` env → local `.claude-plugin/marketplace.json` anchor → `~/.claude/plugins` search. `/ark-update` MUST use this exact pattern.
- **Context-discovery exemption** (`skills/ark-onboard/SKILL.md:10-14`, `skills/ark-health/SKILL.md:10-18`): precedent for new skill to carry the same exemption language verbatim.
- **Python-backed scripts with CI validators**: `skills/ark-context-warmup/scripts/check_chain_integrity.py` and `check_path_b_coverage.py` are the pattern. `check_target_profile_valid.py` follows this.
- **`.ark-workflow/` directory for machine state** (added to `.gitignore` in v1.13): precedent for machine-owned state directories. However, `/ark-update`'s `.ark/` is COMMITTED (not gitignored), because log + pointer are project state, not ephemeral.
- **Frontmatter schema differences** (`CLAUDE.md` root § Ark Frontmatter Schema): `type:` not `category:`, `source-sessions:` and `source-tasks:` not `sources:`. Relevant if a destructive migration ever touches vault page frontmatter.

### No existing artifacts to worry about
- Zero `<!-- ark-managed -->` or `<!-- ark:begin -->` markers anywhere in the repo (verified by grep): clean slate for marker syntax.
- Zero existing `.ark/` directory conventions in any consumer project I can see from the plugin repo: clean slate for state layout.
- Zero existing `plugin-version` file: clean slate for pointer file.

### Stream coordination notes
- Stream A's Check 21 (OMC plugin detection) in `/ark-health` adds the first new post-v1.13 check. Stream B's version-drift check is downstream of it (Check 22 or 23). Stream A's changes to `skills/ark-onboard/SKILL.md` (Healthy Step 3 upgrade entry + Greenfield Step 18 mention) are adjacent-but-not-conflicting to Stream B's Repair-section cross-reference to `/ark-update`. Coordinated merge at release time.

---

## Answers to the 8 Open Architectural Questions

| # | Question | Resolution |
|---|----------|------------|
| Q1 | Version bookkeeping | **Append-only log** `.ark/migrations-applied.jsonl` (authoritative) **+ cached pointer** `.ark/plugin-version`. Both committed. Missing `.ark/` ⇒ `installed_version=0.0.0` bootstrap. /ark-update gets context-discovery exemption (same as /ark-onboard and /ark-health). |
| Q2 | Migration format | **Declarative YAML + Python engine.** No LLM-interpreted playbooks. SKILL.md is thin wrapper only. |
| Q3 | Ops catalog (v1.0) | **5 target-profile ops**: `ensure_claude_md_section`, `ensure_gitignore_entry`, `ensure_mcp_server`, `create_file_from_template`, `ensure_routing_rules_block`. Destructive 3 (`rename_frontmatter_field`, `deprecate_file`, `remove_managed_region`) deferred. |
| Q4 | Idempotency + conflict | **Strict HTML markers `<!-- ark:begin id=X version=Y -->`/`<!-- ark:end id=X -->`. Always overwrite inside markers with backup to `.ark/backups/<file>.<UTC-ts>.bak`. Never touch outside markers.** No three-way merge, no interactive prompt in v1.0. |
| Q5 | Boundary with /ark-onboard | **Coexist, not chained.** Repair stays failure-driven. /ark-update is version-driven. /ark-health surfaces version drift as a new check recommending /ark-update. /ark-update refuses to run on malformed CLAUDE.md / .mcp.json / .ark/log, points user to /ark-onboard repair. /ark-onboard Repair section cross-references /ark-update for version-drift diagnosis (new paragraph). |
| Q6 | Dry-run + rollback | **`--dry-run` flag is mandatory.** Rollback: commit-based at run level + per-file `.ark/backups/<file>.<UTC-ts>.bak` for mid-run restoration. **No per-op rollback in v1.0.** |
| Q7 | Discovery | Plugin version from `$ARK_SKILLS_ROOT/VERSION`. Target-profile from `$ARK_SKILLS_ROOT/skills/ark-update/target-profile.yaml` (always loaded, single file). Destructive migrations from `$ARK_SKILLS_ROOT/skills/ark-update/migrations/*.yaml` sorted semver, filter `version > installed_version`. Hot-patches (v1.13.1) handled by the same rule, no special path. |
| Q8 | Testing strategy | **Two test lanes + per-op unit tests.** Lane 1 (convergence): fixtures at `tests/fixtures/pre-v{N.M.P}/` with `expected-post/` sidecar snapshots. Lane 2 (destructive replay): per-migration fixtures. Per-op unit tests cover apply/idempotency/dry-run/detect-drift/no-touch-outside. CI validator `check_target_profile_valid.py` validates schema + since-field accuracy + template-reference resolution. Manual fixture authoring for v1.0 — regeneration-from-git script deferred to v1.1. |

---

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| TargetProfile | core domain | `managed_regions[]`, `ensured_files[]`, `ensured_gitignore[]`, `ensured_mcp_servers[]`, `schema_version` | Loaded once per run by Engine; drives Phase 2 convergence. |
| ManagedRegion | core domain | `id` (stable), `file`, `version`, `template`, `since` (first plugin version that introduced it) | Delimited in user file by `<!-- ark:begin id=X version=Y -->`...`<!-- ark:end id=X -->`. Owned by Engine inside markers. |
| DestructiveMigration | core domain | `version` (semver), `ops[]` (each op may carry optional `depends_on_op: <op-id>` for skip-cascade on dependency failure), `description` | Per-version YAML in `migrations/`. Optional (most releases have none). Applied once by Engine Phase 1, recorded in log. |
| Operation | core domain | `type` (op name), `args` (typed dict), `dry_run()`, `apply()`, `detect_drift()` | Composed into DestructiveMigration.ops[] or TargetProfile.managed_regions[]. Implemented as Python class under `scripts/ops/`. |
| Engine | supporting | `migrate.py` CLI, `apply(project_root, dry_run=False, force=False)` | Consumes TargetProfile + DestructiveMigration manifests. Writes MigrationLog entries. Orchestrates Phase 1 → Phase 2. |
| SKILL.md wrapper | supporting | LLM-facing markdown, invokes Engine via Bash tool, renders plan summaries | Thin wrapper only. No business logic. |
| MigrationLog | core state | `.ark/migrations-applied.jsonl`, append-only, per-line JSON: `{version, applied_at, ops_ran, ops_skipped, failed_ops: list[{op_id, op_type, error}], result, phase}` (empty `failed_ops: []` on clean runs). **Clean runs MUST be zero-write: no log append, no pointer rewrite.** Log append only occurs when `ops_ran > 0` OR `result != "clean"`. | Authoritative. Written by Engine after each successful *mutating* phase. Read by Engine to compute `installed_version` (= max successful semver across Phase-1 entries, dedup by (semver, phase); `applied_at` is advisory only). Read to determine pending work. |
| VersionPointer | supporting state | `.ark/plugin-version`, single semver line | Cached convenience for `/ark-health` and user grep. Rewritten by Engine after each successful phase. Never the source of truth. |
| Backup | supporting state | `.ark/backups/<file>.<UTC-ts>.bak`, byte-for-byte copy of pre-overwrite file | Written by Engine before ANY overwrite of content inside markers. Drift-restoration mechanism. |

---

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 5 | 5 | - | - | N/A (baseline) |
| 2 | 7 | 2 (MigrationLog, VersionPointer) | 0 | 5 | 71% |
| 3 | 8 | 1 (ManagedRegion) | 0 | 7 | 88% |
| 4 | 9 | 1 (TargetProfile) | 1 (Migration → DestructiveMigration; renamed, same type, >50% field overlap — counts as stable) | 7 | 89% |
| 5 | 9 | 0 | 0 | 9 | **100%** |

Converged fully by Round 5. Operation is now a first-class entity (noted implicitly in Round 1 under Engine, formally surfaced in Round 5 as ops-catalog-selection made it concrete). Matching reasoning: Migration → DestructiveMigration satisfies the >50% field overlap rule (both have version + ops[]; DestructiveMigration dropped the `custom_steps` field that never got pinned).

---

## Key Implementation Notes (for the planner)

These aren't acceptance criteria but are load-bearing design details that should NOT be lost between this spec and the implementation plan.

### Engine architecture
```
skills/ark-update/
├── SKILL.md                        # LLM wrapper, ~200 lines
├── target-profile.yaml             # ~60 lines after v1.11-v1.13 backfill
├── migrations/                     # empty in v1.0
├── templates/
│   ├── omc-routing-block.md        # canonical OMC routing template (copy from /ark-workflow's reference)
│   └── ... (one per create_file_from_template target)
├── scripts/
│   ├── migrate.py                  # engine CLI entry point
│   ├── state.py                    # log + pointer read/write, bootstrap
│   ├── markers.py                  # region extract/insert/replace
│   ├── plan.py                     # dry-run plan builder
│   ├── ops/
│   │   ├── __init__.py             # op registry
│   │   ├── ensure_claude_md_section.py
│   │   ├── ensure_gitignore_entry.py
│   │   ├── ensure_mcp_server.py
│   │   ├── create_file_from_template.py
│   │   └── ensure_routing_rules_block.py  (subclass of ensure_claude_md_section)
│   └── check_target_profile_valid.py  # CI validator
└── tests/
    ├── fixtures/
    │   ├── pre-v1.11/
    │   ├── pre-v1.12/
    │   ├── pre-v1.13/
    │   ├── fresh/
    │   ├── healthy-current/
    │   ├── drift-inside-markers/
    │   └── drift-outside-markers/
    ├── test_convergence.py
    ├── test_idempotency.py
    ├── test_dry_run.py
    └── test_op_*.py                (one per op)
```

### Marker syntax (canonical)
```
<!-- ark:begin id=<stable-id> version=<semver> -->
<content owned by ark-update>
<!-- ark:end id=<stable-id> -->
```

Parsing rules:
- Begin marker regex: `<!-- ark:begin id=([a-z][a-z0-9-]*) version=(\d+\.\d+\.\d+) -->`
- End marker regex: `<!-- ark:end id=([a-z][a-z0-9-]*) -->`
- Begin and end must have matching `id`; mismatch ⇒ refuse to run, point to `/ark-onboard repair`.
- Nested markers are illegal (no `id=outer` region containing `id=inner`).
- A file may contain multiple managed regions with different IDs.

### target-profile.yaml schema (illustrative, to be formalized by planner)
```yaml
schema_version: 1
managed_regions:
  - id: omc-routing
    file: CLAUDE.md
    template: omc-routing-block.md
    since: 1.13.0
    version: 1.13.0   # bumped only when target content changes for this region
  - id: routing-rules
    file: CLAUDE.md
    template: routing-template.md
    since: 1.3.0
    version: 1.12.0  # bumped in 1.12 when warmup step 0 was added
ensured_gitignore:
  - entry: .ark-workflow/
    since: 1.13.0
ensured_mcp_servers:
  - file: .mcp.json
    key: tasknotes-mcp
    # ... specific JSON shape
    since: 1.4.2
ensured_files:
  - target: scripts/setup-vault-symlink.sh
    template: setup-vault-symlink.sh
    since: 1.11.0
    only_if_centralized_vault: true  # gate condition — engine skips if condition absent
```

### Gating conditions (forward-compat)

Some target-profile entries should only apply when the downstream project opted into a particular layout (e.g., centralized vault vs embedded). The engine supports a minimal `only_if_<flag>` key per entry; flags are resolved from CLAUDE.md discovery:
- `only_if_centralized_vault`: CLAUDE.md's "Vault layout" row does NOT contain "embedded".
- More gates added as needed in future target-profile entries. Keep the gate vocabulary small and documented.

### Commit protocol for /ark-update runs
- `/ark-update` instructs the user to commit BEFORE running (refuses on dirty tree unless `--force`).
- After a successful run, `/ark-update` prints a suggested commit message: `chore: run /ark-update → plugin v<latest>` and does NOT auto-commit (user owns the commit).
- Failed/partial runs leave `.ark/backups/*` in place; user can `git status` to see what changed.

---

## Interview Transcript (condensed)

### Round 1 — Migration format (Goal Clarity: 0.35 → 0.75)
- **Q:** What fundamentally IS a migration — LLM instruction, declarative engine, or hybrid?
- **A:** Declarative manifests + Python engine (Recommended).
- **Ambiguity:** 100% → 42.5%

### Round 2 — Version bookkeeping (Goal: 0.75 → 0.88, Constraints: 0.45 → 0.65)
- **Q:** Where does "what migrations are applied" live — CLAUDE.md / plain file / log / hybrid?
- **A:** Append-only log + cached pointer, both committed (Recommended).
- **Ambiguity:** 42.5% → 30.1%

### Round 3 — Idempotency (Constraints: 0.65 → 0.82, Criteria: 0.40 → 0.68)
- **Q:** User edited managed section between runs — skip / prompt / three-way / hash-based?
- **A:** Strict markers + always overwrite with backup (Recommended).
- **Ambiguity:** 30.1% → 16.7%

### Round 4 — CONTRARIAN: unit of evolution (Goal: 0.88 → 0.96)
- **Q:** Is 'version delta' the right unit? v1.11-v1.13 were ~95% additive. Target-profile + destructive-only-migrations might be simpler.
- **A:** Hybrid adopted (Recommended). **Contrarian landed.**
- **Ambiguity:** 16.7% → 10.1%

### Round 5 — Ops catalog v1.0 (Constraints: 0.88 → 0.93, Criteria: 0.82 → 0.92)
- **Q:** Which typed ops ship in v1.0 — MVP (3), target-only (5), or full (8)?
- **A:** Target-profile only (5). Destructive 3 deferred.
- **Ambiguity:** 10.1% → 5.7% — **GATE MET**

---

## Next Stage (pipeline continuation)

Per deep-interview's Execution Bridge and this stream's handoff workflow:

1. **`/ralplan --direct`** on this spec → Planner / Architect / Critic consensus plan at `.omc/plans/ralplan-ark-update.md` (the `--direct` flag skips the interview phase since we just completed it).
2. **`/codex review .omc/plans/ralplan-ark-update.md`** (required per user's saved memory).
3. **`/autopilot`** (recommended) or `superpowers:executing-plans` with manual subagent dispatch. Autopilot will auto-detect the ralplan output, skip Phase 0+1, start at Phase 2 (Execution).
4. **Stage 5 self-test**: run historical backfill (pre-v1.11, pre-v1.12, pre-v1.13 fixtures) through target-profile convergence. Do NOT skip — shipping an untested framework is shipping broken code.
5. **`/ark-code-review`** post-implementation.
6. **`/wiki-update`** session log + vault sync.
7. **Ship coordination**: combined v1.14.0 release PR with Stream A (OMC in onboard/health). Do NOT bump VERSION during Stream B commits.
