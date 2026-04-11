# Codebase Hygiene

## Audit-Only

*for "audit", "review", "assess" requests with no remediation expected*

1. `/codebase-maintenance` — audit (or `/cso` if security audit)
2. Present findings report to the user
3. `/wiki-update` (if vault — to record findings)
4. **STOP** — do not implement, do not ship. Ask user: "Findings above. Do you want to create tickets via `/ark-tasknotes`, or proceed with fixes (I'll re-triage as Hygiene Light/Medium/Heavy)?"

## Light

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. Implement cleanup
4. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

## Medium

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
4. `/test-driven-development` — tests before restructuring
5. Implement cleanup
6. `/ark-code-review --quick` → `/simplify`
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault)

## Heavy

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. **If audit + investigation reveals systemic issues requiring rewrite: escalate to Heavy Greenfield. `/checkpoint` findings, end session, start fresh with design phase.**
4. `/cso` — infrastructure, dependency, secrets audit (this IS the mandatory `/cso` run — no duplicate later)
5. `/test-driven-development` — tests before restructuring
6. Implement cleanup
7. `/ark-code-review --thorough` + `/codex` → `/simplify`
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/claude-history-ingest`

## Dedup rule

If security hardening triggers mandatory early `/cso` (before the chain starts), skip the conditional `/cso` inside the chain. `/cso` runs exactly once per chain execution.
