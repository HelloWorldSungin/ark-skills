"""Op: gh_issues_adoption — adopt GitHub Issues task management (#34).

Wraps the GitHub-Issues playbook
(docs/playbooks/github-issues-task-management.md) as an idempotent,
dry-run-first destructive migration:

  1. precondition: ``gh auth status`` (an authenticated gh CLI)
  2. bootstrap the label taxonomy (triage + type + priority + component)
  3. write ``docs/agents/{issue-tracker,triage-labels,domain}.md`` (create-if-missing;
     ensure the ark proactive-behavior section on an existing issue-tracker.md)
  4. rewrite the CLAUDE.md Task Management row -> GitHub Issues
     (overwrite-on-drift with a ``.bak`` + ``.meta.json`` provenance backup)
  5. freeze ``Session-Logs/`` + ``TaskNotes/`` with banners

Idempotency: a project whose ``docs/agents/issue-tracker.md`` exists and whose
CLAUDE.md Task Management row already points at GitHub Issues is already adopted
-> ``skipped_idempotent``. Missing/broken ``gh`` -> ``failed`` (surfaced to the
operator; adoption cannot proceed without it).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops import DestructiveOp, register_destructive_op  # noqa: E402
from ops._migration_helpers import (  # noqa: E402
    bootstrap_labels,
    freeze_legacy_trackers,
    gh_authenticated,
)
from state import write_backup_with_sidecar  # noqa: E402

_DOCS_AGENTS = ("issue-tracker.md", "triage-labels.md", "domain.md")
_ARK_SECTION_MARKER = "## ark-skills additions"

_TASK_ROW = (
    "| **Task Management** | GitHub Issues via `gh` CLI — see "
    "`docs/agents/issue-tracker.md` for the label families and `gh` crib |"
)
_TASK_ROW_RE = re.compile(r"^\|\s*\*\*Task Management\*\*\s*\|")


class _ClaudeMdResult:
    __slots__ = ("changed", "backup")

    def __init__(self, changed: bool, backup: str | None):
        self.changed = changed
        self.backup = backup


@register_destructive_op("gh_issues_adoption")
class GHIssuesAdoptionOp(DestructiveOp):
    """Adopt GitHub Issues as the project's task-management system."""

    OP_TYPE = "gh_issues_adoption"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _is_adopted(self, project_root: Path) -> bool:
        tracker = project_root / "docs" / "agents" / "issue-tracker.md"
        claude = project_root / "CLAUDE.md"
        if not tracker.exists() or not claude.exists():
            return False
        return "GitHub Issues" in claude.read_text(encoding="utf-8")

    def _templates_dir(self, skills_root: Path) -> Path:
        # docs/agents templates live under assets/ (not templates/), keeping the
        # flat templates/ dir — referenced by target-profile `template:` fields —
        # free of subdirectories.
        return skills_root / "skills" / "ark-update" / "assets" / "docs-agents"

    def _ensure_docs(self, project_root: Path, skills_root: Path, backups_dir: Path) -> list[str]:
        backups: list[str] = []
        tmpl_dir = self._templates_dir(skills_root)
        docs_dir = project_root / "docs" / "agents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        for name in _DOCS_AGENTS:
            dest = docs_dir / name
            template = (tmpl_dir / name).read_text(encoding="utf-8")
            if not dest.exists():
                dest.write_text(template, encoding="utf-8")
                continue
            # Existing issue-tracker.md: ensure the ark proactive-behavior
            # section is present; append it (with a backup) if it's missing.
            if name == "issue-tracker.md":
                existing = dest.read_text(encoding="utf-8")
                if _ARK_SECTION_MARKER not in existing:
                    info = write_backup_with_sidecar(backups_dir, dest)
                    backups.append(str(info["bak_path"]))
                    section = template.split(_ARK_SECTION_MARKER, 1)[1]
                    merged = existing.rstrip("\n") + "\n\n" + _ARK_SECTION_MARKER + section
                    dest.write_text(merged, encoding="utf-8")
        return backups

    def _rewrite_claude_row(self, project_root: Path, backups_dir: Path) -> _ClaudeMdResult:
        claude = project_root / "CLAUDE.md"
        if not claude.exists():
            claude.write_text(
                "# Project\n\n## Project Configuration\n\n"
                "| Topic | Location |\n|-------|----------|\n"
                f"{_TASK_ROW}\n",
                encoding="utf-8",
            )
            return _ClaudeMdResult(changed=True, backup=None)

        text = claude.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)

        # Case A: a Task Management row exists.
        for i, line in enumerate(lines):
            if _TASK_ROW_RE.match(line):
                if "GitHub Issues" in line:
                    return _ClaudeMdResult(changed=False, backup=None)  # already adopted
                info = write_backup_with_sidecar(backups_dir, claude)
                ending = "\n" if line.endswith("\n") else ""
                lines[i] = _TASK_ROW + ending
                claude.write_text("".join(lines), encoding="utf-8")
                return _ClaudeMdResult(changed=True, backup=str(info["bak_path"]))

        # Case B: no row — insert it. Back up first (file existed).
        info = write_backup_with_sidecar(backups_dir, claude)
        insert_at = self._project_config_table_end(lines)
        if insert_at is not None:
            lines.insert(insert_at, _TASK_ROW + "\n")
            claude.write_text("".join(lines), encoding="utf-8")
        else:
            addition = (
                "\n## Project Configuration\n\n"
                "| Topic | Location |\n|-------|----------|\n"
                f"{_TASK_ROW}\n"
            )
            claude.write_text(text.rstrip("\n") + "\n" + addition, encoding="utf-8")
        return _ClaudeMdResult(changed=True, backup=str(info["bak_path"]))

    @staticmethod
    def _project_config_table_end(lines: list[str]) -> int | None:
        """Index just past the last contiguous ``|`` table row under the
        Project Configuration heading, or None if there is no such table."""
        heading = None
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("## project configuration"):
                heading = i
                break
        if heading is None:
            return None
        # Find the table block after the heading.
        i = heading + 1
        last_table = None
        while i < len(lines):
            if lines[i].lstrip().startswith("|"):
                last_table = i
            elif last_table is not None and lines[i].strip() == "":
                break
            i += 1
        return (last_table + 1) if last_table is not None else None

    # ------------------------------------------------------------------
    # dry_run
    # ------------------------------------------------------------------

    def dry_run(self, project_root: Path, args: dict) -> dict:
        op_id = args.get("id", "gh-issues-adoption")

        def report(**kw) -> dict:
            base = {
                "op_id": op_id,
                "op_type": self.OP_TYPE,
                "would_apply": False,
                "would_skip_idempotent": False,
                "would_overwrite_drift": False,
                "would_fail_precondition": False,
                "drift_summary": None,
            }
            base.update(kw)
            return base

        if self._is_adopted(project_root):
            return report(would_skip_idempotent=True)
        if not gh_authenticated():
            return report(would_fail_precondition=True,
                          drift_summary="gh CLI not available or not authenticated")
        return report(would_apply=True)

    # ------------------------------------------------------------------
    # apply
    # ------------------------------------------------------------------

    def apply(self, project_root: Path, args: dict) -> dict:
        op_id = args.get("id", "gh-issues-adoption")
        skills_root = Path(args["skills_root"])
        backups_dir = project_root / ".ark" / "backups"

        def result(status: str, **kw) -> dict:
            base = {
                "op_id": op_id,
                "op_type": self.OP_TYPE,
                "status": status,
                "backups": [],
                "error": None,
            }
            base.update(kw)
            return base

        if self._is_adopted(project_root):
            return result("skipped_idempotent")
        if not gh_authenticated():
            return result("failed",
                          error="gh CLI not available or not authenticated; "
                                "run `gh auth login` before adopting GitHub Issues.")

        backups: list[str] = []
        # 2. label taxonomy (idempotent).
        bootstrap_labels(args.get("component_labels") or [])
        # 3. convention docs.
        backups += self._ensure_docs(project_root, skills_root, backups_dir)
        # 4. CLAUDE.md task row.
        claude_res = self._rewrite_claude_row(project_root, backups_dir)
        if claude_res.backup:
            backups.append(claude_res.backup)
        # 5. freeze legacy trackers under the vault (if a vault exists).
        vault = self.safe_path(project_root, args.get("vault", "vault"))
        if vault.is_dir():
            freeze_legacy_trackers(vault)

        return result("applied", backups=backups)
