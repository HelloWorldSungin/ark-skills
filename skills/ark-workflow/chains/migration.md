# Migration

## Light

*patch/minor version bumps, non-breaking dependency updates*

0. `/ark-context-warmup` — load recent + relevant project context
1. Read migration/upgrade guide for the dependency
2. Implement upgrade
3. Run tests — verify nothing broke
4. `/cso` (if security-relevant — major bumps, known CVEs)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

*Note: Path B is unusual for Migration Light. Shown for discoverability per spec — see `references/omc-integration.md` § Section 2.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — execution only; skips autopilot's internal Phase 5 (docs/ship). See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Medium

*major version bumps, API changes required*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — audit current usage of the thing being migrated
2. Read migration guide, identify breaking changes
3. `/test-driven-development` — write tests for new API surface before migrating
4. Implement migration
5. `/ark-code-review --quick` → `/simplify`
6. `/cso` (if security-relevant)
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault)
10. Session log

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — execution only; skips autopilot's internal Phase 5 (docs/ship). See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Heavy

*framework migrations, platform changes, database migrations*

*Session 1 — Planning:*
0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — audit all usage, map blast radius
2. `/brainstorming` — migration strategy (big bang vs incremental, feature flags, rollback plan)
3. `/ccg` — multi-advisor migration plan review
4. Commit migration plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-4`)

*Session 2 — Implementation:*
5. Read migration plan
6. `/test-driven-development` — tests for new platform/framework before migrating
7. Implement migration in stages (per the plan)
8. `/ark-code-review --thorough` + `/ask codex` → `/simplify`
9. `/cso` (if security-relevant)
10. `/ship` → `/land-and-deploy`
11. `/canary` — **mandatory for Heavy migrations** (not conditional)

*Document:*
12. `/wiki-update` (if vault)
13. `/wiki-ingest` (if vault + migration introduces new architecture concepts)
14. `/cross-linker` (if vault)
15. `/document-release` (if standard docs exist)
16. Session log
17. `/claude-history-ingest`

*Note: Path B uses `/team` as the execution engine (coordinated cross-module migration via `team-plan → team-prd → team-exec → team-verify`). Handback contract: `references/omc-integration.md` § Section 4.2 — `<<HANDBACK>>` fires after `team-verify`, **before** `team-fix`. Bounded remediation (`team-fix`) is reserved for Ark's review loop if `/ark-code-review` concurs with residual defects.*

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + coordinated multi-agent execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/team` — coordinated cross-module migration; follows omc-reference pipeline `team-plan → team-prd → team-exec → team-verify`. See `references/omc-integration.md` § Section 4.2 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority after `team-verify`, **before** `team-fix` (bounded remediation reserved for Ark's review). `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward. If Ark review concurs with residual defects from `team-verify`, invoke `team-fix` from within Ark's review; otherwise proceed to `/ship`. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (/team row).
