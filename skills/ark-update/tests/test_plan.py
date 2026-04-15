"""Tests for skills/ark-update/scripts/plan.py.

Covers:
  - Empty target profile + no pending migrations → empty plan, zero counts
  - Target profile with entries, mocked dry_run → plan aggregates correctly
  - Determinism: two build_plan calls on same inputs → byte-identical JSON
  - render_plan_report produces a parseable human summary
  - YAML accepts optional depends_on_op field on migration op entries
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

# ---------------------------------------------------------------------------
# sys.path shim — same pattern as other test files in this suite
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from plan import build_plan, render_plan_report, PlanReport  # noqa: E402
from ops import OP_REGISTRY, TargetProfileOp, register_op  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_profile() -> dict:
    return {"schema_version": "1.0"}


def _make_profile_with_entries() -> dict:
    return {
        "schema_version": "1.0",
        "managed_regions": [
            {"op": "ensure_claude_md_section", "id": "omc-routing", "file": "CLAUDE.md",
             "template": "templates/omc-routing-block.md", "version": "1.13.0"},
        ],
        "ensured_gitignore": [
            {"op": "ensure_gitignore_entry", "id": "ark-workflow-gitignore",
             "pattern": ".ark-workflow/"},
        ],
        "ensured_mcp_servers": [
            {"op": "ensure_mcp_server", "id": "mcp-tasknotes",
             "server_name": "tasknotes", "command": "uvx"},
        ],
    }


# ---------------------------------------------------------------------------
# 1. Empty target profile + no pending migrations
# ---------------------------------------------------------------------------

def test_empty_profile_no_pending(tmp_path):
    plan = build_plan(_make_empty_profile(), [], tmp_path)

    assert plan["phase_1_ops"] == []
    assert plan["phase_2_ops"] == []
    assert plan["would_apply_count"] == 0
    assert plan["would_skip_count"] == 0
    assert plan["would_overwrite_count"] == 0
    assert plan["would_fail_count"] == 0


def test_empty_profile_json_serializable(tmp_path):
    plan = build_plan(_make_empty_profile(), [], tmp_path)
    # Must not raise
    serialized = json.dumps(plan, sort_keys=True)
    assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# 2. Target profile with entries — stub ops (registry empty in Step 2)
# ---------------------------------------------------------------------------

def test_profile_with_entries_unregistered_ops(tmp_path):
    """In Step 2, OP_REGISTRY is empty; every entry yields would_fail_precondition=True."""
    profile = _make_profile_with_entries()
    plan = build_plan(profile, [], tmp_path)

    # 3 entries in the profile
    assert len(plan["phase_2_ops"]) == 3
    assert plan["phase_1_ops"] == []

    # All should be would_fail_precondition since no ops are registered
    for op_report in plan["phase_2_ops"]:
        assert op_report["would_fail_precondition"] is True
        assert op_report["would_apply"] is False
        assert op_report["would_skip_idempotent"] is False
        assert op_report["would_overwrite_drift"] is False

    assert plan["would_fail_count"] == 3
    assert plan["would_apply_count"] == 0
    assert plan["would_skip_count"] == 0
    assert plan["would_overwrite_count"] == 0


def test_profile_with_entries_mocked_ops(tmp_path):
    """Register a mock op, verify build_plan picks it up and counts correctly."""
    # Create a temporary op class and register it
    mock_dry_run_return = {
        "op_id": "omc-routing",
        "op_type": "ensure_claude_md_section",
        "would_apply": True,
        "would_skip_idempotent": False,
        "would_overwrite_drift": False,
        "would_fail_precondition": False,
        "drift_summary": None,
    }

    class _MockOp(TargetProfileOp):
        OP_TYPE = "ensure_claude_md_section"
        PATH_ARGS = ("file",)

        def _apply_impl(self, project_root, args):
            return {"op_id": "omc-routing", "op_type": "ensure_claude_md_section",
                    "status": "applied"}

        def _dry_run_impl(self, project_root, args):
            return mock_dry_run_return

        def _detect_drift_impl(self, project_root, args):
            return {"has_drift": False, "drift_summary": None, "drifted_regions": []}

    # Temporarily register the mock op
    OP_REGISTRY["ensure_claude_md_section"] = _MockOp
    try:
        profile = {
            "schema_version": "1.0",
            "managed_regions": [
                {"op": "ensure_claude_md_section", "id": "omc-routing",
                 "file": "CLAUDE.md", "template": "templates/omc-routing-block.md",
                 "version": "1.13.0"},
            ],
        }
        plan = build_plan(profile, [], tmp_path)

        assert len(plan["phase_2_ops"]) == 1
        assert plan["would_apply_count"] == 1
        assert plan["would_skip_count"] == 0
        assert plan["would_fail_count"] == 0
        assert plan["phase_2_ops"][0]["would_apply"] is True
    finally:
        OP_REGISTRY.pop("ensure_claude_md_section", None)


def test_aggregation_mixed_statuses(tmp_path):
    """Register 3 different mock ops with different dry_run responses."""
    class _ApplyOp(TargetProfileOp):
        OP_TYPE = "op_apply"
        def _apply_impl(self, r, a): return {"op_id": "x", "op_type": "op_apply", "status": "applied"}
        def _dry_run_impl(self, r, a):
            return {"op_id": "x", "op_type": "op_apply",
                    "would_apply": True, "would_skip_idempotent": False,
                    "would_overwrite_drift": False, "would_fail_precondition": False,
                    "drift_summary": None}
        def _detect_drift_impl(self, r, a):
            return {"has_drift": False, "drift_summary": None, "drifted_regions": []}

    class _SkipOp(TargetProfileOp):
        OP_TYPE = "op_skip"
        def _apply_impl(self, r, a): return {"op_id": "y", "op_type": "op_skip", "status": "skipped_idempotent"}
        def _dry_run_impl(self, r, a):
            return {"op_id": "y", "op_type": "op_skip",
                    "would_apply": False, "would_skip_idempotent": True,
                    "would_overwrite_drift": False, "would_fail_precondition": False,
                    "drift_summary": None}
        def _detect_drift_impl(self, r, a):
            return {"has_drift": False, "drift_summary": None, "drifted_regions": []}

    class _DriftOp(TargetProfileOp):
        OP_TYPE = "op_drift"
        def _apply_impl(self, r, a): return {"op_id": "z", "op_type": "op_drift", "status": "drifted_overwritten"}
        def _dry_run_impl(self, r, a):
            return {"op_id": "z", "op_type": "op_drift",
                    "would_apply": False, "would_skip_idempotent": False,
                    "would_overwrite_drift": True, "would_fail_precondition": False,
                    "drift_summary": "user edited region content"}
        def _detect_drift_impl(self, r, a):
            return {"has_drift": True, "drift_summary": "user edited region content",
                    "drifted_regions": ["z"]}

    OP_REGISTRY["op_apply"] = _ApplyOp
    OP_REGISTRY["op_skip"] = _SkipOp
    OP_REGISTRY["op_drift"] = _DriftOp
    try:
        profile = {
            "managed_regions": [
                {"op": "op_apply", "id": "x"},
                {"op": "op_skip", "id": "y"},
                {"op": "op_drift", "id": "z"},
            ]
        }
        plan = build_plan(profile, [], tmp_path)
        assert plan["would_apply_count"] == 1
        assert plan["would_skip_count"] == 1
        assert plan["would_overwrite_count"] == 1
        assert plan["would_fail_count"] == 0
    finally:
        for k in ("op_apply", "op_skip", "op_drift"):
            OP_REGISTRY.pop(k, None)


# ---------------------------------------------------------------------------
# 3. Determinism: two build_plan calls → byte-identical JSON
# ---------------------------------------------------------------------------

def test_determinism_empty(tmp_path):
    profile = _make_empty_profile()
    plan_a = build_plan(profile, [], tmp_path)
    plan_b = build_plan(profile, [], tmp_path)
    assert json.dumps(plan_a, sort_keys=True) == json.dumps(plan_b, sort_keys=True)


def test_determinism_with_entries(tmp_path):
    profile = _make_profile_with_entries()
    plan_a = build_plan(profile, [], tmp_path)
    plan_b = build_plan(profile, [], tmp_path)
    serialized_a = json.dumps(plan_a, sort_keys=True)
    serialized_b = json.dumps(plan_b, sort_keys=True)
    assert serialized_a == serialized_b


# ---------------------------------------------------------------------------
# 4. render_plan_report — parseable human summary
# ---------------------------------------------------------------------------

def test_render_plan_report_empty(tmp_path):
    plan = build_plan(_make_empty_profile(), [], tmp_path)
    output = render_plan_report(plan)
    assert isinstance(output, str)
    assert "ark-update dry-run plan" in output
    assert "Phase 1" in output
    assert "Phase 2" in output
    assert "nothing to do" in output
    assert "Summary:" in output


def test_render_plan_report_with_entries(tmp_path):
    profile = _make_profile_with_entries()
    plan = build_plan(profile, [], tmp_path)
    output = render_plan_report(plan)
    assert "Phase 2 (target-profile convergence): 3 ops" in output
    assert "Summary:" in output


def test_render_plan_report_contains_counts(tmp_path):
    profile = _make_profile_with_entries()
    plan = build_plan(profile, [], tmp_path)
    output = render_plan_report(plan)
    # Summary line should contain the word "fail"
    assert "fail=" in output


# ---------------------------------------------------------------------------
# 5. depends_on_op field: YAML parser smoke test (acceptance criterion 6)
# ---------------------------------------------------------------------------

def test_yaml_depends_on_op_field_preserved():
    """YAML migration entry with depends_on_op is parsed and field is preserved."""
    yaml_str = """
ops:
  - op_id: step-b
    op_type: rename_frontmatter_field
    depends_on_op: step-a
    args:
      old_field: category
      new_field: type
  - op_id: step-a
    op_type: deprecate_file
    args:
      path: old-file.md
"""
    parsed = yaml.safe_load(yaml_str)
    ops = parsed.get("ops", [])
    assert len(ops) == 2

    op_b = next(o for o in ops if o["op_id"] == "step-b")
    assert "depends_on_op" in op_b
    assert op_b["depends_on_op"] == "step-a"

    op_a = next(o for o in ops if o["op_id"] == "step-a")
    # op_a has no depends_on_op
    assert "depends_on_op" not in op_a


def test_yaml_depends_on_op_optional():
    """YAML migration entry without depends_on_op is also valid."""
    yaml_str = """
ops:
  - op_id: standalone-op
    op_type: deprecate_file
    args:
      path: old-file.md
"""
    parsed = yaml.safe_load(yaml_str)
    ops = parsed.get("ops", [])
    assert len(ops) == 1
    assert "depends_on_op" not in ops[0]


# ---------------------------------------------------------------------------
# 6. pending_migrations passed to build_plan appear in phase_1_ops
# ---------------------------------------------------------------------------

def test_pending_migrations_in_phase_1(tmp_path):
    pending = [
        {
            "op_id": "rename-category",
            "op_type": "rename_frontmatter_field",
            "args": {"old_field": "category", "new_field": "type"},
        }
    ]
    plan = build_plan(_make_empty_profile(), pending, tmp_path)
    assert len(plan["phase_1_ops"]) == 1
    assert plan["phase_1_ops"][0]["op_id"] == "rename-category"
    # Unregistered destructive op → would_fail_precondition
    assert plan["phase_1_ops"][0]["would_fail_precondition"] is True


def test_pending_migration_with_depends_on_op_in_plan(tmp_path):
    """depends_on_op field survives the build_plan round-trip into phase_1_ops."""
    pending = [
        {
            "op_id": "step-b",
            "op_type": "rename_frontmatter_field",
            "depends_on_op": "step-a",
            "args": {},
        }
    ]
    plan = build_plan(_make_empty_profile(), pending, tmp_path)
    assert len(plan["phase_1_ops"]) == 1
    report = plan["phase_1_ops"][0]
    assert report.get("depends_on_op") == "step-a"
