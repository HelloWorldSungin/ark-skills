"""Schema-validator coverage for target-profile pending_migrations (#34).

The two migrations gain an ``op:`` field naming a registered destructive op and
their ``status:`` flips ``pending`` -> ``active`` (engine-implemented). The
validator must accept the real profile and reject a pending entry that names an
unregistered op or an unknown status.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_target_profile_valid import validate  # noqa: E402

_TESTS_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _TESTS_DIR.parent
_REPO_ROOT = _SKILL_DIR.parent.parent


def _paths_for(profile: Path) -> dict:
    return {
        "profile_path": profile,
        "templates_dir": _SKILL_DIR / "templates",
        "changelog_path": _REPO_ROOT / "CHANGELOG.md",
        "migrations_dir": _SKILL_DIR / "migrations",
    }


def test_real_profile_pending_migrations_valid():
    errors = validate(**_paths_for(_SKILL_DIR / "target-profile.yaml"))
    assert errors == [], "\n".join(errors)


def test_unregistered_pending_op_rejected(tmp_path):
    profile = tmp_path / "target-profile.yaml"
    profile.write_text(
        textwrap.dedent("""\
            schema_version: 1
            managed_regions: []
            ensured_files: []
            ensured_gitignore: []
            ensured_mcp_servers: []
            pending_migrations:
              - id: bogus
                op: not_a_real_op
                since: 2.0.0
                status: active
        """)
    )
    errors = validate(**_paths_for(profile))
    assert any("not_a_real_op" in e or "op" in e.lower() for e in errors), errors


def test_unknown_pending_status_rejected(tmp_path):
    profile = tmp_path / "target-profile.yaml"
    profile.write_text(
        textwrap.dedent("""\
            schema_version: 1
            managed_regions: []
            ensured_files: []
            ensured_gitignore: []
            ensured_mcp_servers: []
            pending_migrations:
              - id: okf-conversion
                op: okf_conversion
                since: 2.0.0
                status: banana
        """)
    )
    errors = validate(**_paths_for(profile))
    assert any("status" in e.lower() for e in errors), errors
