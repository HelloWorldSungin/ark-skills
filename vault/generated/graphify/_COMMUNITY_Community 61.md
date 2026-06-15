---
type: community
cohesion: 0.18
members: 11
---

# Community 61

**Cohesion:** 0.18 - loosely connected
**Members:** 11 nodes

## Members
- [[Clock skew older semver has a NEWER applied_at timestamp — still returns max se]] - rationale - skills/ark-update/tests/test_state.py
- [[Partial entries do not count toward installed_version.]] - rationale - skills/ark-update/tests/test_state.py
- [[Phase-2 (convergence) entries do not count toward installed_version.]] - rationale - skills/ark-update/tests/test_state.py
- [[Return the maximum successful semver across Phase-1 (destructive) log entries.]] - rationale - skills/ark-update/scripts/state.py
- [[computed_installed_version()]] - code - skills/ark-update/scripts/state.py
- [[installed_version is the max semver, regardless of entry order or timestamps.]] - rationale - skills/ark-update/tests/test_state.py
- [[test_installed_version_clock_skew_case()]] - code - skills/ark-update/tests/test_state.py
- [[test_installed_version_empty_entries_returns_zero()]] - code - skills/ark-update/tests/test_state.py
- [[test_installed_version_max_semver_not_timestamp_order()]] - code - skills/ark-update/tests/test_state.py
- [[test_installed_version_only_counts_clean_results()]] - code - skills/ark-update/tests/test_state.py
- [[test_installed_version_only_counts_destructive_phase()]] - code - skills/ark-update/tests/test_state.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_61
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Community 43]]
- 4 edges to [[_COMMUNITY_Community 33]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 42]]
- 1 edge to [[_COMMUNITY_Community 68]]

## Top bridge nodes
- [[computed_installed_version()]] - degree 10, connects to 4 communities
- [[test_installed_version_clock_skew_case()]] - degree 4, connects to 2 communities
- [[test_installed_version_max_semver_not_timestamp_order()]] - degree 4, connects to 2 communities
- [[test_installed_version_only_counts_clean_results()]] - degree 4, connects to 2 communities
- [[test_installed_version_only_counts_destructive_phase()]] - degree 4, connects to 2 communities