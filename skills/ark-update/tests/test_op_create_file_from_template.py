"""Tests for skills/ark-update/scripts/ops/create_file_from_template.py.

7 cases (Tier-1 matrix, post codex P1-1 + P2-5 fixes):
  1. test_apply_creates_target_when_missing
  2. test_apply_idempotent_when_target_exists
  3. test_apply_creates_parent_dirs
  4. test_apply_sets_mode_when_specified
  5. test_apply_refuses_symlink_target       (codex P1-1)
  6. test_apply_refuses_missing_template
  7. test_dry_run_matches_apply              (codex P2-5)

Plus:
  test_path_traversal_refusal
  test_detect_drift_always_false
  test_op_registered
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path shim — same pattern as all other test files in this suite
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ops import OP_REGISTRY  # noqa: E402
from ops.create_file_from_template import CreateFileFromTemplate, SymlinkTargetError  # noqa: E402
from paths import PathTraversalError  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

TEMPLATE_NAME = "example-script.sh"
TEMPLATE_CONTENT = b"#!/bin/bash\necho 'hello from template'\n"


def _make_skills_root(base: Path) -> Path:
    """Create a fake skills_root with one template file.

    Layout mirrors the real repo structure so _read_template_bytes resolves:
        <skills_root>/skills/ark-update/templates/<TEMPLATE_NAME>
    """
    templates_dir = base / "skills" / "ark-update" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / TEMPLATE_NAME).write_bytes(TEMPLATE_CONTENT)
    return base


def _op() -> CreateFileFromTemplate:
    return CreateFileFromTemplate()


def _args(project_root: Path, skills_root: Path, **overrides) -> dict:
    """Build a minimal valid args dict."""
    base = {
        "id": "test-create-file",
        "target": "scripts/example-script.sh",
        "template": TEMPLATE_NAME,
        "skills_root": str(skills_root),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. test_apply_creates_target_when_missing
# ---------------------------------------------------------------------------

def test_apply_creates_target_when_missing(tmp_path):
    """Target path does not exist; apply copies template bytes and returns applied."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "scripts").mkdir()

    args = _args(project_root, skills_root)
    result = _op().apply(project_root, args)

    assert result["status"] == "applied"
    assert result["error"] is None

    target = project_root / "scripts" / "example-script.sh"
    assert target.exists()
    assert target.read_bytes() == TEMPLATE_CONTENT


# ---------------------------------------------------------------------------
# 2. test_apply_idempotent_when_target_exists
# ---------------------------------------------------------------------------

def test_apply_idempotent_when_target_exists(tmp_path):
    """Target is a regular file; apply is a no-op (never overwrites)."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    (project_root / "scripts").mkdir(parents=True)
    target = project_root / "scripts" / "example-script.sh"
    original_content = b"# user-edited content - must not be touched\n"
    target.write_bytes(original_content)

    args = _args(project_root, skills_root)
    result = _op().apply(project_root, args)

    assert result["status"] == "skipped_idempotent"
    assert result["error"] is None
    # Bytes must be byte-identical after the no-op.
    assert target.read_bytes() == original_content


# ---------------------------------------------------------------------------
# 3. test_apply_creates_parent_dirs
# ---------------------------------------------------------------------------

def test_apply_creates_parent_dirs(tmp_path):
    """Target path is in a non-existent subdirectory; apply creates parents + file."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()
    # Target nested under a directory that does not yet exist.
    args = _args(project_root, skills_root, target="deep/nested/dir/example-script.sh")

    result = _op().apply(project_root, args)

    assert result["status"] == "applied"
    target = project_root / "deep" / "nested" / "dir" / "example-script.sh"
    assert target.exists()
    assert target.read_bytes() == TEMPLATE_CONTENT


# ---------------------------------------------------------------------------
# 4. test_apply_sets_mode_when_specified
# ---------------------------------------------------------------------------

def test_apply_sets_mode_when_specified(tmp_path):
    """mode: 0o755 in args causes apply to chmod the target file."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()

    args = _args(project_root, skills_root, mode=0o755)
    result = _op().apply(project_root, args)

    assert result["status"] == "applied"
    target = project_root / "scripts" / "example-script.sh"
    actual_mode = os.stat(target).st_mode & 0o777
    assert actual_mode == 0o755


# ---------------------------------------------------------------------------
# 5. test_apply_refuses_symlink_target  (codex P1-1)
# ---------------------------------------------------------------------------

def test_apply_refuses_symlink_target(tmp_path):
    """Target path is a symlink (even to an in-root file); apply raises SymlinkTargetError.

    Assert no file was overwritten.
    """
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    (project_root / "scripts").mkdir(parents=True)

    # Create a real in-root file and a symlink pointing to it.
    real_file = project_root / "scripts" / "real-file.sh"
    real_file.write_bytes(b"# original content\n")
    symlink_target = project_root / "scripts" / "example-script.sh"
    os.symlink(real_file, symlink_target)

    assert symlink_target.is_symlink()  # sanity check
    original_real_bytes = real_file.read_bytes()

    args = _args(project_root, skills_root)

    with pytest.raises(SymlinkTargetError):
        _op().apply(project_root, args)

    # The real file behind the symlink must not have been touched.
    assert real_file.read_bytes() == original_real_bytes
    # The symlink itself must still be a symlink (not replaced by a regular file).
    assert symlink_target.is_symlink()


# ---------------------------------------------------------------------------
# 6. test_apply_refuses_missing_template
# ---------------------------------------------------------------------------

def test_apply_refuses_missing_template(tmp_path):
    """Template name that doesn't exist under skills_root/templates/ raises FileNotFoundError."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()

    args = _args(project_root, skills_root, template="nonexistent-template.sh")

    with pytest.raises(FileNotFoundError):
        _op().apply(project_root, args)

    # Target must not have been created.
    target = project_root / "scripts" / "example-script.sh"
    assert not target.exists()


# ---------------------------------------------------------------------------
# 7. test_dry_run_matches_apply  (codex P2-5)
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path):
    """dry_run decisions match apply's would-be result with no filesystem side-effects."""
    skills_root = _make_skills_root(tmp_path / "skills_root")

    # -- Scenario 1: target missing (would apply) --
    project_root_1 = tmp_path / "proj1"
    project_root_1.mkdir()
    args1 = _args(project_root_1, skills_root)

    dry1 = _op().dry_run(project_root_1, args1)
    assert dry1["would_apply"] is True
    assert dry1["would_skip_idempotent"] is False
    assert dry1["would_fail_precondition"] is False
    # dry_run must not create the file.
    target1 = project_root_1 / "scripts" / "example-script.sh"
    assert not target1.exists()

    # apply should confirm the dry_run prediction.
    result1 = _op().apply(project_root_1, args1)
    assert result1["status"] == "applied"  # matches would_apply=True

    # -- Scenario 2: target already exists (would skip) --
    project_root_2 = tmp_path / "proj2"
    (project_root_2 / "scripts").mkdir(parents=True)
    existing = project_root_2 / "scripts" / "example-script.sh"
    existing.write_bytes(b"# pre-existing\n")
    before_bytes = existing.read_bytes()

    args2 = _args(project_root_2, skills_root)
    dry2 = _op().dry_run(project_root_2, args2)
    assert dry2["would_apply"] is False
    assert dry2["would_skip_idempotent"] is True
    # dry_run must not modify the file.
    assert existing.read_bytes() == before_bytes

    result2 = _op().apply(project_root_2, args2)
    assert result2["status"] == "skipped_idempotent"  # matches would_skip_idempotent=True

    # -- Scenario 3: target missing in a deeply nested dir (would apply + mkdir) --
    project_root_3 = tmp_path / "proj3"
    project_root_3.mkdir()
    args3 = _args(project_root_3, skills_root, target="a/b/c/example-script.sh")

    dry3 = _op().dry_run(project_root_3, args3)
    assert dry3["would_apply"] is True
    # dry_run must not create any directories or files.
    assert not (project_root_3 / "a").exists()

    result3 = _op().apply(project_root_3, args3)
    assert result3["status"] == "applied"


# ---------------------------------------------------------------------------
# test_path_traversal_refusal
# ---------------------------------------------------------------------------

def test_path_traversal_refusal(tmp_path):
    """target: with ../ traversal raises PathTraversalError via base class."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()

    traversal_args = _args(project_root, skills_root, target="../../../etc/passwd")

    with pytest.raises(PathTraversalError):
        _op().apply(project_root, traversal_args)

    # Also dry_run must refuse traversal.
    with pytest.raises(PathTraversalError):
        _op().dry_run(project_root, traversal_args)


# ---------------------------------------------------------------------------
# test_detect_drift_always_false
# ---------------------------------------------------------------------------

def test_detect_drift_always_false(tmp_path):
    """detect_drift always returns has_drift=False for create_file_from_template."""
    skills_root = _make_skills_root(tmp_path / "skills_root")
    project_root = tmp_path / "project"
    project_root.mkdir()

    args = _args(project_root, skills_root)

    # Case A: target missing.
    report = _op().detect_drift(project_root, args)
    assert report["has_drift"] is False
    assert report["drift_summary"] is None
    assert isinstance(report["drifted_regions"], list)
    assert report["drifted_regions"] == []

    # Case B: target exists.
    (project_root / "scripts").mkdir()
    (project_root / "scripts" / "example-script.sh").write_bytes(TEMPLATE_CONTENT)
    report2 = _op().detect_drift(project_root, args)
    assert report2["has_drift"] is False
    assert report2["drift_summary"] is None
    assert report2["drifted_regions"] == []


# ---------------------------------------------------------------------------
# Registry smoke test
# ---------------------------------------------------------------------------

def test_op_registered():
    """CreateFileFromTemplate is registered in OP_REGISTRY under the correct key."""
    assert "create_file_from_template" in OP_REGISTRY
    assert OP_REGISTRY["create_file_from_template"] is CreateFileFromTemplate
