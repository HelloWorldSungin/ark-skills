"""Op: ensure_gitignore_entry — append a single line to .gitignore if absent.

Target-profile YAML shape::

    ensured_gitignore:
      - entry: .ark-workflow/       # the exact line to append if absent
        since: 1.13.0               # first plugin version that introduced this
        # optional file: override; default is "project_root/.gitignore"

Behavior
--------
- ``.gitignore`` absent → create it with entry + trailing newline.
- Entry already present (case-sensitive exact-line match) → no-op,
  ``status="skipped_idempotent"``.
- Entry absent → append, ensuring a preceding newline if file does not end
  with one, then entry + trailing newline.  ``status="applied"``.
- No backup: ``.gitignore`` is append-safe and the operation is reversible
  by removing the appended line.

detect_drift
~~~~~~~~~~~~
Always returns ``{has_drift: False, drift_summary: None, drifted_regions: []}``.
The entry is either present or absent — there is no "managed region" concept
here, so there is no middle ground that qualifies as drift.

PATH_ARGS
~~~~~~~~~
``PATH_ARGS = ("file",)`` because the op accepts an optional ``file:`` override
arg.  When ``file`` is absent the op defaults to ``project_root / ".gitignore"``.
The base-class ``_safe_args`` shim path-validates ``file`` when present;
when absent the op constructs the default path directly under ``project_root``
(always safe — no traversal possible).
"""
from __future__ import annotations

from pathlib import Path

from ops import (  # type: ignore[import]
    ApplyResult,
    DriftReport,
    DryRunReport,
    TargetProfileOp,
    register_op,
)


@register_op("ensure_gitignore_entry")
class EnsureGitignoreEntry(TargetProfileOp):
    """Append a single line to .gitignore if absent."""

    OP_TYPE = "ensure_gitignore_entry"
    # Accept optional "file" override; base class validates it via safe_resolve.
    PATH_ARGS = ("file",)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _gitignore_path(self, project_root: Path, args: dict) -> Path:
        """Return the resolved .gitignore path.

        If args contains a pre-validated ``file`` key (set by base _safe_args),
        use it.  Otherwise default to ``project_root / ".gitignore"``.
        """
        if args.get("file") is not None:
            return Path(args["file"])
        return project_root / ".gitignore"

    def _entry_present(self, content: str, entry: str) -> bool:
        """Return True if *entry* is an exact line in *content*."""
        return any(line == entry for line in content.splitlines())

    # ------------------------------------------------------------------
    # Abstract implementation hooks
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        op_id: str = args.get("id", "ensure_gitignore_entry")
        entry: str = args["entry"]
        gitignore = self._gitignore_path(project_root, args)

        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            if self._entry_present(content, entry):
                return ApplyResult(
                    op_id=op_id,
                    op_type=self.OP_TYPE,
                    status="skipped_idempotent",
                    drift_summary=None,
                    backup_path=None,
                    error=None,
                )
            # Append: ensure preceding newline, then entry + trailing newline.
            prefix = "" if content.endswith("\n") else "\n"
            gitignore.write_text(content + prefix + entry + "\n", encoding="utf-8")
        else:
            # Create with just the entry.
            gitignore.parent.mkdir(parents=True, exist_ok=True)
            gitignore.write_text(entry + "\n", encoding="utf-8")

        return ApplyResult(
            op_id=op_id,
            op_type=self.OP_TYPE,
            status="applied",
            drift_summary=None,
            backup_path=None,
            error=None,
        )

    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        op_id: str = args.get("id", "ensure_gitignore_entry")
        entry: str = args["entry"]
        gitignore = self._gitignore_path(project_root, args)

        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            already_present = self._entry_present(content, entry)
        else:
            already_present = False

        return DryRunReport(
            op_id=op_id,
            op_type=self.OP_TYPE,
            would_apply=not already_present,
            would_skip_idempotent=already_present,
            would_overwrite_drift=False,
            would_fail_precondition=False,
            drift_summary=None,
        )

    def _detect_drift_impl(self, project_root: Path, args: dict) -> DriftReport:
        # No managed-region concept for gitignore: entry is present xor absent.
        # Neither state counts as "drift" in the managed-region sense.
        return DriftReport(
            has_drift=False,
            drift_summary=None,
            drifted_regions=[],
        )
