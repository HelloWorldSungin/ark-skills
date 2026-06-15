"""Op: ensure_python_set_entry — insert a string entry into a Python set literal if absent.

Target-profile YAML shape::

    ensured_python_set_entries:
      - id: graphify-exclude-generated
        op: ensure_python_set_entry
        file: vault/_meta/generate-index.py   # path relative to project_root
        set_name: EXCLUDE_DIRS                # name of the set assignment to target
        entry: "generated"                    # string value to ensure is present
        since: 1.28.0
        version: 1.28.0
        only_if_centralized_vault: true

Behavior
--------
- File absent → no-op, ``status="skipped_idempotent"``, drift_summary explains.
- File present but set assignment ``{set_name} = { ... }`` not found →
  no-op, ``status="skipped_idempotent"``, drift_summary explains.
- Entry already in the set (exact string match ``"<entry>"`` inside the braces) →
  no-op, ``status="skipped_idempotent"``.
- Entry absent → insert ``, "<entry>"`` before the closing brace, write back.
  ``status="applied"``.

Only the targeted set literal line is modified; all other file content is
preserved byte-for-byte.  No backup is written (the change is a trivial
insertion, fully reversible by removing the inserted token).

Set-literal regex
~~~~~~~~~~~~~~~~~
The op matches a **single-line** assignment of the form::

    EXCLUDE_DIRS = {"foo", "bar"}

Regex: ``^(\\s*{set_name}\\s*=\\s*\\{{)([^}}]*)(\\}})``

This is intentionally conservative: multi-line set literals, comprehensions,
and function-call sets are not matched, and the op skips cleanly when the
pattern is absent (drift_summary explains the miss).

detect_drift
~~~~~~~~~~~~
Returns ``has_drift=True`` when the file exists AND the set assignment is found
AND the entry is absent.  Returns ``has_drift=False`` in all skip cases
(file/set missing → nothing to drift; entry present → already converged).

PATH_ARGS
~~~~~~~~~
``PATH_ARGS = ("file",)`` so the base-class ``_safe_args`` shim validates the
file path via ``paths.safe_resolve`` before any method body runs.
"""
from __future__ import annotations

import re
from pathlib import Path

from ops import (  # type: ignore[import]
    ApplyResult,
    DriftReport,
    DryRunReport,
    TargetProfileOp,
    register_op,
)


@register_op("ensure_python_set_entry")
class EnsurePythonSetEntry(TargetProfileOp):
    """Insert a string entry into a single-line Python set literal if absent."""

    OP_TYPE = "ensure_python_set_entry"
    PATH_ARGS = ("file",)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _target_path(self, project_root: Path, args: dict) -> Path:
        """Return the resolved target file path."""
        if args.get("file") is not None:
            return Path(args["file"])
        raise ValueError("ensure_python_set_entry requires a 'file' arg")

    def _make_pattern(self, set_name: str) -> re.Pattern[str]:
        """Return a compiled regex matching a single-line set assignment.

        Captures three groups:
          1. Opening: ``EXCLUDE_DIRS = {``  (with optional leading whitespace)
          2. Contents between the braces (may be empty)
          3. Closing: ``}``
        """
        return re.compile(
            r"^(\s*" + re.escape(set_name) + r"\s*=\s*\{)([^}]*)(\})",
            re.MULTILINE,
        )

    def _entry_token(self, entry: str) -> str:
        """Return the quoted token as it appears inside the set literal."""
        return f'"{entry}"'

    def _entry_present(self, brace_contents: str, entry: str) -> bool:
        """Return True if the quoted entry already appears in the brace contents."""
        return self._entry_token(entry) in brace_contents

    def _insert_entry(self, brace_contents: str, entry: str) -> str:
        """Return updated brace contents with the entry appended.

        Inserts ``, "entry"`` before the closing brace, with a preceding comma
        if the current contents are non-empty (after stripping whitespace).
        """
        stripped = brace_contents.rstrip()
        token = self._entry_token(entry)
        if stripped:
            return brace_contents.rstrip() + ", " + token
        return token

    # ------------------------------------------------------------------
    # Abstract implementation hooks
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        op_id: str = args.get("id", "ensure_python_set_entry")
        set_name: str = args["set_name"]
        entry: str = args["entry"]
        target = self._target_path(project_root, args)

        if not target.exists():
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=f"File not found: {target} — nothing to modify.",
                backup_path=None,
                error=None,
            )

        content = target.read_text(encoding="utf-8")
        pattern = self._make_pattern(set_name)
        m = pattern.search(content)

        if m is None:
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=(
                    f"Set assignment '{set_name} = {{...}}' not found in {target}. "
                    "Skipping — file may use a multi-line or dynamic form."
                ),
                backup_path=None,
                error=None,
            )

        brace_contents = m.group(2)
        if self._entry_present(brace_contents, entry):
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        # Insert the entry before the closing brace.
        new_contents = self._insert_entry(brace_contents, entry)
        new_line = m.group(1) + new_contents + m.group(3)
        new_content = content[: m.start()] + new_line + content[m.end() :]
        target.write_text(new_content, encoding="utf-8")

        return ApplyResult(
            op_id=op_id,
            op_type=self.OP_TYPE,
            status="applied",
            drift_summary=None,
            backup_path=None,
            error=None,
        )

    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        op_id: str = args.get("id", "ensure_python_set_entry")
        set_name: str = args["set_name"]
        entry: str = args["entry"]
        target = self._target_path(project_root, args)

        if not target.exists():
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=True,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=f"File not found: {target} — nothing to modify.",
            )

        content = target.read_text(encoding="utf-8")
        pattern = self._make_pattern(set_name)
        m = pattern.search(content)

        if m is None:
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=True,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=(
                    f"Set assignment '{set_name} = {{...}}' not found in {target}. "
                    "Skipping."
                ),
            )

        already_present = self._entry_present(m.group(2), entry)
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
        set_name: str = args["set_name"]
        entry: str = args["entry"]
        target = self._target_path(project_root, args)

        if not target.exists():
            # File absent: no managed content, no drift.
            return DriftReport(
                has_drift=False,
                drift_summary=None,
                drifted_regions=[],
            )

        content = target.read_text(encoding="utf-8")
        pattern = self._make_pattern(set_name)
        m = pattern.search(content)

        if m is None:
            # Set assignment not found: nothing managed, no drift.
            return DriftReport(
                has_drift=False,
                drift_summary=None,
                drifted_regions=[],
            )

        if self._entry_present(m.group(2), entry):
            return DriftReport(
                has_drift=False,
                drift_summary=None,
                drifted_regions=[],
            )

        # Set exists but entry is missing — this is drift.
        return DriftReport(
            has_drift=True,
            drift_summary=(
                f'"{entry}" missing from {set_name} in {target}.'
            ),
            drifted_regions=[set_name],
        )
