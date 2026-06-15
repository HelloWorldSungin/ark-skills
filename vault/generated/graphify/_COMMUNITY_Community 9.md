---
type: community
cohesion: 0.12
members: 32
---

# Community 9

**Cohesion:** 0.12 - loosely connected
**Members:** 32 nodes

## Members
- [[A region with no body lines has empty string content.]] - rationale - skills/ark-update/tests/test_markers.py
- [[After insert_region, extract_regions finds the new region.]] - rationale - skills/ark-update/tests/test_markers.py
- [[Bytes outside the marker pair must be byte-identical after replace_region.]] - rationale - skills/ark-update/tests/test_markers.py
- [[ManagedRegion.version is populated from the begin marker.]] - rationale - skills/ark-update/tests/test_markers.py
- [[Parse all ark-managed regions from file_path.      Returns     -------     lis]] - rationale - skills/ark-update/scripts/markers.py
- [[Path_15]] - code - skills/ark-update/scripts/markers.py
- [[Replace the content of the named region and update its ``version=``.      Outsid]] - rationale - skills/ark-update/scripts/markers.py
- [[Tests for skillsark-updatescriptsmarkers.py.  Covers   - Extract single regi]] - rationale - skills/ark-update/tests/test_markers.py
- [[When multiple regions exist, only the targeted one changes.]] - rationale - skills/ark-update/tests/test_markers.py
- [[_write()]] - code - skills/ark-update/tests/test_markers.py
- [[extract_regions()]] - code - skills/ark-update/scripts/markers.py
- [[replace_region writes the new version= into the begin marker.]] - rationale - skills/ark-update/tests/test_markers.py
- [[replace_region()]] - code - skills/ark-update/scripts/markers.py
- [[test_begin_marker_re_matches_valid()]] - code - skills/ark-update/tests/test_markers.py
- [[test_begin_marker_re_rejects_uppercase_id()]] - code - skills/ark-update/tests/test_markers.py
- [[test_end_marker_re_matches_valid()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_empty_file_returns_no_regions()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_file_with_no_markers()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_multiple_regions()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_region_with_no_content()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_single_region()]] - code - skills/ark-update/tests/test_markers.py
- [[test_extract_version_field_populated()]] - code - skills/ark-update/tests/test_markers.py
- [[test_insert_region_is_then_parseable()]] - code - skills/ark-update/tests/test_markers.py
- [[test_markers.py]] - code - skills/ark-update/tests/test_markers.py
- [[test_mismatched_id_is_refused()]] - code - skills/ark-update/tests/test_markers.py
- [[test_nested_markers_are_refused()]] - code - skills/ark-update/tests/test_markers.py
- [[test_replace_region_multiple_regions_only_touches_target()]] - code - skills/ark-update/tests/test_markers.py
- [[test_replace_region_nonexistent_id_raises()]] - code - skills/ark-update/tests/test_markers.py
- [[test_replace_region_preserves_outside_bytes()]] - code - skills/ark-update/tests/test_markers.py
- [[test_replace_region_updates_content()]] - code - skills/ark-update/tests/test_markers.py
- [[test_replace_region_updates_version_in_begin_marker()]] - code - skills/ark-update/tests/test_markers.py
- [[test_unclosed_region_is_refused()]] - code - skills/ark-update/tests/test_markers.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_9
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Community 72]]
- 5 edges to [[_COMMUNITY_Community 28]]
- 4 edges to [[_COMMUNITY_Community 19]]

## Top bridge nodes
- [[extract_regions()]] - degree 23, connects to 3 communities
- [[replace_region()]] - degree 10, connects to 2 communities
- [[test_markers.py]] - degree 23, connects to 1 community
- [[_write()]] - degree 19, connects to 1 community
- [[test_insert_region_is_then_parseable()]] - degree 5, connects to 1 community