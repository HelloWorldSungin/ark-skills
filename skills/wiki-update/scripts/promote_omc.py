"""Component 3: /wiki-update Step 3.5 — promote OMC pages to Ark vault."""
from __future__ import annotations

import hashlib
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import OMCPage, body_hash, parse_page, write_page  # noqa: E402


STUB_FILENAME_RE = re.compile(r"^session-log-\d{4}-\d{2}-\d{2}")

CATEGORY_PLACEMENT = {
    "architecture": ("Architecture", "Compiled-Insights"),
    "decision": ("Architecture", "Compiled-Insights"),
    "pattern": ("Compiled-Insights", "Compiled-Insights"),
    "debugging": ("__DUAL__", None),
    "session-log": ("__BRIDGE__", None),
    "environment": (None, None),
}

CATEGORY_TO_TYPE = {
    "architecture": "architecture",
    "decision": "decision-record",
    "pattern": "pattern",
}

OMC_ONLY_FIELDS = {
    "confidence", "schemaVersion", "links", "sources",
    "seed_body_hash", "seed_chain_id",
    "ark-original-type", "ark-source-path", "category",
}

OMC_TAG_MARKERS_TO_STRIP = {"source-warmup", "source-handoff"}


@dataclass
class PromotionConfig:
    repo_root: Path
    omc_wiki_dir: Path
    project_docs_path: Path
    tasknotes_path: Path
    task_prefix: str
    session_slug: str
    session_started_at: float = 0.0


@dataclass
class PromotionReport:
    auto_promoted: int = 0
    staged: int = 0
    tasknotes_created: int = 0
    skipped_filtered: int = 0
    session_edits_promoted: int = 0
    troubleshooting_created: int = 0
    merged_existing: int = 0
    pending_deletes: List[Path] = field(default_factory=list)
    written_paths: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def is_stub(page: OMCPage, *, filename: str) -> bool:
    tags = set(page.frontmatter.get("tags") or [])
    if {"session-log", "auto-captured"}.issubset(tags):
        return True
    if STUB_FILENAME_RE.match(filename):
        return True
    return False


def classify(page: OMCPage, *, filename: str) -> Tuple[str, str]:
    if is_stub(page, filename=filename):
        return "skip", "stub (auto-captured)"
    fm = page.frontmatter
    category = fm.get("category") or ""
    if category == "environment":
        return "skip", "environment (re-derivable)"
    tags = set(fm.get("tags") or [])

    reason_prefix = ""
    if "source-warmup" in tags:
        if fm.get("seed_body_hash") == body_hash(page.body):
            return "skip", "untouched seed (re-derivable from vault)"
        reason_prefix = "edited seed: "

    if category == "debugging":
        return "dual-write-debug", reason_prefix + "debugging"
    if category == "session-log" and "session-bridge" in tags:
        return "bridge-merge", reason_prefix + "session-bridge"

    confidence = fm.get("confidence") or "medium"
    if confidence == "high":
        return "auto-promote", reason_prefix + f"{category} high"
    if confidence == "medium":
        return "stage", reason_prefix + f"{category} medium"
    return "skip", reason_prefix + f"{category} low"


def derive_summary(body: str, *, max_len: int = 200) -> str:
    for line in body.split("\n\n"):
        s = line.strip()
        if s and not s.startswith("#"):
            one_line = " ".join(s.split())
            if len(one_line) <= max_len:
                return one_line
            return one_line[: max_len - 1].rstrip() + "…"
    return ""


def translate_frontmatter(omc_fm: dict, *, session_slug: str) -> dict:
    out = dict(omc_fm)
    vault_type = omc_fm.get("ark-original-type") or CATEGORY_TO_TYPE.get(
        omc_fm.get("category") or "", "reference"
    )
    out["type"] = vault_type
    out["source-sessions"] = [f"[[{session_slug}]]"]
    out["tags"] = [t for t in (omc_fm.get("tags") or []) if t not in OMC_TAG_MARKERS_TO_STRIP]
    out["last-updated"] = time.strftime("%Y-%m-%d", time.localtime())
    if "created" not in out:
        out["created"] = out["last-updated"]
    for k in OMC_ONLY_FIELDS:
        out.pop(k, None)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomic text write via tmp + os.replace. Cleans up tmp on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def _idempotency_marker(content: str) -> str:
    """12-char content hash embedded as an HTML comment; used to block duplicate appends."""
    return f"<!-- src:{hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]} -->"


def _append_to_session_log(log_path: Path, title: str, body: str) -> bool:
    """Atomic + idempotent. Returns True iff a write occurred."""
    text = log_path.read_text()
    marker = _idempotency_marker(f"{title}\n{body}")
    if marker in text:
        return False
    section = "## Issues & Discoveries"
    insertion = f"\n### {title}\n{marker}\n\n{body}\n"
    if section in text:
        updated = text.replace(section, section + insertion, 1)
    else:
        updated = text + f"\n\n{section}\n{insertion}"
    _atomic_write_text(log_path, updated)
    return True


def _merge_into_existing(target: Path, new_body: str) -> bool:
    """Atomic + idempotent continuation append. Returns True iff a write occurred."""
    text = target.read_text()
    marker = _idempotency_marker(new_body)
    if marker in text:
        return False
    continuation = (
        f"\n\n## Continuation — {time.strftime('%Y-%m-%d')}\n"
        f"{marker}\n\n{new_body}\n"
    )
    _atomic_write_text(target, text + continuation)
    return True


def _create_review_tasknote(bugs_dir: Path, task_prefix: str, title: str,
                             staging_path: Path, omc_path: Path) -> Path:
    bugs_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(bugs_dir.glob(f"{task_prefix}*.md"))
    next_n = len(existing) + 1
    task_id = f"{task_prefix}{next_n:03d}"
    path = bugs_dir / f"{task_id}-review-wiki-promotion.md"
    path.write_text(
        f"---\ntitle: \"Review staged wiki promotion: {title}\"\n"
        f"task-id: {task_id}\nstatus: todo\npriority: low\n"
        f"type: bug\ntags: [wiki-promotion-review]\n---\n\n"
        f"## Review\n\nStaged at `{staging_path}`; original OMC source at `{omc_path}`.\n"
    )
    return path


def _resolve_existing_vault_page(project_docs: Path, ark_source_path: Optional[str]) -> Optional[Path]:
    """Resolve ark-source-path inside project_docs with path-traversal containment."""
    if not ark_source_path:
        return None
    try:
        root = project_docs.resolve()
        candidate = (project_docs / ark_source_path).resolve()
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    if candidate.exists():
        return candidate
    return None


def _find_session_log(project_docs: Path, slug: str) -> Optional[Path]:
    """Exact-slug match only. Callers must handle None (no silent cross-session fallback)."""
    exact = project_docs / "Session-Logs" / f"{slug}.md"
    return exact if exact.exists() else None


def promote(config: PromotionConfig) -> PromotionReport:
    report = PromotionReport()
    wiki_dir = config.omc_wiki_dir
    if not wiki_dir.is_dir():
        return report

    log_path = _find_session_log(config.project_docs_path, config.session_slug)

    for omc_path in wiki_dir.glob("*.md"):
        if omc_path.name in ("index.md", "log.md"):
            continue

        # session_started_at filter: skip pages older than session start.
        if config.session_started_at and omc_path.stat().st_mtime < config.session_started_at:
            report.skipped_filtered += 1
            continue

        try:
            page = parse_page(omc_path)
        except ValueError as exc:
            report.errors.append(f"malformed {omc_path.name}: {exc}")
            continue

        disposition, reason = classify(page, filename=omc_path.name)

        try:
            if disposition == "skip":
                report.skipped_filtered += 1
                continue

            if disposition == "dual-write-debug":
                any_effect = False
                if log_path:
                    wrote = _append_to_session_log(
                        log_path,
                        page.frontmatter.get("title", omc_path.stem),
                        page.body,
                    )
                    if wrote:
                        report.written_paths.append(log_path)
                    any_effect = True
                tags = set(page.frontmatter.get("tags") or [])
                if tags & {"pattern", "insight"}:
                    ts_dir = config.project_docs_path / "Troubleshooting"
                    ts_dir.mkdir(parents=True, exist_ok=True)
                    new_fm = translate_frontmatter(page.frontmatter,
                                                    session_slug=config.session_slug)
                    new_fm["type"] = "compiled-insight"
                    new_fm["summary"] = derive_summary(page.body)
                    ts_path = ts_dir / ("troubleshooting-" + omc_path.stem + ".md")
                    write_page(ts_path, OMCPage(frontmatter=new_fm, body=page.body))
                    report.troubleshooting_created += 1
                    report.written_paths.append(ts_path)
                    any_effect = True
                if any_effect:
                    report.pending_deletes.append(omc_path)
                else:
                    report.errors.append(
                        f"{omc_path.name}: dual-write-debug — no session log for slug "
                        f"{config.session_slug!r} and not pattern/insight tagged; OMC source preserved"
                    )
                continue

            if disposition == "bridge-merge":
                if log_path:
                    wrote = _append_to_session_log(log_path, "Session Bridge", page.body)
                    if wrote:
                        report.written_paths.append(log_path)
                    report.pending_deletes.append(omc_path)
                else:
                    report.errors.append(
                        f"{omc_path.name}: bridge-merge — no session log for slug "
                        f"{config.session_slug!r}; OMC source preserved"
                    )
                continue

            # auto-promote or stage: build vault frontmatter
            new_fm = translate_frontmatter(page.frontmatter, session_slug=config.session_slug)
            new_fm["summary"] = derive_summary(page.body)

            category = page.frontmatter.get("category", "")
            primary_name, fallback_name = CATEGORY_PLACEMENT.get(category, ("Compiled-Insights", None))
            if not primary_name or primary_name.startswith("__"):
                report.skipped_filtered += 1
                continue

            ark_path = page.frontmatter.get("ark-source-path")
            existing_target = _resolve_existing_vault_page(config.project_docs_path, ark_path)

            if disposition == "stage":
                staging_dir = config.project_docs_path / "Staging"
                staging_dir.mkdir(parents=True, exist_ok=True)
                target = staging_dir / omc_path.name
                write_page(target, OMCPage(frontmatter=new_fm, body=page.body))
                report.written_paths.append(target)
                bugs_dir = config.tasknotes_path / "Tasks" / "Bug"
                _create_review_tasknote(bugs_dir, config.task_prefix,
                                          page.frontmatter.get("title", omc_path.stem),
                                          target, omc_path)
                report.staged += 1
                report.tasknotes_created += 1
                report.pending_deletes.append(omc_path)
                continue

            # auto-promote
            if existing_target:
                merged = _merge_into_existing(existing_target, page.body)
                if merged:
                    report.written_paths.append(existing_target)
                report.merged_existing += 1
            else:
                primary_dir = config.project_docs_path / primary_name
                if not primary_dir.is_dir():
                    primary_dir = config.project_docs_path / (fallback_name or "Compiled-Insights")
                    primary_dir.mkdir(parents=True, exist_ok=True)
                target = primary_dir / omc_path.name
                write_page(target, OMCPage(frontmatter=new_fm, body=page.body))
                report.written_paths.append(target)
                report.auto_promoted += 1
            if "edited seed" in reason:
                report.session_edits_promoted += 1
            report.pending_deletes.append(omc_path)

        except (OSError, ValueError) as exc:
            # File-level failures: record and move on (OMC source NOT added to pending_deletes).
            # Programmer errors (TypeError/KeyError/AttributeError) are NOT caught — they propagate
            # so CI catches real bugs instead of silently reporting them as per-file "errors".
            report.errors.append(f"{omc_path.name}: {exc}")

    return report


def finalize_deletes(pending: List[Path], *, require: List[Path]) -> Tuple[int, List[str]]:
    """Execute pending deletes only if all `require` paths exist and are non-empty.

    Returns (deleted_count, errors). If `require` is empty the precondition is
    vacuously satisfied — callers that want a real gate must pass a non-empty list.
    """
    errors: List[str] = []
    for req in require:
        if not req.exists() or req.stat().st_size == 0:
            return 0, [f"precondition failed: {req} missing or empty"]
    deleted = 0
    for p in pending:
        try:
            p.unlink()
            deleted += 1
        except OSError as exc:
            errors.append(f"unlink {p}: {exc}")
    return deleted, errors
