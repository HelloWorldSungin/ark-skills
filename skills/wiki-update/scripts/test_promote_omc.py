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


# --- Regression tests for review findings C1 / C2 / H1 / H2 / H3 / H4 ---

from promote_omc import (
    _atomic_write_text, _append_to_session_log, _merge_into_existing,
    _find_session_log, _resolve_existing_vault_page, finalize_deletes,
)


def test_path_traversal_ark_source_path_is_rejected_C1(tmp_path):
    """C1: ark-source-path='../../evil.md' must NOT resolve outside project_docs."""
    project_docs = tmp_path / "vault"
    project_docs.mkdir()
    outside = tmp_path / "evil.md"
    outside.write_text("outside")
    assert _resolve_existing_vault_page(project_docs, "../evil.md") is None
    assert _resolve_existing_vault_page(project_docs, "../../evil.md") is None
    assert _resolve_existing_vault_page(project_docs, "/etc/passwd") is None
    # Legitimate nested path still resolves
    inside = project_docs / "Architecture" / "Auth.md"
    inside.parent.mkdir(parents=True)
    inside.write_text("inside")
    assert _resolve_existing_vault_page(project_docs, "Architecture/Auth.md") == inside.resolve()


def test_promote_does_not_merge_when_ark_source_path_escapes_vault_C1(tmp_path):
    """C1 end-to-end: a crafted ark-source-path must not cause _merge_into_existing
    to write to a file outside project_docs."""
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    outside = repo.parent / "outside.md"
    outside.write_text("---\ntitle: Outside\n---\n\noriginal\n")
    # Overwrite the high-confidence fixture to carry an escaping ark-source-path.
    page = parse_page(repo / ".omc/wiki/arch-high.md")
    page.frontmatter["ark-source-path"] = "../../outside.md"
    write_page(repo / ".omc/wiki/arch-high.md", page)
    report = promote(_mk_config(repo))
    # outside.md must be untouched
    assert outside.read_text() == "---\ntitle: Outside\n---\n\noriginal\n"
    # Page still auto-promoted to in-tree Architecture/
    assert report.auto_promoted >= 1


def test_promote_populates_written_paths_C2(tmp_path):
    """C2: PromotionReport.written_paths must list every vault destination
    write_page / append / merge actually touched."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    report = promote(_mk_config(repo))
    assert len(report.written_paths) >= 1
    for p in report.written_paths:
        assert p.exists()
        assert p.stat().st_size > 0
    # Every written path is inside project_docs
    project_docs = (repo / "vault").resolve()
    for p in report.written_paths:
        p.resolve().relative_to(project_docs)


def test_finalize_deletes_gate_fails_when_required_path_missing_C2(tmp_path):
    """C2: finalize_deletes(require=[...]) must refuse to delete when a required
    destination file is missing."""
    omc_src = tmp_path / "omc.md"
    omc_src.write_text("x")
    missing = tmp_path / "vault" / "never-written.md"
    deleted, errs = finalize_deletes([omc_src], require=[missing])
    assert deleted == 0
    assert errs and "precondition failed" in errs[0]
    assert omc_src.exists()


def test_finalize_deletes_gate_fails_when_required_path_empty_C2(tmp_path):
    omc_src = tmp_path / "omc.md"
    omc_src.write_text("x")
    empty = tmp_path / "empty.md"
    empty.write_text("")
    deleted, errs = finalize_deletes([omc_src], require=[empty])
    assert deleted == 0
    assert errs and "missing or empty" in errs[0]
    assert omc_src.exists()


def test_finalize_deletes_gate_passes_when_required_path_valid_C2(tmp_path):
    omc_src = tmp_path / "omc.md"
    omc_src.write_text("x")
    valid = tmp_path / "valid.md"
    valid.write_text("non-empty")
    deleted, errs = finalize_deletes([omc_src], require=[valid])
    assert deleted == 1
    assert errs == []
    assert not omc_src.exists()


def test_merge_into_existing_is_idempotent_on_retry_H1(tmp_path):
    """H1: Running promote() twice on the same OMC source must not double-append
    the same Continuation block."""
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    auth = repo / "vault" / "Architecture" / "Auth.md"
    auth.parent.mkdir(parents=True, exist_ok=True)
    auth.write_text("---\ntitle: Auth\ntype: architecture\n---\n\n# Existing\n\nold body.\n")
    # First promote — merges.
    promote(_mk_config(repo))
    first_text = auth.read_text()
    first_count = first_text.count("## Continuation —")
    assert first_count == 1
    # Second promote on the same OMC source (pending_deletes never fired) — must be no-op.
    promote(_mk_config(repo))
    second_text = auth.read_text()
    assert second_text.count("## Continuation —") == 1
    assert first_text == second_text


def test_append_to_session_log_is_idempotent_on_retry_H1(tmp_path):
    """H1: dual-write-debug must not double-append the same debug entry when retried."""
    repo = _copy_fixture(tmp_path)
    log = _write_session_log(repo)
    promote(_mk_config(repo))
    first_text = log.read_text()
    first_count = first_text.count("Concurrent refresh causes double-issuance")
    assert first_count == 1
    # Idempotency marker should be present
    assert "<!-- src:" in first_text
    promote(_mk_config(repo))
    second_text = log.read_text()
    # Body content and marker must NOT be duplicated on retry
    assert second_text.count("Concurrent refresh causes double-issuance") == 1
    assert first_text == second_text


def test_append_to_session_log_atomic_via_tmp_rename_H1(tmp_path):
    """H1: _append_to_session_log writes via tmp+rename and does not leave a partial file
    in place of the session log."""
    log = tmp_path / "S001.md"
    log.write_text("---\n---\n\n## Issues & Discoveries\n\n")
    _append_to_session_log(log, "Thing", "body text")
    # No tmp leak
    assert not list(tmp_path.glob(".tmp-*"))
    assert "Thing" in log.read_text()
    assert "body text" in log.read_text()


def test_find_session_log_returns_none_on_miss_H2(tmp_path):
    """H2: no silent fallback to newest Session-Logs/*.md — must return None on slug miss."""
    docs = tmp_path / "vault"
    logs = docs / "Session-Logs"
    logs.mkdir(parents=True)
    (logs / "S050-other.md").write_text("x")
    (logs / "S051-another.md").write_text("y")
    assert _find_session_log(docs, "S001-missing") is None
    # exact match still returns
    (logs / "S001-hit.md").write_text("z")
    assert _find_session_log(docs, "S001-hit") == logs / "S001-hit.md"


def test_bridge_merge_preserves_omc_when_no_session_log_H3(tmp_path):
    """H3: bridge-merge must NOT append to pending_deletes when log_path is None.
    OMC source preserved; error recorded."""
    repo = _copy_fixture(tmp_path)
    # Manufacture a session-bridge OMC page
    bridge = repo / ".omc" / "wiki" / "bridge.md"
    bridge.write_text(
        "---\ntitle: B\ncategory: session-log\nconfidence: high\n"
        "tags: [session-bridge]\n---\n\nbridge body long enough\n"
    )
    cfg = _mk_config(repo)  # no session log written
    report = promote(cfg)
    assert not any(p.name == "bridge.md" for p in report.pending_deletes)
    assert any("bridge-merge" in e for e in report.errors)
    assert bridge.exists()


def test_dual_write_debug_preserves_omc_when_no_log_and_no_pattern_tag_H3(tmp_path):
    """H3: dual-write-debug with no session log AND no pattern/insight tag
    must preserve OMC source."""
    repo = _copy_fixture(tmp_path)
    dbg = repo / ".omc" / "wiki" / "plain-debug.md"
    dbg.write_text(
        "---\ntitle: D\ncategory: debugging\nconfidence: high\ntags: [debugging]\n---\n\n"
        "debugging body with enough length\n"
    )
    cfg = _mk_config(repo)  # no session log
    report = promote(cfg)
    assert not any(p.name == "plain-debug.md" for p in report.pending_deletes)
    assert any("dual-write-debug" in e for e in report.errors)
    assert dbg.exists()


def test_dual_write_debug_deletes_when_troubleshooting_written_but_no_log_H3(tmp_path):
    """H3 boundary: if troubleshooting was written (pattern/insight tag), OMC source
    CAN be deleted even without a session log because a vault side-effect occurred."""
    repo = _copy_fixture(tmp_path)
    # fixture debug-with-pattern-tag.md has tags [pattern, ...]
    cfg = _mk_config(repo)  # no session log
    report = promote(cfg)
    ts = list((repo / "vault" / "Troubleshooting").glob("*.md"))
    assert len(ts) == 1
    assert any(p.name == "debug-with-pattern-tag.md" for p in report.pending_deletes)


def test_programmer_errors_propagate_not_swallowed_H4(tmp_path, monkeypatch):
    """H4: narrow except — TypeError from broken code should CRASH, not become a
    per-file 'error' string."""
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    # Force classify() to raise TypeError (programmer bug); must NOT be swallowed.
    import promote_omc
    def boom(page, *, filename):
        raise TypeError("intentional programmer bug")
    monkeypatch.setattr(promote_omc, "classify", boom)
    with pytest.raises(TypeError, match="intentional programmer bug"):
        promote_omc.promote(_mk_config(repo))


def test_oserror_during_write_is_recorded_not_raised_H4(tmp_path, monkeypatch):
    """H4 complement: OSError from a vault write IS still caught (file-level failure)."""
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    import promote_omc
    original_write = promote_omc.write_page
    def breaking_write(path, page, **kw):
        if "arch-high.md" in str(path) or "Architecture" in str(path):
            raise OSError("simulated disk full")
        return original_write(path, page, **kw)
    monkeypatch.setattr(promote_omc, "write_page", breaking_write)
    report = promote_omc.promote(_mk_config(repo))
    # Failing page is reported but not crashed
    assert any("simulated disk full" in e for e in report.errors)
    # Failed page NOT in pending_deletes
    assert not any("arch-high.md" in str(p) for p in report.pending_deletes)
