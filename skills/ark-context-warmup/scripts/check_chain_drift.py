#!/usr/bin/env python3
"""CI lint: grep /ark-workflow chain + reference files for banned strings
that indicate specific documentation drift previously surfaced in the
2026-04-14 OMC routing audit.

Complements check_path_b_coverage.py:
  - check_path_b_coverage.py → shape distribution + canonicalization invariants
  - check_chain_drift.py     → prose consistency (this script)

Scope (relative to --root):
  - skills/ark-workflow/chains/*.md
  - skills/ark-workflow/references/omc-integration.md

Banned patterns (regex, case-sensitive unless noted):
  1. Literal OMC_EXECUTION_ONLY — fictional env var from v1.13.0 retired
     in R1. Zero matches in OMC v4.11.5 source — see audit D6.1.
  2. Phase 5 with (docs/ship) suffix — stale autopilot phase claim
     corrected in R1. Phase 5 is actually Cleanup (autopilot SKILL.md:70-72).
  3. internal Phase 4 with (execution) suffix — stale phase claim.
     Execution is Phase 2; Phase 4 is Validation (autopilot SKILL.md:64-68).
  4. Step-3 engine anchor at line start (MULTILINE) — "3. \\`/ultrawork\\`"
     or "3. \\`/ralph\\`" as chain step-3 engines retired in R2. Descriptive
     mentions inside step-3 vanilla lines (e.g., "via internal /ultrawork")
     do NOT match because the regex is anchored to the "3. \\`/" prefix
     and the first backtick-wrapped engine on such lines is /autopilot.

We do NOT ban bare § Section 4.2 or § Section 4.3 pointers because those
are legitimate references to the post-R1 /team handback (§4.2) and
crash-recovery procedure (§4.3). If someone re-introduces /ralph or
/ultrawork as a chain step-3 engine, Pattern 4 catches it along with any
accompanying stale pointer.

Exit 0 if zero matches; exit 1 with per-match `file:line:reason` stderr on
any hit.

Design note on "CI wiring":
The ark-skills repo currently has no .github/workflows, Makefile, or
.pre-commit-config.yaml. The drift lint runs whenever someone invokes
pytest on test_check_chain_drift.py locally. Follow-up: wire both this
script and check_path_b_coverage.py into CI when infrastructure is added.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Each entry: (regex, human-readable reason). Regex flags baked in where needed.
BANNED: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"OMC_EXECUTION_ONLY"),
        "OMC_EXECUTION_ONLY env var does not exist in OMC v4.11.5 "
        "(retired in R1; audit D6.1). Replace with a reference to "
        "autopilot's auto-skip composition — see omc-integration.md § Section 4.1.",
    ),
    (
        re.compile(r"Phase 5 \(docs/ship\)"),
        "autopilot Phase 5 is Cleanup (not 'docs/ship'); corrected in R1. "
        "See autopilot SKILL.md:70-72.",
    ),
    (
        re.compile(r"internal Phase 4 \(execution\)"),
        "autopilot Phase 4 is Validation (not Execution); Execution is Phase 2. "
        "See autopilot SKILL.md:53-68.",
    ),
    (
        # Step-3 engine anchor: only matches when a numbered-list line starts
        # with "3. `/ultrawork`" or "3. `/ralph`". Descriptive mentions of
        # those engines INSIDE a step-3 line (e.g., "via internal /ralph")
        # do NOT match because the first backtick-wrapped engine is /autopilot.
        re.compile(r"^3\.\s+`/(ultrawork|ralph)`", re.MULTILINE),
        "/ultrawork and /ralph are not valid chain step-3 engines under the "
        "2026-04-14 uniformity decision (R2). Use /autopilot as the chain "
        "step-3 engine; these loop/parallel engines run inside autopilot's "
        "Phase 2 (Execution) internally.",
    ),
]

# Target globs relative to --root.
TARGET_GLOBS = [
    "skills/ark-workflow/chains/*.md",
    "skills/ark-workflow/references/omc-integration.md",
]


def _collect_files(root: Path) -> list[Path]:
    """Return every target file under root, sorted."""
    files: list[Path] = []
    for glob in TARGET_GLOBS:
        # Path.glob doesn't support absolute-root + relative-pattern in a
        # cross-version-clean way; handle wildcards manually.
        if "*" in glob:
            parent = root / Path(glob).parent
            pattern = Path(glob).name
            if parent.is_dir():
                files.extend(sorted(parent.glob(pattern)))
        else:
            target = root / glob
            if target.is_file():
                files.append(target)
    return files


def _scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return a list of (line_number, matched_text, reason) for each hit.

    Line numbers are 1-indexed. Matched_text is the matched substring (not
    the whole line) to keep stderr concise.
    """
    hits: list[tuple[int, str, str]] = []
    text = path.read_text()

    for rx, reason in BANNED:
        for m in rx.finditer(text):
            # Resolve 1-indexed line number from byte offset.
            line_no = text.count("\n", 0, m.start()) + 1
            hits.append((line_no, m.group(0), reason))

    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path,
                    help="Repository root (directory containing skills/).")
    args = ap.parse_args()

    files = _collect_files(args.root)
    if not files:
        sys.stderr.write(
            f"No target files found under {args.root}. Expected at least one "
            f"of: {TARGET_GLOBS}\n"
        )
        return 1

    all_hits: list[tuple[Path, int, str, str]] = []
    for f in files:
        for line_no, matched, reason in _scan_file(f):
            all_hits.append((f, line_no, matched, reason))

    if all_hits:
        sys.stderr.write(
            f"Chain drift lint FAILED — {len(all_hits)} banned pattern(s) "
            f"found across {len(files)} scanned file(s):\n\n"
        )
        for path, line_no, matched, reason in all_hits:
            sys.stderr.write(f"{path}:{line_no}: {matched!r}\n  reason: {reason}\n\n")
        return 1

    print(f"OK: zero banned patterns found across {len(files)} target file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
