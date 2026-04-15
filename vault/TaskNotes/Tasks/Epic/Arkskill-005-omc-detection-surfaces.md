---
tags:
  - task
title: "OMC Plugin Detection Surfaces in /ark-health + /ark-onboard"
task-id: "Arkskill-005"
status: done
priority: medium
project: "ark-skills"
work-type: development
task-type: epic
urgency: normal
session: "S009"
created: "2026-04-14"
last-updated: "2026-04-14"
source-sessions:
  - "[[S009-OMC-Detection-Surfaces]]"
related:
  - "[[Arkskill-003-omc-integration]]"
---

# Arkskill-005: OMC Plugin Detection Surfaces in /ark-health + /ark-onboard

## Summary

Follow-up to [[Arkskill-003-omc-integration]] (v1.13.0 dual-mode routing).
v1.13.0 wired OMC into `/ark-workflow` runtime routing but left the **detection-
surfacing** side unwired: `/ark-health` had no check reporting whether OMC was
installed, and `/ark-onboard` had no upgrade-opportunity entry pointing users
toward it.

This epic closes that gap as v1.14.0 Stream A (shipped alongside Session 2's
Stream B — the `/ark-update` migration framework — in PR #17).

## Scope

Three surfaces, all additive:

1. **`/ark-health` Check 21** — upgrade-style, tier-agnostic, never fails.
   Detection mirrors the canonical `HAS_OMC` probe in
   `skills/ark-workflow/SKILL.md:54-61` (structural parity enforced by
   `diff`-based test). Honors `ARK_SKIP_OMC=true` escape hatch.
2. **`/ark-onboard` Healthy Step 3** — new `Optional capability extensions`
   sub-block (separate from `Available Full-tier upgrades`) to surface OMC
   without implying it promotes the Full tier.
3. **`/ark-onboard` Greenfield Step 18** — non-blocking OMC mention in final
   reminders.

Plus cascading consistency edits: 17 "20 → 21" sites across both files
(diagnostic checklist sync note, integrations heading, results dict,
scorecard, Repair path, Migration path, tier descriptions).

## Design Decisions

- **Tier-agnostic framing.** Check 21 carries `Tier: Standard` but never
  returns `fail` — it surfaces in the scorecard alongside Standard-tier checks
  without gating any tier. This framing was refined via `/codex` review of the
  plan (see Open Questions #2 below for the thread).
- **Separate sub-blocks in Healthy Step 3.** Listing OMC under "Available
  upgrades" followed by "Upgrade to Full tier now?" would have implied OMC
  promotes to Full. Split into two sub-blocks solves this cleanly.
- **Inline probe with byte-diff parity test.** Rather than import/source the
  canonical probe (not an option in markdown), the plan's verification runs
  `diff <(extract_probe workflow) <(extract_probe health)` to catch drift.

## Linked Artifacts

- Spec/plan: `docs/superpowers/plans/2026-04-14-omc-integration-health-onboard.md`
  (v2, post-codex review — 5 findings from FAIL_WITH_REVISIONS HIGH verdict
  all addressed).
- Commits: `28030b3`, `1535214`, `47d7190`, `a5645a3`.
- PR: #17 (combined v1.14.0 release).
- Session log: [[S009-OMC-Detection-Surfaces]].
- Related compiled insight: [[Structural-Probe-Parity-Pattern]].

## Sessions

- [[S009-OMC-Detection-Surfaces]] — 2026-04-14: implementation + codex review + ship
