"""Op: ensure_claude_md_section — declarative CLAUDE.md managed-region convergence.

This op manages a single ark-marked region inside a target file (typically
CLAUDE.md).  It uses HTML comment markers to delimit ownership:

    <!-- ark:begin id=<id> version=<semver> -->
    ... region content (owned by ark-update) ...
    <!-- ark:end id=<id> -->

Version= drift-signal semantics (codex P2-3):
    A mismatched ``version=`` in the begin-marker triggers drift even when the
    region text content is byte-identical to the template.  This keeps markers
    honest about which managed-region version they carry.  ``detect_drift``
    returns ``has_drift=True`` whenever ``parsed_version != args["version"]``,
    regardless of content comparison.

Behavior per run:
    - **Missing target file**: create the file (empty) then insert the region.
    - **Missing region**: insert the region at EOF.
    - **Region present, content matches template AND version= matches**: no-op
      (``status="skipped_idempotent"``).
    - **Region present, content differs OR version= differs**: backup the file
      to ``.ark/backups/<basename>.<timestamp>.bak``, overwrite the region.
      Returns ``status="drifted_overwritten"`` with ``drift_summary`` and
      ``backup_path``.
    - **Mismatched begin/end ids or nested markers**: raise
      ``MarkerIntegrityError``; engine exits code 4 and points user to
      ``/ark-onboard repair``.

Path-safety:
    ``PATH_ARGS = ("file",)`` causes the base class to pass ``args["file"]``
    through ``safe_resolve(project_root, ...)`` before this impl sees it.
    Absolute paths, ``..``-escapes, and symlink-escapes raise
    ``PathTraversalError``.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path shim — allows bare imports of sibling scripts modules
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from markers import extract_regions, insert_region, replace_region, MarkerIntegrityError  # noqa: E402
from state import backup_path as _backup_path_unused  # noqa: F401, E402 — kept for API compat
from ops import (  # noqa: E402
    TargetProfileOp,
    ApplyResult,
    DryRunReport,
    DriftReport,
    register_op,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_template(skills_root: Path | str, template_name: str) -> str:
    """Read the template file from ``<skills_root>/skills/ark-update/templates/<name>``.

    Parameters
    ----------
    skills_root:
        The root of the ark-skills plugin installation (passed as
        ``args["skills_root"]`` by ``migrate.py``).
    template_name:
        Basename of the template file (e.g. ``"omc-routing-block.md"``).

    Returns
    -------
    str
        Template content.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist.
    """
    template_path = Path(skills_root) / "skills" / "ark-update" / "templates" / template_name
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template {template_name!r} not found at {template_path}. "
            f"Check skills_root and ensure templates/ is populated."
        )
    return template_path.read_text(encoding="utf-8")


def _detect_region_drift(
    region_content: str,
    region_version: str,
    template_content: str,
    target_version: str,
) -> tuple[bool, str | None]:
    """Return ``(has_drift, drift_summary)`` for a single region comparison.

    Drift is declared when:
    - Content differs (byte-level mismatch after normalisation), OR
    - ``region_version != target_version`` (codex P2-3 version-drift signal).

    Parameters
    ----------
    region_content:
        Content parsed from the existing marker region (from ``ManagedRegion.content``).
    region_version:
        ``version=`` parsed from the existing begin marker.
    template_content:
        Content from the template file (authoritative target).
    target_version:
        Version from ``target-profile.yaml`` (authoritative version).

    Returns
    -------
    tuple[bool, str | None]
        ``(True, "reason string")`` when drift detected;
        ``(False, None)`` when no drift.
    """
    content_mismatch = region_content != template_content
    version_mismatch = region_version != target_version

    if content_mismatch and version_mismatch:
        return True, (
            f"Region content differs from template AND version= is stale "
            f"(marker has version={region_version!r}, target expects {target_version!r})."
        )
    if content_mismatch:
        return True, "Region content differs from template (user edit or template update)."
    if version_mismatch:
        # P2-3: version mismatch is drift even when content is byte-identical.
        return True, (
            f"Stale version= in begin-marker: marker has version={region_version!r}, "
            f"target expects {target_version!r}. Content is byte-identical but "
            f"re-stamp is required (codex P2-3)."
        )
    return False, None


# ---------------------------------------------------------------------------
# Op implementation
# ---------------------------------------------------------------------------

@register_op("ensure_claude_md_section")
class EnsureClaudeMdSection(TargetProfileOp):
    """Converge a single ark-managed region in a target file toward the template.

    Target-profile YAML shape::

        managed_regions:
          - id: omc-routing
            file: CLAUDE.md
            template: omc-routing-block.md
            since: 1.13.0
            version: 1.13.0

    All five required fields (``id``, ``file``, ``template``, ``version``,
    ``skills_root``) must be present in ``args``.  ``migrate.py`` injects
    ``skills_root`` automatically.
    """

    OP_TYPE = "ensure_claude_md_section"
    PATH_ARGS = ("file",)  # base class resolves this via safe_resolve

    # ------------------------------------------------------------------
    # _apply_impl
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        target_file: Path = args["file"]  # already resolved by base class
        region_id: str = args["id"]
        target_version: str = args["version"]
        template_content: str = _read_template(args["skills_root"], args["template"])

        op_id = args.get("op_id", region_id)

        # Ensure target file exists (create empty if missing).
        if not target_file.exists():
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text("", encoding="utf-8")

        # Parse existing regions (raises MarkerIntegrityError on violations).
        regions = extract_regions(target_file)
        matching = [r for r in regions if r.id == region_id]

        if not matching:
            # Region missing — insert at EOF.
            insert_region(target_file, region_id, target_version, template_content)
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="applied",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        region = matching[0]
        has_drift, drift_summary = _detect_region_drift(
            region.content, region.version, template_content, target_version
        )

        if not has_drift:
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        # Drift detected — backup then overwrite.
        ark_dir = project_root / ".ark"
        ark_dir.mkdir(parents=True, exist_ok=True)
        backups_dir = ark_dir / "backups"
        backups_dir.mkdir(exist_ok=True)

        # Include region_id in the backup filename to prevent collision when
        # multiple regions in the same file drift during a single run.
        # Format: <basename>.<region_id>.<timestamp>.bak
        from datetime import datetime, timezone as _tz
        ts = datetime.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")
        bak_path = backups_dir / f"{target_file.name}.{region_id}.{ts}.bak"
        pre_bytes = target_file.read_bytes()
        shutil.copy2(target_file, bak_path)

        # Write .meta.json sidecar for backup provenance tracking.
        # Schema: {op, region_id, run_id, pre_hash, reason}
        import hashlib
        import uuid
        meta = {
            "op": self.OP_TYPE,
            "region_id": region_id,
            "run_id": str(uuid.uuid4()),
            "pre_hash": hashlib.sha256(pre_bytes).hexdigest(),
            "reason": drift_summary or "drift detected",
        }
        meta_path = Path(str(bak_path) + ".meta.json")
        import json as _json
        meta_path.write_text(_json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        replace_region(target_file, region_id, template_content, target_version)

        return ApplyResult(
            op_id=op_id,
            op_type=self.OP_TYPE,
            status="drifted_overwritten",
            drift_summary=drift_summary,
            backup_path=bak_path,
            error=None,
        )

    # ------------------------------------------------------------------
    # _dry_run_impl
    # ------------------------------------------------------------------

    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        """Compute what apply would do WITHOUT writing anything.

        ``test_dry_run_matches_apply`` verifies that this returns the same
        decision as ``apply`` would make for every scenario.  No filesystem
        side-effects are produced.
        """
        target_file: Path = args["file"]  # already resolved by base class
        region_id: str = args["id"]
        target_version: str = args["version"]
        template_content: str = _read_template(args["skills_root"], args["template"])

        op_id = args.get("op_id", region_id)

        if not target_file.exists():
            # File missing → apply would create + insert.
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=True,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        regions = extract_regions(target_file)
        matching = [r for r in regions if r.id == region_id]

        if not matching:
            # Region absent → apply would insert.
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=True,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        region = matching[0]
        has_drift, drift_summary = _detect_region_drift(
            region.content, region.version, template_content, target_version
        )

        if not has_drift:
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=True,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        return DryRunReport(
            op_id=op_id,
            op_type=self.OP_TYPE,
            would_apply=False,
            would_skip_idempotent=False,
            would_overwrite_drift=True,
            would_fail_precondition=False,
            drift_summary=drift_summary,
        )

    # ------------------------------------------------------------------
    # _detect_drift_impl
    # ------------------------------------------------------------------

    def _detect_drift_impl(self, project_root: Path, args: dict) -> DriftReport:
        """Detect whether the managed region has drifted from the template.

        Returns the typed ``DriftReport`` dict::

            {
                "has_drift":       bool,
                "drift_summary":   str | None,   # None when has_drift is False
                "drifted_regions": list[str],     # region ids with drift
            }

        Drift is declared when:
        - The target file does not exist, OR
        - The region is missing from the file, OR
        - Region content differs from template, OR
        - ``version=`` in the begin-marker differs from ``args["version"]``
          (codex P2-3 version-drift signal — even byte-identical content is
          considered drift when the marker version is stale).
        """
        target_file: Path = args["file"]
        region_id: str = args["id"]
        target_version: str = args["version"]
        template_content: str = _read_template(args["skills_root"], args["template"])

        if not target_file.exists():
            return DriftReport(
                has_drift=True,
                drift_summary=f"Target file {target_file} does not exist.",
                drifted_regions=[region_id],
            )

        regions = extract_regions(target_file)
        matching = [r for r in regions if r.id == region_id]

        if not matching:
            return DriftReport(
                has_drift=True,
                drift_summary=(
                    f"Region id={region_id!r} not found in {target_file}."
                ),
                drifted_regions=[region_id],
            )

        region = matching[0]
        has_drift, drift_summary = _detect_region_drift(
            region.content, region.version, template_content, target_version
        )

        if has_drift:
            return DriftReport(
                has_drift=True,
                drift_summary=drift_summary,
                drifted_regions=[region_id],
            )

        return DriftReport(
            has_drift=False,
            drift_summary=None,
            drifted_regions=[],
        )
