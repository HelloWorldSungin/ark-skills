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

## Heavy

*framework migrations, platform changes, database migrations*

*Session 1 — Planning:*
0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — audit all usage, map blast radius
2. `/brainstorming` — migration strategy (big bang vs incremental, feature flags, rollback plan)
3. `/codex` — review the migration plan
4. Commit migration plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-4`)

*Session 2 — Implementation:*
5. Read migration plan
6. `/test-driven-development` — tests for new platform/framework before migrating
7. Implement migration in stages (per the plan)
8. `/ark-code-review --thorough` + `/codex` → `/simplify`
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
