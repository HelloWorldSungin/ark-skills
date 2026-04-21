"""Tests for promote_omc: filter, edit-detection, confidence gate, translation."""
import shutil
import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import body_hash, parse_page, write_page
from promote_omc import (
    PromotionConfig, PromotionReport,
    classify, derive_summary, is_stub, promote, translate_frontmatter,
)


def _copy_fixture(tmp_path, name="mixed"):
    src = Path(__file__).parent / "fixtures" / name
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)
    return dst


def test_is_stub_auto_captured(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/stub-auto.md")
    assert is_stub(page, filename="stub-auto.md") is True


def test_is_stub_false_for_arch(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/arch-high.md")
    assert is_stub(page, filename="arch-high.md") is False


def test_classify_high_arch(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/arch-high.md")
    disp, _ = classify(page, filename="arch-high.md")
    assert disp == "auto-promote"


def test_classify_medium_staged(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/pattern-medium.md")
    disp, _ = classify(page, filename="pattern-medium.md")
    assert disp == "stage"


def test_classify_environment_skip(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/env-page.md")
    disp, _ = classify(page, filename="env-page.md")
    assert disp == "skip"


def test_classify_untouched_seed_skip(tmp_path):
    repo = _copy_fixture(tmp_path)
    path = repo / ".omc/wiki/source-warmup-untouched.md"
    page = parse_page(path)
    page.frontmatter["seed_body_hash"] = body_hash(page.body)
    write_page(path, page)
    page = parse_page(path)
    disp, _ = classify(page, filename=path.name)
    assert disp == "skip"


def test_classify_edited_seed_promoted_as_session_authored(tmp_path):
    repo = _copy_fixture(tmp_path)
    path = repo / ".omc/wiki/source-warmup-untouched.md"
    page = parse_page(path)
    page.frontmatter["seed_body_hash"] = "0" * 64
    write_page(path, page)
    page = parse_page(path)
    disp, reason = classify(page, filename=path.name)
    assert disp == "auto-promote"
    assert "edited" in reason.lower()


def test_classify_debugging_dual_write(tmp_path):
    repo = _copy_fixture(tmp_path)
    page = parse_page(repo / ".omc/wiki/debug-with-pattern-tag.md")
    disp, _ = classify(page, filename="debug-with-pattern-tag.md")
    assert disp == "dual-write-debug"


def test_translate_frontmatter_uses_ark_original_type():
    fm = {
        "title": "Users", "tags": ["users", "source-warmup"],
        "category": "architecture", "confidence": "high",
        "ark-original-type": "reference", "ark-source-path": "Architecture/Users.md",
        "sources": ["s1"], "schemaVersion": 1, "links": [],
        "seed_body_hash": "x" * 64, "seed_chain_id": "CH-1",
    }
    out = translate_frontmatter(fm, session_slug="S007-auth")
    assert out["type"] == "reference"
    assert out["source-sessions"] == ["[[S007-auth]]"]
    assert "source-warmup" not in out["tags"]
    for dropped in ("confidence", "schemaVersion", "links", "sources",
                    "seed_body_hash", "seed_chain_id",
                    "ark-original-type", "ark-source-path", "category"):
        assert dropped not in out
    assert "last-updated" in out


def test_translate_fallback_to_category_mapping():
    out = translate_frontmatter(
        {"title": "X", "tags": ["a"], "category": "decision", "confidence": "high"},
        session_slug="S001-x",
    )
    assert out["type"] == "decision-record"


def test_derive_summary_truncated_to_200():
    body = "Short first. " * 30 + "\n\nSecond."
    s = derive_summary(body)
    assert len(s) <= 200
