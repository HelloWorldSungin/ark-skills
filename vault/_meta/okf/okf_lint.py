#!/usr/bin/env python3
"""okf_lint.py — OKF v0.1 conformance + link-integrity lint for the vault.

ERRORS (exit 1):
  * unparseable / missing YAML frontmatter on a non-reserved .md (spec §9.1)
  * missing or empty `type` (spec §9.2)
  * broken relative markdown link (target file does not exist)
  * frontmatter on a non-root index.md (spec §11)

WARNINGS (exit 0):
  * leftover [[wikilinks]] in note bodies (dangling targets are tolerated by
    spec §5.3 — they represent not-yet-written knowledge — but new pages
    should use markdown links)
  * missing `description` (OKF navigation payload)

Usage:  python3 _meta/okf/okf_lint.py [--quiet]
Stdlib only. Wired as the vault's pre-push gate (see _meta/githooks/pre-push).
"""

import argparse
import os
import re
import sys
import urllib.parse
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
EXCLUDE_DIRS = {
    ".obsidian", ".git", ".claude-plugin", ".github", ".notebooklm",
    "generated",
}
RESERVED = {"index.md", "log.md"}

FM_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*(\n|$)", re.DOTALL)
MD_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)")
IMG_LINK_RE = re.compile(r"\!\[[^\]]*\]\(([^)\s]+)\)")
WIKILINK_RE = re.compile(r"!?\[\[[^\[\]]+?\]\]")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def iter_md():
    for root, dirs, files in os.walk(VAULT_ROOT, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if fname.endswith(".md"):
                yield Path(root) / fname


def body_lines(text):
    """Yield body lines outside code fences, with inline code stripped."""
    m = FM_RE.match(text)
    body = text[m.end():] if m else text
    in_fence = False
    marker = None
    for line in body.split("\n"):
        fm = FENCE_RE.match(line)
        if fm:
            if not in_fence:
                in_fence, marker = True, fm.group(1)
            elif fm.group(1) == marker:
                in_fence, marker = False, None
            continue
        if not in_fence:
            yield INLINE_CODE_RE.sub("", line)


def is_external(href):
    return re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="print final count line only")
    args = ap.parse_args()

    errors, warnings = [], []

    for path in iter_md():
        rel = path.relative_to(VAULT_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = FM_RE.match(text)

        if path.name in RESERVED:
            if fm and rel != "index.md":
                errors.append(f"{rel}: frontmatter not permitted on non-root {path.name} (spec §11)")
            continue

        if not fm:
            errors.append(f"{rel}: missing or unparseable frontmatter (spec §9.1)")
        elif not re.search(r"^(?:type|task-type):[ \t]*\S", fm.group(1), re.MULTILINE):
            errors.append(f"{rel}: missing/empty `type` (spec §9.2)")
        elif not re.search(r"^description:[ \t]*\S", fm.group(1), re.MULTILINE):
            warnings.append(f"{rel}: missing `description`")

        for line in body_lines(text):
            for wl in WIKILINK_RE.findall(line):
                warnings.append(f"{rel}: leftover wikilink {wl}")
            for m in list(MD_LINK_RE.finditer(line)) + list(IMG_LINK_RE.finditer(line)):
                href = m.group(1)
                if is_external(href):
                    continue
                target = urllib.parse.unquote(href.split("#", 1)[0])
                if not target:
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    errors.append(f"{rel}: broken link -> {href}")

    if not args.quiet:
        for e in errors:
            print(f"ERROR   {e}")
        for w in warnings:
            print(f"warning {w}")
    print(f"okf_lint: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
