"""Tests for context_probe.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_probe as cp  # noqa: E402

FIXTURES = SCRIPTS_DIR / "fixtures" / "context-probe"


class TestProbeLevels:
    def test_ok_fresh(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        assert result["level"] == "ok"
        assert result["pct"] == 5

    def test_ok_warm_just_below_nudge(self):
        result = cp.probe(FIXTURES / "ok-warm.json")
        assert result["level"] == "ok"
        assert result["pct"] == 19

    def test_nudge_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "nudge-low.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 20

    def test_nudge_mid(self):
        result = cp.probe(FIXTURES / "nudge-mid.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28

    def test_nudge_high_just_below_strong(self):
        result = cp.probe(FIXTURES / "nudge-high.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 34

    def test_strong_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "strong-low.json")
        assert result["level"] == "strong"
        assert result["pct"] == 35

    def test_strong_high(self):
        result = cp.probe(FIXTURES / "strong-high.json")
        assert result["level"] == "strong"
        assert result["pct"] == 72

    def test_over_100_clamped(self):
        result = cp.probe(FIXTURES / "over-100.json")
        assert result["level"] == "strong"
        assert result["pct"] == 100  # clamped

    def test_threshold_overrides(self):
        # Custom thresholds: 10/25 instead of 20/35.
        result = cp.probe(FIXTURES / "nudge-mid.json", nudge_pct=10, strong_pct=25)
        assert result["level"] == "strong"  # 28 >= 25 with custom strong


class TestProbeTokens:
    def test_tokens_summed_when_all_subfields_present(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        # 6 + 100 + 1000 + 50000 = 51106
        assert result["tokens"] == 51106
        assert result["warnings"] == []

    def test_tokens_unavailable_when_current_usage_missing(self):
        result = cp.probe(FIXTURES / "missing-current-usage.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]

    def test_tokens_unavailable_when_subfield_non_integer(self):
        result = cp.probe(FIXTURES / "non-integer-token.json")
        assert result["level"] == "nudge"
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]


import os
import stat
import tempfile


class TestProbeErrors:
    def test_malformed_json(self):
        result = cp.probe(FIXTURES / "malformed.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "parse_error"

    def test_truncated_json(self):
        result = cp.probe(FIXTURES / "truncated.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "parse_error"

    def test_missing_used_percentage(self):
        result = cp.probe(FIXTURES / "missing-field.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "schema_mismatch"

    def test_wrong_type_used_percentage(self):
        result = cp.probe(FIXTURES / "wrong-type.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "schema_mismatch"

    def test_missing_file(self, tmp_path):
        result = cp.probe(tmp_path / "does-not-exist.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "file_missing"

    def test_directory_instead_of_file(self, tmp_path):
        result = cp.probe(tmp_path)  # tmp_path is a directory
        assert result["level"] == "unknown"
        assert result["reason"] == "not_a_file"

    def test_permission_denied(self, tmp_path):
        f = tmp_path / "noperm.json"
        f.write_text('{"context_window": {"used_percentage": 5}}')
        original_mode = f.stat().st_mode
        try:
            os.chmod(f, 0)
            result = cp.probe(f)
        finally:
            os.chmod(f, original_mode)
        assert result["level"] == "unknown"
        assert result["reason"] == "permission_error"


import time


class TestProbeSession:
    def test_cwd_mismatch(self):
        result = cp.probe(FIXTURES / "cwd-mismatch.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_cwd_match_passes(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "ok"

    def test_workspace_falls_back_when_cwd_absent(self):
        result = cp.probe(FIXTURES / "workspace-mismatch.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_session_id_mismatch(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_session_id="DIFFERENT-SESSION")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_session_id_match_passes(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_session_id="test-session-ok-fresh")
        assert result["level"] == "ok"

    def test_session_id_check_supersedes_mtime(self, tmp_path):
        # When expected_session_id is provided, mtime check is bypassed.
        f = tmp_path / "fresh.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        os.utime(f, (time.time() - 999999, time.time() - 999999))  # very old
        result = cp.probe(
            f,
            expected_session_id="test-session-ok-fresh",
            max_age_seconds=60,
        )
        assert result["level"] == "ok"  # session match wins

    def test_stale_file_rejected_when_no_session_id(self, tmp_path):
        f = tmp_path / "stale.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        os.utime(f, (time.time() - 999999, time.time() - 999999))
        result = cp.probe(f, max_age_seconds=60)
        assert result["level"] == "unknown"
        assert result["reason"] == "stale_file"

    def test_fresh_file_passes_ttl(self, tmp_path):
        f = tmp_path / "fresh.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        # mtime defaults to "now" — should pass.
        result = cp.probe(f, max_age_seconds=60)
        assert result["level"] == "ok"


class TestAtomicUpdate:
    def test_apply_mutator_writes_result(self, tmp_path):
        f = tmp_path / "chain.md"
        f.write_text("hello")
        cp.chain_file.atomic_update(f, lambda s: s + " world")
        assert f.read_text() == "hello world"

    def test_missing_file_creates(self, tmp_path):
        f = tmp_path / "newchain.md"
        cp.chain_file.atomic_update(f, lambda s: "fresh content")
        assert f.read_text() == "fresh content"

    def test_no_intermediate_state_visible(self, tmp_path):
        # Verify the temp-file-then-rename pattern: the original file is never partially written.
        f = tmp_path / "chain.md"
        f.write_text("initial")

        def slow_mutator(s):
            return s.upper() + "_DONE"

        cp.chain_file.atomic_update(f, slow_mutator)
        assert f.read_text() == "INITIAL_DONE"

    def test_concurrent_updates_serialize(self, tmp_path):
        # Spawn multiple threads doing atomic_update; verify count is exactly N.
        import threading
        f = tmp_path / "counter.md"
        f.write_text("0")

        def increment(_):
            cp.chain_file.atomic_update(f, lambda s: str(int(s.strip()) + 1))

        threads = [threading.Thread(target=increment, args=(None,)) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert int(f.read_text().strip()) == 20
