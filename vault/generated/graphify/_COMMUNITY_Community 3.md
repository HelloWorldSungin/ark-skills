---
type: community
cohesion: 0.08
members: 43
---

# Community 3

**Cohesion:** 0.08 - loosely connected
**Members:** 43 nodes

## Members
- [[Build a deterministic dry-run plan from target profile + pending migrations.]] - rationale - skills/ark-update/scripts/plan.py
- [[Call dry_run on a destructive migration op dict.      In v1.0 Step 2 there are n]] - rationale - skills/ark-update/scripts/plan.py
- [[Call dry_run on a target-profile entry dict.      Looks up the op class in ``OP_]] - rationale - skills/ark-update/scripts/plan.py
- [[Convert any Path values in a report dict to strings for JSON serialization.]] - rationale - skills/ark-update/scripts/plan.py
- [[Deterministic JSON-serializable dry-run plan report.      ``phase_1_ops`` list]] - rationale - skills/ark-update/scripts/plan.py
- [[Dry-run plan builder for ark-update.  ``build_plan`` aggregates per-op ``dry_run]] - rationale - skills/ark-update/scripts/plan.py
- [[In Step 2, OP_REGISTRY is empty; every entry yields would_fail_precondition=True]] - rationale - skills/ark-update/tests/test_plan.py
- [[Path_24]] - code - skills/ark-update/scripts/plan.py
- [[PlanReport]] - code - skills/ark-update/scripts/plan.py
- [[Register 3 different mock ops with different dry_run responses.]] - rationale - skills/ark-update/tests/test_plan.py
- [[Register a mock op, verify build_plan picks it up and counts correctly.]] - rationale - skills/ark-update/tests/test_plan.py
- [[Render a ``PlanReport`` as a human-readable summary string for stdout.      Exam]] - rationale - skills/ark-update/scripts/plan.py
- [[Return the human-readable status tag for a dry-run report entry.]] - rationale - skills/ark-update/scripts/plan.py
- [[Tests for skillsark-updatescriptsplan.py.  Covers   - Empty target profile +]] - rationale - skills/ark-update/tests/test_plan.py
- [[YAML migration entry with depends_on_op is parsed and field is preserved.]] - rationale - skills/ark-update/tests/test_plan.py
- [[YAML migration entry without depends_on_op is also valid.]] - rationale - skills/ark-update/tests/test_plan.py
- [[Yield all op-entry dicts from a parsed target profile, in declaration order.]] - rationale - skills/ark-update/scripts/plan.py
- [[_dry_run_migration_op()]] - code - skills/ark-update/scripts/plan.py
- [[_dry_run_target_profile_entry()]] - code - skills/ark-update/scripts/plan.py
- [[_iter_target_profile_entries()_1]] - code - skills/ark-update/scripts/plan.py
- [[_make_empty_profile()]] - code - skills/ark-update/tests/test_plan.py
- [[_make_profile_with_entries()]] - code - skills/ark-update/tests/test_plan.py
- [[_op_tag()]] - code - skills/ark-update/scripts/plan.py
- [[_to_serializable()]] - code - skills/ark-update/scripts/plan.py
- [[build_plan()]] - code - skills/ark-update/scripts/plan.py
- [[depends_on_op field survives the build_plan round-trip into phase_1_ops.]] - rationale - skills/ark-update/tests/test_plan.py
- [[plan.py]] - code - skills/ark-update/scripts/plan.py
- [[render_plan_report()]] - code - skills/ark-update/scripts/plan.py
- [[test_aggregation_mixed_statuses()]] - code - skills/ark-update/tests/test_plan.py
- [[test_determinism_empty()]] - code - skills/ark-update/tests/test_plan.py
- [[test_determinism_with_entries()]] - code - skills/ark-update/tests/test_plan.py
- [[test_empty_profile_json_serializable()]] - code - skills/ark-update/tests/test_plan.py
- [[test_empty_profile_no_pending()]] - code - skills/ark-update/tests/test_plan.py
- [[test_pending_migration_with_depends_on_op_in_plan()]] - code - skills/ark-update/tests/test_plan.py
- [[test_pending_migrations_in_phase_1()]] - code - skills/ark-update/tests/test_plan.py
- [[test_plan.py]] - code - skills/ark-update/tests/test_plan.py
- [[test_profile_with_entries_mocked_ops()]] - code - skills/ark-update/tests/test_plan.py
- [[test_profile_with_entries_unregistered_ops()]] - code - skills/ark-update/tests/test_plan.py
- [[test_render_plan_report_contains_counts()]] - code - skills/ark-update/tests/test_plan.py
- [[test_render_plan_report_empty()]] - code - skills/ark-update/tests/test_plan.py
- [[test_render_plan_report_with_entries()]] - code - skills/ark-update/tests/test_plan.py
- [[test_yaml_depends_on_op_field_preserved()]] - code - skills/ark-update/tests/test_plan.py
- [[test_yaml_depends_on_op_optional()]] - code - skills/ark-update/tests/test_plan.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_3
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 28]]
- 1 edge to [[_COMMUNITY_Community 7]]
- 1 edge to [[_COMMUNITY_Community 0]]
- 1 edge to [[_COMMUNITY_Community 18]]

## Top bridge nodes
- [[plan.py]] - degree 14, connects to 5 communities
- [[build_plan()]] - degree 21, connects to 1 community
- [[render_plan_report()]] - degree 8, connects to 1 community
- [[PlanReport]] - degree 5, connects to 1 community