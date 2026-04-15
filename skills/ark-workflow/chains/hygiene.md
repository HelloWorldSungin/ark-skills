# Codebase Hygiene

## Audit-Only

*for "audit", "review", "assess" requests with no remediation expected*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/codebase-maintenance` — audit (or `/cso` if security audit)
2. Present findings report to the user
3. `/wiki-update` (if vault — to record findings)
4. **STOP** — do not implement, do not ship. Ask user: "Findings above. Do you want to create tickets via `/ark-tasknotes`, or proceed with fixes (I'll re-triage as Hygiene Light/Medium/Heavy)?"

### Path B (OMC-powered — if HAS_OMC=true)

*Findings-only — no code review, no ship.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on audit scope (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus audit plan
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts; produces findings document
4. `<<HANDBACK>>` — Ark resumes authority
5. **Ark closeout (Special-A):** `/wiki-update` (record findings in vault) → STOP. No code review, no ship — findings-only chain. See `references/omc-integration.md` § Section 4 (Special-A row).

## Light

0. `/ark-context-warmup` — load recent + relevant project context
1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. Implement cleanup
4. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Medium

0. `/ark-context-warmup` — load recent + relevant project context
1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
4. `/test-driven-development` — tests before restructuring
5. Implement cleanup
6. `/ark-code-review --quick` → `/simplify`
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault)

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --quick` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Heavy

0. `/ark-context-warmup` — load recent + relevant project context
1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. **If audit + investigation reveals systemic issues requiring rewrite: escalate to Heavy Greenfield. `/checkpoint` findings, end session, start fresh with design phase.**
4. `/cso` — infrastructure, dependency, secrets audit (this IS the mandatory `/cso` run — no duplicate later)
5. `/test-driven-development` — tests before restructuring
6. Implement cleanup
7. `/ark-code-review --thorough` + `/ask codex` → `/simplify`
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/claude-history-ingest`

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).

## Dedup rule

If security hardening triggers mandatory early `/cso` (before the chain starts), skip the conditional `/cso` inside the chain. `/cso` runs exactly once per chain execution.
