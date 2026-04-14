"""Tests for check_target_profile_valid.py.

Two test cases per the plan:
  1. Runs validator against the actual target-profile.yaml — asserts exit 0.
  2. Runs validator against a broken fixture (invalid since: value) — asserts non-zero.

~60 LOC.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Resolve paths relative to the repo root (two levels above tests/)
_TESTS_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _TESTS_DIR.parent
_SCRIPTS_DIR = _SKILL_DIR / "scripts"
_REPO_ROOT = _SKILL_DIR.parent.parent  # ark-skills repo root

# Add scripts/ to sys.path so we can import the validator directly.
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from check_target_profile_valid import validate  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def real_paths():
    """Return paths for the actual production target-profile.yaml."""
    return {
        "profile_path": _SKILL_DIR / "target-profile.yaml",
        "templates_dir": _SKILL_DIR / "templates",
        "changelog_path": _REPO_ROOT / "CHANGELOG.md",
        "ark_workflow_ref": _REPO_ROOT / "skills" / "ark-workflow" / "references" / "routing-template.md",
        "migrations_dir": _SKILL_DIR / "migrations",
    }


@pytest.fixture()
def broken_profile(tmp_path):
    """Write a target-profile.yaml with an invalid since: value (99.99.99)."""
    profile = tmp_path / "target-profile.yaml"
    profile.write_text(
        textwrap.dedent("""\
            schema_version: 1
            managed_regions:
              - id: bad-entry
                op: ensure_claude_md_section
                file: CLAUDE.md
                template: omc-routing-block.md
                since: 99.99.99
                version: 99.99.99
            ensured_files: []
            ensured_gitignore: []
            ensured_mcp_servers: []
        """)
    )
    return {
        "profile_path": profile,
        "templates_dir": _SKILL_DIR / "templates",
        "changelog_path": _REPO_ROOT / "CHANGELOG.md",
        "ark_workflow_ref": _REPO_ROOT / "skills" / "ark-workflow" / "references" / "routing-template.md",
        "migrations_dir": _SKILL_DIR / "migrations",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_actual_profile_is_valid(real_paths):
    """Validator must return zero errors for the actual production target-profile.yaml."""
    errors = validate(**real_paths)
    assert errors == [], f"Unexpected errors:\n" + "\n".join(errors)


def test_broken_since_value_is_rejected(broken_profile):
    """Validator must return at least one error for a profile with since: 99.99.99."""
    errors = validate(**broken_profile)
    assert len(errors) >= 1, "Expected at least one error for invalid since: value"
    # Confirm the error is about the since value
    since_errors = [e for e in errors if "99.99.99" in e or "since" in e.lower()]
    assert since_errors, (
        f"Expected an error mentioning since: 99.99.99; got:\n" + "\n".join(errors)
    )


def test_missing_template_file_is_rejected(tmp_path):
    """Validator must error when a template: reference points to a non-existent file."""
    profile = tmp_path / "target-profile.yaml"
    profile.write_text(
        textwrap.dedent("""\
            schema_version: 1
            managed_regions:
              - id: missing-tmpl
                op: ensure_claude_md_section
                file: CLAUDE.md
                template: nonexistent-template.md
                since: 1.13.0
                version: 1.13.0
            ensured_files: []
            ensured_gitignore: []
            ensured_mcp_servers: []
        """)
    )
    # Use a separate empty templates dir so the file is genuinely missing
    empty_templates = tmp_path / "templates"
    empty_templates.mkdir()
    errors = validate(
        profile_path=profile,
        templates_dir=empty_templates,
        changelog_path=_REPO_ROOT / "CHANGELOG.md",
        ark_workflow_ref=_REPO_ROOT / "skills" / "ark-workflow" / "references" / "routing-template.md",
        migrations_dir=_SKILL_DIR / "migrations",
    )
    template_errors = [e for e in errors if "nonexistent-template" in e or "template" in e.lower()]
    assert template_errors, (
        f"Expected a template-resolution error; got:\n" + "\n".join(errors)
    )
