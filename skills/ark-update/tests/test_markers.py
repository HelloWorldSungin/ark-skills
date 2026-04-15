"""Tests for skills/ark-update/scripts/markers.py.

Covers:
  - Extract single region
  - Extract multiple regions
  - Nested markers → refuse (MarkerIntegrityError)
  - Mismatched id (begin id=a, end id=b) → refuse
  - Replace region preserves outside-markers bytes exactly
  - Insert region at EOF
  - version= parsing populates ManagedRegion.version
  - replace_region writes new version= into the begin marker
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from markers import (
    BEGIN_MARKER_RE,
    END_MARKER_RE,
    ManagedRegion,
    MarkerIntegrityError,
    extract_regions,
    insert_region,
    replace_region,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

def test_begin_marker_re_matches_valid():
    m = BEGIN_MARKER_RE.match("<!-- ark:begin id=omc-routing version=1.13.0 -->")
    assert m is not None
    assert m.group(1) == "omc-routing"
    assert m.group(2) == "1.13.0"


def test_begin_marker_re_rejects_uppercase_id():
    assert BEGIN_MARKER_RE.match("<!-- ark:begin id=OMC version=1.0.0 -->") is None


def test_end_marker_re_matches_valid():
    m = END_MARKER_RE.match("<!-- ark:end id=omc-routing -->")
    assert m is not None
    assert m.group(1) == "omc-routing"


# ---------------------------------------------------------------------------
# Extract single region
# ---------------------------------------------------------------------------

def test_extract_single_region(tmp_path):
    content = (
        "Before content\n"
        "<!-- ark:begin id=section-a version=1.11.0 -->\n"
        "Region body line 1\n"
        "Region body line 2\n"
        "<!-- ark:end id=section-a -->\n"
        "After content\n"
    )
    p = _write(tmp_path, "CLAUDE.md", content)
    regions = extract_regions(p)
    assert len(regions) == 1
    r = regions[0]
    assert r.id == "section-a"
    assert r.version == "1.11.0"
    assert r.begin_line == 2
    assert r.end_line == 5
    assert "Region body line 1" in r.content
    assert r.file == p


def test_extract_version_field_populated(tmp_path):
    """ManagedRegion.version is populated from the begin marker."""
    content = (
        "<!-- ark:begin id=my-region version=1.12.0 -->\n"
        "body\n"
        "<!-- ark:end id=my-region -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    regions = extract_regions(p)
    assert regions[0].version == "1.12.0"


def test_extract_region_with_no_content(tmp_path):
    """A region with no body lines has empty string content."""
    content = (
        "<!-- ark:begin id=empty version=1.0.0 -->\n"
        "<!-- ark:end id=empty -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    regions = extract_regions(p)
    assert len(regions) == 1
    assert regions[0].content == ""


# ---------------------------------------------------------------------------
# Extract multiple regions
# ---------------------------------------------------------------------------

def test_extract_multiple_regions(tmp_path):
    content = (
        "text before\n"
        "<!-- ark:begin id=alpha version=1.0.0 -->\n"
        "alpha content\n"
        "<!-- ark:end id=alpha -->\n"
        "middle text\n"
        "<!-- ark:begin id=beta version=1.1.0 -->\n"
        "beta content\n"
        "<!-- ark:end id=beta -->\n"
        "text after\n"
    )
    p = _write(tmp_path, "f.md", content)
    regions = extract_regions(p)
    assert len(regions) == 2
    assert regions[0].id == "alpha"
    assert regions[1].id == "beta"
    assert regions[0].version == "1.0.0"
    assert regions[1].version == "1.1.0"


def test_extract_empty_file_returns_no_regions(tmp_path):
    p = _write(tmp_path, "empty.md", "")
    assert extract_regions(p) == []


def test_extract_file_with_no_markers(tmp_path):
    p = _write(tmp_path, "plain.md", "Just some text\nNo markers here\n")
    assert extract_regions(p) == []


# ---------------------------------------------------------------------------
# Nested markers → refuse
# ---------------------------------------------------------------------------

def test_nested_markers_are_refused(tmp_path):
    content = (
        "<!-- ark:begin id=outer version=1.0.0 -->\n"
        "outer start\n"
        "<!-- ark:begin id=inner version=1.0.0 -->\n"
        "inner content\n"
        "<!-- ark:end id=inner -->\n"
        "outer end\n"
        "<!-- ark:end id=outer -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    with pytest.raises(MarkerIntegrityError, match="nested"):
        extract_regions(p)


# ---------------------------------------------------------------------------
# Mismatched id → refuse
# ---------------------------------------------------------------------------

def test_mismatched_id_is_refused(tmp_path):
    content = (
        "<!-- ark:begin id=section-a version=1.0.0 -->\n"
        "content\n"
        "<!-- ark:end id=section-b -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    with pytest.raises(MarkerIntegrityError, match="mismatched"):
        extract_regions(p)


def test_unclosed_region_is_refused(tmp_path):
    content = (
        "<!-- ark:begin id=section-a version=1.0.0 -->\n"
        "content with no end marker\n"
    )
    p = _write(tmp_path, "f.md", content)
    with pytest.raises(MarkerIntegrityError, match="unclosed"):
        extract_regions(p)


# ---------------------------------------------------------------------------
# Replace region: outside-markers bytes preserved exactly
# ---------------------------------------------------------------------------

def test_replace_region_preserves_outside_bytes(tmp_path):
    """Bytes outside the marker pair must be byte-identical after replace_region."""
    before_outside = "PREAMBLE LINE 1\nPREAMBLE LINE 2\n"
    after_outside = "EPILOGUE LINE 1\nEPILOGUE LINE 2\n"
    original_content = "original body\n"
    original = (
        before_outside
        + "<!-- ark:begin id=target version=1.0.0 -->\n"
        + original_content
        + "<!-- ark:end id=target -->\n"
        + after_outside
    )
    p = _write(tmp_path, "f.md", original)

    replace_region(p, "target", "new body\n", "1.1.0")

    result = p.read_text(encoding="utf-8")
    assert result.startswith(before_outside)
    assert result.endswith(after_outside)


def test_replace_region_updates_content(tmp_path):
    content = (
        "<!-- ark:begin id=r1 version=1.0.0 -->\n"
        "old content\n"
        "<!-- ark:end id=r1 -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    replace_region(p, "r1", "new content\n", "1.1.0")

    result = p.read_text(encoding="utf-8")
    assert "new content" in result
    assert "old content" not in result


def test_replace_region_updates_version_in_begin_marker(tmp_path):
    """replace_region writes the new version= into the begin marker."""
    content = (
        "<!-- ark:begin id=r1 version=1.0.0 -->\n"
        "body\n"
        "<!-- ark:end id=r1 -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    replace_region(p, "r1", "updated body\n", "1.3.0")

    result = p.read_text(encoding="utf-8")
    assert "version=1.3.0" in result
    assert "version=1.0.0" not in result


def test_replace_region_nonexistent_id_raises(tmp_path):
    content = (
        "<!-- ark:begin id=real version=1.0.0 -->\n"
        "body\n"
        "<!-- ark:end id=real -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    with pytest.raises(KeyError):
        replace_region(p, "nonexistent", "x", "1.0.0")


def test_replace_region_multiple_regions_only_touches_target(tmp_path):
    """When multiple regions exist, only the targeted one changes."""
    content = (
        "<!-- ark:begin id=alpha version=1.0.0 -->\n"
        "alpha body\n"
        "<!-- ark:end id=alpha -->\n"
        "<!-- ark:begin id=beta version=1.0.0 -->\n"
        "beta body\n"
        "<!-- ark:end id=beta -->\n"
    )
    p = _write(tmp_path, "f.md", content)
    replace_region(p, "alpha", "alpha updated\n", "2.0.0")

    result = p.read_text(encoding="utf-8")
    assert "alpha updated" in result
    assert "beta body" in result  # beta unchanged


# ---------------------------------------------------------------------------
# Insert region at EOF
# ---------------------------------------------------------------------------

def test_insert_region_eof(tmp_path):
    p = _write(tmp_path, "f.md", "existing content\n")
    insert_region(p, "new-section", "1.0.0", "inserted body\n")

    result = p.read_text(encoding="utf-8")
    assert "existing content" in result
    assert "<!-- ark:begin id=new-section version=1.0.0 -->" in result
    assert "inserted body" in result
    assert "<!-- ark:end id=new-section -->" in result


def test_insert_region_eof_on_empty_file(tmp_path):
    p = _write(tmp_path, "f.md", "")
    insert_region(p, "s1", "1.0.0", "body\n")

    result = p.read_text(encoding="utf-8")
    assert "<!-- ark:begin id=s1 version=1.0.0 -->" in result
    assert "body" in result


def test_insert_region_is_then_parseable(tmp_path):
    """After insert_region, extract_regions finds the new region."""
    p = _write(tmp_path, "f.md", "header\n")
    insert_region(p, "new-region", "1.2.0", "region body\n")

    regions = extract_regions(p)
    assert len(regions) == 1
    assert regions[0].id == "new-region"
    assert regions[0].version == "1.2.0"


def test_insert_region_unsupported_insertion_point_raises(tmp_path):
    p = _write(tmp_path, "f.md", "content\n")
    with pytest.raises(ValueError, match="eof"):
        insert_region(p, "s1", "1.0.0", "body", insertion_point="top")
