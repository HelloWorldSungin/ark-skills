"""Tests for warmup-helpers.py - Phase 1 helpers."""
import importlib.util
import hashlib
from pathlib import Path

HELPERS_PATH = Path(__file__).parent / "warmup-helpers.py"
spec = importlib.util.spec_from_file_location("warmup_helpers", HELPERS_PATH)
wh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wh)


class TestTaskNormalize:
    def test_simple(self):
        # "Add" and "to" are in the stopwords list; "API" survives as "api".
        assert wh.task_normalize("Add rate limiting to API") == "rate limiting api"

    def test_empty_string(self):
        assert wh.task_normalize("") == "__empty__"

    def test_whitespace_only(self):
        assert wh.task_normalize("   \t\n  ") == "__empty__"

    def test_all_stopwords(self):
        assert wh.task_normalize("and the of") == "__empty__"

    def test_single_letter_and_stopwords_removed(self):
        # Single letters filtered by len>1 rule; "add" is a stopword.
        assert wh.task_normalize("x y z add feature") == "feature"

    def test_punctuation_stripped(self):
        assert wh.task_normalize("Fix: users' auth!") == "users auth"

    def test_unicode_nfc(self):
        # 'é' as single codepoint U+00E9
        single = wh.task_normalize("caf\u00e9 migration")
        # 'é' as 'e' + combining acute U+0301 — NFC should merge
        decomposed = wh.task_normalize("cafe\u0301 migration")
        assert single == decomposed

    def test_case_insensitive(self):
        assert wh.task_normalize("ADD FEATURE") == wh.task_normalize("add feature")

    def test_preserves_hyphens_and_underscores(self):
        assert wh.task_normalize("fix user-auth_flow") == "user-auth_flow"

    def test_drops_non_bmp(self):
        # Emoji should be stripped, word kept
        assert wh.task_normalize("🎉 migrate database") == "migrate database"


class TestTaskSummary:
    def test_preserves_case_and_punctuation(self):
        assert wh.task_summary("Add Rate Limiting!") == "Add Rate Limiting!"

    def test_collapses_whitespace(self):
        assert wh.task_summary("foo\n\nbar\tbaz") == "foo bar baz"

    def test_truncates_at_word_boundary(self):
        long = "word " * 50  # 250 chars
        result = wh.task_summary(long)
        assert len(result) <= 121  # 120 + ellipsis
        assert result.endswith("…")
        assert " " not in result[-3:-1]  # truncated at whitespace, not mid-word

    def test_short_unchanged(self):
        assert wh.task_summary("short task") == "short task"

    def test_empty(self):
        assert wh.task_summary("") == ""


class TestTaskHash:
    def test_determinism(self):
        assert wh.task_hash("hello world") == wh.task_hash("hello world")

    def test_different_inputs_different_hashes(self):
        assert wh.task_hash("foo") != wh.task_hash("bar")

    def test_length_is_16(self):
        assert len(wh.task_hash("anything")) == 16

    def test_hash_is_hex(self):
        h = wh.task_hash("test")
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_operates_on_already_normalized(self):
        # task_hash assumes its input is already normalized
        h = wh.task_hash("add rate limiting")
        expected = hashlib.sha256("add rate limiting".encode("utf-8")).hexdigest()[:16]
        assert h == expected

    def test_empty_sentinel_hashed(self):
        assert wh.task_hash("__empty__") == hashlib.sha256(b"__empty__").hexdigest()[:16]


import re


class TestChainId:
    def test_is_ulid_like_format(self):
        cid = wh.chain_id_new()
        # ULID: 26 characters, Crockford base32
        assert re.match(r"^[0-9A-HJKMNP-TV-Z]{26}$", cid)

    def test_two_calls_produce_different_ids(self):
        assert wh.chain_id_new() != wh.chain_id_new()

    def test_timestamp_prefix_non_decreasing_across_ms(self):
        # ULID timestamp prefix (first 10 chars) is non-decreasing across calls
        # separated by ≥1 ms. Within the same ms, the random tail may not sort — that
        # is acceptable for our use (chain_id is a coarse ordering, not a sequence).
        import time as _t
        cids = []
        for _ in range(10):
            cids.append(wh.chain_id_new())
            _t.sleep(0.002)  # ensure >= 1 ms between calls
        prefixes = [c[:10] for c in cids]
        assert prefixes == sorted(prefixes)


import subprocess


class TestCli:
    def test_cli_normalize(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "normalize", "Add rate limiting to API"],
            capture_output=True, text=True, check=True,
        )
        assert r.stdout.strip() == "rate limiting api"

    def test_cli_summary(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "summary", "Fix Auth!"],
            capture_output=True, text=True, check=True,
        )
        assert r.stdout.strip() == "Fix Auth!"

    def test_cli_hash(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "hash", "add rate limiting"],
            capture_output=True, text=True, check=True,
        )
        assert len(r.stdout.strip()) == 16

    def test_cli_chain_id(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "chain-id"],
            capture_output=True, text=True, check=True,
        )
        assert len(r.stdout.strip()) == 26

    def test_cli_unknown_command(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "bogus"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "unknown command" in r.stderr.lower()
