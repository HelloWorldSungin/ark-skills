---
title: "Structural Probe Parity — Byte-Diff Verification for Duplicated Bash Snippets"
type: compiled-insight
tags:
  - skill
  - skill-quality
  - codex-review
  - drift-detection
  - canonical-constants
  - ark-workflow
  - ark-health
summary: "When a canonical bash probe is duplicated into copy sites, substring-level grep verification misses structural drift. Use diff <(extract_probe canonical) <(extract_probe copy) to enforce byte-level structural parity. Pattern emerged from /codex finding on Arkskill-005."
source-sessions:
  - "[[S009-OMC-Detection-Surfaces]]"
  - "[[S007-OMC-Integration-Design]]"
source-tasks:
  - "[[Arkskill-005-omc-detection-surfaces]]"
related:
  - "[[Plugin-Architecture-and-Context-Discovery]]"
  - "[[Shell-Script-Safety-Patterns]]"
  - "[[Codex-Review-Non-Convergence]]"
created: 2026-04-14
last-updated: 2026-04-14
---

# Structural Probe Parity — Byte-Diff Verification for Duplicated Bash Snippets

## The Problem

When an ark-skills skill documents a canonical bash probe (e.g., the `HAS_OMC`
detection in `skills/ark-workflow/SKILL.md:54-61`), other skills that need to
invoke the same detection end up **inlining a copy** of the probe. Markdown
doesn't have `#include`; the skill text is the contract.

Functional equivalence is easy to eyeball. **Structural parity is not.** Two
snippets can produce identical outputs in every observed case while differing
in ways that matter:

- Ordering — canonical does `detect → set flag → apply ARK_SKIP_OMC override`;
  a copy might do `if skip → elif detect → else upgrade`. Same outputs for
  known inputs, but when OMC changes its cache-dir location or the override
  acquires a new third state, the re-mapping becomes a subtle refactor.
- Output messages — `"PASS: OMC detected"` vs `"HAS_OMC=true"` break any
  downstream consumer that greps for the canonical literal.
- Env-var naming — `ARK_SKIP_OMC` vs a near-miss rename eliminates the
  emergency-rollback contract.

## Why Substring Grep Isn't Enough

The natural verification pattern is:

```bash
grep -c 'command -v omc' skills/ark-health/SKILL.md
grep -c 'plugins/cache/omc' skills/ark-health/SKILL.md
grep -c 'ARK_SKIP_OMC' skills/ark-health/SKILL.md
```

All return `≥1`, the test "passes," and the copy has completely rearranged
control flow.

`/codex` caught this on the Arkskill-005 plan review: the v1 plan rewrote the
probe into an `if/elif/else` cascade and the verification was blind to the
structural drift. Verdict was FAIL_WITH_REVISIONS, Confidence HIGH, finding
#1.

## The Pattern

Instead of substring greps, compare **canonicalized block extracts**:

```bash
extract_probe() {
  awk '
    /^if command -v omc/{flag=1}
    flag {print}
    /^\[ "\$ARK_SKIP_OMC" = "true" \] && HAS_OMC=false$/{flag=0; exit}
  ' "$1" | grep -vE '^\s*#|^\s*$'
}
diff <(extract_probe skills/ark-workflow/SKILL.md) <(extract_probe skills/ark-health/SKILL.md)
echo "diff exit: $?"
```

Components:

1. **AWK block extractor** — delimited by unique start/end markers that are
   part of the canonical block itself. The start marker (`if command -v omc`)
   and end marker (`ARK_SKIP_OMC` override line) are stable identifiers that
   every valid copy must contain.
2. **Comment + blank-line filter** — `grep -vE '^\s*#|^\s*$'` lets copies
   add their own comments (documentation density varies per skill) without
   breaking parity.
3. **`diff` exit code** — `0` means byte-identical canonical block. Non-zero
   is a drift alarm.

## When to Use

Every time a bash probe is duplicated across ≥2 skill files:

- Canonical: `skills/ark-workflow/SKILL.md` (the source-of-truth skill)
- Copy site 1: `skills/ark-health/SKILL.md` (the new Check N)
- Copy site 2 (future): `skills/ark-onboard/SKILL.md` if it ever inlines
  detection instead of referencing the check
- Reference doc: `skills/ark-workflow/references/omc-integration.md` Section 0
  (canonical constants — URL, env-var name, cache-dir path)

Pair the diff check with a **literal URL grep** across all three file sets:

```bash
EXPECTED_URL="https://github.com/anthropics/oh-my-claudecode"
grep -c "$EXPECTED_URL" skills/ark-health/SKILL.md      # copy
grep -c "$EXPECTED_URL" skills/ark-onboard/SKILL.md     # copy
grep -c "$EXPECTED_URL" skills/ark-workflow/references/omc-integration.md  # canonical
```

The URL grep catches the complementary drift class: structural probes match
but the install-hint URL silently renamed.

## Generalization

The pattern applies to any duplicated canonical block:

| Canonical block | Start marker | End marker |
|---|---|---|
| `HAS_OMC` probe | `if command -v omc` | `ARK_SKIP_OMC.*HAS_OMC=false$` |
| `HAS_VAULT` detection | `if [ -d vault ]` | vault-dir closing conditional |
| `ARK_SKILLS_ROOT` resolve | `if [ -n "${CLAUDE_PLUGIN_DIR:-}"` | the final `export` or `exit` line |
| Context-discovery exemption | `## Context-Discovery Exemption` | next `##` heading |

For each, author the extractor once in the skill's verification step, then
re-use the pattern across all copy sites.

## CI Integration

Worth promoting to a dedicated script (e.g., `skills/shared/check_canonical_parity.sh`)
that runs over a manifest of (canonical_file, copy_file, start_marker, end_marker)
tuples. Today the diff is embedded in per-plan verification steps; over time
each recurring pair becomes a candidate for the manifest.

## Related

- [[Codex-Review-Non-Convergence]] — why second-opinion review catches gaps
  first-party verification misses.
- [[Plugin-Architecture-and-Context-Discovery]] — the context-discovery
  pattern is itself a candidate for structural-parity enforcement across
  skills that duplicate it.
- [[Shell-Script-Safety-Patterns]] — probes that mutate env vars (export
  lines, subshell scoping) have additional structural drift surfaces.
