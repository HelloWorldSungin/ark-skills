"""Integration tests: ensure_python_set_entry is wired into the convergence engine.

These tests close the gap the unit tests (test_op_ensure_python_set_entry.py) missed:
the op works in isolation, but the engine must actually *enumerate* its
target-profile section (`ensured_python_set_entries`) for it to run in practice.

Two tiers
---------
Tier A — enumeration: load the REAL target-profile.yaml and assert
         _iter_target_profile_entries yields the graphify-exclude-generated entry
         with op == "ensure_python_set_entry" and file == "vault/_meta/generate-index.py"
         (gates unset → yielded unconditionally per the backward-compat note).

Tier B — full Phase-2 drive: build a fixture project with a real
         vault/_meta/generate-index.py containing EXCLUDE_DIRS = {"_meta"}, run
         migrate.py end-to-end, and assert "generated" is added to the set.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared helpers / sys.path shim (matches the other test files in this suite)
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent  # worktree root / skills root

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Tier A — enumeration test against the REAL target-profile.yaml
# ---------------------------------------------------------------------------

def test_real_profile_yields_python_set_entry(monkeypatch):
    """The shipped target-profile.yaml must surface the graphify-exclude-generated op.

    Runs with gate-flag env vars UNSET → entries are yielded unconditionally
    (backward-compat), so the only_if_centralized_vault gate does not suppress it.
    """
    monkeypatch.delenv("ARK_HAS_OMC", raising=False)
    monkeypatch.delenv("ARK_CENTRALIZED_VAULT", raising=False)

    import migrate as _migrate
    importlib.reload(_migrate)  # pick up unset env in _read_gate_flags

    profile = _migrate._load_target_profile(_SKILLS_ROOT)
    entries = list(_migrate._iter_target_profile_entries(profile))

    matches = [
        e for e in entries
        if e.get("op") == "ensure_python_set_entry"
        and e.get("file") == "vault/_meta/generate-index.py"
    ]
    assert matches, (
        "Expected an entry with op=ensure_python_set_entry and "
        "file=vault/_meta/generate-index.py to be yielded by "
        "_iter_target_profile_entries. Got ops: "
        + ", ".join(sorted({e.get("op", "<none>") for e in entries}))
    )
    entry = matches[0]
    assert entry.get("set_name") == "EXCLUDE_DIRS"
    assert entry.get("entry") == "generated"


def test_real_profile_path_validation_covers_python_set_entry():
    """_validate_target_profile_paths must accept the entry's file path without error.

    A non-traversing relative path under project_root must pass cleanly (no SystemExit).
    """
    import migrate as _migrate
    importlib.reload(_migrate)

    profile = _migrate._load_target_profile(_SKILLS_ROOT)
    # Should not raise / SystemExit for the in-repo relative path.
    _migrate._validate_target_profile_paths(_SKILLS_ROOT, profile)


# ---------------------------------------------------------------------------
# Tier B — full Phase-2 drive against a fixture project
# ---------------------------------------------------------------------------

def _run_engine(project_root: Path) -> subprocess.CompletedProcess:
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
    )


def test_convergence_adds_generated_to_exclude_dirs(tmp_path: Path):
    """End-to-end: a project with EXCLUDE_DIRS={"_meta"} gains "generated" after convergence."""
    # Build minimal fixture project with the target file present.
    gen_index = tmp_path / "vault" / "_meta" / "generate-index.py"
    gen_index.parent.mkdir(parents=True)
    gen_index.write_text(
        '#!/usr/bin/env python3\nEXCLUDE_DIRS = {"_meta"}\n\nprint("index")\n',
        encoding="utf-8",
    )

    result = _run_engine(tmp_path)
    assert result.returncode == 0, (
        f"Engine exited {result.returncode}:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    after = gen_index.read_text(encoding="utf-8")
    assert '"generated"' in after, (
        f"'generated' not added to EXCLUDE_DIRS after convergence:\n{after}\n"
        f"--- engine stdout ---\n{result.stdout}"
    )
    assert 'EXCLUDE_DIRS = {"_meta", "generated"}' in after, (
        f"EXCLUDE_DIRS not updated as expected:\n{after}"
    )
    # Surrounding content preserved.
    assert "#!/usr/bin/env python3" in after
    assert 'print("index")' in after


def test_convergence_python_set_entry_idempotent(tmp_path: Path):
    """A second convergence run does not modify an already-converged file."""
    gen_index = tmp_path / "vault" / "_meta" / "generate-index.py"
    gen_index.parent.mkdir(parents=True)
    gen_index.write_text(
        'EXCLUDE_DIRS = {"_meta", "generated"}\n', encoding="utf-8"
    )
    before = gen_index.read_bytes()

    result = _run_engine(tmp_path)
    assert result.returncode == 0, (
        f"Engine exited {result.returncode}:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert gen_index.read_bytes() == before, (
        "generate-index.py changed on an already-converged file — not idempotent"
    )
