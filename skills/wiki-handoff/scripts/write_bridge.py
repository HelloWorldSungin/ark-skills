"""/wiki-handoff — writes a session bridge page to .omc/wiki/.

Invoked from /ark-workflow Step 6.5 action branch before /compact or /clear.
Uses shared omc_page module. PyYAML required (plugin-standard dep).

Exit codes:
  0 — bridge written OR .omc/wiki dir absent (silent no-op per SKILL contract)
  2 — schema rejection; caller must NOT proceed to /compact|/clear
  3 — too many filename collisions; caller must NOT proceed either
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, write_page  # noqa: E402


# Full-string generic placeholders. Matched case-insensitively after stripping
# leading/trailing whitespace and trailing punctuation.
GENERIC_PATTERNS = {
    "continue task", "continue", "continuing", "continuing task",
    "tbd", "todo", "to-do", "to do",
    "keep going", "keep at it", "proceed",
    "none", "n/a", "na", "nothing",
    "work in progress", "wip",
    "more work", "more to do",
}

# Token-prefix family. Any input whose first token (after normalization) starts
# with one of these is treated as filler regardless of the rest.
FILLER_TOKEN_PREFIXES = (
    "tbd", "todo", "wip", "fixme", "xxx",
)

MIN_LENGTH = 20

# Minimum number of distinct word tokens (alnum only, >=2 chars). Filters strings
# that pass MIN_LENGTH via repetition (e.g., "todo todo todo todo todo").
MIN_DISTINCT_TOKENS = 3

# Scenario must be a DNS-like slug: starts alnum, then alnum / hyphen, <=32 chars.
SCENARIO_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,31}$")


def _normalize(s: str) -> str:
    """Lower-case; strip whitespace and common trailing punctuation."""
    return s.strip().lower().rstrip(".!?,:;'\"`-")


def _validate(field_name: str, value: str) -> str | None:
    s = (value or "").strip()
    if not s:
        return f"{field_name} must be non-empty"
    norm = _normalize(s)
    if norm in GENERIC_PATTERNS:
        return f"{field_name} is generic placeholder ({s!r}) — provide specific detail"
    first_tok = norm.split()[0] if norm.split() else ""
    if any(first_tok.startswith(p) for p in FILLER_TOKEN_PREFIXES):
        return f"{field_name} starts with a filler token ({first_tok!r}) — provide specific detail"
    if len(s) < MIN_LENGTH:
        return f"{field_name} is too short (<{MIN_LENGTH} chars) — provide specific detail"
    distinct = {t for t in re.findall(r"[A-Za-z0-9]{2,}", s.lower())}
    if len(distinct) < MIN_DISTINCT_TOKENS:
        return (
            f"{field_name} has too few distinct words "
            f"({len(distinct)}<{MIN_DISTINCT_TOKENS}) — provide specific detail"
        )
    return None


def _validate_scenario(value: str) -> str | None:
    s = (value or "").strip()
    if not s:
        return "scenario must be non-empty"
    if not SCENARIO_RE.match(s):
        return (
            f"scenario {s!r} is not a DNS-like slug "
            f"(lowercase alnum + hyphen, <=32 chars, must start alnum)"
        )
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

    # Structural field validation. Scenario uses a charset slug check;
    # the free-text fields use _validate (emptiness + generic-filler + distinct-token rules).
    scenario_err = _validate_scenario(args.scenario)
    if scenario_err:
        print(f"wiki-handoff: {scenario_err}.", file=sys.stderr)
        return 2

    validated_fields: list[tuple[str, str]] = [
        ("task_text", args.task_text),
        ("open_threads", args.open_threads),
        ("next_steps", args.next_steps),
    ]
    # done_summary is optional (default=""); only validate when non-empty.
    if args.done_summary.strip():
        validated_fields.append(("done_summary", args.done_summary))

    for name, val in validated_fields:
        err = _validate(name, val)
        if err:
            print(
                f"wiki-handoff: {err}. Re-invoke with specific file paths / decision points.",
                file=sys.stderr,
            )
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
