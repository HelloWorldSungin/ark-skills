---
type: community
cohesion: 0.26
members: 16
---

# Community 41

**Cohesion:** 0.26 - loosely connected
**Members:** 16 nodes

## Members
- [[A fully idempotent run must NOT append to the log (codex P1-2).]] - rationale - skills/ark-update/tests/test_logging.py
- [[A non-clean run (pre-v1.11) writes at least one JSONL log entry.]] - rationale - skills/ark-update/tests/test_logging.py
- [[After Phase 2 convergence, log must have a 'convergence' phase entry.]] - rationale - skills/ark-update/tests/test_logging.py
- [[After a non-clean run, .arkplugin-version must be written.]] - rationale - skills/ark-update/tests/test_logging.py
- [[CompletedProcess_8]] - code - skills/ark-update/tests/test_logging.py
- [[Each log entry must have all required fields with correct types.]] - rationale - skills/ark-update/tests/test_logging.py
- [[Path_34]] - code - skills/ark-update/tests/test_logging.py
- [[Tests engine emits structured log to migrations-applied.jsonl.  Verifies that a]] - rationale - skills/ark-update/tests/test_logging.py
- [[_copy_fixture_pre()_6]] - code - skills/ark-update/tests/test_logging.py
- [[_run_engine()_5]] - code - skills/ark-update/tests/test_logging.py
- [[test_clean_run_does_not_append_log()]] - code - skills/ark-update/tests/test_logging.py
- [[test_convergence_phase_logged()]] - code - skills/ark-update/tests/test_logging.py
- [[test_log_entry_schema()]] - code - skills/ark-update/tests/test_logging.py
- [[test_logging.py]] - code - skills/ark-update/tests/test_logging.py
- [[test_non_clean_run_writes_jsonl()]] - code - skills/ark-update/tests/test_logging.py
- [[test_plugin_version_pointer_written()]] - code - skills/ark-update/tests/test_logging.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_41
SORT file.name ASC
```
