---
okf_version: "0.1"
generated: 2026-07-06T23:43:13Z
---

# Vault Index

Auto-generated catalog of 72 pages. Human entry point: [00-Home](00-Home.md). Directory indexes below support progressive disclosure; the flat catalog after them is grouped by `type`.

# Directories

* [Compiled-Insights](Compiled-Insights/) - 29 pages
* [Session-Logs](Session-Logs/) - 21 pages
* [TaskNotes](TaskNotes/) - 13 pages
* [_Templates](_Templates/) - 6 pages
* [_meta](_meta/) - 2 pages

# Pages

* [Ark Skills Knowledge Base](00-Home.md) - Navigation hub for ark-skills: links to project areas and key resources.

# bug (1 pages)

* [Bug: {TITLE}](_Templates/Bug-Template.md)

# compiled-insight (30 pages)

* [Atomic Chain-File Mutation Pattern](Compiled-Insights/Atomic-Chain-File-Mutation-Pattern.md) - fcntl.flock(LOCK_EX) + tempfile.mkstemp + os.replace — the stdlib-only pattern used in context_probe.py to serialize concurrent read-modify-write sequences against a shared markdown file with frontmatter + checklist content. Both torn-write protection and lost-update prevention in one shape.
* [Codex Review Does Not Converge Across Passes](Compiled-Insights/Codex-Review-Non-Convergence.md) - codex review --base master samples different code paths on each invocation. Successive passes drop earlier findings and surface new ones. Never rerun hoping for a clean gate — fix current-pass P1s, accept non-blocking P2/P3s with justification, stop.
* [Development Workflow Patterns](Compiled-Insights/Development-Workflow-Patterns.md) - Workflow patterns: brainstorm→spec→codex→plan→implement, audit-first, NotebookLM queries, risk-primary triage with density escalation, hybrid TodoWrite+file continuity.
* [Dogfooding-Driven Skill Development](Compiled-Insights/Dogfooding-Driven-Skill-Development.md) - The most effective way to develop skills is to use them on the plugin's own repo — wiki-setup grew from 10 to 13 steps after dogfooding.
* [Ecosystem Architecture Map](Compiled-Insights/Ecosystem-Architecture-Map.md) - The Ark ecosystem connects 7 repos via shared skills plugin, Obsidian vaults synced to NotebookLM, Linear via linear-updater, and Proxmox homelab infrastructure.
* [Execution Philosophy — Dual-Mode Ark-Native ↔ OMC-Powered](Compiled-Insights/Execution-Philosophy-Dual-Mode.md) - Dual-mode execution — Ark-native (Path A, high checkpoint-density) and OMC-powered (Path B, low checkpoint-density) — co-exists per chain variant with discoverability-biased surfacing, variant-inherited handback with enumerated special cases, and byte-identity CI gating. Patterns replicate to any orchestrator skill that wants to add an autonomous alternative without removing the user-in-the-loop default. (Post-2026-04-15 refactor: variants dropped to 17 and classifier shapes to 4 under the uniformity decision — see [[Path-B-Canonicalization-Hash-vs-Shape]].)
* [Gstack Per-Host Install & the Runtime Root](Compiled-Insights/Gstack-Per-Host-Install-And-Runtime-Root.md) - gstack installs per-host via `setup --host <name>` into per-host skill dirs. `~/.claude/skills/gstack` is the shared runtime root (50+ skills reference it), NOT a deletable duplicate — deleting it breaks the Claude install. Auto-upgrade only re-syncs claude, so codex drifts.
* [Hook Drift Detection Pattern](Compiled-Insights/Hook-Drift-Detection-Pattern.md) - Plugin updates don't overwrite files installed outside the plugin tree (~/.claude/hooks/, ~/.local/bin/). Drift detection requires byte-compare against a version-aware canonical path — naive globs sort alphabetically and silently pick the oldest cached version.
* [MemPalace HNSW Bloat Repair](Compiled-Insights/MemPalace-HNSW-Bloat-Repair.md) - When `_upsert`/`_query` segfaults persist after upgrading mempalace, the on-disk HNSW segment is bloated and must be manually moved aside before `mempalace repair` can run. v3.3.4 prevents future bloat but doesn't repair existing on-disk corruption.
* [MemPalace Integration Architecture](Compiled-Insights/MemPalace-Integration-Architecture.md) - claude-history-ingest wraps mempalace with custom hooks and three modes (index/compile/full) — NOT using mempalace's built-in hooks, which are too intrusive.
* [PID-Aware Cross-Wing Mutex](Compiled-Insights/PID-Aware-Cross-Wing-Mutex.md) - Shell mutex that embeds the holder PID so contenders can distinguish a live long-running lock from a stale one. Fixes the 'live mine wiped by age-only stale recovery' regression in age-only timestamp mutexes. Distinct from in-process fcntl.flock — this is for cross-process shell hook serialization with planned retirement when upstream concurrency lands.
* [Path B Canonicalization — Hash Count vs Classifier Shape Count](Compiled-Insights/Path-B-Canonicalization-Hash-vs-Shape.md) - Byte-identity CI on structural chain blocks has two independent scalars: raw-text canonicalized hash count (varies with step count + descriptive text) and classifier-visible shape count (keys on semantic markers only). They diverge any time a pre-step or mid-block addition lengthens the block body without changing its semantic markers. Tracking them separately — and documenting the divergence — prevents false alarms on future additions.
* [Plugin Architecture & Context-Discovery Pattern](Compiled-Insights/Plugin-Architecture-and-Context-Discovery.md) - Ark-skills uses a Claude Code plugin with context-discovery — skills read CLAUDE.md at runtime, eliminating hardcoded project config and enabling cross-project reuse.
* [Plugin Versioning & Cache Pitfalls](Compiled-Insights/Plugin-Versioning-and-Cache-Pitfalls.md) - Claude Code plugin versioning has 4 sources of truth (VERSION, plugin.json, marketplace.json, cache SHA) — any desync causes silent update failure.
* [Python 3.14 @dataclass + future annotations + spec_from_file_location Pitfall](Compiled-Insights/Python-314-Dataclass-Future-Annotations-Pitfall.md) - On Python 3.14, combining @dataclass with `from __future__ import annotations` breaks when the module is loaded via importlib.util.spec_from_file_location without being registered in sys.modules. Dataclass internals read sys.modules[cls.__module__].__dict__ and get None.
* [Retrieval Backend Benchmark — index.md vs Obsidian-CLI vs MemPalace](Compiled-Insights/Retrieval-Backend-Benchmark.md) - Benchmarked 3 retrieval backends on ArkNode-AI vault (394 pages): index.md scan won for documented decisions (~2K tokens), Obsidian-CLI matched quality but needs two-step pattern, MemPalace failed on vault queries (wrong corpus — indexes conversations, not pages).
* [SKILL.md Shrink-to-Core via References Extraction](Compiled-Insights/SKILL-Shrink-to-Core-Pattern.md) - Cut SKILL.md verbosity by relocating long bash, prompts, templates, and report skeletons to references/*.md load-on-demand. v1.21.0 audit hit a 30% aggregate reduction (49–58% per-skill on slimmed targets) with zero behavior change. Verbosity reduction is not capability deletion — preserve all ark-specific IP inline only when its scannability matters at invocation time.
* [Session Habits for Context Longevity](Compiled-Insights/Session-Habits-For-Context-Longevity.md) - Three habits that shape context longevity across a skill chain: rewind-before-correction, new-task-means-new-session, compact-with-forward-brief. Landed in ark-workflow SKILL.md as a coaching block in v1.17.0; the Step 6.5 probe surfaces them contextually.
* [Session Log Knowledge Burial — The Core Vault Problem](Compiled-Insights/Session-Log-Knowledge-Burial.md) - Session log knowledge burial is the primary vault problem — 103+ session logs with hard-won ML insights buried in chronological journals, inaccessible to retrieval.
* [Session-Capability Plugin Detection Pattern](Compiled-Insights/Session-Capability-Plugin-Detection-Pattern.md) - For Claude Code plugin availability detection, the canonical signal is the session skill-list (semantic probe by the agent), not filesystem inspection. Filesystem/CLI probes are advisory only — they distinguish 'absent' from 'broken-install' but don't prove the plugin is loadable in the current session. Extracted from v1.18.0 gstack integration; matches pattern already proven in /ark-health and /ark-onboard.
* [Shell Script Safety Patterns — Lessons from mine-vault.sh Review](Compiled-Insights/Shell-Script-Safety-Patterns.md) - Four shell scripting pitfalls caught by code review: TMPDIR env collision, pipefail+tail swallowing, missing EXIT traps, and unquoted-tilde parameter stripping. All patterns survived spec review in plans and were only caught by code quality review.
* [Skill-Graph Hardening Pass — Design Rationale](Compiled-Insights/Skill-Graph-Hardening-Pass.md) - Why the ark-skills plugin is rejecting a wikilink-traversal/tier-frontmatter graph rebuild in favor of a smaller composition-contract + lint pass. Records the /codex consult+challenge transcripts that drove the v3 plan.
* [Structural Probe Parity — Byte-Diff Verification for Duplicated Bash Snippets](Compiled-Insights/Structural-Probe-Parity-Pattern.md) - When a canonical bash probe is duplicated into copy sites, substring-level grep verification misses structural drift. Use diff <(extract_probe canonical) <(extract_probe copy) to enforce byte-level structural parity. Pattern emerged from /codex finding on Arkskill-005.
* [TaskNotes MCP Integration — Architecture & Limitations](Compiled-Insights/TaskNotes-MCP-Integration-Model.md) - TaskNotes MCP is an HTTP endpoint inside Obsidian (not standalone), with limited schema — custom frontmatter requires post-edit or direct markdown write.
* [TaskNotes Status & Triage — Design Decisions](Compiled-Insights/TaskNotes-Status-Triage-Design.md) - ark-tasknotes status uses MCP-first data gathering with LLM triage — no algorithmic scoring. Six-section report with opinionated work plan recommendations.
* [Upstream Fork CHANGELOG vs PyPI Release Skew](Compiled-Insights/Upstream-Fork-Changelog-vs-PyPI-Release-Skew.md) - A CLOSED GitHub issue is not a shipped release. ark-skill-healer's changelog tier reads a plugin-fork CHANGELOG that runs ahead of the PyPI package — verify pypi.org/pypi/<pkg>/json before floor-bumping or retiring a workaround on an upstream fix.
* [Vault Hosting Evolution — Submodules to Standalone Repos](Compiled-Insights/Vault-Hosting-Evolution.md) - Vaults evolved from submodules in ark-skills to standalone repos at ~/.superset/vaults/, symlinked from projects. As of v1.11.0 this is /ark-onboard's greenfield default; embedded is an explicit escape hatch.
* [Vault Layout Detection — Structural Markers Beat Config Strings](Compiled-Insights/Vault-Layout-Detection-Structural-vs-Config.md) - Three-round recurring bug in notebooklm-vault-sync.sh — symlink traversal + standalone vs wrapped layout — kept resurfacing because retrieval scripts branched on the vault_root config string. Structural detection (marker dirs at vault root) survives misconfig where config-string parsing does not, and recurring fixes in the same file family are a layout-typing architectural smell.
* [Vault Retrieval Tier Architecture — T1-T4 Design](Compiled-Insights/Vault-Retrieval-Tier-Architecture.md) - Four-tier retrieval: NotebookLM (T1, ~500 tokens), MemPalace (T2, ~2500), Obsidian-CLI (T3, ~119+reads), index.md (T4, ~2100). Routing by query type, not corpus. Key finding: MemPalace on vault pages scored 8/10 vs 0/10 on conversations alone.
* [{TITLE}](_Templates/Compiled-Insight-Template.md)

# epic (10 pages)

* [/ark-context-warmup — Automatic Context Loader](TaskNotes/Tasks/Epic/Arkskill-002-ark-context-warmup.md) - Epic for the /ark-context-warmup automatic context loader — done.
* [/ark-update Version-Driven Migration Framework](TaskNotes/Tasks/Epic/Arkskill-004-ark-update-framework.md) - Epic for the /ark-update version-driven migration framework — ready to ship.
* [/ark-workflow Context-Budget Probe (v1.17.0)](TaskNotes/Tasks/Epic/Arkskill-007-context-budget-probe.md) - Epic for the /ark-workflow context-budget probe shipped in v1.17.0 — done.
* [/ark-workflow Path B Uniformity Refactor](TaskNotes/Tasks/Epic/Arkskill-006-path-b-uniformity.md) - Epic for the /ark-workflow Path B uniformity refactor — done.
* [/ark-workflow gstack planning integration + Brainstorm scenario (v1.18.0)](TaskNotes/Tasks/Epic/Arkskill-008-gstack-planning-brainstorm.md) - Epic for /ark-workflow gstack planning integration and the Brainstorm scenario (v1.18.0) — done.
* [Arkskill-012: Skill-Graph Hardening Pass](TaskNotes/Tasks/Epic/Arkskill-012-skill-graph-hardening-pass.md) - Hardening pass for the ark-skills plugin: catalog drift lint, external skill registry, anchor-ref lint, exception-aware composition guardrails. Replaces the rejected wikilink-graph and tier-only-frontmatter proposals.
* [Multi-Backend Vault Retrieval Tiers](TaskNotes/Tasks/Epic/Arkskill-001-vault-retrieval-tiers.md) - Epic tracking the multi-backend vault retrieval tier design (NotebookLM/MemPalace/Obsidian-CLI/index.md) — in progress.
* [OMC Plugin Detection Surfaces in /ark-health + /ark-onboard](TaskNotes/Tasks/Epic/Arkskill-005-omc-detection-surfaces.md) - Epic for OMC plugin detection surfaces added to /ark-health and /ark-onboard — done.
* [OMC ↔ /ark-workflow Dual-Mode Integration](TaskNotes/Tasks/Epic/Arkskill-003-omc-integration.md) - Epic for the OMC / ark-workflow dual-mode integration — done.
* [gstack v1.5.1.0 integration into /ark-workflow (Waves 1+2)](TaskNotes/Tasks/Epic/Arkskill-009-gstack-v1-5-1-0-integration.md) - Epic tracking gstack v1.5.1.0 integration into /ark-workflow across Waves 1 and 2 — in progress.

# meta (2 pages)

* [Tag Taxonomy](_meta/taxonomy.md) - Canonical tag vocabulary for ark-skills vault. All tags should come from this list.
* [Vault Schema](_meta/vault-schema.md) - Self-documenting vault structure, frontmatter conventions, and navigation patterns for ark-skills.

# moc (3 pages)

* [Ark Skills Knowledge Base](00-Home.md) - Navigation hub for ark-skills: links to project areas and key resources.
* [Project Management Guide](TaskNotes/00-Project-Management-Guide.md) - How task IDs, statuses, and task notes work in the ark-skills project.
* [Session Logs Guide](Session-Logs/00-Session-Logs-Guide.md) - Entry point for the Session-Logs archive — frozen, read-only history of past work sessions.

# research (1 pages)

* [Research: {TITLE}](_Templates/Research-Template.md)

# service (1 pages)

* [{SERVICE_NAME}](_Templates/Service-Template.md)

# session-log (21 pages)

* [Session 11: /ark-workflow Context-Budget Probe (v1.17.0 ship)](Session-Logs/S011-Ark-Workflow-Context-Budget-Probe.md) - Shipped v1.17.0: stdlib-only context_probe.py with 6 CLI modes + atomic chain-file helper + session habits coaching block. 22 atomic commits on branch context-management, merged via PR #19 as squash commit 8d42bd8. No P1 blockers in final /ccg review; 7 P2 + 4 P3 follow-ups filed.
* [Session 12: /ark-workflow gstack planning integration + Brainstorm scenario (v1.18.0 ship)](Session-Logs/S012-Ark-Workflow-Gstack-Planning.md) - Shipped v1.18.0: wired gstack planning (/autoplan, /plan-*-review, /office-hours) into /ark-workflow and added Brainstorm scenario with Continuous Brainstorm pivot gate. Two /ccg review passes — design-level (6 reworks) and pre-push diff-level (4 fixes). 2 commits on branch gstack-improve, PR #21 open.
* [Session 13: gstack v1.5.1.0 integration Wave 1 (v1.20.0)](Session-Logs/S013-Gstack-v1-5-1-0-Integration-Wave1.md) - Shipped v1.20.0 — Wave 1 of gstack v1.5.1.0 integration: 8 /checkpoint refs renamed to /context-save, continuous-checkpoint wired into Step 6.5 (opt-in), /context-save added as compaction-recovery option (d). 4 atomic commits on master; review and security passes both green.
* [Session 14: MemPalace v3.3.4 upgrade + palace-global mutex retirement (v1.23.1)](Session-Logs/S014-MemPalace-v3-3-4-Upgrade-Mutex-Retirement.md) - Shipped v1.23.1 — upgraded mempalace 3.3.2 → 3.3.4, retired palace-global mine mutex (Arkskill-010), repaired 294GB HNSW bloat, smoke-tested #976, synced live hook. Arkskill-010 closed.
* [Session 15: /ark-skill-healer first real run — gstack upgrade, mempalace fork-vs-PyPI correction, MarkItDown ingest](Session-Logs/S015-Ark-Skill-Healer-Run-Mempalace-Fork-vs-PyPI.md) - First real /ark-skill-healer advisory run. Upgraded gstack 1.42.1.0→1.56.0.0. Caught a fork-vs-PyPI error: mempalace #1457 closed via #1461 but NOT on PyPI (latest 3.3.5) — reverted a wrong floor-bump + workaround-retire. Wired MarkItDown office-doc front-end into ingest skills.
* [Session 16: ark-skill-healer tracked rebuild — deep-interview→consensus→ralph, + S015 fix fold-in](Session-Logs/S016-Ark-Skill-Healer-Tracked-Rebuild.md) - Rebuilt the (lost, untracked) ark-skill-healer via deep-interview→omc-plan consensus→ralph. Consensus caught a false .claude/skills discovery path + the mempalace dual-upstream bug pre-execution. Discovered S015 had already run an untracked copy; folded its two methodology fixes (binary install-lag, fork-vs-PyPI authority) back in before committing/tracking. 28-test bats suite green.
* [Session 17: gstack install scoping (claude+codex) in /ark-onboard + /ark-health](Session-Logs/S017-Gstack-Install-Scoping-Onboard-Health.md) - Repaired a broken Claude gstack install (deleted runtime root), then taught /ark-onboard to actively install gstack scoped to claude+codex and /ark-health to detect the failure class (Check 2a). /ccg review + live bash verification caught a find -type d symlink miss and a zsh word-split bug. Shipped v1.28.0, PR #29.
* [Session 5: /ark-onboard Centralized Vault Recommendation (v1.11.0)](Session-Logs/S005-Ark-Onboard-Centralized-Vault.md) - Shipped /ark-onboard centralized-vault default (symlinked vault repo at $HOME/.superset/vaults/<project>), externalization plan-file generator, check #20 (warn-only), downstream skill notes. v1.10.1 → v1.11.0. PR #13.
* [Session 6: /ark-context-warmup Ship + Codex Harden (v1.12.0)](Session-Logs/S006-Ark-Context-Warmup-Ship.md) - Shipped /ark-context-warmup as step 0 of every chain. Fixed 13 codex-raised findings across 5 review passes (YAML safety, shell-escape, shel-path resolution, 2-layer interp, availability probes, evidence pipeline, index table parser). Tests 107→143. v1.11.0 → v1.12.0. PR #14.
* [Session 7: OMC ↔ /ark-workflow Dual-Mode Integration (v1.13.0)](Session-Logs/S007-OMC-Integration-Design.md) - Shipped dual-mode /ark-workflow routing. Every chain variant now has Path A (Ark-native) and Path B (OMC-powered) when HAS_OMC=true. 19 variants across 7 chain files; 3 canonicalized shapes (vanilla + special-a + special-b). HAS_OMC probe + omc-integration reference doc + check_path_b_coverage.py CI. v1.12.0 → v1.13.0.
* [Session 8: /ark-update Version-Driven Migration Framework (v1.14.0 Stream B)](Session-Logs/S008-Ark-Update-Framework.md) - Shipped /ark-update — version-driven migration framework that converges projects to the current ark-skills target profile. 19-skill plugin, 237 tests, ~2000 LOC. Combined v1.14.0 release with Stream A (OMC detection).
* [Session 8: Path B Uniformity Refactor (audit + 7-commit implementation)](Session-Logs/S010-Path-B-Uniformity-Refactor.md) - Audited /ark-workflow Path B routing; implemented 2026-04-14 uniformity decision in 7 atomic commits on branch ark-workflow-improve-OMC. All chain Path B engines collapsed to /autopilot except Migration Heavy (/team). Added chain drift lint (R4). 17 blocks / 4 classifier shapes / 5 raw-text hashes. Shipped in v1.16.0 via PR #18 (renumbered from S008 during rebase onto master's S008/S009).
* [Session 9: OMC Detection Surfaces in /ark-health + /ark-onboard (v1.14.0 Stream A)](Session-Logs/S009-OMC-Detection-Surfaces.md) - Shipped OMC plugin detection to /ark-health (Check 21) and /ark-onboard (Healthy Step 3 + Greenfield Step 18 + scorecard). Upgrade-style, tier-agnostic. Structural parity with canonical HAS_OMC probe enforced by diff. Combined v1.14.0 release alongside Session 2's Stream B. PR #17.
* [Session {NNN}: {TITLE}](_Templates/Session-Template.md)
* [Session: /ark-workflow Progressive-Disclosure Split (1.7.0)](Session-Logs/S004-Ark-Workflow-Split.md) - Split the 858-line ark-workflow SKILL.md into a 270-line router + 7 chain files + 4 reference files. All 22 v2 gaps + 19 chain variants preserved; 13/13 smoke tests pass.
* [Session: /ark-workflow Skill Implementation](Session-Logs/S002-Ark-Workflow-Skill.md) - Implemented /ark-workflow skill: task triage, scenario detection, weight-class skill chains. 11 tasks via subagent-driven-development, shipped v1.2.0.
* [Session: /ark-workflow v2 Rewrite](Session-Logs/S003-Ark-Workflow-v2-Rewrite.md) - Rewrote /ark-workflow SKILL.md to address 22 gaps: 7 scenarios, risk+density triage, batch triage, continuity mechanism, cross-session resume. Shipped 1.6.0 in 6 phases.
* [Session: MemPalace Integration for claude-history-ingest](Session-Logs/S001-MemPalace-Integration.md) - Implemented MemPalace (ChromaDB) backend for claude-history-ingest: Stop hook, installer, SKILL.md rewrite, shipped v1.1.0-1.1.2.
* [Session: Vault Retrieval Tiers Phase 1 Implementation](Session-Logs/S002-Vault-Retrieval-Tiers-Phase1.md) - Implemented T1-T4 multi-backend retrieval for wiki-query: mine-vault.sh, CLAUDE.md tier table, wiki-query rewrite, README update. 4 commits, all reviews passed.
* [Stage-5 Self-Test Gate Evidence — ark-update v1.14.0 pre-release](Session-Logs/2026-04-14-stage5-self-test-evidence.md) - Complete Stage-5 self-test gate evidence for /ark-update v1.14.0 pre-release. All parts passed.
* [Step 11 — /codex + /ark-code-review findings + triage](Session-Logs/2026-04-14-step11-review-findings.md) - Two-lane review of shipped /ark-update framework. 1 P1 fixed (gate-flag test coverage), 2 P1 codex-only deferred (atomic writes — bounded blast radius), 11 P2/P3 deferred to v1.1 ADR.

# task (3 pages)

* [Relocate Check 14a/14b/14c/14d/16b bash blocks to references/ (shrink-to-core follow-up)](TaskNotes/Tasks/Task/Arkskill-011-relocate-check-14-and-16b-bash-to-references.md) - v1.21.0 Shrink-to-Core moved heavy bash to references/. v1.21.1/2 added new checks inline. Relocate them to honor the original direction once they've stabilized.
* [Retire cross-wing mutex + revisit hook strategy when MemPalace #976 merges](TaskNotes/Tasks/Task/Arkskill-010-retire-cross-wing-mutex-when-mempalace-976-merges.md) - Watch MemPalace #976 (HNSW thread-safety). When merged, retire palace-global mutex and revisit dropping our custom Stop-hook in favor of the plugin's native auto-ingest.
* [{TITLE}](_Templates/Task-Template.md)
