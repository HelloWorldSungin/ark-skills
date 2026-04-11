# TODO — ark-skills

Deferred work items. Add new entries at the top.

---

## Session log frontmatter backfill + S002 collision

**Priority:** P2
**Deferred from:** 1.8.0 (session log consolidation into /wiki-update)
**Why:** existing session logs in `vault/Session-Logs/` (S001, S002×2, S003, S004) lack the new `date:` and `status:` fields added in 1.8.0. They still parse cleanly against `_meta/generate-index.py` via `.get()` defaults, so no hard break. `/wiki-update` Step 2's skip-detection falls back through `date → last-updated → created → mtime` to handle them.

**Two tasks, one PR:**
1. Backfill `date:` and `status: complete` frontmatter into the 5 existing session logs.
2. Resolve the pre-existing `S002` numbering collision: `S002-Ark-Workflow-Skill.md` and `S002-Vault-Retrieval-Tiers-Phase1.md` both claim session number 2. Pick whichever is canonically S002 (probably the earlier-created one by `created:` date) and renumber the other. Update filename, `session:` frontmatter, any `prev:` references in later logs, re-run the index generator.

**Scope:** ~10 minutes of edits + verify `python3 vault/_meta/generate-index.py` still green.
