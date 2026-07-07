"""Shared helpers for the destructive migration ops (issue #34).

Both ``okf_conversion`` and ``gh_issues_adoption`` need to:
  * shell out to a vault tool / the ``gh`` CLI and capture the result,
  * freeze legacy tracker trees with an idempotent banner,
  * bootstrap the GitHub-Issues label taxonomy.

These live here so the two ops share one implementation (and one place to fix
bugs) rather than drifting apart.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Label taxonomy — mirrors docs/playbooks/github-issues-task-management.md.
# (name, color, description).  bug/wontfix ship as GitHub defaults but are
# created idempotently anyway so a fresh repo gets them too.
TRIAGE_LABELS = [
    ("needs-triage", "e99695", "Maintainer needs to evaluate this issue"),
    ("needs-info", "fbca04", "Waiting on reporter for more information"),
    ("ready-for-agent", "0e8a16", "Fully specified, ready for an AFK agent"),
    ("ready-for-human", "1d76db", "Requires human implementation"),
    ("wontfix", "ffffff", "Will not be actioned"),
]
TYPE_LABELS = [
    ("epic", "3e4b9e", "Parent issue with a task-list body linking child issues"),
    ("story", "5319e7", "User-facing unit of work, child of an epic"),
    ("task", "bfdadc", "Small technical work item"),
    ("bug", "d73a4a", "Something isn't working"),
]
PRIORITY_LABELS = [
    ("P1", "b60205", "Urgent — do first"),
    ("P2", "d93f0b", "Normal priority"),
    ("P3", "f9d0c4", "Low priority / someday"),
]
COMPONENT_COLOR = "c5def5"


def utc_date() -> str:
    """Return today's UTC date as ``YYYY-MM-DD`` (for freeze banners)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def run_tool(script_path: Path, extra_args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a bundle python tool with the current interpreter; capture output.

    The OKF tools resolve their own ``VAULT_ROOT`` from ``__file__``, so running
    the *project's* copy (under ``vault/_meta/okf/``) targets the project vault.
    """
    return subprocess.run(
        [sys.executable, str(script_path), *extra_args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=120,
    )


def gh(argv: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Invoke the ``gh`` CLI with *argv*; capture output. Never raises on rc!=0."""
    return subprocess.run(
        ["gh", *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def gh_authenticated() -> bool:
    """True if ``gh auth status`` exits 0 (a usable, authenticated gh CLI)."""
    try:
        return gh(["auth", "status"]).returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def bootstrap_labels(component_labels: list[str] | None = None) -> None:
    """Create the label taxonomy idempotently via ``gh label create``.

    ``gh label create`` fails when the label already exists — that non-zero exit
    is the idempotency signal, so we ignore it. Component labels come from the
    project's target-profile entry (``component_labels:``); each downstream repo
    supplies its own vocabulary.
    """
    families = TRIAGE_LABELS + TYPE_LABELS + PRIORITY_LABELS
    for name, color, desc in families:
        gh(["label", "create", name, "--color", color, "--description", desc])
    for name in component_labels or []:
        gh(["label", "create", name, "--color", COMPONENT_COLOR,
            "--description", f"{name} component"])


def freeze_legacy_trackers(vault: Path) -> list[Path]:
    """Prepend a FROZEN banner to each legacy tracker tree's entry doc.

    Freezes ``Session-Logs/`` and ``TaskNotes/`` under *vault* (playbook:
    "Freeze, don't migrate"). No file moves; history stays put. Idempotent — a
    tree already carrying a FROZEN banner is left untouched.

    The banner deliberately uses an inline-code path, not a markdown link, so it
    does not register as a broken relative link under ``okf_lint.py``.
    """
    frozen: list[Path] = []
    banner = (
        f"> **FROZEN {utc_date()}** — active tracking moved to GitHub Issues "
        f"(`docs/agents/issue-tracker.md`). This tree is read-only legacy history.\n\n"
    )
    for tree_name in ("Session-Logs", "TaskNotes"):
        tree = vault / tree_name
        if not tree.is_dir():
            continue
        entry = tree / "index.md"
        existing = entry.read_text(encoding="utf-8") if entry.exists() else ""
        if "FROZEN" in existing:
            continue
        entry.write_text(banner + existing, encoding="utf-8")
        frozen.append(entry)
    return frozen
