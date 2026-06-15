---
source_file: "skills/wiki-update/scripts/promote_omc.py"
type: "code"
community: "Community 8"
location: "L220"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Community_8
---

# promote()

## Source

[`skills/wiki-update/scripts/promote_omc.py` (L220)](../../../skills/wiki-update/scripts/promote_omc.py)


## Connections
- [[OMCPage_2]] - `calls` [EXTRACTED]
- [[PromotionConfig]] - `references` [EXTRACTED]
- [[PromotionReport]] - `references` [EXTRACTED]
- [[_append_to_session_log()]] - `calls` [EXTRACTED]
- [[_create_review_tasknote()]] - `calls` [EXTRACTED]
- [[_find_session_log()]] - `calls` [EXTRACTED]
- [[_merge_into_existing()]] - `calls` [EXTRACTED]
- [[_resolve_existing_vault_page()]] - `calls` [EXTRACTED]
- [[classify()]] - `calls` [EXTRACTED]
- [[derive_summary()]] - `calls` [EXTRACTED]
- [[main()_15]] - `calls` [INFERRED]
- [[parse_page()]] - `calls` [INFERRED]
- [[promote_omc.py]] - `contains` [EXTRACTED]
- [[test_append_to_session_log_is_idempotent_on_retry_H1()]] - `calls` [INFERRED]
- [[test_bridge_merge_preserves_omc_when_no_session_log_H3()]] - `calls` [INFERRED]
- [[test_dual_write_debug_deletes_when_troubleshooting_written_but_no_log_H3()]] - `calls` [INFERRED]
- [[test_dual_write_debug_preserves_omc_when_no_log_and_no_pattern_tag_H3()]] - `calls` [INFERRED]
- [[test_merge_into_existing_is_idempotent_on_retry_H1()]] - `calls` [INFERRED]
- [[test_promote_debugging_pattern_dual_writes()]] - `calls` [INFERRED]
- [[test_promote_does_not_merge_when_ark_source_path_escapes_vault_C1()]] - `calls` [INFERRED]
- [[test_promote_high_arch_lands_in_architecture()]] - `calls` [INFERRED]
- [[test_promote_medium_stages_and_creates_tasknote()]] - `calls` [INFERRED]
- [[test_promote_merges_via_ark_source_path_when_target_exists()]] - `calls` [INFERRED]
- [[test_promote_pending_deletes_not_executed()]] - `calls` [INFERRED]
- [[test_promote_populates_written_paths_C2()]] - `calls` [INFERRED]
- [[test_promote_skips_pages_older_than_session_started_at()]] - `calls` [INFERRED]
- [[translate_frontmatter()]] - `calls` [EXTRACTED]
- [[write_page()]] - `calls` [INFERRED]

#graphify/code #graphify/INFERRED #community/Community_8