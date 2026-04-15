"""Dry-run plan builder for ark-update.

``build_plan`` aggregates per-op ``dry_run`` results from both the target-profile
(Phase 2) and pending destructive migrations (Phase 1) into a single deterministic
``PlanReport`` dict.

Determinism guarantee
---------------------
Two calls to ``build_plan`` on the same inputs MUST produce byte-identical JSON
when serialized with ``json.dumps(plan, sort_keys=True)``.  This is enforced by:

- Stable op ordering: Phase 1 ops sorted by semver ascending (same order the
  engine applies them); Phase 2 ops in target-profile declaration order.
- No timestamps or random values in the report.
- All ``DryRunReport`` dicts contain only JSON-serializable scalars (str, bool,
  None).  ``Path`` objects must be converted to strings before inclusion.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# sys.path shim — allows bare "import paths" / "import state" etc.
# ---------------------------------------------------------------------------
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from ops import OP_REGISTRY, TargetProfileOp  # noqa: E402

# Import concrete op modules so their @register_op decorators fire.
# Required for dry_run dispatch to work correctly.
import ops.ensure_claude_md_section  # noqa: F401, E402
import ops.ensure_routing_rules_block  # noqa: F401, E402
import ops.ensure_gitignore_entry  # noqa: F401, E402
import ops.create_file_from_template  # noqa: F401, E402
import ops.ensure_mcp_server  # noqa: F401, E402


# ---------------------------------------------------------------------------
# PlanReport typed dict
# ---------------------------------------------------------------------------

class PlanReport(TypedDict):
    """Deterministic JSON-serializable dry-run plan report.

    ``phase_1_ops``: list of ``DryRunReport`` dicts for pending destructive
        migrations (Phase 1), sorted semver ascending.
    ``phase_2_ops``: list of ``DryRunReport`` dicts for target-profile convergence
        ops (Phase 2), in declaration order.
    ``would_apply_count``: total ops where ``would_apply`` is True.
    ``would_skip_count``: total ops where ``would_skip_idempotent`` is True.
    ``would_overwrite_count``: total ops where ``would_overwrite_drift`` is True.
    ``would_fail_count``: total ops where ``would_fail_precondition`` is True.
    """
    phase_1_ops: list[dict]
    phase_2_ops: list[dict]
    would_apply_count: int
    would_skip_count: int
    would_overwrite_count: int
    would_fail_count: int


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------

def build_plan(
    target_profile: dict,
    pending_migrations: list[dict],
    project_root: Path,
) -> PlanReport:
    """Build a deterministic dry-run plan from target profile + pending migrations.

    Parameters
    ----------
    target_profile:
        Parsed contents of ``target-profile.yaml``.  Expected shape::

            {
                "schema_version": "1.0",
                "managed_regions": [...],
                "ensured_files": [...],
                "ensured_gitignore": [...],
                "ensured_mcp_servers": [...],
            }

        In v1.0 Step 2, ``OP_REGISTRY`` is empty so all Phase-2 ops return a
        stub ``DryRunReport`` with ``would_fail_precondition=True`` and
        ``op_type="<unregistered>"``.  Step 3 fills the registry and this
        function automatically picks up the concrete classes.

    pending_migrations:
        List of migration op dicts — already filtered to semver > installed_version
        and sorted ascending by the caller (``migrate.py``).  Each dict has at
        minimum: ``{op_id, op_type, args, depends_on_op?}``.

    project_root:
        Absolute path to the project root.  Passed through to each op's
        ``dry_run`` call.

    Returns
    -------
    PlanReport
        A fully JSON-serializable ``PlanReport`` dict.  Serialize with
        ``json.dumps(plan, sort_keys=True)`` for deterministic byte output.
    """
    phase_1_reports: list[dict] = []
    for migration_op in pending_migrations:
        report = _dry_run_migration_op(migration_op, project_root)
        phase_1_reports.append(_to_serializable(report))

    phase_2_reports: list[dict] = []
    # Collect all op entries from all sections of target_profile.
    for entry in _iter_target_profile_entries(target_profile):
        report = _dry_run_target_profile_entry(entry, project_root)
        phase_2_reports.append(_to_serializable(report))

    all_reports = phase_1_reports + phase_2_reports
    would_apply = sum(1 for r in all_reports if r.get("would_apply", False))
    would_skip = sum(1 for r in all_reports if r.get("would_skip_idempotent", False))
    would_overwrite = sum(1 for r in all_reports if r.get("would_overwrite_drift", False))
    would_fail = sum(1 for r in all_reports if r.get("would_fail_precondition", False))

    return PlanReport(
        phase_1_ops=phase_1_reports,
        phase_2_ops=phase_2_reports,
        would_apply_count=would_apply,
        would_skip_count=would_skip,
        would_overwrite_count=would_overwrite,
        would_fail_count=would_fail,
    )


# ---------------------------------------------------------------------------
# Human-readable renderer
# ---------------------------------------------------------------------------

def render_plan_report(plan: PlanReport) -> str:
    """Render a ``PlanReport`` as a human-readable summary string for stdout.

    Example output::

        ark-update dry-run plan
        =======================
        Phase 1 (destructive migrations): 0 ops
        Phase 2 (target-profile convergence): 3 ops
          [would_apply]           ensure_claude_md_section  (op_id=omc-routing-rules)
          [would_skip_idempotent] ensure_gitignore_entry    (op_id=ark-workflow-gitignore)
          [would_overwrite_drift] ensure_mcp_server         (op_id=mcp-server-tasknotes)

        Summary: apply=1  skip=1  overwrite=1  fail=0
    """
    lines: list[str] = [
        "ark-update dry-run plan",
        "=======================",
        f"Phase 1 (destructive migrations): {len(plan['phase_1_ops'])} ops",
    ]

    for op in plan["phase_1_ops"]:
        tag = _op_tag(op)
        op_type = op.get("op_type", "?")
        op_id = op.get("op_id", "?")
        lines.append(f"  [{tag:<28}] {op_type:<34} (op_id={op_id})")

    lines.append(f"Phase 2 (target-profile convergence): {len(plan['phase_2_ops'])} ops")

    for op in plan["phase_2_ops"]:
        tag = _op_tag(op)
        op_type = op.get("op_type", "?")
        op_id = op.get("op_id", "?")
        drift = op.get("drift_summary")
        suffix = f"  drift: {drift}" if drift else ""
        lines.append(f"  [{tag:<28}] {op_type:<34} (op_id={op_id}){suffix}")

    lines.append("")
    lines.append(
        f"Summary: apply={plan['would_apply_count']}"
        f"  skip={plan['would_skip_count']}"
        f"  overwrite={plan['would_overwrite_count']}"
        f"  fail={plan['would_fail_count']}"
    )

    if (plan["would_apply_count"] == 0
            and plan["would_skip_count"] == 0
            and plan["would_overwrite_count"] == 0
            and plan["would_fail_count"] == 0
            and not plan["phase_1_ops"]
            and not plan["phase_2_ops"]):
        lines.append("(no target profile entries, nothing to do)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_target_profile_entries(target_profile: dict):
    """Yield all op-entry dicts from a parsed target profile, in declaration order.

    Injects ``op`` key for sections whose entries don't carry an explicit ``op``
    field (e.g. ``ensured_gitignore`` uses ``entry`` + implicit op type).
    """
    _IMPLICIT_OPS = {
        "ensured_gitignore": "ensure_gitignore_entry",
        "ensured_mcp_servers": "ensure_mcp_server",
    }
    for section_key in ("managed_regions", "ensured_files", "ensured_gitignore", "ensured_mcp_servers"):
        implicit_op = _IMPLICIT_OPS.get(section_key)
        for entry in target_profile.get(section_key, []):
            if implicit_op and not entry.get("op"):
                entry = dict(entry)
                entry["op"] = implicit_op
            yield entry


def _dry_run_migration_op(migration_op: dict, project_root: Path) -> dict:
    """Call dry_run on a destructive migration op dict.

    In v1.0 Step 2 there are no registered destructive op classes, so this
    returns a stub report with ``would_fail_precondition=True``.
    """
    op_id = migration_op.get("op_id", "unknown")
    op_type = migration_op.get("op_type", "unknown")
    args = migration_op.get("args", {})
    depends_on = migration_op.get("depends_on_op")

    # No destructive op classes registered in v1.0 — return unregistered stub.
    return {
        "op_id": op_id,
        "op_type": op_type,
        "would_apply": False,
        "would_skip_idempotent": False,
        "would_overwrite_drift": False,
        "would_fail_precondition": True,
        "drift_summary": None,
        "_note": f"destructive op type {op_type!r} not registered in v1.0",
        **({"depends_on_op": depends_on} if depends_on else {}),
    }


def _dry_run_target_profile_entry(entry: dict, project_root: Path) -> dict:
    """Call dry_run on a target-profile entry dict.

    Looks up the op class in ``OP_REGISTRY`` by ``entry["op"]``.  If not found
    (Step 2 — registry empty), returns a stub with ``would_fail_precondition=True``.
    """
    op_type = entry.get("op", "unknown")
    op_id = entry.get("id", entry.get("target", op_type))
    args = dict(entry)  # pass full entry as args; op extracts what it needs

    cls = OP_REGISTRY.get(op_type)
    if cls is None:
        return {
            "op_id": op_id,
            "op_type": op_type,
            "would_apply": False,
            "would_skip_idempotent": False,
            "would_overwrite_drift": False,
            "would_fail_precondition": True,
            "drift_summary": None,
            "_note": f"op type {op_type!r} not yet registered (Step 3 will add it)",
        }

    instance = cls()
    try:
        report = instance.dry_run(project_root, args)
        return dict(report)
    except Exception as exc:  # noqa: BLE001
        return {
            "op_id": op_id,
            "op_type": op_type,
            "would_apply": False,
            "would_skip_idempotent": False,
            "would_overwrite_drift": False,
            "would_fail_precondition": True,
            "drift_summary": None,
            "error": str(exc),
        }


def _op_tag(op: dict) -> str:
    """Return the human-readable status tag for a dry-run report entry."""
    if op.get("would_overwrite_drift"):
        return "would_overwrite_drift"
    if op.get("would_skip_idempotent"):
        return "would_skip_idempotent"
    if op.get("would_fail_precondition"):
        return "would_fail_precondition"
    if op.get("would_apply"):
        return "would_apply"
    return "?"


def _to_serializable(report: dict) -> dict:
    """Convert any Path values in a report dict to strings for JSON serialization."""
    result = {}
    for k, v in report.items():
        if isinstance(v, Path):
            result[k] = str(v)
        else:
            result[k] = v
    return result
