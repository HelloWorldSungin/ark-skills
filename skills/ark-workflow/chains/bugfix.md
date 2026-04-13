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

## Heavy

0. `/ark-context-warmup` — load recent + relevant project context
1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected. **If investigation reveals architectural redesign is needed: `/checkpoint` findings, end session, start fresh with a design phase (pivot to Heavy Greenfield from step 1).**
3. `/test-driven-development` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix (structured, may require `/executing-plans`)
5. `/ark-code-review --thorough` + `/codex` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/wiki-ingest` (if vault + fix introduces a new concept)
12. `/cross-linker` (if vault)
13. Session log
14. `/claude-history-ingest`
