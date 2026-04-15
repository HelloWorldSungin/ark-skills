"""Tests for ops/ensure_claude_md_section.py.

Tier-1 test matrix (per ralplan):
  1. test_apply_creates_missing_file
  2. test_apply_inserts_missing_region
  3. test_apply_idempotent_when_matching
  4. test_apply_drift_inside_markers_content
  5. test_apply_drift_stale_version
  6. test_apply_no_touch_outside_markers
  7. test_apply_refuses_mismatched_id
  8. test_detect_drift_return_shape
  9. test_dry_run_matches_apply   (codex P2-5)
 10. test_path_traversal_refusal  (codex P1-1)
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

from markers import extract_regions, MarkerIntegrityError  # noqa: E402
from paths import PathTraversalError  # noqa: E402
from ops import OP_REGISTRY  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEMPLATE_CONTENT = "# OMC Routing\nRoute everything here.\n"
TEMPLATE_NAME = "omc-routing-block.md"
REGION_ID = "omc-routing"
VERSION = "1.13.0"


@pytest.fixture()
def skills_root(tmp_path):
    """Build a fake skills_root with the omc-routing-block.md template."""
    template_dir = tmp_path / "skills" / "ark-update" / "templates"
    template_dir.mkdir(parents=True)
    (template_dir / TEMPLATE_NAME).write_text(TEMPLATE_CONTENT, encoding="utf-8")
    return tmp_path


@pytest.fixture()
def op(skills_root):
    """Import and instantiate EnsureClaudeMdSection, cleaning registry after use."""
    # Import here so the @register_op decorator fires.
    from ops.ensure_claude_md_section import EnsureClaudeMdSection  # noqa: E402
    instance = EnsureClaudeMdSection()
    yield instance
    # Cleanup registry entry so other tests don't see leaked registrations.
    OP_REGISTRY.pop("ensure_claude_md_section", None)


def _make_args(project_root: Path, skills_root: Path, file_rel: str = "CLAUDE.md") -> dict:
    return {
        "id": REGION_ID,
        "file": file_rel,
        "template": TEMPLATE_NAME,
        "version": VERSION,
        "skills_root": str(skills_root),
        "op_id": REGION_ID,
    }


def _managed_block(content: str = TEMPLATE_CONTENT, version: str = VERSION) -> str:
    return (
        f"<!-- ark:begin id={REGION_ID} version={version} -->\n"
        f"{content}"
        f"<!-- ark:end id={REGION_ID} -->\n"
    )


# ---------------------------------------------------------------------------
# 1. test_apply_creates_missing_file
# ---------------------------------------------------------------------------

def test_apply_creates_missing_file(tmp_path, op, skills_root):
    """target file doesn't exist — apply creates it with marker + content."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"

    assert not target_file.exists()

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert target_file.exists(), "apply must create the target file"
    assert result["status"] == "applied"

    regions = extract_regions(target_file)
    assert len(regions) == 1
    assert regions[0].id == REGION_ID
    assert regions[0].content == TEMPLATE_CONTENT
    assert result["error"] is None


# ---------------------------------------------------------------------------
# 2. test_apply_inserts_missing_region
# ---------------------------------------------------------------------------

def test_apply_inserts_missing_region(tmp_path, op, skills_root):
    """Target file exists but has no managed region — apply inserts at EOF.

    Bytes outside the inserted region must be preserved byte-exact.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    existing_content = "# My Project\n\nSome existing content.\n"
    target_file.write_text(existing_content, encoding="utf-8")

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert result["status"] == "applied"
    final_text = target_file.read_text(encoding="utf-8")

    # Original content must still be present at the start.
    assert final_text.startswith(existing_content)

    # Region must be parseable.
    regions = extract_regions(target_file)
    assert any(r.id == REGION_ID for r in regions)


# ---------------------------------------------------------------------------
# 3. test_apply_idempotent_when_matching
# ---------------------------------------------------------------------------

def test_apply_idempotent_when_matching(tmp_path, op, skills_root):
    """Second run on already-matching state: status=skipped_idempotent, no writes."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    target_file.write_text(_managed_block(), encoding="utf-8")

    args = _make_args(project_root, skills_root)
    mtime_before = target_file.stat().st_mtime_ns

    result = op.apply(project_root, args)

    assert result["status"] == "skipped_idempotent"
    assert result["backup_path"] is None
    assert result["error"] is None
    # File must not have been touched (mtime unchanged).
    assert target_file.stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# 4. test_apply_drift_inside_markers_content
# ---------------------------------------------------------------------------

def test_apply_drift_inside_markers_content(tmp_path, op, skills_root):
    """User edited content inside markers — apply backs up then overwrites.

    Codex P1-1 mitigation 1.1: backup bytes must be byte-equal to the
    pre-overwrite content.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    user_edited_content = "# OMC Routing\nUser-edited content — WRONG.\n"
    target_file.write_text(_managed_block(content=user_edited_content), encoding="utf-8")

    original_bytes = target_file.read_bytes()

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert result["status"] == "drifted_overwritten"
    assert result["drift_summary"] is not None
    assert isinstance(result["drift_summary"], str)
    assert result["backup_path"] is not None

    bak_path: Path = result["backup_path"]
    assert bak_path.exists(), "backup file must exist"
    # Backup must be byte-equal to pre-overwrite content (codex P1-1 mitigation 1.1).
    assert bak_path.read_bytes() == original_bytes, (
        "Backup bytes must be byte-equal to pre-overwrite file content"
    )

    # After overwrite, region content matches template.
    regions = extract_regions(target_file)
    region = next(r for r in regions if r.id == REGION_ID)
    assert region.content == TEMPLATE_CONTENT


# ---------------------------------------------------------------------------
# 5. test_apply_drift_stale_version
# ---------------------------------------------------------------------------

def test_apply_drift_stale_version(tmp_path, op, skills_root):
    """Content matches template BUT marker version= is stale (codex P2-3).

    apply must backup + re-stamp with the target version.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    stale_version = "1.12.0"
    # Content is byte-identical to template but version= is stale.
    target_file.write_text(_managed_block(content=TEMPLATE_CONTENT, version=stale_version), encoding="utf-8")

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert result["status"] == "drifted_overwritten"
    assert result["backup_path"] is not None
    assert result["drift_summary"] is not None

    # After re-stamp, marker version= must equal target version.
    regions = extract_regions(target_file)
    region = next(r for r in regions if r.id == REGION_ID)
    assert region.version == VERSION, (
        f"Expected marker version={VERSION!r} after re-stamp, got {region.version!r}"
    )


# ---------------------------------------------------------------------------
# 6. test_apply_no_touch_outside_markers
# ---------------------------------------------------------------------------

def test_apply_no_touch_outside_markers(tmp_path, op, skills_root):
    """Non-managed content before and after the region must be byte-identical after apply."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"

    preamble = "# Preamble\n\nSome user content here.\n\n"
    postamble = "\n## Other Section\n\nMore content.\n"
    user_edited_content = "# OMC Routing\nDrifted content.\n"
    full_content = preamble + _managed_block(content=user_edited_content) + postamble
    target_file.write_text(full_content, encoding="utf-8")

    args = _make_args(project_root, skills_root)
    result = op.apply(project_root, args)

    assert result["status"] == "drifted_overwritten"
    final_text = target_file.read_text(encoding="utf-8")

    # Preamble and postamble must survive byte-exact.
    assert final_text.startswith(preamble), "Preamble must be preserved byte-exact"
    assert final_text.endswith(postamble), "Postamble must be preserved byte-exact"


# ---------------------------------------------------------------------------
# 7. test_apply_refuses_mismatched_id
# ---------------------------------------------------------------------------

def test_apply_refuses_mismatched_id(tmp_path, op, skills_root):
    """File has mismatched begin/end marker ids — apply must raise MarkerIntegrityError."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    # Intentionally mismatched ids.
    corrupt_content = (
        "<!-- ark:begin id=foo version=1.0.0 -->\n"
        "some content\n"
        "<!-- ark:end id=bar -->\n"
    )
    target_file.write_text(corrupt_content, encoding="utf-8")

    args = _make_args(project_root, skills_root)
    with pytest.raises(MarkerIntegrityError):
        op.apply(project_root, args)


# ---------------------------------------------------------------------------
# 8. test_detect_drift_return_shape
# ---------------------------------------------------------------------------

def test_detect_drift_return_shape(tmp_path, op, skills_root):
    """detect_drift always returns the typed DriftReport shape.

    Check both has_drift=True and has_drift=False cases.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()

    args = _make_args(project_root, skills_root)

    # Case A: file missing → has_drift=True
    target_file = project_root / "CLAUDE.md"
    assert not target_file.exists()
    report_a = op.detect_drift(project_root, args)

    assert "has_drift" in report_a
    assert "drift_summary" in report_a
    assert "drifted_regions" in report_a
    assert report_a["has_drift"] is True
    assert isinstance(report_a["drift_summary"], str)
    assert isinstance(report_a["drifted_regions"], list)
    assert len(report_a["drifted_regions"]) > 0

    # Case B: matching state → has_drift=False
    target_file.write_text(_managed_block(), encoding="utf-8")
    report_b = op.detect_drift(project_root, args)

    assert report_b["has_drift"] is False
    assert report_b["drift_summary"] is None
    assert report_b["drifted_regions"] == []

    # Case C: stale version → has_drift=True (codex P2-3)
    target_file.write_text(_managed_block(version="1.11.0"), encoding="utf-8")
    report_c = op.detect_drift(project_root, args)

    assert report_c["has_drift"] is True
    assert isinstance(report_c["drift_summary"], str)
    assert REGION_ID in report_c["drifted_regions"]


# ---------------------------------------------------------------------------
# 9. test_dry_run_matches_apply  (codex P2-5)
# ---------------------------------------------------------------------------

def test_dry_run_matches_apply(tmp_path, op, skills_root):
    """dry_run returns the same decision as apply for each scenario.

    Scenarios tested (map to cases 1–5):
      S1: target file missing
      S2: file exists, region missing
      S3: file exists, region matches (idempotent)
      S4: file exists, region content drifted
      S5: file exists, region version= stale
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "CLAUDE.md"
    args = _make_args(project_root, skills_root)

    # S1: file missing → dry_run says would_apply; no file created.
    assert not target_file.exists()
    dr_s1 = op.dry_run(project_root, args)
    assert dr_s1["would_apply"] is True
    assert dr_s1["would_skip_idempotent"] is False
    assert dr_s1["would_overwrite_drift"] is False
    assert not target_file.exists(), "dry_run must NOT create the target file"

    # S2: file exists, region absent.
    target_file.write_text("# Existing content\n", encoding="utf-8")
    dr_s2 = op.dry_run(project_root, args)
    assert dr_s2["would_apply"] is True
    assert dr_s2["would_skip_idempotent"] is False

    # S3: region matches template + version.
    target_file.write_text(_managed_block(), encoding="utf-8")
    mtime_s3 = target_file.stat().st_mtime_ns
    dr_s3 = op.dry_run(project_root, args)
    assert dr_s3["would_skip_idempotent"] is True
    assert dr_s3["would_apply"] is False
    assert dr_s3["would_overwrite_drift"] is False
    # Confirm no write occurred.
    assert target_file.stat().st_mtime_ns == mtime_s3

    # S4: content drifted.
    drifted_content = "# OMC Routing\nDrifted.\n"
    target_file.write_text(_managed_block(content=drifted_content), encoding="utf-8")
    mtime_s4 = target_file.stat().st_mtime_ns
    dr_s4 = op.dry_run(project_root, args)
    assert dr_s4["would_overwrite_drift"] is True
    assert dr_s4["would_skip_idempotent"] is False
    assert isinstance(dr_s4["drift_summary"], str)
    # No backup written during dry_run.
    ark_backups = project_root / ".ark" / "backups"
    assert not any(True for _ in ark_backups.glob("*.bak")) if ark_backups.exists() else True
    # File not touched.
    assert target_file.stat().st_mtime_ns == mtime_s4

    # S5: stale version= (byte-identical content).
    target_file.write_text(_managed_block(version="1.11.0"), encoding="utf-8")
    mtime_s5 = target_file.stat().st_mtime_ns
    dr_s5 = op.dry_run(project_root, args)
    assert dr_s5["would_overwrite_drift"] is True
    assert isinstance(dr_s5["drift_summary"], str)
    # No write.
    assert target_file.stat().st_mtime_ns == mtime_s5


# ---------------------------------------------------------------------------
# 10. test_path_traversal_refusal  (codex P1-1)
# ---------------------------------------------------------------------------

def test_path_traversal_refusal(tmp_path, op, skills_root):
    """file: ../etc/passwd in args raises PathTraversalError BEFORE _apply_impl."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Absolute path.
    args_abs = {
        "id": REGION_ID,
        "file": "/etc/passwd",
        "template": TEMPLATE_NAME,
        "version": VERSION,
        "skills_root": str(skills_root),
        "op_id": REGION_ID,
    }
    with pytest.raises(PathTraversalError):
        op.apply(project_root, args_abs)

    # Parent-escape via '..'.
    args_escape = {
        "id": REGION_ID,
        "file": "../etc/passwd",
        "template": TEMPLATE_NAME,
        "version": VERSION,
        "skills_root": str(skills_root),
        "op_id": REGION_ID,
    }
    with pytest.raises(PathTraversalError):
        op.apply(project_root, args_escape)

    # dry_run must also refuse before any logic.
    with pytest.raises(PathTraversalError):
        op.dry_run(project_root, args_abs)

    # detect_drift must also refuse.
    with pytest.raises(PathTraversalError):
        op.detect_drift(project_root, args_abs)
