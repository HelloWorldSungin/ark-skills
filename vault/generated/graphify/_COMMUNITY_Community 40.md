---
type: community
cohesion: 0.26
members: 16
---

# Community 40

**Cohesion:** 0.26 - loosely connected
**Members:** 16 nodes

## Members
- [[Backup bytes must hash to meta.pre_hash (pre-mortem mitigation 1.1).      This v]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[CompletedProcess_2]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[Each .bak file must have a corresponding .bak.meta.json sidecar.]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[Each .meta.json sidecar must contain the required provenance fields.]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[Idempotent run must not create any backup files.]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[P2-3 stale version= in marker must trigger backup even when content is identica]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[Path_27]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[Tests each backup has a .meta.json sidecar with provenance fields.  When the en]] - rationale - skills/ark-update/tests/test_backup_provenance.py
- [[_copy_fixture_pre()]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[_run_engine()_1]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_backup_bytes_match_pre_hash()]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_backup_has_meta_sidecar()]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_backup_meta_schema()]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_backup_provenance.py]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_no_backup_on_idempotent_run()]] - code - skills/ark-update/tests/test_backup_provenance.py
- [[test_stale_version_drift_creates_backup()]] - code - skills/ark-update/tests/test_backup_provenance.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_40
SORT file.name ASC
```
