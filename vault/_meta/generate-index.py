#!/usr/bin/env python3
"""Generate OKF index.md files (spec §6) across the vault.

Produces:
  * a per-folder `index.md` in every directory that contains concept pages —
    progressive disclosure: agents read one level at a time. Per OKF §6 these
    carry NO frontmatter; entries are `* [Title](url) - description`.
  * the bundle-root `index.md` — flat global catalog of every page grouped by
    `type`, plus a Directories section. Carries the `okf_version` declaration
    (the only index.md where frontmatter is permitted, spec §11).

Descriptions come from each page's `description:` frontmatter. Stdlib only.
"""

import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent
EXCLUDE_DIRS = {
    ".obsidian", ".git", ".claude-plugin", ".github", ".notebooklm",
    "generated", "_Attachments",
}
RESERVED = {"index.md", "log.md"}


def extract_frontmatter(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        return None

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    fm = {}
    current_key = None
    for line in match.group(1).split("\n"):
        list_item = re.match(r"^  - (.+)", line)
        if list_item and current_key:
            if not isinstance(fm.get(current_key), list):
                fm[current_key] = []
            fm[current_key].append(list_item.group(1).strip())
            continue
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if kv:
            key, value = kv.group(1), kv.group(2).strip().strip("\"'")
            current_key = key
            if value:
                inline = re.match(r"^\[(.+)\]$", value)
                fm[key] = ([v.strip().strip("\"'") for v in inline.group(1).split(",")]
                           if inline else value)
            else:
                fm[key] = []
        else:
            current_key = None
    return fm


def encode_href(relpath):
    return urllib.parse.quote(relpath, safe="/-._~!$&'()+,;=@")


def collect_pages():
    pages = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".md") or fname in RESERVED:
                continue
            filepath = Path(root) / fname
            rel = filepath.relative_to(VAULT_ROOT)
            fm = extract_frontmatter(filepath) or {}
            title = fm.get("title") or fname[:-3].replace("-", " ")
            if isinstance(title, list):
                title = fname[:-3].replace("-", " ")
            category = fm.get("type", fm.get("task-type", "uncategorized"))
            if isinstance(category, list):
                category = category[0] if category else "uncategorized"
            description = fm.get("description", "")
            if isinstance(description, list):
                description = ""
            pages.append({
                "rel": rel.as_posix(),
                "dir": rel.parent.as_posix(),
                "title": title,
                "category": category,
                "description": description,
            })
    return pages


def entry(title, href, description):
    line = f"* [{title}]({encode_href(href)})"
    if description:
        line += f" - {description}"
    return line


def write_folder_indexes(pages):
    by_dir = {}
    for p in pages:
        by_dir.setdefault(p["dir"], []).append(p)

    all_dirs = set(by_dir)
    # a directory also gets listed in its parent's index; intermediate dirs
    # with only subdirectories still get indexes
    children = {}
    worklist = [d for d in all_dirs if d != "."]
    while worklist:
        d = worklist.pop()
        parent = Path(d).parent.as_posix()
        children.setdefault(parent, set()).add(d)
        if parent not in all_dirs and parent != ".":
            all_dirs.add(parent)
            worklist.append(parent)

    count = 0
    for d in sorted(all_dirs):
        if d == ".":
            continue  # bundle root handled separately
        lines = [f"# {d}", ""]
        for p in sorted(by_dir.get(d, []), key=lambda p: p["rel"]):
            lines.append(entry(p["title"], Path(p["rel"]).name, p["description"]))
        subdirs = sorted(children.get(d, set()))
        if subdirs:
            lines += ["", "# Subdirectories", ""]
            for sub in subdirs:
                n = sum(1 for p in pages if p["dir"] == sub or p["dir"].startswith(sub + "/"))
                lines.append(entry(Path(sub).name, Path(sub).name + "/", f"{n} pages"))
        (VAULT_ROOT / d / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        count += 1
    return count, sorted(children.get(".", set()) | {d for d in all_dirs if "/" not in d and d != "."})


def write_root_index(pages, top_dirs):
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        'okf_version: "0.1"',
        f"generated: {now_utc}",
        "---",
        "",
        "# Vault Index",
        "",
        f"Auto-generated catalog of {len(pages)} pages. Human entry point: "
        "[00-Home](00-Home.md). Directory indexes below support progressive "
        "disclosure; the flat catalog after them is grouped by `type`.",
        "",
        "# Directories",
        "",
    ]
    for d in top_dirs:
        n = sum(1 for p in pages if p["dir"] == d or p["dir"].startswith(d + "/"))
        lines.append(entry(d, d + "/", f"{n} pages"))
    root_pages = [p for p in pages if p["dir"] == "."]
    if root_pages:
        lines += ["", "# Pages", ""]
        for p in sorted(root_pages, key=lambda p: p["rel"]):
            lines.append(entry(p["title"], p["rel"], p["description"]))

    categories = {}
    for p in pages:
        categories.setdefault(p["category"], []).append(p)
    for cat in sorted(categories):
        cat_pages = sorted(categories[cat], key=lambda p: str(p["title"]))
        lines += ["", f"# {cat} ({len(cat_pages)} pages)", ""]
        for p in cat_pages:
            lines.append(entry(p["title"], p["rel"], p["description"]))

    (VAULT_ROOT / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    pages = collect_pages()
    n_folders, top_dirs = write_folder_indexes(pages)
    write_root_index(pages, top_dirs)
    print(f"Generated root index.md ({len(pages)} pages) + {n_folders} folder indexes")


if __name__ == "__main__":
    main()
