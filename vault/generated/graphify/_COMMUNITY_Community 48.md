---
type: community
cohesion: 0.20
members: 14
---

# Community 48

**Cohesion:** 0.20 - loosely connected
**Members:** 14 nodes

## Members
- [[C2 finalize_deletes(require=...) must refuse to delete when a required     de]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[CLI entry point for wiki-update Step 3.5. Orchestrates promote() → index regen]] - rationale - skills/wiki-update/scripts/cli_promote.py
- [[Execute pending deletes only if all `require` paths exist and are non-empty.]] - rationale - skills/wiki-update/scripts/promote_omc.py
- [[Path_48]] - code - skills/wiki-update/scripts/cli_promote.py
- [[PromotionConfig]] - code - skills/wiki-update/scripts/promote_omc.py
- [[Read session-log `created` frontmatter. Falls back to mtime if absent.]] - rationale - skills/wiki-update/scripts/cli_promote.py
- [[_run_index_regen()]] - code - skills/wiki-update/scripts/cli_promote.py
- [[_session_created_at()]] - code - skills/wiki-update/scripts/cli_promote.py
- [[cli_promote.py]] - code - skills/wiki-update/scripts/cli_promote.py
- [[finalize_deletes()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[main()_15]] - code - skills/wiki-update/scripts/cli_promote.py
- [[test_finalize_deletes_gate_fails_when_required_path_empty_C2()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_finalize_deletes_gate_fails_when_required_path_missing_C2()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_finalize_deletes_gate_passes_when_required_path_valid_C2()]] - code - skills/wiki-update/scripts/test_promote_omc.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_48
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Community 8]]
- 3 edges to [[_COMMUNITY_Community 22]]
- 1 edge to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 15]]

## Top bridge nodes
- [[PromotionConfig]] - degree 6, connects to 3 communities
- [[main()_15]] - degree 7, connects to 1 community
- [[finalize_deletes()]] - degree 7, connects to 1 community
- [[_session_created_at()]] - degree 5, connects to 1 community
- [[test_finalize_deletes_gate_fails_when_required_path_missing_C2()]] - degree 3, connects to 1 community