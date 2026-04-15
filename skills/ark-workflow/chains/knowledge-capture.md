# Knowledge Capture

Requires vault — if `HAS_VAULT=false`, tell the user to run `/wiki-setup` first. (This should already be caught by the early exit in Project Discovery.)

## Light

*syncing recent changes, updating a few pages*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/wiki-update` — end-of-session workflow (session log, TaskNote update, insight extraction, index regen)
2. `/cross-linker` (if vault)

### Path B (OMC-powered — if HAS_OMC=true)

*Reflective capture with front-loaded mining + autonomous synthesis.*

0. `/ark-context-warmup` — same as Path A
1. `/claude-history-ingest` — mine recent conversations as capture source (substitutes for `/deep-interview` since capture is reflective)
2. `/omc-plan --consensus` — plan the capture (wiki pages, tags, cross-links)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts; runs `/wiki-ingest` + `/cross-linker` + `/tag-taxonomy`
4. `<<HANDBACK>>` — Ark resumes authority
5. **Ark closeout (Special-B):** `/wiki-update` (finalize session log + epic) → `/claude-history-ingest` (final mining sweep). No code review, no ship — capture-only chain. See `references/omc-integration.md` § Section 4 (Special-B row).

## Full

*catching up after extended period, rebuilding tags, ingesting external docs*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/wiki-status` — vault statistics
2. `/wiki-lint` — broken links, missing frontmatter, tag violations
3. `/wiki-update` — end-of-session workflow (session log, TaskNote update, insight extraction, index regen)
4. `/wiki-ingest` — distill external documents if needed
5. `/cross-linker` — discover missing wikilinks
6. `/tag-taxonomy` — normalize tags
7. `/claude-history-ingest` — mine recent sessions

Knowledge-Capture **Full** intentionally has no Path B block. Full-variant capture is too broad and too branchy for a single-engine autonomous pass — `/omc-teams` with a Gemini 1M-context worker was considered but rejected as auto-routed behavior (orchestration-model mismatch; keeps `/omc-teams` a user-triggered power tool instead). Users who want autonomous bulk capture can invoke `/omc-teams 1:gemini "<task>"` manually, or run the Path A steps above with `/autopilot` invocations on the individual sub-steps.
