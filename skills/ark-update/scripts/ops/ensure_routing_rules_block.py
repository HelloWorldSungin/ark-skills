"""Op: ensure_routing_rules_block — specialized ensure_claude_md_section for routing rules.

This op is a thin specialization of ``EnsureClaudeMdSection`` with two
hardcoded canonical values:

    - ``id`` is always ``"routing-rules"`` — the stable region identifier for
      the ark-workflow routing block in CLAUDE.md.  Users cannot override this.
    - ``template`` is always ``"routing-template.md"`` — the byte-copy of
      ``skills/ark-workflow/references/routing-template.md`` that lives under
      ``skills/ark-update/templates/``.

Why subclass instead of duplicating?
-------------------------------------
The spec states: "specialized ``ensure_claude_md_section`` with the canonical
routing-template.md. Markers: ``id=routing-rules``."  Subclassing is the
direct expression of that relationship — all insertion, backup-on-drift,
idempotency, and path-safety logic lives in the parent; this class only
enforces the two canonical invariants.

Target-profile YAML shape::

    managed_regions:
      - op: ensure_routing_rules_block
        file: CLAUDE.md          # optional: defaults to CLAUDE.md
        since: 1.3.0
        version: 1.12.0

The ``id`` and ``template`` fields are injected by ``_canonical_args``; they
MUST NOT appear in the target-profile YAML entry (or they will be silently
overwritten, keeping the canonical values authoritative).
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path shim — mirrors the shim in ensure_claude_md_section.py
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops import register_op  # noqa: E402
from ops.ensure_claude_md_section import EnsureClaudeMdSection  # noqa: E402

_CANONICAL_ID = "routing-rules"
_CANONICAL_TEMPLATE = "routing-template.md"


@register_op("ensure_routing_rules_block")
class EnsureRoutingRulesBlock(EnsureClaudeMdSection):
    """Converge the routing-rules managed region toward ``routing-template.md``.

    Identical to ``EnsureClaudeMdSection`` except ``id`` and ``template`` are
    hardcoded to ``"routing-rules"`` and ``"routing-template.md"``
    respectively — neither field can be overridden via the target profile.
    """

    OP_TYPE = "ensure_routing_rules_block"
    PATH_ARGS = ("file",)  # inherited from EnsureClaudeMdSection but stated explicitly

    # ------------------------------------------------------------------
    # Canonical-args injection
    # ------------------------------------------------------------------

    def _canonical_args(self, args: dict) -> dict:
        """Return a copy of *args* with id and template forced to canonical values."""
        return {**args, "id": _CANONICAL_ID, "template": _CANONICAL_TEMPLATE}

    # ------------------------------------------------------------------
    # Override the three impl hooks — inject canonical args then delegate
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict):
        return super()._apply_impl(project_root, self._canonical_args(args))

    def _dry_run_impl(self, project_root: Path, args: dict):
        return super()._dry_run_impl(project_root, self._canonical_args(args))

    def _detect_drift_impl(self, project_root: Path, args: dict):
        return super()._detect_drift_impl(project_root, self._canonical_args(args))
