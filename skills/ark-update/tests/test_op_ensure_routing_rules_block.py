"""Tests for ops/ensure_routing_rules_block.py.

Tier-1 test matrix (per ralplan line 146):
  1. test_inherits_ensure_claude_md_section_contract
  2. test_id_is_hardcoded_routing_rules
  3. test_template_path_resolved
  4. test_dry_run_matches_apply  (codex P2-5)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path shim
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops import OP_REGISTRY, TargetProfileOp  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROUTING_TEMPLATE_CONTENT = "# Routing Rules\nRoute via context-discovery.\n"
ROUTING_TEMPLATE_NAME = "routing-template.md"
CANONICAL_ID = "routing-rules"
VERSION = "1.12.0"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def skills_root(tmp_path):
    """Build a fake skills_root with routing-template.md in templates/."""
    template_dir = tmp_path / "skills" / "ark-update" / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / ROUTING_TEMPLATE_NAME).write_text(
        ROUTING_TEMPLATE_CONTENT, encoding="utf-8"
    )
    return tmp_path


@pytest.fixture()
def op(skills_root):
    """Import and instantiate EnsureRoutingRulesBlock, clean registry after use."""
    from ops.ensure_routing_rules_block import EnsureRoutingRulesBlock  # noqa: E402
    instance = EnsureRoutingRulesBlock()
    yield instance
    OP_REGISTRY.pop("ensure_routing_rules_block", None)
    OP_REGISTRY.pop("ensure_claude_md_section", None)


def _make_args(project_root: Path, skills_root: Path, file_rel: str = "CLAUDE.md") -> dict:
    return {
        "file": file_rel,
        "version": VERSION,
        "skills_root": str(skills_root),
        "op_id": CANONICAL_ID,
        # Intentionally omit 'id' and 'template' — the op must inject them.
    }


def _managed_block(content: str = ROUTING_TEMPLATE_CONTENT, version: str = VERSION) -> str:
    return (
        f"<!-- ark:begin id={CANONICAL_ID} version={version} -->\n"
        f"{content}"
        f"<!-- ark:end id={CANONICAL_ID} -->\n"
    )


# ---------------------------------------------------------------------------
# 1. test_inherits_ensure_claude_md_section_contract
# ---------------------------------------------------------------------------

def test_inherits_ensure_claude_md_section_contract():
    """MRO must include both EnsureClaudeMdSection and TargetProfileOp."""
    from ops.ensure_routing_rules_block import EnsureRoutingRulesBlock
    from ops.ensure_claude_md_section import EnsureClaudeMdSection

    assert issubclass(EnsureRoutingRulesBlock, EnsureClaudeMdSection), (
        "EnsureRoutingRulesBlock must subclass EnsureClaudeMdSection"
    )
    assert issubclass(EnsureRoutingRulesBlock, TargetProfileOp), (
        "EnsureRoutingRulesBlock must subclass TargetProfileOp (via EnsureClaudeMdSection)"
    )

    # Confirm both appear in the MRO.
    mro_names = [cls.__name__ for cls in EnsureRoutingRulesBlock.__mro__]
    assert "EnsureClaudeMdSection" in mro_names
    assert "TargetProfileOp" in mro_names


# ---------------------------------------------------------------------------
# 2. test_id_is_hardcoded_routing_rules
# ---------------------------------------------------------------------------

def test_id_is_hardcoded_routing_rules(tmp_path, op, skills_root):
    """Passing a different 'id' in args must NOT affect marker id — always routing-rules."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"

    # Pass a deliberately wrong id — should be ignored.
    args = {
        "id": "some-other-id",
        "file": "CLAUDE.md",
        "template": "wrong-template.md",  # wrong template too — should be overridden
        "version": VERSION,
        "skills_root": str(skills_root),
        "op_id": "some-other-id",
    }

    result = op.apply(project_root, args)
    assert result["status"] == "applied"

    # The region written must use the canonical id, not the caller-supplied one.
    target_text = target_file.read_text(encoding="utf-8")
    assert f"id={CANONICAL_ID}" in target_text, (
        f"Marker must use canonical id={CANONICAL_ID!r}, not user-supplied id"
    )
    assert "id=some-other-id" not in target_text, (
        "User-supplied id must be ignored"
    )

    # Also confirm the routing template content was used, not the wrong template.
    assert ROUTING_TEMPLATE_CONTENT in target_text


# ---------------------------------------------------------------------------
# 3. test_template_path_resolved
# ---------------------------------------------------------------------------

def test_template_path_resolved(tmp_path, op, skills_root):
    """The op must load routing-template.md from templates/ under skills_root."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert result["status"] == "applied"

    # File content must contain the routing template content, not some other template.
    target_text = target_file.read_text(encoding="utf-8")
    assert ROUTING_TEMPLATE_CONTENT in target_text, (
        "apply must write routing-template.md content into the managed region"
    )

    # Confirm the exact template path that would be resolved exists.
    expected_template_path = (
        Path(skills_root) / "skills" / "ark-update" / "templates" / ROUTING_TEMPLATE_NAME
    )
    assert expected_template_path.exists(), (
        f"Template must exist at {expected_template_path}"
    )
    assert expected_template_path.read_text(encoding="utf-8") == ROUTING_TEMPLATE_CONTENT


# ---------------------------------------------------------------------------
# 4. test_dry_run_matches_apply  (codex P2-5)
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path, op, skills_root):
    """dry_run returns the same decision as apply, writing nothing.

    Scenarios:
      S1: target file missing → would_apply
      S2: file exists, region missing → would_apply
      S3: region matches (idempotent) → would_skip_idempotent
      S4: region content drifted → would_overwrite_drift
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    args = _make_args(project_root, skills_root)

    # S1: file missing → dry_run says would_apply; must NOT create file.
    assert not target_file.exists()
    dr_s1 = op.dry_run(project_root, args)
    assert dr_s1["would_apply"] is True
    assert dr_s1["would_skip_idempotent"] is False
    assert dr_s1["would_overwrite_drift"] is False
    assert not target_file.exists(), "dry_run must NOT create the target file"

    # S2: file exists, region absent → would_apply.
    target_file.write_text("# Existing content\n", encoding="utf-8")
    dr_s2 = op.dry_run(project_root, args)
    assert dr_s2["would_apply"] is True
    assert dr_s2["would_skip_idempotent"] is False

    # S3: region matches template + version → would_skip_idempotent; no write.
    target_file.write_text(_managed_block(), encoding="utf-8")
    mtime_s3 = target_file.stat().st_mtime_ns
    dr_s3 = op.dry_run(project_root, args)
    assert dr_s3["would_skip_idempotent"] is True
    assert dr_s3["would_apply"] is False
    assert dr_s3["would_overwrite_drift"] is False
    assert target_file.stat().st_mtime_ns == mtime_s3, "dry_run must not touch the file"

    # S4: content drifted → would_overwrite_drift; no backup written.
    drifted_content = "# Routing Rules\nDrifted content.\n"
    target_file.write_text(_managed_block(content=drifted_content), encoding="utf-8")
    mtime_s4 = target_file.stat().st_mtime_ns
    dr_s4 = op.dry_run(project_root, args)
    assert dr_s4["would_overwrite_drift"] is True
    assert dr_s4["would_skip_idempotent"] is False
    assert isinstance(dr_s4["drift_summary"], str), (
        "drift_summary must be a non-None string when would_overwrite_drift is True"
    )
    # No backup written and file not touched.
    ark_backups = project_root / ".ark" / "backups"
    no_backups = not any(True for _ in ark_backups.glob("*.bak")) if ark_backups.exists() else True
    assert no_backups, "dry_run must not write any backup files"
    assert target_file.stat().st_mtime_ns == mtime_s4, "dry_run must not write the target file"
