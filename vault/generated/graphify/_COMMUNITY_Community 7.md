---
type: community
cohesion: 0.08
members: 35
---

# Community 7

**Cohesion:** 0.08 - loosely connected
**Members:** 35 nodes

## Members
- [[._apply_impl()_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[._detect_drift_impl()_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[._dry_run_impl()_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[._entry_present()]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[._gitignore_path()]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[.gitignore already contains the entry; apply is a no-op.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[.gitignore does not exist; apply creates it with just the entry.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[.gitignore exists but does not contain the entry; apply adds it.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[.gitignore exists without a trailing newline; apply adds entry correctly.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[Append a single line to .gitignore if absent.]] - rationale - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[ApplyResult_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[DriftReport_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[DryRunReport_3]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[EnsureGitignoreEntry_1]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[EnsureGitignoreEntry]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[EnsureGitignoreEntry is registered in OP_REGISTRY under the correct key.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[Op ensure_gitignore_entry — append a single line to .gitignore if absent.  Targ]] - rationale - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[Path_20]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[Return True if entry is an exact line in content.]] - rationale - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[Return the resolved .gitignore path.          If args contains a pre-validated `]] - rationale - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[Tests for skillsark-updatescriptsopsensure_gitignore_entry.py.  7 cases (Tie]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[_op()_1]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[detect_drift always returns has_drift=False regardless of entry presence.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[dry_run returns the same decision flags that apply would act on, without writing]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[ensure_gitignore_entry.py]] - code - skills/ark-update/scripts/ops/ensure_gitignore_entry.py
- [[file override with .. traversal raises PathTraversalError via base class.]] - rationale - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_apply_appends_when_absent()]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_apply_creates_gitignore_when_missing()]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_apply_idempotent_when_present()]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_apply_normalizes_trailing_newline()]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_detect_drift_always_false()_1]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_dry_run_matches_apply()_2]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_op_ensure_gitignore_entry.py]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_op_registered()_1]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py
- [[test_path_traversal_refusal()_2]] - code - skills/ark-update/tests/test_op_ensure_gitignore_entry.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_7
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 3]]
- 1 edge to [[_COMMUNITY_Community 0]]

## Top bridge nodes
- [[ensure_gitignore_entry.py]] - degree 5, connects to 2 communities
- [[EnsureGitignoreEntry]] - degree 9, connects to 1 community
- [[EnsureGitignoreEntry_1]] - degree 3, connects to 1 community