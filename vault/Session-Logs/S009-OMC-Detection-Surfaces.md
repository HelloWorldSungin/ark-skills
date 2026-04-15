---
title: "Session 9: OMC Detection Surfaces in /ark-health + /ark-onboard (v1.14.0 Stream A)"
type: session-log
tags:
  - session-log
  - S009
  - skill
  - ark-health
  - ark-onboard
  - omc
  - dual-mode
  - codex-review
  - release
summary: "Shipped OMC plugin detection to /ark-health (Check 21) and /ark-onboard (Healthy Step 3 + Greenfield Step 18 + scorecard). Upgrade-style, tier-agnostic. Structural parity with canonical HAS_OMC probe enforced by diff. Combined v1.14.0 release alongside Session 2's Stream B. PR #17."
session: "S009"
status: complete
date: 2026-04-14
prev: "[[S008-Ark-Update-Framework]]"
epic: "[[Arkskill-005-omc-detection-surfaces]]"
source-tasks:
  - "[[Arkskill-005-omc-detection-surfaces]]"
related:
  - "[[S007-OMC-Integration-Design]]"
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-14
last-updated: 2026-04-14
---

# Session 9: OMC Detection Surfaces in /ark-health + /ark-onboard (v1.14.0 Stream A)

## Objective

Close the detection-surface gap left by v1.13.0 (Arkskill-003): `/ark-workflow`
had the `HAS_OMC` probe wired into runtime routing, but `/ark-health` had no
diagnostic check reporting OMC presence and `/ark-onboard` had no upgrade
opportunity surfacing it to users.

Goal: 3 additive surfaces in 2 skill files + all cascading "20 → 21" consistency
edits. Ship as v1.14.0 Stream A alongside Session 2's Stream B (`/ark-update`
framework).

## Context

- [[S007-OMC-Integration-Design]] shipped v1.13.0 dual-mode routing but
  explicitly deferred detection surfaces to a follow-up.
- [[S008-Ark-Update-Framework]] ran in parallel on the same branch
  (`ark-update`) as a separate worktree session; coordination was explicit —
  neither stream shipped solo, version bump was batched.
- Branch: `ark-update`. Worktree: `/Users/sunginkim/.superset/worktrees/ark-skills/ark-update`.

## Work Done

### /ark-workflow triage (Greenfield-Light)

`HAS_UI=false, HAS_VAULT=true, HAS_STANDARD_DOCS=true, HAS_CI=false, HAS_OMC=true`.
No Path B signals fired (keyword/Heavy-weight/multi-module/explicit-autonomy all
negative) — rendered Path A only with `[Show me both]` footer.

### /ark-context-warmup

NotebookLM lane skipped (commands returned null). Wiki lane returned 3 matches
including `S007-OMC-Integration-Design.md` (direct precedent) and
`Execution-Philosophy-Dual-Mode.md` (pattern doc). No in-flight collisions
detected — just 1 in-progress task and 2 done.

### /superpowers:writing-plans

Wrote `docs/superpowers/plans/2026-04-14-omc-integration-health-onboard.md` v1.
4 tasks, per-file atomic commits, structural verification steps.

### /codex (consult mode)

**Verdict: FAIL_WITH_REVISIONS, Confidence: HIGH.** Five findings, all valid:

1. Bash probe wasn't byte-for-byte canonical — v1 used `if skip / elif detect
   / else upgrade`; canonical is `detect → set HAS_OMC → apply override after`.
2. "Standard tier" framing was incoherent — a check that never fails cannot be
   a Standard-tier gating requirement.
3. Missing 8 cascading "20 → 21" consistency edits beyond the 5 user-specified
   surfaces (e.g., `ark-health:99`, `ark-health:654`, shared diagnostic checklist
   in `ark-onboard:193-251`, repair-path Run-all-20 sites at 2379/2490/2511/2546).
4. Internal verification contradiction — Task 2 Step 1 decided NOT to update
   "Checks 7–20" but Task 2 Step 5 still greped for "Checks 7–21".
5. Non-atomic commits — 4 commits across 2 files left intermediate inconsistency.

### Plan v2

Revised plan to address all 5 findings:

1. Bash probe now mirrors canonical structure exactly; added `diff
   <(extract_probe workflow) <(extract_probe health)` parity check.
2. Kept `Tier: Standard` label (per user's original instruction) but marked
   `tier-agnostic` everywhere, and split Healthy Step 3 into separate
   sub-blocks: `Available Full-tier upgrades` vs `Optional capability
   extensions (do NOT promote tier)`.
3. Expanded scope to all 17 stale "20" sites (Task 2 + Task 3 + Task 4).
4. Removed the contradictory grep; kept "Checks 7–20" with parenthetical
   "(Check 21 is exempt — runs unconditionally)".
5. Consolidated to 2 atomic per-file commits.

### Implementation

Two atomic commits:

- `28030b3` feat(ark-health): Check 21 OMC plugin — insertion + all 8
  cascading 20→21 edits in one file (intro, abort-prevention, line 99
  CLAUDE.md-missing note, Step 1 header+body, results dict, tier assignment
  (new tier-agnostic paragraph + expanded warn+upgrade note), Output Format
  Integrations block, authoritative-skill claim at :654).
- `1535214` feat(ark-onboard): OMC awareness — diagnostic checklist sync note,
  integrations heading 12-21, Check 21 row, results dict, skip rule +
  exemption, Greenfield Step 18 reminder + conditional adjustment, Migration
  Step 13 full-21-check, Repair steps 2379/2490/2511, Healthy Step 1 Run-all-
  21, Healthy Step 3 sub-block restructure, Full-tier 2546 wording, scorecard
  ASCII row + count bump 2→3, collapse rules `check 21 → "OMC plugin"`,
  Full-tier table line tier-agnostic note, warn-checks expanded note.

### /ark-code-review --quick

Found 2 issues, both fixed in `47d7190`:

- **HIGH:** `ark-health:565` section header `### Step 1: Run All 20 Checks`
  was missed — body was updated but heading wasn't.
- **MEDIUM:** `ark-onboard:2546` original wording "All 21 checks pass. Full
  tier active." contradicted itself when Check 21 might be in upgrade state.
  Reworded to: "Checks 1-20 all pass. Full tier active. (Check 21 OMC is
  tier-agnostic — install separately if interested.)"

Plan doc committed as `a5645a3` (post-codex v2).

### Ship coordination

Paused after /ark-code-review per user choice "C then A": commit the plan
(C), then wait for Session 2 (A). When Session 2 signaled completion, the
coordinated release was already in place — Session 2 had handled the version
bump (1.13.0 → 1.14.0 across VERSION/plugin.json/marketplace.json), written
the combined CHANGELOG covering both streams, made release commit `11bad46`,
pushed ark-update, and opened PR #17. All 4 Stream A commits are in PR #17.

Session 2 additionally extended the diagnostic surface by adding their own
**Check 22: Plugin Versioning** on top of my Check 21 — the skill ships with
22 checks total in v1.14.0.

## Decisions Made

- **`/codex` is load-bearing for plans involving canonical constants.** The v1
  plan's `grep`-based verification would have landed with a broken internal
  contradiction and drifted probes. The diff-based parity check emerged
  directly from finding #1 and is now reusable convention — see
  [[Structural-Probe-Parity-Pattern]].
- **"Tier: Standard" + `tier-agnostic` is the right framing for optional-but-
  surfaced capabilities.** Keeping the tier label preserves scorecard
  placement semantics (surface alongside Standard-tier rows) while the
  `tier-agnostic` annotation makes it explicit the check never gates
  classification. Cleaner than inventing a new tier category.
- **Healthy Step 3 structural split.** "Available Full-tier upgrades" +
  "Optional capability extensions (do NOT promote tier)" is the
  no-regrets UX for mixing promote-tier upgrades with non-promoting
  extensions. Session 2's Check 22 (Plugin Versioning) fits the same
  pattern — if it ever ships a UI on /ark-onboard, the sub-block scaffolding
  is already there.
- **Ship as a combined release.** Coordinating with Session 2 for a single
  v1.14.0 release covering both streams is cleaner than sequential 1.14.0 +
  1.14.1. User's version-bump memory already encoded this preference.

## Issues & Discoveries

- **Plan line-number brittleness.** Line numbers drift as edits land; a
  plan that references line 2519 may land at 2527 after prior edits. The
  fix-up commit `47d7190` was a direct result of the line-header miss
  (body-only edit while header moved). Future plans should prefer context-
  anchored edits (`old_string`/`new_string` with unique surrounding
  context) over line-number-keyed instructions.
- **Hook false positives.** The runtime's "Command failed" hook fired on
  several bash commands that actually succeeded (git check-ignore returning
  1 when not ignored, etc.). Noise; ignored.
- **Session 2 already wrote S008 and expanded Check 21 → Check 22.** Clean
  extension — no conflict with my commits.

## Next Steps

- **PR #17 merge** — awaiting human review.
- **Check 22 compiled insight** — Session 2's Plugin Versioning check is a
  candidate for a separate compiled-insight page capturing the version-drift
  detection pattern. Not blocking.
- **Memory update** — user's memory system ("Always bump plugin version")
  now has a real-world precedent for the coordination pattern: 2 worktree
  sessions, shared branch, one coordinated bump. Consider extending the
  memory to cover multi-session coordination explicitly.
