# OMC Routing Audit — ark-workflow

**Date:** 2026-04-14
**Branch:** `ark-workflow-improve-OMC`
**OMC version:** 4.11.5
**Ark-workflow VERSION:** v1.14.0 shipped (commit `0376ebc`, unpushed); chain WIP (`/codex → /ask codex|/ccg` rename) unstaged
**Review:** Claude draft + Codex adversarial pass (artifact at `.omc/artifacts/ask/codex-…2026-04-15T03-32-55-851Z.md`)

---

## Framing note: uniform vs specialized routing

Codex's review surfaced a meta-question the draft audit took for granted: **is Path B optimizing for a uniform operator mental model, or for best-specialized OMC skill per scenario?**

The current design (`/deep-interview → /omc-plan --consensus → {engine}` applied nearly uniformly across variants) suggests ark-workflow deliberately chose uniformity — one recipe, easy to teach, predictable handback semantics. Several findings in this audit (D2.2, D3.1, D2.3) argue against that uniformity. If uniformity is the *intended* product property, those findings become optimizations, not gaps.

The audit does not resolve this tension — it surfaces it. Reader should decide before acting on any Gap finding that replaces a uniform step with a specialized skill. See Recommendation #R18.

---

## Summary

| Dimension | Verdict tally | Highest severity |
|---|---|---|
| D1 — Engine selection | 3 Correct, 1 Gap, 1 Over-engineered | **High** (Greenfield Heavy → /ultrawork misfit) |
| D2 — Front-end uniformity | 1 Gap, 1 Optimization, 1 Removed | Medium |
| D3 — Missed skills | 3 Gaps, 1 Partial, 3 Correct-to-not-route | Medium |
| D4 — Advisor fan-out consistency | 1 Gap, 1 Drift, 1 Unclear | Medium |
| D5 — Signal rules + telemetry | 2 Gaps, 1 Drift | Medium |
| D6 — /autopilot execution-only | 1 Doc-drift-high | **High** (not ship-blocker after Codex review) |
| **Totals** | **8 Gap, 2 Drift, 1 Optimization, 1 Over-engineered, 1 Unclear, 1 High-severity doc drift** | |

**Severity scale revised after Codex review:** no ship-blockers. D6 is high-severity doc drift, not undefined behavior — Section 6 of `omc-integration.md` already labels the mechanism "unresolved in v1.13.0." The practical risk is documentation lying about the handback boundary, not runtime correctness.

**Priority fixes (top 4):**
1. **D6** — Rewrite `omc-integration.md:§4.1` + `§6` to correct autopilot phase numbering (Execution=Phase 2, Cleanup=Phase 5, no "docs/ship") and retire the fictional `OMC_EXECUTION_ONLY` env var. Adopt prompt-instruction control OR explicitly accept autopilot-full-pipeline + Ark review as intentional double-review. **Effort: S.**
2. **D1.1** — Replace `/ultrawork` with `/autopilot` in Greenfield Heavy Path B step 3. `/ultrawork`'s own SKILL.md categorically says it is a *component*, not a standalone runner. **Effort: S.**
3. **D4.1** — Back-port v1.14.0 `HAS_CODEX`/`HAS_GEMINI` probe to the 10 ark-workflow call sites so missing vendor CLIs don't cause silent failure. **Effort: M.**
4. **New-from-Codex** — Add chain conformance lint test that catches stale strings like `"Phase 5 (docs/ship)"` across all chain files. Prevents this specific doc drift from recurring. **Effort: S.**

---

## Findings by Dimension

### D1 — Engine-selection correctness

**D1.1 — Greenfield Heavy → `/ultrawork` is a categorical misfit** — Gap (severity: high)

Codex independently confirmed this finding. `/ultrawork`'s own SKILL.md says it is "a component, not a standalone persistence mode" and directs full-pipeline work to `/autopilot`. ark-workflow routes Greenfield Heavy directly to `/ultrawork` at `greenfield.md:98`, discarding Expansion + Planning + QA + Validation + Cleanup phases.

- Evidence: `ultrawork/SKILL.md:19-24` Do_Not_Use_When
- Evidence: `omc-integration.md:57` allows `/autopilot or /ultrawork`
- Evidence: `greenfield.md:96-100` Path B step 3 = `/ultrawork`
- Fix: replace with `/autopilot` (which uses ultrawork internally for Phase 2 parallelism, preserving the "parallel lanes" benefit)

**D1.2 — Bugfix Heavy alt → `/ralph`, Performance Medium/Heavy → `/ralph`** — Correct
Matches `ralph/SKILL.md:16-20` Use_When. Reproduction-finicky and benchmark-target-loop scenarios are archetypal ralph usage.

**D1.3 — Migration Heavy → `/team`** — Correct
Matches `team/SKILL.md:11-12`. Handback contract at `omc-integration.md:§4.4` is well-specified.

**D1.4 — Ship Standalone has a Path B block despite being "discouraged"** — Over-engineered (severity: low)
`omc-integration.md:62` labels Ship Standalone "discouraged but available; Ship is already mechanical." Yet `ship.md:15-22` ships a full Path B block that's exposed via the 3-button UX. Recommend removing the block entirely or gating it behind `--force`.

---

### D2 — Front-end uniformity

**D2.1 — Light variants route through `/deep-interview`, contradicting the skill's own do-not-use-when** — Gap (severity: medium)

- Evidence: `deep-interview/SKILL.md:26-31` Do_Not_Use_When: "User has a detailed, specific request with file paths … — execute directly" and "User wants a quick fix or single change"
- Evidence: All 12 Vanilla Light/Medium variants use `/deep-interview` as step 1 unconditionally
- Fix: For Light variants, route to `/omc-plan --direct` instead. Reserve `/deep-interview` for Medium+ when requirements are genuinely fuzzy.

**D2.2 — Bugfix Heavy could optionally use `/deep-dive` when root cause unknown** — Possible optimization (severity: low — downgraded after Codex review)

Codex's challenge: Bugfix Heavy may intentionally normalize through uniform `/deep-interview → /omc-plan → /autopilot` for operator-mental-model consistency. Causal investigation can plausibly happen inside the execution/planning phases.

- Evidence: `deep-dive/SKILL.md:20-27` does name "Bug investigation: 'Something broke and I need to figure out why'" as its archetype
- Evidence: `bugfix.md:73-78` Path B uses uniform front-end
- Disposition: Not a gap. Reframe as optional alternate step 1 for users who explicitly want trace-driven investigation. Document as an *operator choice* rather than a chain default.

**D2.3 — Performance /sciomc suggestion** — Removed (not a finding)

Codex's challenge: `/sciomc` is a general research workflow, not performance-specific. Performance Medium/Heavy already use `/ralph` (not `/autopilot`), and `/deep-interview` for target/baseline clarification before a loop-to-benchmark engine is reasonable.

Disposition: Accepted. Remove from report. No action.

---

### D3 — Missed skills

| Skill | Chain fit | Verdict |
|---|---|---|
| `/trace` | Standalone not needed when `/deep-dive` covers it | **Correct to not route** |
| `/deep-dive` | Bugfix Heavy (optional) | See D2.2 — optimization, not gap |
| `/sciomc` | — | See D2.3 — removed |
| `/ai-slop-cleaner` | Hygiene Light/Medium | **Gap — downgraded to medium** (see D3.1) |
| `/external-context` | Migration Medium/Heavy, Greenfield Medium | **Gap — medium** (see D3.2) |
| `/verify` | Closeout duplicates `/ark-code-review` | **Correct to not route** (confirmed by Codex) |
| `/ultraqa` | Light/Medium closeout pre-gate | Partial Gap — medium (see D3.3) |
| `/visual-verdict` | Greenfield UI variants | **Gap — medium** (see D3.4) |
| `/omc-teams` | — | **Correct to not auto-route** (confirmed by Codex; stays user-triggered per v1.14.0 ADR) |
| `/ccg` as planning front-end | Already used for plan review | **Correct** |

**D3.1 — Hygiene chain doesn't leverage `/ai-slop-cleaner`** — Gap (severity: medium — downgraded after Codex review)

Codex's challenge: `/ai-slop-cleaner` triggers on explicit "deslop/anti-slop" keywords and warns against broad redesign. Hygiene includes audit + test-first restructuring + sometimes broken-behavior investigation — broader scope than `/ai-slop-cleaner`'s bounded cleanup.

- Evidence: `ai-slop-cleaner/SKILL.md:13-24` When/When-Not
- Evidence: `hygiene.md:48-54` Hygiene Medium includes /cso + /test-driven-development + implementation
- Disposition: Accept downgrade. Not a high-severity omission; a plausible alternate for explicit deslop prompts (which already route to Path B via Signal #1 keyword detection, so users self-select into this).
- Recommendation: Document `/ai-slop-cleaner` as an *alternate engine* for Hygiene Light when the prompt contains "deslop"/"anti-slop" keywords. Keep `/autopilot` as default for uniform operator experience.

**D3.2 — Migration chain doesn't use `/external-context` for framework docs** — Gap (severity: medium)
Framework upgrades reason from potentially-stale training data. `/external-context` parallel doc-specialist fetch would give authoritative migration guides. Add as pre-step 1 for Migration Medium/Heavy.

**D3.3 — Light closeout could use `/ultraqa` as a mechanical pre-gate** — Partial Gap (severity: medium)
`/ultraqa --tests` is complementary to (not redundant with) `/ark-code-review`: mechanical pass/fail vs qualitative review. Surface as optional step between engine completion and closeout when the chain spec has hard targets.

**D3.4 — Greenfield UI variants don't route to `/visual-verdict`** — Gap (severity: medium)
Conditional `(if UI with design reference)` → `/visual-verdict` in Greenfield closeouts would give deterministic JSON verdict for visual fidelity. Currently users invoke it manually.

---

### D4 — External-advisor fan-out consistency

**D4.1 — v1.14.0 vendor-probe gate not applied to ark-workflow's own `/ask codex` and `/ccg` calls** — Gap (severity: medium)
v1.14.0 commit `0376ebc` added `HAS_OMC=true AND (codex OR gemini on PATH)` gate for `/ark-code-review --thorough`. The 10 chain call sites (6 `/ask codex`, 4 `/ccg`) have no equivalent probe. WIP (git diff HEAD) shows call-site rename from `/codex` but no probe added. Missing CLI → silent failure or mid-chain error.

**D4.2 — Implicit "codex for code, ccg for plans" rule is undocumented** — Drift (severity: low)
Observed 6x `/ask codex` at code-review, 4x `/ccg` at plan-review. Convention isn't stated anywhere. Low-cost fix: add Section 7 "Advisor selection rules" to `omc-integration.md`.

**D4.3 — `/ccg` vs `/plan --critic codex` for plan review** — Unclear
Both have merit. `/ccg` is broader (3 perspectives); `/plan --critic codex` is tighter (1 alternate critic). Current choice reasonable; codifying it via short ADR prevents future churn.

---

### D5 — Signal rules and discoverability

**D5.1 — `omc-integration.md:111` overstates "verbatim" claim** — Drift (severity: low)
ark-workflow's actual list is a deliberate superset of canonical `omc-reference/SKILL.md:89–101` (adds `team`, `/team`, `ultrawork`, `deep-interview`). Fix: change "Verbatim" to "Superset of" + document delta.

**D5.2 — Multi-module signal detector path not documented** — Gap (severity: low)
Grep finds no mechanical multi-module counter. Most likely an LLM-judgment call during triage; should be documented as such at `omc-integration.md:84`.

**D5.3 — Telemetry doesn't capture execution outcome** — Gap (severity: medium)
Current fields: `{ts, has_omc, ark_skip_omc, signals_matched, recommendation, path_selected, variant}`. Missing: which engine ran, handback success, crash detection, duration. Extend to a second NDJSON line on chain completion/abort.

---

### D6 — `/autopilot` execution-only weakness

**D6.1 — `OMC_EXECUTION_ONLY` env var does not exist in OMC v4.11.5** — Doc drift (severity: high — downgraded from ship-blocker after Codex review)

Codex's challenge: Section 6 already labels the mechanism "unresolved in v1.13.0" and says not to enable Path B for /autopilot variants in production unless verified interactively. This makes it bad documentation with a wrong boundary model, not actively broken runtime behavior. Critical only if these variants are already shipping as production-safe automation.

**Evidence (unchanged):**
1. `grep -ri OMC_EXECUTION_ONLY ~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/` — zero matches
2. `autopilot/SKILL.md:39-72` actual phases: 0 Expansion → 1 Planning → 2 Execution → 3 QA → 4 Validation → 5 Cleanup
3. `omc-integration.md:168` wrong: claims Phase 4 is execution (actually Validation)
4. `omc-integration.md:171` wrong: claims Phase 5 is docs/ship (actually Cleanup)

**Fix options (updated after Codex review):**

| Fix | Description | Trade-off |
|---|---|---|
| **(a)** Rewrite as intentional double-review | Document that Vanilla Path B runs autopilot's full pipeline INCLUDING Phase 4 Validation, and Ark closeout is a deliberate second-layer review. Retire env var fiction. | Acknowledges current reality; 2× review cost per Vanilla Path B run; Ark remains last-word reviewer (original intent) |
| **(b)** Mark /autopilot variants experimental | Disable or "preview" all 12 Vanilla variants until a real stop-point exists | Honest; narrows Path B coverage significantly |
| **(c)** Prompt-instruction stop-after-Phase-3 | Chain step 3 invokes `/autopilot` with explicit "Complete Phase 0–3, then emit `<<HANDBACK>>` and stop" prompt | No upstream dependency; risk: autopilot agent may ignore instruction |

Recommend **(a)** as cleanest given current runtime reality, with **(c)** as a lightweight enhancement if prompt-following proves reliable. Open an OMC upstream issue requesting a first-class `--stop-after-phase N` flag regardless.

---

## Cross-reference: Unused OMC Skills

| Skill | Plausible chain | Verdict | Notes |
|---|---|---|---|
| `/trace` | Bugfix, Performance | Correct (subsumed by /deep-dive) | |
| `/deep-dive` | Bugfix Heavy (RC unknown) | Optimization, not gap | Operator choice |
| `/sciomc` | — | Not a finding | Codex: "weak, not reportable" |
| `/ai-slop-cleaner` | Hygiene Light (deslop prompts) | Gap (medium) | Alternate, not replacement |
| `/external-context` | Migration Medium/Heavy | Gap (medium) | Framework docs |
| `/ultraqa` | Light/Medium closeout pre-gate | Partial Gap (medium) | Complementary to /ark-code-review |
| `/visual-verdict` | Greenfield UI variants | Gap (medium) | Deterministic visual gate |
| `/verify` | Closeout | **Correct — confirmed by Codex** | Duplicates /ark-code-review |
| `/omc-teams` | Knowledge-Capture Full | **Correct — confirmed by Codex** | User-triggered per v1.14.0 ADR |
| `/self-improve`, `/release`, `/debug`, `/learner`, `/skillify`, `/deepinit`, `/remember` | — | Correct | Out of scope for chain routing |

---

## Recommendations (prioritized)

| # | Recommendation | Severity | Effort | Dimension | Risk if deferred |
|---|---|---|---|---|---|
| R1 | Rewrite `omc-integration.md:§4.1` + `§6` — correct autopilot phase numbers (Execution=2, Cleanup=5); retire fictional OMC_EXECUTION_ONLY; adopt Option (a) "intentional double-review" OR Option (c) prompt-instruction stop-after-Phase-3 | **High** | S (1-2h) | D6 | Documentation lies about the handback boundary |
| R2 | Replace `/ultrawork` with `/autopilot` in Greenfield Heavy Path B step 3; update `omc-integration.md:57` and the handback table | **High** | S (30m) | D1.1 | Greenfield Heavy silently skips QA + Validation + Cleanup |
| R3 | Back-port v1.14.0 probe: add `HAS_CODEX` / `HAS_GEMINI` to SKILL.md; gate the 10 fan-out call sites | Medium | M (3-4h) | D4.1 | Silent failure on hosts missing vendor CLIs |
| R4 | *(new from Codex)* Add chain conformance lint test — greps for stale strings like `"Phase 5 (docs/ship)"`, `"OMC_EXECUTION_ONLY"`, phase-number claims — across all chain + reference files. Fails CI on match. | **High** | S (1-2h) | D6 meta | Exact drift recurs |
| R5 | *(new from Codex)* Write cross-chain consistency ADR: "uniform operator mental model" vs "best specialized OMC skill per scenario." Audit assumes the latter; the code suggests the former. Resolving before acting on R7/R9/R10. | **High** | S (1-2h) | meta | Recommendations downstream of this are premature without the decision |
| R6 | *(new from Codex)* Document cancellation / rollback UX: when to `/oh-my-claudecode:cancel` vs resume vs abandon Path B. What does the user see on abnormal exit? Add to `omc-integration.md` or new `references/path-b-operations.md`. | Medium | S (1-2h) | meta | Users lack guidance when Path B stalls |
| R7 | *(new from Codex)* Explicit failure signaling — define the exact artifact/marker that proves `<<HANDBACK>>` fired; define user-visible message on abnormal exit | Medium | S (1h) | D6 meta | Silent failure looks like "still running" |
| R8 | For Light variants, route to `/omc-plan --direct` instead of `/deep-interview` | Medium | S (1h) | D2.1 | Burns interview cycles on already-specific tasks |
| R9 | Document `/ai-slop-cleaner` as alternate engine for Hygiene Light when "deslop"/"anti-slop" in prompt (keep `/autopilot` as default). Gated on R5 resolving in favor of best-specialized | Medium | S (30m) | D3.1 | Explicit-deslop users get generic pipeline |
| R10 | Add `/external-context` as pre-step 1 for Migration Medium/Heavy | Medium | S (1h) | D3.2 | Framework upgrades reason from stale training data |
| R11 | Add conditional `(if UI with design reference)` → `/visual-verdict` to Greenfield UI closeouts | Medium | S (1h) | D3.4 | No deterministic visual fidelity gate |
| R12 | Add optional `/ultraqa --tests` pre-gate for Light/Medium closeouts (conditional on hard pass-fail target in spec) | Medium | S (1h) | D3.3 | Mechanical failures surface only during human review |
| R13 | Extend telemetry with completion NDJSON line: `{chain_id, engine_invoked, handback_fired, duration_minutes, outcome}` | Medium | M (3-4h) | D5.3 | No feedback loop for OR-any signal rule validation |
| R14 | Document implicit "codex for code, ccg for plans" rule as Section 7 of `omc-integration.md` | Low | S (20m) | D4.2 | Chain edits may drift from convention |
| R15 | Fix "verbatim" → "superset of" at `omc-integration.md:111` + document delta keywords | Low | S (10m) | D5.1 | False claim about canonical list |
| R16 | Document multi-module signal as "LLM-judgment call during triage (no mechanical counter)" at `omc-integration.md:84` | Low | S (10m) | D5.2 | Implementation opacity |
| R17 | Remove Ship Standalone Path B block entirely (doc says "discouraged", UX exposes it) | Low | S (10m) | D1.4 | Exposes a path the doc recommends against |
| R18 | Write ADR for `/ccg` vs `/plan --critic codex` for plan review | Low | S (1h) | D4.3 | Undocumented choice may churn |

**Total effort (all 18):** ~25-35 hours (most items are S = <2h).

**Sequence guidance:**
- **Do first:** R1, R2, R4, R5 (the doc-drift blockers + the meta-decision that gates downstream work)
- **Do next:** R3, R6, R7 (operational safety + UX gaps)
- **Conditional on R5's decision:** R8, R9, R10, R11, R12 (specialized routings — only if R5 resolves in favor of best-specialized)
- **Housekeeping anytime:** R13–R18

---

## Codex Review Notes (disposition of adversarial feedback)

All Codex feedback received from artifact at `.omc/artifacts/ask/codex-read-the-omc-routing-audit-draft-at-users-sunginkim-superset-2026-04-15T03-32-55-851Z.md`. Eight substantive points; disposition:

| Codex point | Disposition | Rationale |
|---|---|---|
| 1. D6 is real doc drift but "ship-blocker" overstates it | **Accepted** | Severity downgraded to High. Section 6 already labels mechanism unresolved; practical impact is bad docs, not undefined runtime behavior |
| 2. D1.1 Greenfield Heavy /ultrawork is a real misfit | **Accepted (agreement)** | Finding kept as High severity |
| 3. D3.1 /ai-slop-cleaner is debatable, not obviously a gap | **Accepted** | Severity downgraded from High to Medium. Recommendation rewritten as "alternate engine for explicit deslop prompts" not "replace /autopilot" |
| 4. D2.2 /deep-dive for Bugfix is arguable | **Accepted** | Reframed from Gap to "Possible optimization (low severity)". Documented as operator choice |
| 5. D2.3 /sciomc for Performance is weak | **Accepted** | Finding removed entirely. Not reportable |
| 6a. Missing rec: cancellation / rollback UX | **Accepted** | Added as R6 |
| 6b. Missing rec: explicit failure signaling | **Accepted** | Added as R7 |
| 6c. Missing rec: chain conformance tests | **Accepted** | Added as R4 (elevated to High priority — directly prevents D6 recurrence) |
| 6d. Missing rec: cross-chain consistency ADR (uniform vs specialized) | **Accepted** | Added as R5. Also added to top-of-report as Framing Note. This is the most important single point of the Codex review — it reframes several audit findings as downstream of an unresolved product decision |
| 7. /verify and /omc-teams correctly not routed | **Accepted (agreement)** | Cross-reference table updated to mark as "confirmed by Codex" |

**No Codex points rejected.** Codex's review substantively changed the report's severity distribution (no ship-blockers remain; 3 findings downgraded; 1 removed; 4 recommendations added). The meta-point about uniform vs specialized routing (R5) is carried to the Framing Note as a decision gate for future work.

---

## Appendix: Evidence file paths

**Ark workflow (this branch):**
- `skills/ark-workflow/SKILL.md` — HAS_OMC probe (51–63), Step 6 dual-mode (210–254)
- `skills/ark-workflow/references/omc-integration.md` — Sections 0–6
- `skills/ark-workflow/chains/{bugfix,greenfield,hygiene,migration,performance,ship,knowledge-capture}.md`
- `skills/ark-workflow/references/troubleshooting.md:23`
- `skills/ark-context-warmup/scripts/check_path_b_coverage.py`

**OMC plugin cache (v4.11.5):**
- `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/ultrawork/SKILL.md:19-24` (D1.1 evidence)
- `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/autopilot/SKILL.md:39-72` (D6 evidence)
- `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/ai-slop-cleaner/SKILL.md:13-24` (D3.1 evidence)
- `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/deep-interview/SKILL.md:26-31` (D2.1 evidence)
- `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/omc-reference/SKILL.md:89-101` (D5.1 canonical list)

**Recent git:**
- `0376ebc` (v1.14.0, unpushed) — `omc ask` vendor fan-out
- `842d0ff` (v1.13.0) — dual-mode integration
- `134b7ba` — post-v1.13.0 doc sync
- Unstaged WIP on this branch — chain call-site rename `/codex → /ask codex|/ccg`

**Audit artifacts:**
- Draft: `.omc/drafts/omc-routing-audit-draft-2026-04-14.md`
- Codex review: `.omc/artifacts/ask/codex-read-the-omc-routing-audit-draft-at-users-sunginkim-superset-2026-04-15T03-32-55-851Z.md`
- Final report (this file): `.ark-workflow/audits/omc-routing-audit-2026-04-14.md`

---

## Implementation addendum — 2026-04-15

Six atomic commits landed on branch `ark-workflow-improve-OMC` implementing
the uniformity refactor. Order reflects the commit-sequence optimization
that R15+R16+R17 ran before R4 so the drift lint had clean input.

| # | Ref | SHA | Subject |
|---|-----|-----|---------|
| — | pre-R1 WIP | `0856b8e` | `/codex → /ask codex \| /ccg` call-site rename (v1.14.0 alignment) |
| 1 | R1 | `b3926c3` | Rewrite omc-integration.md §4.1 + §6; delete §4.2/§4.3 (/ralph, /ultrawork); renumber §4.4→§4.2 (/team), §4.5→§4.3 (crash recovery); migration.md cross-refs updated |
| 2 | R2 | `1b5b8ae` | Collapse Path B engines to uniform /autopilot (greenfield Heavy /ultrawork→/autopilot, performance Med+Heavy /ralph→/autopilot); propagate new step-3 wording to all 15 Vanilla blocks; Special-A + Special-B step-3 updated; check_path_b_coverage.py + test fixed (pre-existing 19→18 drift resolved) |
| 3 | R15+R16+R17 | `bf0187d` | "Verbatim" → "Superset of" + document Ark-added keywords; Signal #3 parenthetical; remove Ship Standalone Path B block (chain + table rows); coverage tightened to 17/4 |
| 4 | R4 | `3294d9e` | check_chain_drift.py + pytest harness (banned patterns: OMC_EXECUTION_ONLY, Phase 5 (docs/ship), internal Phase 4 (execution), /ralph+/ultrawork as step-3 engines) |
| 5 | R10 | `5856c2c` | /external-context pre-step for Migration Medium + Heavy Path B; classifier-vs-hash distinction documented; max_distinct_shapes 4→5 |
| 6 | R11 + addendum | *(this commit)* | /visual-verdict closeout for Greenfield Medium + Heavy UI variants; SKILL.md Condition Resolution entry for "UI with design reference"; audit addendum |

### V1 — Runtime probe: CONFIRMED (static + runtime, 2026-04-15)

**Static verification (session 8, 2026-04-14).** Grep of
`~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/autopilot/SKILL.md`
confirmed the auto-skip premise is explicit at lines 41, 42, 173–189.

**Runtime probe (session 9, 2026-04-15).** Probe fixtures
(`.omc/specs/deep-interview-probe.md`, `.omc/plans/ralplan-probe.md`) were
placed, then `/oh-my-claudecode:autopilot` invoked with task
`probe — print hello world`. The skill detected both artifacts on first
file check; ralplan rule (line 41) took precedence over the spec-only
branch (line 42) as documented. Observed Phase 0 announcement verbatim:

> Detected `.omc/plans/ralplan-probe.md` (matches `ralplan-*.md` glob).
> Per 3-stage pipeline contract, the plan has already been
> Planner/Architect/Critic validated.
>
> **Skipping Phase 0 (Expansion)** — ralplan consensus plan exists;
> analyst+architect expansion unnecessary.
>
> **Skipping Phase 1 (Planning)** — ralplan consensus plan exists;
> architect plan creation and critic validation already done.
>
> **Jumping directly to Phase 2 (Execution)** with plan
> `.omc/plans/ralplan-probe.md`.
>
> Also noted: `.omc/specs/deep-interview-probe.md` present (matches
> `deep-interview-*.md`). Superseded by ralplan rule at line 41, which
> takes precedence over line 42's spec-only branch.

Runtime behavior matches the documented spec. The static premise
underlying R5 closure and the R2 engine collapse holds. Probe was
cancelled via `/oh-my-claudecode:cancel` before Phase 2 execution
(state_write `active=false`, state_clear `skill-active`). Probe
fixtures removed post-confirmation.

### V2 — Coverage check: PASS (17 blocks, 5 hashes → 4 classifier shapes)

Final state after all 6 commits:
```
$ python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains
OK: 17 Path B block(s); 5 distinct canonicalized shape(s)
```
Hash count is 5 (not 4) because Migration Medium + Heavy's R10
`/external-context` pre-step lengthens their block bodies by one line,
yielding distinct raw-text canonicalized hashes from the common vanilla
and /team forms. The ALLOWED_SHAPES distribution assertion (classifier
view) confirms 4 shapes: vanilla:14, team:1, special-a:1, special-b:1.
See `omc-integration.md` § Section 4 note on hash count vs shape count.

### V3 — Chain drift lint: PASS (zero banned patterns across 8 target files)

```
$ python3 skills/ark-context-warmup/scripts/check_chain_drift.py --root .
OK: zero banned patterns found across 8 target file(s)
```

### Completed recommendations

| # | Status | Commit |
|---|--------|--------|
| R1 | ✓ DONE | `b3926c3` |
| R2 | ✓ DONE | `1b5b8ae` |
| R4 | ✓ DONE | `3294d9e` |
| R10 | ✓ DONE | `5856c2c` |
| R11 | ✓ DONE | *(this commit)* |
| R15 | ✓ DONE | `bf0187d` |
| R16 | ✓ DONE | `bf0187d` |
| R17 | ✓ DONE | `bf0187d` |

### Obsolete recommendations (under uniformity)

| # | Status | Reason |
|---|--------|--------|
| R5 | ✓ RESOLVED 2026-04-14 (static) + 2026-04-15 (runtime) | Uniformity decision captured in memory file; auto-skip premise verified both statically (session 8) and at runtime via live probe (session 9) |
| R8 | ✗ OBSOLETE | "/omc-plan --direct for Light variants" is redundant under uniformity — the front-end stays /deep-interview across all variants |
| R9 | ✗ OBSOLETE | "/ai-slop-cleaner as alternate engine for Hygiene" — Signal #1 keyword trigger handles the explicit-deslop case without chain-level branching |

### Pending recommendations (deferred to follow-up sessions)

| # | Severity | Effort | Rationale for deferral |
|---|----------|--------|------------------------|
| R3 | Medium | M (3-4h) | HAS_CODEX/HAS_GEMINI probe back-port; bundle with next shipping cycle |
| R6 | Medium | S (1-2h) | Cancellation/rollback UX doc; low urgency |
| R7 | Medium | S (1h) | Explicit failure signaling for <<HANDBACK>>; pairs with R6 |
| R12 | Medium | S (1h) | Optional /ultraqa pre-gate for Light/Medium closeouts |
| R13 | Medium | M (3-4h) | Telemetry completion NDJSON line; pairs with R3 shipping cycle |
| R14 | Low | S (20m) | Implicit "codex for code, ccg for plans" rule ADR; housekeeping |
| R18 | Low | S (1h) | ADR for /ccg vs /plan --critic codex; housekeeping |

### Scope refinements noted during implementation

1. **V2 expected hash count corrected from "2 shapes" to "4 classifier shapes /
   5 raw-text hashes".** The classifier keys on engine + closeout markers,
   preserving Special-A (STOP) and Special-B (/wiki-ingest) distinctions
   independent of engine uniformity. The `/external-context` pre-step from
   R10 adds a raw-text hash variant without changing classifier shape.
2. **chains/bugfix.md was a no-op for R2's engine collapse.** The Heavy
   Path B block already used /autopilot in the working copy (WIP state);
   only the §2 table row cleanup was needed.
3. **Pre-existing test drift fixed in R2.** `test_check_path_b_coverage.py`
   was asserting 19 blocks across 7 places while the script default was 18
   — the uniformity refactor normalized both to the post-R17 final count
   of 17 in the same commit sequence.
4. **Ship Standalone Path B elimination ordered before R4.** The drift
   lint's `Phase 5 (docs/ship)` banned pattern would have flagged the
   ship.md stale line until R17 removed the whole block. Swapping the
   R4/R17 order let the drift lint land against a clean state.
5. **No CI infrastructure exists in this repo.** The drift lint and
   coverage check both ship as pytest tests. Future session should add
   `.github/workflows/ci.yml` (or equivalent) that invokes both.
