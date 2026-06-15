---
type: community
cohesion: 0.16
members: 18
---

# Community 33

**Cohesion:** 0.16 - loosely connected
**Members:** 18 nodes

## Members
- [[Append a single entry dict as a JSONL line.      This function performs a raw ap]] - rationale - skills/ark-update/scripts/state.py
- [[Conditionally append the log entry and rewrite the pointer.      Enforces the cl]] - rationale - skills/ark-update/scripts/state.py
- [[Duplicate (version, phase) pairs last-seen entry wins.]] - rationale - skills/ark-update/tests/test_state.py
- [[Existing log is byte-identical before and after a clean run.]] - rationale - skills/ark-update/tests/test_state.py
- [[_make_entry()]] - code - skills/ark-update/tests/test_state.py
- [[append_log()]] - code - skills/ark-update/scripts/state.py
- [[maybe_append_log_and_pointer()]] - code - skills/ark-update/scripts/state.py
- [[ops_ran=0 AND result='clean' must not write log or pointer.]] - rationale - skills/ark-update/tests/test_state.py
- [[ops_ran=1 allows log append and pointer rewrite.]] - rationale - skills/ark-update/tests/test_state.py
- [[result='partial' with ops_ran=0 still writes (not a clean run).]] - rationale - skills/ark-update/tests/test_state.py
- [[test_append_and_read_round_trip()]] - code - skills/ark-update/tests/test_state.py
- [[test_bootstrap_with_existing_log_returns_installed_version()]] - code - skills/ark-update/tests/test_state.py
- [[test_clean_run_invariant_preserves_existing_log()]] - code - skills/ark-update/tests/test_state.py
- [[test_clean_run_invariant_skips_log_and_pointer()]] - code - skills/ark-update/tests/test_state.py
- [[test_dedup_by_version_and_phase_last_wins()]] - code - skills/ark-update/tests/test_state.py
- [[test_multiple_entries_round_trip()]] - code - skills/ark-update/tests/test_state.py
- [[test_non_clean_run_does_write()]] - code - skills/ark-update/tests/test_state.py
- [[test_partial_result_does_write()]] - code - skills/ark-update/tests/test_state.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_33
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 43]]
- 7 edges to [[_COMMUNITY_Community 42]]
- 4 edges to [[_COMMUNITY_Community 68]]
- 4 edges to [[_COMMUNITY_Community 61]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[_make_entry()]] - degree 15, connects to 4 communities
- [[maybe_append_log_and_pointer()]] - degree 10, connects to 2 communities
- [[test_clean_run_invariant_preserves_existing_log()]] - degree 6, connects to 2 communities
- [[test_dedup_by_version_and_phase_last_wins()]] - degree 5, connects to 2 communities
- [[test_append_and_read_round_trip()]] - degree 4, connects to 2 communities