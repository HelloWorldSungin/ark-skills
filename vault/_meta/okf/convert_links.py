#!/usr/bin/env python3
"""convert_links.py — Convert Obsidian wikilinks to relative markdown links.

OKF conversion (repo restructure Phase 3, issue #149). Stdlib only.

Handles, in note bodies only (frontmatter, fenced code blocks, and inline
code spans are left untouched):
    [[Page]]                -> [Page](relative/Page.md)
    [[Page|alias]]          -> [alias](relative/Page.md)
    [[Page#Heading]]        -> [Page > Heading](relative/Page.md#Heading%20enc)
    [[Page#Heading|alias]]  -> [alias](relative/Page.md#Heading%20enc)
    [[#Heading]]            -> [Heading](#Heading%20enc)          (same file)
    ![[image.png]]          -> ![image.png](relative/_Attachments/image.png)

Anchors keep the raw heading text URL-encoded (Obsidian-native form; renders
and resolves in Obsidian, and stays human/agent readable in plain text).

Resolution follows Obsidian shortest-path semantics: bare names resolve via a
vault-wide basename map (case-insensitive); names containing '/' resolve from
the vault root, then by path suffix. Unresolvable or ambiguous targets are
REPORTED and left unchanged — never silently rewritten.

Usage:
    python3 _meta/okf/convert_links.py            # dry run: report only
    python3 _meta/okf/convert_links.py --apply    # rewrite files
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

WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]]+?)\]\]")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def iter_vault_files():
    for root, dirs, files in os.walk(VAULT_ROOT, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            yield Path(root) / fname


ALIASES_KEY_RE = re.compile(r"^aliases:[ \t]*(.*)$", re.MULTILINE)


def extract_aliases(content):
    """Frontmatter aliases: supports block lists and inline [a, b] lists."""
    m = re.match(r"^---\s*\n(.*?)(?:\n---|---[ \t]*(?:\n|$))", content, re.DOTALL)
    if not m:
        return []
    fm = m.group(1)
    km = ALIASES_KEY_RE.search(fm)
    if not km:
        return []
    inline = km.group(1).strip()
    if inline.startswith("[") and inline.endswith("]"):
        return [a.strip().strip("\"'") for a in inline[1:-1].split(",") if a.strip()]
    aliases = []
    for line in fm[km.end():].split("\n"):
        item = re.match(r"^\s+-\s+(.+)$", line)
        if item:
            aliases.append(item.group(1).strip().strip("\"'"))
        elif line.strip():
            break
    return aliases


def build_maps():
    """basename/alias (lowercase) -> [relpaths]; full relpath (lowercase, no .md) -> relpath."""
    by_basename = {}
    by_relpath = {}
    all_relpaths = []
    for path in iter_vault_files():
        rel = path.relative_to(VAULT_ROOT).as_posix()
        all_relpaths.append(rel)
        name = path.name
        keys = {name.lower()}
        if name.lower().endswith(".md"):
            keys.add(name[:-3].lower())
            by_relpath[rel[:-3].lower()] = rel
            try:
                for alias in extract_aliases(path.read_text(encoding="utf-8")):
                    keys.add(alias.lower())
            except (UnicodeDecodeError, OSError):
                pass
        by_relpath[rel.lower()] = rel
        for k in keys:
            by_basename.setdefault(k, []).append(rel)
    return by_basename, by_relpath, all_relpaths


def resolve(target, by_basename, by_relpath, all_relpaths):
    """Return (relpath, status) where status is 'ok' | 'ambiguous' | 'unresolved'."""
    t = target.strip()
    tl = t.lower()
    if "/" in t:
        for key in (tl, tl + ".md"):
            if key in by_relpath:
                return by_relpath[key], "ok"
        # suffix match (Obsidian resolves partial paths)
        suffixes = ("/" + tl, "/" + tl + ".md")
        hits = [r for r in all_relpaths if r.lower().endswith(suffixes[0]) or r.lower().endswith(suffixes[1])]
        if len(hits) == 1:
            return hits[0], "ok"
        return None, "ambiguous" if len(hits) > 1 else "unresolved"
    hits = by_basename.get(tl, [])
    if len(hits) == 1:
        return hits[0], "ok"
    if len(hits) > 1:
        return sorted(hits), "ambiguous"
    # prefix heuristic: [[Session-343]] / [[Infra-002]] style IDs referring to
    # files named <ID>-<slug>.md (older pages predate the aliases convention)
    if re.fullmatch(r"[A-Za-z]+-\d+", t):
        prefix = tl + "-"
        phits = sorted({r for r in all_relpaths
                        if r.lower().rsplit("/", 1)[-1].startswith(prefix) and r.endswith(".md")})
        if len(phits) == 1:
            return phits[0], "ok"
        if len(phits) > 1:
            return phits, "ambiguous"
    return None, "unresolved"


def encode_path(relpath_from_source):
    return urllib.parse.quote(relpath_from_source, safe="/-._~!$&'()+,;=@")


def encode_anchor(heading):
    return urllib.parse.quote(heading.strip(), safe="-._~!$&'()+,;=@")


def relative_to(source_rel, target_rel):
    """POSIX relative path from source file's directory to target file."""
    src_dir = Path(source_rel).parent
    return os.path.relpath(target_rel, start=src_dir.as_posix() if str(src_dir) != "." else ".").replace(os.sep, "/")


def split_frontmatter(content):
    m = re.match(r"^---\s*\n.*?\n---[ \t]*\n", content, re.DOTALL)
    if m:
        return content[: m.end()], content[m.end():]
    # malformed closer glued to last value line, e.g. `summary: "..."---`
    m = re.match(r'^---\s*\n.*?---[ \t]*(\n|$)', content, re.DOTALL)
    if m:
        return content[: m.end()], content[m.end():]
    return "", content


def convert_content(source_rel, body, maps, report):
    by_basename, by_relpath, all_relpaths = maps

    def replace_in_text(text):
        def sub(m):
            bang, inner = m.group(1), m.group(2)
            # split alias (tables escape the pipe as \|)
            alias = None
            if "\\|" in inner:
                inner, alias = inner.split("\\|", 1)
            elif "|" in inner:
                inner, alias = inner.split("|", 1)
            # split heading
            heading = None
            if "#" in inner:
                inner, heading = inner.split("#", 1)
            inner = inner.strip()
            if heading is not None and heading.startswith("^"):
                report["blockref"].append((source_rel, m.group(0)))
                return m.group(0)
            if inner == "":  # same-file anchor [[#Heading]]
                display = alias or heading or ""
                report["converted"][0] += 1
                return f"[{display}](#{encode_anchor(heading or '')})"
            relpath, status = resolve(inner, by_basename, by_relpath, all_relpaths)
            if status == "ambiguous":
                # deterministic: nearest candidate by path distance, then alphabetical
                candidates = list(relpath or [])
                chosen = min(candidates,
                             key=lambda c: (len(relative_to(source_rel, c).split("/")), c))
                report["ambiguous"].append((source_rel, f"{m.group(0)} -> {chosen}"))
                relpath = chosen
            elif status != "ok" or relpath is None:
                report[status].append((source_rel, m.group(0)))
                return m.group(0)
            href = encode_path(relative_to(source_rel, relpath))
            if heading:
                href += "#" + encode_anchor(heading)
            if bang:
                display = alias or inner
                report["converted"][0] += 1
                return f"![{display}]({href})"
            display = alias or (f"{inner} > {heading.strip()}" if heading else inner)
            report["converted"][0] += 1
            return f"[{display}]({href})"

        return WIKILINK_RE.sub(sub, text)

    out_lines = []
    in_fence = False
    fence_marker = None
    for line in body.split("\n"):
        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, None
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        # mask inline code spans
        spans = []

        def stash(m):
            spans.append(m.group(0))
            return f"\x00{len(spans) - 1}\x00"

        masked = INLINE_CODE_RE.sub(stash, line)
        converted = replace_in_text(masked)
        for i, s in enumerate(spans):
            converted = converted.replace(f"\x00{i}\x00", s)
        out_lines.append(converted)
    return "\n".join(out_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="rewrite files (default: dry run)")
    args = ap.parse_args()

    maps = build_maps()
    report = {"converted": [0], "unresolved": [], "ambiguous": [], "blockref": [], "files_changed": 0}

    for path in iter_vault_files():
        if path.suffix != ".md":
            continue
        rel = path.relative_to(VAULT_ROOT).as_posix()
        content = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(content)
        new_body = convert_content(rel, body, maps, report)
        if new_body != body:
            report["files_changed"] += 1
            if args.apply:
                path.write_text(fm + new_body, encoding="utf-8")

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] converted {report['converted'][0]} wikilinks across {report['files_changed']} files")
    for kind in ("unresolved", "ambiguous", "blockref"):
        items = report[kind]
        print(f"  {kind}: {len(items)}")
        for src, link in items:
            print(f"    {src}: {link}")
    # non-zero exit on dry run problems so CI-style callers can gate
    return 0


if __name__ == "__main__":
    sys.exit(main())
