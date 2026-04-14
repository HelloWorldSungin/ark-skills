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
#
# Six canonicalized shapes now allowed (was 3 prior to P2-1 hardening): the
# base `vanilla` shape invokes `/autopilot` (Section 4.1). Three engine-specific
# shapes wire the remaining Section 4 sub-contracts into real chains:
#   - `ralph`      → Performance Medium + Heavy (Section 4.2)
#   - `ultrawork`  → Greenfield Heavy (Section 4.3)
#   - `team`       → Migration Heavy (Section 4.4, handback after team-verify/before team-fix)
# Plus the two pre-existing special-case shapes.
ALLOWED_SHAPES = {
    "vanilla": 12,
    "ralph": 2,
    "ultrawork": 1,
    "team": 1,
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
    """Return one of: 'vanilla', 'ralph', 'ultrawork', 'team',
    'special-a-hygiene-audit-only', 'special-b-knowledge-capture', or 'unknown'.

    Order matters:
      1. Special-B is the distinctive-marker variant (has `/wiki-ingest` as an
         actual step); check first because its block mentions `/deep-interview`
         in a parenthetical ("substitutes for `/deep-interview`").
      2. Special-A: `STOP` + no `/claude-history-ingest` (findings-only).
      3. Engine-specific shapes key on the step-3 engine keyword. `/team`,
         `/ralph`, `/ultrawork` each appear only in their own shape; vanilla
         contains none of them.
      4. Vanilla: `/autopilot` present + `/ark-code-review` in closeout.

    We do NOT rely on `/deep-interview` absence for classification because
    Special-B mentions it in a parenthetical.
    """
    has_wiki_ingest = "/wiki-ingest" in canonical
    has_stop = "STOP" in canonical
    has_history_ingest = "/claude-history-ingest" in canonical
    has_code_review = "/ark-code-review" in canonical
    has_team = "/team" in canonical
    has_ralph = "/ralph" in canonical
    has_ultrawork = "/ultrawork" in canonical
    has_autopilot = "/autopilot" in canonical
    # Special-B has /wiki-ingest as an actual step (unique to reflective capture).
    if has_wiki_ingest:
        return "special-b-knowledge-capture"
    # Special-A: findings-only, STOP in closeout, no further mining.
    if has_stop and not has_history_ingest:
        return "special-a-hygiene-audit-only"
    # Engine-specific vanillas — each engine keyword is unique to its own shape.
    if has_team:
        return "team"
    if has_ralph:
        return "ralph"
    if has_ultrawork:
        return "ultrawork"
    # Vanilla: default /autopilot engine + closeout inherits Path A.
    if has_autopilot and has_code_review:
        return "vanilla"
    return "unknown"


def _classification_flags(canonical: str) -> dict:
    """Return the flag set used by _classify_shape(), for diagnostic output
    on 'unknown' classifications. A developer hitting the "did not classify
    into an allowed shape" error can use this to figure out which marker(s)
    were unexpectedly present or missing without re-running the classifier
    mentally against the raw markdown.
    """
    return {
        "wiki_ingest": "/wiki-ingest" in canonical,
        "stop": "STOP" in canonical,
        "history_ingest": "/claude-history-ingest" in canonical,
        "code_review": "/ark-code-review" in canonical,
        "team": "/team" in canonical,
        "ralph": "/ralph" in canonical,
        "ultrawork": "/ultrawork" in canonical,
        "autopilot": "/autopilot" in canonical,
    }


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
    ap.add_argument("--max-distinct-shapes", type=int, default=6,
                    help="Max distinct canonicalized hashes (default 6 — see ALLOWED_SHAPES)")
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
        unknown_details: list[str] = []
        for path, _, canonical in canonicals:
            shape = _classify_shape(canonical)
            distribution[shape] = distribution.get(shape, 0) + 1
            if shape == "unknown":
                flags = _classification_flags(canonical)
                flag_str = ", ".join(f"{k}={v}" for k, v in flags.items())
                unknown_details.append(f"{path.name} markers={{{flag_str}}}")
        for shape, expected_count in ALLOWED_SHAPES.items():
            actual = distribution.get(shape, 0)
            if actual != expected_count:
                errors.append(
                    f"shape '{shape}' count = {actual}, expected {expected_count}"
                )
        if unknown_details:
            errors.append(
                f"{len(unknown_details)} block(s) did not classify into an "
                f"allowed shape:"
            )
            errors.extend(f"  - {d}" for d in unknown_details)

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
