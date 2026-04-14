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

    def test_precondition_script_resolved_against_skill_dir(self, tmp_path):
        """Codex follow-up P1: the contract declares precondition scripts with
        paths relative to the backend skill (e.g. 'scripts/session_shape_check.sh').
        load_contract must resolve those to absolute paths anchored at the SKILL.md's
        directory so /ark-context-warmup can execute them from any cwd."""
        skill_dir = tmp_path / "my-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        script_file = scripts_dir / "guard.sh"
        script_file.write_text("#!/usr/bin/env bash\nexit 0\n")
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "## Warmup Contract\n\n"
            "```yaml\n"
            "warmup_contract:\n"
            "  version: 1\n"
            "  commands:\n"
            "    - id: with-pre\n"
            "      shell: 'echo {{x}}'\n"
            "      inputs:\n"
            "        x: {from: env, env_var: X, required: true}\n"
            "      preconditions:\n"
            "        - id: guard\n"
            "          script: scripts/guard.sh\n"
            "      output:\n"
            "        format: json\n"
            "        extract: {x: '$.x'}\n"
            "        required_fields: [x]\n"
            "```\n"
        )
        c = contract.load_contract(skill_md)
        assert c is not None
        pre_script = c["commands"][0]["preconditions"][0]["script"]
        # Must be absolute and point at the resolved file under skill_dir
        assert Path(pre_script).is_absolute(), (
            f"precondition script should be absolute, got {pre_script!r}"
        )
        assert Path(pre_script).resolve() == script_file.resolve(), (
            f"precondition script should resolve to {script_file}, got {pre_script}"
        )

    def test_absolute_precondition_script_preserved(self, tmp_path):
        """Absolute paths (or $-prefixed paths that a caller has pre-expanded)
        must pass through load_contract unchanged."""
        abs_script = tmp_path / "external" / "pre.sh"
        abs_script.parent.mkdir()
        abs_script.write_text("#!/usr/bin/env bash\nexit 0\n")
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "## Warmup Contract\n\n"
            "```yaml\n"
            "warmup_contract:\n"
            "  version: 1\n"
            "  commands:\n"
            "    - id: abs-pre\n"
            "      shell: 'echo x'\n"
            "      inputs: {}\n"
            f"      preconditions:\n"
            f"        - id: guard\n"
            f"          script: {abs_script}\n"
            "      output:\n"
            "        format: json\n"
            "        extract: {}\n"
            "        required_fields: []\n"
            "```\n"
        )
        c = contract.load_contract(skill_md)
        assert c is not None
        assert c["commands"][0]["preconditions"][0]["script"] == str(abs_script)

    def test_notebooklm_contract_precondition_is_absolute(self):
        """End-to-end: the real notebooklm-vault contract must, after load,
        have an absolute precondition path that points at the committed
        session_shape_check.sh file."""
        skill_md = _P(__file__).parent.parent.parent / "notebooklm-vault" / "SKILL.md"
        c = contract.load_contract(skill_md)
        assert c is not None
        expected = skill_md.parent / "scripts" / "session_shape_check.sh"
        assert expected.exists(), f"fixture check: {expected} must exist"
        pres = c["commands"][0].get("preconditions", [])
        assert pres, "session-continue must have at least one precondition"
        resolved = Path(pres[0]["script"])
        assert resolved.is_absolute()
        assert resolved.resolve() == expected.resolve()

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

    def test_wiki_available_when_index_exists_without_schema(self, tmp_path):
        """Codex P2: minimal / pre-restructured vaults have index.md but may
        not have _meta/vault-schema.md. warmup_scan.py only reads index.md, so
        the wiki lane is functional — availability must not require the
        schema file or T4 gets incorrectly marked Degraded."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "index.md").write_text("# Index\n")
        # No _meta/vault-schema.md — that's fine for availability purposes.
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is True

    def test_wiki_unavailable_when_index_missing(self, tmp_path):
        """The only hard requirement for the wiki lane is that index.md exists
        so warmup_scan.py has something to parse."""
        vault = tmp_path / "vault"
        vault.mkdir()
        # No index.md
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is False
        assert "index.md" in p["wiki_skip_reason"]

    def test_tasknotes_detected_from_tasks_dir(self, tmp_path):
        """Codex P2: warmup_search.py only reads Tasks/*.md, never the counter
        file. Availability must key off the searchable content, not the
        task-creation counter."""
        tn = tmp_path / "tn"
        (tn / "Tasks").mkdir(parents=True)
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tn,
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["tasknotes"] is True

    def test_tasknotes_available_without_counter_file(self, tmp_path):
        """Imported or read-only vaults may have TaskNotes but no counter
        file yet. The search backend still works; availability must agree."""
        tn = tmp_path / "tn"
        (tn / "Tasks").mkdir(parents=True)
        (tn / "Tasks" / "X-01.md").write_text("---\ntitle: sample\n---\n")
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tn,
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["tasknotes"] is True

    def test_tasknotes_unavailable_without_tasks_dir(self, tmp_path):
        tn = tmp_path / "tn"
        tn.mkdir()
        # No Tasks/ subdir — nothing for warmup_search to read.
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tn,
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["tasknotes"] is False

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

    def test_notebooklm_config_falls_through_on_malformed_vault_side(self, tmp_path):
        """Codex P3: the documented lookup order is vault config first then
        project-repo config. A malformed vault-side .notebooklm/config.json
        must not short-circuit the lookup — we must still try the project-repo
        fallback."""
        vault = tmp_path / "vault"
        (vault / ".notebooklm").mkdir(parents=True)
        (vault / ".notebooklm" / "config.json").write_text("this is not valid json")
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "fallback-nb"}}}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",
        )
        assert p["notebooklm"] is True, (
            f"Should have fallen back to project-repo config; got {p.get('notebooklm_skip_reason')!r}"
        )

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

    def test_duplicate_component_match_includes_backlog(self):
        """Pre-landing review finding: /ark-tasknotes creates new tasks with
        default status: backlog (see ark-tasknotes/SKILL.md:83). The component
        duplicate detector must treat backlog as active — otherwise fresh
        not-yet-started tasks in the same component are silently missed."""
        out = evidence.derive_candidates(
            task_normalized="rate limiting api",
            scenario="greenfield",
            tasknotes={
                "extracted_component": "ratelimit",
                "matches": [
                    {
                        "id": "ARK-123",
                        "title": "Add rate limiting to API",
                        "status": "backlog",
                        "component": "ratelimit",
                        "work-type": "story",
                        "matched_field": "component",
                        "title_overlap": 0.9,
                    }
                ],
            },
            notebooklm=None,
            wiki=None,
        )
        dup = [c for c in out if c["type"] == "Possible duplicate"]
        assert any(c["id"] == "ARK-123" and c["confidence"] == "high" for c in dup), (
            "backlog-status TaskNote with component match must surface as "
            f"high-confidence duplicate; got {dup}"
        )

    def test_prior_rejection_apostrophe_variants(self):
        """Codex P2: tokenization strips apostrophes from citation text, so
        the configured trigger 'won't do' must match the natural spelling
        after normalization, not just the rarer 'wont do' form."""
        apostrophed = evidence.derive_candidates(
            task_normalized="service mesh adoption",
            scenario="greenfield",
            tasknotes=None,
            notebooklm={
                "recent_sessions": "",
                "immediate_next_steps": "",
                "where_we_left_off": "",
                "citations": [
                    {"quote": "we won't do service mesh because complexity is high and team lacks experience"}
                ],
            },
            wiki=None,
        )
        assert any(c["type"] == "Possible prior rejection" for c in apostrophed), (
            "apostrophized 'won't do' must still match after tokenization"
        )

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


_SYN_PATH = _P(__file__).parent / "synthesize.py"
_spec_s = _ilu.spec_from_file_location("synthesize", _SYN_PATH)
synthesize = _ilu.module_from_spec(_spec_s)
_spec_s.loader.exec_module(synthesize)


class TestSynthesize:
    def test_brief_structure(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123",
            task_hash="hash1234abcd5678",
            task_summary="Add rate limiting",
            scenario="greenfield",
            notebooklm_out="Recent sessions: S042...",
            wiki_out="Found: rate-limiting.md",
            tasknotes_out="3 in-progress, 1 open",
            evidence=[{"type": "Possible duplicate", "confidence": "high", "id": "X-01",
                       "detail": "rate limiting", "reason": "component match"}],
        )
        assert "## Context Brief" in brief
        assert "### Where We Left Off" in brief
        assert "### Recent Project Activity" in brief
        assert "### Vault Knowledge Relevant to This Task" in brief
        assert "### Related Tasks & In-flight Work" in brief
        assert "### Evidence" in brief
        assert "Possible duplicate" in brief

    def test_empty_evidence_reads_none(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        assert "### Evidence\nNone" in brief

    def test_omc_detected_line_yes(self):
        """Spec AC8: Context Brief includes an 'OMC detected: yes/no' line."""
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="",
            evidence=[], has_omc=True,
        )
        assert "**OMC detected:** yes" in brief
        # Must appear before the first sub-section so it's visible at top.
        omc_idx = brief.index("**OMC detected:**")
        where_idx = brief.index("### Where We Left Off")
        assert omc_idx < where_idx

    def test_omc_detected_line_no(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="",
            evidence=[], has_omc=False,
        )
        assert "**OMC detected:** no" in brief

    def test_omc_detected_line_defaults_to_no(self):
        """Backward compat: callers that don't pass has_omc still work."""
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        assert "**OMC detected:** no" in brief

    def test_frontmatter_fields(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="bugfix", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        assert brief.startswith("---\n")
        assert "chain_id: CID123" in brief
        assert "task_hash: hash1234abcd5678" in brief

    def test_frontmatter_yaml_safe_for_risky_task_summary(self, tmp_path):
        """Codex P2: the cache brief's frontmatter must roundtrip through
        yaml.safe_load even when task_summary contains YAML-significant
        characters. Otherwise cached_brief_if_fresh misparses, returns None,
        and every warm-up for tasks like 'Fix auth: rate limit' or
        '# cleanup' runs cold. Same class as the chain-file P1 #1."""
        import yaml
        risky_cases = [
            "Fix auth: rate limit",
            "# starts with hash",
            "pipe | in middle",
            'quote "inside" it',
            "apostrophe 'inside' it",
            "yes: maybe",
        ]
        for summary in risky_cases:
            brief = synthesize.assemble_brief(
                chain_id="C1", task_hash="abcdef1234567890", task_summary=summary,
                scenario="bugfix", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
            )
            m = re.match(r"---\n(.*?)\n---\n", brief, re.DOTALL)
            assert m is not None, f"frontmatter markers not found for summary={summary!r}"
            fm = yaml.safe_load(m.group(1))
            assert isinstance(fm, dict), f"yaml.safe_load returned non-dict for summary={summary!r}: {fm!r}"
            assert fm.get("task_summary", "").strip() == summary

    def test_cache_freshness_works_with_risky_task_summary(self, tmp_path):
        """End-to-end: write → read roundtrip must hit the cache even when
        the task summary contains YAML-significant text. Without the P2 fix,
        cached_brief_if_fresh returned None → every warm-up cold."""
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        risky = "Fix auth: rate limit"
        brief = synthesize.assemble_brief(
            chain_id="C2", task_hash="abcdef1234567890", task_summary=risky,
            scenario="bugfix", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        synthesize.write_brief_atomic(cache_dir=cache_dir, chain_id="C2",
                                      task_hash="abcdef1234567890", brief_text=brief)
        hit = synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="C2", task_hash="abcdef1234567890"
        )
        assert hit is not None, "cache must hit for YAML-safe-frontmatter brief"

    def test_atomic_write_and_prune(self, tmp_path):
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        # Pre-populate with a stale brief
        stale = cache_dir / "context-brief-OLD-00000000.md"
        stale.write_text("stale")
        import os, time
        old_time = time.time() - (25 * 3600)  # 25h ago
        os.utime(stale, (old_time, old_time))
        brief = "## Context Brief\nhello"
        written = synthesize.write_brief_atomic(
            cache_dir=cache_dir, chain_id="NEW",
            task_hash="abcdef1234567890", brief_text=brief,
        )
        assert written.exists()
        assert written.name == "context-brief-NEW-abcdef12.md"
        # 24h pruning happened
        assert not stale.exists()

    def test_cache_freshness_check(self, tmp_path):
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        brief = synthesize.assemble_brief(
            chain_id="CID", task_hash="abcdef1234567890", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        synthesize.write_brief_atomic(cache_dir=cache_dir, chain_id="CID",
                                      task_hash="abcdef1234567890", brief_text=brief)
        assert synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="CID", task_hash="abcdef1234567890"
        ) is not None
        # Mismatched hash → cache miss
        assert synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="CID", task_hash="DIFFERENT12345678"
        ) is None

    def test_cache_rejects_wrong_frontmatter(self, tmp_path):
        """Deferred finding: cached_brief_if_fresh must parse frontmatter, not substring.
        If a file at the expected path has wrong frontmatter values, reject it."""
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        target = cache_dir / "context-brief-MYCID-abcdef12.md"
        # Write a file whose body happens to mention a chain_id that differs from frontmatter.
        # Frontmatter chain_id = WRONG, but body mentions "chain_id: MYCID".
        target.write_text(
            "---\nchain_id: WRONG\ntask_hash: 00000000abcdef12\n---\n"
            "## Body\nFor reference, chain_id: MYCID was the previous chain.\n"
        )
        # Request chain_id=MYCID, task_hash=abcdef1234567890 (truncates to abcdef12).
        # A correct frontmatter parse MUST reject this (frontmatter chain_id is WRONG).
        result = synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="MYCID", task_hash="abcdef1234567890"
        )
        assert result is None

    def test_tmp_filename_unique_per_call(self, tmp_path, monkeypatch):
        """Deferred finding: tmp file must be unique per process to prevent concurrent-write clobber.
        The implementation should use PID + random suffix on the tmp file."""
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        # Capture tmp filenames via monkeypatching Path.write_text to record the path
        captured_tmp_paths = []
        original_write_text = type(tmp_path).write_text

        def recording_write_text(self, *args, **kwargs):
            if self.name.endswith(".tmp") or ".tmp." in self.name:
                captured_tmp_paths.append(self.name)
            return original_write_text(self, *args, **kwargs)

        monkeypatch.setattr(type(tmp_path), "write_text", recording_write_text)

        # Write twice with same chain_id+hash — tmp filenames must differ
        synthesize.write_brief_atomic(
            cache_dir=cache_dir, chain_id="CID", task_hash="abcdef1234567890",
            brief_text="a",
        )
        synthesize.write_brief_atomic(
            cache_dir=cache_dir, chain_id="CID", task_hash="abcdef1234567890",
            brief_text="b",
        )
        assert len(captured_tmp_paths) >= 2
        # At least two distinct tmp names (ensures uniqueness)
        assert len(set(captured_tmp_paths)) == len(captured_tmp_paths)


_EXEC_PATH = _P(__file__).parent / "executor.py"
_spec_ex = _ilu.spec_from_file_location("executor", _EXEC_PATH)
executor = _ilu.module_from_spec(_spec_ex)
_spec_ex.loader.exec_module(executor)


class TestInputResolution:
    def test_env_input(self, monkeypatch):
        monkeypatch.setenv("WARMUP_SCENARIO", "greenfield")
        input_spec = {"from": "env", "env_var": "WARMUP_SCENARIO", "required": True}
        assert executor.resolve_input(input_spec, config=None, templates={}) == "greenfield"

    def test_env_input_missing_required(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        input_spec = {"from": "env", "env_var": "MISSING_VAR", "required": True}
        import pytest
        with pytest.raises(executor.InputResolutionError):
            executor.resolve_input(input_spec, config=None, templates={})

    def test_config_input_simple_json_path(self):
        cfg = {"notebooks": {"main": {"id": "nb-abc"}}}
        input_spec = {"from": "config", "json_path": "notebooks.main.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-abc"

    def test_config_input_lookup_single_or_default_for_warmup(self):
        cfg = {"notebooks": {"main": {"id": "nb-abc"}}}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-abc"

    def test_config_input_lookup_multi_with_default(self):
        cfg = {"notebooks": {"a": {"id": "nb-a"}, "b": {"id": "nb-b"}}, "default_for_warmup": "b"}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-b"

    def test_config_input_lookup_multi_without_default_raises(self):
        cfg = {"notebooks": {"a": {"id": "nb-a"}, "b": {"id": "nb-b"}}}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        import pytest
        with pytest.raises(executor.InputResolutionError, match="default_for_warmup"):
            executor.resolve_input(input_spec, config=cfg, templates={})

    def test_template_input_leaves_unknown_placeholder_literal(self, monkeypatch):
        """When a {VAR} placeholder has no matching env var, the placeholder
        passes through literally — matching the pre-interpolation behavior for
        unknown vars. (Used to document the expected 'fail soft' policy.)"""
        monkeypatch.delenv("WARMUP_TASK_TEXT", raising=False)
        input_spec = {"from": "template", "template_id": "my_prompt"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"my_prompt": "Hello, {WARMUP_TASK_TEXT}!"},
        )
        assert result == "Hello, {WARMUP_TASK_TEXT}!"

    def test_template_input_interpolates_env_placeholder(self, monkeypatch):
        """Templates use {WARMUP_TASK_TEXT} / {WARMUP_PROJECT_NAME} placeholders
        which must be replaced with env values before the shell executes.
        Codex P1: without interpolation, NotebookLM gets asked about the
        literal string "{WARMUP_TASK_TEXT}" instead of the user's task."""
        monkeypatch.setenv("WARMUP_TASK_TEXT", "rate limit the login route")
        input_spec = {"from": "template", "template_id": "my_prompt"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"my_prompt": "What is: {WARMUP_TASK_TEXT}?"},
        )
        assert result == "What is: rate limit the login route?"

    def test_template_input_interpolates_multiple_placeholders(self, monkeypatch):
        monkeypatch.setenv("WARMUP_TASK_TEXT", "foo")
        monkeypatch.setenv("WARMUP_PROJECT_NAME", "bar")
        input_spec = {"from": "template", "template_id": "p"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"p": "Project {WARMUP_PROJECT_NAME} task {WARMUP_TASK_TEXT}"},
        )
        assert result == "Project bar task foo"

    def test_template_input_resolves_two_layer_indirection(self, monkeypatch):
        """Codex P1 (latest): wiki-query's scenario_query template contains
        {WARMUP_SCENARIO_QUERY_TEMPLATE} which expands to e.g.
        'Has anything like {WARMUP_TASK_TEXT} been built before?' — the inner
        {WARMUP_TASK_TEXT} must also expand. Interpolation must iterate until
        no further substitution is possible."""
        monkeypatch.setenv(
            "WARMUP_SCENARIO_QUERY_TEMPLATE",
            "Has anything like {WARMUP_TASK_TEXT} been built before?",
        )
        monkeypatch.setenv("WARMUP_TASK_TEXT", "rate limiting")
        input_spec = {"from": "template", "template_id": "p"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"p": "{WARMUP_SCENARIO_QUERY_TEMPLATE}"},
        )
        assert result == "Has anything like rate limiting been built before?"

    def test_template_input_self_reference_terminates(self, monkeypatch):
        """Iterative interpolation must not loop if an env var self-references
        its own placeholder. The value reaches a fixed point and we stop."""
        monkeypatch.setenv("WARMUP_LOOP", "{WARMUP_LOOP}")
        input_spec = {"from": "template", "template_id": "p"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"p": "{WARMUP_LOOP}"},
        )
        # Fixed point: the substitution keeps emitting {WARMUP_LOOP} itself.
        assert result == "{WARMUP_LOOP}"


class TestShellSubstitution:
    def test_substitute_plain_values_pass_through(self):
        """Bare-word values are idempotent under shlex.quote so the simple
        substitution case reads identically to the pre-quoting behavior."""
        result = executor.substitute_shell_template(
            "run {{cmd}} with id {{id}}", {"cmd": "do-thing", "id": "xyz"}
        )
        assert result == "run do-thing with id xyz"

    def test_missing_var_raises(self):
        import pytest
        with pytest.raises(KeyError):
            executor.substitute_shell_template("run {{missing}}", {})

    def test_values_with_spaces_are_quoted(self):
        """A value with whitespace must be quoted so it stays as a single
        argument when bash -c parses the resulting command."""
        result = executor.substitute_shell_template(
            "run {{x}}", {"x": "hello world"}
        )
        # After bash -c parses the result, argv[1] must be 'hello world' (one arg).
        # shlex.quote produces 'hello world' with surrounding single quotes.
        r = executor.run_shell(
            f"bash -c 'echo \"[$1]\"' -- {executor.substitute_shell_template('{{x}}', {'x': 'hello world'})}"
        )
        assert r.stdout.strip() == "[hello world]"

    def test_values_with_double_quotes_are_safe(self):
        """Codex P1: task text like 'Fix the \"auth\" bug' would have broken
        the `notebooklm ask \"{{prompt}}\" ...` command and swallowed the
        inner quotes."""
        dangerous = 'Fix the "auth" bug'
        subbed = executor.substitute_shell_template("printf '%s' {{x}}", {"x": dangerous})
        r = executor.run_shell(subbed)
        assert r.exit_code == 0
        assert r.stdout == dangerous

    def test_values_with_dollar_substitution_are_neutralized(self):
        """Codex P1: a crafted task text like '$(...)' must NOT run on the
        host. printf is idempotent on its arg so equality with the literal
        input proves no command substitution ran — if $() fired, we'd see
        'MARKER-FIRED' here instead."""
        dangerous = "$(printf MARKER-FIRED)"
        subbed = executor.substitute_shell_template("printf %s {{x}}", {"x": dangerous})
        r = executor.run_shell(subbed)
        assert r.exit_code == 0
        # Exactly the literal input; not the 11-char substitution result.
        assert r.stdout == dangerous

    def test_values_with_backticks_are_neutralized(self):
        """Same premise as the $(...) test but for the older backtick form."""
        dangerous = "`printf MARKER-FIRED`"
        subbed = executor.substitute_shell_template("printf %s {{x}}", {"x": dangerous})
        r = executor.run_shell(subbed)
        assert r.exit_code == 0
        assert r.stdout == dangerous

    def test_values_with_single_quote_are_escaped(self):
        dangerous = "can't stop"
        subbed = executor.substitute_shell_template("printf '%s' {{x}}", {"x": dangerous})
        r = executor.run_shell(subbed)
        assert r.exit_code == 0
        assert r.stdout == dangerous

    def test_numeric_values_stringify_and_quote(self):
        """Non-string values (e.g. ints) must not blow up shlex.quote."""
        subbed = executor.substitute_shell_template("echo {{n}}", {"n": 42})
        r = executor.run_shell(subbed)
        assert r.exit_code == 0
        assert r.stdout.strip() == "42"


class TestBackendContractTemplatePlaceholders:
    """Guardrail: prompt_templates in backend contracts must use the
    single-brace `{UPPERCASE_VAR}` form that _interpolate_template recognises.
    `${VAR}` / `$VAR` was once used and silently left the literal string in
    the resolved input — codex P1 (latest). Scan every template for a bare
    `$` and fail loudly if one appears."""

    _SKILLS = [
        _P(__file__).parent.parent.parent / "notebooklm-vault" / "SKILL.md",
        _P(__file__).parent.parent.parent / "wiki-query" / "SKILL.md",
        _P(__file__).parent.parent.parent / "ark-tasknotes" / "SKILL.md",
    ]

    def test_no_dollar_placeholders_in_prompt_templates(self):
        import re
        for skill_md in self._SKILLS:
            c = contract.load_contract(skill_md)
            assert c is not None, f"contract failed to load for {skill_md}"
            templates = c.get("prompt_templates") or {}
            for tid, body in templates.items():
                assert "$" not in body, (
                    f"{skill_md.name} prompt_templates[{tid!r}] contains a '$' — "
                    f"the executor's _interpolate_template matches single-brace "
                    f"{{UPPERCASE}} placeholders, not shell-style ${{VAR}}. "
                    f"Body: {body!r}"
                )


class TestBackendContractShellTemplates:
    """Guardrail: backend warmup_contract `shell:` templates must NOT wrap
    {{placeholder}} substitutions in surrounding shell quotes. The executor
    shlex-quotes every substituted value, so templates that write
    `"{{prompt}}"` end up with doubled quotes after substitution (breaking
    parsing). Every double-brace substitution site in a shell template must
    appear bare."""

    _SKILLS = [
        _P(__file__).parent.parent.parent / "notebooklm-vault" / "SKILL.md",
        _P(__file__).parent.parent.parent / "wiki-query" / "SKILL.md",
        _P(__file__).parent.parent.parent / "ark-tasknotes" / "SKILL.md",
    ]

    def test_no_quoted_placeholders_in_backend_shells(self):
        import re
        for skill_md in self._SKILLS:
            c = contract.load_contract(skill_md)
            assert c is not None, f"contract failed to load for {skill_md}"
            for cmd in c["commands"]:
                shell = cmd["shell"]
                # Find all {{placeholder}} positions and their immediate neighbors
                for m in re.finditer(r"\{\{[^}]+\}\}", shell):
                    start, end = m.span()
                    before = shell[start - 1] if start > 0 else ""
                    after = shell[end] if end < len(shell) else ""
                    assert not (before in ("'", '"') and before == after), (
                        f"{skill_md.name} command {cmd['id']!r}: placeholder "
                        f"{m.group(0)} is wrapped in {before!r} quotes — remove "
                        f"the quotes; the executor shlex-quotes substituted values."
                    )


class TestJSONPathExtract:
    def test_dotted(self):
        data = {"answer": {"sections": {"recent": "stuff"}}}
        assert executor.extract_json_path(data, "$.answer.sections.recent") == "stuff"

    def test_missing_key_returns_none(self):
        assert executor.extract_json_path({"a": 1}, "$.b.c") is None

    def test_root(self):
        assert executor.extract_json_path({"x": 1}, "$") == {"x": 1}

    def test_array_indexing_not_supported_raises(self):
        import pytest
        with pytest.raises(executor.JSONPathError, match="array"):
            executor.extract_json_path({"a": [1, 2]}, "$.a[0]")


class TestPrecondition:
    def test_script_exit_zero_runs(self, tmp_path):
        script = tmp_path / "ok.sh"
        script.write_text("#!/usr/bin/env bash\nexit 0\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=5
        )
        assert ok is True

    def test_script_nonzero_skips(self, tmp_path):
        script = tmp_path / "nope.sh"
        script.write_text("#!/usr/bin/env bash\necho skip reason >&2\nexit 1\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=5
        )
        assert ok is False
        assert "skip reason" in stderr

    def test_script_timeout_treated_as_skip(self, tmp_path):
        script = tmp_path / "slow.sh"
        script.write_text("#!/usr/bin/env bash\nsleep 10\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=1
        )
        assert ok is False
        assert "timeout" in stderr.lower() or "timed out" in stderr.lower()

    def test_script_receives_env(self, tmp_path):
        script = tmp_path / "echoenv.sh"
        script.write_text("#!/usr/bin/env bash\n[ \"$WARMUP_TASK_HASH\" = 'abc' ] && exit 0 || exit 1\n")
        script.chmod(0o755)
        ok, _ = executor.run_precondition(
            script_path=script, env={"WARMUP_TASK_HASH": "abc"}, timeout_s=5
        )
        assert ok is True


class TestShellExecute:
    def test_shell_timeout(self):
        r = executor.run_shell("sleep 10", timeout_s=1)
        assert r.timed_out is True

    def test_shell_captures_stdout(self):
        r = executor.run_shell("echo hello", timeout_s=5)
        assert r.timed_out is False
        assert r.exit_code == 0
        assert r.stdout.strip() == "hello"


class TestEndToEndExecute:
    def test_execute_command_happy_path(self, tmp_path, monkeypatch):
        script = tmp_path / "fake_backend.sh"
        script.write_text("#!/usr/bin/env bash\necho '{\"payload\": {\"value\": \"'\"$FOO\"'\"}}'\n")
        script.chmod(0o755)
        monkeypatch.setenv("FOO", "bar")
        command_spec = {
            "id": "fake",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {"value": "$.payload.value"},
                "required_fields": ["value"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result == {"value": "bar"}

    def test_execute_command_missing_required_field_returns_none(self, tmp_path):
        script = tmp_path / "empty.sh"
        script.write_text("#!/usr/bin/env bash\necho '{}'\n")
        script.chmod(0o755)
        command_spec = {
            "id": "empty",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {"value": "$.missing"},
                "required_fields": ["value"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result is None

    def test_execute_command_accepts_empty_required_list(self, tmp_path):
        """Codex P2: an empty list/dict is a legitimate result from a healthy
        backend (e.g. 'no matching sessions found'). The required_fields check
        must only reject missing-or-None, not any falsy value. Otherwise the
        empty-but-valid case gets misclassified as Degraded coverage."""
        script = tmp_path / "empty_valid.sh"
        script.write_text(
            "#!/usr/bin/env bash\n"
            "echo '{\"matches\": [], \"status_summary\": {}, \"flag\": false}'\n"
        )
        script.chmod(0o755)
        command_spec = {
            "id": "empty-valid",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {
                    "matches": "$.matches",
                    "status_summary": "$.status_summary",
                    "flag": "$.flag",
                },
                "required_fields": ["matches", "status_summary", "flag"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result == {"matches": [], "status_summary": {}, "flag": False}

    def test_execute_command_still_rejects_null_required_field(self, tmp_path):
        """Guard against over-correction: explicit null in the JSON payload for
        a required field must still skip the lane."""
        script = tmp_path / "null_field.sh"
        script.write_text("#!/usr/bin/env bash\necho '{\"matches\": null}'\n")
        script.chmod(0o755)
        command_spec = {
            "id": "null-field",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {"matches": "$.matches"},
                "required_fields": ["matches"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result is None

    def test_execute_command_interpolates_template_env_before_shell(self, tmp_path, monkeypatch):
        """End-to-end: a template input containing {FOO} must be interpolated
        from the environment so the shell actually receives the expanded value
        via {{prompt}} substitution. Codex P1: without this, NotebookLM gets
        asked about the literal string '{WARMUP_TASK_TEXT}'. The {{prompt}} is
        used bare (no surrounding shell quotes) — substitute_shell_template
        shlex-quotes the value for us."""
        monkeypatch.setenv("FOO", "resolved-value")
        # echo the substituted prompt so we can observe what the shell saw
        script = tmp_path / "echo_backend.sh"
        script.write_text("#!/usr/bin/env bash\nprintf '{\"seen\":\"%s\"}\\n' \"$1\"\n")
        script.chmod(0o755)
        command_spec = {
            "id": "tmpl-interp",
            "shell": f"bash {script} {{{{prompt}}}}",
            "inputs": {
                "prompt": {"from": "template", "template_id": "p"},
            },
            "output": {
                "format": "json",
                "extract": {"seen": "$.seen"},
                "required_fields": ["seen"],
            },
        }
        result = executor.execute_command(
            command_spec,
            config=None,
            templates={"p": "hello {FOO}"},
            env_overrides={},
            timeout_s=5,
        )
        assert result == {"seen": "hello resolved-value"}

    def test_execute_command_safely_handles_shell_dangerous_prompt(self, tmp_path, monkeypatch):
        """End-to-end shell-escaping: a task text containing dollar-substitution
        and quotes must land in the backend as its literal string — not as a
        command executed on the host. Uses a Python-backed fake-backend so
        JSON escaping is handled by python -c rather than by the shell."""
        dangerous = 'Fix "auth": $(printf MARKER-FIRED)'
        monkeypatch.setenv("WARMUP_TASK_TEXT", dangerous)
        script = tmp_path / "echo_backend.py"
        script.write_text(
            "#!/usr/bin/env python3\nimport json, sys\n"
            "print(json.dumps({'seen': sys.argv[1]}))\n"
        )
        script.chmod(0o755)
        command_spec = {
            "id": "tmpl-dangerous",
            "shell": f"python3 {script} {{{{prompt}}}}",
            "inputs": {"prompt": {"from": "template", "template_id": "p"}},
            "output": {
                "format": "json",
                "extract": {"seen": "$.seen"},
                "required_fields": ["seen"],
            },
        }
        result = executor.execute_command(
            command_spec,
            config=None,
            templates={"p": "{WARMUP_TASK_TEXT}"},
            env_overrides={},
            timeout_s=5,
        )
        assert result == {"seen": dangerous}

    def test_execute_command_precondition_skip(self, tmp_path):
        pre = tmp_path / "pre.sh"
        pre.write_text("#!/usr/bin/env bash\nexit 1\n")
        pre.chmod(0o755)
        shell_script = tmp_path / "main.sh"
        shell_script.write_text("#!/usr/bin/env bash\necho '{\"x\":\"should-not-run\"}'\n")
        shell_script.chmod(0o755)
        command_spec = {
            "id": "skipped",
            "shell": f"bash {shell_script}",
            "inputs": {},
            "preconditions": [{"id": "no", "script": str(pre)}],
            "output": {"format": "json", "extract": {"x": "$.x"}, "required_fields": ["x"]},
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result is None


class TestNotebookLMContractInputs:
    """The notebooklm-vault warmup_contract's notebook_id input must include a
    json_path_template so executor.resolve_input (lookup: single_or_default_for_warmup)
    can resolve the notebook ID. Codex P1 finding: without json_path_template the
    executor raises KeyError silently, and the entire NotebookLM lane returns None
    → Degraded coverage on every warm-up."""

    _NOTEBOOKLM_SKILL = _P(__file__).parent.parent.parent / "notebooklm-vault" / "SKILL.md"

    def _load(self):
        c = contract.load_contract(self._NOTEBOOKLM_SKILL)
        assert c is not None, "notebooklm-vault warmup_contract missing or invalid"
        return c

    def test_every_notebook_id_input_has_json_path_template(self):
        c = self._load()
        for cmd in c["commands"]:
            nb = cmd.get("inputs", {}).get("notebook_id")
            assert nb is not None, f"command {cmd['id']!r} missing notebook_id input"
            assert nb.get("lookup") == "single_or_default_for_warmup", (
                f"command {cmd['id']!r} notebook_id lookup changed; test assumption broken"
            )
            assert "json_path_template" in nb, (
                f"command {cmd['id']!r} notebook_id input is missing json_path_template; "
                f"executor._lookup_single_or_default will KeyError at runtime"
            )

    def test_notebook_id_resolves_for_single_notebook_config(self):
        c = self._load()
        sample_config = {"notebooks": {"main": {"id": "nb-single-123"}}}
        for cmd in c["commands"]:
            nb_spec = cmd["inputs"]["notebook_id"]
            resolved = executor.resolve_input(
                nb_spec, config=sample_config, templates={}
            )
            assert resolved == "nb-single-123", (
                f"command {cmd['id']!r} notebook_id did not resolve to the notebook's id "
                f"(got {resolved!r})"
            )

    def test_notebook_id_resolves_for_multi_notebook_with_default(self):
        c = self._load()
        sample_config = {
            "notebooks": {"main": {"id": "nb-main"}, "infra": {"id": "nb-infra"}},
            "default_for_warmup": "infra",
        }
        for cmd in c["commands"]:
            nb_spec = cmd["inputs"]["notebook_id"]
            resolved = executor.resolve_input(
                nb_spec, config=sample_config, templates={}
            )
            assert resolved == "nb-infra"


class TestChainFrontmatterYamlSafety:
    """Step 6.5 frontmatter template must produce valid YAML even when the
    task_summary contains YAML-significant characters like ':', '#', '|', or
    quotes (codex P1 finding). This guards against cold-cache fallback caused
    by unparseable .ark-workflow/current-chain.md."""

    _SKILL_MD_PATH = _P(__file__).parent.parent.parent / "ark-workflow" / "SKILL.md"

    @staticmethod
    def _render_chain_frontmatter(task_summary: str) -> str:
        """Render a chain frontmatter body matching the shape /ark-workflow
        Step 6.5 should emit after the fix (block scalar |-)."""
        return (
            "scenario: greenfield\n"
            "weight: 2\n"
            "batch: false\n"
            "created: 2026-04-13T12:00:00Z\n"
            "chain_id: 01HABC\n"
            "task_text: |\n"
            "  raw task text here\n"
            "task_summary: |-\n"
            f"  {task_summary}\n"
            "task_normalized: foo bar\n"
            "task_hash: abc123\n"
            "handoff_marker: null\n"
            "handoff_instructions: null\n"
        )

    def test_risky_summaries_roundtrip(self):
        import yaml
        risky = [
            "Fix auth: rate limit",
            "# starts with hash",
            "pipe | in middle",
            'quote "inside" it',
            "apostrophe 'inside' it",
            "yes: maybe",
            "trailing-colon:",
            "bracket {inside} it",
        ]
        for summary in risky:
            body = self._render_chain_frontmatter(summary)
            parsed = yaml.safe_load(body)
            assert parsed is not None, f"YAML parse returned None for summary={summary!r}\nbody:\n{body}"
            assert parsed["task_summary"].strip() == summary, (
                f"Roundtrip failed: expected {summary!r}, got {parsed['task_summary']!r}\nbody:\n{body}"
            )

    def test_skill_md_template_uses_safe_form(self):
        """Guardrail: SKILL.md's Step 6.5 template must use a YAML-safe form for
        task_summary. Plain scalar `task_summary: {TASK_SUMMARY}` is NOT safe —
        it breaks as soon as the task text contains a colon, pound, pipe, or
        quote. Accept block scalar (|, |-, >, >-) or quoted forms."""
        import re
        text = self._SKILL_MD_PATH.read_text()
        m = re.search(r"###\s+Step\s+6\.5.*?(?=\n###\s|\Z)", text, re.DOTALL | re.IGNORECASE)
        assert m is not None, "Step 6.5 section not found in ark-workflow/SKILL.md"
        section = m.group(0)
        summary_match = re.search(r"^\s*task_summary:(.*?)$", section, re.MULTILINE)
        assert summary_match is not None, "task_summary line not found in Step 6.5"
        value_part = summary_match.group(1).strip()
        safe = (
            value_part in ("|", "|-", ">", ">-")
            or value_part.startswith('"')
            or value_part.startswith("'")
        )
        assert safe, (
            f"task_summary in Step 6.5 uses unsafe plain scalar form: {value_part!r}. "
            f"Use block scalar `|-` (followed by indented value on the next line) "
            f"or a quoted scalar to protect against YAML-significant characters "
            f"in the task text."
        )
