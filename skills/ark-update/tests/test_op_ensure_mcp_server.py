"""Unit tests for ops/ensure_mcp_server.py — 9 required cases.

Test matrix (from ralplan Tier-1 table):
  1. test_apply_creates_mcp_json_when_missing
  2. test_apply_merges_into_existing
  3. test_apply_replaces_ark_managed_entry
  4. test_apply_idempotent_when_matching
  5. test_apply_preserves_other_user_servers
  6. test_apply_refuses_malformed_mcp_json
  7. test_apply_refuses_clobber_non_ark_key     (codex P2-5)
  8. test_dry_run_matches_apply                 (codex P2-5)
  9. test_path_traversal_refusal               (codex P1-1)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path shim — mirror what migrate.py does so bare imports resolve
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops.ensure_mcp_server import EnsureMcpServer, McpClobberError  # noqa: E402
from paths import PathTraversalError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _op() -> EnsureMcpServer:
    return EnsureMcpServer()


def _write_mcp(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_mcp(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_args(tmp_path: Path, *, extra: dict | None = None) -> dict:
    """Minimal valid args for the op."""
    args = {
        "id": "tasknotes-mcp",
        "key": "mcpServers.tasknotes-mcp",
        "entry": {"type": "http", "url": "http://localhost:3000/mcp"},
    }
    if extra:
        args.update(extra)
    return args


# ---------------------------------------------------------------------------
# Case 1: create .mcp.json when missing
# ---------------------------------------------------------------------------

def test_apply_creates_mcp_json_when_missing(tmp_path: Path) -> None:
    op = _op()
    args = _base_args(tmp_path)
    result = op.apply(tmp_path, args)

    assert result["status"] == "applied"
    assert result["backup_path"] is None
    assert result["error"] is None

    mcp_file = tmp_path / ".mcp.json"
    assert mcp_file.exists()

    data = _read_mcp(mcp_file)
    entry = data["mcpServers"]["tasknotes-mcp"]
    assert entry["type"] == "http"
    assert entry["url"] == "http://localhost:3000/mcp"
    assert entry["_ark_managed"] is True

    # detect_drift: not yet drifted — entry was just created correctly.
    drift = op.detect_drift(tmp_path, args)
    assert drift["has_drift"] is False
    assert drift["drift_summary"] is None
    assert isinstance(drift["drifted_regions"], list)
    assert drift["drifted_regions"] == []


# ---------------------------------------------------------------------------
# Case 2: merge new entry into existing .mcp.json (user servers present)
# ---------------------------------------------------------------------------

def test_apply_merges_into_existing(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    existing = {
        "mcpServers": {
            "user-server-a": {"type": "stdio", "command": "myserver"}
        }
    }
    _write_mcp(mcp_file, existing)

    op = _op()
    args = _base_args(tmp_path)
    result = op.apply(tmp_path, args)

    assert result["status"] == "applied"

    data = _read_mcp(mcp_file)
    # User server must still be present and byte-identical.
    assert data["mcpServers"]["user-server-a"] == {"type": "stdio", "command": "myserver"}
    # New managed entry added.
    assert data["mcpServers"]["tasknotes-mcp"]["_ark_managed"] is True
    assert data["mcpServers"]["tasknotes-mcp"]["type"] == "http"

    # detect_drift shape validation.
    drift = op.detect_drift(tmp_path, args)
    assert drift["has_drift"] is False
    assert drift["drift_summary"] is None
    assert isinstance(drift["drifted_regions"], list)


# ---------------------------------------------------------------------------
# Case 3: replace ark-managed entry that differs; backup byte-equal to original
# ---------------------------------------------------------------------------

def test_apply_replaces_ark_managed_entry(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    old_entry = {
        "type": "http",
        "url": "http://localhost:9999/mcp",  # stale URL
        "_ark_managed": True,
    }
    _write_mcp(mcp_file, {"mcpServers": {"tasknotes-mcp": old_entry}})

    # Capture pre-overwrite bytes for byte-equality check (codex P1-1 mitigation 1.1).
    pre_overwrite_bytes = mcp_file.read_bytes()

    # Bootstrap .ark/backups so backup_path resolves correctly.
    (tmp_path / ".ark" / "backups").mkdir(parents=True, exist_ok=True)

    op = _op()
    args = _base_args(tmp_path)
    result = op.apply(tmp_path, args)

    assert result["status"] == "drifted_overwritten"
    assert result["drift_summary"] is not None
    assert isinstance(result["drift_summary"], str)
    bak: Path = result["backup_path"]
    assert bak is not None
    assert bak.exists()
    # Backup must be byte-equal to pre-overwrite content.
    assert bak.read_bytes() == pre_overwrite_bytes

    # New content updated.
    data = _read_mcp(mcp_file)
    assert data["mcpServers"]["tasknotes-mcp"]["url"] == "http://localhost:3000/mcp"
    assert data["mcpServers"]["tasknotes-mcp"]["_ark_managed"] is True

    # detect_drift before apply would have reported drift.
    # After apply, running detect_drift again should show no drift.
    drift_after = op.detect_drift(tmp_path, args)
    assert drift_after["has_drift"] is False
    assert drift_after["drift_summary"] is None
    assert isinstance(drift_after["drifted_regions"], list)


# ---------------------------------------------------------------------------
# Case 4: idempotent when matching
# ---------------------------------------------------------------------------

def test_apply_idempotent_when_matching(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    matching_entry = {
        "type": "http",
        "url": "http://localhost:3000/mcp",
        "_ark_managed": True,
    }
    _write_mcp(mcp_file, {"mcpServers": {"tasknotes-mcp": matching_entry}})
    mtime_before = mcp_file.stat().st_mtime

    op = _op()
    args = _base_args(tmp_path)
    result = op.apply(tmp_path, args)

    assert result["status"] == "skipped_idempotent"
    assert result["backup_path"] is None
    assert result["error"] is None
    # File must not have been rewritten.
    assert mcp_file.stat().st_mtime == mtime_before

    # detect_drift: no drift.
    drift = op.detect_drift(tmp_path, args)
    assert drift["has_drift"] is False
    assert drift["drift_summary"] is None
    assert isinstance(drift["drifted_regions"], list)
    assert drift["drifted_regions"] == []


# ---------------------------------------------------------------------------
# Case 5: preserve other user servers — diff excluding managed key is zero
# ---------------------------------------------------------------------------

def test_apply_preserves_other_user_servers(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    existing = {
        "mcpServers": {
            "user-server-a": {"type": "stdio", "command": "alpha"},
            "user-server-b": {"type": "stdio", "command": "beta"},
            "user-server-c": {"type": "sse", "url": "http://example.com/sse"},
        }
    }
    _write_mcp(mcp_file, existing)

    op = _op()
    args = _base_args(tmp_path)
    result = op.apply(tmp_path, args)

    assert result["status"] == "applied"

    data = _read_mcp(mcp_file)

    # All user servers byte-identical in the result.
    for key in ("user-server-a", "user-server-b", "user-server-c"):
        assert data["mcpServers"][key] == existing["mcpServers"][key], (
            f"User server '{key}' was modified — must not be touched."
        )

    # Managed entry present.
    assert "_ark_managed" in data["mcpServers"]["tasknotes-mcp"]

    # detect_drift shape.
    drift = op.detect_drift(tmp_path, args)
    assert isinstance(drift["has_drift"], bool)
    assert isinstance(drift["drifted_regions"], list)


# ---------------------------------------------------------------------------
# Case 6: refuse malformed .mcp.json
# ---------------------------------------------------------------------------

def test_apply_refuses_malformed_mcp_json(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    mcp_file.write_text("{this is not valid json", encoding="utf-8")

    op = _op()
    args = _base_args(tmp_path)

    with pytest.raises(ValueError, match="Malformed JSON"):
        op.apply(tmp_path, args)

    # dry_run: would_fail_precondition = True, no raises.
    report = op.dry_run(tmp_path, args)
    assert report["would_fail_precondition"] is True
    assert report["would_apply"] is False


# ---------------------------------------------------------------------------
# Case 7: refuse clobber of non-ark key (codex P2-5)
# ---------------------------------------------------------------------------

def test_apply_refuses_clobber_non_ark_key(tmp_path: Path) -> None:
    mcp_file = tmp_path / ".mcp.json"
    # Entry at key exists but has NO _ark_managed marker — user-authored.
    user_entry = {"type": "stdio", "command": "user-server-binary"}
    _write_mcp(mcp_file, {"mcpServers": {"tasknotes-mcp": user_entry}})

    op = _op()
    args = _base_args(tmp_path)

    with pytest.raises(McpClobberError):
        op.apply(tmp_path, args)

    # dry_run also surfaces the refusal without raising.
    report = op.dry_run(tmp_path, args)
    assert report["would_fail_precondition"] is True
    assert report["would_apply"] is False
    assert report["would_overwrite_drift"] is False

    # File must be byte-identical (no write occurred).
    data = _read_mcp(mcp_file)
    assert data["mcpServers"]["tasknotes-mcp"] == user_entry


# ---------------------------------------------------------------------------
# Case 8: dry_run decisions match apply (scenarios 1–5)
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path: Path) -> None:
    op = _op()

    # Scenario 1: file missing → dry_run says would_apply, apply returns "applied".
    s1_root = tmp_path / "s1"
    s1_root.mkdir()
    args = _base_args(s1_root)
    dry = op.dry_run(s1_root, args)
    assert dry["would_apply"] is True
    assert dry["would_skip_idempotent"] is False
    assert dry["would_overwrite_drift"] is False
    assert dry["would_fail_precondition"] is False
    # Apply must produce "applied".
    result = op.apply(s1_root, args)
    assert result["status"] == "applied"

    # Scenario 2: merge into existing → dry_run says would_apply.
    s2_root = tmp_path / "s2"
    s2_root.mkdir()
    _write_mcp(
        s2_root / ".mcp.json",
        {"mcpServers": {"other": {"type": "stdio", "command": "x"}}},
    )
    args2 = _base_args(s2_root)
    dry2 = op.dry_run(s2_root, args2)
    assert dry2["would_apply"] is True
    result2 = op.apply(s2_root, args2)
    assert result2["status"] == "applied"

    # Scenario 3: drift → dry_run says would_overwrite_drift.
    s3_root = tmp_path / "s3"
    s3_root.mkdir()
    (s3_root / ".ark" / "backups").mkdir(parents=True)
    _write_mcp(
        s3_root / ".mcp.json",
        {"mcpServers": {"tasknotes-mcp": {"type": "http", "url": "OLD", "_ark_managed": True}}},
    )
    args3 = _base_args(s3_root)
    dry3 = op.dry_run(s3_root, args3)
    assert dry3["would_overwrite_drift"] is True
    assert dry3["drift_summary"] is not None
    result3 = op.apply(s3_root, args3)
    assert result3["status"] == "drifted_overwritten"

    # Scenario 4: idempotent → dry_run says would_skip_idempotent.
    s4_root = tmp_path / "s4"
    s4_root.mkdir()
    _write_mcp(
        s4_root / ".mcp.json",
        {"mcpServers": {"tasknotes-mcp": {
            "type": "http", "url": "http://localhost:3000/mcp", "_ark_managed": True
        }}},
    )
    args4 = _base_args(s4_root)
    dry4 = op.dry_run(s4_root, args4)
    assert dry4["would_skip_idempotent"] is True
    result4 = op.apply(s4_root, args4)
    assert result4["status"] == "skipped_idempotent"

    # Scenario 5: preserve user servers — dry_run says would_apply (key absent).
    s5_root = tmp_path / "s5"
    s5_root.mkdir()
    _write_mcp(
        s5_root / ".mcp.json",
        {"mcpServers": {"user-only": {"type": "stdio", "command": "bin"}}},
    )
    args5 = _base_args(s5_root)
    dry5 = op.dry_run(s5_root, args5)
    assert dry5["would_apply"] is True
    result5 = op.apply(s5_root, args5)
    assert result5["status"] == "applied"


# ---------------------------------------------------------------------------
# Case 9: path traversal refusal (codex P1-1)
# ---------------------------------------------------------------------------

def test_path_traversal_refusal(tmp_path: Path) -> None:
    op = _op()
    # Traversal via ".." in the file arg — base class safe_resolve must catch this.
    args = _base_args(
        tmp_path,
        extra={"file": "../../../etc/shadow"},
    )
    with pytest.raises(PathTraversalError):
        op.apply(tmp_path, args)

    with pytest.raises(PathTraversalError):
        op.dry_run(tmp_path, args)

    with pytest.raises(PathTraversalError):
        op.detect_drift(tmp_path, args)


# ---------------------------------------------------------------------------
# detect_drift return-shape assertions (Step 3 acceptance criterion 3)
# ---------------------------------------------------------------------------

def test_detect_drift_shape_when_no_drift(tmp_path: Path) -> None:
    """drift_summary is None and drifted_regions is [] when has_drift is False."""
    mcp_file = tmp_path / ".mcp.json"
    _write_mcp(
        mcp_file,
        {"mcpServers": {"tasknotes-mcp": {
            "type": "http", "url": "http://localhost:3000/mcp", "_ark_managed": True,
        }}},
    )
    op = _op()
    args = _base_args(tmp_path)
    drift = op.detect_drift(tmp_path, args)

    assert drift["has_drift"] is False
    assert drift["drift_summary"] is None
    assert drift["drifted_regions"] == []


def test_detect_drift_shape_when_drifted(tmp_path: Path) -> None:
    """drift_summary is a non-empty string and drifted_regions is non-empty when has_drift is True."""
    mcp_file = tmp_path / ".mcp.json"
    _write_mcp(
        mcp_file,
        {"mcpServers": {"tasknotes-mcp": {
            "type": "http", "url": "http://STALE/mcp", "_ark_managed": True,
        }}},
    )
    op = _op()
    args = _base_args(tmp_path)
    drift = op.detect_drift(tmp_path, args)

    assert drift["has_drift"] is True
    assert isinstance(drift["drift_summary"], str)
    assert len(drift["drift_summary"]) > 0
    assert isinstance(drift["drifted_regions"], list)
    assert len(drift["drifted_regions"]) > 0
