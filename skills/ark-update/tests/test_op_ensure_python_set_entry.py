"""Tests for skills/ark-update/scripts/ops/ensure_python_set_entry.py.

9 cases (Tier-1 matrix):
  1. test_apply_adds_entry_when_missing
  2. test_apply_idempotent_when_already_present
  3. test_apply_skips_when_file_missing
  4. test_apply_skips_when_set_name_absent
  5. test_apply_preserves_other_content
  6. test_detect_drift
  7. test_dry_run_matches_apply
  8. test_op_registered
  9. test_path_traversal_refusal
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
from ops.ensure_python_set_entry import EnsurePythonSetEntry  # noqa: E402
from paths import PathTraversalError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SET_NAME = "EXCLUDE_DIRS"
ENTRY = "generated"

_ARGS_BASE: dict = {
    "id": "test-set-entry",
    "set_name": SET_NAME,
    "entry": ENTRY,
}

# Relative path used for the standard target — safe_resolve requires relative paths.
_REL_FILE = "vault/_meta/generate-index.py"

_INITIAL_CONTENT = 'EXCLUDE_DIRS = {"_Templates", "_meta"}\n\nprint("hello")\n'
_EXPECTED_AFTER = 'EXCLUDE_DIRS = {"_Templates", "_meta", "generated"}\n\nprint("hello")\n'


def _op() -> EnsurePythonSetEntry:
    return EnsurePythonSetEntry()


def _args(rel_file: str = _REL_FILE) -> dict:
    """Return args dict with file set to a relative path (safe_resolve compatible)."""
    return {**_ARGS_BASE, "file": rel_file}


def _make_standard_target(tmp_path: Path, content: str) -> Path:
    """Create the standard target at vault/_meta/generate-index.py under tmp_path."""
    target = tmp_path / "vault" / "_meta" / "generate-index.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# 1. test_apply_adds_entry_when_missing
# ---------------------------------------------------------------------------

def test_apply_adds_entry_when_missing(tmp_path):
    """apply inserts the entry when it is absent from the set literal."""
    target = _make_standard_target(tmp_path, _INITIAL_CONTENT)

    result = _op().apply(tmp_path, _args())

    assert result["status"] == "applied"
    assert result["error"] is None
    assert target.read_text(encoding="utf-8") == _EXPECTED_AFTER


# ---------------------------------------------------------------------------
# 2. test_apply_idempotent_when_already_present
# ---------------------------------------------------------------------------

def test_apply_idempotent_when_already_present(tmp_path):
    """apply is a no-op when the entry is already in the set."""
    target = _make_standard_target(tmp_path, _EXPECTED_AFTER)
    before_bytes = target.read_bytes()

    result = _op().apply(tmp_path, _args())

    assert result["status"] == "skipped_idempotent"
    assert target.read_bytes() == before_bytes


# ---------------------------------------------------------------------------
# 3. test_apply_skips_when_file_missing
# ---------------------------------------------------------------------------

def test_apply_skips_when_file_missing(tmp_path):
    """apply skips cleanly when the target file does not exist."""
    # tmp_path is fresh; vault/_meta/generate-index.py does not exist.
    assert not (tmp_path / _REL_FILE).exists()

    result = _op().apply(tmp_path, _args())

    assert result["status"] == "skipped_idempotent"
    assert result["drift_summary"] is not None
    assert "not found" in result["drift_summary"]
    assert not (tmp_path / _REL_FILE).exists()


# ---------------------------------------------------------------------------
# 4. test_apply_skips_when_set_name_absent
# ---------------------------------------------------------------------------

def test_apply_skips_when_set_name_absent(tmp_path):
    """apply skips cleanly when the named set assignment is not in the file."""
    content = 'OTHER_SET = {"_Templates", "_meta"}\n\nprint("hello")\n'
    target = _make_standard_target(tmp_path, content)
    before_bytes = target.read_bytes()

    result = _op().apply(tmp_path, _args())

    assert result["status"] == "skipped_idempotent"
    assert result["drift_summary"] is not None
    assert "not found" in result["drift_summary"]
    # File must be byte-for-byte untouched.
    assert target.read_bytes() == before_bytes


# ---------------------------------------------------------------------------
# 5. test_apply_preserves_other_content
# ---------------------------------------------------------------------------

def test_apply_preserves_other_content(tmp_path):
    """apply only modifies the matched set line; all other content is preserved."""
    content = (
        "# header comment\n"
        "import os\n"
        "\n"
        'EXCLUDE_DIRS = {"_Templates"}\n'
        "\n"
        "def main():\n"
        "    pass\n"
    )
    target = _make_standard_target(tmp_path, content)

    result = _op().apply(tmp_path, _args())

    assert result["status"] == "applied"
    after = target.read_text(encoding="utf-8")
    # The set line was updated.
    assert 'EXCLUDE_DIRS = {"_Templates", "generated"}' in after
    # Surrounding content is untouched.
    assert "# header comment" in after
    assert "import os" in after
    assert "def main():" in after


# ---------------------------------------------------------------------------
# 6. test_detect_drift
# ---------------------------------------------------------------------------

def test_detect_drift(tmp_path):
    """detect_drift returns has_drift=True iff entry is absent from an existing set."""
    # Case A: entry missing — drift expected.
    _make_standard_target(tmp_path, _INITIAL_CONTENT)
    report = _op().detect_drift(tmp_path, _args())

    assert report["has_drift"] is True
    assert report["drift_summary"] is not None
    assert "generated" in report["drift_summary"]
    assert SET_NAME in report["drifted_regions"]

    # Case B: entry present — no drift.
    (tmp_path / _REL_FILE).write_text(_EXPECTED_AFTER, encoding="utf-8")
    report2 = _op().detect_drift(tmp_path, _args())

    assert report2["has_drift"] is False
    assert report2["drift_summary"] is None
    assert report2["drifted_regions"] == []

    # Case C: file missing — no drift (nothing managed yet).
    (tmp_path / _REL_FILE).unlink()
    report3 = _op().detect_drift(tmp_path, _args())

    assert report3["has_drift"] is False
    assert report3["drift_summary"] is None
    assert report3["drifted_regions"] == []

    # Case D: set_name absent in file — no drift.
    (tmp_path / _REL_FILE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / _REL_FILE).write_text('OTHER_SET = {"_Templates"}\n', encoding="utf-8")
    report4 = _op().detect_drift(tmp_path, _args())

    assert report4["has_drift"] is False
    assert report4["drift_summary"] is None
    assert report4["drifted_regions"] == []


# ---------------------------------------------------------------------------
# 7. test_dry_run_matches_apply
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path):
    """dry_run returns the same decision flags apply would act on, without writing."""

    # Scenario 1: entry absent, file exists.
    target = _make_standard_target(tmp_path, _INITIAL_CONTENT)
    before = target.read_bytes()

    dry = _op().dry_run(tmp_path, _args())
    assert dry["would_apply"] is True
    assert dry["would_skip_idempotent"] is False
    # No side effect from dry_run.
    assert target.read_bytes() == before

    # Apply matches prediction.
    result = _op().apply(tmp_path, _args())
    assert result["status"] == "applied"

    # Scenario 2: entry now present.
    dry2 = _op().dry_run(tmp_path, _args())
    assert dry2["would_apply"] is False
    assert dry2["would_skip_idempotent"] is True

    result2 = _op().apply(tmp_path, _args())
    assert result2["status"] == "skipped_idempotent"

    # Scenario 3: file missing — skip predicted, no file created.
    missing_root = tmp_path / "fresh"
    missing_root.mkdir()
    dry3 = _op().dry_run(missing_root, _args())
    assert dry3["would_apply"] is False
    assert dry3["would_skip_idempotent"] is True
    assert not (missing_root / _REL_FILE).exists()

    # Scenario 4: set_name absent in file.
    other_root = tmp_path / "other_root"
    other_root.mkdir()
    (other_root / "vault" / "_meta").mkdir(parents=True)
    (other_root / _REL_FILE).write_text('OTHER = {"x"}\n', encoding="utf-8")
    dry4 = _op().dry_run(other_root, _args())
    assert dry4["would_apply"] is False
    assert dry4["would_skip_idempotent"] is True


# ---------------------------------------------------------------------------
# 8. test_op_registered
# ---------------------------------------------------------------------------

def test_op_registered():
    """EnsurePythonSetEntry is registered in OP_REGISTRY under the correct key."""
    assert "ensure_python_set_entry" in OP_REGISTRY
    assert OP_REGISTRY["ensure_python_set_entry"] is EnsurePythonSetEntry


# ---------------------------------------------------------------------------
# 9. test_path_traversal_refusal
# ---------------------------------------------------------------------------

def test_path_traversal_refusal(tmp_path):
    """file: with ../ traversal raises PathTraversalError via base class."""
    traversal_args = {**_ARGS_BASE, "file": "../etc/passwd"}

    with pytest.raises(PathTraversalError):
        _op().apply(tmp_path, traversal_args)

    with pytest.raises(PathTraversalError):
        _op().dry_run(tmp_path, traversal_args)
