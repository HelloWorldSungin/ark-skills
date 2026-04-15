# Greenfield Feature

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
2. `/ask codex` — single-advisor spec review
3. Commit spec → **end session, start fresh for implementation** (set `handoff_marker: after-step-3`)

*Session 2 — Implementation:*
4. Read spec from `docs/superpowers/specs/`
5. `/test-driven-development` — write tests first, implement against them
6. `/ark-code-review --quick` → `/simplify`
7. `/qa` (if UI)
8. `/cso` (if security-relevant)
9. `/ship` → `/land-and-deploy`
10. `/canary` (if deploy risk)

*Document:*
11. `/wiki-update` (if vault)
12. `/wiki-ingest` (if vault + new component needs its own page)
13. `/cross-linker` (if vault)
14. `/document-release` (if standard docs exist)
15. Session log

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
2. `/ccg` — multi-advisor spec review (architecture + alternatives, synthesized)
3. `/writing-plans` — break into phased implementation plan
4. `/ccg` — multi-advisor plan review
5. Commit spec + plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/test-driven-development` per step
8. `/subagent-driven-development` — parallelize independent modules
9. `/checkpoint` (optional — if pausing mid-implementation)
10. `/ark-code-review --thorough` + `/ask codex` → `/simplify`
11. `/qa` (if UI)
12. `/design-review` (if UI)
13. `/cso` (if security-relevant)
14. `/ship` → `/land-and-deploy`
15. `/canary` (if deploy risk)

*Document:*
16. `/wiki-update` (if vault)
17. `/wiki-ingest` (if vault + new component needs its own page)
18. `/cross-linker` (if vault)
19. `/document-release` (if standard docs exist)
20. Session log
21. `/claude-history-ingest`

*Note: Path B uses `/autopilot` as the execution engine. Multi-module parallelism is handled inside autopilot's Phase 2 (Execution via internal /ultrawork). Handback contract: `references/omc-integration.md` § Section 4.1.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).
