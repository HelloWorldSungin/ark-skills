"""Op: create_file_from_template — copy a template file into the project if target absent.

Most conservative op in v1.0: NEVER overwrites existing files.

Target-profile YAML shape::

    ensured_files:
      - id: setup-vault-symlink
        target: scripts/setup-vault-symlink.sh   # path under project_root
        template: setup-vault-symlink.sh          # file under skills/ark-update/templates/
        since: 1.11.0
        only_if_centralized_vault: true           # optional gate; engine resolves
        mode: 0o755                               # optional; default 0o644

Behavior per run
----------------
- Target absent: copy template bytes to target (mkdir -p parents; chmod if
  ``mode:`` specified).  ``status="applied"``.
- Target exists as regular file: NO-OP.  ``status="skipped_idempotent"``.
  **never overwrites — out of scope for v1.0.**
- Target exists as symlink: REFUSE.  Raises ``SymlinkTargetError``.
  Engine exits code 3.
- Template not found under skills_root: REFUSE.  Raises ``FileNotFoundError``.
- Gate condition present and false: ``status="skipped_precondition"``.

detect_drift
~~~~~~~~~~~~
Always returns ``{has_drift: False, drift_summary: None, drifted_regions: []}``.
This op either exists (and was never overwritten) or doesn't; there is no
managed-region concept.  The file is not "owned" post-creation — user edits
are intentional.

PATH_ARGS
~~~~~~~~~
``PATH_ARGS = ("target",)`` so the base-class ``_safe_args`` shim validates
``target`` via ``safe_resolve(project_root, ...)`` before this impl sees it.
Absolute paths, ``..``-escapes, and symlink-escapes (where the resolved
destination lies outside the project root) raise ``PathTraversalError``.

Symlink-as-target handling (codex P1-1)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``safe_resolve`` catches symlinks whose resolved target escapes the project
root.  However, a symlink pointing to a file *inside* the root is not a
traversal — it resolves cleanly and passes.  We therefore add an explicit
symlink check here: if the resolved target path *itself* is a symlink (even
an in-root one) we raise ``SymlinkTargetError`` rather than overwriting the
symlink's pointee.  Writing to a symlink is almost never intentional for a
"copy template" op.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path shim — allows bare imports of sibling scripts modules
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops import (  # noqa: E402
    ApplyResult,
    DriftReport,
    DryRunReport,
    TargetProfileOp,
    register_op,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class SymlinkTargetError(Exception):
    """Raised when the resolved target path is a symlink.

    Writing through a symlink is almost never intentional for a template-copy
    op.  Rather than silently overwriting the symlink's pointee, we refuse and
    ask the user to resolve the situation manually.
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_template_bytes(skills_root: Path | str, template_name: str) -> bytes:
    """Read the template file as raw bytes from the canonical templates directory.

    Parameters
    ----------
    skills_root:
        Root of the ark-skills plugin installation (``args["skills_root"]``).
    template_name:
        Basename of the template file (e.g. ``"setup-vault-symlink.sh"``).

    Returns
    -------
    bytes
        Raw file content.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist under the expected path.
    """
    template_path = (
        Path(skills_root) / "skills" / "ark-update" / "templates" / template_name
    )
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template {template_name!r} not found at {template_path}. "
            f"Check skills_root and ensure templates/ is populated."
        )
    return template_path.read_bytes()


def _check_gate(args: dict) -> bool:
    """Return True if all ``only_if_*`` gate conditions are satisfied.

    In v1.0 the engine injects boolean gate values into ``args`` under the
    same key name as the YAML field (e.g. ``only_if_centralized_vault``).
    If a gate key is absent from args it defaults to ``True`` (no gate =
    unconditional apply).

    TODO: actual flag resolution from CLAUDE.md is wired in migrate.py;
    this helper just reads the pre-resolved boolean that the engine injects.
    """
    for key, value in args.items():
        if key.startswith("only_if_"):
            if not value:
                return False
    return True


def _check_symlink(target: Path) -> None:
    """Raise ``SymlinkTargetError`` if *target* is a symlink.

    Called before any write attempt.  Works on both existing and non-existing
    symlinks (dangling symlinks are still symlinks).
    """
    if target.is_symlink():
        raise SymlinkTargetError(
            f"Target path {target!r} is a symlink. "
            f"create_file_from_template refuses to write through symlinks "
            f"(codex P1-1). Remove or resolve the symlink manually, then re-run."
        )


# ---------------------------------------------------------------------------
# Op implementation
# ---------------------------------------------------------------------------

@register_op("create_file_from_template")
class CreateFileFromTemplate(TargetProfileOp):
    """Copy a template file into the project if the target does not yet exist.

    Target-profile YAML shape::

        ensured_files:
          - id: setup-vault-symlink
            target: scripts/setup-vault-symlink.sh
            template: setup-vault-symlink.sh
            since: 1.11.0
            only_if_centralized_vault: true   # optional
            mode: 0o755                        # optional; default 0o644

    Required args: ``id``, ``target`` (resolved by base), ``template``,
    ``skills_root`` (injected by migrate.py).
    Optional args: ``mode`` (int, default 0o644), ``only_if_*`` gates (bool).
    """

    OP_TYPE = "create_file_from_template"
    PATH_ARGS = ("target",)  # base class validates via safe_resolve

    # ------------------------------------------------------------------
    # _safe_args override — symlink check BEFORE safe_resolve follows symlinks
    # ------------------------------------------------------------------

    def _safe_args(self, project_root: Path, args: dict) -> dict:
        """Check for symlink target BEFORE safe_resolve follows the symlink.

        ``safe_resolve`` calls ``Path.resolve()`` which follows symlinks
        transparently.  If we wait until ``_apply_impl``, the resolved path
        is the real file — not a symlink — and the check is a no-op.

        By overriding here we inspect ``(project_root / args["target"])``
        with ``.is_symlink()`` (no resolution) before delegating to the
        parent resolver.  This catches in-root symlinks that safe_resolve
        would otherwise silently follow (codex P1-1).
        """
        if "target" in args and args["target"] is not None:
            pre_resolved = project_root / args["target"]
            _check_symlink(pre_resolved)
        return super()._safe_args(project_root, args)

    # ------------------------------------------------------------------
    # _apply_impl
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        target: Path = args["target"]  # already resolved by base class
        op_id: str = args.get("id", "create_file_from_template")

        # Gate check — skipped_precondition when any only_if_* is False.
        if not _check_gate(args):
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_precondition",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        # Symlink check on the resolved path (defense in depth — _safe_args
        # already checked the pre-resolved path; this catches edge cases where
        # the resolved path itself is a symlink, e.g. a symlink to a symlink).
        _check_symlink(target)

        # Idempotency: target already exists as a regular file — never overwrite.
        # never overwrites — out of scope for v1.0 (skipped_idempotent if target exists)
        if target.exists():
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        # Template lookup — raises FileNotFoundError on miss.
        template_bytes = _read_template_bytes(args["skills_root"], args["template"])

        # mkdir -p parents then write.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(template_bytes)

        # Optional mode bits (e.g. 0o755 for executable scripts).
        mode: int | None = args.get("mode")
        if mode is not None:
            os.chmod(target, mode)

        return ApplyResult(
            op_id=op_id,
            op_type=self.OP_TYPE,
            status="applied",
            drift_summary=None,
            backup_path=None,
            error=None,
        )

    # ------------------------------------------------------------------
    # _dry_run_impl
    # ------------------------------------------------------------------

    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        """Compute what apply would do WITHOUT writing anything.

        ``test_dry_run_matches_apply`` verifies that this returns the same
        decision as apply would make for every scenario.  No filesystem
        side-effects are produced.
        """
        target: Path = args["target"]  # already resolved by base class
        op_id: str = args.get("id", "create_file_from_template")

        # Gate check.
        if not _check_gate(args):
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=True,
                drift_summary=None,
            )

        # Symlink check — dry_run mirrors the apply refusal.
        _check_symlink(target)

        # Idempotency check.
        if target.exists():
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=True,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        # Template existence check (raises FileNotFoundError on miss — same as apply).
        _read_template_bytes(args["skills_root"], args["template"])

        return DryRunReport(
            op_id=op_id,
            op_type=self.OP_TYPE,
            would_apply=True,
            would_skip_idempotent=False,
            would_overwrite_drift=False,
            would_fail_precondition=False,
            drift_summary=None,
        )

    # ------------------------------------------------------------------
    # _detect_drift_impl
    # ------------------------------------------------------------------

    def _detect_drift_impl(self, project_root: Path, args: dict) -> DriftReport:
        """Detect drift — always returns has_drift=False for this op.

        ``create_file_from_template`` has no managed-region concept.  Once the
        file is placed, the user owns it entirely.  Post-creation edits are
        intentional; we never re-stamp or overwrite.  There is no middle-ground
        "drift" state: either the file exists (and was never overwritten by us)
        or it doesn't.  Neither state qualifies as drift in the managed-region
        sense.
        """
        return DriftReport(
            has_drift=False,
            drift_summary=None,
            drifted_regions=[],
        )
