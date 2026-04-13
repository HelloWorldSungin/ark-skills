#!/usr/bin/env python3
"""TaskNotes search + status summary for /ark-context-warmup.

Reads TaskNote markdown files directly from {tasknotes_path}/Tasks/ (recursively).
Falls back from MCP; the parent skill decides when to invoke this vs MCP.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def _extract_component(task_normalized: str) -> str:
    """Very conservative component extractor.
    Looks for the first token ≥4 chars — a reasonable proxy for component name.
    Spec D3 says: first '[A-Z][a-zA-Z0-9]+' run in task_summary OR None. But task_normalized
    is already lowercased; so we use its first meaningful token instead.
    """
    for tok in task_normalized.split():
        if len(tok) >= 4:
            return tok
    return ""


def _token_overlap(a: str, b: str) -> float:
    toks_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    toks_b = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not toks_a or not toks_b:
        return 0.0
    shared = toks_a & toks_b
    smaller = min(len(toks_a), len(toks_b))
    return len(shared) / smaller


def search(tasknotes_path: Path, prefix: str, task_normalized: str, scenario: str) -> dict:
    tasks_dir = tasknotes_path / "Tasks"
    results = []
    status_counter = Counter()
    component = _extract_component(task_normalized)
    if not tasks_dir.is_dir():
        return {
            "matches": [],
            "status_summary": dict(status_counter),
            "extracted_component": component,
        }
    # rglob: recurse into nested directories (Tasks/Bug/, Tasks/Story/, etc.)
    for md in tasks_dir.rglob(f"{prefix}*.md"):
        fm = _parse_frontmatter(md)
        status = fm.get("status", "unknown")
        status_counter[status] += 1
        if status == "done":
            continue
        # Match heuristics
        matched_field = None
        title_overlap = _token_overlap(task_normalized, fm.get("title", ""))
        if component and fm.get("component", "").lower() == component:
            matched_field = "component"
        elif title_overlap >= 0.60:
            matched_field = f"title_overlap={title_overlap:.2f}"
        if matched_field:
            results.append({
                "id": md.stem,
                "title": fm.get("title", ""),
                "status": status,
                "component": fm.get("component", ""),
                "work-type": fm.get("work-type", ""),
                "matched_field": matched_field,
                "title_overlap": title_overlap,
            })
    return {
        "matches": results,
        "status_summary": dict(status_counter),
        "extracted_component": component,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasknotes", required=True, type=Path)
    parser.add_argument("--prefix", required=True, help="Task prefix including trailing dash, e.g. Arkskill-")
    parser.add_argument("--task-normalized", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out = search(args.tasknotes, args.prefix, args.task_normalized, args.scenario)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
