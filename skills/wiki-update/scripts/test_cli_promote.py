"""End-to-end tests for cli_promote.py. Focus: transactional delete gate,
exit codes, regen output surfacing — review findings C2 / H7 / H8 / M6."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
SCRIPT = HERE / "cli_promote.py"
SHARED = HERE.resolve().parents[1] / "shared" / "python"


def _copy_fixture(tmp_path, name="mixed"):
    src = HERE / "fixtures" / name
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)
    return dst


def _write_session_log(repo, slug="S001-test"):
    logs = repo / "vault" / "Session-Logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / f"{slug}.md"
    path.write_text(
        "---\ntitle: Session 1\nsession: S001\ntype: session-log\n"
        "created: 2026-04-20\n---\n\n## Issues & Discoveries\n\n"
    )
    return path


def _run(argv, cwd=None):
    env = {**os.environ, "PYTHONPATH": str(SHARED)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *argv],
        capture_output=True, text=True, env=env, cwd=str(cwd) if cwd else None,
    )


def _base_args(repo, extra=()):
    return [
        "--repo-root", str(repo),
        "--omc-wiki-dir", ".omc/wiki",
        "--project-docs-path", str(repo / "vault"),
        "--tasknotes-path", str(repo / "vault" / "TaskNotes"),
        "--task-prefix", "Arktest-",
        "--session-slug", "S001-test",
        *extra,
    ]


def _install_noop_regen(repo):
    """Install a _meta/generate-index.py that exits 0 and writes a non-empty index.md."""
    meta = repo / "vault" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    script = meta / "generate-index.py"
    script.write_text(
        "import pathlib\n"
        "pathlib.Path('index.md').write_text('# index\\n')\n"
    )


def _install_failing_regen(repo, rc=2):
    meta = repo / "vault" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    script = meta / "generate-index.py"
    script.write_text(f"import sys\nprint('regen boom', file=sys.stderr)\nsys.exit({rc})\n")


def test_cli_promote_happy_path_deletes_omc_sources(tmp_path):
    """C2 happy: promote → regen rc=0 → finalize_deletes fires."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    _install_noop_regen(repo)
    r = _run(_base_args(repo))
    assert r.returncode == 0, r.stdout + r.stderr
    # arch-high OMC source should now be gone (deleted after regen)
    assert not (repo / ".omc" / "wiki" / "arch-high.md").exists()
    # Vault destination present
    assert list((repo / "vault" / "Architecture").glob("*.md"))
    assert "Deleted from OMC:" in r.stdout


def test_cli_promote_blocks_deletes_when_regen_script_missing_C2(tmp_path):
    """C2: missing _meta/generate-index.py must NOT satisfy the regen gate —
    deletes must be blocked and OMC sources preserved."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    # No _meta/generate-index.py installed — script missing.
    r = _run(_base_args(repo))
    assert r.returncode == 1, r.stdout + r.stderr
    # OMC sources still present
    assert (repo / ".omc" / "wiki" / "arch-high.md").exists()
    assert "SKIPPED (script missing)" in r.stdout or "script missing" in r.stdout
    assert "BLOCKED" in r.stdout


def test_cli_promote_allow_missing_index_script_opts_out(tmp_path):
    """M6/C2: operators without an index script must be able to opt out
    via --allow-missing-index-script."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    r = _run(_base_args(repo, ["--allow-missing-index-script"]))
    assert r.returncode == 0, r.stdout + r.stderr
    # With opt-in, OMC source is deleted
    assert not (repo / ".omc" / "wiki" / "arch-high.md").exists()


def test_cli_promote_blocks_deletes_when_regen_fails_C2(tmp_path):
    """C2: regen exits non-zero → deletes blocked; OMC sources preserved."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    _install_failing_regen(repo, rc=7)
    r = _run(_base_args(repo))
    assert r.returncode == 1, r.stdout + r.stderr
    assert (repo / ".omc" / "wiki" / "arch-high.md").exists()
    assert "exit code: 7" in r.stdout or "exited 7" in r.stdout
    # H8: regen stderr must be surfaced on failure
    assert "regen boom" in r.stdout


def test_cli_promote_nonzero_exit_when_promote_errors_H7(tmp_path):
    """H7: cli_promote.main() must return non-zero when promote() records errors."""
    repo = _copy_fixture(tmp_path)
    _write_session_log(repo)
    _install_noop_regen(repo)
    # Trigger a malformed-frontmatter error: frontmatter parses as a list, not a mapping.
    bad = repo / ".omc" / "wiki" / "malformed.md"
    bad.write_text("---\n- item1\n- item2\n---\n\nbody\n")
    r = _run(_base_args(repo))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Errors (promotion)" in r.stdout
    # Deletes must be blocked when promote errors are present
    assert "BLOCKED" in r.stdout
    # Other OMC files must still be present (delete phase skipped)
    assert (repo / ".omc" / "wiki" / "arch-high.md").exists()


def test_cli_promote_blocks_deletes_when_required_paths_removed_C2(tmp_path):
    """C2 end-to-end: the finalize_deletes require=written_paths gate fires
    when a written vault path vanishes between promote() and finalize_deletes.
    Sanity path — require=[] would silently pass, which is the bug we fixed."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    # Install a regen script that DELETES the just-written vault page before exiting 0.
    # This simulates a scenario where the regen step destabilizes the write.
    meta = repo / "vault" / "_meta"
    meta.mkdir(parents=True)
    (meta / "generate-index.py").write_text(
        "import pathlib, shutil\n"
        "arch = pathlib.Path('Architecture')\n"
        "if arch.is_dir():\n"
        "    shutil.rmtree(arch)\n"
        "pathlib.Path('index.md').write_text('# index\\n')\n"
    )
    r = _run(_base_args(repo))
    # Required path was wiped → deletes must be blocked; exit 1.
    assert r.returncode == 1, r.stdout + r.stderr
    assert "Deleted from OMC: 0" in r.stdout
    # OMC source still present because finalize_deletes refused to unlink
    assert (repo / ".omc" / "wiki" / "arch-high.md").exists()


def test_cli_promote_reports_written_paths_count_C2(tmp_path):
    """C2 surface: report should surface Vault paths written: N for auditability."""
    repo = _copy_fixture(tmp_path)
    (repo / "vault" / "Architecture").mkdir(parents=True, exist_ok=True)
    _write_session_log(repo)
    _install_noop_regen(repo)
    r = _run(_base_args(repo))
    assert "Vault paths written:" in r.stdout
