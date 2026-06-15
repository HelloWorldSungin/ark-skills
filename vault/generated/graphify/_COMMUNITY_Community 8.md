---
type: community
cohesion: 0.17
members: 33
---

# Community 8

**Cohesion:** 0.17 - loosely connected
**Members:** 33 nodes

## Members
- [[C1 end-to-end a crafted ark-source-path must not cause _merge_into_existing]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[C2 PromotionReport.written_paths must list every vault destination     write_pa]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H1 Running promote() twice on the same OMC source must not double-append     th]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H1 dual-write-debug must not double-append the same debug entry when retried.]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H3 boundary if troubleshooting was written (patterninsight tag), OMC source]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H3 bridge-merge must NOT append to pending_deletes when log_path is None.     O]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H3 dual-write-debug with no session log AND no patterninsight tag     must pre]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H4 complement OSError from a vault write IS still caught (file-level failure).]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[H4 narrow except — TypeError from broken code should CRASH, not become a     pe]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[Tests for promote_omc filter, edit-detection, confidence gate, translation.]] - rationale - skills/wiki-update/scripts/test_promote_omc.py
- [[_copy_fixture()_1]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[_mk_config()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[_write_session_log()_1]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[promote()]] - code - skills/wiki-update/scripts/promote_omc.py
- [[test_append_to_session_log_is_idempotent_on_retry_H1()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_bridge_merge_preserves_omc_when_no_session_log_H3()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_dual_write_debug_deletes_when_troubleshooting_written_but_no_log_H3()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_dual_write_debug_preserves_omc_when_no_log_and_no_pattern_tag_H3()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_merge_into_existing_is_idempotent_on_retry_H1()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_oserror_during_write_is_recorded_not_raised_H4()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_programmer_errors_propagate_not_swallowed_H4()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_debugging_pattern_dual_writes()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_does_not_merge_when_ark_source_path_escapes_vault_C1()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_high_arch_lands_in_architecture()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_medium_stages_and_creates_tasknote()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_merges_via_ark_source_path_when_target_exists()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_omc.py]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_pending_deletes_not_executed()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_populates_written_paths_C2()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_promote_skips_pages_older_than_session_started_at()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_translate_fallback_to_category_mapping()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[test_translate_frontmatter_uses_ark_original_type()]] - code - skills/wiki-update/scripts/test_promote_omc.py
- [[translate_frontmatter()]] - code - skills/wiki-update/scripts/promote_omc.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_8
SORT file.name ASC
```

## Connections to other communities
- 22 edges to [[_COMMUNITY_Community 15]]
- 13 edges to [[_COMMUNITY_Community 22]]
- 6 edges to [[_COMMUNITY_Community 48]]

## Top bridge nodes
- [[test_promote_omc.py]] - degree 36, connects to 3 communities
- [[promote()]] - degree 28, connects to 3 communities
- [[_copy_fixture()_1]] - degree 24, connects to 1 community
- [[_mk_config()]] - degree 17, connects to 1 community
- [[test_promote_does_not_merge_when_ark_source_path_escapes_vault_C1()]] - degree 8, connects to 1 community