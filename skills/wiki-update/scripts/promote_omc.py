"""Component 3: /wiki-update Step 3.5 — promote OMC pages to Ark vault."""
from __future__ import annotations

import re
import sys
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


def promote(config: PromotionConfig) -> PromotionReport:
    raise NotImplementedError("Implemented in Task 12")
