# Deep Interview Spec: OMC ↔ /ark-workflow Integration

## Metadata

- **Interview ID:** omc-ark-workflow-integration-2026-04-13
- **Rounds:** 5
- **Final Ambiguity Score:** 8%
- **Type:** brownfield
- **Generated:** 2026-04-13
- **Threshold:** 20% (met at round 3; continued to round 5 for architectural pinning)
- **Status:** PASSED

## Clarity Breakdown

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.95 | 0.35 | 0.333 |
| Constraint Clarity | 0.97 | 0.25 | 0.243 |
| Success Criteria Clarity | 0.90 | 0.25 | 0.225 |
| Context Clarity | 0.80 | 0.15 | 0.120 |
| **Total Clarity** | | | **0.92** |
| **Ambiguity** | | | **0.08** |

## Goal

Integrate Oh My Claude Code (OMC) into `/ark-workflow` as a **dual-mode** routing layer. Each of the 19 chain variants (7 scenarios × Light/Medium/Heavy/etc.) gains a second execution path. Users choose between two philosophies at triage time:

- **Path A (Ark-native):** step-by-step, user-in-the-loop development with frequent judgment checkpoints (brainstorm → spec → codex → plan → codex → implement → review → ship).
- **Path B (OMC-powered):** front-loaded judgment (deep-interview + consensus plan) followed by autonomous execution (autopilot/ralph/team), then handback to Ark for vault + ship closeout.

The underlying axis is **checkpoint density / where judgment lives** — Ark distributes human judgment throughout; OMC front-loads it into heavy gates and then delegates execution. "Two execution philosophies" is the user-facing label; "checkpoint density" is the implementation-side name.

When `/ark-workflow` triages a task and OMC is installed, it emits Path A + Path B with a recommendation based on task signals. When OMC is not installed, only Path A is emitted plus a one-line install hint.

## Constraints

- **All 19 chain variants** across all 7 scenarios (Greenfield, Bugfix, Hygiene, Ship, Knowledge Capture, Migration, Performance) × Light/Medium/Heavy/Audit-Only/Full/Standalone get the dual-mode treatment. No chain is exempt, because the execution-philosophy axis applies universally.
- **OMC is an optional dependency.** The availability probe pattern established by `/ark-context-warmup` (v1.12.0) is reused. Chain output degrades gracefully to Path A only when OMC is absent.
- **Path B recommendation rule:** OR-any across 4 signals fires "Path B recommended":
  1. Prompt contains explicit OMC keyword (`autopilot`, `autonomous`, `ralph`, `ultrawork`, `team`, or a named OMC skill)
  2. Prompt is vague (no file paths, no function names, no acceptance criteria)
  3. Triage classifies Heavy weight
  4. Off-keyboard/batch signal (`overnight`, `while I'm away`, `until done`, or batch triage produces >3 parallel items)
- **User override:** Triage output presents three buttons: `[Accept Path B]` `[Use Path A]` `[Show me both]`. Aggressive OR recall is intentional (discoverability); user always has the override.
- **Hybrid handback is mandatory.** Path B's /autopilot phase runs **execution only** (skips autopilot's internal docs/ship Phase 5). After autopilot completes, control returns to Ark chain for `/ark-code-review --thorough` → `/ship` → `/land-and-deploy` → `/canary` → `/wiki-update` → `/cross-linker` → session log → `/claude-history-ingest`. Ark closeout is never skipped.
- **Ark chain file is authoritative.** `.ark-workflow/current-chain.md` remains the single source of truth throughout Path B. It shows `/autopilot` as `in_progress` while OMC runs, with the `.omc/state/sessions/{id}/` path annotated in the Notes section. `.omc/state/` is transient OMC-internal; it is not used for resume logic by Ark.
- **Respect the established priority rule:** "Agent Directives win over OMC doctrine" (codified in `~/.claude/CLAUDE.md`). Integration must not contradict Agent Directives (phased execution, forced verification, no semantic search, etc.).
- **Respect the established Ark pipeline:** brainstorm → spec → `/codex` review → plan → `/codex` review → implement. This spec itself should be `/codex`-reviewed before a plan is written.

## Non-Goals

- **NOT** replacing `/ark-workflow` with `/autopilot`. Ark remains the entry point; OMC is invoked under its routing.
- **NOT** making OMC a hard dependency of the ark-skills plugin. Plugin must remain installable and usable on systems without OMC.
- **NOT** modifying OMC itself (no patches, no forks, no OMC-side PRs).
- **NOT** modifying Ark closeout skills (`/wiki-update`, `/wiki-ingest`, `/cross-linker`, `/ship`, `/claude-history-ingest`). They stay pure Ark.
- **NOT** removing `/brainstorming` or `/writing-plans` from Path A. Path A remains exactly what it is today.
- **NOT** auto-invoking Path B without user approval. The recommendation is always a prompt, never a silent route.
- **NOT** modifying `/ark-context-warmup`'s existing backend contracts (notebooklm, wiki-query, tasknotes). Only the availability probe surface is extended.
- **NOT** touching the 22 codex-raised v1.12.0 hardening findings (already resolved).

## Acceptance Criteria

- [ ] `skills/ark-workflow/SKILL.md` contains a `HAS_OMC` availability probe that checks for OMC via `command -v omc` OR `~/.claude/plugins/cache/omc` presence, mirroring the `/ark-context-warmup` probe pattern.
- [ ] All 7 chain files (`greenfield.md`, `bugfix.md`, `hygiene.md`, `ship.md`, `knowledge-capture.md`, `migration.md`, `performance.md`) updated; all 19 variants render Path A and Path B blocks when `HAS_OMC=true`.
- [ ] Every Path B chain uses the hybrid handback pattern: `/deep-interview` → `/omc-plan --consensus` → `/autopilot` (execution-only) → `<<HANDBACK>>` → `/ark-code-review --thorough` → `/ship` → `/land-and-deploy` → `/canary` (if deploy risk) → `/wiki-update` → `/cross-linker` (if vault) → session log → `/claude-history-ingest`.
- [ ] Triage output when OMC installed recommends Path B if ≥1 of the 4 signals matches; output includes three options `[Accept Path B]` `[Use Path A]` `[Show me both]`.
- [ ] Triage output when OMC not installed emits only Path A plus a one-line install hint `NOTE: OMC not detected. Autonomous-execution chains hidden. Install: <URL>`.
- [ ] `.ark-workflow/current-chain.md` during Path B shows the Path B steps as the single checklist; `/autopilot` step notes include the `.omc/state/sessions/{id}/` path but Ark file remains authoritative for resume.
- [ ] New `skills/ark-workflow/references/omc-integration.md` documents:
  - The two-philosophies axis (user-facing) and checkpoint-density axis (implementation-side)
  - Per-chain skill map (which OMC skill maps to which Ark chain position)
  - When Path B beats Path A
  - The hybrid handback contract
  - The 4 Path-B signals and the OR-any rule
- [ ] `skills/ark-context-warmup/scripts/availability.py` extended to emit `HAS_OMC` in its probe result; Context Brief includes an "OMC detected: yes/no" line.
- [ ] `VERSION` bumped to `1.13.0`; `plugin.json` and `.claude-plugin/marketplace.json` versions aligned (per project convention — user memory: "always bump plugin version").
- [ ] `CHANGELOG.md` entry for v1.13.0 describing the dual-mode integration.
- [ ] `vault/TaskNotes/Tasks/Epic/Arkskill-003-omc-integration.md` epic file created (status: done after merge).
- [ ] `vault/Session-Logs/S007-OMC-Integration-Design.md` design session log capturing the 5-round deep interview, rationale, and final decisions.
- [ ] `vault/Compiled-Insights/Execution-Philosophy-Dual-Mode.md` compiled insight capturing the checkpoint-density axis, the hybrid handback pattern, and the OR-any signal rule.
- [ ] Smoke test: invoke `/ark-workflow` with a Greenfield Heavy prompt. Verify output changes between OMC-detected and OMC-absent states.
- [ ] `/codex review` the written implementation plan before any code is written (per Ark pipeline).
- [ ] `/codex review` the diff before `/ship` (per Ark pipeline).

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| OMC adds capability → the integration is about new features | Round 1 asked: capability or philosophy? | Two execution philosophies (checkpoint density) is the right user-facing mental model. Implementation is still gap-fill, but presented to users as a choice between driving and being driven. |
| Dual-mode applies only to Heavy chains where OMC's machinery pays off | Round 2 explicit scope question | All 19 variants. User's insight: "Ark gives step-by-step in-the-loop development, OMC planning is heavy but can run autonomously after planning." The axis applies universally. |
| Triage should pick neutrally and let user choose | Round 4 Contrarian: what if triage didn't recommend? | User held aggressive OR-any recall. Discoverability > neutrality. Mitigated by `[Show me both]` override button. |
| OMC would take over end-to-end once Path B starts | Round 5 handback question | Hybrid: OMC plans+executes; Ark owns vault, ship, session log, canary, code review, claude-history-ingest. Every Path B chain hands back. |
| Dual state files could coexist | Round 5 state authority question | Ark chain file is single source of truth. `.omc/state/` is transient; never read by Ark resume logic. |
| OMC would be a hard dependency after integration | Round 2 dependency posture question | Optional with graceful degradation. Mirrors `/ark-context-warmup` availability probe pattern. |

## Technical Context (Brownfield)

- `/ark-workflow` v1.12.0 shipped 2026-04-13 (today, PR #14). Architecture:
  - Router: `skills/ark-workflow/SKILL.md` (~270 lines, progressive disclosure)
  - Chains: `skills/ark-workflow/chains/{scenario}.md` × 7 files containing 19 variants
  - References: `skills/ark-workflow/references/{topic}.md` × 4 (batch-triage, continuity, routing-template, troubleshooting)
- Continuity via hybrid `.ark-workflow/current-chain.md` + TodoWrite (S003, v1.6.0). Handoff markers for design→implementation session breaks (S003).
- Step 0 `/ark-context-warmup` (S006, v1.12.0) with fan-out to NotebookLM + wiki-query + tasknotes; availability probe at `skills/ark-context-warmup/scripts/availability.py`. **This file is the pattern to follow for OMC detection.**
- OMC installed globally via `~/.claude/CLAUDE.md`. Path: `~/.claude/plugins/cache/omc/oh-my-claudecode/{version}/`. Current version at time of interview: 4.11.5.
- Priority rule codified: "When Agent Directives below conflict with OMC doctrine above, Agent Directives win."
- OMC skills in scope for this integration:
  - **Path B primary pipeline:** `/deep-interview`, `/omc-plan --consensus --direct`, `/autopilot`
  - **Path B variants (per scenario):** `/ralph` (loop-to-verified), `/ultrawork` (parallel), `/team` (coordinated agents)
  - **Complementary (invoked by name inside chains):** `/ccg` (tri-model consensus), `/skillify`, `/learner`, `/verify`, `/trace`, `/deep-dive`
- Vault: Obsidian at `vault/`. TaskNote prefix `Arkskill-`. Counter at `vault/TaskNotes/meta/Arkskill-counter`.
- Related prior memories (to preserve): always `/codex` review specs before implementation; always bump VERSION+plugin.json+marketplace.json+CHANGELOG on push to master; NotebookLM preferred for vault queries.

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Chain | core | scenario, weight, path_a_steps, path_b_steps, handback_step | belongs-to scenario; emitted-by router |
| Scenario | core | name, trigger_patterns | has-many Chain (one per weight class) |
| Path A | core | steps (Ark-native sequence), philosophy (stepwise judgment) | alternative-to Path B |
| Path B | core | steps (deep-interview → omc-plan → autopilot → handback → Ark closeout), philosophy (front-loaded judgment) | alternative-to Path A |
| Execution philosophy | core | axis (checkpoint density / judgment placement) | parent-of Path A, Path B |
| Signal | supporting | name, detector, weight | triggers Path B recommendation |
| Triage recommendation | supporting | recommended_path, signals_matched, override_buttons | output-of router |
| Availability probe | supporting | target (OMC), method (CLI-check OR plugin-cache-dir), result (bool) | runs-in router; mirrors ark-context-warmup pattern |
| Handback boundary | supporting | `<<HANDBACK>>` marker in Path B chains | separates OMC execution from Ark closeout |
| State authority | supporting | .ark-workflow/current-chain.md = SoT, .omc/state/ = transient | constraint-on resume logic |
| User override | supporting | `[Accept B]` `[Use A]` `[Show me both]` | responds-to Triage recommendation |
| Upstream vault artifacts | supporting | TaskNote epic (Arkskill-003), session log (S007), Compiled Insight (Execution-Philosophy-Dual-Mode), /ark-context-warmup probe extension | output-of done-bar (Complete + upstream integration) |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|--------------|-----|---------|--------|-----------------|
| 1 | 7 | 7 | 0 | 0 | N/A |
| 2 | 8 | 2 | 2 | 5 | 75% |
| 3 | 10 | 2 | 0 | 8 | 80% |
| 4 | 11 | 1 | 0 | 10 | 91% |
| 5 | 12 | 2 | 0 | 10 | 83% (core held, boundary entities specialized) |

Core noun (`Chain`) stable across all 5 rounds. `Execution philosophy` appeared round 2 and stabilized immediately — this was the reframing moment, not churn. Round 5 additions (`Handback boundary`, `State authority`) are architectural specializations of pre-existing boundary concepts, not new territory.

## Interview Transcript (Summary)

<details>
<summary>Full 5-round Q&A</summary>

### Round 1 — Integration shape
**Q:** When OMC "fits into" /ark-workflow, which shape matches your intent? (Reference-only / Gap-fill / Dual-mode toggle / OMC-as-inner-engine)
**A:** Gap-fill + Dual-mode hybrid — triage recommends based on task, user chooses.
**Ambiguity:** 85% → 50%. Key insight: user unified the dual-mode around **execution philosophy** (user-in-the-loop vs autonomous-after-planning), not capability.

### Round 2 — Scope and dependency
**Q:** Which chains get dual-mode? What's the OMC dependency posture?
**A:** All 19 chain variants. OMC is recommended-but-optional with graceful degradation.
**Ambiguity:** 50% → 33%. User rationale locked: "ark-workflow = step-by-step user-in-the-loop; OMC = heavy planning then autonomous execution." Entity `Execution philosophy` stabilized.

### Round 3 — Done bar and signals
**Q:** What's the minimum PR that ships it? Which signals bias toward Path B?
**A:** Complete + upstream vault integration (TaskNote epic, session log, Compiled Insight, /ark-context-warmup probe extension). All 4 signals with OR logic.
**Ambiguity:** 33% → 13%. Threshold crossed.

### Round 4 — Contrarian (signal bias)
**Q:** What if triage shouldn't recommend at all — what if "user chooses" means stay neutral?
**A:** Held OR-any (aggressive recall + `[Show me both]` override button). Discoverability over neutrality.
**Ambiguity:** 13% → 11%. Conviction noted in spec.

### Round 5 — Architectural boundaries
**Q:** Handback posture? State authority?
**A:** Hybrid (OMC plans+executes; Ark closes out vault/ship/log) + Ark chain file is single source of truth.
**Ambiguity:** 11% → 8%. All boundaries pinned.

</details>

## Next Steps (Ark Pipeline)

Per the project's established pipeline (`brainstorm → spec → codex → plan → codex → implement`), this spec is the **brainstorm + spec** artifact. Before implementation:

1. **Convert/copy** the design-relevant sections (Goal, Constraints, Non-Goals, Acceptance Criteria, Technical Context) into `docs/superpowers/specs/2026-04-13-omc-ark-workflow-integration-design.md` for the Ark convention.
2. **`/codex review`** the design spec. Resolve any findings inline.
3. **`/writing-plans`** (Path A) OR `/omc-plan --consensus` (Path B — meta-appropriate since this integration IS adding Path B): break into phased implementation plan at `docs/superpowers/plans/2026-04-13-omc-ark-workflow-integration.md`.
4. **`/codex review`** the plan. Resolve any findings inline.
5. **Execute** per the plan (phased, per Agent Directive #2 — never attempt multi-file refactors in a single response; 5 files per phase max).

## Execution Options (Deep-Interview Standard Bridge)

The skill's standard bridge offers: Ralplan→Autopilot (recommended), Autopilot-only, Ralph, Team, or Refine Further. Because this project has its own codex-gated pipeline and because the Ark maintainer is likely the one executing, the recommendation adapts:

1. **Ark pipeline (convert spec → codex → plan → codex → implement)** — honors the project's established workflow. **Recommended for this project.**
2. **Ralplan → Autopilot** — the deep-interview canonical 3-stage handoff. Would produce a consensus plan via `/omc-plan --consensus --direct` then execute via `/autopilot`. Valid but bypasses Ark's `/codex` gate.
3. **Autopilot direct** — fastest; skip ralplan consensus, go straight to autopilot with this spec as Phase 0.
4. **Refine further** — add more interview rounds (e.g., on default path when both recommended, on the `/ark-context-warmup` probe signature).

---

**Interview complete. Ambiguity: 8% (threshold: 20%). Status: PASSED.**
