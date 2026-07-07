# TODO — ark-skills

Deferred work items. Add new entries at the top.

---

## Downstream v2.0.0 convergence

**Priority:** P2
**Context:** the v2.0.0 restructure ships only the ark-skills plugin repo. Downstream
projects (ArkNode-AI — already converged, ArkNode-Poly, trading-signal-ai, …) still run
v1.x conventions until each is converged per-project via `/ark-update` (target profile
`pending_migrations`: `okf-conversion`, `gh-issues-adoption`). File one GitHub epic per
downstream project when convergence begins.

## ark-update engine v2 conversion

**Priority:** P2
**Context:** the ark-update Python engine (`scripts/ops/ensure_routing_rules_block.py`,
its migrate.py registration, the CLAUDE.md-routing-block tests, and the fixtures under
`tests/fixtures/`) still implements the retired v1 routing-injection. The v2 target
profile no longer invokes it. A follow-up should retire the routing op + its tests and
regenerate the fixtures against the v2 profile so `pytest skills/ark-update/tests/` is
green under the new profile.
