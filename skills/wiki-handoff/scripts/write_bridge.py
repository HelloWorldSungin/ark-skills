"""/wiki-handoff — writes a session bridge page to .omc/wiki/.

Invoked from /ark-workflow Step 6.5 action branch before /compact or /clear.
Uses shared omc_page module. PyYAML required (plugin-standard dep).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, write_page  # noqa: E402


GENERIC_PATTERNS = {
    "continue task", "tbd", "todo", "keep going", "none", "n/a", "na",
}
MIN_LENGTH = 20


def _validate(field_name: str, value: str) -> str | None:
    s = (value or "").strip()
    if not s:
        return f"{field_name} must be non-empty"
    if s.lower() in GENERIC_PATTERNS:
        return f"{field_name} is generic placeholder ({s!r}) — provide specific detail"
    if len(s) < MIN_LENGTH:
        return f"{field_name} is too short (<{MIN_LENGTH} chars) — provide specific detail"
    return None


def _timestamp() -> str:
    fixed = os.environ.get("WIKI_HANDOFF_FIXED_STAMP")
    if fixed:
        return fixed
    return time.strftime("%Y-%m-%d-%H%M%S", time.localtime())


def _build_filename(session_id: str, ts: str) -> str:
    sid8 = (session_id or "00000000")[-8:]
    return f"session-bridge-{ts}-{sid8}.md"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chain-id", required=True)
    p.add_argument("--task-text", required=True)
    p.add_argument("--scenario", required=True)
    p.add_argument("--step-index", required=True)
    p.add_argument("--step-count", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--open-threads", required=True)
    p.add_argument("--next-steps", required=True)
    p.add_argument("--notes", default="")
    p.add_argument("--done-summary", default="")
    p.add_argument("--git-diff-stat", default="")
    args = p.parse_args()

    for name, val in (("open_threads", args.open_threads), ("next_steps", args.next_steps)):
        err = _validate(name, val)
        if err:
            print(f"wiki-handoff: {err}. Re-invoke with specific file paths / decision points.", file=sys.stderr)
            return 2

    wiki_dir = Path.cwd() / ".omc" / "wiki"
    if not wiki_dir.is_dir():
        return 0

    ts = _timestamp()
    base_name = _build_filename(args.session_id, ts)
    target = wiki_dir / base_name

    task_summary = args.task_text.strip().splitlines()[0][:80]
    body = f"""# Session Bridge — {task_summary}

## Task
{args.task_text}

## Scenario
{args.scenario} (step {args.step_index}/{args.step_count})

## What was done
{args.git_diff_stat or '(no diff stat provided)'}

{args.done_summary}

## Open threads
{args.open_threads}

## Next steps
{args.next_steps}

## Notes
{args.notes}
"""

    fm = {
        "title": f"Session Bridge — {task_summary}",
        "tags": ["session-bridge", "source-handoff", f"scenario-{args.scenario}"],
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": [args.chain_id, args.session_id],
        "links": [],
        "category": "session-log",
        "confidence": "high",
        "schemaVersion": 1,
        "chain_id": args.chain_id,
    }
    page = OMCPage(frontmatter=fm, body=body)

    attempt = 1
    while attempt <= 10:
        try_path = target if attempt == 1 else wiki_dir / f"{target.stem}-{attempt}.md"
        try:
            write_page(try_path, page, exclusive=True)
            print(str(try_path))
            return 0
        except FileExistsError:
            attempt += 1
    print("wiki-handoff: too many filename collisions", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
