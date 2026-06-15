---
type: community
cohesion: 0.14
members: 15
---

# Community 43

**Cohesion:** 0.14 - loosely connected
**Members:** 15 nodes

## Members
- [[A lock file with a dead PID is silently reclaimed.]] - rationale - skills/ark-update/tests/test_state.py
- [[Acquiring a lock we already hold raises RuntimeError (same process).]] - rationale - skills/ark-update/tests/test_state.py
- [[Ensure ``.ark`` exists; return the installed version string.      Creates ``.ar]] - rationale - skills/ark-update/scripts/state.py
- [[Tests for skillsark-updatescriptsstate.py.  Covers   - Log append  parse ro]] - rationale - skills/ark-update/tests/test_state.py
- [[bootstrap()]] - code - skills/ark-update/scripts/state.py
- [[release_lock does not raise if lock does not exist.]] - rationale - skills/ark-update/tests/test_state.py
- [[test_acquire_creates_lock_file()]] - code - skills/ark-update/tests/test_state.py
- [[test_bootstrap_creates_ark_dir()]] - code - skills/ark-update/tests/test_state.py
- [[test_bootstrap_missing_log_returns_zero_zero_zero()]] - code - skills/ark-update/tests/test_state.py
- [[test_double_acquire_same_pid_raises()]] - code - skills/ark-update/tests/test_state.py
- [[test_read_log_missing_file_returns_empty_list()]] - code - skills/ark-update/tests/test_state.py
- [[test_release_lock_noop_if_not_held()]] - code - skills/ark-update/tests/test_state.py
- [[test_release_lock_removes_file()]] - code - skills/ark-update/tests/test_state.py
- [[test_stale_pid_lock_is_reclaimed()]] - code - skills/ark-update/tests/test_state.py
- [[test_state.py]] - code - skills/ark-update/tests/test_state.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_43
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 33]]
- 6 edges to [[_COMMUNITY_Community 61]]
- 6 edges to [[_COMMUNITY_Community 68]]
- 3 edges to [[_COMMUNITY_Community 80]]
- 2 edges to [[_COMMUNITY_Community 42]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[bootstrap()]] - degree 9, connects to 5 communities
- [[test_state.py]] - degree 30, connects to 4 communities
- [[test_read_log_missing_file_returns_empty_list()]] - degree 2, connects to 1 community