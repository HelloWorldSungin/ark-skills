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


import time
import secrets

# Crockford base32 alphabet (excludes I, L, O, U)
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(n: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def chain_id_new() -> str:
    """Generate a ULID. 48-bit timestamp (ms) + 80-bit randomness, Crockford base32."""
    timestamp_ms = int(time.time() * 1000)
    random_bits = secrets.randbits(80)
    ts_part = _encode_crockford(timestamp_ms, 10)
    rand_part = _encode_crockford(random_bits, 16)
    return ts_part + rand_part


def _main(argv):
    import sys
    if len(argv) < 2:
        sys.stderr.write("usage: warmup-helpers.py <command> [args...]\n")
        return 2
    cmd = argv[1]
    if cmd == "normalize":
        if len(argv) < 3:
            sys.stderr.write("usage: normalize <task_text>\n")
            return 2
        print(task_normalize(argv[2]))
        return 0
    if cmd == "summary":
        if len(argv) < 3:
            sys.stderr.write("usage: summary <task_text>\n")
            return 2
        print(task_summary(argv[2]))
        return 0
    if cmd == "hash":
        if len(argv) < 3:
            sys.stderr.write("usage: hash <task_normalized>\n")
            return 2
        print(task_hash(argv[2]))
        return 0
    if cmd == "chain-id":
        print(chain_id_new())
        return 0
    sys.stderr.write(f"unknown command: {cmd}\n")
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv))
