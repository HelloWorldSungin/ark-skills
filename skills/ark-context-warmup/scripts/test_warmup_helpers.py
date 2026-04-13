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


import importlib.util as _ilu
from pathlib import Path as _P

_CONTRACT_PATH = _P(__file__).parent / "contract.py"
_spec_c = _ilu.spec_from_file_location("contract", _CONTRACT_PATH)
contract = _ilu.module_from_spec(_spec_c)
_spec_c.loader.exec_module(contract)


class TestContractParser:
    SAMPLE_SKILL_MD = """\
# Sample

Some content.

## Warmup Contract

```yaml
warmup_contract:
  version: 1
  commands:
    - id: cmd-a
      shell: 'echo {{foo}}'
      inputs:
        foo:
          from: env
          env_var: FOO
          required: true
      output:
        format: json
        extract:
          result: '$.result'
        required_fields: [result]
```
"""

    def test_extracts_contract(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(self.SAMPLE_SKILL_MD)
        c = contract.load_contract(skill_md)
        assert c is not None
        assert c["version"] == 1
        assert c["commands"][0]["id"] == "cmd-a"

    def test_missing_contract_returns_none(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Skill with no contract\n")
        assert contract.load_contract(skill_md) is None

    def test_malformed_yaml_returns_none(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("## Warmup Contract\n\n```yaml\nnot: valid: yaml\n```\n")
        assert contract.load_contract(skill_md) is None

    def test_validates_required_shell(self, tmp_path):
        bad = """## Warmup Contract

```yaml
warmup_contract:
  version: 1
  commands:
    - id: no-shell
      inputs: {}
      output:
        format: json
        extract: {}
        required_fields: []
```
"""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(bad)
        assert contract.load_contract(skill_md) is None


_AVAIL_PATH = _P(__file__).parent / "availability.py"
_spec_a = _ilu.spec_from_file_location("availability", _AVAIL_PATH)
avail = _ilu.module_from_spec(_spec_a)
_spec_a.loader.exec_module(avail)


class TestAvailabilityProbe:
    def test_all_unavailable(self, tmp_path):
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nonexistent",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,  # not on PATH
        )
        assert p["notebooklm"] is False
        assert p["wiki"] is False
        assert p["tasknotes"] is False

    def test_wiki_detected(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "_meta").mkdir(parents=True)
        (vault / "index.md").write_text("# Index\n")
        (vault / "_meta" / "vault-schema.md").write_text("# Schema\n")
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is True

    def test_wiki_missing_schema(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "index.md").write_text("# Index\n")
        # No _meta/vault-schema.md
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is False

    def test_tasknotes_detected(self, tmp_path):
        tn = tmp_path / "tn"
        (tn / "meta").mkdir(parents=True)
        (tn / "meta" / "X-counter").write_text("1\n")
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tn,
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["tasknotes"] is True

    def test_notebooklm_detected_with_valid_config(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "abc"}}}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",  # stand-in for "CLI exists"
        )
        assert p["notebooklm"] is True

    def test_notebooklm_multi_notebook_without_default_skipped(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",
        )
        assert p["notebooklm"] is False
        assert "default_for_warmup" in p["notebooklm_skip_reason"]

    def test_notebooklm_multi_notebook_with_default(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}, "default_for_warmup": "main"}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",
        )
        assert p["notebooklm"] is True


_ilu = importlib.util
_P = Path


_EV_PATH = _P(__file__).parent / "evidence.py"
_spec_e = _ilu.spec_from_file_location("evidence", _EV_PATH)
evidence = _ilu.module_from_spec(_spec_e)
_spec_e.loader.exec_module(evidence)


class TestEvidenceCandidates:
    def test_duplicate_component_match_high(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration provider",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-001", "title": "Auth rework", "status": "in-progress",
                     "component": "auth", "work-type": "feature", "matched_field": "component", "title_overlap": 0.2}
                ],
                "status_summary": {"in-progress": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert len(dups) == 1
        assert dups[0]["confidence"] == "high"
        assert dups[0]["id"] == "X-001"

    def test_duplicate_medium_overlap(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting api",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-002", "title": "rate limiting implementation api", "status": "open",
                     "component": "server", "work-type": "feature",
                     "matched_field": "title_overlap=0.75", "title_overlap": 0.75}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "rate",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert len(dups) == 1
        assert dups[0]["confidence"] == "medium"

    def test_duplicate_low_overlap_dropped(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting api",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-003", "title": "unrelated caching work", "status": "open",
                     "component": "cache", "work-type": "feature",
                     "matched_field": "title_overlap=0.45", "title_overlap": 0.45}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "rate",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert dups == []

    def test_closed_task_not_duplicate(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-004", "title": "Auth migration", "status": "done",
                     "component": "auth", "work-type": "feature",
                     "matched_field": "component", "title_overlap": 1.0}
                ],
                "status_summary": {"done": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        assert not [c for c in out if c["type"] == "Possible duplicate"]

    def test_worktype_alone_not_high(self):
        out = evidence.derive_candidates(
            task_normalized="fix authentication bug",
            scenario="bugfix",
            tasknotes={
                "matches": [
                    {"id": "X-005", "title": "completely unrelated feature", "status": "open",
                     "component": "billing", "work-type": "bug",
                     "matched_field": None, "title_overlap": 0.1}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "authentication",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert dups == []

    def test_prior_rejection_hit(self):
        out = evidence.derive_candidates(
            task_normalized="service mesh adoption",
            scenario="greenfield",
            tasknotes={"matches": [], "status_summary": {}, "extracted_component": "service"},
            notebooklm={
                "citations": [
                    {"session": "S042", "quote": "We decided against service mesh adoption because of operational overhead."}
                ],
                "bootstrap": "",
                "session_continue": "",
            },
            wiki={"matches": []},
        )
        prs = [c for c in out if c["type"] == "Possible prior rejection"]
        assert len(prs) == 1
        assert prs[0]["confidence"] == "medium"

    def test_prior_rejection_false_positive(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting",
            scenario="greenfield",
            tasknotes={"matches": [], "status_summary": {}, "extracted_component": "rate"},
            notebooklm={
                "citations": [
                    {"session": "S042", "quote": "We decided against the old quarterly planning cadence."}
                ],
                "bootstrap": "",
                "session_continue": "",
            },
            wiki={"matches": []},
        )
        prs = [c for c in out if c["type"] == "Possible prior rejection"]
        assert prs == []

    def test_in_flight_collision_high(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-006", "title": "Auth rework phase 2", "status": "in-progress",
                     "component": "auth", "work-type": "feature",
                     "matched_field": "component", "title_overlap": 0.3}
                ],
                "status_summary": {"in-progress": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        colls = [c for c in out if c["type"] == "Possible in-flight collision"]
        assert len(colls) == 1
        assert colls[0]["confidence"] == "high"

    def test_degraded_coverage_emitted(self):
        out = evidence.derive_candidates(
            task_normalized="anything",
            scenario="greenfield",
            tasknotes=None,  # lane unavailable
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        deg = [c for c in out if c["type"] == "Degraded coverage"]
        assert len(deg) == 1
        assert "tasknotes" in deg[0]["detail"].lower()

    def test_empty_lanes_not_degraded(self):
        # Deferred finding (codex round 3): an available-but-empty lane is NOT Degraded coverage.
        # Only a lane that was unavailable (None) counts as Degraded coverage.
        out = evidence.derive_candidates(
            task_normalized="unrelated task",
            scenario="greenfield",
            tasknotes={"matches": [], "status_summary": {}, "extracted_component": "unrelated"},
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        deg = [c for c in out if c["type"] == "Degraded coverage"]
        assert deg == []

    def test_all_lanes_unavailable_three_degraded(self):
        out = evidence.derive_candidates(
            task_normalized="anything",
            scenario="greenfield",
            tasknotes=None,
            notebooklm=None,
            wiki=None,
        )
        deg = [c for c in out if c["type"] == "Degraded coverage"]
        assert len(deg) == 3
        details = " ".join(d["detail"].lower() for d in deg)
        assert "tasknotes" in details
        assert "notebooklm" in details
        assert "wiki" in details
