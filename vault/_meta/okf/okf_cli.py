#!/usr/bin/env python3
"""okf_cli.py — dependency-free navigation for the OKF vault.

Agent-facing: list / search / read without any MCP server or index service.

Usage:
    python3 _meta/okf/okf_cli.py list [--type TYPE] [--dir DIR]
    python3 _meta/okf/okf_cli.py search TERM [TERM ...] [--body]
    python3 _meta/okf/okf_cli.py read PAGE          # rel path or basename

`search` matches title, tags, description, and path (AND across terms);
`--body` also greps page bodies. `read` accepts a vault-relative path
(`Trading-Signal-AI/Models/TFT.md`) or a bare page name (`TFT`).
Stdlib only.
"""

import argparse
import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
EXCLUDE_DIRS = {
    ".obsidian", ".git", ".claude-plugin", ".github", ".notebooklm",
    "generated",
}
FM_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*(\n|$)", re.DOTALL)


def iter_pages():
    for root, dirs, files in os.walk(VAULT_ROOT, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if fname.endswith(".md"):
                yield Path(root) / fname


def page_meta(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    fm = m.group(1) if m else ""

    def field(key):
        km = re.search(rf"^{key}:[ \t]*(.*)$", fm, re.MULTILINE)
        return km.group(1).strip().strip("\"'") if km else ""

    return {
        "rel": path.relative_to(VAULT_ROOT).as_posix(),
        "type": field("type") or field("task-type"),
        "title": field("title") or path.stem,
        "tags": field("tags"),
        "description": field("description"),
        "body": text[m.end():] if m else text,
    }


def cmd_list(args):
    for path in iter_pages():
        meta = page_meta(path)
        if args.type and meta["type"].lower() != args.type.lower():
            continue
        if args.dir and not meta["rel"].startswith(args.dir.rstrip("/") + "/"):
            continue
        print(f"{meta['rel']}\t{meta['type']}\t{meta['title']}")


def cmd_search(args):
    terms = [t.lower() for t in args.terms]
    hits = 0
    for path in iter_pages():
        meta = page_meta(path)
        haystack = " ".join(
            [meta["rel"], meta["title"], meta["tags"], meta["description"]]
        ).lower()
        if args.body:
            haystack += " " + meta["body"].lower()
        if all(t in haystack for t in terms):
            hits += 1
            description = meta["description"][:160]
            print(f"{meta['rel']}\t{description}")
    if not hits:
        print("no matches", file=sys.stderr)
        return 1
    return 0


def cmd_read(args):
    name = args.page
    direct = VAULT_ROOT / name
    if direct.is_file():
        print(direct.read_text(encoding="utf-8", errors="replace"))
        return 0
    wanted = name.lower().removesuffix(".md")
    matches = [p for p in iter_pages() if p.stem.lower() == wanted]
    if len(matches) == 1:
        print(matches[0].read_text(encoding="utf-8", errors="replace"))
        return 0
    if matches:
        print("ambiguous page name:", file=sys.stderr)
        for p in matches:
            print(f"  {p.relative_to(VAULT_ROOT).as_posix()}", file=sys.stderr)
        return 1
    print(f"not found: {name}", file=sys.stderr)
    return 1


def main():
    ap = argparse.ArgumentParser(prog="okf_cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--type")
    p_list.add_argument("--dir")

    p_search = sub.add_parser("search")
    p_search.add_argument("terms", nargs="+")
    p_search.add_argument("--body", action="store_true")

    p_read = sub.add_parser("read")
    p_read.add_argument("page")

    args = ap.parse_args()
    return {"list": cmd_list, "search": cmd_search, "read": cmd_read}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
