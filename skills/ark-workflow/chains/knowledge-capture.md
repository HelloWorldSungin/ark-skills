# Knowledge Capture

Requires vault — if `HAS_VAULT=false`, tell the user to run `/wiki-setup` first. (This should already be caught by the early exit in Project Discovery.)

## Light

*syncing recent changes, updating a few pages*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/wiki-update` — end-of-session workflow (session log, TaskNote update, insight extraction, index regen)
2. `/cross-linker` (if vault)

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
