# Greenfield Feature

*Greenfield assumes implementation commitment. If step 1 `/brainstorming` reveals scope uncertainty ("I don't know if this is the right thing", "should we even build this"), pivot to Brainstorm scenario — see `SKILL.md § When Things Change § Scope-retreat pivot`.*

## Light

*rare for greenfield*

0. `/ark-context-warmup` — load recent + relevant project context
1. Implement directly
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Medium

*Session 1 — Design:*
0. `/ark-context-warmup` — load recent + relevant project context
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/plan-design-review` (if gstack AND UI-with-design-reference) — design critique of the spec's design decisions; rates each dimension 0-10 and fixes toward 10. *(Note: at Medium scale, the spec from step 1 is the design-review target — there's no separate `/writing-plans` artifact as in Heavy.)*
3. `/plan-devex-review` (if gstack AND developer-facing surface) — developer-experience critique of the spec's API/CLI/SDK decisions. *(Same note as step 2: operates on the spec at Medium scale.)*
4. `/ask codex` **[probe-gated §7]** — single-advisor spec review
5. Commit spec → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read spec from `docs/superpowers/specs/`
7. `/test-driven-development` — write tests first, implement against them
8. `/ark-code-review --quick` → `/simplify`
9. `/qa` (if UI)
10. `/visual-verdict` (if UI with design reference)
11. `/cso` (if security-relevant)
12. `/ship` → `/land-and-deploy`
13. `/canary` (if deploy risk)

*Document:*
14. `/wiki-update` (if vault)
15. `/wiki-ingest` (if vault + new component needs its own page)
16. `/cross-linker` (if vault)
17. `/document-release` (if standard docs exist)
18. Session log

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Heavy

*Session 1 — Design & Planning:*
0. `/ark-context-warmup` — load recent + relevant project context
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/ccg` **[probe-gated §7]** — multi-advisor spec review (architecture + alternatives, synthesized)
3. `/writing-plans` — break into phased implementation plan
4. `/ccg` **[probe-gated §7]** — multi-advisor plan review *(substitution: replaced by `/autoplan` when `HAS_GSTACK_PLANNING=true` — gstack multi-persona bundle (CEO+design+eng+DX) supersedes multi-model consensus for plan review. See SKILL.md § Heavy planning authority substitution. The step 2 `/ccg` spec review is NOT substituted — it reviews the spec, not the plan.)*
5. Commit spec + plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/test-driven-development` per step
8. `/subagent-driven-development` — parallelize independent modules
9. `/context-save` (optional — if pausing mid-implementation)
10. `/ark-code-review --thorough` + `/ask codex` **[probe-gated §7]** → `/simplify`
11. `/qa` (if UI)
12. `/design-review` (if UI)
13. `/visual-verdict` (if UI with design reference)
14. `/cso` (if security-relevant)
15. `/ship` → `/land-and-deploy`
16. `/canary` (if deploy risk)

*Document:*
17. `/wiki-update` (if vault)
18. `/wiki-ingest` (if vault + new component needs its own page)
19. `/cross-linker` (if vault)
20. `/document-release` (if standard docs exist)
21. Session log
22. `/claude-history-ingest`

*Note: Path B uses `/autopilot` as the execution engine. Multi-module parallelism is handled inside autopilot's Phase 2 (Execution via internal /ultrawork). Handback contract: `references/omc-integration.md` § Section 4.1.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).
