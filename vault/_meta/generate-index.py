#!/usr/bin/env python3
"""Generate index.md — a flat catalog of all vault pages with summaries.

Usage:
    cd vault/
    python3 _meta/generate-index.py

Scans all .md files (excluding index.md, templates, and _meta/),
extracts frontmatter title and summary, and writes index.md.
"""

import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = VAULT_ROOT / "index.md"

EXCLUDE_DIRS = {"_Templates", "_Attachments", "_meta", ".obsidian"}
EXCLUDE_FILES = {"index.md"}


def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter fields from a markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    fm = {}
    for line in match.group(1).splitlines():
        m = re.match(r'^(\w[\w-]*):\s*"?(.*?)"?\s*$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip('"').strip("'")
    return fm


def collect_pages() -> list[dict]:
    """Walk the vault and collect page metadata."""
    pages = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        rel_root = Path(root).relative_to(VAULT_ROOT)
        for fname in sorted(files):
            if not fname.endswith(".md") or fname in EXCLUDE_FILES:
                continue

            filepath = Path(root) / fname
            rel_path = rel_root / fname

            fm = parse_frontmatter(filepath)
            title = fm.get("title", fname.removesuffix(".md"))
            summary = fm.get("summary", "")
            page_type = fm.get("type", "")

            pages.append(
                {
                    "path": str(rel_path),
                    "title": title,
                    "summary": summary,
                    "type": page_type,
                }
            )

    return sorted(pages, key=lambda p: p["path"])


def generate_index(pages: list[dict]) -> str:
    """Render index.md content."""
    lines = [
        "---",
        'title: "Index"',
        "type: meta",
        "tags:",
        "  - meta",
        'summary: "Machine-generated flat catalog of all vault pages."',
        f"last-updated: {__import__('datetime').date.today().isoformat()}",
        "---",
        "",
        "# Index",
        "",
        "<!-- AUTO-GENERATED — do not edit manually. Run: python3 _meta/generate-index.py -->",
        "",
        "| Page | Type | Summary |",
        "|------|------|---------|",
    ]

    for p in pages:
        title = p["title"].replace("|", "\\|")
        summary = p["summary"].replace("|", "\\|")
        page_type = p["type"]
        link = f'[[{p["path"]}|{title}]]'
        lines.append(f"| {link} | {page_type} | {summary} |")

    lines.append("")
    return "\n".join(lines)


def main():
    pages = collect_pages()
    content = generate_index(pages)
    INDEX_PATH.write_text(content, encoding="utf-8")
    print(f"index.md generated with {len(pages)} entries.")


if __name__ == "__main__":
    main()
