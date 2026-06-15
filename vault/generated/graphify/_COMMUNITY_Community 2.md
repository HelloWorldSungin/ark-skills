---
type: community
cohesion: 0.05
members: 48
---

# Community 2

**Cohesion:** 0.05 - loosely connected
**Members:** 48 nodes

## Members
- [[._ids()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[._read()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_both_one_returns_true_true()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_both_one_yields_all()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_both_unset_returns_none_none()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_both_zero_returns_false_false()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_both_zero_skips_both_gated()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_empty_string_skips_both_gated()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_empty_string_treated_as_false()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_garbage_values_treated_as_false()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_omc_one_vault_zero()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_omc_one_vault_zero_skips_vault_symlink()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_omc_zero_vault_one()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_omc_zero_vault_one_skips_omc_routing()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_truthy_english_skips_both_gated()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_truthy_english_word_treated_as_false()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_unset_unset_yields_all_backward_compat()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_whitespace_around_one_is_true()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[.test_yes_no_both_treated_as_false()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[ARK_CENTRALIZED_VAULT=0 → setup-vault-symlink SKIPPED; omc-routing CREATED.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[ARK_HAS_OMC=0 → omc-routing SKIPPED; setup-vault-symlink CREATED.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Both disabled → omc-routing AND setup-vault-symlink SKIPPED; routing-rules still]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Both explicitly enabled → all entries yielded.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Both unset → all entries yielded (backward-compat for Step-6 fixture tests).]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Call _iter_target_profile_entries with given env overrides; return list of entry]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[CompletedProcess_6]] - code - skills/ark-update/tests/test_gate_flags.py
- [[E2E smoke ARK_HAS_OMC=0 + ARK_CENTRALIZED_VAULT=0 → 2 ops applied (routing-rule]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[E2E fresh fixture with gate-flag overrides produces correct appliedskipped cou]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Empty string is present (not None) but strip() == '' != '1' → False.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Empty string → treated as False → both gated entries skipped.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Path_32]] - code - skills/ark-update/tests/test_gate_flags.py
- [[Pin _read_gate_flags return values for all relevant env-var states.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Pin which entries _iter_target_profile_entries yields for each gate-flag combo.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[Run migrate.py on project_root with explicit gate-flag env overrides.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[TestIterTargetProfileEntries]] - code - skills/ark-update/tests/test_gate_flags.py
- [[TestReadGateFlags]] - code - skills/ark-update/tests/test_gate_flags.py
- [[Tests gate-flag evaluation in _read_gate_flags() and _iter_target_profile_entri]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[_copy_fixture_pre()_4]] - code - skills/ark-update/tests/test_gate_flags.py
- [[_entry_ids()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[_run_with_gates()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[test_e2e_both_gates_off_summary_counts()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[test_e2e_gate_flags_fresh_fixture()]] - code - skills/ark-update/tests/test_gate_flags.py
- [[test_gate_flags.py]] - code - skills/ark-update/tests/test_gate_flags.py
- [[true''true' → treated as False → both gated entries skipped.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[true''yes' are NOT accepted — only strict '1' is truthy.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[val.strip() == '1' — leadingtrailing whitespace is stripped → True.]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[yes''no' are garbage — both map to False (not None, not True).]] - rationale - skills/ark-update/tests/test_gate_flags.py
- [[yes''no' → both False → both gated entries skipped.]] - rationale - skills/ark-update/tests/test_gate_flags.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_2
SORT file.name ASC
```
