# Greenfield Feature

## Light

*rare for greenfield*

1. Implement directly
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

## Medium

*Session 1 — Design:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
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

## Heavy

*Session 1 — Design & Planning:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. `/writing-plans` — break into phased implementation plan
4. `/codex` — review the plan
5. Commit spec + plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/test-driven-development` per step
8. `/subagent-driven-development` — parallelize independent modules
9. `/checkpoint` (optional — if pausing mid-implementation)
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
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
