# Changelog

All notable changes to this project will be documented in this file.

## [1.15.0] - 2026-04-15

### Added

- **External Second Opinion via `omc ask`** in `skills/ark-code-review/SKILL.md`. `/ark-code-review --thorough` (and any mode that inherits it, including `--full`) now solicits a vendor-training-biased second opinion from `codex` and/or `gemini` when either CLI is on PATH alongside OMC. Opt-out via `--no-multi-vendor` (alias `--no-xv`). Uses the `omc ask <vendor> "<prompt>"` primitive — no tmux, no process orchestration. Each vendor response is captured as a plain markdown artifact at `.omc/artifacts/ask/<vendor>-<slug>-<ts>.md` and merged into the unified report.
- **Trust Boundary Notice** in the External Second Opinion section — explicit guidance to confirm the diff contains no regulated / NDA / secret content before accepting the default fan-out, with per-invocation (`--no-multi-vendor`) and per-project (CLAUDE.md routing) opt-out paths.
- **Vendor context cap discipline.** Vendors receive only `<diff_path>`, `<changed_files_list>`, and a 1-paragraph neutral branch description — **NOT** CLAUDE.md, plugin skills, vault content, or TaskNotes. Native CC agents remain the conventions-aware layer; vendor streams are a vendor-diversity sanity check, not a capability expansion.
- **Gemini capacity caveat** documented — observed `MODEL_CAPACITY_EXHAUSTED` (HTTP 429) on `gemini-3.1-pro-preview` under burst load during live testing, handled as a per-vendor runtime failure with graceful degradation to "synthesize on remaining streams".

### Changed

- **`--thorough` and `--full` mode descriptions** in `skills/ark-code-review/SKILL.md` updated to document the External Second Opinion augmentation and its trust-boundary / context-cap discipline.

### Explicitly not included

- **`/omc-teams` chain integration.** `/omc-teams` (process-based CLI workers in tmux panes) is NOT auto-routed by `/ark-workflow`. It remains a user-triggered power tool — users invoke `/omc-teams 1:<vendor> "<task>"` manually when they want a process-isolated worker. Knowledge-Capture Full deliberately has no Path B block for the same reason: full-variant capture is too broad and branchy for a single-engine autonomous pass, and wiring `/omc-teams` as the step-3 engine clashes with its multi-stage leader-driven orchestration model (`omc team` only allocates + registers workers; it does not auto-execute, and the framework enforces `one_team_per_leader_session`). Users can still invoke `/omc-teams` manually for bulk capture if desired.
- **`HAS_OMC_TEAMS` probe.** Not needed — External Second Opinion uses `omc ask` which requires only `HAS_OMC=true AND (codex OR gemini on PATH)`, and there is no auto-routed `/omc-teams` integration.

### Rationale

`omc ask` was chosen over `omc team` (the `/omc-teams` primitive) for External Second Opinion fan-out because:

- No tmux dependency.
- No multi-stage leader-driven orchestration required; single-shot invocation matches the review skill's single-pass consumption model.
- No `omc team api list-tasks --json` schema dependency; vendor output is returned as a plain markdown artifact path on stdout.
- Built-in shell/JSON quoting removes the injection surface from prompt interpolation.

Early design iterations routed `/ark-workflow` chains to `/omc-teams` (a "Knowledge-Capture Full" Path B variant using `/omc-teams 1:gemini` as the step-3 engine). A live Codex review on that design surfaced two bug-level issues (gate over-permissiveness on codex-only hosts; hardcoded `vault/` path violating the plugin's context-discovery rule) and an architectural mismatch (`omc team` expects leader-driven multi-stage flow, not a single "spawn and wait" call). The decision was made to drop auto-routed `/omc-teams` integration entirely and keep `/omc-teams` as a user-triggered primitive. The `omc ask`-based External Second Opinion in `/ark-code-review --thorough` is the only ark-auto-routed vendor integration that ships in v1.15.0.

### Coverage footprint

- `skills/ark-context-warmup/scripts/check_path_b_coverage.py` expects **18 Path B blocks** across 7 chain files (was 19 pre-v1.15.0 — Knowledge-Capture Full's Path B was removed this release). `ALLOWED_SHAPES` count for `special-b-knowledge-capture` dropped from 2 → 1 (only the Light variant now has a Special-B block). Distinct canonicalized shapes remain 6.

### Version note

This entry was originally authored as v1.14.0 on branch `ark-workflow-improve-OMC` (commit `0376ebc`, date 2026-04-14) before a rebase onto master. While this branch was open, master independently shipped a different v1.14.0 (Stream A + Stream B — see entry below). This External Second Opinion release was renumbered to v1.15.0 to avoid the collision. Content is unchanged; only the version label differs from the original commit.

## [1.14.0] - 2026-04-14

Combined two-stream release: **Stream A** (OMC plugin detection in `/ark-onboard` + `/ark-health`) and **Stream B** (`/ark-update` version-driven migration framework). Total plugin skill count: 18 → **19**. Total `/ark-health` diagnostic check count: 20 → **22**.

### Added

#### Stream B — `/ark-update` version-driven migration framework (NEW skill, 19th)

- **`skills/ark-update/SKILL.md`** — LLM-facing wrapper (210 LOC). Preflight git dirty-check, `ARK_SKILLS_ROOT` three-case resolution (mirrors `/ark-context-warmup:31-49`), `HAS_OMC` probe + centralized-vault detection exported as `ARK_HAS_OMC` / `ARK_CENTRALIZED_VAULT` env vars to `migrate.py`, pre-run warning for inside-marker overwrite, post-run summary rendering (ops-applied / drift events / failures / suggested commit message), refusal-mode handoff to `/ark-onboard repair`. Context-discovery exemption block (byte-pattern-parallel to `/ark-onboard`, `/ark-health`). POSIX-only declaration.
- **`skills/ark-update/scripts/migrate.py`** — CLI entry point. Two-phase engine: Phase 1 replays pending destructive migrations (`migrations/*.yaml`, ordered by semver, with `depends_on_op` chaining and dedup against `migrations-applied.jsonl`); Phase 2 converges on the declarative `target-profile.yaml` (idempotent, HTML-comment marker-driven). `_read_gate_flags()` strictly recognizes `"0"`/`"1"` env values (whitespace-stripped); other values degrade safely to "disabled." `_check_ark_not_gitignored` pre-mortem guard refuses when `.ark/` is gitignored.
- **`skills/ark-update/scripts/plan.py`** — dry-run plan builder that enumerates the same target-profile surface as the engine, renders a byte-deterministic plan tree.
- **`skills/ark-update/scripts/state.py`** — log + pointer + lock + backup_path. **Clean-run zero-write invariant** (codex P1-2): `maybe_append_log_and_pointer` short-circuits on runs with zero ops applied — no JSONL append, no pointer rewrite, byte-stable on disk. `computed_installed_version` derives from max-semver dedup over `(semver, phase)` pairs (codex P2-6); timestamps are advisory only. JSONL log schema includes `failed_ops[]` array (codex P2-4).
- **`skills/ark-update/scripts/markers.py`** — HTML-comment marker extract/replace/insert. Marker format: `<!-- ark:begin id=<id> version=<semver> -->` / `<!-- ark:end id=<id> -->`. Stale `version=` triggers rewrite + backup even when content matches template (codex P2-3 — marker-version honesty).
- **`skills/ark-update/scripts/paths.py`** — `safe_resolve` + `PathTraversalError` (codex P1-1). All op-accepted paths dual-gated: load-time validation in `migrate.py:_validate_target_profile_paths` and dispatch-time re-validation in `TargetProfileOp._safe_args`. Symlink targets pre-resolved before comparison.
- **`skills/ark-update/scripts/ops/__init__.py`** — `TargetProfileOp` + `DestructiveOp` base classes and `OP_REGISTRY`. `DestructiveOp` scaffold wired-but-empty for v1.0; first destructive migration ships when needed.
- **Five op implementations:**
  - `ensure_claude_md_section` — managed HTML-comment regions in CLAUDE.md; drift detection + `.bak` + `.bak.meta.json` provenance sidecar ({op, region_id, run_id, pre_hash (sha256), reason, timestamp}).
  - `ensure_gitignore_entry` — appends patterns if absent; safe no-op if already present.
  - `ensure_mcp_server` — adds entries to `.mcp.json`; `_ark_managed: true` sentinel prevents clobbering user-managed entries; `McpClobberError` refusal on collision without sentinel; `JSONDecodeError`-tolerant.
  - `create_file_from_template` — byte-copy templates into project with symlink-target guard (`SymlinkTargetError`).
  - `ensure_routing_rules_block` — subclass of `ensure_claude_md_section` with canonical `_canonical_args` injection for the routing-rules region.
- **`skills/ark-update/scripts/check_target_profile_valid.py`** — CI validator. Schema-checks `target-profile.yaml`; enforces `templates/routing-template.md` byte-equality with `skills/ark-workflow/references/routing-template.md` (drift guard); accepts log-schema extensions (`failed_ops`, `depends_on_op`).
- **`skills/ark-update/target-profile.yaml`** — v1.0 declarative profile: 2 managed regions (`omc-routing` since 1.13.0, `routing-rules` at v1.12.0), 1 ensured-file (`setup-vault-symlink` gated on `only_if_centralized_vault` since 1.11.0), 1 gitignore entry (`.ark-workflow/` since 1.13.0), 0 MCP server rows. `schema_version: 1`.
- **`skills/ark-update/tests/`** — **237 passing tests in ~9s**. Unit coverage for paths, state, markers, plan, each of 5 ops. Integration: 7 fixtures (pre-v1.11, pre-v1.12, pre-v1.13, fresh, healthy-current, drift-inside-markers, drift-outside-markers) × convergence + idempotency + dry-run + refusal-modes + destructive-replay + e2e-shell + logging + run-summary + backup-provenance + gate-flags (23 new). `MANUAL_STAGE5.md` runbook for the mandatory ship gate.

#### Stream A — OMC plugin detection in `/ark-onboard` + `/ark-health`

- **`/ark-health` Check 21** — detects the `oh-my-claudecode` plugin. Upgrade-style, tier-agnostic. Present in all tiers (Lite, Standard, Full). Warn-only when OMC absent — never fails the scorecard.
- **`/ark-onboard` Healthy Step 3** — OMC upgrade entry surfaced when scorecard shows Check 21 = warn. Non-blocking.
- **`/ark-onboard` Greenfield Step 18** — OMC mention during new-project setup (optional).
- **`/ark-onboard` scorecard** — now reports 21 checks (before Stream B's Check 22 lands below).

#### Stream A + Stream B — `/ark-health` Check 22 (Plugin Versioning)

- **New `### Plugin Versioning (Checks 22+)` section** in `skills/ark-health/SKILL.md`.
- **Check 22: `ark-skills version current?`** — compares `.ark/plugin-version` vs `$ARK_SKILLS_ROOT/VERSION`; surfaces `upgrade available: run /ark-update` on mismatch. Warn-only (never fails). Additionally asserts `.ark/` is not gitignored (pre-mortem Scenario 3 mitigation).

### Changed

- **`skills/ark-onboard/SKILL.md` Repair section** — new anchored paragraph at end of `## Path: Partial Ark (Repair)`: "For version drift (plugin updated but project conventions out of date), run `/ark-update`..." Wrapped with `<!-- stream-b: /ark-update cross-reference begin/end -->` HTML-comment anchors for merge-traceability.
- **Repo-wide check-count phrasing** updated from various stale counts (19/20/21) to final **22** — `/ark-health` tier descriptions, `/ark-onboard` scorecard output, and all inline references. Remaining `checks 7–20` phrases are legitimate range descriptions (Checks 21 and 22 are CLAUDE.md-exempt).
- **`README.md`** — `/ark-update` row added to skill table under Onboarding. Plugin skill count 18 → 19. Architecture diagram + Repository Structure table updated. Verification check regex comment updated.

### Fixed

- **Gate-flag test coverage** (`cf0ec41`, codex P1 + /ark-code-review P1-A). Gate-flag paths (`ARK_HAS_OMC`, `ARK_CENTRALIZED_VAULT`) added in Step 7 had no test coverage. New `tests/test_gate_flags.py` adds 23 tests pinning `_read_gate_flags` edge cases (unset/"1"/"0"/""/"true"/"yes"/whitespace) and `_iter_target_profile_entries` skip behavior across all gate combinations. Regression-safe for Step 7 wiring.

### Security

- **Path traversal hardening** (codex P1-1). All paths declared in `target-profile.yaml` `PATH_ARGS` tuples are dual-gated through `safe_resolve` — raises `PathTraversalError` if the resolved absolute path is outside the project root. Test coverage across all path-accepting ops.
- **Symlink-target validation** (`create_file_from_template`). Pre-resolves the template target; refuses with `SymlinkTargetError` if the target resolves outside the project root.
- **`.mcp.json` clobber guard.** `ensure_mcp_server` refuses to overwrite existing entries without an `_ark_managed: true` sentinel; `McpClobberError` with suggested repair path.

### Testing Acceptance Criteria (Stage-5 ship gate)

Mandatory manual self-test gate — PASSED:

- Full pytest: **237/237 passing** in ~9s.
- Fixture authenticity check: visual attestation that pre-v1.11, pre-v1.12, pre-v1.13 represent believable pre-v(N) project shape.
- End-to-end convergence via `migrate.py` CLI on all three historical fixtures: post-state byte-exact to `expected-post/`; `.ark/plugin-version` = `1.14.0`; `.ark/migrations-applied.jsonl` correctly populated; zero `.ark/backups/` writes on non-drift fixtures.
- Idempotency spot-check: second run on pre-v1.11 emits "clean — nothing to do" with zero file changes, zero JSONL append (codex P1-2 invariant held in the wild).
- Evidence captured in `vault/Session-Logs/2026-04-14-stage5-self-test-evidence.md`.

### Code Review (Step 11 — two-lane)

- `/ark-code-review` multi-agent synthesis (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) and codex second-opinion pass. 1 consensus P1 fixed (gate-flag tests above). 1 codex-only P1 (non-atomic pointer/log writes — /ark-code-review rated P2) and 10 P2 + 10 P3 findings deferred to v1.1.0 ADR triage.
- Findings captured in `vault/Session-Logs/2026-04-14-step11-review-findings.md` with ADR candidates (ADR-1 atomic filesystem writes, ADR-2 schema versioning, ADR-3 operational surface hardening).

### Degradation contract

- `/ark-update` is opt-in. Absence has zero impact on existing workflows. `/ark-onboard` repair and `/ark-update` convergence are **peers** — neither chains the other automatically; `/ark-update` refuses on malformed state and points users to `/ark-onboard`.
- Gate flags degrade safely: unset env vars = unconditional application (backward-compat); non-`"1"`/`"0"` values degrade to "disabled." SKILL.md wrapper only emits `"0"` or `"1"`.

### Spec & Plan

- Deep-interview spec: `.omc/specs/deep-interview-ark-update-framework.md`
- Ralplan consensus: `.omc/plans/ralplan-ark-update.md` (Architect + Critic APPROVE)
- Epic: `vault/TaskNotes/Tasks/Epic/Arkskill-004-ark-update-framework.md`
- Session log: `vault/Session-Logs/S008-Ark-Update-Framework.md`

### Commit convention

All 11-step Stream B commits and the combined release commit follow the intent-line + structured-trailer format (`Confidence:`, `Scope-risk:`, `Not-tested:`) from prior releases.

## [1.13.0] - 2026-04-13

### Added

- **Dual-mode `/ark-workflow` routing.** Every chain now emits Path A (Ark-native, step-by-step, user-in-the-loop) and Path B (OMC-powered: `/deep-interview` → `/omc-plan --consensus` → `/autopilot` execution-only → `<<HANDBACK>>` → variant-inherited Ark closeout) when OMC is installed. 19 variants across 7 chain files; graceful degradation to Path A only when `HAS_OMC=false`.
- **`HAS_OMC` availability probe** in `skills/ark-workflow/SKILL.md` (bash; mirrors `HAS_UI`/`HAS_VAULT` pattern). Honors `ARK_SKIP_OMC=true` env var as emergency rollback.
- **`has_omc` key** added to `skills/ark-context-warmup/scripts/availability.py` probe result; Context Brief now includes an "OMC detected: yes/no" line.
- **`skills/ark-workflow/references/omc-integration.md`** consolidates Section 0 canonical constants (`OMC_CACHE_DIR`, `OMC_CLI_BIN`, `INSTALL_HINT_URL`, `HANDBACK_MARKER`), two-philosophies axis, per-chain skill map, OR-any signal rule (4 signals: keyword / Heavy weight / multi-module / explicit autonomy), variant-inherited handback contract with four sub-contracts (`/autopilot`, `/ralph`, `/ultrawork`, `/team`), per-variant expected-closeout table (19 rows, 3 shapes), and `/autopilot` execution-only mechanism (`OMC_EXECUTION_ONLY=1` env-var fallback pending first-class OMC flag).
- **`skills/ark-context-warmup/scripts/check_path_b_coverage.py`** — CI check enforcing 19 Path B blocks across 7 chain files with ≤6 distinct canonicalized shapes: Vanilla (`/autopilot`, 12 variants), `/ralph` (Performance Medium+Heavy, 2 variants — Section 4.2), `/ultrawork` (Greenfield Heavy, 1 variant — Section 4.3), `/team` (Migration Heavy, 1 variant — Section 4.4), Special-A Hygiene-Audit-Only (1), Special-B Knowledge-Capture (2). Canonicalization strips `--(quick|thorough)` weight markers and `{weight}` placeholders so weight-indistinguishable blocks within a shape hash identically.

### Changed

- **All 19 variants across all 7 chain files** gained a `### Path B (OMC-powered)` section (12 Vanilla + 2 `/ralph` + 1 `/ultrawork` + 1 `/team` + 1 Special-A + 2 Special-B).
- **Step 6 of `/ark-workflow`** now renders the 3-button recommendation UX (`[Accept Path B] [Use Path A] [Show me both]`) when `HAS_OMC=true` and ≥1 of the 4 signals fires (OR-any rule; discoverability over neutrality). Includes checkpoint-density + duration estimate next to `[Accept Path B]` to mitigate blackbox-acceptance risk.

### Degradation contract

- `HAS_OMC=false` emits Path A only, plus a one-line install hint (`NOTE: OMC not detected. Autonomous-execution chains hidden. Install: <URL>`). `ARK_SKIP_OMC=true` forces this path regardless of detection. Zero behavioral change vs v1.12.0 on OMC-less installs. OMC remains optional.

### Observability

- Router writes one newline-delimited JSON line per triage invocation to `.ark-workflow/telemetry.log` (gitignored, covered by the existing `.ark-workflow/` ignore rule). Fields: `ts`, `has_omc`, `ark_skip_omc`, `signals_matched`, `recommendation`, `path_selected`, `variant`. Anonymized — no prompt text, no user identifier, no file paths. Enables post-hoc measurement of Path B selection rate, recommendation accuracy, and `ARK_SKIP_OMC` usage.

### Commit convention

All Phase 1/2a/2b/3/4/5 commits use the intent-line + structured-trailer format from `.claude/skills/omc-reference/SKILL.md` lines 112–141 (`Constraint:`, `Rejected:`, `Directive:`, `Confidence:`, `Scope-risk:`, `Not-tested:`). See `.omc/plans/2026-04-13-omc-ark-workflow-integration.md` § Commit Convention for the worked example.

### Plan

Implementation plan: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md` (ralplan consensus iteration 2, Architect + Critic both APPROVE). Spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md`.

## [1.12.0] - 2026-04-13

### Added

- `/ark-context-warmup` skill: automatic context loader that runs as step 0 of every `/ark-workflow` chain. Queries `/notebooklm-vault`, `/wiki-query`, and `/ark-tasknotes` backends in a partial parallel fan-out, synthesizes one Context Brief, surfaces possible duplicates / prior rejections / in-flight collisions as Evidence candidates. Cache keyed on `chain_id + task_hash`, 2-hour TTL, 24-hour pruning. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`.
- `warmup_contract` YAML blocks in `skills/notebooklm-vault/SKILL.md`, `skills/wiki-query/SKILL.md`, `skills/ark-tasknotes/SKILL.md` describing the machine-readable interface warm-up consumes.
- `skills/ark-workflow/SKILL.md` Step 6.5 now persists five additional frontmatter fields in `.ark-workflow/current-chain.md`: `chain_id`, `task_text`, `task_summary`, `task_normalized`, `task_hash`.
- Chain-integrity and contract-extension CI checks (`check_chain_integrity.py`, `check_contract_extension.py`) that run against the chains and `/ark-workflow` SKILL.md to catch regressions to step-0 insertion and Step 6.5 frontmatter fields.
- Evidence-candidate regression fixtures (9 YAMLs) locked-down at data level, replayed through `evidence.derive_candidates` via `test_fixtures.py`.

### Changed

- All seven chain files (`skills/ark-workflow/chains/*.md`) prepend `0. /ark-context-warmup` as step 0 in every weight-class section; handoff markers preserved (still reference original step numbers — see the plan's Task 20 notes).

### Fixed

Post-implementation hardening from successive codex review passes (committed on this branch before ship):

- **YAML safety.** `task_summary` is now emitted as a block scalar (`|-`) in both the chain-file frontmatter (`/ark-workflow` Step 6.5) and the cache-brief frontmatter (`synthesize.assemble_brief`). Task text containing `:`, `#`, `|`, or quotes no longer invalidates the frontmatter and forces cold-cache every run.
- **NotebookLM lane works end-to-end.** Added `json_path_template` to both `notebook_id` input specs (was raising `KeyError` silently and returning None). Template inputs now interpolate `{UPPERCASE_VAR}` placeholders from the environment (was asking NotebookLM about the literal string `"{WARMUP_TASK_TEXT}"`). Interpolation iterates until fixed-point to resolve wiki-query's two-layer `scenario_query` → scenario template indirection. Precondition script paths are now resolved at contract-load time against the backend skill directory rather than CWD.
- **Shell safety.** `substitute_shell_template` now passes every substituted value through `shlex.quote`, and the three backend `shell:` templates drop their surrounding quotes. Task text with `"`, backticks, or `$(...)` lands as a literal string in the backend rather than breaking the command or triggering host-side shell substitution.
- **Availability probes.** Wiki lane availability only requires `index.md` (schema check dropped — `warmup_scan` never reads it). TaskNotes lane availability keys off `Tasks/` directory existence instead of the task-creation counter file (imports and read-only clones register as available now). NotebookLM config lookup falls through to the project-repo config when the vault-side config is malformed.
- **Evidence pipeline.** Empty-but-present required fields (`[]`, `{}`, `False`) are accepted as valid backend output rather than demoting to Degraded coverage. Component extraction follows spec D3 (first `[A-Z][a-zA-Z0-9]+` run in `task_summary`) instead of a lowercase-first-token heuristic that emitted false-positive high-confidence duplicates on lowercase noun-led requests. Rejection triggers normalize apostrophes on both sides so "won't do" matches. Active-status set for the component-duplicate branch includes `backlog` — fresh `/ark-tasknotes`-created tasks in the same component now surface as duplicates.
- **Table-form index parser.** `warmup_scan` recognises both bullet (`- [[Page]]`) and table (`| [[Page.md\|Title]] |`) forms in `index.md`. Generated Ark vault indices use the table form, so the wiki lane was returning empty matches on every real vault.
- **Python 3.9 compatibility.** Added `from __future__ import annotations` to 4 of 5 affected script files; `executor.py` uses `typing.Optional[X]` (with a documented exception for the Python 3.14 `@dataclass` + `spec_from_file_location` interaction).
- Chains `bugfix.md` Heavy pivot-to-Greenfield now anchors at step 0 so the mandatory warm-up still runs on redesign branches.
- Step 6.5's `ARK_SKILLS_ROOT` snippet matches the canonical three-case resolution in `/ark-context-warmup` (adds the `./.claude-plugin/marketplace.json` repo-local case).

### Migration notes

Chains produced by `/ark-workflow` before 1.12.0 (legacy chain files) still work — `/ark-context-warmup` detects missing extended-contract fields, prompts for task text inline, and logs a warning that cache will be cold. Re-run `/ark-workflow` to regenerate `.ark-workflow/current-chain.md` with the new fields.

## [1.11.0] - 2026-04-12

### Added

- **`/ark-onboard` centralized-vault recommendation.** Greenfield now defaults to an externalized vault at `~/.superset/vaults/<project>/` (or `~/Vaults/<project>/` for non-superset users) with a `vault` symlink into the project repo. Mirrors ArkNode-Poly's production pattern. Includes:
  - New Greenfield Steps 2a-2d (vault repo init, symlink, automation install, GitHub remote offer).
  - Explicit embedded-vault escape hatch via `| **Vault layout** | embedded (not symlinked) |` row in CLAUDE.md.
  - `$HOME/`-portable `VAULT_TARGET` in the tracked `scripts/setup-vault-symlink.sh` — collaborators' clones are not poisoned with machine-specific paths.
  - Path constraint: vault paths must be under `$HOME` (users with external drives symlink-in).
- **Externalization path.** Projects with an embedded `vault/` directory + no opt-out now route through a plan-file generator that emits `docs/superpowers/plans/YYYY-MM-DD-externalize-vault.md`. The plan has Phase 0 preflight (including `git diff --no-index` sibling comparison + empty-dir shape check), Phase 1 destructive main-repo steps, Phase 2 per-sibling worktree conversion, Phase 3 manual follow-ups.
- **Repair additions.** Centralized-vault-specific repairs for broken symlink, symlink-drift (readlink vs script VAULT_TARGET), missing canonical script (with backfill from readlink), and missing post-checkout hook.
- **Check #20 — vault-externalized (warn-only, Standard tier).** Exhaustive status matrix across symlink/real-dir/missing × script-present/absent × opt-out. Never fails — embedded vaults still qualify as Healthy when opt-out is explicit.
- Downstream skill notes in `/notebooklm-vault` (sync-state location), `/wiki-update` (hostname-prefixed session logs), `/codebase-maintenance` (vault-repo commit target), `/ark-workflow` (advisory surfacing).

### Changed

- **Healthy-classification rule relaxed** in both `/ark-onboard` and `/ark-health`: was "all Critical + Standard pass," now "no Critical or Standard fail (warn is OK)." Allows warn-returning checks (10 index staleness, 20 vault-externalized) to surface as advisory without demoting tier.
- **Total diagnostic checks: 19 → 20.**

### Design notes

Spec: `docs/superpowers/specs/2026-04-12-ark-onboard-centralized-vault-design.md` (commit `dd80baa`, revision 4, codex round-4 PASS).

## [1.10.1] - 2026-04-12

### Corrected

v1.10.0's framing overstated the hook-registration problem. Correction:

- **Claude Code merges hook arrays from global `~/.claude/settings.json` and project-local
  `.claude/settings.json`** — it does NOT shadow. The Stop hook registered in `~/.claude/settings.json`
  was firing for `ArkNode-AI/projects/trading-signal-ai`, `ArkNode-Poly`, and `ark-skills` the
  entire time, despite each project's local `settings.json` containing only `PostToolUse`.
  Evidence: `~/.mempalace/hook_state/mine.log` showed hundreds of hook fires per day for all
  three wings — including fires that happened **before** v1.10.0's `install-hook.sh` runs
  added the project-local registration.
- **The project-local hook installs in v1.10.0 were cosmetic, not functional.** The three
  projects already had the hook firing via the global registration. The installs added
  redundant entries that don't change observable behavior.
- **What v1.10.0 DID correctly fix:** the `threshold-lock` WARN in `/ark-health` Check 16
  caught Poly's real bug — `compile_threshold.json` baseline stuck at 4319 == current, so
  `new_drawers = 0` forever, and auto-compile never fired. That WARN is still valuable and
  unchanged.
- **Why Poly's baseline got stuck** (root cause, previously unexplained in v1.10.0):
  `mempalace mine` dedupes by filename. Claude Code session transcripts are monotonically
  appended (session_id is the filename, content grows over the session lifecycle). Modified
  transcripts get skipped by mine as "already filed", so the drawer count doesn't grow when
  sessions are continued rather than newly started. Poly had mostly continuation sessions,
  so the 4319 baseline went stale. Filed [mempalace#645](https://github.com/MemPalace/mempalace/issues/645#issuecomment-4233459673)
  with the Claude Code repro (existing issue — author already filed a markdown-vault variant).

### Changed

- `/ark-onboard` repair mode: the Check 16 reclassification remains, but the "missing
  project-local registration" scenario is now understood as cosmetic in most cases (hook
  fires via global). The reclassification is still useful for the narrower case where
  neither global nor project-local has the hook — rare but real.
- `/wiki-update` auto-trigger documentation: unchanged. Still accurate.

### What to know going forward

1. If `/ark-health` Check 16 WARNs on `threshold-lock`, that's a **real** bug — the auto-compile
   will never fire until the baseline moves. Fix: run `/claude-history-ingest compile` to
   re-anchor, or lower the baseline manually.
2. If Check 16 FAILs on "hook registered" but mempalace is firing (check `mine.log`),
   investigate whether you actually need project-local registration. Usually the global
   registration is sufficient.
3. Long-running Claude sessions don't add drawers via `mempalace mine` until new session
   files are created. Start fresh sessions periodically, or wait for `mempalace --refresh`
   (tracked upstream at [#645](https://github.com/MemPalace/mempalace/issues/645)).

## [1.10.0] - 2026-04-12

### Fixed
- **MemPalace auto-hook now detects silent-failure modes in `/ark-health` Check 16.**
  The hook was installed globally (`~/.claude/settings.json`) but project-local
  `.claude/settings.json` files shadow the global for that project, so projects
  like `ArkNode-AI/projects/trading-signal-ai` and `ArkNode-Poly` were silently
  running without session auto-indexing or the 50-drawer auto-compile trigger.
  Check 16 previously only verified that the hook was registered; it now catches
  three additional drift modes as WARNs:
  - **Wing-mismatch** — `mempalace status` has no wing matching the PWD-derived key.
  - **Threshold-staleness** — `new_drawers >= 200` (way past the 50-threshold) but no compile has fired.
  - **Threshold-lock** — `current_drawers == drawers_at_last_compile` and baseline > 500 (stuck state).
  Wing-match uses `grep -Fxq --` to avoid treating wing keys (which start with `-`) as flag arguments.

### Changed
- **`/ark-onboard` repair mode reclassifies Check 16 as Standard failure** when
  mempalace + vault wing are present but the hook is unregistered — this is the
  missing-glue case, and it's now auto-fixed in Step 3 rather than being hidden
  under "Available upgrades". Added a new **Step 3b: Warnings (interactive review)**
  that presents Check 16's three WARN sub-conditions with fix-now / skip / explain
  options (threshold-lock and wing-mismatch need human judgment, so they are
  never auto-applied).
- **`/wiki-update`** now documents its relationship to the 50-drawer auto-compile
  trigger — clarifies that `compile_threshold.json` is owned by `/claude-history-ingest compile`,
  and that manual `/wiki-update` runs after a compile do not affect the next auto-fire.

### Context
Discovered while debugging why `ArkNode-AI/trading-signal-ai` and `ArkNode-Poly`
were not firing the 50-conversation auto-hook despite the global hook being
installed. Root cause: project-local `settings.json` shadows global, and neither
project registered the Stop hook. Both projects were fixed by running
`install-hook.sh` from each CWD; ark-health/ark-onboard were hardened so this
silent-failure class is detected and repair-able going forward.

## [1.9.0] - 2026-04-12

### Fixed
- **`/notebooklm-vault` sync no longer accumulates ghost source registrations.**
  `notebooklm-py`'s `add_file()` is a 3-step pipeline (register → start-upload →
  stream); if step 2 or 3 fails, a ghost source is registered on the server but
  not tracked locally, so the next run re-registers it. This caused
  `linear-updater`'s notebooks to hit the 300-source cap with ~332 duplicates
  between them. The same bug class applied to the plugin's
  `skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh` (verified by direct
  code reading). Ported the fix from `linear-updater`:
  - **Notebook-authoritative existence.** Each incremental run lists remote
    sources once per notebook and builds a title→id map; existence is checked
    against the remote, not against local state. `sync-state.json` is now a
    hash cache only.
  - **Dedupe-and-heal pass on every incremental run.** Groups sources by title;
    keeps survivor (READY > PROCESSING > ERROR, tiebreak oldest `created_at`),
    deletes the rest. Orphan-prunes `.md` titles not present in the vault
    (preserves non-`.md` sources like manually-added PDFs).
  - **Ghost registration recovery.** Snapshots per-title source IDs before each
    `notebooklm source add`. On any failure, re-lists and diffs against the
    snapshot; if exactly one new source appeared, claims it instead of retrying
    (which would create a duplicate).
  - **Collision detection (fail-loud).** Two vault files with the same basename
    routed to the same notebook would silently overwrite each other (NotebookLM
    titles by basename only). Script now fails with a clear error listing the
    conflicting paths.
  - **State-delete verification.** The state-driven deletion pass now verifies
    a source is actually gone (re-list check) before clearing local state on
    delete failure, preventing orphan leaks.
  - **Per-vault concurrency lock.** `mkdir`-based lock at
    `/tmp/notebooklm-vault-sync.<vault>.lock` serializes concurrent runs. Stale
    locks from crashed runs are detected via PID and removed automatically.
    Portable (no `flock` dependency — works on macOS out of the box).
  - **Cleanup trap surfaces flush failures** instead of silencing them.
- Latent exclusion bug: `TaskNotes/` and `_meta/` now included in the default
  excludes list for standalone vaults (previously only filtered for wrapped
  vaults via subdir discovery). TaskNotes were never meant to sync to NotebookLM.
- Empty notebook id in `.notebooklm/config.json` now fails with a clear
  "Run '/notebooklm-vault setup'" message instead of an opaque
  `notebooklm source list` error.

### Changed
- `/notebooklm-vault` SKILL.md: new `## Sync Behavior` section documenting the
  four modes (incremental, `--sessions-only`, `--file`, `--full`), ghost
  recovery, and troubleshooting. Updated the "Periodic sync is owned by the
  scheduled sync service" warning — local runs are now safe, since the script
  self-heals drift rather than creating duplicates.

## [1.8.0] - 2026-04-10

### Changed
- **`/wiki-update` is now the single end-of-session workflow.** Previously a
  5-step knowledge-sync-and-index skill, it now runs a 6-step flow that creates
  or updates the session log, updates linked TaskNote epic/stories, extracts
  compiled insights from the session log content, regenerates `index.md`, and
  commits. Includes skip detection for ad-hoc docs syncs (preserves backward
  compat for narrow invocations with no git changes since the last session log).
- Session log frontmatter schema merged: `vault/_Templates/Session-Template.md`
  now uses `title` (with session number), `type: session-log`, `summary`,
  `session` (with `S` prefix), `status`, `date`, `prev`, `epic`, `source-tasks`,
  `created`, `last-updated`. The template's prior `title: "Session: {TITLE}"`
  (missing the session number) is fixed. `vault/_meta/vault-schema.md` type-specific
  fields row updated to document `date` and `status`.
- `skills/ark-workflow/` — Hygiene chains previously ended with `/wiki-update
  (if vault) + session log`. The `+ session log` suffix is dropped in the
  progressive-disclosure chain files because session log creation is now
  implicit in `/wiki-update`.
- `CLAUDE.md` (plugin) — `/wiki-update` and `/notebooklm-vault` skill descriptions
  updated to reflect the new split of responsibility.

### Removed
- **`/notebooklm-vault session-handoff` sub-command removed.** Its session log
  write, TaskNote epic/stories update, and sync-notify logic moved into
  `/wiki-update` (Step 2 + Step 3). `/notebooklm-vault` is now focused purely on
  NotebookLM query/sync concerns: `setup`, `ask`, `session-continue`, `bootstrap`,
  `audio`, `report`, `conflict-check`, `status`. The skill description and README
  sub-command list were updated accordingly. Any existing invocation using
  `wrap up`, `end session`, `hand off`, or `session log` triggers now routes to
  `/wiki-update`. Schema mismatch between the old session-handoff writes and the
  Session-Template (latent bug — old format omitted `title` and `summary`, which
  the vault index generator treats as canonical) is resolved by the merged schema.

### Known Issues (deferred)
- Existing session logs in `vault/Session-Logs/` (S001, S002×2, S003, S004) lack
  the new `date` and `status` fields. They still parse cleanly against
  `_meta/generate-index.py` (defaults via `.get()`), so no migration is strictly
  required. A follow-up PR should backfill them and resolve the pre-existing
  `S002` numbering collision (`S002-Ark-Workflow-Skill.md` vs
  `S002-Vault-Retrieval-Tiers-Phase1.md` both use session number 2).

## [1.7.0] - 2026-04-10

### Changed
- **ark-workflow**: Progressive-disclosure split of the monolithic router
  - Main `SKILL.md`: 858 → 270 lines (68.5%)
  - Common-path context load (router + one chain file): 858 → ~313 lines avg (63.5%); worst case (Greenfield) 858 → 334 lines (61.1%); best case (Ship) 858 → 280 lines (67.4%)
  - Chain variants moved to `chains/{scenario}.md` (7 files: greenfield, bugfix, ship, knowledge-capture, hygiene, migration, performance)
  - Pay-per-use content moved to `references/{batch-triage,continuity,troubleshooting,routing-template}.md`
  - Behavioral parity: all 22 v2 gaps preserved, all 19 chain variants preserved, 10 `/test-driven-development` references preserved in chains/ (2 baseline references at SKILL.md L282 and L751 were intentionally dropped by Phase 3 — slimmed Step 6.5 and removed example block), 0 `/TDD` references
  - File count in `skills/ark-workflow/`: 1 → 12
  - Total repo footprint: 858 → 833 lines (−25 net — the progressive-disclosure split is a net shrink on disk AND a major context-load win)
  - Dropped the Condition Resolution "Example resolved output" block (14 lines, illustrative only)

## [1.6.0] - 2026-04-09

### Changed
- **ark-workflow**: Major rewrite of the task triage skill addressing 22 gaps (12 initial + 10 from Codex review)
  - Expanded from 5 to 7 scenarios: added Migration and Performance as first-class scenarios
  - Replaced factor-matrix triage with risk-primary + decision-density escalation (Heavy risk stays Heavy; architecture decisions escalate Light → Heavy)
  - Added Batch Triage for multi-item prompts with root cause consolidation, dependency heuristics, and per-group execution plans
  - Added Continuity mechanism: TodoWrite tasks + `.ark-workflow/current-chain.md` state file for in-session and cross-session chain tracking, with handoff markers, stale-chain detection, and context recovery after compaction
  - Added Hygiene Audit-Only variant for assessment-only requests (no implementation/ship forced)
  - Split security routing into Audit and Hardening paths, with `/cso` dedup rule (`/cso` runs exactly once per chain)
  - Added `/investigate` as conditional step in Hygiene chains for bug-like items
  - Added session handoff guidance for Heavy Bugfix, Hygiene, Migration, and Performance
  - Added scenario-shift re-triage handling with pivot examples
  - Fixed `/TDD` naming to `/test-driven-development` across all chains
  - Rewrote Routing Rules Template with session-resume block and new-task triggers for 7 scenarios

### Fixed
- ark-workflow: removed unreliable "10 tool calls since last file read" handoff trigger (output quality signals replace it)
- ark-workflow: Knowledge Capture now has Light/Full split instead of one-size-fits-all chain

## [1.5.0] - 2026-04-09

### Added
- `/ark-tasknotes status` subcommand — task overview dashboard with opinionated triage
  recommendations. Shows status counts, active work, stale/blocked items, velocity pulse,
  recently completed tasks, and a prioritized "what to work on next" work plan.
  Uses MCP tools when Obsidian is running, falls back to direct markdown reads.
- Skill restructured with Modes section (Create and Status) for extensibility.

## [1.4.2] - 2026-04-09

### Fixed
- `/ark-onboard` and `/ark-health`: TaskNotes MCP config now uses built-in HTTP transport
  (`type: http`, `url: http://localhost:{apiPort}/mcp`) instead of nonexistent `tasknotes-mcp`
  npm package. Removed `enableAPI` from TaskNotes `data.json` template (not a real setting).

## [1.4.1] - 2026-04-09

### Changed
- `/ark-onboard` Step 11 now downloads Obsidian plugin binaries (TaskNotes, Obsidian Git)
  directly from GitHub releases via the community-plugins.json registry. Falls back to
  reference vault copy, then manual GUI install as last resort.
- `/ark-onboard` Step 12 generates full `data.json` configs for both plugins — TaskNotes
  gets Ark-specific folder paths, custom statuses, field mappings, and Bases view bindings;
  Obsidian Git gets auto-save/pull/push intervals and merge strategy. No GUI configuration
  required.
- Repair path check 12 fix updated to use GitHub download instead of manual install.

## [1.4.0] - 2026-04-08

### Added
- `/ark-onboard` — interactive setup wizard for new Ark projects. Handles greenfield,
  non-Ark vault migration, partial repair, and health reporting. Absorbs `/wiki-setup`
  as the recommended entry point. Supports Quick, Standard, and Full setup tiers.
- `/ark-health` — diagnostic check for Ark ecosystem health. Runs 19 checks across
  plugins, CLAUDE.md fields, vault structure, and integrations. Produces a scored
  scorecard with actionable fix instructions.

## [1.3.0] - 2026-04-08

### Added
- `/ark-workflow` skill — task triage and skill chain orchestration. Entry point for all
  non-trivial work. Detects scenario (greenfield, bugfix, ship, knowledge capture, hygiene),
  classifies weight (light/medium/heavy) with risk as primary signal, and outputs the
  optimal ordered skill chain with project-specific conditions resolved.
- Routing rules template for project CLAUDE.md auto-triggering

## [1.2.0] - 2026-04-08

### Added
- Multi-backend vault retrieval tiers for `/wiki-query`: T1 (NotebookLM), T2 (MemPalace),
  T3 (Obsidian-CLI), T4 (index.md scan). Routes queries by type with automatic fallback.
- `skills/shared/mine-vault.sh` — one-time helper to index vault .md files into MemPalace.
  Accepts vault path argument, detects symlink vs real dir, derives wing name.
- Vault Retrieval Defaults section in CLAUDE.md: tier table, availability checks,
  failure messaging, and 7-rule query routing guide.
- Optional dependency table in README (MemPalace, NotebookLM CLI, Obsidian CLI).

### Changed
- `wiki-query` SKILL.md rewritten: query classification (factual, synthesis, gap, search,
  browse), tier availability check, per-type routing, T4 fallback guard, CONVO_WING for
  shared vaults. Old Tier 1/2/3 renamed to Step 3a/3b/3c within T4.
- README Vault Maintenance section updated for multi-backend language scoped to wiki-query (Phase 1).

## [1.1.2] - 2026-04-08

### Fixed
- SKILL.md index mode now explicitly states to mine the project root directory only,
  preventing errors from attempting to mine subdirectories like `memory/`

## [1.1.1] - 2026-04-08

### Fixed
- Stop hook now registers in per-project `.claude/settings.json` instead of global settings.
  The hook only fires in projects that explicitly run the installer.

## [1.1.0] - 2026-04-08

### Changed
- `claude-history-ingest` skill rewritten to use MemPalace (ChromaDB) for indexing and retrieval.
  Auto-indexes sessions via Stop hook (zero LLM tokens). Compiles insights via semantic search
  (~10K tokens vs 100-200K previously). Three modes: index, compile, full.
  Requires `pip install mempalace`.

### Added
- `skills/claude-history-ingest/hooks/ark-history-hook.sh` — Stop hook for auto-indexing
- `skills/claude-history-ingest/hooks/install-hook.sh` — One-time setup helper

### Fixed
- Path encoding now matches Claude Code's convention (replaces both `/` and `.` with `-`)
- Installer updates existing hook to latest version instead of silently skipping

## [1.0.2.0] - 2026-04-08

### Changed
- `claude-history-ingest` skill now scopes to current project's Claude directory instead of scanning all projects

## [1.0.1.0] - 2026-04-08

### Added
- Ark vault for this repo (`vault/`) with standard structure, templates, metadata, and task tracking
- Obsidian configuration with TaskNotes (v4.5.1) and Obsidian Git plugins pre-installed
- NotebookLM config template (`.notebooklm/config.json`) with placeholder notebook ID
- Project Configuration section in CLAUDE.md for context-discovery

### Changed
- wiki-setup skill now includes Obsidian plugin installation (Steps 8-9), NotebookLM config (Step 10), and expanded post-setup checklist
- Onboarding guide rewritten with full CLAUDE.md template, three layout examples (standalone, separate repo, monorepo), plugin documentation, and NotebookLM config reference

## [1.0.0.0] - 2026-04-08

### Added
- Claude Code plugin manifest (`.claude-plugin/plugin.json`, `marketplace.json`) for installation via `/plugin marketplace add`
- 14 shared skills: ark-code-review, ark-tasknotes, codebase-maintenance, notebooklm-vault, wiki-query, wiki-status, wiki-update, wiki-lint, wiki-setup, wiki-ingest, tag-taxonomy, cross-linker, claude-history-ingest, data-ingest
- Context-discovery pattern: all skills read project CLAUDE.md at runtime instead of hardcoding paths
- Vault restructure artifacts (summary frontmatter, index.md, vault-schema, tag-taxonomy) in both AI and Poly vault submodules
- NotebookLM vault sync script with incremental change detection
- Onboarding guide for new projects
- Comprehensive README with installation instructions and skill reference

### Fixed
- Shell script function ordering: `die()` and `jq` prereq check moved before first usage in vault sync script
