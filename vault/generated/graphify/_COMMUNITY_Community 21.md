---
type: community
cohesion: 0.11
members: 25
---

# Community 21

**Cohesion:** 0.11 - loosely connected
**Members:** 25 nodes

## Members
- [[.' resolves to the root itself and is accepted.]] - rationale - skills/ark-update/tests/test_paths.py
- [[....etcpasswd' escapes root and is refused.]] - rationale - skills/ark-update/tests/test_paths.py
- [[..sibling' escapes root and is refused.]] - rationale - skills/ark-update/tests/test_paths.py
- [[A nested relative path stays inside root and is returned resolved.]] - rationale - skills/ark-update/tests/test_paths.py
- [[A simple relative path inside root returns a resolved absolute Path.]] - rationale - skills/ark-update/tests/test_paths.py
- [[A symlink pointing outside project_root is refused.]] - rationale - skills/ark-update/tests/test_paths.py
- [[Absolute Path object is also refused.]] - rationale - skills/ark-update/tests/test_paths.py
- [[Passing an absolute path raises PathTraversalError immediately.]] - rationale - skills/ark-update/tests/test_paths.py
- [[Path_23]] - code - skills/ark-update/scripts/paths.py
- [[Resolve candidate relative to project_root and verify it stays inside.]] - rationale - skills/ark-update/scripts/paths.py
- [[Safe path resolution for ark-update ops.  Contract ``safe_resolve(project_root,]] - rationale - skills/ark-update/scripts/paths.py
- [[Tests for skillsark-updatescriptspaths.py.  Covers the three rejection classe]] - rationale - skills/ark-update/tests/test_paths.py
- [[paths.py]] - code - skills/ark-update/scripts/paths.py
- [[safe_resolve()]] - code - skills/ark-update/scripts/paths.py
- [[subdir..file.txt' resolves inside root and is accepted.]] - rationale - skills/ark-update/tests/test_paths.py
- [[test_absolute_path_as_path_object_is_refused()]] - code - skills/ark-update/tests/test_paths.py
- [[test_absolute_path_is_refused()]] - code - skills/ark-update/tests/test_paths.py
- [[test_dotdot_escape_is_refused()]] - code - skills/ark-update/tests/test_paths.py
- [[test_dotdot_that_stays_inside_root_is_accepted()]] - code - skills/ark-update/tests/test_paths.py
- [[test_paths.py]] - code - skills/ark-update/tests/test_paths.py
- [[test_root_itself_as_dot_is_accepted()]] - code - skills/ark-update/tests/test_paths.py
- [[test_single_dotdot_to_parent_is_refused()]] - code - skills/ark-update/tests/test_paths.py
- [[test_symlink_escape_is_refused()]] - code - skills/ark-update/tests/test_paths.py
- [[test_valid_nested_relative_path()]] - code - skills/ark-update/tests/test_paths.py
- [[test_valid_relative_path_returns_resolved()]] - code - skills/ark-update/tests/test_paths.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_21
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Community 0]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 12]]

## Top bridge nodes
- [[safe_resolve()]] - degree 15, connects to 3 communities
- [[paths.py]] - degree 3, connects to 1 community