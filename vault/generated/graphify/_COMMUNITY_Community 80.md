---
type: community
cohesion: 0.25
members: 8
---

# Community 80

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[Compute the backup path for target_file under backups_dir.      Returns ``.a]] - rationale - skills/ark-update/scripts/state.py
- [[Different source files produce different backup basenames.]] - rationale - skills/ark-update/tests/test_state.py
- [[backup_path returns a path matching basename.UTC-ts.bak format.]] - rationale - skills/ark-update/tests/test_state.py
- [[backup_path timestamp suffix ends with 'Z' (UTC marker).]] - rationale - skills/ark-update/tests/test_state.py
- [[backup_path()]] - code - skills/ark-update/scripts/state.py
- [[test_backup_path_different_files_differ()]] - code - skills/ark-update/tests/test_state.py
- [[test_backup_path_format()]] - code - skills/ark-update/tests/test_state.py
- [[test_backup_path_uses_utc()]] - code - skills/ark-update/tests/test_state.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_80
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 43]]
- 2 edges to [[_COMMUNITY_Community 42]]
- 1 edge to [[_COMMUNITY_Community 0]]

## Top bridge nodes
- [[backup_path()]] - degree 7, connects to 2 communities
- [[test_backup_path_different_files_differ()]] - degree 3, connects to 1 community
- [[test_backup_path_format()]] - degree 3, connects to 1 community
- [[test_backup_path_uses_utc()]] - degree 3, connects to 1 community