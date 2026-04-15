# Bug Investigation & Fix

## Light

0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — root cause analysis
2. Fix directly
3. `/cso` (if security-relevant)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)
7. Session log (only if surprising root cause)

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
1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected
3. `/test-driven-development` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix
5. `/ark-code-review --quick` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

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
1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected. **If investigation reveals architectural redesign is needed: `/checkpoint` findings, end session, start fresh with a design phase (pivot to Heavy Greenfield from step 0 — the mandatory `/ark-context-warmup` still runs first).**
3. `/test-driven-development` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix (structured, may require `/executing-plans`)
5. `/ark-code-review --thorough` + `/ask codex` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/wiki-ingest` (if vault + fix introduces a new concept)
12. `/cross-linker` (if vault)
13. Session log
14. `/claude-history-ingest`

### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --thorough` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).
