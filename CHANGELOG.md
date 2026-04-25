# Changelog

All notable changes to this project will be documented in this file.

## [1.22.1] - 2026-04-25

### Fixed

- **`/notebooklm-vault` sync fails on centralized + standalone vault layouts.** Three independent bugs in `skills/notebooklm-vault/scripts/notebooklm-vault-sync.sh` that combined to make a fresh `/ark-onboard` Standalone Full-tier project unable to upload sources on the first `/notebooklm-vault setup`:
  - **Bug 1 — `find` did not traverse the vault symlink.** `build_vault_file_list` ran `find "$scan_base" -name "*.md" -type f` against a symlink path. macOS BSD find (and GNU find on Linux) does not descend into symlinked directories without `-L`, so discovery returned 0 files and sync exited cleanly with `Added: 0`. Fixed by adding `-L`.
  - **Bug 2 — `notebooklm source list ... --json 2>&1` corrupted the JSON piped to `jq`.** notebooklm-py v0.3.3 logs a runtime warning to stderr on empty notebooks (`Sources data for <id> is not a list (type=NoneType)`). With `2>&1`, that timestamped warning landed at the start of the captured buffer and `jq` failed parsing at the timestamp's `:`. Fixed at both occurrences (`fetch_notebook_sources` and the `dedupe_and_heal_notebook` refresh) by capturing stderr to a tempfile and only surfacing it on non-zero exit. Other source-list call sites in the same script already used the safer `2>/dev/null` pattern.
  - **Bug 3 — `resolve_scan_base` mis-routed standalone vaults that hit the `vault_root: "vault"` config branch.** A centralized + standalone project's project-level config carries `vault_root: "vault"` (it has to — the config lives in the project repo, the vault sits across a symlink). The script took the string at face value and walked for a wrapping project subdirectory. Standalone vaults have no such subdirectory, so the script landed on the first non-excluded subdirectory — `Session-Logs/` on a fresh Ark vault, which is empty. Sync ran to completion with a misleading `WARN: No files discovered in <vault>/Session-Logs`.

### Changed

- **`/notebooklm-vault` setup step 4 now branches on layout.** Previously wrote a project-level `.notebooklm/config.json` with `vault_root: "vault"` unconditionally — fine for monorepo layouts but redundant (and historically the source of the Bug 3 misconfig) for standalone vaults. Setup now detects layout via marker-dir signal: for standalone, it fills in the existing vault-side config (already written by `/ark-onboard` Step 15) and skips creating a project-level config; for monorepo, it writes the project-level config as before. Narrative across `Project Discovery`, `Architecture`, `Centralized Vault Awareness`, and `Important Notes` sections updated to qualify "tracked, authoritative" by layout.
- **`/ark-onboard` layout diagram annotated.** The project-repo `.notebooklm/config.json` row in the centralized-vault layout diagram now marks itself as monorepo-only and notes that standalone vaults rely solely on the vault-side config.

### Refactored

- **Single layout classifier in `notebooklm-vault-sync.sh`.** Closes the architectural follow-up that the bug-fix portion above flagged. Introduces a `VAULT_LAYOUT` enum (`STANDALONE_DIRECT | STANDALONE_CENTRALIZED | WRAPPED`) computed once at script load by `classify_vault_layout()`. `resolve_scan_base` now switches on the enum instead of re-deriving from `VAULT_ROOT_REL` plus structural marker checks at every call site. The `is_standalone_vault` helper introduced earlier in this release is retired — its body is the classifier's middle branch. The startup banner now prints `Layout:` so the classifier's verdict is visible in any debug session — historically this matrix drifted silently from what `/ark-onboard` and `/notebooklm-vault setup` write, so making it loud is part of the fix.

### Notes

- This is the third round of "symlinks + standalone layout" fixes in `notebooklm-vault-sync.sh` (after `a30dbbb` and `172fc39`). Recurring bugs in the same file family are an architectural smell — handled in the same release by consolidating the layout matrix into a single classifier (above). Compiled insight at `vault/Compiled-Insights/Vault-Layout-Detection-Structural-vs-Config.md` captures the pattern.
- Behavior-preserving classifier verified across all three layouts: `STANDALONE_CENTRALIZED` on the live `ark-trade-agent` vault with synthetic `vault_root: "vault"` config; `STANDALONE_DIRECT` on the vault-side config with `vault_root: "."`; `WRAPPED` on a synthetic monorepo vault where markers nest inside a project subdirectory. `bash -n` clean.
- Sister script `skills/shared/mine-vault.sh` was checked and does not need the same treatment — it reads `VAULT_PATH` from CLAUDE.md and scans wholesale via `find -L`, never branching on layout.
- Verification gap: end-to-end success against a live `/ark-onboard` + `/notebooklm-vault setup` against a fresh standalone project requires interactive NotebookLM auth and was not exercised in this release. Mechanical repros (find symlink: 0 → 11 files; marker detection on the live ark-trade-agent vault returns true; `resolve_scan_base` with synthetic broken state lands on vault root and EXCLUDES filter leaves exactly `00-Home.md` + `index.md`) are the verification evidence.

## [1.22.0] - 2026-04-24

### Added

- **`Arkskill-012-S2`: external skills registry.** New `skills/ark-workflow/references/external-skills.yaml` enumerates the 33 external slash-commands referenced from `skills/ark-workflow/chains/*.md` (gstack, OMC, superpowers, vendor-cli) with their condition gates. Mandatory dependency for the chain-reachability lint added in S3.
- **`Arkskill-012-S3`: skill-graph audit mode for `/wiki-lint`.** New `skills/wiki-lint/scripts/skill_graph_audit.py` runs six checks on the plugin repo:
  1. **Catalog drift** — HARD error on count mismatch between filesystem ground truth and the parsed catalogs in `skills/AGENTS.md`, `README.md`, and `CLAUDE.md`; WARN on description divergence.
  2. **Section-anchor refs** — verifies `references/<file>.md § Section X.Y` cites resolve under the dual `## Section N` / `### N.M` heading scheme used in this repo.
  3. **Description shape** — heuristic warns on length, missing trigger verbs, or high cross-skill description overlap. Not a phrase-match for "Use when / Do NOT use" — three canonical atom skills don't have those phrases and are correct.
  4. **Active-body length** — informational warn at 500 lines (Anthropic guidance). Does not auto-trigger refactor; load-bearing sections in `/ark-workflow`, `/ark-onboard`, `/ark-health` cannot move into `references/`.
  5. **Chain reachability** — extracts leading-token slash-commands from chain backtick spans (so `/ark-code-review --quick` resolves to `/ark-code-review`); cross-checks against internal SKILL.md set ∪ external registry. Warns on unclassified.
  6. **Compound-to-compound calls** — soft warn only. Per the design doc, live examples in this repo are correct; the lint is informational, not a block.
- **`Arkskill-012-S4`: composition guardrails text in `skills/AGENTS.md`.** New `### Composition Guardrails` subsection adopting the exception-aware wording from the epic. Replaces the rejected v2 wording ("Compounds do not invoke other compounds"); the "molecules sequence atoms" tier sentence was never in the codebase to begin with and stays out — `/ark-context-warmup` is a molecule-shaped prelude that runs as step 0 of every chain, so the sentence would be technically false.

### Notes

- **`Arkskill-012-S5` had no work to do.** Section-anchor lint surfaced zero broken refs after the dual-scheme resolver landed — the design doc's suspicion that `omc-integration.md § Section 4.1` was silently broken was based on a literal-string grep that didn't account for the `### 4.1 ...` sub-numbering. The existing cites are valid.
- Final audit state: 0 errors, 36 soft warnings (3 description-drift, 1 description-shape, 3 active-body-length, 29 compound-to-compound). All 36 are expected — they document known signal that the epic explicitly classified as soft.
- Design rationale and `/codex` consult+challenge transcripts: `vault/Compiled-Insights/Skill-Graph-Hardening-Pass.md`. Epic + stories: `vault/TaskNotes/Tasks/Epic/Arkskill-012-skill-graph-hardening-pass.md`.

## [1.21.5] - 2026-04-24

### Fixed

- **Catalog drift surfaced by `/codex` challenge.** Three skill catalogs disagreed on counts and contents:
  - `README.md` claimed 19 skills (lines 3, 132, 151, 176–177); now 20. Added `/wiki-handoff` row to the Available Skills table.
  - `skills/AGENTS.md` claimed 18 skills; now 20. Added `ark-update/` and `wiki-handoff/` rows. `/ark-health` description corrected from "19-check" to "22-check" (matches `ark-health/SKILL.md` and `ark-onboard/SKILL.md`).
  - `CLAUDE.md` Available Skills section was missing `/ark-update` and `/wiki-handoff`; `/ark-health` line claimed "20 checks" instead of 22. Both corrected.
- Filesystem ground truth: `find skills -maxdepth 2 -name SKILL.md` returns 20.

### Notes

- Documentation-only patch. No skill behavior changes.
- Catalog-drift lint (and the broader skill-graph hardening pass it belongs to) is tracked under `Arkskill-012`. See `vault/Compiled-Insights/Skill-Graph-Hardening-Pass.md` for the design rationale, including the `/codex` consult+challenge transcript that drove this v3 plan.

## [1.21.4] - 2026-04-23

### Fixed

- **Cross-wing mine mutex now PID-aware, not age-only.** The v1.21.1 mutex in `skills/claude-history-ingest/hooks/ark-history-hook.sh` used a 10-minute mtime check to recover stale locks — but a legitimate `mempalace mine` running past 10 minutes could have its live lock wiped by a later session, reopening the exact HNSW write race the release closes. Replaced with an `acquire_lock()` helper that writes the holder PID into the lock dir; contenders check `kill -0 $pid` first and only fall back to age-based cleanup when the PID file is missing. Applied to both the per-wing lock (`$STATE_DIR/$WING.lock`) and the palace-global lock (`~/.mempalace/palace/.ark-global-mine-mutex`).
- **Portable `stat` across macOS + Linux.** The hook and `/ark-health` Check 14d used `stat -f %m` (BSD mtime), which on GNU/Linux is filesystem-format info, not file-mtime — silent mis-probe for Linux users. New `mtime()` / `_mtime()` helper tries BSD form first, falls back to GNU `stat -c %Y`.
- **Check 14d warn text now points at real evidence.** The probe previously discarded stderr with `2>/dev/null` while the warn message told users to "inspect `/tmp/mempalace-mcp-last.log`" — a log that didn't exist. Probe now appends stderr to the log so the diagnostic pointer is actually actionable.
- **Step 13b shim writer hardened.** Refuses to write when `~/.local/bin/mempalace-mcp` is a pre-existing symlink (cat `>` follows symlinks and would clobber the target). Write is now atomic via tempfile + `mv`. Generated shim quotes the interpreter path (`exec "$MEMPALACE_VENV_PYTHON"`) so pipx env paths with spaces don't break it.

### Changed

- **Step 13b prompt simplified from [Y/n/c] to [Y/n].** The [C] ("CLI stays, skip plugin") option was redundant — same user-visible outcome as [N], and [C] being non-standard (usually means Cancel) was a UX trap. [N] helptext now clarifies that CLI install from Step 13 stays in place.

### Notes

- All four fixes caught by a /ccg tri-model review (Codex + Gemini) run pre-push. Zero downstream-user behavior changes if the issues never triggered — but on Linux, under long-mine workloads, or with pre-existing `~/.local/bin/mempalace-mcp` symlinks, the pre-v1.21.4 code had real failure modes.
- Deferred from this release: relocating the new Check 14a/14b/14c/14d/16b bash blocks into `references/check-implementations.md` to honor the v1.21.0 Shrink-to-Core direction. Tracked as Arkskill-011.

## [1.21.3] - 2026-04-23

### Fixed

- **`/ark-health` Check 16b path-resolver bug.** The shell glob `~/.claude/plugins/cache/ark-skills/ark-skills/*/skills/...` returns matches in **alphabetical** order, not version order — `1.16.0` sorts before `1.20.0` and `1.21.x`. The original `for candidate ... break` loop picked the first match, which on any system that has accumulated multiple cached plugin versions resolved to the OLDEST copy. That defeats the check's purpose: the installed hook can match an older cached copy (because the older copy happened to be byte-identical to what was installed at the time) while genuinely being stale relative to the live plugin. Caught pre-push by running the bash directly against the live cache (six versions present: 1.16.0 through 1.21.0). Fix: pipe the glob through `sort -V | tail -1` to pick the highest version. Fallback chain to legacy single-version cache layout + dev-mode CWD preserved.

## [1.21.2] - 2026-04-23

### Added

- **`/ark-health` Check 16b — History hook content drift.** Detects when `~/.claude/hooks/ark-history-hook.sh` (the installed copy) diverges from the plugin's current version. Plugin upgrades don't overwrite files under `~/.claude/hooks/`, so a user who installed the hook at v1.20.x and upgraded to v1.21.1 is missing the cross-wing mutex and still exposed to the HNSW write race v1.21.1 closes. The check runs `cmp -s` against the plugin cache's current copy and warns with the `install-hook.sh` re-run action. Skipped when Check 16 fails (no hook installed).

### Notes

- **Why not `/ark-update`?** Per the existing `target-profile.yaml` convention ("hooks are `/ark-onboard repair` territory, not `/ark-update`"), hook drift is detected by `/ark-health` and fixed by re-running `install-hook.sh`. Adding a Phase 1 destructive migration to /ark-update would contradict that rule.
- **Paired with:** `/ark-onboard` Integrations checklist gains row 16b for completeness.

## [1.21.1] - 2026-04-23

**T2 MCP-first via the MemPalace Claude Code plugin, layered onto the v1.21.0 Shrink-to-Core slim.** Consolidates three internal patches (T2 plugin install + CCG-review correctness fixes + cross-wing race fix) into one release, since the underlying intent was always one logical change. Adopts the v1.21.0 references/ structure — new bash stays inline alongside the existing checks rather than expanding the references files.

### Added

- **`/ark-onboard` Step 13b — MemPalace Claude Code plugin install (Greenfield, optional but recommended).** Authors `~/.local/bin/mempalace-mcp` shim (plugin's bundled `.mcp.json` declares command `mempalace-mcp` but the pip package ships the server as `python -m mempalace.mcp_server`), validates `~/.local/bin` is on PATH, hard-fails if the pipx venv python is missing rather than falling back to system python3 (unsafe). [Y/n/c] prompt: Y installs plugin + shim, N skips entirely, C keeps CLI but skips plugin.
- **`/ark-health` Check 14a — MemPalace plugin installed (user scope).** Block-aware awk parse of `claude plugin list` (scoped to the `mempalace@` block to avoid false-PASS when a different plugin is the user-scope/enabled one). Returns `warn`.
- **`/ark-health` Check 14b — MemPalace MCP server responds.** Two probes: `claude mcp list` for plugin-registered MCP, fallback shim handshake via `perl -e 'alarm 5; exec @ARGV'` (portable timeout — `timeout`/`gtimeout` aren't on stock macOS). Returns `warn`.
- **`/ark-health` Check 14c — MemPalace hook state (informational).** JSON-aware Python parse of `.hooks.Stop` and `.hooks.PreCompact` in cached `hooks.json` — never warns, always passes, just reports state A (neutralized) vs state B (active). New `>>` symbol in the scorecard for state-display checks.
- **`/ark-health` Check 14d — MemPalace palace read sanity.** Exercises the HNSW read path via a real `mempalace_search` through the shim. On crash, detects HNSW/SQLite drift signature ([#1000](https://github.com/MemPalace/mempalace/pull/1000)) and surfaces the `quarantine_stale_hnsw()` recovery one-liner. Returns `warn`. Retire when upstream [#1062](https://github.com/MemPalace/mempalace/pull/1062) lands.
- **Cross-wing mine mutex** in `skills/claude-history-ingest/hooks/ark-history-hook.sh`. Non-blocking mkdir on `~/.mempalace/palace/.ark-global-mine-mutex`; if another wing's `mempalace mine` is running, skip this session and log. Stale-lock recovery at 10 min. Closes the cross-wing concurrent-writer race that produced 38k-drawer palace corruption (the in-repo per-wing lock didn't cover it; upstream [#1023](https://github.com/MemPalace/mempalace/pull/1023) PID guard and [#784](https://github.com/MemPalace/mempalace/pull/784) per-source-file lock don't cover it either). Retire when upstream [#976](https://github.com/MemPalace/mempalace/pull/976) (HNSW thread-safety) lands.

### Changed

- **`/ark-onboard` Step 13 pins Python 3.13 + chromadb 1.5.7.** Python 3.14's ABI shifts hit a chromadb cp39-abi3 wheel SIGSEGV in MCP vector query ([#1109](https://github.com/MemPalace/mempalace/issues/1109)); chromadb 1.5.8 introduced a vector-query regression and concurrent-writer corruption risk ([#1092](https://github.com/MemPalace/mempalace/issues/1092) / [#1132](https://github.com/MemPalace/mempalace/issues/1132)). Step 13 now: preflights `pipx` and `python3.13` (auto-installs via Homebrew on macOS), reads existing install's interpreter from the venv directly (NOT `pipx list --short`, which shows the package version, not the interpreter), gates `MEMPALACE_OK=true` on exit code from each branch, and pins chromadb to 1.5.7 via `pipx runpip mempalace install`.
- **`/ark-onboard` Integrations checklist** gains rows 14a/14b/14c/14d under existing row 14, with the skip rule "checks 14b/14c/14d skip if 14a failed."
- **`/ark-health` tier policy** updated to enumerate warn-returning checks (10, 14a, 14b, 14d, 20, 22) and informational checks (14c) explicitly. Added `>>` symbol to the result table and output-format rules.
- **CLAUDE.md T2 retrieval block.** MCP for reads, CLI for ingest only. CLI search fallback dropped — `mempalace search` segfaults in `chromadb/api/rust.py:_query` upstream ([#1092](https://github.com/MemPalace/mempalace/issues/1092) / [#1132](https://github.com/MemPalace/mempalace/issues/1132)) and `mempalace status` hits SQLite's 32k-variable limit on palaces past ~32k drawers ([#802](https://github.com/MemPalace/mempalace/issues/802)). If MCP is unreachable, skip T2 entirely.

### Notes

- v1.20.1, v1.20.2, v1.20.3 were never published — they exist only as ancestor commits to this release. The three corrections collapsed into one consolidated entry above (the v1.20.x series is summarized in the commit message).
- **Defense-in-depth, not corruption-prevention.** mempalace 3.3.2's #1023 PID guard + #784 per-file lock make the plugin's auto-save hooks meaningfully safer than at v1.20.1. Neutralizing them is now an opt-in choice (Check 14c) — the cross-wing race is closed at the ark-skills layer by the new mutex.
- **Retire watchpoints.** Check 14d → upstream #1062. Mutex → upstream #976. Re-evaluate the chromadb 1.5.7 pin and Python 3.13 pin once #976 / #991 / #1062 land.

## [1.21.0] - 2026-04-23

**Layer 3 Shrink-to-Core audit.** Ships the approved "ark-skills Identity Audit — Shrink to Core" plan (design doc under `~/.gstack/projects/HelloWorldSungin-ark-skills/`, approved 2026-04-22). Cuts Layer 3 SKILL.md verbosity without touching Layer 1 (orchestration) or Layer 2 (vault integration).

### Per-skill outcomes

| Skill | Before | After | Reduction | Disposition |
|-------|-------|-------|-----------|-------------|
| `/ark-health` | 743 | 378 | 49% | SLIM — bash implementations for 9 checks (5, 6, 8, 10, 11, 16, 18, 20, 22) relocated to `references/check-implementations.md` |
| `/codebase-maintenance` | 156 | 156 | — | KEEP — 156 LOC router with 4 ark-specific sub-workflows (chain-invoked in all 4 hygiene variants); no upstream equivalent |
| `/ark-code-review` | 784 | 357 | 54% | SLIM — agent prompts, per-mode report formats, and External Second Opinion framing relocated to 3 reference files; Trust Boundary Notice and operational rules stay inline |
| `/ark-onboard` | 2650 | 1122 | 58% | SLIM — file templates (801 LOC), externalization plan template (215 LOC), state detection bash (130 LOC), plugin install bash (128 LOC), and centralized-vault repair scenarios (142 LOC) relocated to 5 reference files; wizard UX preserved verbatim |

**Aggregate:** 7,707 LOC → 5,388 LOC across all SKILL.md files (**30% reduction** — hits the design-doc stretch target). At-invocation footprint drops proportionally; `references/*.md` load only on demand.

### Rationale revision

The design doc's original slim rationale cited "overlap with OMC `omc-doctor`" (for `/ark-health`) and "wrapper skills routing to upstream" (for Layer 3 generally). Evidence during execution contradicted that framing: `omc-doctor` (211 LOC) covers OMC-specific cache/version/legacy concerns; `/ark-health` covers ark-project concerns — disjoint domains. Similarly, no upstream plugin replicates `/ark-code-review`'s multi-agent fan-out + epic + plan modes, or `/codebase-maintenance`'s code/vault/skills three-phase sweep. The actual slim pattern is **verbosity reduction via load-on-demand references**, not deletion of upstream-delegable content. Ark-specific IP is preserved in full.

### Invocation audit (methodology)

Before slimming, captured three signals across the full `~/.claude/projects/` transcript history and `vault/Session-Logs/`:

- **G1 mentions** (prose + SKILL.md loads + system-reminders): `/ark-workflow` dominates (25k); `/notebooklm-vault` and `/ark-update` next.
- **G2 Skill-tool programmatic invocations**: `/notebooklm-vault` (41) and `/codebase-maintenance` (10) are the true chain workhorses; most L2/L3 skills have 0–2 programmatic fires.
- **G3 session-log authorial mentions**: `/ark-workflow` (45) leads; L3 skills `/ark-onboard` (27), `/ark-health` (21), `/ark-update` (17), `/ark-code-review` (12) are direct-invocation-first (matches the design doc's P1 layered-identity premise).

Captured in the design doc under `## Invocation Audit — 2026-04-23`. Informed audit ordering (Codex-recommended `/ark-health` first, `/ark-onboard` last).

### Verify-then-slim discipline

Every slim commit gated on independent `codex` review before landing. Findings summary:

- **Phase 1 `/ark-health`:** codex clean on first pass (no [P1] / [P2]).
- **Phase 3 `/ark-code-review`:** codex flagged 2 [P2] NITs — missing `--epic` Code Reviewer prompt variant and inaccurate agent-roster mode-applicability column. Both fixed in `e32c198` before proceeding.
- **Phase 4 `/ark-onboard`:** codex flagged 3 [P1]s — reference-pointer integrity (backtick/parenthetical-wrapped headings didn't match literal `§` lookups), Greenfield Step 1 wizard UX regression (compressed prompts), design-bullet/step-marker inconsistency. All fixed in `a2e54dd` before release.

### Deferred (out of scope, explicitly named)

- **L1 chain-manifest decoupling** (design-doc Open Question 10). Per-file churn on `/ark-workflow` (5,131 LOC over 6 weeks) comes from inline chain-resolution referencing upstream plugin names. Externalizing chain manifests from SKILL.md is the right fix — target v1.22.0 or later. Not addressed by this slim.
- **Low-signal L2 candidates** surfaced by the invocation audit (`/wiki-lint`, `/data-ingest`, `/wiki-handoff`, `/tag-taxonomy`, `/cross-linker`, `/wiki-status` at G2=0, low G3). Candidates for a future L2 slim pass — not this audit.

### Added

- **`skills/ark-health/references/check-implementations.md`** (270 LOC) — bash for checks 5, 6, 8, 10, 11, 16, 18, 20, 22.
- **`skills/ark-code-review/references/agent-prompts.md`** (181 + 14 after fix) — 5 agent prompts + 4 mode variants.
- **`skills/ark-code-review/references/report-formats.md`** (230 LOC) — per-mode report skeletons (default / `--full` / `--epic` / `--plan` / `--pr` / `--quick`).
- **`skills/ark-code-review/references/external-second-opinion.md`** (61 LOC) — framing, synthesis detail, cost notice, vendor capacity caveat (trust-boundary operational rules stay inline in SKILL.md).
- **`skills/ark-onboard/references/templates.md`** (801 LOC) — all embedded file templates (shell scripts, Python, markdown, JSON configs).
- **`skills/ark-onboard/references/externalize-vault-plan.md`** (215 LOC) — the 199-LOC externalization plan template for Phase 0–3 / rollback.
- **`skills/ark-onboard/references/state-detection.md`** (130 LOC) — project-state detection bash + flag derivation.
- **`skills/ark-onboard/references/plugin-install.md`** (128 LOC) — 3-tier plugin install fallback bash.
- **`skills/ark-onboard/references/centralized-vault-repair.md`** (142 LOC) — 5 centralized-vault repair scenarios.

### Changed

- `skills/ark-health/SKILL.md` — 743 → 378 LOC.
- `skills/ark-code-review/SKILL.md` — 784 → 357 LOC.
- `skills/ark-onboard/SKILL.md` — 2650 → 1122 LOC.

### Unchanged

- All Layer 1 skills (`/ark-workflow`, `/ark-context-warmup`).
- All Layer 2 skills (vault integration — `/notebooklm-vault`, `/wiki-*`, `/tag-taxonomy`, `/cross-linker`, `/data-ingest`, `/claude-history-ingest`).
- `/codebase-maintenance`, `/ark-tasknotes`, `/ark-update` (KEEP per audit).
- All public contracts preserved: grep contracts (VAULT_TARGET, embedded opt-out), 22-check rubric, tier classifications, scorecard formats, wizard UX prompts, chain invocation points (`--quick` / `--thorough`).

## [1.20.0] - 2026-04-22

Wave 1 of gstack v1.5.1.0 integration (Approach B). Cleanup + wiring; Wave 2 (v1.21.0) ships `/benchmark-models` calibration and data-driven chain-substitution edits.

### Changed

- **`/checkpoint` references renamed to `/context-save`.** 8 stale references across `skills/ark-workflow/` — 1 in SKILL.md, 4 in `references/troubleshooting.md`, 1 each in `chains/hygiene.md`, `chains/bugfix.md`, `chains/greenfield.md`. gstack moved `/checkpoint` to a Claude Code native rewind alias; `/context-save` is the current gstack command. `<checkpoint>` XML tags in `skills/codebase-maintenance/` (different namespace) are unchanged.

### Added

- **Continuous-checkpoint mode wired into Step 6.5 check-off.** Opt-in via gstack config. When `gstack-config get checkpoint_mode` returns `continuous`, each completed chain step drops a WIP commit with a pinned `[gstack-context]` body (Decisions / Remaining / Skill). `git log --grep "WIP:"` now reconstructs chain reasoning across worktrees and clones, which gitignored `.ark-workflow/current-chain.md` cannot. Silent no-op for the default `explicit` mode path. Lock boundary: WIP commits shell out AFTER the chain-file lock releases, no coordination needed. `gstack-config` binary resolver: `GSTACK_CONFIG="${GSTACK_CONFIG:-$HOME/.claude/skills/gstack/bin/gstack-config}"` (NOT on PATH by default). Failure modes — all silent no-ops or warn-and-continue; none block check-off. Full contract table in `skills/ark-workflow/SKILL.md` § Continuous Checkpoint Integration.
- **`/context-save` as compaction-recovery option (d).** Mid-chain menu: `[a/b/c/proceed]` → `[a/b/c/d/proceed]`. Entry menu: `[b/c/proceed]` → `[b/c/d/proceed]`. Option (d) runs `/context-save --no-stage` (lightweight markdown save under `~/.gstack/`; `--no-stage` preserves dirty worktree) then `/compact`. By design, (d) opts OUT of the Wiki-handoff invariant — different contract from (a)/(b) which require vault schema validation. (c)/(d) both skip `/wiki-handoff`: (c) because subagent dispatch preserves parent context, (d) because the whole point is a lighter exit when vault validation is overkill.

### Tests

- **+3 pytest tests** in `test_step_boundary_render.py` covering option (d) rendering in both mid-chain and entry menus, and the new answer-set shape.
- **+9 bats tests** in new `scripts/integration/test_continuous_checkpoint.bats` covering every row of the continuous-checkpoint failure-mode table: continuous/explicit/empty/unexpected modes, missing / non-executable binary, non-git-repo, chain-complete remaining label, commit-failure warn-and-continue.
- **Existing tests updated** for the new menu answer-sets: `test_context_probe.py::TestCliStepBoundary::test_nudge_level_prints_menu`, `test_probe_skill_invocation.bats` entry-menu assertion.
- All 70 pytest + 23 bats pass.

### Out of scope (deferred to v1.21.0)

- `/benchmark-models` calibration run against the 6 `/ccg` substitution points (Greenfield / Migration / Performance Heavy plan + spec reviews).
- Data-driven revision of substitution rules in `chains/*`.

## [1.19.1] - 2026-04-20

Bugfix release addressing `/ark-code-review --thorough` findings against v1.19.0. 2 Critical + 8 High + related Mediums. No schema changes; consumers of `promote_omc`, `cli_promote`, `write_bridge` keep their argparse surface. Adds 89 regression tests (Python + bats); all 298 tests pass.

### Fixed — Critical

- **C1 — Path traversal via `ark-source-path`.** `promote_omc._resolve_existing_vault_page` now calls `.resolve()` + `.relative_to(project_docs)` on the joined path and returns `None` when the resolved target escapes `project_docs`. Previously a crafted `ark-source-path: "../../evil.md"` could cause `_merge_into_existing` to append OMC content to a file outside the vault.
- **C2 — Transactional-delete gate was load-bearing on index-regen exit code alone.** `cli_promote.py` now gates `finalize_deletes` on THREE conditions: (a) `promote()` recorded zero errors, (b) index regen actually ran and returned 0 (missing script no longer silently counts as success; opt out with `--allow-missing-index-script`), and (c) every path `promote()` wrote still exists and is non-empty. `PromotionReport` gains a `written_paths: List[Path]` field; `cli_promote` passes it as `require=` so `finalize_deletes`'s precondition loop is no longer a no-op.

### Fixed — High

- **H1 — `_append_to_session_log` / `_merge_into_existing` are now atomic AND idempotent.** Both helpers write via `tempfile.mkstemp` + `os.replace` (matching `omc_page.write_page`). Each append embeds a 12-char content-hash marker (`<!-- src:<hash> -->`); retries detect the marker and skip. This closes the retry-appends-duplicates race that defeated the transactional-delete design's intended "safe to re-run after partial failure" guarantee.
- **H2 — `_find_session_log` no longer silently falls back to the newest `Session-Logs/*.md`.** Returns `None` on exact-slug miss. Callers already guard `if log_path:`; cross-session content contamination via typo / stale slug is eliminated.
- **H3 — `bridge-merge` and `dual-write-debug` no longer queue OMC delete when nothing was written.** `pending_deletes.append(omc_path)` is now gated on a vault-side effect actually happening (session-log append OR troubleshooting write for dual-write-debug; session-log append for bridge-merge). When nothing happened, the reason is recorded in `report.errors` and the OMC source is preserved for the next run.
- **H4 — `except Exception` in `promote()` narrowed to `(OSError, ValueError)`.** Programmer errors (`TypeError`, `AttributeError`, `KeyError`) now propagate instead of being absorbed as per-file "error" strings, so CI catches real bugs.
- **H5 — `/wiki-handoff` schema validation extended to all substantive fields.** `_validate` now applies to `task_text`, `open_threads`, `next_steps` (required) and `done_summary` (optional when empty). `scenario` must match `^[a-z0-9][a-z0-9\-]{0,31}$` (DNS-like slug); previously it was embedded into a tag unchecked.
- **H6 — `GENERIC_PATTERNS` hardened.** Normalization strips trailing punctuation before comparison; a filler-token-prefix family catches `tbd/todo/wip/fixme/xxx`-prefixed strings; a distinct-word-count check (`MIN_DISTINCT_TOKENS=3`) blocks repetition-padded bypasses like `"todo todo todo todo"`. Rejects variants `"TO-DO"`, `"todo."`, `"TODO!"`, `"continuing"`, `"tbd again"`, `"wip wip wip"` that previously passed.
- **H7 — `cli_promote.main()` returns non-zero when anything goes wrong.** Previously always returned 0 regardless of `report.errors`, `delete_errors`, or regen exit code. Callers (bash step in `/wiki-update` Step 3.5, CI) now get a real signal.
- **H8 — Index regen stdout/stderr surfaced on failure.** On `rc != 0` (and on missing-script), `cli_promote` prints the captured output instead of discarding it.

### Fixed — Medium

- **M6 — `/ark-workflow` Step 6.5 documents all write_bridge exit codes as blocking.** Previously only exit 2 (schema rejection) was explicitly called out as a block; exit 3 (>10 collision retries) and other non-zero codes had no LLM-facing guidance. Updated prose gate explicitly covers 2 / 3 / other non-zero with resolution paths.
- **M10 — `_run_index_regen` now has a 120-second `subprocess.run(..., timeout=120)`.** Prevents a hung regen script from stalling `/wiki-update` indefinitely.
- **Transactional surface visibility.** `cli_promote` report now prints `Vault paths written: N` and `Delete status: BLOCKED — <reason>` when the gate refuses to unlink. Previously the report showed `Deleted from OMC: 0` with no actionable reason.

### Added — Regression tests

- **`test_promote_omc.py`** (+15 tests): path-traversal acceptance/rejection (C1); `written_paths` population (C2); `finalize_deletes` require-gate on missing / empty / valid paths (C2); idempotent merge + append on retry (H1); `_find_session_log` no-fallback semantics (H2); bridge-merge / dual-write-debug `log_path=None` preservation (H3); programmer-error propagation + OSError capture asymmetry (H4).
- **`test_cli_promote.py`** (new, +7 tests): end-to-end happy path, missing-regen-script blocks deletes, `--allow-missing-index-script` opt-out, regen rc!=0 blocks, `report.errors` blocks, simulated write-destabilization detected by `require=` gate, `Vault paths written:` surface assertion.
- **`test_write_bridge.py`** (+21 parametrized cases): GENERIC_PATTERNS bypass hardening (casing / punctuation / filler-prefix / distinct-word variants); `task_text` and `done_summary` validation; `scenario` slug sanitization (accept/reject grid).
- **`test_promote_omc_e2e.bats`** (+3 tests): C2 missing-regen blocks + non-zero exit; `--allow-missing-index-script` opt-out; H8 regen stderr surfacing.

### Changed

- `skills/ark-workflow/SKILL.md` — Step 6.5 callout expanded to document exit 3 and any other non-zero as blocking.
- `skills/wiki-update/scripts/cli_promote.py` — new `--allow-missing-index-script` flag.

### Not changed (flagged in review but out-of-scope for bugfix release)

- `translate_frontmatter` still pops `ark-source-path` from vault output (OMC_ONLY_FIELDS). Whether to preserve provenance in vault pages is a schema decision for a future minor release.
- `read_bridges` still uses `path.stat().st_mtime` instead of the frontmatter `created:` field. Low-impact in normal workflows; defer.
- `seed_omc` permission inconsistency (`0o644` for O_EXCL, `0o600` for tempfile). Defer.

## [1.19.0] - 2026-04-20

New **OMC↔Ark Wiki Bridge** — connects OMC `/wiki` (per-worktree, gitignored scratchpad) with Ark `/wiki-*` (per-project, git-tracked Obsidian vault). Seeds OMC with cited vault sources on warmup prompt+cache-miss; flushes validated session bridges on v1.17.0 probe's compact/clear; promotes durable OMC content into the vault at `/wiki-update` with lossless frontmatter round-trip and transactional (post-index-regen) deletes. Both advisors (Codex + Gemini) reviewed the design and the implementation plan; Codex flagged 4 HIGH design concerns + 4 HIGH plan concerns, all resolved before implementation.

### Added

- **Shared module** `skills/shared/python/omc_page.py` — OMC page read/write/hash primitives used across wiki-handoff, warmup, and wiki-update. Pyyaml-backed frontmatter, `O_EXCL` atomic writes, `body_hash`, `content_hash_slug(vault_path + content)` → 12-char slug.
- **`/wiki-handoff` skill** (`skills/wiki-handoff/`) — session-bridge writer with schema enforcement (rejects empty / generic `open_threads` / `next_steps`), `O_EXCL` + suffix-retry collision handling. Invoked from `/ark-workflow` Step 6.5 on `(a) compact` and `(b) clear`; `(c) subagent` skipped.
- **`seed_omc.py`** in `/ark-context-warmup` — populates `.omc/wiki/` with cited vault sources keyed by `sha256(vault_path + content)[0:12]`; idempotent; per-chain stale cleanup. Writes provenance (`ark-original-type`, `ark-source-path`, `seed_body_hash`, `seed_chain_id`) for lossless round-trip.
- **`read_bridges.py`** in `/ark-context-warmup` — next-session pickup. Chain-ID affinity: match → 7-day window; mismatch → single most-recent ≤ 48h. Rendered under "Prior Session Handoff" in Context Brief via extended `synthesize.assemble_brief(prior_bridge=...)`.
- **`evidence.derive_candidates(has_omc=True)`** returns `{"candidates": [...], "seed_sources": [...]}` so warmup Step 5b can feed `seed_omc.py` without extra fanout.
- **`/wiki-update` Step 3.5 — Promote OMC Wiki Pages** via `cli_promote.py` wrapper:
  - Stubs, environment pages, untouched source-warmup, pre-session pages → skipped
  - `high` → auto-promote to `Architecture/` or `Compiled-Insights/`, merge via `ark-source-path` if existing vault page resolves
  - `medium` → stage in `vault/Staging/` + low-priority TaskNote bug (non-interactive Q4A)
  - debugging → fold inline into session log; also `vault/Troubleshooting/` cross-link when tagged `pattern`/`insight` (Q5C)
  - session-bridge → merge into session log body
- **Transactional delete** — `promote()` returns `pending_deletes`; `cli_promote.py` runs `_meta/generate-index.py` and only executes deletes on exit 0. Failed vault writes or failed index regen preserve OMC sources for retry.
- **Integration suite** — bats e2e at `skills/wiki-update/scripts/integration/test_promote_omc_e2e.bats`.

### Changed

- `skills/ark-context-warmup/scripts/evidence.py` — `derive_candidates` now returns dict with `candidates` + `seed_sources`. Existing callers updated to read `out["candidates"]`.
- `skills/ark-context-warmup/scripts/synthesize.py` — `assemble_brief` accepts `prior_bridge` kwarg, renders "Prior Session Handoff" section when non-empty.
- `skills/ark-context-warmup/SKILL.md` — new Step 1b (bridge read) + Step 5b (OMC seed on cache miss).
- `skills/ark-workflow/SKILL.md` — Step 6.5 action bullet expanded into `(a)/(b)/(c)` branch block; `(a)` and `(b)` invoke `/wiki-handoff` before the destructive action and before `record-reset`.
- `skills/wiki-update/SKILL.md` — new Step 3.5 between existing Steps 3 and 4.

### Degradation contract

Silent no-ops throughout: no `.omc/`, no prompt, cache hit, missing vault dirs. Schema rejection blocks destructive action until LLM re-invokes with specifics. Non-portable shellouts removed (`date -r` replaced by pyyaml frontmatter parsing).

### Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-20-omc-wiki-ark-bridge-design.md`
- Plan: `docs/superpowers/plans/2026-04-20-omc-wiki-ark-bridge.md`

## [1.18.1] - 2026-04-20

Bugfix release for the `/ark-update` framework. Two independent issues surfaced when running `/ark-update` against the plugin's own repo for the first time since the routing-rules v1.17.0 template bump.

### Fixed

- **`/ark-update --dry-run` reports a correct plan.** `scripts/plan.py:_dry_run_target_profile_entry` did not inject `args["skills_root"]` into the op args dict, while the apply path (`scripts/migrate.py:_run_phase_2`) did. The mismatch caused every op that reads a template (`ensure_claude_md_section`, `ensure_routing_rules_block`, `create_file_from_template`) to report `would_fail_precondition=True` with `error="'skills_root'"` (KeyError), even when the real apply would have succeeded. The apply path was unaffected — only the dry-run report was misleading. Thread `skills_root` through `build_plan` → `_dry_run_target_profile_entry` to mirror the apply path.

### Test infrastructure

- **Regenerated fixtures** under `skills/ark-update/tests/fixtures/` that fell out of sync with commit `547cc34` (routing-rules bumped to v1.17.0 + added "Session habits" subsection). 11 convergence/summary/backup-provenance tests that expected idempotent "clean" runs were seeing legitimate drift and failing. The engine was behaving correctly — fixtures were stale. Regenerated in two semantic groups: (A) `expected-post` only for fixtures representing older/drifted/fresh state (`pre-v1.11`, `pre-v1.12`, `pre-v1.13`, `fresh`, `drift-inside-markers`); (B) both pre and post for fixtures representing "at current target" state (`healthy-current`, `drift-outside-markers`) — outside-markers content manually verified preserved byte-exact on the latter.
- **`test_convergence_pre_v1_13_skips_two_existing`** renamed to `_converges_existing` and assertions updated. With `target-profile.yaml` routing-rules at v1.17.0 and the `pre-v1.13` fixture's region at v1.12.0, the region legitimately drift-overwrites on convergence — only `setup-vault-symlink.sh` remains `skipped`. Expected breakdown: `2 applied, 1 drift-overwritten, 1 skipped`.
- **New fixture-regeneration helper** `skills/ark-update/tests/regenerate_fixtures.py`. Supports `--dry-run` (preview) and `--apply`. For future template or target-profile bumps, re-running this helper regenerates `expected-post/` across all fixtures (Group A) and additionally rewrites the pre-state for "at-target" fixtures (Group B). Eliminates the manual regeneration burden that caused this release's test drift.

### Known follow-up

- The underlying cause of fixture staleness — template/target-profile bumps without fixture regeneration in the same commit — is a process gap, not a tooling gap. Consider adding a CI check that fails if running `regenerate_fixtures.py --dry-run` would produce non-empty output.

## [1.18.0] - 2026-04-18

New **Brainstorm** scenario + **gstack planning integration** in `/ark-workflow`. Both were designed with a `/ccg` second-opinion pass — Codex flagged three HIGH concerns (wrong-truth-source detection, zombie chain files after Brainstorm STOP, Path B parity), Gemini flagged "Review Hell" (stacked `/ccg` + `/autoplan`) and bureaucratic re-invocation after Brainstorm. The synthesized rework shipped before Phase 2 chain edits.

### Added

- **`Brainstorm` scenario** in `/ark-workflow` — pre-triage exploration for fuzzy ideas. No weight class. Triggers on creation-intent phrases only ("brainstorm", "I have an idea", "should I build", "worth building", "shape this idea", "is this worth"). Produces a spec artifact suitable for re-triage. New `chains/brainstorm.md`.
- **Continuous Brainstorm pivot gate** in `chains/brainstorm.md` — at spec-commit, offers interactive `[Y/n]` prompt. Y archives the chain file and re-invokes `/ark-workflow` internally with the spec; N archives and stops. Either branch prevents zombie chains from being offered on session resume.
- **Session-capability `HAS_GSTACK_PLANNING` detection** in `/ark-workflow` Project Discovery — agent-executed semantic probe that reads the skill list in the system-reminder context. Matches the detection pattern used by `/ark-health` and `/ark-onboard` (plugin availability = "skill loadable in current session", not filesystem inspection).
- **`GSTACK_STATE_PRESENT` advisory filesystem cross-check** — secondary, non-authoritative signal based on `$HOME/.gstack/config.yaml`. Used only to distinguish "gstack absent" from "gstack installed-but-broken" — not used for routing decisions.
- **Three-state UX for gstack availability**: healthy (include the step), absent (silent skip — no notice), broken-install (one-notice-per-chain pointing to `/ark-health`). Brainstorm is the single exception — it always emits a fallback notice when invoked without gstack.
- **Heavy planning authority substitution rule** (SKILL.md § Condition Resolution) — Path A Heavy chains **replace** `/ccg` plan review with the gstack planning authority when `HAS_GSTACK_PLANNING=true`:
  - Greenfield Heavy step 4 `/ccg` plan review → `/autoplan` (CEO+design+eng+DX bundle)
  - Migration Heavy step 3 `/ccg` migration plan review → `/plan-eng-review` (architecture-focused)
  - Performance Heavy step 4 `/ccg` optimization plan review → `/plan-eng-review`
  Prevents stacked-committee ceremony. Spec-review `/ccg` steps (earlier in each chain) stay unchanged — they review the spec, not the plan.
- **Path B gstack-independence** documented as explicit product decision (SKILL.md § Path B gstack-independence). Path B's `/autopilot`/`/team` engines already include internal review phases; layering gstack planning on top would reintroduce stacked-committee ceremony. Users who want gstack reviews choose Path A.
- **Greenfield Medium additive planning steps** (not substitution — Medium uses `/ask codex` single-advisor review, not `/ccg`):
  - `/plan-design-review` at step 2 (if gstack AND UI-with-design-reference)
  - `/plan-devex-review` at step 3 (if gstack AND developer-facing surface)
  Handoff marker renumbered `after-step-3` → `after-step-5`.
- **New condition triggers** in SKILL.md Condition Resolution:
  - "Developer-facing surface" (for `/plan-devex-review`): public APIs, CLIs, SDKs, plugin interfaces, developer docs
  - Extended "UI-with-design-reference" trigger now also gates `/plan-design-review`
  - `(if gstack)` resolver branches on both `HAS_GSTACK_PLANNING` and `GSTACK_STATE_PRESENT` per the three-state UX
- **Scope-retreat pivot** (Greenfield → Brainstorm) documented in SKILL.md § When Things Change. If step 1 `/brainstorming` reveals scope uncertainty ("should we even build this", "I don't know if this is the right thing"), pivot mid-chain to Brainstorm scenario. This is a *downshift* pattern, distinct from the existing upshift re-triage rule — Greenfield assumes implementation commitment; Brainstorm does scope-challenging. Escape-hatch note also added at the top of `chains/greenfield.md`.

### Changed

- Brainstorm scenario triggers deliberately exclude "explore" and "think through" (too generic — would match verbose bug descriptions or Hygiene tasks). Creation-intent phrases only.
- `chains/brainstorm.md` step 4 changed from `**STOP** — invoke /ark-workflow again` to the Continuous Brainstorm interactive pivot + archive-either-branch semantics.
- Greenfield Medium `/plan-design-review` and `/plan-devex-review` step descriptions clarified to note that at Medium scale the spec itself is the review target (no separate `/writing-plans` artifact exists at Medium, unlike Heavy). Functional behavior unchanged; documentation clearer.

### Rework context

Phase 1 was patched in place (semantic detection change, substitution rule, Brainstorm pivot) before Phase 2 chain edits. Both advisors' raw outputs and the synthesis are preserved in `.omc/artifacts/ask/` for the 2026-04-18 design session.

### Post-commit review fixes (pre-push)

Ran a second `/ccg` review against the v1.18.0 commit diff before pushing. Codex flagged two HIGH contract bugs and one MEDIUM rendering concern; Gemini flagged one UX red flag. All addressed in a follow-up commit on the same 1.18.0 release (not pushed yet at review time — no version bump needed).

- **Brainstorm archive path aligned with `references/continuity.md` convention** — changed from `.ark-workflow/archive/{chain_id}.md` to `.ark-workflow/archive/YYYY-MM-DD-brainstorm.md`. Two different archive contracts for the same operation would have produced drift between continuity.md's stale-chain logic and Brainstorm's pivot.
- **Brainstorm pivot Y-branch reframed as inline re-triage**, not a recursive `/ark-workflow` skill invocation. Reconciles with SKILL.md Step 7's core contract ("ark-workflow does not invoke downstream skills itself"). The agent continues applying the triage algorithm inline against the new spec and writes a fresh `current-chain.md` — no recursion.
- **Substitution render rule** added to SKILL.md Step 6: when `HAS_GSTACK_PLANNING=true`, the resolved chain rewrites substituted step text (`/ccg` → `/autoplan` / `/plan-eng-review`) and drops the substitution note from user-facing output. Chain-file storage stays canonical; the user sees exactly one skill per step.
- **Misleading "Path B exception" note removed** from `chains/brainstorm.md` — Brainstorm Path B uses OMC skills (`/deep-interview`, `/ralplan`, `/ccg`), not gstack. No actual exception to the Path B gstack-independence rule; the note was residue.
- **Non-interactive pivot-gate fallback** documented in `chains/brainstorm.md`: in auto-mode, CI, or unattended background execution, default to Y (continue to triage) without prompting. Addresses Gemini's red flag that the `[Y/n]` prompt would hang in backgrounded contexts.

Known follow-ups for a future minor release: semantic probe silent misclassification (low-severity — relies on agent correctly reading skill-list names), Brainstorm trigger rigidity for "explore new feature idea" (false-negative by design), substitution note verbosity in chain-file storage.

## [1.17.0] - 2026-04-17

### Added

- **Context-budget probe in `/ark-workflow`.** New helper `skills/ark-workflow/scripts/context_probe.py` reads the Claude Code statusline cache at `.omc/state/hud-stdin-cache.json` and surfaces a three-option mitigation menu (compact / clear / subagent) at chain entry, each step boundary (Path A only), and Path B acceptance. Six CLI modes: `raw`, `step-boundary`, `path-b-acceptance`, `record-proceed`, `record-reset`, `check-off`. Stdlib only. Thresholds: nudge at 20%, strong at 35% of `context_window.used_percentage`.
- **Atomic chain-file mutation helper.** All `.ark-workflow/current-chain.md` mutations (frontmatter writes via `record-proceed`/`record-reset`, checklist `[ ]` → `[x]` writes via `check-off`) now go through one shared `chain_file.atomic_update(path, mutator_fn)` helper using `fcntl.flock(LOCK_EX)` + temp-file + `os.replace` to prevent torn writes and lost updates between concurrent frontmatter and checklist edits.
- **Nudge-fatigue suppression** via new optional `proceed_past_level` field in `current-chain.md` frontmatter. `record-proceed` self-detects the current level and persists `proceed_past_level: nudge` only when current level is `nudge`; strong-level proceed never persists suppression. Lifecycle is explicit (no inference) — caller invokes `record-reset` after the user takes option (a) `/compact` or (b) `/clear`.
- **Session / freshness rejection layers.** Probe accepts `--expected-cwd`, `--expected-session-id`, and `--max-age-seconds`. Session-id (when resolvable from `$CLAUDE_SESSION_ID` or `.omc/state/hud-state.json`) is the primary check; cwd is the secondary check; mtime-based TTL (300s for entry-time probes) is the tertiary fallback. All session/freshness mismatches degrade to silent no-op via `level: unknown`.
- **"Session Habits" coaching block** in `/ark-workflow` SKILL.md (between "When Things Change" and "Routing Rules Template") and as a "### Session habits" subsection in `references/routing-template.md`. Three habits: rewind-before-correction, new-task-means-new-session, compact-with-forward-brief. Pushed to downstream projects via `/ark-update`.
- **Manual smoke-test runbook** at `skills/ark-workflow/scripts/smoke-test.md` for hands-on validation when bats is not installed.
- **Bats integration suite** at `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` covering all six CLI modes, end-to-end reset lifecycle, atomic-write stress test (concurrent check-off + record-proceed for ~2 seconds), and exit-0-on-missing-state guarantee.

### Changed

- **`/ark-workflow` Step 6.5** "Activate Continuity" now resolves `SESSION_ID` once at the top, runs a chain-entry probe (with `--max-age-seconds 300`) before executing step 1, and replaces the single-line "after each step" bullet with a 5-substep block that calls the atomic `check-off` helper, runs the step-boundary probe, and handles the proceed/reset/(c) decision.
- **`/ark-workflow` Step 6** dual-path presentation now invokes the `path-b-acceptance` probe and renders a one-line warning above the `[Accept Path B]` button when the session is already at nudge or strong level.
- **`/ark-update` `routing-rules` managed region** version bumped from `1.12.0` → `1.17.0` because `references/routing-template.md` gained the Session habits subsection. Downstream projects pull the block via `/ark-update`.

### Degradation contract

- Probe is gated behind `HAS_OMC=true`. When OMC is not installed, Step 6.5 falls back to today's behavior (no menu, no probe call). All probe failure modes (missing file, malformed JSON, schema mismatch, session mismatch, stale file, permission denied) degrade silently to no menu.

### Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md`
- Plan: `docs/superpowers/plans/2026-04-17-ark-workflow-context-probe.md`

## [1.16.0] - 2026-04-15

Two themes in one release: (1) **Path B uniformity** — every chain variant now
routes to a single execution engine (`/autopilot`) in Path B, closing audit
items R1, R2, R4, R10, R11, R15, R16, R17; and (2) **External advisor
probe-gating** — the v1.15.0 `HAS_CODEX` / `HAS_GEMINI` probe contract from
`/ark-code-review` is back-ported to chain-level `/ask codex` and `/ccg` call
sites, closing audit item R3.

Audit reference: `.ark-workflow/audits/omc-routing-audit-2026-04-14.md`
(implementation addendum section "Completed recommendations").

### Added

- **§ Section 7 "External Advisor Probe Gates"** in
  `skills/ark-workflow/references/omc-integration.md` — canonical probe
  contract for chain-level `/ask codex` and `/ccg` invocations, including
  shell probe, gate-resolution table, one-line skip-notice templates, and
  documented interaction with `/ark-code-review --thorough`'s internal
  v1.14.0 probe. Resolves audit **R3** (Medium).
- **`HAS_CODEX` and `HAS_GEMINI` bash probes** in `skills/ark-workflow/SKILL.md`
  Step 1, exported alongside `HAS_OMC`. Same `command -v` pattern; vendor
  probes are independent of OMC (`ARK_SKIP_OMC=true` does NOT affect them).
- **`[probe-gated §7]` markers** on all 10 chain-level `/ask codex` and
  `/ccg` invocations across `bugfix.md`, `greenfield.md`, `performance.md`,
  `migration.md`, `hygiene.md`. Distribution: bugfix:1, greenfield:4,
  performance:2, migration:2, hygiene:1.
- **Canonical constants** `CODEX_CLI_BIN`, `GEMINI_CLI_BIN`,
  `CODEX_INSTALL_URL`, `GEMINI_INSTALL_URL` in `omc-integration.md` § 0.
- **`/external-context` pre-step** for Migration Medium + Heavy Path B
  (framework-migration contexts benefit from external documentation lookup
  before autopilot execution). Resolves audit **R10** (Medium).
- **`/visual-verdict` closeout step** for Greenfield Medium + Heavy Path B
  when a UI design reference exists; added Condition Resolution entry for
  "UI with design reference" in `skills/ark-workflow/SKILL.md`. Resolves
  audit **R11** (Medium).
- **`check_chain_drift.py`** CI lint at
  `skills/ark-context-warmup/scripts/check_chain_drift.py` — scans chain
  files + `omc-integration.md` for banned patterns (`OMC_EXECUTION_ONLY`,
  incorrect autopilot phase wording, stale `/ralph` or `/ultrawork` as
  step-3 engine). Pytest harness included; target globs: chains + integration
  reference. Resolves audit **R4** (High).
- **"External advisor CLI missing" entry** in
  `skills/ark-workflow/references/troubleshooting.md` — points at § Section 7
  for the probe contract, skip notices, and install URLs.

### Changed

- **Path B engine collapse.** All 17 Path B blocks across chain files now
  route to `/autopilot` as the step-3 engine. Greenfield Heavy's direct
  `/ultrawork` step-3 and Performance Medium + Heavy's direct `/ralph`
  step-3 have been retired at the chain layer; those engines still run
  **inside** autopilot's Phase 2 (Execution) per
  `omc-integration.md` § Section 4.1. Resolves audit **R2** (High).
- **Autopilot phase numbering** corrected in
  `omc-integration.md` Section 4. Phase 2 is Execution, Phase 3 is QA,
  Phase 4 is Validation, Phase 5 is Cleanup (authoritative source:
  `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/autopilot/SKILL.md:39-73`).
  Deleted the fictional `OMC_EXECUTION_ONLY` env-var section and all
  references to "Phase 5 (docs/ship)" or "internal Phase 4 (execution)".
  Resolves audit **R1** (High).
- **Section 4 "Verbatim"** changed to **"Superset of"** in the Per-Variant
  Expected Closeout Table. Path B closeout does a superset of Path A for
  the same variant (variant-inherited handback + additional Path-B-specific
  steps like `/wiki-ingest` for newly-introduced concepts). Resolves audit
  **R15** (Low).
- **Signal #3 parenthetical** in § Section 3 updated to document
  ark-added trigger keywords beyond the base OMC-native list. Resolves
  audit **R16** (Low).
- **Ship Standalone Path B** block retired (chain block + Section 2 table
  row). Pure-Ship workflows (no bugfix, no greenfield) are Path A only;
  the scenario no longer benefits from OMC's autonomous-execution shape.
  Coverage footprint tightened from 18 → 17 Path B blocks. Resolves
  audit **R17** (Low).

### Removed

- **OMC_EXECUTION_ONLY fictional env var** from `omc-integration.md`
  (never implemented in OMC runtime; a cache-wide grep of v4.11.5 source
  returns zero matches). See audit D6.1 for the origin-of-error trace.
- **Ship Standalone Path B** block (retired under R17 per Changed section).

### Coverage footprint

- `check_path_b_coverage.py` now expects **17 Path B blocks** (was 18) across
  chain files. Canonicalized shapes: 4 (`vanilla:14, team:1, special-a:1,
  special-b:1`). Raw-text hashes: 5 — Migration Medium + Heavy diverge from
  the vanilla hash because R10's `/external-context` pre-step lengthens their
  block bodies without changing classifier shape. Assertion distribution
  confirms 4 classifier shapes, 17 total blocks. See
  `omc-integration.md` § Section 4 note on hash count vs shape count.

### Rationale for uniformity

The 2026-04-14 uniformity decision resolved the central engine-selection
question from v1.13.0's design review: rather than ark-workflow routing
**between** execution engines (`/autopilot`, `/ralph`, `/ultrawork`, `/team`)
based on variant characteristics, it routes uniformly to `/autopilot` and
lets autopilot compose the parallel/persistent sub-engines inside Phase 2.
This removes two classes of chain-level drift (engine mismatch vs. variant,
phase-numbering errors leaking from obsolete v1.13.0 drafts) and reduces
the audit surface from per-engine-per-variant correctness to engine-composition
correctness inside autopilot — which OMC tests independently. The uniformity
premise (autopilot's auto-skip detects pre-placed artifacts and jumps to
Phase 2) was verified both statically (grep of SKILL.md:41-42) and at
runtime (live probe on 2026-04-15 — see audit addendum V1 subsection).

### Verification

```
$ python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py \
    --chains skills/ark-workflow/chains
  OK: 17 Path B block(s); 5 distinct canonicalized shape(s)

$ python3 skills/ark-context-warmup/scripts/check_chain_drift.py --root .
  OK: zero banned patterns found across 8 target file(s)

$ python3 -m pytest skills/ark-context-warmup/scripts/ -q
  179 passed
```

### Known pending items

- **v1.14.0 session log backfill** — not blocking this release. Session 7
  (v1.14.0 External Second Opinion shipping) did not produce a vault session
  log; to be backfilled in a subsequent housekeeping pass.
- **Audit recommendations R6, R7, R12, R13, R14, R18** — deferred per the
  implementation addendum's "Pending recommendations" table. Low-to-medium
  severity, low-to-medium effort; grouped for a future shipping cycle.

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
