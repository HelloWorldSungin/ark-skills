"""Tests for skills/ark-update/scripts/state.py.

Covers:
  - Log append / parse round-trip
  - Clean-run invariant (ops_ran=0 AND result="clean" → no write, no pointer rewrite)
  - Max-semver installed_version (never timestamp-sorted; clock-skew case)
  - Bootstrap from missing .ark/ → returns "0.0.0"
  - Malformed JSONL entry → raise ValueError
  - Lockfile: acquire, double-acquire same PID, stale-PID cleanup
  - Backup path computation: deterministic UTC format
"""
import json
import os
import sys
import time
from datetime import timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from state import (
    LogEntry,
    acquire_lock,
    append_log,
    backup_path,
    bootstrap,
    computed_installed_version,
    maybe_append_log_and_pointer,
    read_log,
    release_lock,
    utc_now_iso,
    write_pointer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(version, phase="destructive", result="clean", ops_ran=1):
    return {
        "version": version,
        "applied_at": utc_now_iso(),
        "ops_ran": ops_ran,
        "ops_skipped": 0,
        "failed_ops": [],
        "result": result,
        "phase": phase,
    }


# ---------------------------------------------------------------------------
# Log append / parse round-trip
# ---------------------------------------------------------------------------

def test_append_and_read_round_trip(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    entry = _make_entry("1.11.0")
    append_log(log, entry)

    entries = read_log(log)
    assert len(entries) == 1
    assert entries[0].version == "1.11.0"
    assert entries[0].phase == "destructive"
    assert entries[0].result == "clean"
    assert entries[0].ops_ran == 1
    assert entries[0].failed_ops == []


def test_multiple_entries_round_trip(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    for v in ["1.11.0", "1.12.0", "1.13.0"]:
        append_log(log, _make_entry(v))

    entries = read_log(log)
    assert len(entries) == 3
    assert [e.version for e in entries] == ["1.11.0", "1.12.0", "1.13.0"]


def test_read_log_empty_file_returns_empty_list(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    log.touch()
    assert read_log(log) == []


def test_read_log_missing_file_returns_empty_list(tmp_path):
    log = tmp_path / "nonexistent.jsonl"
    assert read_log(log) == []


def test_dedup_by_version_and_phase_last_wins(tmp_path):
    """Duplicate (version, phase) pairs: last-seen entry wins."""
    log = tmp_path / "migrations-applied.jsonl"
    entry1 = _make_entry("1.11.0", phase="destructive", result="clean")
    entry2 = {**_make_entry("1.11.0", phase="destructive"), "result": "partial"}
    append_log(log, entry1)
    append_log(log, entry2)

    entries = read_log(log)
    assert len(entries) == 1
    assert entries[0].result == "partial"


# ---------------------------------------------------------------------------
# Clean-run invariant (codex P1-2)
# ---------------------------------------------------------------------------

def test_clean_run_invariant_skips_log_and_pointer(tmp_path):
    """ops_ran=0 AND result='clean' must not write log or pointer."""
    log = tmp_path / "migrations-applied.jsonl"
    pointer = tmp_path / "plugin-version"

    entry = _make_entry("1.13.0", ops_ran=0)
    entry["result"] = "clean"

    wrote = maybe_append_log_and_pointer(log, pointer, entry, "1.13.0")

    assert wrote is False
    assert not log.exists(), "log must not be created on a clean run"
    assert not pointer.exists(), "pointer must not be written on a clean run"


def test_clean_run_invariant_preserves_existing_log(tmp_path):
    """Existing log is byte-identical before and after a clean run."""
    log = tmp_path / "migrations-applied.jsonl"
    pointer = tmp_path / "plugin-version"

    # Write an initial entry.
    initial_entry = _make_entry("1.12.0", ops_ran=1)
    append_log(log, initial_entry)
    write_pointer(pointer, "1.12.0")

    before_log = log.read_bytes()
    before_pointer = pointer.read_bytes()

    # Now attempt a clean run.
    clean_entry = _make_entry("1.13.0", ops_ran=0)
    clean_entry["result"] = "clean"
    maybe_append_log_and_pointer(log, pointer, clean_entry, "1.13.0")

    assert log.read_bytes() == before_log
    assert pointer.read_bytes() == before_pointer


def test_non_clean_run_does_write(tmp_path):
    """ops_ran=1 allows log append and pointer rewrite."""
    log = tmp_path / "migrations-applied.jsonl"
    pointer = tmp_path / "plugin-version"

    entry = _make_entry("1.13.0", ops_ran=1)
    wrote = maybe_append_log_and_pointer(log, pointer, entry, "1.13.0")

    assert wrote is True
    assert log.exists()
    assert pointer.read_text().strip() == "1.13.0"


def test_partial_result_does_write(tmp_path):
    """result='partial' with ops_ran=0 still writes (not a clean run)."""
    log = tmp_path / "migrations-applied.jsonl"
    pointer = tmp_path / "plugin-version"

    entry = _make_entry("1.13.0", ops_ran=0)
    entry["result"] = "partial"
    wrote = maybe_append_log_and_pointer(log, pointer, entry, "1.13.0")

    assert wrote is True


# ---------------------------------------------------------------------------
# Max-semver installed_version (codex P2-6)
# ---------------------------------------------------------------------------

def test_installed_version_max_semver_not_timestamp_order(tmp_path):
    """installed_version is the max semver, regardless of entry order or timestamps."""
    entries = [
        LogEntry.from_dict(_make_entry("1.11.0")),
        LogEntry.from_dict(_make_entry("1.13.0")),
        LogEntry.from_dict(_make_entry("1.12.0")),
    ]
    assert computed_installed_version(entries) == "1.13.0"


def test_installed_version_clock_skew_case(tmp_path):
    """Clock skew: older semver has a NEWER applied_at timestamp — still returns max semver."""
    # 1.11.0 has a future timestamp (clock skew simulation)
    far_future = "2099-01-01T00:00:00Z"
    past = "2026-01-01T00:00:00Z"

    raw_old = _make_entry("1.11.0")
    raw_old["applied_at"] = far_future
    raw_new = _make_entry("1.13.0")
    raw_new["applied_at"] = past

    entries = [LogEntry.from_dict(raw_old), LogEntry.from_dict(raw_new)]
    # Despite 1.11.0 having a newer timestamp, 1.13.0 must win.
    assert computed_installed_version(entries) == "1.13.0"


def test_installed_version_only_counts_destructive_phase(tmp_path):
    """Phase-2 (convergence) entries do not count toward installed_version."""
    entries = [
        LogEntry.from_dict(_make_entry("1.13.0", phase="convergence")),
    ]
    assert computed_installed_version(entries) == "0.0.0"


def test_installed_version_only_counts_clean_results(tmp_path):
    """Partial entries do not count toward installed_version."""
    raw = _make_entry("1.13.0", phase="destructive")
    raw["result"] = "partial"
    entries = [LogEntry.from_dict(raw)]
    assert computed_installed_version(entries) == "0.0.0"


def test_installed_version_empty_entries_returns_zero(tmp_path):
    assert computed_installed_version([]) == "0.0.0"


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def test_bootstrap_creates_ark_dir(tmp_path):
    ark = tmp_path / ".ark"
    result = bootstrap(ark)
    assert result == "0.0.0"
    assert ark.is_dir()
    assert (ark / "backups").is_dir()


def test_bootstrap_missing_log_returns_zero_zero_zero(tmp_path):
    ark = tmp_path / ".ark"
    ark.mkdir()
    result = bootstrap(ark)
    assert result == "0.0.0"


def test_bootstrap_with_existing_log_returns_installed_version(tmp_path):
    ark = tmp_path / ".ark"
    ark.mkdir()
    (ark / "backups").mkdir()
    log = ark / "migrations-applied.jsonl"
    append_log(log, _make_entry("1.12.0", phase="destructive"))
    result = bootstrap(ark)
    assert result == "1.12.0"


# ---------------------------------------------------------------------------
# Malformed JSONL
# ---------------------------------------------------------------------------

def test_malformed_json_line_raises(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    # NOT_JSON is on line 1 so json.loads raises and we get the "Malformed JSON" message.
    log.write_text('NOT_JSON\n{"version": "1.11.0", "applied_at": "x"}\n')
    with pytest.raises(ValueError, match="Malformed JSON"):
        read_log(log)


def test_missing_required_field_raises(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    # Missing 'phase' field.
    bad = {"version": "1.11.0", "applied_at": "x", "ops_ran": 1,
           "ops_skipped": 0, "failed_ops": [], "result": "clean"}
    log.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="missing required fields"):
        read_log(log)


def test_failed_ops_not_list_raises(tmp_path):
    log = tmp_path / "migrations-applied.jsonl"
    bad = _make_entry("1.11.0")
    bad["failed_ops"] = "not-a-list"
    log.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="failed_ops"):
        read_log(log)


# ---------------------------------------------------------------------------
# Lockfile
# ---------------------------------------------------------------------------

def test_acquire_creates_lock_file(tmp_path):
    lock = tmp_path / "lock"
    acquire_lock(lock)
    assert lock.exists()
    recorded = int(lock.read_text().strip())
    assert recorded == os.getpid()
    release_lock(lock)


def test_double_acquire_same_pid_raises(tmp_path):
    """Acquiring a lock we already hold raises RuntimeError (same process)."""
    lock = tmp_path / "lock"
    acquire_lock(lock)
    with pytest.raises(RuntimeError, match="already running"):
        acquire_lock(lock)
    release_lock(lock)


def test_stale_pid_lock_is_reclaimed(tmp_path):
    """A lock file with a dead PID is silently reclaimed."""
    lock = tmp_path / "lock"
    # Write a PID that is guaranteed not to exist.
    # PID 1 is init/systemd and won't be us; use a very large number.
    # Use PID 999999 which is almost certainly not running.
    dead_pid = 999999
    # Verify it's actually dead before using it in the test.
    try:
        os.kill(dead_pid, 0)
        pytest.skip(f"PID {dead_pid} unexpectedly exists on this system")
    except ProcessLookupError:
        pass
    except PermissionError:
        pytest.skip(f"PID {dead_pid} exists (permission denied)")

    lock.write_text(str(dead_pid) + "\n")
    acquire_lock(lock)  # Should not raise.
    assert int(lock.read_text().strip()) == os.getpid()
    release_lock(lock)


def test_release_lock_removes_file(tmp_path):
    lock = tmp_path / "lock"
    acquire_lock(lock)
    assert lock.exists()
    release_lock(lock)
    assert not lock.exists()


def test_release_lock_noop_if_not_held(tmp_path):
    """release_lock does not raise if lock does not exist."""
    lock = tmp_path / "lock"
    release_lock(lock)  # Should not raise.


# ---------------------------------------------------------------------------
# Backup path computation
# ---------------------------------------------------------------------------

def test_backup_path_format(tmp_path):
    """backup_path returns a path matching <basename>.<UTC-ts>.bak format."""
    backups = tmp_path / "backups"
    backups.mkdir()
    target = tmp_path / "CLAUDE.md"

    result = backup_path(backups, target)

    # Should be under backups dir.
    assert result.parent == backups
    # Should start with the target's basename.
    assert result.name.startswith("CLAUDE.md.")
    # Should end with .bak.
    assert result.name.endswith(".bak")
    # Timestamp part should match YYYYmmddTHHMMSSZ pattern.
    import re
    ts_part = result.name[len("CLAUDE.md.") : -len(".bak")]
    assert re.fullmatch(r"\d{8}T\d{6}Z", ts_part), f"Unexpected timestamp: {ts_part!r}"


def test_backup_path_uses_utc(tmp_path):
    """backup_path timestamp suffix ends with 'Z' (UTC marker)."""
    backups = tmp_path / "backups"
    backups.mkdir()
    result = backup_path(backups, Path("some_file.md"))
    assert "Z.bak" in result.name


def test_backup_path_different_files_differ(tmp_path):
    """Different source files produce different backup basenames."""
    backups = tmp_path / "backups"
    backups.mkdir()
    p1 = backup_path(backups, Path("a.md"))
    p2 = backup_path(backups, Path("b.md"))
    assert p1.name.startswith("a.md.")
    assert p2.name.startswith("b.md.")
