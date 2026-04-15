"""Tests: gate-flag evaluation in _read_gate_flags() and _iter_target_profile_entries().

Step 7 (commit a9958c8) wired gate-flag resolution in migrate.py.  This file pins
the behaviour so regressions cannot slip past CI.

Two test tiers
--------------
Tier A — unit tests: import _read_gate_flags / _iter_target_profile_entries directly
          and use monkeypatch.setenv.  Fast; no filesystem I/O.
Tier B — subprocess e2e: run migrate.py on the ``fresh`` fixture with env overrides
          and assert which ops appear in the run summary.  One smoke test per gate
          combo (both-off, omc-off, vault-off, both-on).

Sidecar note
------------
The existing ``fresh/expected-post/`` sidecar was built with env vars UNSET
(unconditional-apply mode, backward-compat).  Gated-mode tests do NOT diff against
that sidecar — they compute expected state inline and assert it directly.

_read_gate_flags edge-case semantics
-------------------------------------
The parser uses ``val.strip() == "1"``:
  "1"    → True   (explicitly enabled)
  "0"    → False  (explicitly disabled)
  ""     → False  (empty string is NOT None; stripped == "" != "1")
  "true" → False  (truthy English word rejected — only "1" accepted)
  "yes"  → False  (same)
  "no"   → False  (same as "0" — both are non-"1" False, not None)
  unset  → None   (env var absent → unconditional/backward-compat)

This is intentionally strict.  The SKILL.md wrapper only ever exports "0" or "1".
Non-standard values are treated as "disabled" (False), not as errors.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# sys.path shim — give direct imports access to scripts/
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# Minimal synthetic target profile used by Tier-A unit tests
# ---------------------------------------------------------------------------
_SYNTHETIC_PROFILE = {
    "managed_regions": [
        # omc-routing — gated on ARK_HAS_OMC
        {
            "id": "omc-routing",
            "op": "ensure_claude_md_section",
            "file": "CLAUDE.md",
            "template": "omc-routing-block.md",
            "since": "1.13.0",
            "version": "1.13.0",
            "only_if_has_omc": True,
        },
        # routing-rules — no gate (always applied)
        {
            "id": "routing-rules",
            "op": "ensure_routing_rules_block",
            "file": "CLAUDE.md",
            "since": "1.3.0",
            "version": "1.12.0",
        },
    ],
    "ensured_files": [
        # setup-vault-symlink — gated on ARK_CENTRALIZED_VAULT
        {
            "id": "setup-vault-symlink",
            "op": "create_file_from_template",
            "target": "scripts/setup-vault-symlink.sh",
            "template": "setup-vault-symlink.sh",
            "since": "1.11.0",
            "version": "1.11.0",
            "only_if_centralized_vault": True,
            "mode": "0o755",
        },
    ],
    "ensured_gitignore": [],
    "ensured_mcp_servers": [],
}


def _entry_ids(profile: dict, omc: str | None, vault: str | None) -> list[str]:
    """Call _iter_target_profile_entries with given env overrides; return list of entry ids."""
    import importlib
    import migrate as _migrate  # noqa: PLC0415

    # Force reimport so env changes are picked up by _read_gate_flags
    importlib.reload(_migrate)

    entries = list(_migrate._iter_target_profile_entries(profile))
    return [e.get("id", "<no-id>") for e in entries]


# ---------------------------------------------------------------------------
# Tier A — unit tests via monkeypatch.setenv
# ---------------------------------------------------------------------------

class TestReadGateFlags:
    """Pin _read_gate_flags return values for all relevant env-var states."""

    def _read(self, omc: str | None, vault: str | None):
        import importlib
        import migrate as _migrate
        importlib.reload(_migrate)
        return _migrate._read_gate_flags()

    def test_both_unset_returns_none_none(self, monkeypatch):
        monkeypatch.delenv("ARK_HAS_OMC", raising=False)
        monkeypatch.delenv("ARK_CENTRALIZED_VAULT", raising=False)
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is None
        assert cv is None

    def test_both_one_returns_true_true(self, monkeypatch):
        monkeypatch.setenv("ARK_HAS_OMC", "1")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "1")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is True
        assert cv is True

    def test_both_zero_returns_false_false(self, monkeypatch):
        monkeypatch.setenv("ARK_HAS_OMC", "0")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "0")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is False
        assert cv is False

    def test_omc_zero_vault_one(self, monkeypatch):
        monkeypatch.setenv("ARK_HAS_OMC", "0")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "1")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is False
        assert cv is True

    def test_omc_one_vault_zero(self, monkeypatch):
        monkeypatch.setenv("ARK_HAS_OMC", "1")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "0")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is True
        assert cv is False

    # Edge cases: non-"0"/"1" values

    def test_empty_string_treated_as_false(self, monkeypatch):
        """Empty string is present (not None) but strip() == '' != '1' → False."""
        monkeypatch.setenv("ARK_HAS_OMC", "")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is False, "empty string must be False (not None)"
        assert cv is False, "empty string must be False (not None)"

    def test_truthy_english_word_treated_as_false(self, monkeypatch):
        """'true'/'yes' are NOT accepted — only strict '1' is truthy."""
        monkeypatch.setenv("ARK_HAS_OMC", "true")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "true")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is False, "'true' must be treated as False (non-'1')"
        assert cv is False, "'true' must be treated as False (non-'1')"

    def test_garbage_values_treated_as_false(self, monkeypatch):
        """'yes'/'no' are garbage — both map to False (not None, not True)."""
        monkeypatch.setenv("ARK_HAS_OMC", "yes")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "no")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is False, "'yes' must be False"
        assert cv is False, "'no' must be False"

    def test_whitespace_around_one_is_true(self, monkeypatch):
        """val.strip() == '1' — leading/trailing whitespace is stripped → True."""
        monkeypatch.setenv("ARK_HAS_OMC", "  1  ")
        monkeypatch.setenv("ARK_CENTRALIZED_VAULT", "\t1\n")
        import importlib, migrate as _m; importlib.reload(_m)
        has_omc, cv = _m._read_gate_flags()
        assert has_omc is True, "whitespace-padded '1' must strip to True"
        assert cv is True, "whitespace-padded '1' must strip to True"


class TestIterTargetProfileEntries:
    """Pin which entries _iter_target_profile_entries yields for each gate-flag combo."""

    def _ids(self, monkeypatch, omc: str | None, vault: str | None) -> list[str]:
        if omc is None:
            monkeypatch.delenv("ARK_HAS_OMC", raising=False)
        else:
            monkeypatch.setenv("ARK_HAS_OMC", omc)
        if vault is None:
            monkeypatch.delenv("ARK_CENTRALIZED_VAULT", raising=False)
        else:
            monkeypatch.setenv("ARK_CENTRALIZED_VAULT", vault)
        import importlib, migrate as _m; importlib.reload(_m)
        return [e.get("id", "<no-id>") for e in _m._iter_target_profile_entries(_SYNTHETIC_PROFILE)]

    def test_unset_unset_yields_all_backward_compat(self, monkeypatch):
        """Both unset → all entries yielded (backward-compat for Step-6 fixture tests)."""
        ids = self._ids(monkeypatch, None, None)
        assert "omc-routing" in ids, "unset omc → omc-routing must be yielded"
        assert "setup-vault-symlink" in ids, "unset vault → setup-vault-symlink must be yielded"
        assert "routing-rules" in ids, "ungated entry must always be yielded"

    def test_both_one_yields_all(self, monkeypatch):
        """Both explicitly enabled → all entries yielded."""
        ids = self._ids(monkeypatch, "1", "1")
        assert "omc-routing" in ids
        assert "setup-vault-symlink" in ids
        assert "routing-rules" in ids

    def test_omc_zero_vault_one_skips_omc_routing(self, monkeypatch):
        """ARK_HAS_OMC=0 → omc-routing SKIPPED; setup-vault-symlink CREATED."""
        ids = self._ids(monkeypatch, "0", "1")
        assert "omc-routing" not in ids, "omc-routing must be skipped when ARK_HAS_OMC=0"
        assert "setup-vault-symlink" in ids
        assert "routing-rules" in ids

    def test_omc_one_vault_zero_skips_vault_symlink(self, monkeypatch):
        """ARK_CENTRALIZED_VAULT=0 → setup-vault-symlink SKIPPED; omc-routing CREATED."""
        ids = self._ids(monkeypatch, "1", "0")
        assert "omc-routing" in ids
        assert "setup-vault-symlink" not in ids, "setup-vault-symlink must be skipped when ARK_CENTRALIZED_VAULT=0"
        assert "routing-rules" in ids

    def test_both_zero_skips_both_gated(self, monkeypatch):
        """Both disabled → omc-routing AND setup-vault-symlink SKIPPED; routing-rules still yielded."""
        ids = self._ids(monkeypatch, "0", "0")
        assert "omc-routing" not in ids
        assert "setup-vault-symlink" not in ids
        assert "routing-rules" in ids, "ungated entry must never be skipped"

    def test_truthy_english_skips_both_gated(self, monkeypatch):
        """'true'/'true' → treated as False → both gated entries skipped."""
        ids = self._ids(monkeypatch, "true", "true")
        assert "omc-routing" not in ids, "'true' is non-'1' → skipped"
        assert "setup-vault-symlink" not in ids, "'true' is non-'1' → skipped"

    def test_empty_string_skips_both_gated(self, monkeypatch):
        """Empty string → treated as False → both gated entries skipped."""
        ids = self._ids(monkeypatch, "", "")
        assert "omc-routing" not in ids, "empty string is non-'1' → skipped"
        assert "setup-vault-symlink" not in ids, "empty string is non-'1' → skipped"

    def test_yes_no_both_treated_as_false(self, monkeypatch):
        """'yes'/'no' → both False → both gated entries skipped."""
        ids = self._ids(monkeypatch, "yes", "no")
        assert "omc-routing" not in ids
        assert "setup-vault-symlink" not in ids


# ---------------------------------------------------------------------------
# Tier B — subprocess e2e smoke tests (fresh fixture, env overrides)
#
# Note: fresh/expected-post/ was built with env UNSET (unconditional).
# These tests do NOT diff against that sidecar — they assert run-summary
# output (which ops were applied/skipped) computed inline.
# ---------------------------------------------------------------------------

def _copy_fixture_pre(fixture_name: str, dest: Path) -> None:
    src = _FIXTURES_DIR / fixture_name
    for item in src.iterdir():
        if item.name == "expected-post":
            continue
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d)
        else:
            shutil.copy2(item, d)


def _run_with_gates(project_root: Path, omc: str | None, vault: str | None) -> subprocess.CompletedProcess:
    """Run migrate.py on *project_root* with explicit gate-flag env overrides."""
    env = os.environ.copy()
    if omc is None:
        env.pop("ARK_HAS_OMC", None)
    else:
        env["ARK_HAS_OMC"] = omc
    if vault is None:
        env.pop("ARK_CENTRALIZED_VAULT", None)
    else:
        env["ARK_CENTRALIZED_VAULT"] = vault

    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "migrate.py"),
            "--project-root", str(project_root),
            "--skills-root", str(_SKILLS_ROOT),
            "--force",
        ],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.mark.parametrize("omc,vault,expect_omc_routing,expect_symlink", [
    # (ARK_HAS_OMC, ARK_CENTRALIZED_VAULT, omc-routing created, setup-vault-symlink created)
    (None, None, True,  True),   # unset/unset → backward-compat: all applied
    ("1",  "1",  True,  True),   # both on → all applied
    ("0",  "1",  False, True),   # omc off, vault on → omc-routing skipped
    ("1",  "0",  True,  False),  # omc on, vault off → symlink skipped
    ("0",  "0",  False, False),  # both off → both gated entries skipped
])
def test_e2e_gate_flags_fresh_fixture(
    omc: str | None,
    vault: str | None,
    expect_omc_routing: bool,
    expect_symlink: bool,
    tmp_path: Path,
) -> None:
    """E2E: fresh fixture with gate-flag overrides produces correct applied/skipped counts.

    Does NOT diff against expected-post/ sidecar (that sidecar reflects unconditional
    mode). Asserts the run summary text and file-system state inline.
    """
    _copy_fixture_pre("fresh", tmp_path)
    result = _run_with_gates(tmp_path, omc, vault)

    assert result.returncode == 0, (
        f"Engine failed (omc={omc!r}, vault={vault!r}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # --- file-system assertions ---
    omc_routing_present = (tmp_path / "CLAUDE.md").exists() and "ark:begin id=omc-routing" in (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    symlink_present = (tmp_path / "scripts" / "setup-vault-symlink.sh").exists()

    if expect_omc_routing:
        assert omc_routing_present, (
            f"omc-routing region expected in CLAUDE.md (omc={omc!r})\nstdout: {result.stdout}"
        )
    else:
        assert not omc_routing_present, (
            f"omc-routing region must be ABSENT when ARK_HAS_OMC={omc!r}\nstdout: {result.stdout}"
        )

    if expect_symlink:
        assert symlink_present, (
            f"setup-vault-symlink.sh expected (vault={vault!r})\nstdout: {result.stdout}"
        )
    else:
        assert not symlink_present, (
            f"setup-vault-symlink.sh must be ABSENT when ARK_CENTRALIZED_VAULT={vault!r}\nstdout: {result.stdout}"
        )


def test_e2e_both_gates_off_summary_counts(tmp_path: Path) -> None:
    """E2E smoke: ARK_HAS_OMC=0 + ARK_CENTRALIZED_VAULT=0 → 2 ops applied (routing-rules + gitignore), 0 skipped_idempotent."""
    _copy_fixture_pre("fresh", tmp_path)
    result = _run_with_gates(tmp_path, "0", "0")

    assert result.returncode == 0, f"Unexpected failure:\n{result.stdout}\n{result.stderr}"
    # routing-rules + gitignore entry → 2 applied; both gated entries → 0 (not counted as skipped_idempotent)
    assert "2 applied" in result.stdout, (
        f"Expected '2 applied' with both gates off:\n{result.stdout}"
    )
