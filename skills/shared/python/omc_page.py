"""Shared OMC page utilities: read, write, hash. Used by /wiki-handoff,
/ark-context-warmup seeder, and /wiki-update promoter.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class OMCPage:
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""


def body_hash(body: str) -> str:
    """SHA-256 hex of the supplied string. Caller chooses what to hash."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def content_hash_slug(source_path: str, content: str) -> str:
    """12-char stable slug from vault source path + content."""
    h = hashlib.sha256(f"{source_path}\n{content}".encode("utf-8")).hexdigest()
    return h[:12]


def parse_page(path: Path) -> OMCPage:
    """Parse a markdown page with optional YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return OMCPage(frontmatter={}, body=text)
    end = text.find("\n---\n", 4)
    if end == -1:
        return OMCPage(frontmatter={}, body=text)
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"malformed frontmatter in {path}: {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"frontmatter in {path} is not a mapping")
    return OMCPage(frontmatter=fm, body=body)


def write_page(path: Path, page: OMCPage, *, exclusive: bool = False) -> None:
    """Write page atomically. If exclusive=True, fail when file exists."""
    fm_text = yaml.safe_dump(page.frontmatter, sort_keys=False).rstrip()
    # parse_page preserves the leading newline after the closing "---"; avoid
    # duplicating it on round-trip so body_hash stays stable across write+reparse.
    separator = "\n" if page.body.startswith("\n") else "\n\n"
    text = f"---\n{fm_text}\n---{separator}{page.body}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        fd = os.open(str(path), flags, 0o644)
        try:
            os.write(fd, text.encode("utf-8"))
        finally:
            os.close(fd)
    else:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise
