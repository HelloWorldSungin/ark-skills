#!/usr/bin/env python3
"""Minimal T4 scan of a vault's index.md for /ark-context-warmup.

Scores candidate pages by query-token overlap with the index line. Returns top-N as JSON.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _parse_index_line(line: str):
    """Return (title, summary, path) or None if the line is not a match entry."""
    # Expected patterns:
    #   - [[PageName]] — ...summary...
    #   - [[PageName]] — tags: x, y — summary
    m = re.match(r"^\s*[-*]\s*\[\[([^\]]+)\]\]\s*[—-]\s*(.*)$", line)
    if not m:
        return None
    return {"title": m.group(1).strip(), "summary": m.group(2).strip(), "path": m.group(1).strip() + ".md"}


def scan(vault_path: Path, query: str, top_n: int) -> dict:
    index = vault_path / "index.md"
    if not index.exists():
        raise FileNotFoundError(f"no index.md in {vault_path}")
    query_tokens = _tokens(query)
    candidates = []
    for line in index.read_text().splitlines():
        parsed = _parse_index_line(line)
        if not parsed:
            continue
        line_tokens = _tokens(parsed["title"] + " " + parsed["summary"])
        overlap = len(query_tokens & line_tokens)
        if overlap > 0:
            candidates.append((overlap, parsed))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return {"tier": "T4", "matches": [c[1] for c in candidates[:top_n]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="emit JSON (default)")
    args = parser.parse_args()
    try:
        result = scan(args.vault, args.query, args.top)
    except FileNotFoundError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
