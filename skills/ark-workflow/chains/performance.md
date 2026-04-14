# Performance

## Light

*single hotspot fix, obvious optimization*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — profile and identify the bottleneck
2. Fix the hotspot
3. Verify improvement (before/after timing or metric)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)

*Note: Path B is unusual for Performance Light. Shown for discoverability per spec — see `references/omc-integration.md` § Section 2.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — execution only; skips autopilot's internal Phase 5 (docs/ship). See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Medium

*multiple hotspots, caching layer, query optimization*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — profile and identify bottlenecks
2. `/benchmark` — establish baseline metrics (if available)
3. `/test-driven-development` — write performance regression tests
4. Implement optimizations
5. `/benchmark` — verify improvement against baseline
6. `/ark-code-review --quick` → `/simplify`
7. `/cso` (if security-relevant — e.g., caching introduces data exposure)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

*Note: Path B uses `/ralph` as the execution engine (loop-to-verified until benchmark target met). Handback contract: `references/omc-integration.md` § Section 4.2.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + loop-to-verified execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/ralph` — loop-to-verified against benchmark target; exits on success criterion met. See `references/omc-integration.md` § Section 4.2 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority after `/ralph`'s success exit; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (/ralph row).

## Heavy

*architecture-level optimization, data layer redesign*

*Session 1 — Analysis & Planning:*
0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — deep profiling, identify systemic bottlenecks
2. `/benchmark` — comprehensive baseline
3. `/brainstorming` — optimization strategy (caching architecture, query redesign, etc.)
4. `/codex` — review the optimization plan
5. Commit plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read optimization plan
7. `/test-driven-development` — performance regression tests
8. Implement optimizations in stages
9. `/benchmark` — verify improvement per stage
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
11. `/cso` (if security-relevant)
12. `/ship` → `/land-and-deploy`
13. `/canary` — **mandatory for Heavy performance changes** (not conditional)

*Document:*
14. `/wiki-update` (if vault)
15. `/wiki-ingest` (if vault + optimization introduces new architecture)
16. `/cross-linker` (if vault)
17. Session log
18. `/claude-history-ingest`

*Note: Path B uses `/ralph` as the execution engine (loop-to-verified until benchmark target met). Handback contract: `references/omc-integration.md` § Section 4.2.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + loop-to-verified execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/ralph` — loop-to-verified against benchmark target; exits on success criterion met. See `references/omc-integration.md` § Section 4.2 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority after `/ralph`'s success exit; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (/ralph row).
