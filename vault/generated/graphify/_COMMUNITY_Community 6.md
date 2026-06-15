---
type: community
cohesion: 0.08
members: 37
---

# Community 6

**Cohesion:** 0.08 - loosely connected
**Members:** 37 nodes

## Members
- [[Check 1 top-level keys and required fields per entry type.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 2 all op values are in OP_REGISTRY.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 3 all template references resolve to real files under templates.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 4 all since values appear in CHANGELOG.md.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 5 templatesrouting-template.md byte-equals the ark-workflow reference.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 6 (codex P1-1) every filetarget field is path-safe.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 7 (codex P2-4) migrations.yaml accept failed_ops and depends_on_op.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Check 8 ensure_mcp_server entries should document _ark_managed sentinel.      T]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Path_14]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[Return None if rel_path is safe, or an error string if it escapes project_root.]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Return paths for the actual production target-profile.yaml.]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[Run all checks. Return list of error strings (empty = valid).]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Tests for check_target_profile_valid.py.  Two test cases per the plan   1. Runs]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[Validator must error when a template reference points to a non-existent file.]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[Validator must return at least one error for a profile with since 99.99.99.]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[Validator must return zero errors for the actual production target-profile.yaml.]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[Walk up from start to find the git repo root (contains CHANGELOG.md).]] - rationale - skills/ark-update/scripts/check_target_profile_valid.py
- [[Write a target-profile.yaml with an invalid since value (99.99.99).]] - rationale - skills/ark-update/tests/test_check_target_profile_valid.py
- [[_check_mcp_sentinel_docs()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_migrations_schema()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_op_registry()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_path_safety()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_routing_template_byte_equality()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_since_values()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_template_refs()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_check_yaml_structure()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_find_repo_root()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[_safe_resolve_check()]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[broken_profile()]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[check_target_profile_valid.py]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[main()_5]] - code - skills/ark-update/scripts/check_target_profile_valid.py
- [[real_paths()]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[test_actual_profile_is_valid()]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[test_broken_since_value_is_rejected()]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[test_check_target_profile_valid.py]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[test_missing_template_file_is_rejected()]] - code - skills/ark-update/tests/test_check_target_profile_valid.py
- [[validate()]] - code - skills/ark-update/scripts/check_target_profile_valid.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_6
SORT file.name ASC
```
