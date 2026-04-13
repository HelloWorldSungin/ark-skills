"""Pure helpers for /ark-context-warmup. No I/O except reading stopwords.txt."""
import hashlib
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

STOPWORDS_PATH = Path(__file__).parent / "stopwords.txt"


@lru_cache(maxsize=1)
def _load_stopwords() -> frozenset:
    with open(STOPWORDS_PATH, "r", encoding="utf-8") as f:
        return frozenset(line.strip() for line in f if line.strip())


def task_normalize(task_text: str) -> str:
    """Deterministic projection of task_text used for hashing and matching."""
    if not task_text:
        return "__empty__"
    s = unicodedata.normalize("NFC", task_text)
    s = s.lower()
    s = re.sub(r"[^a-z0-9 _-]", " ", s)
    tokens = s.split()
    stopwords = _load_stopwords()
    tokens = [t for t in tokens if len(t) > 1 and t not in stopwords]
    result = " ".join(tokens)
    return result if result else "__empty__"


def task_summary(task_text: str, limit: int = 120) -> str:
    """Human-readable single-line projection, case + punctuation preserved."""
    if not task_text:
        return ""
    s = re.sub(r"\s+", " ", task_text).strip()
    if len(s) <= limit:
        return s
    truncated = s[:limit]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"


def task_hash(task_normalized: str) -> str:
    """Stable 16-hex-char hash over an already-normalized string."""
    return hashlib.sha256(task_normalized.encode("utf-8")).hexdigest()[:16]
