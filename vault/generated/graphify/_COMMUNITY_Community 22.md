---
type: community
cohesion: 0.11
members: 25
---

# Community 22

**Cohesion:** 0.11 - loosely connected
**Members:** 25 nodes

## Members
- [[12-char content hash embedded as an HTML comment; used to block duplicate append]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[Atomic + idempotent continuation append. Returns True iff a write occurred.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[Atomic + idempotent. Returns True iff a write occurred.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[Atomic text write via tmp + os.replace. Cleans up tmp on failure.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[C1 ark-source-path='....evil.md' must NOT resolve outside project_docs.]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[Component 3 wiki-update Step 3.5 — promote OMC pages to Ark vault.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[Exact-slug match only. Callers must handle None (no silent cross-session fallbac]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[H1 _append_to_session_log writes via tmp+rename and does not leave a partial fi]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H2 no silent fallback to newest Session-Logs.md — must return None on slug mi]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[Path_49]] - code - skills/wiki-update/scripts/promote_omc.py
- [[PromotionReport]] - code - skills/wiki-update/scripts/promote_omc.py
- [[Resolve ark-source-path inside project_docs with path-traversal containment.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[_append_to_session_log()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_atomic_write_text()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_create_review_tasknote()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_find_session_log()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_idempotency_marker()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_merge_into_existing()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[_resolve_existing_vault_page()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[derive_summary()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[promote_omc.py]] - code - skills/wiki-update/scripts/promote_omc.py
- [[test_append_to_session_log_atomic_via_tmp_rename_H1()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_derive_summary_truncated_to_200()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_find_session_log_returns_none_on_miss_H2()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_path_traversal_ark_source_path_is_rejected_C1()]] - code - skills/wiki-update/scripts/test_promote_omc.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_22
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Community 8]]
- 3 edges to [[_COMMUNITY_Community 48]]
- 2 edges to [[_COMMUNITY_Community 20]]
- 2 edges to [[_COMMUNITY_Community 15]]

## Top bridge nodes
- [[promote_omc.py]] - degree 16, connects to 3 communities
- [[Path_49]] - degree 8, connects to 2 communities
- [[PromotionReport]] - degree 3, connects to 2 communities
- [[_append_to_session_log()]] - degree 7, connects to 1 community
- [[_merge_into_existing()]] - degree 6, connects to 1 community