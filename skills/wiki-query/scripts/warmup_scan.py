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


def _split_wikilink(target: str):
    """Parse the content of [[...]] — may be 'Page' or 'Page.md' or 'Page.md|Display'.
    Returns (title, path)."""
    display = None
    if "|" in target:
        path_part, _, display = target.partition("|")
    else:
        path_part = target
    path_part = path_part.strip()
    display = (display or path_part).strip()
    # Title: prefer display; fall back to filename without .md
    title = display[:-3] if display.endswith(".md") else display
    # Path: ensure .md suffix
    path = path_part if path_part.endswith(".md") else path_part + ".md"
    return title, path


_BULLET_RE = re.compile(r"^\s*[-*]\s*\[\[([^\]]+)\]\]\s*[—-]\s*(.*)$")
# Table row: "| [[Page.md|Title]] | type | summary |"
# Accept 2+ columns after the wikilink. Grab the final column as the summary
# (index generator writes Summary last).
_TABLE_RE = re.compile(r"^\s*\|\s*\[\[([^\]]+)\]\]\s*\|(.+)\|\s*$")


def _parse_index_line(line: str):
    """Return {title, summary, path} or None if the line is not a match entry.
    Supports two index formats:
      - bullet:  - [[Page]] — summary
      - table:   | [[Page.md|Title]] | type | summary |
    Skips markdown table header/separator rows."""
    # Skip markdown table separators like '|---|---|' — these have no wikilinks.
    if line.strip().startswith("|") and "[[" not in line:
        return None
    m = _BULLET_RE.match(line)
    if m:
        title, path = _split_wikilink(m.group(1))
        return {"title": title, "summary": m.group(2).strip(), "path": path}
    m = _TABLE_RE.match(line)
    if m:
        title, path = _split_wikilink(m.group(1))
        cells = [c.strip() for c in m.group(2).split("|")]
        summary = cells[-1] if cells else ""
        return {"title": title, "summary": summary, "path": path}
    return None


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
