"""ark-update state management: .ark/ bootstrap, migration log, pointer, lockfile, backups.

Clean-run invariant (codex P1-2):
    When ``ops_ran == 0`` AND ``result == "clean"``, a run produced no mutations.
    In this case:
      - ``append_log`` MUST NOT write anything to ``migrations-applied.jsonl``.
      - ``write_pointer`` MUST NOT rewrite ``.ark/plugin-version``.
    Use ``maybe_append_log_and_pointer(log_path, pointer_path, entry, version)``
    which enforces the invariant at the call site. Callers that bypass this
    helper and call ``append_log``/``write_pointer`` directly are responsible
    for checking the invariant themselves (engine uses ``maybe_append_log_and_pointer``
    exclusively for end-of-phase commits).

Log schema (each JSONL line):
    {
        "version": "<semver>",
        "applied_at": "<ISO-8601 UTC>",
        "ops_ran": <int>,
        "ops_skipped": <int>,
        "failed_ops": [{"op_id": "<str>", "op_type": "<str>", "error": "<str>"}, ...],
        "result": "clean" | "partial",
        "phase": "destructive" | "convergence"
    }

installed_version semantics (codex P2-6):
    ``computed_installed_version`` returns the **maximum successful semver**
    across Phase-1 (``phase == "destructive"``) log entries, deduped by
    ``(semver, phase)``.  It is NEVER derived from ``applied_at`` ordering —
    ``applied_at`` is advisory only and must not be used for version comparisons
    (clock-skew safety for parallel-worktree merges).

Advisory lockfile:
    PID-based at ``.ark/lock``. If the recorded PID is dead (no such process),
    the stale lock is removed and reclaimed. Mirrors the ``notebooklm-vault-sync.sh``
    pattern from the ark-skills plugin.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from packaging.version import Version

from paths import PathTraversalError, safe_resolve  # noqa: F401  (re-exported for callers)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    """Parsed representation of a single JSONL line in migrations-applied.jsonl."""

    version: str
    applied_at: str
    ops_ran: int
    ops_skipped: int
    failed_ops: list[dict]
    result: str   # "clean" | "partial"
    phase: str    # "destructive" | "convergence"

    # Preserve the original raw dict for round-trip fidelity.
    _raw: dict = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, d: dict, line_number: int = 0) -> "LogEntry":
        required = {"version", "applied_at", "ops_ran", "ops_skipped",
                    "failed_ops", "result", "phase"}
        missing = required - d.keys()
        if missing:
            raise ValueError(
                f"Malformed log entry at line {line_number}: "
                f"missing required fields {sorted(missing)!r}. "
                f"Run /ark-onboard repair to fix a corrupted .ark/ directory."
            )
        if not isinstance(d["failed_ops"], list):
            raise ValueError(
                f"Malformed log entry at line {line_number}: "
                f"'failed_ops' must be a list, got {type(d['failed_ops']).__name__!r}."
            )
        return cls(
            version=d["version"],
            applied_at=d["applied_at"],
            ops_ran=int(d["ops_ran"]),
            ops_skipped=int(d["ops_skipped"]),
            failed_ops=d["failed_ops"],
            result=d["result"],
            phase=d["phase"],
            _raw=d,
        )

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "applied_at": self.applied_at,
            "ops_ran": self.ops_ran,
            "ops_skipped": self.ops_skipped,
            "failed_ops": self.failed_ops,
            "result": self.result,
            "phase": self.phase,
        }


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap(ark_dir: Path) -> str:
    """Ensure ``.ark/`` exists; return the installed version string.

    Creates ``.ark/``, ``.ark/backups/``, and ``.ark/migrations-applied.jsonl``
    if they do not exist.  If the log is absent, returns ``"0.0.0"`` (cold-start
    bootstrap — no migrations applied yet).

    Parameters
    ----------
    ark_dir:
        Path to the ``.ark/`` directory (may or may not exist yet).

    Returns
    -------
    str
        The installed version as a semver string.  ``"0.0.0"`` when there is no
        prior log.
    """
    ark_dir.mkdir(parents=True, exist_ok=True)
    (ark_dir / "backups").mkdir(exist_ok=True)

    log_path = ark_dir / "migrations-applied.jsonl"
    if not log_path.exists():
        return "0.0.0"

    entries = read_log(log_path)
    return computed_installed_version(entries)


# ---------------------------------------------------------------------------
# Log read / write
# ---------------------------------------------------------------------------

def read_log(log_path: Path) -> list[LogEntry]:
    """Parse the JSONL migration log; refuse on malformed entries.

    Parameters
    ----------
    log_path:
        Path to ``migrations-applied.jsonl``.  If the file does not exist,
        returns an empty list.

    Returns
    -------
    list[LogEntry]
        Parsed entries, deduped by ``(version, phase)`` (last-seen wins).

    Raises
    ------
    ValueError
        If any line is not valid JSON or is missing required fields.  Callers
        should surface this as a refusal-to-run (see spec acceptance criteria).
    """
    if not log_path.exists():
        return []

    text = log_path.read_text(encoding="utf-8")
    entries: list[LogEntry] = []
    seen: dict[tuple[str, str], int] = {}  # (version, phase) -> index in entries

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            d = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in migration log {log_path} at line {lineno}: {exc}. "
                f"Run /ark-onboard repair to fix a corrupted .ark/ directory."
            ) from exc

        entry = LogEntry.from_dict(d, line_number=lineno)
        key = (entry.version, entry.phase)
        if key in seen:
            # Dedup: last-seen wins (later line overwrites earlier).
            entries[seen[key]] = entry
        else:
            seen[key] = len(entries)
            entries.append(entry)

    return entries


def append_log(log_path: Path, entry: dict) -> None:
    """Append a single entry dict as a JSONL line.

    This function performs a raw append without enforcing the clean-run
    invariant.  Use ``maybe_append_log_and_pointer`` for all engine end-of-phase
    commits — it enforces the invariant automatically.

    Parameters
    ----------
    log_path:
        Path to ``migrations-applied.jsonl``.  Parent directory must exist.
    entry:
        Dict matching the log schema (see module docstring).
    """
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


# ---------------------------------------------------------------------------
# installed_version computation (codex P2-6 — max semver, never timestamp-sort)
# ---------------------------------------------------------------------------

def computed_installed_version(log_entries: list[LogEntry]) -> str:
    """Return the maximum successful semver across Phase-1 (destructive) log entries.

    Deduplication by ``(semver, phase)`` is already applied by ``read_log``
    before this function is called.  This function further filters to
    ``phase == "destructive"`` and ``result == "clean"`` entries only.

    **NEVER** uses ``applied_at`` ordering — timestamps are advisory-only and
    must not influence version comparisons (parallel-worktree clock-skew safety).

    Returns ``"0.0.0"`` when there are no qualifying Phase-1 entries (bootstrap).
    """
    qualifying = [
        e for e in log_entries
        if e.phase == "destructive" and e.result == "clean"
    ]
    if not qualifying:
        return "0.0.0"

    max_entry = max(qualifying, key=lambda e: Version(e.version))
    return max_entry.version


# ---------------------------------------------------------------------------
# Pointer read / write
# ---------------------------------------------------------------------------

def write_pointer(pointer_path: Path, version: str) -> None:
    """Rewrite ``.ark/plugin-version`` with *version*.

    The pointer is a convenience cache for ``/ark-health`` and user grep.
    It is NEVER the authoritative source of truth — ``migrations-applied.jsonl``
    is.  Callers should use ``maybe_append_log_and_pointer`` to enforce the
    clean-run invariant rather than calling this directly.
    """
    pointer_path.write_text(version + "\n", encoding="utf-8")


def read_pointer(pointer_path: Path) -> Optional[str]:
    """Read ``.ark/plugin-version``; return ``None`` if absent."""
    if not pointer_path.exists():
        return None
    return pointer_path.read_text(encoding="utf-8").strip() or None


# ---------------------------------------------------------------------------
# Clean-run invariant enforcer (codex P1-2)
# ---------------------------------------------------------------------------

def maybe_append_log_and_pointer(
    log_path: Path,
    pointer_path: Path,
    entry: dict,
    version: str,
) -> bool:
    """Conditionally append the log entry and rewrite the pointer.

    Enforces the clean-run invariant: if ``entry["ops_ran"] == 0`` AND
    ``entry["result"] == "clean"``, NEITHER the log nor the pointer is
    touched.  This ensures that a fully-idempotent run (no mutations) leaves
    the ``.ark/`` state byte-identical — second runs are truly zero-write.

    Parameters
    ----------
    log_path:
        Path to ``migrations-applied.jsonl``.
    pointer_path:
        Path to ``plugin-version``.
    entry:
        The log entry dict to conditionally append.
    version:
        The semver string to write into the pointer on a non-clean-run.

    Returns
    -------
    bool
        ``True`` if the log was appended (and pointer rewritten); ``False`` if
        the clean-run invariant caused a skip.
    """
    is_clean_run = (entry.get("ops_ran", 0) == 0 and entry.get("result") == "clean")
    if is_clean_run:
        return False

    append_log(log_path, entry)
    write_pointer(pointer_path, version)
    return True


# ---------------------------------------------------------------------------
# Advisory lockfile (PID-based, stale cleanup)
# ---------------------------------------------------------------------------

def acquire_lock(lock_path: Path) -> None:
    """Acquire the advisory PID-based lockfile at *lock_path*.

    Raises
    ------
    RuntimeError
        If another live process holds the lock.

    The lock file contains the PID of the owning process as a plain integer.
    If the recorded PID is stale (process no longer exists), the lock is
    silently reclaimed — mirroring the ``notebooklm-vault-sync.sh`` stale-PID
    pattern.
    """
    if lock_path.exists():
        try:
            recorded_pid = int(lock_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            # Corrupt or empty lock file — reclaim it.
            lock_path.unlink(missing_ok=True)
        else:
            if _pid_is_alive(recorded_pid):
                raise RuntimeError(
                    f"ark-update is already running (PID {recorded_pid}). "
                    f"Lock file: {lock_path}. "
                    f"If that process is dead, remove {lock_path} manually."
                )
            # Stale PID — reclaim.
            lock_path.unlink(missing_ok=True)

    lock_path.write_text(str(os.getpid()) + "\n", encoding="utf-8")


def release_lock(lock_path: Path) -> None:
    """Release the advisory lockfile if we own it.

    Only removes the lock if it records our own PID.  If the lock file records
    a different PID (shouldn't happen in normal operation), it is left alone.
    """
    if not lock_path.exists():
        return
    try:
        recorded_pid = int(lock_path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        lock_path.unlink(missing_ok=True)
        return

    if recorded_pid == os.getpid():
        lock_path.unlink(missing_ok=True)


def _pid_is_alive(pid: int) -> bool:
    """Return True if *pid* corresponds to a running process on this host."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we can't signal it — treat as alive (safe default).
        return True


# ---------------------------------------------------------------------------
# Backup path computation
# ---------------------------------------------------------------------------

def backup_path(backups_dir: Path, target_file: Path) -> Path:
    """Compute the backup path for *target_file* under *backups_dir*.

    Returns ``.ark/backups/<basename>.<UTC-timestamp>.bak``.
    Timestamp format: ``%Y%m%dT%H%M%SZ`` (e.g. ``20260414T140300Z``).

    This function only **computes** the path; callers are responsible for
    writing the bytes (typically a ``shutil.copy2`` or ``Path.write_bytes``).
    Using a UTC timestamp avoids timezone-dependent collisions in multi-user
    or CI environments.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{target_file.name}.{ts}.bak"
    return backups_dir / filename


# ---------------------------------------------------------------------------
# Convenience: current UTC ISO-8601 timestamp for log entries
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with 'Z' suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
