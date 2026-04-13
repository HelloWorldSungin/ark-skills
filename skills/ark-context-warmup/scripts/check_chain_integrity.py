#!/usr/bin/env python3
"""CI check for /ark-workflow chain files.

Strengthened beyond the plan's initial version (per controller deferred-findings fix):
 1. Scans BOTH ## sections AND the preamble for numbered lists (plan missed ship.md,
    which has no ## sections).
 2. Validates step 0 actually contains '/ark-context-warmup' (plan only checked the
    digit 0 — any line starting with "0." would have passed).
 3. handoff_marker validation: each 'after-step-N' must reference a step that
    exists in the same logical section (preamble or ## section).
"""
import argparse
import re
import sys
from pathlib import Path


_STEP_RE = re.compile(r"^(\d+)\.\s+(.*)$", re.MULTILINE)
_HANDOFF_RE = re.compile(r"handoff_marker:\s*after-step-(\d+)")
_SECTION_SPLIT_RE = re.compile(r"^## ", re.MULTILINE)


def _logical_sections(text: str):
    """Yield (label, body) for each section that could contain a numbered list.

    First yield: ('<preamble>', preamble_body). Then yield one per ## section.
    """
    parts = _SECTION_SPLIT_RE.split(text)
    preamble = parts[0]
    yield ("<preamble>", preamble)
    for p in parts[1:]:
        heading = p.split("\n", 1)[0].strip()
        body = p.split("\n", 1)[1] if "\n" in p else ""
        yield (heading, body)


def _validate_section(path: Path, label: str, body: str) -> list[str]:
    errors = []
    steps = list(_STEP_RE.finditer(body))
    if not steps:
        return errors  # No numbered list in this section — nothing to validate.

    # (A) First step must be 0
    first_step_n = int(steps[0].group(1))
    if first_step_n != 0:
        errors.append(
            f"{path.name}:section={label!r}: first step is {first_step_n}, expected 0 (warmup)"
        )

    # (B) Step 0 text must mention /ark-context-warmup
    if first_step_n == 0:
        step_0_text = steps[0].group(2)
        if "ark-context-warmup" not in step_0_text:
            errors.append(
                f"{path.name}:section={label!r}: step 0 exists but does not reference "
                f"'/ark-context-warmup' — found: {step_0_text!r}"
            )

    # (C) handoff_marker drift: each after-step-N must match an existing step number
    step_numbers = {int(m.group(1)) for m in steps}
    for m in _HANDOFF_RE.finditer(body):
        n = int(m.group(1))
        if n not in step_numbers:
            errors.append(
                f"{path.name}:section={label!r}: handoff_marker references after-step-{n} "
                f"but no such step in this section (steps: {sorted(step_numbers)})"
            )

    return errors


def check_chain(path: Path) -> list[str]:
    """Return list of error strings (empty if OK)."""
    errors: list[str] = []
    text = path.read_text()
    for label, body in _logical_sections(text):
        errors.extend(_validate_section(path, label, body))
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", required=True, type=Path)
    args = ap.parse_args()
    chain_files = sorted(args.chains.glob("*.md"))
    all_errors: list[str] = []
    for chain in chain_files:
        all_errors.extend(check_chain(chain))
    if all_errors:
        for e in all_errors:
            sys.stderr.write(f"{e}\n")
        return 1
    print(f"OK: {len(chain_files)} chain files check clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
