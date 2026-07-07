"""Tests for ops/gh_issues_adoption.py — the gh-issues-adoption migration op (#34).

Uses a fake ``gh`` shim on PATH so no real GitHub calls happen. The shim
records every invocation to a log file so label bootstrap can be asserted.

Scenarios:
  * fresh project + working gh  -> writes docs/agents + CLAUDE.md row, "applied"
  * second run                  -> "skipped_idempotent", byte-identical tree
  * gh not authenticated        -> "failed" (apply) / would_fail_precondition (dry_run)
  * pre-existing stale CLAUDE row-> replaced with a backup + sidecar
  * dry_run writes nothing
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ops import DESTRUCTIVE_OP_REGISTRY  # noqa: E402
from ops.gh_issues_adoption import GHIssuesAdoptionOp  # noqa: E402

_SKILLS_ROOT = Path(__file__).resolve().parents[3]


def _op() -> GHIssuesAdoptionOp:
    return GHIssuesAdoptionOp()


def _args(**overrides) -> dict:
    base = {
        "id": "gh-issues-adoption",
        "op": "gh_issues_adoption",
        "since": "2.0.0",
        "component_labels": ["consultant", "conventions"],
        "skills_root": str(_SKILLS_ROOT),
    }
    base.update(overrides)
    return base


def _install_fake_gh(tmp_path: Path, monkeypatch, authed: bool = True) -> Path:
    """Put a fake `gh` on PATH. Logs argv to gh-calls.log; exit code per `authed`."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    log = tmp_path / "gh-calls.log"
    auth_rc = 0 if authed else 1
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{log}"\n'
        'if [ "$1" = "auth" ]; then\n'
        f"  exit {auth_rc}\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    os.chmod(gh, 0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return log


def _make_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".ark" / "backups").mkdir(parents=True)
    return project_root


def _snapshot(root: Path, exclude=(".ark",)) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and not any(part in exclude for part in f.relative_to(root).parts):
            snap[str(f.relative_to(root))] = f.read_bytes()
    return snap


def test_apply_fresh_project(tmp_path, monkeypatch):
    log = _install_fake_gh(tmp_path, monkeypatch, authed=True)
    project_root = _make_project(tmp_path)

    result = _op().apply(project_root, _args())
    assert result["status"] == "applied", result

    # docs/agents scaffolding written.
    for name in ("issue-tracker.md", "triage-labels.md", "domain.md"):
        assert (project_root / "docs" / "agents" / name).exists(), name
    # CLAUDE.md Task Management row points at GitHub Issues.
    claude = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Task Management" in claude
    assert "GitHub Issues" in claude
    # Labels were bootstrapped via gh.
    calls = log.read_text(encoding="utf-8")
    assert "label create epic" in calls
    assert "label create needs-triage" in calls
    assert "label create consultant" in calls  # component label from args


def test_apply_idempotent_second_run(tmp_path, monkeypatch):
    _install_fake_gh(tmp_path, monkeypatch, authed=True)
    project_root = _make_project(tmp_path)

    first = _op().apply(project_root, _args())
    assert first["status"] == "applied"
    snap1 = _snapshot(project_root)

    second = _op().apply(project_root, _args())
    assert second["status"] == "skipped_idempotent", second
    snap2 = _snapshot(project_root)
    assert snap1 == snap2, "Second gh-issues-adoption run mutated the tree"


def test_apply_fails_without_gh_auth(tmp_path, monkeypatch):
    _install_fake_gh(tmp_path, monkeypatch, authed=False)
    project_root = _make_project(tmp_path)

    result = _op().apply(project_root, _args())
    assert result["status"] == "failed", result
    assert "gh" in (result.get("error") or "").lower()
    # No convention files written on a failed precondition.
    assert not (project_root / "docs" / "agents").exists()


def test_apply_rewrites_stale_claude_row(tmp_path, monkeypatch):
    _install_fake_gh(tmp_path, monkeypatch, authed=True)
    project_root = _make_project(tmp_path)
    stale = (
        "# Project\n\n"
        "## Project Configuration\n\n"
        "| Topic | Location |\n"
        "|-------|----------|\n"
        "| **Task Management** | TaskNotes MCP + Linear sync |\n"
    )
    (project_root / "CLAUDE.md").write_text(stale, encoding="utf-8")

    result = _op().apply(project_root, _args())
    assert result["status"] == "applied", result

    claude = (project_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "GitHub Issues" in claude
    assert "TaskNotes MCP + Linear sync" not in claude
    # A backup with a sidecar was recorded.
    baks = list((project_root / ".ark" / "backups").glob("CLAUDE.md.*.bak"))
    assert baks, "expected a CLAUDE.md backup"
    assert Path(str(baks[0]) + ".meta.json").exists()
    assert result.get("backups"), "backups list should be non-empty"


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    _install_fake_gh(tmp_path, monkeypatch, authed=True)
    project_root = _make_project(tmp_path)
    snap_before = _snapshot(project_root)

    report = _op().dry_run(project_root, _args())
    assert report["would_apply"] is True
    snap_after = _snapshot(project_root)
    assert snap_before == snap_after, "dry_run mutated the tree"


def test_dry_run_fails_without_gh(tmp_path, monkeypatch):
    _install_fake_gh(tmp_path, monkeypatch, authed=False)
    project_root = _make_project(tmp_path)
    report = _op().dry_run(project_root, _args())
    assert report["would_apply"] is False
    assert report["would_fail_precondition"] is True


def test_op_registered():
    assert "gh_issues_adoption" in DESTRUCTIVE_OP_REGISTRY
    assert DESTRUCTIVE_OP_REGISTRY["gh_issues_adoption"] is GHIssuesAdoptionOp
