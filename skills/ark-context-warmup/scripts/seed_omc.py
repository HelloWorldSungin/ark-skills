"""Warmup populator: writes cited vault sources into .omc/wiki/ with
content-hashed filenames, plus stale cleanup."""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, body_hash, content_hash_slug, parse_page, write_page  # noqa: E402


MIN_BODY_LEN = 200

VAULT_TYPE_TO_OMC_CATEGORY = {
    "architecture": "architecture",
    "decision-record": "decision",
    "pattern": "pattern",
    "compiled-insight": "pattern",
    "research": "architecture",
    "reference": "architecture",
    "guide": "architecture",
}

EXCLUDED_VAULT_TYPES = {"session-log", "epic", "story", "bug", "task"}


@dataclass
class SeedSource:
    title: str
    vault_source_path: str
    body: str
    vault_type: str
    tags: List[str]
    confidence: str


@dataclass
class SeedResult:
    written: int = 0
    deleted_stale: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)


def _build_page(source: SeedSource, chain_id: str) -> OMCPage:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    category = VAULT_TYPE_TO_OMC_CATEGORY.get(source.vault_type, "architecture")
    tags = list(dict.fromkeys(source.tags + ["source-warmup"]))
    fm = {
        "title": source.title,
        "tags": tags,
        "created": now,
        "updated": now,
        "sources": [source.vault_source_path, chain_id],
        "links": [],
        "category": category,
        "confidence": source.confidence,
        "schemaVersion": 1,
        "ark-original-type": source.vault_type,
        "ark-source-path": source.vault_source_path,
        "seed_body_hash": body_hash(source.body),
        "seed_chain_id": chain_id,
    }
    return OMCPage(frontmatter=fm, body=source.body)


def seed(wiki_dir: Path, *, chain_id: str, sources: List[SeedSource]) -> SeedResult:
    r = SeedResult()
    wiki_dir.mkdir(parents=True, exist_ok=True)

    active_slugs: Set[str] = set()
    for src in sources:
        if src.vault_type in EXCLUDED_VAULT_TYPES or len(src.body) < MIN_BODY_LEN:
            r.skipped += 1
            continue
        slug = content_hash_slug(src.vault_source_path, src.body)
        active_slugs.add(slug)
        target = wiki_dir / f"source-{slug}.md"
        if target.exists():
            continue
        try:
            write_page(target, _build_page(src, chain_id))
            r.written += 1
        except Exception as exc:  # noqa: BLE001
            r.errors.append(f"{src.vault_source_path}: {exc}")

    for existing in wiki_dir.glob("source-*.md"):
        slug = existing.stem[len("source-"):]
        if slug in active_slugs:
            continue
        try:
            page = parse_page(existing)
        except ValueError:
            continue
        if page.frontmatter.get("seed_chain_id") != chain_id:
            continue
        if "source-warmup" not in (page.frontmatter.get("tags") or []):
            continue
        try:
            existing.unlink()
            r.deleted_stale += 1
        except OSError as exc:
            r.errors.append(f"unlink {existing}: {exc}")

    return r


def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--wiki-dir", required=True)
    p.add_argument("--chain-id", required=True)
    args = p.parse_args()
    payload = json.load(sys.stdin)
    sources = [SeedSource(**s) for s in payload]
    res = seed(Path(args.wiki_dir), chain_id=args.chain_id, sources=sources)
    print(json.dumps({
        "written": res.written, "deleted_stale": res.deleted_stale,
        "skipped": res.skipped, "errors": res.errors,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
