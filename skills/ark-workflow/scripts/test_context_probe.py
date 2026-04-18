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


import subprocess
import json as _json

SCRIPT_PATH = SCRIPTS_DIR / "context_probe.py"


def _run_cli(*args):
    """Run context_probe.py CLI; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestCliRaw:
    def test_raw_ok_fixture(self):
        rc, out, err = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
        )
        assert rc == 0, f"stderr: {err}"
        result = _json.loads(out)
        assert result["level"] == "ok"
        assert result["pct"] == 5

    def test_raw_strong_fixture(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "strong-low.json"),
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["level"] == "strong"

    def test_raw_with_expected_cwd_mismatch(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_raw_missing_file_exits_zero(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", "/tmp/__definitely_does_not_exist__.json",
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["reason"] == "file_missing"


SAMPLE_CHAIN = """\
---
scenario: bugfix
weight: medium
chain_id: TEST123
proceed_past_level: null
---
# Current Chain: bugfix-medium
## Steps
- [ ] /ark-context-warmup
- [ ] /investigate
- [ ] Fix
- [ ] /ship
## Notes
"""


class TestCliCheckOff:
    def test_check_off_first_step(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "check-off",
            "--step-index", "1",
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        body = chain.read_text()
        assert "- [x] /ark-context-warmup" in body
        assert "- [ ] /investigate" in body  # untouched

    def test_check_off_third_step(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, _ = _run_cli(
            "--format", "check-off",
            "--step-index", "3",
            "--chain-path", str(chain),
        )
        assert rc == 0
        body = chain.read_text()
        assert "- [x] Fix" in body
        assert "- [ ] /ark-context-warmup" in body
        assert "- [ ] /ship" in body

    def test_check_off_index_zero_no_op(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "check-off",
            "--step-index", "0",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == SAMPLE_CHAIN  # unchanged

    def test_check_off_index_too_large_no_op(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, _ = _run_cli(
            "--format", "check-off",
            "--step-index", "99",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == SAMPLE_CHAIN

    def test_check_off_idempotent_on_already_checked(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        # First check-off
        _run_cli("--format", "check-off", "--step-index", "1", "--chain-path", str(chain))
        first = chain.read_text()
        # Second check-off of the same step
        _run_cli("--format", "check-off", "--step-index", "1", "--chain-path", str(chain))
        assert chain.read_text() == first


class TestCliRecordProceed:
    def test_record_proceed_at_nudge_writes_nudge(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        assert "proceed_past_level: nudge" in chain.read_text()

    def test_record_proceed_at_strong_writes_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "strong-low.json"),
            "--chain-path", str(chain),
        )
        body = chain.read_text()
        assert "proceed_past_level: null" in body  # strong never silenced

    def test_record_proceed_at_ok_writes_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
            "--chain-path", str(chain),
        )
        assert "proceed_past_level: null" in chain.read_text()

    def test_record_proceed_no_stdout(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _, out, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert out == ""

    def test_record_proceed_idempotent(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        before = chain.read_text()
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert chain.read_text() == before

    def test_record_proceed_unknown_level_preserves_existing(self, tmp_path):
        # Spec: probe failures degrade silently; record-proceed must not
        # destroy existing suppression state when the cache is gone.
        chain = tmp_path / "current-chain.md"
        initial = SAMPLE_CHAIN.replace("proceed_past_level: null",
                                       "proceed_past_level: nudge")
        chain.write_text(initial)
        rc, _, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(tmp_path / "no-such-cache.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == initial  # unchanged

    def test_set_proceed_past_level_block_scalar_safe(self, tmp_path):
        # Regression: a chain file whose frontmatter has a block scalar
        # (`task_summary: |-`) with an indented line that literally contains
        # "proceed_past_level:" must NOT have that indented line clobbered.
        chain = tmp_path / "current-chain.md"
        chain.write_text(
            "---\n"
            "scenario: bugfix\n"
            "weight: medium\n"
            "task_summary: |-\n"
            "  Mention proceed_past_level: in user prose — must stay verbatim\n"
            "proceed_past_level: null\n"
            "---\n"
            "## Steps\n"
            "- [ ] /investigate\n"
        )
        rc, _, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        body = chain.read_text()
        assert "proceed_past_level: nudge" in body
        # The indented block-scalar line must be preserved exactly.
        assert "  Mention proceed_past_level: in user prose — must stay verbatim" in body


class TestCliRecordReset:
    def test_reset_clears_nudge(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, _, _ = _run_cli(
            "--format", "record-reset",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "proceed_past_level: null" in chain.read_text()
        assert "proceed_past_level: nudge" not in chain.read_text()

    def test_reset_idempotent_on_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)  # already null
        before = chain.read_text()
        _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert chain.read_text() == before

    def test_reset_no_stdout(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        _, out, _ = _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert out == ""

    def test_reset_preserves_checklist_body(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        body_with_progress = SAMPLE_CHAIN.replace("- [ ] /ark-context-warmup",
                                                  "- [x] /ark-context-warmup") \
                                         .replace("proceed_past_level: null",
                                                  "proceed_past_level: nudge")
        chain.write_text(body_with_progress)
        _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert "- [x] /ark-context-warmup" in chain.read_text()


class TestCliStepBoundary:
    def test_ok_level_prints_nothing(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_nudge_level_prints_menu(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace(
            "- [ ] /ark-context-warmup", "- [x] /ark-context-warmup"
        ).replace(
            "- [ ] /investigate", "- [x] /investigate"
        ))
        rc, out, err = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        assert "Context at 28%" in out
        assert "Which option? [a/b/c/proceed]" in out

    def test_nudge_suppressed_by_proceed_past_level(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_strong_not_suppressed_by_proceed_past_level(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "strong-low.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "Context at 35%" in out
        assert "attention-rot zone" in out

    def test_zero_completed_uses_entry_render(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)  # all unchecked
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "before chain has started" in out
        assert "(a) /compact — unavailable" in out

    def test_session_mismatch_silent(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_missing_chain_file_emits_degraded_menu(self, tmp_path):
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(tmp_path / "does-not-exist.md"),
        )
        assert rc == 0
        # Degraded menu still warns at the right level even with no chain context.
        assert "Context at 28%" in out


class TestCliPathBAcceptance:
    def test_ok_level_prints_nothing(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
        )
        assert rc == 0
        assert out == ""

    def test_nudge_level_prints_one_line_warning(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
        )
        assert rc == 0
        assert "Context at 28%" in out
        assert "Path B" in out
        assert "/clear" in out or "/compact" in out
        # Should be a single line of output (plus terminating newline).
        assert out.count("\n") <= 2

    def test_strong_level_prints_warning(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "strong-low.json"),
        )
        assert rc == 0
        assert "Context at 35%" in out

    def test_session_mismatch_silent(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
        )
        assert rc == 0
        assert out == ""
