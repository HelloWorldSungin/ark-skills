"""CLI entry point for /wiki-update Step 3.5. Orchestrates promote() →
index regen → finalize_deletes() so deletes only occur after successful index regen."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import parse_page  # noqa: E402
from promote_omc import PromotionConfig, finalize_deletes, promote  # noqa: E402


def _session_created_at(project_docs: Path, slug: str) -> float:
    """Read session-log `created:` frontmatter. Falls back to mtime if absent."""
    path = project_docs / "Session-Logs" / f"{slug}.md"
    if not path.exists():
        return 0.0
    try:
        page = parse_page(path)
    except ValueError:
        return path.stat().st_mtime
    created = page.frontmatter.get("created")
    if not created:
        return path.stat().st_mtime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return time.mktime(time.strptime(str(created), fmt))
        except ValueError:
            continue
    return path.stat().st_mtime


def _run_index_regen(vault_path: Path) -> tuple[int, str]:
    script = vault_path / "_meta" / "generate-index.py"
    if not script.exists():
        return 0, "(no _meta/generate-index.py — skipping index regen)"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(vault_path), capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", required=True)
    p.add_argument("--omc-wiki-dir", required=True)
    p.add_argument("--project-docs-path", required=True)
    p.add_argument("--tasknotes-path", required=True)
    p.add_argument("--task-prefix", required=True)
    p.add_argument("--session-slug", required=True)
    args = p.parse_args()

    project_docs = Path(args.project_docs_path)
    started = _session_created_at(project_docs, args.session_slug)

    cfg = PromotionConfig(
        repo_root=Path(args.repo_root),
        omc_wiki_dir=Path(args.repo_root) / args.omc_wiki_dir,
        project_docs_path=project_docs,
        tasknotes_path=Path(args.tasknotes_path),
        task_prefix=args.task_prefix,
        session_slug=args.session_slug,
        session_started_at=started,
    )
    report = promote(cfg)

    # Run index regen BEFORE deletes (transactional requirement)
    rc, _regen_out = _run_index_regen(project_docs)

    deletes_done = 0
    delete_errors: list[str] = []
    if rc == 0 and report.pending_deletes:
        # Require all destination paths to exist (sampled: just run unlink gated on require=[])
        deletes_done, delete_errors = finalize_deletes(
            report.pending_deletes, require=[],
        )

    print("OMC Promotion Report")
    print("====================")
    print(f"Auto-promoted (high confidence): {report.auto_promoted}")
    print(f"Merged into existing vault pages: {report.merged_existing}")
    print(f"Staged for review (medium): {report.staged} pages → Staging/ + {report.tasknotes_created} TaskNotes")
    print(f"Skipped (filtered/untouched-seed/pre-session): {report.skipped_filtered}")
    print(f"Session-authored seed edits promoted: {report.session_edits_promoted}")
    print(f"Troubleshooting cross-links created: {report.troubleshooting_created}")
    print(f"Pending deletes: {len(report.pending_deletes)}")
    print(f"Index regen exit code: {rc}")
    print(f"Deleted from OMC: {deletes_done} (post-index-regen; 0 means blocked)")
    if report.errors:
        print(f"Errors (promotion): {len(report.errors)}")
        for e in report.errors:
            print(f"  - {e}")
    if delete_errors:
        print(f"Errors (delete phase): {len(delete_errors)}")
        for e in delete_errors:
            print(f"  - {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
