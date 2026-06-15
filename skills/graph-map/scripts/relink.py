"""Rewrite relative markdown links after the graphify export is relocated.

Resolves each relative link target against the OLD export location, then rewrites
it relative to the NEW location so source back-links keep resolving.

Usage: python3 relink.py --old-dir <path> --new-dir <path>
Operates in place over *.md under --new-dir. Wikilinks ([[name]]) are untouched.
"""
import argparse
import os
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)]+)(\))")


def _is_relative_path(target: str) -> bool:
    t = target.strip()
    if not t or t.startswith("#"):
        return False
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", t):  # scheme://
        return False
    if t.startswith("mailto:") or t.startswith("/"):
        return False
    return True


def rewrite_link(target: str, old_page_dir: Path, new_page_dir: Path):
    """Return rewritten link, or None if it should be left unchanged."""
    if not _is_relative_path(target):
        return None
    # split off any #anchor / ?query
    frag = ""
    core = target
    for sep in ("#", "?"):
        if sep in core:
            idx = core.index(sep)
            frag = core[idx:] + frag
            core = core[:idx]
    if not core:
        return None
    resolved = (old_page_dir / core).resolve()
    new_rel = os.path.relpath(resolved, start=new_page_dir.resolve())
    return new_rel + frag


def process_file(page: Path, old_dir: Path, new_dir: Path) -> int:
    page = Path(page)
    # the page's directory relative to new_dir mirrors its position under old_dir
    rel_dir = page.parent.resolve().relative_to(new_dir.resolve())
    old_page_dir = (old_dir / rel_dir)
    changed = 0

    def repl(m):
        nonlocal changed
        new_target = rewrite_link(m.group(2), old_page_dir, page.parent)
        if new_target is None or new_target == m.group(2):
            return m.group(0)
        changed += 1
        return m.group(1) + new_target + m.group(3)

    text = page.read_text(errors="ignore")
    new_text = LINK_RE.sub(repl, text)
    if changed:
        page.write_text(new_text)
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-dir", required=True)
    ap.add_argument("--new-dir", required=True)
    args = ap.parse_args(argv)
    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    total = 0
    for md in sorted(new_dir.rglob("*.md")):
        total += process_file(md, old_dir, new_dir)
    print(f"relink: rewrote {total} link(s) under {new_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
