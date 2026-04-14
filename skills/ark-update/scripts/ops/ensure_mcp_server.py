"""Op: ensure_mcp_server — manage a single MCP server entry in .mcp.json.

Target-profile YAML shape::

    ensured_mcp_servers:
      - id: tasknotes-mcp
        file: .mcp.json              # path under project_root (default)
        key: mcpServers.tasknotes-mcp   # dot-path into the JSON to the entry
        entry:
          type: http
          url: http://localhost:3000/mcp
        since: 1.4.2

Behavior
--------
- ``.mcp.json`` missing → create with ``{"mcpServers": {"<id>": {...entry, _ark_managed: True}}}``.
  ``status="applied"``.
- Entry at ``key`` exists + ``_ark_managed: True`` + JSON-equal to entry → no-op.
  ``status="skipped_idempotent"``.
- Entry at ``key`` exists + ``_ark_managed: True`` + content differs → backup + overwrite.
  ``status="drifted_overwritten"``.
- Entry at ``key`` exists + no ``_ark_managed: True`` (user-authored) → raise ``McpClobberError``.
  Engine exits code 4; user pointed to ``/ark-onboard repair``.
- ``.mcp.json`` is malformed JSON → raise ``ValueError`` with message pointing to
  ``/ark-onboard repair``.

Ark-managed sentinel
--------------------
When this op writes an entry for the first time, it adds ``_ark_managed: true``
as a sibling field inside the entry dict.  On subsequent runs, presence of
``_ark_managed: true`` authorises the op to overwrite the entry on drift.
Absence of the marker AND a key collision → ``McpClobberError`` (clobber refusal).

Rationale for in-entry marker vs. separate namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Nesting under ``mcpServers._ark.<id>`` would require clients to know the
``_ark`` prefix when referencing the server.  In-entry ``_ark_managed: true``
keeps the entry addressable at its natural key while still authorising future
engine writes.  The sentinel field is ignored by MCP clients (unknown fields
are typically ignored).

Other user servers
------------------
All keys in ``mcpServers`` outside the managed key are PRESERVED verbatim.
The op reads the full ``.mcp.json``, modifies only the target slot, and
writes the merged result back.

dry_run
~~~~~~~
Same decision logic as ``_apply_impl``, but no file writes.

detect_drift
~~~~~~~~~~~~
Returns ``{has_drift: True, ...}`` iff the ark-managed entry content (excluding
``_ark_managed``) differs from the target ``entry``.  Returns
``{has_drift: False, ...}`` when absent (not yet created) or matching.

PATH_ARGS
~~~~~~~~~
``PATH_ARGS = ("file",)`` — ``file`` defaults to ``project_root / ".mcp.json"``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from ops import (  # type: ignore[import]
    ApplyResult,
    DriftReport,
    DryRunReport,
    TargetProfileOp,
    register_op,
)
from state import backup_path  # type: ignore[import]


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class McpClobberError(Exception):
    """Raised when the op would overwrite a user-authored (non-ark) MCP entry.

    A non-ark entry is one that exists at the target key but lacks the
    ``_ark_managed: true`` sentinel.  Overwriting it could destroy user
    configuration silently, so the op refuses and surfaces this error for
    the engine to handle (exit code 4).
    """


# ---------------------------------------------------------------------------
# Helper: dot-path navigation
# ---------------------------------------------------------------------------

def _get_dot_path(data: dict, dot_path: str) -> object:
    """Navigate a dot-separated path in *data*; return the value or ``_MISSING``."""
    parts = dot_path.split(".")
    current: object = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _set_dot_path(data: dict, dot_path: str, value: object) -> None:
    """Set the value at *dot_path* in *data*, creating intermediate dicts as needed."""
    parts = dot_path.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


_MISSING = object()  # sentinel for absent keys


# ---------------------------------------------------------------------------
# Helper: entry equality (ignores _ark_managed marker)
# ---------------------------------------------------------------------------

def _entry_without_marker(entry: dict) -> dict:
    """Return a copy of *entry* with ``_ark_managed`` removed."""
    result = dict(entry)
    result.pop("_ark_managed", None)
    return result


def _entries_equal(stored: dict, target: dict) -> bool:
    """Compare stored entry (may have ``_ark_managed``) to target (no marker)."""
    return _entry_without_marker(stored) == target


# ---------------------------------------------------------------------------
# Helper: drift summary
# ---------------------------------------------------------------------------

def _make_drift_summary(stored: dict, target: dict) -> str:
    """Produce a human-readable diff summary for the drift report."""
    stored_clean = _entry_without_marker(stored)
    added = {k: target[k] for k in target if k not in stored_clean}
    removed = {k: stored_clean[k] for k in stored_clean if k not in target}
    changed = {
        k: {"from": stored_clean[k], "to": target[k]}
        for k in target
        if k in stored_clean and stored_clean[k] != target[k]
    }
    parts: list[str] = []
    if added:
        parts.append(f"added keys: {list(added)}")
    if removed:
        parts.append(f"removed keys: {list(removed)}")
    if changed:
        parts.append(f"changed keys: {list(changed)}")
    return "; ".join(parts) if parts else "content differs"


# ---------------------------------------------------------------------------
# Op
# ---------------------------------------------------------------------------

@register_op("ensure_mcp_server")
class EnsureMcpServer(TargetProfileOp):
    """Manage a single MCP server entry in .mcp.json declaratively."""

    OP_TYPE = "ensure_mcp_server"
    PATH_ARGS = ("file",)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mcp_path(self, project_root: Path, args: dict) -> Path:
        """Return the resolved .mcp.json path."""
        if args.get("file") is not None:
            return Path(args["file"])
        return project_root / ".mcp.json"

    def _load_mcp_json(self, mcp_file: Path) -> dict:
        """Load and parse .mcp.json; raise ValueError on malformed JSON."""
        text = mcp_file.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in {mcp_file}: {exc}. "
                f"Fix the file manually or run /ark-onboard repair."
            ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a JSON object in {mcp_file}, got {type(data).__name__}. "
                f"Fix the file manually or run /ark-onboard repair."
            )
        return data

    def _write_mcp_json(self, mcp_file: Path, data: dict) -> None:
        """Write *data* to *mcp_file* as pretty-printed JSON."""
        mcp_file.parent.mkdir(parents=True, exist_ok=True)
        mcp_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _decide(
        self,
        project_root: Path,
        args: dict,
    ) -> dict:
        """Core decision logic shared by apply, dry_run, and detect_drift.

        Returns a decision dict with keys:
            action: "create" | "skip" | "overwrite" | "clobber_error" | "malformed"
            mcp_file: Path
            data: dict | None          (loaded JSON, or None if file absent/malformed)
            stored_entry: dict | None  (current value at key, or None)
            target_entry: dict         (target entry from args, no marker)
            drift_summary: str | None
            error_message: str | None  (set when action == "malformed")
        """
        op_id: str = args.get("id", "ensure_mcp_server")  # noqa: F841
        key: str = args["key"]
        target_entry: dict = args["entry"]
        mcp_file = self._mcp_path(project_root, args)

        if not mcp_file.exists():
            return {
                "action": "create",
                "mcp_file": mcp_file,
                "data": None,
                "stored_entry": None,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": None,
            }

        # File exists — parse it.
        try:
            data = self._load_mcp_json(mcp_file)
        except ValueError as exc:
            return {
                "action": "malformed",
                "mcp_file": mcp_file,
                "data": None,
                "stored_entry": None,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": str(exc),
            }

        stored = _get_dot_path(data, key)

        if stored is _MISSING:
            # Key absent in existing file — safe to create.
            return {
                "action": "create",
                "mcp_file": mcp_file,
                "data": data,
                "stored_entry": None,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": None,
            }

        if not isinstance(stored, dict):
            # Non-dict at key — treat as non-ark (clobber refusal).
            return {
                "action": "clobber_error",
                "mcp_file": mcp_file,
                "data": data,
                "stored_entry": stored,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": (
                    f"Key '{key}' in {mcp_file} holds a non-dict value. "
                    f"Cannot overwrite without the _ark_managed sentinel."
                ),
            }

        stored_dict: dict = stored  # type: ignore[assignment]

        if not stored_dict.get("_ark_managed"):
            # User-authored entry — clobber refusal.
            return {
                "action": "clobber_error",
                "mcp_file": mcp_file,
                "data": data,
                "stored_entry": stored_dict,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": (
                    f"Key '{key}' in {mcp_file} exists without '_ark_managed: true'. "
                    f"Refusing to overwrite a user-authored MCP server entry. "
                    f"Add '_ark_managed: true' to the entry to allow ark-update to manage it, "
                    f"or choose a different key in your target profile."
                ),
            }

        # Ark-managed entry — compare content.
        if _entries_equal(stored_dict, target_entry):
            return {
                "action": "skip",
                "mcp_file": mcp_file,
                "data": data,
                "stored_entry": stored_dict,
                "target_entry": target_entry,
                "drift_summary": None,
                "error_message": None,
            }

        drift_summary = _make_drift_summary(stored_dict, target_entry)
        return {
            "action": "overwrite",
            "mcp_file": mcp_file,
            "data": data,
            "stored_entry": stored_dict,
            "target_entry": target_entry,
            "drift_summary": drift_summary,
            "error_message": None,
        }

    # ------------------------------------------------------------------
    # Abstract implementation hooks
    # ------------------------------------------------------------------

    def _apply_impl(self, project_root: Path, args: dict) -> ApplyResult:
        op_id: str = args.get("id", "ensure_mcp_server")
        key: str = args["key"]
        decision = self._decide(project_root, args)
        action = decision["action"]
        mcp_file: Path = decision["mcp_file"]

        if action == "malformed":
            raise ValueError(decision["error_message"])

        if action == "clobber_error":
            raise McpClobberError(decision["error_message"])

        if action == "skip":
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="skipped_idempotent",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        target_entry = decision["target_entry"]
        # Build the entry with the ark-managed sentinel.
        managed_entry = dict(target_entry)
        managed_entry["_ark_managed"] = True

        if action == "create":
            data = decision["data"]
            if data is None:
                data = {}
            _set_dot_path(data, key, managed_entry)
            self._write_mcp_json(mcp_file, data)
            return ApplyResult(
                op_id=op_id,
                op_type=self.OP_TYPE,
                status="applied",
                drift_summary=None,
                backup_path=None,
                error=None,
            )

        # action == "overwrite"
        data = decision["data"]
        assert data is not None  # overwrite implies file existed and was parsed

        # Backup the original file before overwriting.
        ark_dir = project_root / ".ark"
        backups_dir = ark_dir / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        bak = backup_path(backups_dir, mcp_file)
        bak.write_bytes(mcp_file.read_bytes())

        _set_dot_path(data, key, managed_entry)
        self._write_mcp_json(mcp_file, data)

        return ApplyResult(
            op_id=op_id,
            op_type=self.OP_TYPE,
            status="drifted_overwritten",
            drift_summary=decision["drift_summary"],
            backup_path=bak,
            error=None,
        )

    def _dry_run_impl(self, project_root: Path, args: dict) -> DryRunReport:
        op_id: str = args.get("id", "ensure_mcp_server")
        decision = self._decide(project_root, args)
        action = decision["action"]

        if action == "malformed":
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=True,
                drift_summary=None,
            )

        if action == "clobber_error":
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=True,
                drift_summary=None,
            )

        if action == "skip":
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=False,
                would_skip_idempotent=True,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        if action == "create":
            return DryRunReport(
                op_id=op_id,
                op_type=self.OP_TYPE,
                would_apply=True,
                would_skip_idempotent=False,
                would_overwrite_drift=False,
                would_fail_precondition=False,
                drift_summary=None,
            )

        # action == "overwrite"
        return DryRunReport(
            op_id=op_id,
            op_type=self.OP_TYPE,
            would_apply=False,
            would_skip_idempotent=False,
            would_overwrite_drift=True,
            would_fail_precondition=False,
            drift_summary=decision["drift_summary"],
        )

    def _detect_drift_impl(self, project_root: Path, args: dict) -> DriftReport:
        key: str = args["key"]
        decision = self._decide(project_root, args)
        action = decision["action"]

        if action in ("create", "malformed", "clobber_error"):
            # No ark-managed entry exists yet (or file is unreadable) — not drift.
            return DriftReport(
                has_drift=False,
                drift_summary=None,
                drifted_regions=[],
            )

        if action == "skip":
            return DriftReport(
                has_drift=False,
                drift_summary=None,
                drifted_regions=[],
            )

        # action == "overwrite" — ark-managed entry content differs.
        return DriftReport(
            has_drift=True,
            drift_summary=decision["drift_summary"],
            drifted_regions=[key],
        )
