"""Op base classes and registry for ark-update.

Two-base-class design (codex P2-4)
-----------------------------------
All v1.0 ops are **target-profile ops** — they converge the project toward a
declarative template.  A second base class, ``DestructiveOp``, is scaffolded
here but has zero concrete subclasses in v1.0.

Why two bases?
  ``TargetProfileOp.detect_drift`` answers: "Does the current file content differ
  from what the target template expects?"  This is an idempotency check — the
  same question on every run.

  ``DestructiveOp.detect_drift`` (when implemented) will answer: "Has this
  one-shot destructive transform already been applied?"  That is a version-gate
  question, not an idempotency check.  The two questions are fundamentally
  different, so they must not share a base class.  Subclassing ``TargetProfileOp``
  for a destructive op would cause ``detect_drift`` to fire on every Phase-2
  convergence run, which is wrong — destructive ops are dispatched once by the
  Phase-1 engine, version-gated, never re-run.

Registry protocol
-----------------
Ops register themselves by decorating their class with ``@register_op("<op-type>")``.
The decorator inserts the class into ``OP_REGISTRY`` keyed by op-type name.
``migrate.py`` imports this module and then imports each op module (so the
decorators fire); after that, ``OP_REGISTRY`` is fully populated.

In v1.0 Step 2 the registry is empty.  Step 3 fills it with the 5 target-profile
op classes.

Typed-dict return shapes
------------------------
All abstract methods are documented with their expected return-dict shapes.
These shapes are load-bearing (Step 3 per-op tests assert them explicitly):

``ApplyResult``::

    {
        "op_id":     str,
        "op_type":   str,
        "status":    "applied" | "skipped_idempotent" | "drifted_overwritten" | "failed",
        "drift_summary":  str | None,   # present when status == "drifted_overwritten"
        "backup_path":    Path | None,  # present when a backup was written
        "error":          str | None,   # present when status == "failed"
    }

``DryRunReport``::

    {
        "op_id":                    str,
        "op_type":                  str,
        "would_apply":              bool,
        "would_skip_idempotent":    bool,
        "would_overwrite_drift":    bool,
        "would_fail_precondition":  bool,
        "drift_summary":            str | None,
    }

``DriftReport``::

    {
        "has_drift":       bool,
        "drift_summary":   str | None,   # None when has_drift is False
        "drifted_regions": list[str],    # list of region ids with drift
    }
"""
from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypedDict

# ---------------------------------------------------------------------------
# sys.path shim — allows bare "import paths" / "import state" in op modules
# ---------------------------------------------------------------------------
_scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from paths import safe_resolve  # noqa: E402 (after sys.path shim)


# ---------------------------------------------------------------------------
# Typed-dict shapes (load-bearing for Step 3 per-op tests)
# ---------------------------------------------------------------------------

class ApplyResult(TypedDict, total=False):
    op_id: str
    op_type: str
    status: str          # "applied" | "skipped_idempotent" | "drifted_overwritten" | "failed"
    drift_summary: str   # optional — present when status == "drifted_overwritten"
    backup_path: Path    # optional — present when a backup was written
    error: str           # optional — present when status == "failed"


class DryRunReport(TypedDict, total=False):
    op_id: str
    op_type: str
    would_apply: bool
    would_skip_idempotent: bool
    would_overwrite_drift: bool
    would_fail_precondition: bool
    drift_summary: str   # optional


class DriftReport(TypedDict):
    """Return type of ``TargetProfileOp.detect_drift``.

    Load-bearing: Step 3 per-op tests assert this exact shape.  ``drift_summary``
    MUST be ``None`` when ``has_drift`` is ``False``; MUST be a non-empty string
    when ``has_drift`` is ``True``.  ``drifted_regions`` is always a list (empty
    when no drift).
    """
    has_drift: bool
    drift_summary: str | None
    drifted_regions: list[str]


# ---------------------------------------------------------------------------
# Op registry
# ---------------------------------------------------------------------------

OP_REGISTRY: dict[str, type["TargetProfileOp"]] = {}


def register_op(op_type: str):
    """Class decorator — inserts the decorated class into ``OP_REGISTRY``.

    Usage::

        @register_op("ensure_claude_md_section")
        class EnsureCLAUDEMdSection(TargetProfileOp):
            ...

    The decorator fires when the module is imported.  ``migrate.py`` imports
    each op module explicitly so that all ops are registered before the engine
    dispatches any work.
    """
    def decorator(cls: type) -> type:
        OP_REGISTRY[op_type] = cls
        return cls
    return decorator


# ---------------------------------------------------------------------------
# TargetProfileOp — abstract base for all v1.0 convergence ops
# ---------------------------------------------------------------------------

class TargetProfileOp(ABC):
    """Abstract base class for target-profile convergence ops.

    All 5 v1.0 ops (``ensure_claude_md_section``, ``ensure_gitignore_entry``,
    ``ensure_mcp_server``, ``create_file_from_template``,
    ``ensure_routing_rules_block``) subclass this.

    Path-safety contract (codex P1-1 — defense in depth)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Before dispatching to ``_apply_impl``/``_dry_run_impl``/``_detect_drift_impl``,
    this base class passes every file-path value in ``args`` through
    ``paths.safe_resolve(project_root, ...)``.  Subclasses receive pre-validated,
    fully-resolved ``Path`` objects in ``safe_args``; they MUST NOT call
    ``safe_resolve`` again (double-call is harmless but redundant).  The
    primary safety gate is at load time in ``migrate.py`` (full target-profile
    scan); this is the secondary gate at dispatch time.

    Concrete subclasses must implement ``_apply_impl``, ``_dry_run_impl``,
    and ``_detect_drift_impl``.  Do NOT override ``apply``/``dry_run``/
    ``detect_drift`` directly (the base wrappers enforce path safety and
    typing invariants).
    """

    # Subclasses must set these at the class level.
    OP_TYPE: str = ""      # e.g. "ensure_claude_md_section"
    PATH_ARGS: tuple[str, ...] = ()  # arg keys whose values are file paths

    # ------------------------------------------------------------------
    # Public interface (called by engine)
    # ------------------------------------------------------------------

    def apply(self, project_root: Path, args: dict) -> ApplyResult:
        """Apply this op, returning an ``ApplyResult`` dict.

        Base class resolves all ``PATH_ARGS`` via ``safe_resolve`` before
        delegating to ``_apply_impl``.  Subclasses see resolved paths.
        """
        safe_args = self._safe_args(project_root, args)
        return self._apply_impl(project_root, safe_args)

    def dry_run(self, project_root: Path, args: dict) -> DryRunReport:
        """Compute what ``apply`` would do without writing anything.

        Returns a ``DryRunReport`` dict.
        """
        safe_args = self._safe_args(project_root, args)
        return self._dry_run_impl(project_root, safe_args)

    def detect_drift(self, project_root: Path, args: dict) -> DriftReport:
        """Detect whether the managed region/file has drifted from the template.

        Returns a ``DriftReport`` typed dict::

            {
                "has_drift":       bool,
                "drift_summary":   str | None,
                "drifted_regions": list[str],
            }

        Callers MUST treat ``parsed_version != target_profile.version`` as
        drift (codex P2-3 / markers.py version-drift-signal semantics), even
        when region text content is byte-identical to the target template.
        The ``drift_summary`` field propagates into the run summary and
        SKILL.md user-facing warning (pre-mortem mitigation 1.4).
        """
        safe_args = self._safe_args(project_root, args)
        return self._detect_drift_impl(project_root, safe_args)

    # ------------------------------------------------------------------
    # Abstract implementation hooks (override in subclasses)
    # ------------------------------------------------------------------

    @abstractmethod
    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        ...

    @abstractmethod
    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        ...

    @abstractmethod
    def _detect_drift_impl(self, project_root: Path, args: dict) -> DriftReport:
        ...

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_args(self, project_root: Path, args: dict) -> dict:
        """Return a copy of *args* with PATH_ARGS values resolved via safe_resolve."""
        safe = dict(args)
        for key in self.PATH_ARGS:
            if key in safe and safe[key] is not None:
                safe[key] = safe_resolve(project_root, safe[key])
        return safe


# ---------------------------------------------------------------------------
# DestructiveOp — abstract base for future destructive primitives
# ---------------------------------------------------------------------------

class DestructiveOp(ABC):
    """Abstract base class for destructive migration primitives.

    **Reserved for future use — zero concrete subclasses in v1.0.**

    Destructive primitives (``rename_frontmatter_field``, ``deprecate_file``,
    ``remove_managed_region``) are deferred to a future release when an actual
    destructive migration is needed.

    Why this MUST NOT subclass ``TargetProfileOp``
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``TargetProfileOp.detect_drift`` answers: "Does content differ from the
    target template?" — an idempotency check, run on every Phase-2 convergence.

    ``DestructiveOp.detect_drift`` (when implemented) will answer: "Has this
    one-shot transform already been applied?" — a version-gate check, dispatched
    once per version in Phase-1, never re-run.

    These are fundamentally different questions.  Sharing a base class would
    cause Phase-2 convergence to invoke destructive ``detect_drift``, which is
    semantically wrong and potentially dangerous.

    ``depends_on_op`` field
    ~~~~~~~~~~~~~~~~~~~~~~
    YAML entries for destructive migration ops may carry an optional
    ``depends_on_op: <op-id>`` field.  If the referenced op failed (its id
    appears in ``failed_ops[]`` of the current run), the engine skips this op
    and marks it ``skipped_due_to_dependency``.  This field is parsed and stored
    by ``migrate.py`` at load time; it is not used in v1.0 (no destructive
    migrations ship) but the parser wires it.
    """

    OP_TYPE: str = ""

    @abstractmethod
    def apply(self, project_root: Path, args: dict) -> dict:
        """Apply this destructive migration op.

        Returns a dict with at minimum: ``{op_id, op_type, status}``.
        """
        ...

    @abstractmethod
    def dry_run(self, project_root: Path, args: dict) -> dict:
        """Compute what ``apply`` would do, writing nothing.

        Returns a dict with at minimum: ``{op_id, op_type, would_apply}``.
        """
        ...

    # Note: NO detect_drift here.  Version-gate detection for destructive ops
    # is handled by the engine before dispatching the op (comparing pending
    # semver against installed_version), not by the op itself.
