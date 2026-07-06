#!/usr/bin/env python3
"""normalize_frontmatter.py — OKF frontmatter conformance for the vault.

OKF v0.1 (§4.1, §9) requires every non-reserved .md file to carry parseable
YAML frontmatter with a non-empty `type`. This script (stdlib only):

  * repairs malformed closing fences (`description: "..."---` glued to the last
    value line — breaks every YAML parser including Obsidian's)
  * adds a frontmatter block where none exists
  * ensures `type`   — from `task-type`, else a folder-based default
  * ensures `tags`   — defaults to [<type>]
  * ensures `timestamp` — ISO 8601, derived from last-updated/date/filed/
    created, else the file's last git commit date
  * adds `resource`  — from `source_arxiv` (arxiv.org URL) or `url`
  * derives `description` for Research/Methodology cards from their H1 title

Existing keys and their order are never modified — missing keys are appended
at the end of the block. Files still missing `description` are reported, not
fabricated.

Usage:
    python3 _meta/okf/normalize_frontmatter.py            # dry run
    python3 _meta/okf/normalize_frontmatter.py --apply
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
EXCLUDE_DIRS = {
    ".obsidian", ".git", ".claude-plugin", ".github", ".notebooklm",
    "generated",
}
RESERVED = {"index.md", "log.md"}

# folder-prefix -> default type (first match wins; most specific first)
FOLDER_TYPES = [
    ("Trading-Signal-AI/Research/Cards/", "research-card"),
    ("Trading-Signal-AI/Research/Methodology-Cards/", "methodology-card"),
    ("Trading-Signal-AI/Research/Compiled-Insights/", "compiled-insight"),
    ("Trading-Signal-AI/Session-Logs/", "session-log"),
    ("Trading-Signal-AI/Research/", "research"),
    ("Trading-Signal-AI/Models/", "model"),
    ("Trading-Signal-AI/Strategies/", "strategy"),
    ("Trading-Signal-AI/Training/", "training"),
    ("Trading-Signal-AI/Operations/", "operations"),
    ("Trading-Signal-AI/Live-Trading/", "operations"),
    ("Trading-Signal-AI/Paper-Trading/", "operations"),
    ("Infrastructure/Containers/", "container"),
    ("Infrastructure/Services/", "service"),
    ("Infrastructure/Networking/", "networking"),
    ("Infrastructure/Hardware/", "hardware"),
    ("Infrastructure/", "reference"),
    ("Compiled-Insights/", "compiled-insight"),
    ("TaskNotes/Templates/", "template"),
    ("_Templates/", "template"),
    ("TaskNotes/", "task"),
    ("TinyClaw-Trading/", "reference"),
    ("Ark-Line/", "reference"),
    ("_Attachments/", "reference"),
    ("_meta/", "schema"),
]

DATE_KEYS = ("last-updated", "date", "filed", "created", "updated")

FM_OK_RE = re.compile(r"^---[ \t]*\n(.*?)\n---[ \t]*(\n|$)", re.DOTALL)
# malformed: closing --- glued onto the last value line
FM_GLUED_RE = re.compile(r"^---[ \t]*\n(.*?)---[ \t]*(\n|$)", re.DOTALL)
KV_RE = re.compile(r"^(\w[\w-]*):[ \t]*(.*)$")


def iter_pages():
    for root, dirs, files in os.walk(VAULT_ROOT, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if fname.endswith(".md") and fname not in RESERVED:
                yield Path(root) / fname


def parse_keys(fm_text):
    keys = {}
    for line in fm_text.split("\n"):
        m = KV_RE.match(line)
        if m:
            keys[m.group(1)] = m.group(2).strip().strip("\"'")
    return keys


def folder_type(rel):
    for prefix, t in FOLDER_TYPES:
        if rel.startswith(prefix):
            return t
    return "reference"


def to_iso(value):
    value = value.strip().strip("\"'")
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    if m:
        return f"{m.group(1)}T00:00:00Z"
    return None


def git_timestamp(rel):
    try:
        out = subprocess.run(
            ["git", "-C", str(VAULT_ROOT), "log", "-1", "--format=%aI", "--", rel],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        return re.sub(r"(\+00:00|Z)$", "Z", out) if out else None
    except OSError:
        return None


def h1_description(body):
    """`# RC-2026-001 — Some descriptive title` -> `Some descriptive title`."""
    for line in body.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            for dash in (" — ", " – ", " - "):
                if dash in title:
                    return title.split(dash, 1)[1].strip()
            return title
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    stats = {"fence_fixed": 0, "fm_added": 0, "keys_added": 0, "files_changed": 0}
    no_description = []
    type_assigned = []

    for path in iter_pages():
        rel = path.relative_to(VAULT_ROOT).as_posix()
        content = path.read_text(encoding="utf-8")
        changed = False

        m = FM_OK_RE.match(content)
        if not m:
            g = FM_GLUED_RE.match(content)
            if g:
                # split the glued closer onto its own line
                fm_text = g.group(1)
                rest = content[g.end():]
                content = f"---\n{fm_text}\n---\n{rest}"
                m = FM_OK_RE.match(content)
                stats["fence_fixed"] += 1
                changed = True
            else:
                title = path.stem.replace("-", " ")
                content = f"---\ntitle: \"{title}\"\n---\n\n{content}"
                m = FM_OK_RE.match(content)
                stats["fm_added"] += 1
                changed = True

        assert m is not None
        fm_text = m.group(1)
        body = content[m.end():]
        keys = parse_keys(fm_text)
        additions = []

        if not keys.get("type"):
            t = keys.get("task-type") or folder_type(rel)
            additions.append(f"type: {t}")
            type_assigned.append((rel, t))

        if "tags" not in keys:
            t = keys.get("type") or keys.get("task-type") or folder_type(rel)
            additions.append(f"tags: [{t}]")

        if "timestamp" not in keys:
            ts = None
            for k in DATE_KEYS:
                if keys.get(k):
                    ts = to_iso(keys[k])
                    if ts:
                        break
            ts = ts or git_timestamp(rel)
            if ts:
                additions.append(f"timestamp: {ts}")

        if "resource" not in keys:
            if keys.get("source_arxiv"):
                additions.append(f"resource: https://arxiv.org/abs/{keys['source_arxiv']}")
            elif keys.get("url"):
                additions.append(f"resource: {keys['url']}")

        if "description" not in keys:
            derived = None
            if rel.startswith(("Trading-Signal-AI/Research/Cards/",
                               "Trading-Signal-AI/Research/Methodology-Cards/")):
                derived = h1_description(body)
            if derived:
                additions.append(f'description: "{derived}"')
            else:
                no_description.append(rel)

        if additions:
            new_fm = fm_text + "\n" + "\n".join(additions)
            content = f"---\n{new_fm}\n---\n{body}"
            stats["keys_added"] += len(additions)
            changed = True

        if changed:
            stats["files_changed"] += 1
            if args.apply:
                path.write_text(content, encoding="utf-8")

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"[{mode}] {stats}")
    print(f"type assigned ({len(type_assigned)}):")
    for rel, t in type_assigned:
        print(f"    {rel}: {t}")
    print(f"still missing description ({len(no_description)}):")
    for rel in no_description:
        print(f"    {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
