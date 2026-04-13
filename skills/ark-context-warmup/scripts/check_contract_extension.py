#!/usr/bin/env python3
"""CI check: /ark-workflow's Step 6.5 includes the warmup-contract fields and the bash
snippet that invokes warmup-helpers.py to compute them.

Strengthened beyond the plan's initial version (per controller deferred-findings fix):
 1. Checks fields appear within the Step 6.5 section body specifically, not just
    somewhere in the file.
 2. Checks the Step 6.5 section contains a bash invocation of warmup-helpers.py —
    without it, /ark-workflow doesn't actually compute chain_id/task_hash.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "chain_id:",
    "task_text:",
    "task_summary:",
    "task_normalized:",
    "task_hash:",
]

# Match "### Step 6.5" heading (case-preserving) and capture body up to the next "### "
# heading or end of file.
_STEP_65_RE = re.compile(
    r"###\s+Step\s+6\.5.*?(?=\n###\s|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def _extract_step_65(text: str) -> str | None:
    m = _STEP_65_RE.search(text)
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, type=Path)
    args = ap.parse_args()
    text = args.skill.read_text()

    section = _extract_step_65(text)
    if section is None:
        sys.stderr.write(
            f"{args.skill}: no '### Step 6.5' / Activate Continuity section found\n"
        )
        return 1

    # (A) Required fields must appear within the Step 6.5 section, not elsewhere
    missing = [f for f in REQUIRED_FIELDS if f not in section]
    if missing:
        sys.stderr.write(
            f"{args.skill}: Step 6.5 section missing warmup-contract fields: {missing}\n"
        )
        return 1

    # (B) Step 6.5 must contain a bash invocation of warmup-helpers.py
    if "warmup-helpers.py" not in section:
        sys.stderr.write(
            f"{args.skill}: Step 6.5 section does not invoke warmup-helpers.py "
            f"(expected bash snippet that computes CHAIN_ID, TASK_NORMALIZED, etc.)\n"
        )
        return 1

    print(f"OK: {args.skill} Step 6.5 contains all required fields and warmup-helpers.py invocation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
