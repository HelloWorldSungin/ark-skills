"""End-to-end: migrate.py dispatching target-profile pending_migrations (#34).

The two v2.0.0 conventions (okf-conversion, gh-issues-adoption) are declared in
target-profile.yaml under ``pending_migrations``. They run ONLY when the
operator opts in with ``--run-pending-migrations`` (env ARK_RUN_PENDING_MIGRATIONS=1),
so the default engine path — and the 220-test baseline — is untouched.

Terminal state is a per-project marker ``.ark/pending-migrations.json`` (the
plugin-shared target-profile.yaml cannot hold per-project state).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parents[2]


def _install_fake_gh(tmp_path: Path) -> dict:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "auth" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    os.chmod(gh, 0o755)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return env


def _make_non_okf_vault(project_root: Path) -> None:
    vault = project_root / "vault"
    (vault / "Research").mkdir(parents=True)
    (vault / "Session-Logs").mkdir(parents=True)
    (vault / "00-Home.md").write_text(
        "---\ntype: moc\ndescription: Home\n---\n\n# Home\n\nSee [[Alpha-Study]].\n",
        encoding="utf-8",
    )
    (vault / "Research" / "Alpha-Study.md").write_text(
        "---\ntype: research\ndescription: Alpha\n---\n\n# Alpha\n\nBack [[00-Home]].\n",
        encoding="utf-8",
    )
    (vault / "Session-Logs" / "S001-Kickoff.md").write_text(
        "---\ntype: session\ndescription: Kickoff\n---\n\n# S001\n\nWork.\n",
        encoding="utf-8",
    )


def _run(project_root: Path, env: dict, run_pending: bool, dry: bool = False) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "migrate.py"),
        "--project-root", str(project_root),
        "--skills-root", str(_SKILLS_ROOT),
        "--force",
    ]
    if run_pending:
        cmd.append("--run-pending-migrations")
    if dry:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def _snapshot(root: Path, exclude=(".ark",)) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and not any(p in exclude for p in f.relative_to(root).parts):
            snap[str(f.relative_to(root))] = f.read_bytes()
    return snap


def test_default_run_does_not_touch_pending(tmp_path):
    """Without --run-pending-migrations the engine must not run the two migrations.

    (The engine's ordinary Phase-2 convergence — e.g. setup-vault-symlink — still
    runs; this test asserts only that no pending-migration artifact is produced.)
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    _make_non_okf_vault(project_root)
    env = _install_fake_gh(tmp_path)

    result = _run(project_root, env, run_pending=False)
    assert result.returncode == 0, result.stderr

    # No okf-conversion: vault stays non-OKF (no _meta tooling, no okf_version).
    assert not (project_root / "vault" / "_meta" / "okf").exists()
    assert not (project_root / "vault" / "index.md").exists()
    # No gh-issues-adoption: no convention docs.
    assert not (project_root / "docs" / "agents").exists()
    # No per-project pending marker written.
    assert not (project_root / ".ark" / "pending-migrations.json").exists()


def test_run_pending_applies_both_and_records_marker(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _make_non_okf_vault(project_root)
    env = _install_fake_gh(tmp_path)

    result = _run(project_root, env, run_pending=True)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    # Both migrations produced their artifacts.
    assert (project_root / "vault" / "index.md").exists()
    assert "okf_version" in (project_root / "vault" / "index.md").read_text()
    assert (project_root / "docs" / "agents" / "issue-tracker.md").exists()

    marker = project_root / ".ark" / "pending-migrations.json"
    assert marker.exists()
    data = json.loads(marker.read_text())
    assert data["okf-conversion"]["status"] == "applied"
    assert data["gh-issues-adoption"]["status"] == "applied"


def test_run_pending_second_run_idempotent(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _make_non_okf_vault(project_root)
    env = _install_fake_gh(tmp_path)

    first = _run(project_root, env, run_pending=True)
    assert first.returncode == 0, first.stderr
    snap1 = _snapshot(project_root)

    second = _run(project_root, env, run_pending=True)
    assert second.returncode == 0, second.stderr
    snap2 = _snapshot(project_root)

    assert snap1 == snap2, "second --run-pending-migrations run mutated the tree"


def test_run_pending_dry_run_writes_nothing(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _make_non_okf_vault(project_root)
    env = _install_fake_gh(tmp_path)
    snap_before = _snapshot(project_root)

    result = _run(project_root, env, run_pending=True, dry=True)
    assert result.returncode == 0, result.stderr
    snap_after = _snapshot(project_root)
    assert snap_before == snap_after, "dry-run mutated the tree"
    # The plan mentions the pending migrations.
    assert "okf-conversion" in result.stdout or "okf_conversion" in result.stdout
