"""Wire each graphify concept note to its origin source file (Video-2 wiring).

graphify's --obsidian notes carry `source_file:` in their YAML frontmatter (a
repo-root-relative path) but expose no navigable link to it. After the notes are
relocated into the vault, this injects a `## Source` link pointing from each note
to the in-repo source file by relative path — a signpost Claude follows, not a
copy. Inter-note navigation already uses wikilinks; this only adds the source.

Usage: python3 wire_source.py --notes-dir <dir> --repo-root <path>
Idempotent: skips notes that already have a `## Source` section or no source_file.
"""
import argparse
import os
import re
import sys
from pathlib import Path

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
SRC_RE = re.compile(r'^source_file:\s*[\'"]?(.*?)[\'"]?\s*$', re.MULTILINE)
LOC_RE = re.compile(r'^location:\s*[\'"]?(.*?)[\'"]?\s*$', re.MULTILINE)
H1_RE = re.compile(r"^# .*$", re.MULTILINE)


def _parse_front(text):
    """Return (source_file, location, frontmatter_end_index) or (None, None, 0)."""
    m = FM_RE.match(text)
    if not m:
        return None, None, 0
    fm = m.group(1)
    s = SRC_RE.search(fm)
    loc = LOC_RE.search(fm)
    return (s.group(1) if s else None), (loc.group(1) if loc else None), m.end()


def wire_note(path: Path, repo_root: Path) -> bool:
    """Inject a `## Source` link into one note. Return True if it was wired."""
    path = Path(path)
    text = path.read_text(errors="ignore")
    if "## Source" in text:
        return False
    src, loc, fm_end = _parse_front(text)
    if not src:
        return False
    target = Path(repo_root) / src
    rel = os.path.relpath(target, start=path.parent)
    label = f"`{src}`" + (f" ({loc})" if loc else "")
    block = f"\n## Source\n\n[{label}]({rel})\n"
    h1 = H1_RE.search(text)
    if h1:
        idx = h1.end()
        new = text[:idx] + "\n" + block + text[idx:]
    else:
        new = text[:fm_end] + block + text[fm_end:]
    path.write_text(new)
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes-dir", required=True)
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args(argv)
    notes_dir = Path(args.notes_dir)
    repo_root = Path(args.repo_root)
    wired = 0
    for md in sorted(notes_dir.rglob("*.md")):
        if wire_note(md, repo_root):
            wired += 1
    print(f"wire_source: wired {wired} note(s) to source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
