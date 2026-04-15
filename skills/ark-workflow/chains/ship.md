# Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

*Note: Ship Standalone is Path A only — no Path B block. Ship is already
mechanical; the OMC-powered pipeline added no value and was retired in R17
of the 2026-04-15 uniformity refactor. See `references/omc-integration.md`
§ Section 2 for the rationale.*
