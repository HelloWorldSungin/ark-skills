"""Tests for skills/ark-update/scripts/ops/ensure_gitignore_entry.py.

7 cases (Tier-1 matrix, post codex P1-1 + P2-5 fixes):
  1. test_apply_appends_when_absent
  2. test_apply_idempotent_when_present
  3. test_apply_creates_gitignore_when_missing
  4. test_apply_normalizes_trailing_newline
  5. test_detect_drift_always_false
  6. test_dry_run_matches_apply
  7. test_path_traversal_refusal
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path shim — same pattern as all other test files in this suite
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ops import OP_REGISTRY  # noqa: E402
from ops.ensure_gitignore_entry import EnsureGitignoreEntry  # noqa: E402
from paths import PathTraversalError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENTRY = ".ark-workflow/"

_ARGS_BASE: dict = {"id": "test-gitignore", "entry": ENTRY}


def _op() -> EnsureGitignoreEntry:
    return EnsureGitignoreEntry()


# ---------------------------------------------------------------------------
# 1. test_apply_appends_when_absent
# ---------------------------------------------------------------------------

def test_apply_appends_when_absent(tmp_path):
    """.gitignore exists but does not contain the entry; apply adds it."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n.DS_Store\n", encoding="utf-8")

    result = _op().apply(tmp_path, _ARGS_BASE)

    assert result["status"] == "applied"
    assert result["error"] is None
    final = gitignore.read_text(encoding="utf-8")
    assert ENTRY in final
    # File must end with a newline and the last line must be the entry.
    assert final.endswith(ENTRY + "\n")


# ---------------------------------------------------------------------------
# 2. test_apply_idempotent_when_present
# ---------------------------------------------------------------------------

def test_apply_idempotent_when_present(tmp_path):
    """.gitignore already contains the entry; apply is a no-op."""
    content = f"node_modules/\n{ENTRY}\n.DS_Store\n"
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(content, encoding="utf-8")
    before_bytes = gitignore.read_bytes()

    result = _op().apply(tmp_path, _ARGS_BASE)

    assert result["status"] == "skipped_idempotent"
    # File bytes must be identical after no-op.
    assert gitignore.read_bytes() == before_bytes


# ---------------------------------------------------------------------------
# 3. test_apply_creates_gitignore_when_missing
# ---------------------------------------------------------------------------

def test_apply_creates_gitignore_when_missing(tmp_path):
    """.gitignore does not exist; apply creates it with just the entry."""
    gitignore = tmp_path / ".gitignore"
    assert not gitignore.exists()

    result = _op().apply(tmp_path, _ARGS_BASE)

    assert result["status"] == "applied"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert content == ENTRY + "\n"


# ---------------------------------------------------------------------------
# 4. test_apply_normalizes_trailing_newline
# ---------------------------------------------------------------------------

def test_apply_normalizes_trailing_newline(tmp_path):
    """.gitignore exists without a trailing newline; apply adds entry correctly."""
    gitignore = tmp_path / ".gitignore"
    # Deliberately omit trailing newline.
    gitignore.write_text("node_modules/", encoding="utf-8")

    result = _op().apply(tmp_path, _ARGS_BASE)

    assert result["status"] == "applied"
    content = gitignore.read_text(encoding="utf-8")
    # Both lines present, each on its own line.
    lines = content.splitlines()
    assert "node_modules/" in lines
    assert ENTRY in lines
    # Ends with newline (valid file).
    assert content.endswith("\n")


# ---------------------------------------------------------------------------
# 5. test_detect_drift_always_false
# ---------------------------------------------------------------------------

def test_detect_drift_always_false(tmp_path):
    """detect_drift always returns has_drift=False regardless of entry presence."""
    # Case A: entry missing.
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("node_modules/\n", encoding="utf-8")

    report = _op().detect_drift(tmp_path, _ARGS_BASE)

    assert report["has_drift"] is False
    assert report["drift_summary"] is None
    assert isinstance(report["drifted_regions"], list)
    assert report["drifted_regions"] == []

    # Case B: even when entry is also present, still no drift.
    gitignore.write_text(f"node_modules/\n{ENTRY}\n", encoding="utf-8")
    report2 = _op().detect_drift(tmp_path, _ARGS_BASE)
    assert report2["has_drift"] is False
    assert report2["drift_summary"] is None
    assert report2["drifted_regions"] == []

    # Case C: .gitignore missing entirely.
    gitignore.unlink()
    report3 = _op().detect_drift(tmp_path, _ARGS_BASE)
    assert report3["has_drift"] is False
    assert report3["drift_summary"] is None
    assert report3["drifted_regions"] == []


# ---------------------------------------------------------------------------
# 6. test_dry_run_matches_apply
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path):
    """dry_run returns the same decision flags that apply would act on, without writing."""

    # Scenario 1: entry absent, file exists.
    g = tmp_path / ".gitignore"
    g.write_text("node_modules/\n", encoding="utf-8")
    before = g.read_bytes()

    dry = _op().dry_run(tmp_path, _ARGS_BASE)
    assert dry["would_apply"] is True
    assert dry["would_skip_idempotent"] is False
    # No side effect from dry_run.
    assert g.read_bytes() == before

    # Now apply and verify it matches what dry_run predicted.
    result = _op().apply(tmp_path, _ARGS_BASE)
    assert result["status"] == "applied"  # matches would_apply=True

    # Scenario 2: entry present (re-run on same file).
    dry2 = _op().dry_run(tmp_path, _ARGS_BASE)
    assert dry2["would_apply"] is False
    assert dry2["would_skip_idempotent"] is True

    result2 = _op().apply(tmp_path, _ARGS_BASE)
    assert result2["status"] == "skipped_idempotent"  # matches would_skip_idempotent=True

    # Scenario 3: file missing.
    missing_root = tmp_path / "fresh"
    missing_root.mkdir()
    dry3 = _op().dry_run(missing_root, _ARGS_BASE)
    assert dry3["would_apply"] is True
    assert dry3["would_skip_idempotent"] is False
    # dry_run must not create the file.
    assert not (missing_root / ".gitignore").exists()

    # Scenario 4: trailing newline normalization — dry_run predicts apply.
    norm_root = tmp_path / "norm"
    norm_root.mkdir()
    (norm_root / ".gitignore").write_text("node_modules/", encoding="utf-8")
    dry4 = _op().dry_run(norm_root, _ARGS_BASE)
    assert dry4["would_apply"] is True

    result4 = _op().apply(norm_root, _ARGS_BASE)
    assert result4["status"] == "applied"


# ---------------------------------------------------------------------------
# 7. test_path_traversal_refusal
# ---------------------------------------------------------------------------

def test_path_traversal_refusal(tmp_path):
    """file: override with ../ traversal raises PathTraversalError via base class."""
    # The op declares PATH_ARGS = ("file",) so base class runs safe_resolve on "file".
    traversal_args = {"id": "test-gitignore", "entry": ENTRY, "file": "../etc/passwd"}

    with pytest.raises(PathTraversalError):
        _op().apply(tmp_path, traversal_args)

    # Also assert dry_run refuses traversal (no writes on error path).
    with pytest.raises(PathTraversalError):
        _op().dry_run(tmp_path, traversal_args)


# ---------------------------------------------------------------------------
# Registry smoke test
# ---------------------------------------------------------------------------

def test_op_registered():
    """EnsureGitignoreEntry is registered in OP_REGISTRY under the correct key."""
    assert "ensure_gitignore_entry" in OP_REGISTRY
    assert OP_REGISTRY["ensure_gitignore_entry"] is EnsureGitignoreEntry
