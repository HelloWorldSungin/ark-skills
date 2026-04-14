"""Tests for skills/ark-update/scripts/paths.py.

Covers the three rejection classes:
  1. Absolute path input
  2. '..' escape that crosses project_root
  3. Symlink whose resolved target lies outside project_root

Plus two positive cases:
  - Valid relative path directly under root
  - Valid nested relative path
"""
import sys
from pathlib import Path

import pytest

# Add scripts/ to path so we can import paths directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from paths import PathTraversalError, safe_resolve


# ---------------------------------------------------------------------------
# Rejection class 1: absolute paths
# ---------------------------------------------------------------------------

def test_absolute_path_is_refused(tmp_path):
    """Passing an absolute path raises PathTraversalError immediately."""
    with pytest.raises(PathTraversalError, match="relative"):
        safe_resolve(tmp_path, "/etc/passwd")


def test_absolute_path_as_path_object_is_refused(tmp_path):
    """Absolute Path object is also refused."""
    with pytest.raises(PathTraversalError, match="relative"):
        safe_resolve(tmp_path, Path("/tmp/evil"))


# ---------------------------------------------------------------------------
# Rejection class 2: '..' escape
# ---------------------------------------------------------------------------

def test_dotdot_escape_is_refused(tmp_path):
    """'../../etc/passwd' escapes root and is refused."""
    with pytest.raises(PathTraversalError):
        safe_resolve(tmp_path, "../../etc/passwd")


def test_single_dotdot_to_parent_is_refused(tmp_path):
    """'../sibling' escapes root and is refused."""
    with pytest.raises(PathTraversalError):
        safe_resolve(tmp_path, "../sibling_dir/file.txt")


def test_dotdot_that_stays_inside_root_is_accepted(tmp_path):
    """'subdir/../file.txt' resolves inside root and is accepted."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").touch()
    result = safe_resolve(tmp_path, "subdir/../file.txt")
    assert result == (tmp_path / "file.txt").resolve()


# ---------------------------------------------------------------------------
# Rejection class 3: symlink whose resolved target escapes root
# ---------------------------------------------------------------------------

def test_symlink_escape_is_refused(tmp_path):
    """A symlink pointing outside project_root is refused."""
    # Create a directory outside the project root.
    outside = tmp_path.parent / "outside_dir"
    outside.mkdir(exist_ok=True)
    outside_file = outside / "secret.txt"
    outside_file.write_text("secret")

    # Create a symlink inside project root that points outside.
    project_root = tmp_path / "project"
    project_root.mkdir()
    evil_link = project_root / "evil_link"
    evil_link.symlink_to(outside_file)

    with pytest.raises(PathTraversalError):
        safe_resolve(project_root, "evil_link")


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

def test_valid_relative_path_returns_resolved(tmp_path):
    """A simple relative path inside root returns a resolved absolute Path."""
    (tmp_path / "CLAUDE.md").touch()
    result = safe_resolve(tmp_path, "CLAUDE.md")
    assert result == (tmp_path / "CLAUDE.md").resolve()
    assert result.is_absolute()


def test_valid_nested_relative_path(tmp_path):
    """A nested relative path stays inside root and is returned resolved."""
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "config.yaml").touch()

    result = safe_resolve(tmp_path, "a/b/config.yaml")
    assert result == (tmp_path / "a" / "b" / "config.yaml").resolve()
    assert result.is_absolute()


def test_root_itself_as_dot_is_accepted(tmp_path):
    """'.' resolves to the root itself and is accepted."""
    result = safe_resolve(tmp_path, ".")
    assert result == tmp_path.resolve()
