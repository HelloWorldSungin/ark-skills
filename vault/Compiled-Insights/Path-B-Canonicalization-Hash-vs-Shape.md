---
title: "Path B Canonicalization — Hash Count vs Classifier Shape Count"
type: compiled-insight
tags:
  - compiled-insight
  - ci
  - canonicalization
  - ark-workflow
  - path-b
  - skill
summary: "Byte-identity CI on structural chain blocks has two independent scalars: raw-text canonicalized hash count (varies with step count + descriptive text) and classifier-visible shape count (keys on semantic markers only). They diverge any time a pre-step or mid-block addition lengthens the block body without changing its semantic markers. Tracking them separately — and documenting the divergence — prevents false alarms on future additions."
source-sessions:
  - "[[S010-Path-B-Uniformity-Refactor]]"
source-tasks:
  - "[[Arkskill-006-path-b-uniformity]]"
created: 2026-04-15
last-updated: 2026-04-15
---

# Path B Canonicalization — Hash Count vs Classifier Shape Count

## Summary

When a byte-identity CI contract ([[check_path_b_coverage.py]] in this
codebase) validates that a set of structured markdown blocks collapse to
a small number of allowed canonical forms, there are actually **two
independent scalars** to track:

1. **Raw-text canonicalized hash count.** Hash of the block body after
   whitespace + weight-marker stripping. Every line of the block
   contributes. Adding or removing ANY line changes the hash.
2. **Classifier-visible shape count.** A rule-based classifier that
   returns a shape name based on semantic markers (which engine keyword
   appears, which closeout markers are present) — ignores step count and
   line-level content outside the markers.

These scalars are independent. Raw-text hash drift does not imply shape
drift. Conflating them is an easy mistake to make in planning — it led
to the initial "V2 expected count = 2 shapes" guess in the uniformity
refactor plan being wrong (the real answer was 4 classifier shapes / 5
raw-text hashes).

## When the two diverge

Raw-text hashes MULTIPLY faster than classifier shapes when:

- A **pre-step** (like the R10 `/external-context` addition to Migration
  Medium + Heavy) lengthens some blocks but not others. Classifier still
  sees vanilla + team markers; raw-text hash is new.
- **Descriptive text** differs between blocks that share the same
  semantic shape (e.g., one block mentions "internal /ralph" in a
  comment, another mentions "internal /ultrawork"). Classifier ignores
  these because its rules don't key on them; raw-text hash differs.
- **Weight markers** differ (`--quick` vs `--thorough`). In the current
  canonicalization these are deliberately stripped to `--WEIGHT`, so
  they do NOT drive hash divergence — but adding a new weight-like
  variant without updating the strip regex would.

## Why keep both checks

- **Raw-text hash ceiling** catches invisibly-drifting docs: if someone
  edits one vanilla block to have different prose than the others, the
  hash count rises. This is a style/consistency signal — weaker than
  semantic drift, but useful.
- **Classifier shape distribution** catches real semantic drift: if
  someone re-introduces a retired engine like `/ralph` as a standalone
  step-3 engine, the classifier returns "unknown" (and surfaces the
  full flag set for diagnosis).

Running only the raw-hash check would fire on harmless prose edits.
Running only the classifier would miss style drift. Running both is
the right trade — with `--max-distinct-shapes` high enough to tolerate
the expected pre-step variance, and `ALLOWED_SHAPES` pinned to the
semantic distribution.

## Pattern for future additions

If a future chain edit adds a new pre-step to some (but not all)
variants, follow this procedure:

1. **Expect raw-text hash count to rise** by the number of pre-step
   variants introduced. Calculate the new ceiling: pre-edit hashes +
   (number of distinct pre-step patterns × number of variant families).
2. **Expect classifier shape count to stay constant** unless the new
   pre-step adds a semantic marker the classifier keys on (e.g., a new
   engine keyword or closeout marker).
3. **Bump `--max-distinct-shapes` default** in `check_path_b_coverage.py`
   by the expected hash-ceiling increase. Document the rationale in the
   script's help text AND in `omc-integration.md §4`.
4. **Leave `ALLOWED_SHAPES` untouched** unless the semantic distribution
   actually changed. Run the test suite to confirm.
5. **Update `test_real_repo_chains_pass`** to assert the new hash count
   ("5 distinct canonicalized shape" etc.).

## Alternative: step-count-invariant canonicalization

If raw-text hashes become an annoying-enough false-alarm source, the
canonicalization could be extended to strip step-count variance —
e.g., strip leading `N.` prefixes and re-number to a single canonical
form. This trades one kind of invariant (true byte identity) for
another (semantic identity modulo step count). Not yet warranted — the
current single pre-step addition added one extra hash, not ten.

Design principle: keep canonicalization simple and the shape classifier
semantic. Let `max-distinct-shapes` tolerate small variation; rely on
`ALLOWED_SHAPES` distribution for the hard contract.

## Evidence

- [[check_path_b_coverage.py]] `_canonicalize`, `_hash`, `_classify_shape`
- [[S010-Path-B-Uniformity-Refactor]] — R10 commit (`5856c2c`) where the
  divergence first materialized
- [[omc-integration]] § Section 4 footnote documenting the hash-vs-shape
  distinction inline with the closeout table
- [[Execution-Philosophy-Dual-Mode]] — sibling insight on the overall
  dual-mode pattern that this canonicalization CI gates
