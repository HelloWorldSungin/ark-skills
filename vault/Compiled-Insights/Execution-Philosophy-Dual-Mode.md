---
title: "Execution Philosophy — Dual-Mode Ark-Native ↔ OMC-Powered"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - workflow
  - omc
  - dual-mode
  - ark-workflow
  - handback-boundary
summary: "Dual-mode execution — Ark-native (Path A, high checkpoint-density) and OMC-powered (Path B, low checkpoint-density) — co-exists per chain variant with discoverability-biased surfacing, variant-inherited handback with enumerated special cases, and byte-identity CI gating. Patterns replicate to any orchestrator skill that wants to add an autonomous alternative without removing the user-in-the-loop default."
source-sessions:
  - "[[S007-OMC-Integration-Design]]"
source-tasks:
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-13
last-updated: 2026-04-13
---

# Execution Philosophy — Dual-Mode Ark-Native ↔ OMC-Powered

## Summary

When layering an autonomous-execution framework (OMC) onto a user-in-the-loop
orchestrator (`/ark-workflow`), the clean pattern is two co-existing paths per
chain variant, not replacement. Path A preserves the step-by-step default;
Path B front-loads judgment (`/deep-interview`), delegates planning + execution
to OMC, and hands control back to Ark for closeout. Discoverability is biased
toward surfacing Path B when any of four signals fires (OR-any rule), mitigated
by a 3-button UX that always offers `[Use Path A]`. Byte-identity CI
(`check_path_b_coverage.py`) enforces that 19 variants collapse to ≤3 allowed
canonicalized shapes — mechanical gate instead of hand-audit.

## Key Insights

### Checkpoint-Density Axis (Implementation-Side) vs. User-Facing Axis

Two independent axes govern any dual-mode skill:

- **User-facing axis:** Ark-native (Path A) vs. OMC-powered (Path B). Names the
  two paths. Marketing concept.
- **Implementation-side axis:** checkpoint-density. Path A is high-density
  (checkpoint at every step); Path B is low-density (checkpoint at spec + plan,
  then unattended until handback). Governs user experience.

Keeping these separate prevents a subtle confusion: "OMC-powered" does not
*mean* "low checkpoint-density" — it's just a particular implementation choice.
A future Path C could be Ark-native but low-checkpoint (e.g., a one-shot
scripted chain). Designers should reach for the axis, not the brand.

### Discoverability Over Neutrality (OR-Any Signal Rule)

When surfacing a secondary path, bias toward over-surfacing with a cheap
override, not under-surfacing with a silent footer. Rule: **Path B is
recommended when ANY of 4 signals fires** (keyword, Heavy weight, multi-module
scope, explicit-autonomy phrase) + a 3-button UX (`[Accept Path B] [Use Path A]
[Show me both]`). One click of `[Use Path A]` costs the user nothing; missing a
signal costs them hours of inappropriate Path A work.

**Evidence of value:** Initially spec proposed "2-of-4 AND rule" to avoid
over-surfacing. Deep-interview Round 4 (Contrarian) inverted to OR-any because
the override cost is asymmetrically cheap.

### Variant-Inherited Handback with Enumerated Special Cases

Every Path B chain delegates plan + execute to OMC, then hands control back to
Ark for closeout. The handback contract is **variant-inherited** — closeout
matches that variant's Path A tail — except for enumerated special cases:

- **Vanilla (16/19 variants):** closeout starts at `/ark-code-review --{quick |
  thorough}`, ends at `/claude-history-ingest`.
- **Special-A (Hygiene Audit-Only):** closeout is `/wiki-update` → STOP (no
  code review, no ship — findings-only).
- **Special-B (Knowledge-Capture Light/Full):** substitutes
  `/claude-history-ingest` for `/deep-interview` at step 1 (capture is
  reflective, not prospective); closeout is `/wiki-update` →
  `/claude-history-ingest`.

Enumerating rather than generalizing catches future drift. The reference doc
(`skills/ark-workflow/references/omc-integration.md` § Section 4) pins the
per-variant expected closeout as a table; CI byte-identity check asserts ≤3
distinct canonicalized shapes.

### Four Engine-Specific Handback Sub-Contracts

`<<HANDBACK>>` fires at different moments depending on which OMC engine
executes:

- **4.1 `/autopilot`:** after internal Phase 4 (execution); internal Phase 5
  (docs/ship) is SKIPPED.
- **4.2 `/ralph`:** after loop-to-verified exits with success.
- **4.3 `/ultrawork`:** after the last parallel lane's completion signal.
- **4.4 `/team`:** after `team-verify`, **before** `team-fix`. `team-fix`
  (bounded remediation) is reserved for within Ark's own code review, not the
  OMC-internal loop. Keeps Ark as the last-word reviewer.

Each sub-contract is a separate clause in the reference doc, not a footnote.

### Dual-Consumer Probe Pattern (Bash Router + Python Library)

A detection probe that feeds both a bash router and a Python library must
share a canonical constant. Pattern:

1. Define `OMC_CACHE_DIR` once in `references/omc-integration.md` § Section 0.
2. Bash probe (`SKILL.md` Project Discovery) comments the canonical path:
   `# OMC_CACHE_DIR canonical: ~/.claude/plugins/cache/omc`.
3. Python probe (`availability.py`) comments the same path and uses
   `Path.home() / ".claude" / "plugins" / "cache" / "omc"` as the runtime
   default.

Neither file duplicates the literal without a comment pointer. Any drift is a
code-review smell.

### Release-Artifact Lockstep Rule

For any release, all of `VERSION`, `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, and `CHANGELOG.md` bump in the same commit
at the same version number. Grep-verified before the commit:

```
diff <(grep -o '1\.13\.0' VERSION) <(grep -o '1\.13\.0' .claude-plugin/plugin.json)
```

This is [[feedback_version_bump]] (user memory) — captured here as an
artifact-level pattern, not just personal preference.

### Emergency-Rollback Env Var Pattern

Any optional-dependency integration should ship with a user-facing env var
that forces "absent" regardless of detection. For this integration:
`ARK_SKIP_OMC=true` forces `HAS_OMC=false`. Rationale:

- Downstream projects may have adopted a grep-pinning recipe during the prior
  version that suppresses the new integration. An env var is clean
  documentation ("export this") vs. editing their hardening config.
- Incident response: if a Path B invocation turns out to be broken in a
  downstream context, `ARK_SKIP_OMC=true` is a 3-keystroke workaround while
  the fix ships.

The bash probe honors it after detection:

```bash
[ "$ARK_SKIP_OMC" = "true" ] && HAS_OMC=false
```

### Byte-Identity CI Gate Instead of Hand-Audit

19 variants × per-variant Path B block = mechanical repetition risk. Instead
of hand-auditing each block for template conformance, write a canonicalizer
that strips variant-specific markers (weight, `{weight}` placeholders,
whitespace), hashes the result, and asserts ≤N distinct hashes. Any edit that
drifts the template breaks CI immediately, without review surface.

`check_path_b_coverage.py`:
- Extracts every `### Path B` block body.
- Canonicalizes: strips `--quick`, `--thorough`, `{weight}`, whitespace.
- Asserts total count matches `--expected-blocks`.
- Asserts distinct hashes ≤ 3.
- Asserts shape distribution (16 vanilla + 1 special-a + 2 special-b).
- Asserts every block contains `<<HANDBACK>>` + `/deep-interview` OR
  `/claude-history-ingest`.

Running time: <50 ms. Replaces a 19-section hand-audit.

### Classifier-Marker Selection — Key on Uniqueness, Not Absence

Initial Special-B classifier used `/deep-interview` absence. Failed because
Special-B's template includes the substring `/deep-interview` inside a
parenthetical ("substitutes for `/deep-interview`"). Fix: key on
`/wiki-ingest` (uniquely present in Special-B's step 3). General rule: for
text-based classifiers, key on uniquely-present distinguishing markers, not on
the absence of commonly-present markers.

### Plan-Arithmetic Cross-Check

Planning documents can carry off-by-one errors even after multi-reviewer
consensus. Iteration 2 of ralplan had `--expected-blocks 10` and
`--expected-blocks 13` that summed wrong against the per-file counts
(3+3+3=9, not 10). Both Architect and Critic APPROVE passes missed it. The
byte-identity CI check caught it in <1 second. **Mechanical gates > human
counting.**

## Evidence

- Plan: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md` (consensus
  iteration 2, Architect + Critic APPROVE).
- Spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md` (5-round
  deep interview, Round 4 Contrarian → OR-any + show-always).
- Reference doc: `skills/ark-workflow/references/omc-integration.md`
  (Sections 0–6).
- CI script: `skills/ark-context-warmup/scripts/check_path_b_coverage.py`.
- Session log: [[S007-OMC-Integration-Design]].
- User memory: [[feedback_version_bump]] (release-artifact lockstep).

## Implications

- Any new orchestrator skill that wants to add an autonomous alternative
  should follow this pattern: separate paths per variant, discoverability-
  biased surfacing with an override, variant-inherited handback with
  enumerated special cases, and byte-identity CI instead of hand-audit.
- Any new engine added to OMC (e.g., `/ccg`) should inherit the Section 4
  handback sub-contract pattern — enumerate its own handback boundary as a
  4.5 clause, don't generalize away from the existing four.
- The `OMC_CACHE_DIR` single-source canonical-constant pattern should be
  reused whenever a new optional dependency lands that has dual consumers
  (bash + Python).
- Telemetry schema from this integration (`{ts, has_omc, ark_skip_omc,
  signals_matched, recommendation, path_selected, variant}`) is reusable as a
  starting template for any multi-path skill's observability layer.
