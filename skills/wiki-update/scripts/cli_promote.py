"""CLI entry point for /wiki-update Step 3.5. Orchestrates promote() →
index regen → finalize_deletes() so deletes only fire after ALL of:
  1. promote() recorded zero errors,
  2. the destination vault paths promote() wrote still exist & are non-empty,
  3. _meta/generate-index.py exited 0 (and actually ran — a missing script
     does NOT satisfy this gate)."""
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


# Sentinel returned by _run_index_regen when the regen script is missing.
REGEN_SCRIPT_MISSING = -1


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
        return REGEN_SCRIPT_MISSING, f"(no _meta/generate-index.py at {script})"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(vault_path), capture_output=True, text=True, timeout=120,
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
    p.add_argument(
        "--allow-missing-index-script",
        action="store_true",
        help=(
            "Treat a missing _meta/generate-index.py as acceptable and proceed "
            "to deletes. Without this flag, missing script blocks deletes."
        ),
    )
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

    # Run index regen BEFORE deletes (transactional requirement).
    rc, regen_out = _run_index_regen(project_docs)

    # Transactional delete gate. ALL conditions must hold:
    #   1. promote() recorded zero errors
    #   2. index regen either ran and returned 0, OR was explicitly opted-out via flag
    #   3. every written path promote() reports still exists and is non-empty (finalize_deletes checks this)
    regen_ok = rc == 0 or (rc == REGEN_SCRIPT_MISSING and args.allow_missing_index_script)
    deletes_done = 0
    delete_errors: list[str] = []
    delete_blocked_reason = ""
    if report.errors:
        delete_blocked_reason = f"promote() recorded {len(report.errors)} error(s)"
    elif not regen_ok:
        if rc == REGEN_SCRIPT_MISSING:
            delete_blocked_reason = (
                "index regen script missing — pass --allow-missing-index-script "
                "to opt out of the regen gate"
            )
        else:
            delete_blocked_reason = f"index regen exited {rc}"
    elif not report.pending_deletes:
        delete_blocked_reason = "no pending deletes"
    else:
        deletes_done, delete_errors = finalize_deletes(
            report.pending_deletes, require=report.written_paths,
        )
        if deletes_done == 0 and delete_errors:
            delete_blocked_reason = delete_errors[0]

    print("OMC Promotion Report")
    print("====================")
    print(f"Auto-promoted (high confidence): {report.auto_promoted}")
    print(f"Merged into existing vault pages: {report.merged_existing}")
    print(f"Staged for review (medium): {report.staged} pages → Staging/ + {report.tasknotes_created} TaskNotes")
    print(f"Skipped (filtered/untouched-seed/pre-session): {report.skipped_filtered}")
    print(f"Session-authored seed edits promoted: {report.session_edits_promoted}")
    print(f"Troubleshooting cross-links created: {report.troubleshooting_created}")
    print(f"Vault paths written: {len(report.written_paths)}")
    print(f"Pending deletes: {len(report.pending_deletes)}")
    if rc == REGEN_SCRIPT_MISSING:
        print("Index regen: SKIPPED (script missing)")
    else:
        print(f"Index regen exit code: {rc}")
    if rc != 0 and regen_out.strip():
        # Surface regen stderr/stdout to the user only on failure or missing-script.
        print("Index regen output:")
        for line in regen_out.splitlines():
            print(f"  {line}")
    print(f"Deleted from OMC: {deletes_done}")
    if delete_blocked_reason:
        print(f"Delete status: BLOCKED — {delete_blocked_reason}")
    if report.errors:
        print(f"Errors (promotion): {len(report.errors)}")
        for e in report.errors:
            print(f"  - {e}")
    if delete_errors:
        print(f"Errors (delete phase): {len(delete_errors)}")
        for e in delete_errors:
            print(f"  - {e}")

    # Exit code: 0 only when everything went cleanly.
    if report.errors or delete_errors or (not regen_ok and report.pending_deletes):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
