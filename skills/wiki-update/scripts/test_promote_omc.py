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


def _write_session_log(repo, slug="S001-test"):
    logs_dir = repo / "vault" / "Session-Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / f"{slug}.md"
    path.write_text(
        "---\ntitle: Session 1\nsession: S001\ntype: session-log\n"
        "created: 2026-04-20\n---\n\n## Issues & Discoveries\n\n"
    )
    return path


def _mk_config(repo):
    return PromotionConfig(
        repo_root=repo,
        omc_wiki_dir=repo / ".omc" / "wiki",
        project_docs_path=repo / "vault",
        tasknotes_path=repo / "vault" / "TaskNotes",
        task_prefix="Arktest-",
        session_slug="S001-test",
        session_started_at=0.0,
    )


def test_promote_high_arch_lands_in_architecture(tmp_path):
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert report.auto_promoted >= 1
    promoted = list((repo / "vault" / "Architecture").glob("*.md"))
    assert any("JWT" in p.read_text() for p in promoted)
    # OMC source NOT yet deleted — it's in pending_deletes
    assert (repo / ".omc/wiki/arch-high.md").exists()
    assert any(p.name == "arch-high.md" for p in report.pending_deletes)


def test_promote_medium_stages_and_creates_tasknote(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert report.staged >= 1
    assert list((repo / "vault" / "Staging").glob("*.md"))
    assert list((repo / "vault" / "TaskNotes" / "Tasks" / "Bug").glob("*.md"))
    assert report.tasknotes_created >= 1


def test_promote_debugging_pattern_dual_writes(tmp_path):
    repo = _copy_fixture(tmp_path)
    log = _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert "JWT Refresh Race" in log.read_text()
    ts = list((repo / "vault" / "Troubleshooting").glob("*.md"))
    assert len(ts) == 1
    assert "compiled-insight" in ts[0].read_text()
    assert report.troubleshooting_created == 1


def test_promote_skips_pages_older_than_session_started_at(tmp_path):
    import os
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    ancient = repo / ".omc/wiki/arch-high.md"
    t = 0  # Jan 1, 1970
    os.utime(ancient, (t, t))
    cfg = _mk_config(repo)
    cfg.session_started_at = 1_000_000.0  # later than 0
    report = promote(cfg)
    # arch-high.md skipped because older than session start
    assert not any(p.name == "arch-high.md" for p in report.pending_deletes)


def test_promote_merges_via_ark_source_path_when_target_exists(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    # Pre-create a vault page at Architecture/Auth.md (matches ark-source-path in fixture arch-high.md)
    auth = repo / "vault" / "Architecture" / "Auth.md"
    auth.parent.mkdir(parents=True, exist_ok=True)
    auth.write_text("---\ntitle: Auth\ntype: architecture\n---\n\n# Existing\n\nold body.\n")
    report = promote(_mk_config(repo))
    assert report.merged_existing >= 1
    merged_text = auth.read_text()
    assert "Existing" in merged_text  # old body preserved
    assert "JWT" in merged_text  # new content appended
    assert "Continuation" in merged_text


def test_promote_pending_deletes_not_executed(tmp_path):
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    # No OMC page under pending_deletes is removed yet
    for pd in report.pending_deletes:
        assert pd.exists()
