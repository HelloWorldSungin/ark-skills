---
tags:
  - task
title: "/ark-workflow Context-Budget Probe (v1.17.0)"
task-id: "Arkskill-007"
status: done
priority: high
project: "ark-skills"
work-type: feature
task-type: epic
urgency: normal
session: "S011"
created: "2026-04-17"
last-updated: "2026-04-17"
source-sessions:
  - "[[S011-Ark-Workflow-Context-Budget-Probe]]"
parent:
  - "[[Arkskill-003-omc-integration]]"
---

# Arkskill-007: /ark-workflow Context-Budget Probe

## Summary

Add step-boundary context-budget awareness to `/ark-workflow` via a single
stdlib-only Python helper (`skills/ark-workflow/scripts/context_probe.py`)
that reads the Claude Code statusline cache at
`.omc/state/hud-stdin-cache.json` and surfaces a three-option mitigation menu
(compact / clear / subagent) at chain entry, each step boundary (Path A only),
and Path B acceptance. Closes the "long chains silently push the session past
the attention-rot zone" gap described in the spec.

Shipped v1.17.0 in 22 atomic commits on branch `context-management`, merged
to master as squash commit `8d42bd8` via PR #19 on 2026-04-17.

## Six CLI modes

| Mode | Purpose |
|------|---------|
| `raw` | JSON probe result; surfaces level/pct/tokens/warnings/reason |
| `step-boundary` | Renders the mitigation menu at a chain step boundary (entry or mid-chain, auto-detected) |
| `path-b-acceptance` | Prints a one-line warning above `[Accept Path B]` when level is nudge/strong |
| `record-proceed` | Atomically persists `proceed_past_level: nudge` iff current level is `nudge` (strong never suppresses) |
| `record-reset` | Atomically clears `proceed_past_level: null` after the user takes `/compact` or `/clear` |
| `check-off` | Atomically flips the Nth checklist item `[ ]` → `[x]` in current-chain.md |

All six modes exit 0 even on missing state/chain files — the probe is
gated behind `HAS_OMC=true` and every failure mode degrades silently to
no menu.

## Key design anchors

- **Atomic chain-file mutations.** All writes to
  `.ark-workflow/current-chain.md` route through a shared
  `chain_file.atomic_update(path, mutator_fn)` helper using
  `fcntl.flock(LOCK_EX)` + temp-file + `os.replace`. Prevents torn writes
  and lost updates between concurrent frontmatter (record-proceed/reset)
  and checklist (check-off) writes. 14/14 bats stress test passes
  (~2 seconds of concurrent check-off + record-proceed asserting
  `^proceed_past_level: (null|nudge)$` count == 1).
- **Nudge-fatigue suppression.** New optional `proceed_past_level`
  frontmatter field. Lifecycle is explicit — `record-proceed` self-detects
  the current level from the cache and persists `"nudge"` only when level
  is `nudge`. Strong-level proceed never silences anything. Caller invokes
  `record-reset` after the user takes (a) `/compact` or (b) `/clear`.
- **Session/freshness rejection layers.** Probe accepts `--expected-cwd`,
  `--expected-session-id`, `--max-age-seconds`. Session-id primary,
  cwd secondary, 300s TTL tertiary for entry-time probes. All mismatches
  → `level: unknown`, silent no-op.
- **Thresholds.** 20% nudge, 35% strong (of `context_window.used_percentage`);
  overrideable via `probe()` kwargs.
- **Block-scalar safe frontmatter writer.** `_set_proceed_past_level` uses
  `line.startswith("proceed_past_level:")` at column 0 — avoids clobbering
  indented occurrences inside `task_summary: |-` block scalars.

## Implementation outline (22 atomic tasks)

| # | Commit | Scope |
|---|--------|-------|
| 1 | `67bcf25` | Scaffold `context_probe.py` with ok-level threshold |
| 2 | `eee6ee8` | Probe threshold logic with nudge/strong overrides |
| 3 | `d2b1aa3` | Sum context-window tokens with graceful fallback |
| 4 | `2072594` | Distinct reason codes for probe error cases |
| 5 | `c57d643` | Session-id + cwd + mtime freshness checks |
| 6 | `187438c` | Atomic chain-file update helper with fcntl lock |
| 7 | `4ecf801` | Scaffold CLI raw mode + argparse |
| 8 | `e1aafc8` | `check-off` CLI mode flips Nth checklist item |
| 9 | `a13939f` | `record-proceed`/`record-reset` frontmatter mutators |
| 10 | `2432707` | Mid-chain mitigation-menu rendering |
| 11 | `e5aef1a` | Entry-render branch for zero-completed chains |
| 12 | `5d97457` | `step-boundary` CLI mode with suppression + degraded fallback |
| 13 | `a635349` | `path-b-acceptance` CLI mode |
| 14 | `c036f48` | Bats integration suite (14 tests incl. atomic stress) |
| 15 | `ebaa321` | Wire step-boundary probe into Step 6.5 "after each step" |
| 16 | `505e373` | Chain-entry probe + `SESSION_ID` resolution to Step 6.5 |
| 17 | `f28434e` | Path-b-acceptance probe in Step 6 dual-path |
| 18 | `e667fc9` | "Session Habits" coaching section in SKILL.md |
| 19 | `f8a9054` | "Session habits" subsection in routing-template.md |
| 20 | `547cc34` | Bump `/ark-update` routing-rules to v1.17.0 |
| 21 | `cbfbe24` | Manual smoke-test runbook for context_probe |
| 22 | `3c0c2c5` | Release v1.17.0 (VERSION / plugin.json / marketplace.json / CHANGELOG) |

One post-review commit `3ecc1c9` filed P2/P3 follow-up notes at
`docs/superpowers/followups/2026-04-17-ark-workflow-context-probe-review-notes.md`.

## Review posture

- Spec + plan passed two `/ccg` review rounds before implementation.
- Each of the 22 tasks passed two-stage review (spec compliance + code quality).
- Final cross-cutting review: **no P1 blockers.** Codex explicit verdict:
  "No P1s found." Gemini: "Proceed with ship."

## Tests at ship time

- `python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py skills/ark-workflow/scripts/test_step_boundary_render.py` → **69/69 passed**
- `bats skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` → **14/14 passed**
- `python3 skills/ark-update/scripts/check_target_profile_valid.py` → OK
- Template byte-equality verified between
  `skills/ark-workflow/references/routing-template.md` and
  `skills/ark-update/templates/routing-template.md`

## Follow-ups (non-blocking)

All filed at `docs/superpowers/followups/2026-04-17-ark-workflow-context-probe-review-notes.md`:

- **P2-1:** Lock file opens with symlink-follow/truncation — swap to `os.open(O_NOFOLLOW)` + `fstat` regular-file check.
- **P2-2:** Session-policy drift — when expected session-id given but cache lacks `session_id`, probe returns `session_mismatch` instead of falling through to cwd/TTL tiers.
- **P2-3:** Checklist parser is body-wide; should scope to `## Steps` block to avoid flipping wrong item if `## Notes` ever has checklists.
- **P2-4:** `record-proceed` re-probes without session/cwd guards (harmless given current-level-unknown preservation but inconsistent with `step-boundary`).
- **P2-5:** Smoke-test runbook should include inline heredoc setup so it's self-contained.
- **P2-6:** SKILL.md `SESSION_FLAG` used in Step 6 before being defined in Step 6.5.
- **P2-7:** "Pause for user decision" mechanism ambiguity for non-interactive agents.
- **P3-1:** Invalid `--step-index` silent instead of stderr-error per spec.
- **P3-2:** `isinstance(..., int)` accepts JSON booleans.
- **P3-3:** Session Habits callout weight.
- **P3-4:** CHANGELOG mode one-liners.

## Cross-links

- Session: [[S011-Ark-Workflow-Context-Budget-Probe]]
- Parent epic: [[Arkskill-003-omc-integration]]
- Session habits insight: [[Session-Habits-For-Context-Longevity]]
- Atomic chain-file mutation pattern: [[Atomic-Chain-File-Mutation-Pattern]]
