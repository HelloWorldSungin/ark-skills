"""Tests for shared OMC page utilities."""
from pathlib import Path

import pytest

from omc_page import (
    OMCPage,
    body_hash,
    content_hash_slug,
    parse_page,
    write_page,
)


def test_body_hash_deterministic():
    assert body_hash("hello") == body_hash("hello")
    assert body_hash("hello") != body_hash("world")


def test_body_hash_operates_on_provided_string_only():
    # Callers pass the body portion — the function does not strip frontmatter itself.
    raw_with_fm = "---\ntitle: x\n---\n\n# Body\n"
    body_only = "# Body\n"
    assert body_hash(raw_with_fm) != body_hash(body_only)
    # When caller passes the post-parse body, the hash reflects that body.
    path = Path("/tmp/_test_body_hash_parse.md")
    path.write_text(raw_with_fm)
    page = parse_page(path)
    assert body_hash(page.body) == body_hash("\n# Body\n")  # parse_page preserves the leading newline


def test_content_hash_slug_stable_and_12_chars():
    slug = content_hash_slug("vault/Architecture/Auth.md", "body text")
    assert len(slug) == 12
    assert all(c in "0123456789abcdef" for c in slug)
    assert slug == content_hash_slug("vault/Architecture/Auth.md", "body text")
    assert slug != content_hash_slug("vault/Architecture/Users.md", "body text")
    assert slug != content_hash_slug("vault/Architecture/Auth.md", "different")


def test_parse_page_roundtrip(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: X\ntags: [a, b]\n---\n\n# X\n\nBody.\n")
    page = parse_page(path)
    assert page.frontmatter["title"] == "X"
    assert page.frontmatter["tags"] == ["a", "b"]
    assert "# X\n\nBody." in page.body


def test_parse_page_missing_frontmatter(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("# No frontmatter\n\nJust body.\n")
    page = parse_page(path)
    assert page.frontmatter == {}
    assert "No frontmatter" in page.body


def test_parse_page_malformed_yaml_raises(tmp_path):
    path = tmp_path / "page.md"
    path.write_text("---\ntitle: [unclosed\n---\n\nBody.\n")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_page(path)


def test_write_page_atomic(tmp_path):
    path = tmp_path / "new.md"
    page = OMCPage(frontmatter={"title": "T"}, body="# T\n\nBody.\n")
    write_page(path, page)
    assert path.exists()
    assert "title: T" in path.read_text()


def test_write_page_o_excl_blocks_overwrite(tmp_path):
    path = tmp_path / "existing.md"
    path.write_text("original")
    page = OMCPage(frontmatter={"title": "T"}, body="body")
    with pytest.raises(FileExistsError):
        write_page(path, page, exclusive=True)
