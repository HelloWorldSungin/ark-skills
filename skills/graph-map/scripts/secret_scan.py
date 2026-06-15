"""Scan graphify output for secrets and oversized files before commit.

Usage: python3 secret_scan.py <dir> [--max-mb 5]
Exit 1 if any secret or oversized file is found, else 0.
"""
import argparse
import re
import sys
from pathlib import Path

PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("assigned_secret", re.compile(
        r"(?i)\b(api[_-]?key|api[_-]?token|secret|password|passwd|access[_-]?token)\b"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9/\+_\-]{16,}")),
]
# graphify output is text-ish; skip obvious binaries by extension.
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2", ".ico"}


def scan_text(text):
    return [(name, m.group(0)[:40]) for name, rx in PATTERNS for m in rx.finditer(text)]


def scan_dir(root, max_bytes):
    root = Path(root)
    findings = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        size = p.stat().st_size
        if size > max_bytes:
            findings.append({"kind": "oversized", "file": str(p), "bytes": size})
        if p.suffix.lower() in SKIP_EXT:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for name, sample in scan_text(text):
            findings.append({"kind": "secret", "file": str(p), "rule": name, "sample": sample})
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--max-mb", type=float, default=5.0)
    args = ap.parse_args(argv)
    findings = scan_dir(args.dir, int(args.max_mb * 1024 * 1024))
    for f in findings:
        print(f)
    if findings:
        print(f"FAIL: {len(findings)} issue(s) found in {args.dir}", file=sys.stderr)
        return 1
    print(f"PASS: no secrets/oversized files in {args.dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
