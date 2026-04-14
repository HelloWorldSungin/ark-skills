#!/usr/bin/env python3
"""CI check for Path B (OMC-powered) block coverage across /ark-workflow chains.

Enforces the per-variant expected-closeout contract documented in
skills/ark-workflow/references/omc-integration.md § Section 4.

What this script checks:
  1. Total Path B blocks across chain files matches --expected-blocks.
  2. Canonicalized blocks collapse to ≤3 distinct hashes (Vanilla, Special-A, Special-B).
  3. Every block contains the literal `<<HANDBACK>>` marker.
  4. Every block contains either `/deep-interview` OR `/claude-history-ingest`.
  5. Distribution of shapes matches ALLOWED_SHAPES when --expected-blocks == 19.

Canonicalization strips:
  - The scenario-specific header line (`### Path B (OMC-powered...)`).
  - The `{weight}` placeholder.
  - The `--quick` and `--thorough` weight markers (tweak #1 from executor brief —
    otherwise Light/Medium Vanilla blocks would hash differently from Heavy
    Vanilla blocks and inflate the distinct-hash count).
  - Leading/trailing whitespace on each line.
  - Collapse of repeated internal whitespace.

Exit 0 on success; 1 with per-variant error messages on failure.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

# Expected distribution when --expected-blocks == 19 (the full plan target).
ALLOWED_SHAPES = {
    "vanilla": 16,
    "special-a-hygiene-audit-only": 1,
    "special-b-knowledge-capture": 2,
}

_PATH_B_HEADING_RE = re.compile(
    r"^###\s+Path B\s+\(OMC-powered[^)]*\)\s*$", re.MULTILINE
)
_NEXT_HEADING_RE = re.compile(r"^(##\s|###\s)", re.MULTILINE)
# Tweak #1: strip weight markers in the canonicalization step, not just the
# `{weight}` placeholder.
_WEIGHT_MARKERS_RE = re.compile(r"--(?:quick|thorough)")
_WEIGHT_PLACEHOLDER_RE = re.compile(r"\{weight\}")
_MULTISPACE_RE = re.compile(r"[ \t]+")


def _extract_path_b_blocks(text: str) -> list[str]:
    """Return every Path B block body (without the heading line).

    A block starts at the heading `### Path B (OMC-powered...)` and ends at the
    next `##` or `###` heading, or EOF.
    """
    blocks: list[str] = []
    for m in _PATH_B_HEADING_RE.finditer(text):
        start = m.end()
        # Find next heading after this position.
        next_hdr = _NEXT_HEADING_RE.search(text, pos=start)
        end = next_hdr.start() if next_hdr else len(text)
        blocks.append(text[start:end])
    return blocks


def _canonicalize(block: str) -> str:
    """Normalize a Path B block body for byte-identity comparison."""
    stripped = block.strip()
    stripped = _WEIGHT_MARKERS_RE.sub("--WEIGHT", stripped)
    stripped = _WEIGHT_PLACEHOLDER_RE.sub("WEIGHT", stripped)
    # Normalize per-line whitespace.
    lines = [_MULTISPACE_RE.sub(" ", ln).rstrip() for ln in stripped.splitlines()]
    # Drop fully-empty surrounding lines.
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _hash(canonical: str) -> str:
    return hashlib.sha256(canonical.encode()).hexdigest()


def _classify_shape(canonical: str) -> str:
    """Return one of: 'vanilla', 'special-a-hygiene-audit-only',
    'special-b-knowledge-capture', or 'unknown'."""
    has_interview = "/deep-interview" in canonical
    has_history_ingest = "/claude-history-ingest" in canonical
    has_stop = "STOP" in canonical
    has_wiki_ingest = "/wiki-ingest" in canonical or "wiki-ingest" in canonical
    if has_stop and not has_history_ingest:
        return "special-a-hygiene-audit-only"
    if has_history_ingest and has_wiki_ingest and not has_interview:
        return "special-b-knowledge-capture"
    if has_interview:
        return "vanilla"
    return "unknown"


def _collect(chain_dir: Path) -> list[tuple[Path, str]]:
    """Return list of (file_path, raw_block_body) across all chain files."""
    collected: list[tuple[Path, str]] = []
    for md in sorted(chain_dir.glob("*.md")):
        text = md.read_text()
        for block in _extract_path_b_blocks(text):
            collected.append((md, block))
    return collected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", required=True, type=Path,
                    help="Directory containing chain *.md files")
    ap.add_argument("--expected-blocks", type=int, default=19,
                    help="Expected total Path B blocks (default 19)")
    ap.add_argument("--max-distinct-shapes", type=int, default=3,
                    help="Max distinct canonicalized hashes (default 3)")
    args = ap.parse_args()

    errors: list[str] = []
    blocks = _collect(args.chains)

    # Assertion 1: total blocks.
    if len(blocks) != args.expected_blocks:
        errors.append(
            f"total Path B blocks = {len(blocks)}, expected {args.expected_blocks}"
        )

    # Short-circuit trivial success (Phase 1 verifies with --expected-blocks 0).
    if args.expected_blocks == 0 and not blocks:
        print("OK: 0 Path B blocks (foundation phase)")
        return 0

    # Assertion 2: marker presence.
    # Assertion 3: interview-or-ingest presence.
    canonicals: list[tuple[Path, str, str]] = []
    for path, block in blocks:
        if "<<HANDBACK>>" not in block:
            errors.append(f"{path.name}: Path B block missing <<HANDBACK>> marker")
        if "/deep-interview" not in block and "/claude-history-ingest" not in block:
            errors.append(
                f"{path.name}: Path B block missing both /deep-interview and "
                "/claude-history-ingest (at least one required)"
            )
        canonical = _canonicalize(block)
        canonicals.append((path, block, canonical))

    # Assertion 4: distinct hash count.
    distinct = {_hash(c) for _, _, c in canonicals}
    if len(distinct) > args.max_distinct_shapes:
        errors.append(
            f"distinct canonicalized shapes = {len(distinct)}, "
            f"expected ≤ {args.max_distinct_shapes}"
        )

    # Assertion 5: shape distribution (only when full coverage expected).
    if args.expected_blocks == 19:
        distribution: dict[str, int] = {}
        unknown_files: list[str] = []
        for path, _, canonical in canonicals:
            shape = _classify_shape(canonical)
            distribution[shape] = distribution.get(shape, 0) + 1
            if shape == "unknown":
                unknown_files.append(path.name)
        for shape, expected_count in ALLOWED_SHAPES.items():
            actual = distribution.get(shape, 0)
            if actual != expected_count:
                errors.append(
                    f"shape '{shape}' count = {actual}, expected {expected_count}"
                )
        if unknown_files:
            errors.append(
                f"{len(unknown_files)} block(s) did not classify into an "
                f"allowed shape: {unknown_files}"
            )

    if errors:
        for e in errors:
            sys.stderr.write(f"{e}\n")
        return 1

    print(
        f"OK: {len(blocks)} Path B block(s); "
        f"{len(distinct)} distinct canonicalized shape(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
