"""Synthesizer: assembles the Context Brief + handles atomic cache writes + 24h pruning."""
from __future__ import annotations

import os
import re
import secrets
import time
import yaml
from pathlib import Path


_CACHE_TTL_SECONDS = 2 * 3600          # 2 hours
_CACHE_PRUNE_SECONDS = 24 * 3600        # 24 hours


def _format_evidence(evidence: list) -> str:
    if not evidence:
        return "None"
    lines = []
    for ev in evidence:
        kind = ev.get("type", "Unknown")
        conf = ev.get("confidence")
        id_ = ev.get("id")
        detail = ev.get("detail", "")
        reason = ev.get("reason", "")
        parts = [f"- **{kind}**"]
        if conf:
            parts.append(f"(conf: {conf})")
        if id_:
            parts.append(f"`{id_}`")
        parts.append(f"— {detail}")
        if reason:
            parts.append(f"  \n  *{reason}*")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def assemble_brief(
    *,
    chain_id: str,
    task_hash: str,
    task_summary: str,
    scenario: str,
    notebooklm_out: str,
    wiki_out: str,
    tasknotes_out: str,
    evidence: list,
    has_omc: bool = False,
) -> str:
    # Serialize frontmatter via yaml.safe_dump so task_summary values
    # containing ':', '#', '|', or quotes don't invalidate the block that
    # cached_brief_if_fresh later parses. Without this, cache reuse silently
    # falls through to cold warm-up every time for very common summaries
    # (codex P2 finding).
    fm = yaml.safe_dump(
        {
            "chain_id": chain_id,
            "task_hash": task_hash,
            "task_summary": task_summary,
            "scenario": scenario,
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    # Spec AC8: Context Brief includes a one-line "OMC detected: yes/no" row.
    # Sourced from availability.probe() `has_omc` via the calling skill.
    omc_line = f"**OMC detected:** {'yes' if has_omc else 'no'}\n\n"
    return (
        "---\n"
        f"{fm}"
        "---\n\n"
        "## Context Brief\n\n"
        f"{omc_line}"
        "### Where We Left Off\n"
        f"{notebooklm_out or 'Fresh start — no recent session found.'}\n\n"
        "### Recent Project Activity\n"
        f"{notebooklm_out or 'Not queried — notebooklm lane unavailable.'}\n\n"
        "### Vault Knowledge Relevant to This Task\n"
        f"{wiki_out or 'Not queried — wiki backend unavailable.'}\n\n"
        "### Related Tasks & In-flight Work\n"
        f"{tasknotes_out or 'Not queried — tasknotes backend unavailable.'}\n\n"
        "### Evidence\n"
        f"{_format_evidence(evidence)}\n"
    )


def _cache_filename(chain_id: str, task_hash: str) -> str:
    return f"context-brief-{chain_id}-{task_hash[:8]}.md"


def _unique_tmp_path(target: Path) -> Path:
    """Fix: unique tmp filename per call — PID + random suffix.
    Prevents concurrent writers to the same target from clobbering each other.
    """
    suffix = f".{os.getpid()}.{secrets.token_hex(4)}.tmp"
    return target.with_suffix(target.suffix + suffix)


def write_brief_atomic(*, cache_dir: Path, chain_id: str, task_hash: str, brief_text: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / _cache_filename(chain_id, task_hash)
    tmp = _unique_tmp_path(target)
    try:
        tmp.write_text(brief_text, encoding="utf-8")
        tmp.replace(target)  # atomic on POSIX
    except Exception:
        # Best-effort cleanup of the unique tmp file if the rename failed
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    _prune(cache_dir)
    return target


def _prune(cache_dir: Path) -> None:
    now = time.time()
    for p in cache_dir.glob("context-brief-*.md"):
        try:
            if now - p.stat().st_mtime > _CACHE_PRUNE_SECONDS:
                p.unlink()
        except OSError:
            pass
    # Clean up orphan tmp files older than 10 minutes (from crashed writers)
    for p in cache_dir.glob("context-brief-*.tmp"):
        try:
            if now - p.stat().st_mtime > 600:
                p.unlink()
        except OSError:
            pass


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict | None:
    """Parse the YAML frontmatter (first --- ... --- block). Return dict or None."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        d = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return d if isinstance(d, dict) else None


def cached_brief_if_fresh(*, cache_dir: Path, chain_id: str, task_hash: str) -> str | None:
    path = cache_dir / _cache_filename(chain_id, task_hash)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > _CACHE_TTL_SECONDS:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    # Fix: parse frontmatter properly instead of substring-matching the whole text
    fm = _parse_frontmatter(text)
    if not fm:
        return None
    if fm.get("chain_id") != chain_id:
        return None
    if fm.get("task_hash") != task_hash:
        return None
    return text
