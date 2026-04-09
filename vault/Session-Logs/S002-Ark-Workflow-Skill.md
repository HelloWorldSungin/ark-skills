---
title: "Session: /ark-workflow Skill Implementation"
type: session-log
tags:
  - session-log
  - skill
  - plugin
  - workflow
summary: "Implemented /ark-workflow skill: task triage, scenario detection, weight-class skill chains. 11 tasks via subagent-driven-development, shipped v1.2.0."
prev: "[[S001-MemPalace-Integration]]"
epic: ""
session: "S002"
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Session: /ark-workflow Skill Implementation

## Objective

Create `/ark-workflow`, a new skill that triages any non-trivial task into a weight class (light/medium/heavy) and outputs the optimal ordered skill chain based on scenario and project characteristics.

## Context

Design spec and implementation plan were written and reviewed by Codex in prior sessions. This session executed the 11-task plan using subagent-driven-development.

- Spec: `docs/superpowers/specs/2026-04-08-optimal-workflow-design.md`
- Plan: `docs/superpowers/plans/2026-04-08-ark-workflow-skill.md`
- Branch: `ark-workflow`

## Work Done

### Tasks 1-3: Skeleton (frontmatter, Project Discovery, Scenario Detection, Triage, Workflow)

Created `skills/ark-workflow/SKILL.md` with:
- YAML frontmatter with trigger patterns for auto-detection
- Project Discovery using the existing context-discovery pattern, plus bash scripts for `HAS_UI`, `HAS_VAULT`, `HAS_STANDARD_DOCS`, `HAS_CI`
- Scenario Detection table (5 scenarios: greenfield, bugfix, ship, knowledge capture, hygiene) with disambiguation prompt
- Triage system using risk as primary signal (not file count)
- 7-step Workflow algorithm: discover → detect → classify → look up → resolve → present → hand off

### Tasks 4-6: Skill Chains

Added complete chains for all 5 scenarios:

| Scenario | Weight Classes | Steps |
|----------|---------------|-------|
| Greenfield Feature | Light (6), Medium (15), Heavy (21) | Session-split design for medium+, /TDD, /codex review |
| Bug Investigation & Fix | Light (7), Medium (11), Heavy (14) | /investigate first, re-triage rule, reproducibility caveat |
| Shipping & Deploying | None (6) | Standalone: /review → /ship → /land-and-deploy |
| Knowledge Capture | None (8) | Vault-only: /wiki-status through /claude-history-ingest |
| Codebase Hygiene | Light (6), Medium (8), Heavy (9) | /codebase-maintenance audit first, /cso unconditional in heavy |

Key design decisions from spec:
- Risk is the primary triage signal — a one-file auth change is heavy
- Medium+ greenfield splits into design and implementation sessions
- Ship and Knowledge Capture skip weight classification entirely
- Heavy chains include /claude-history-ingest for compiled insights

### Task 7: Support Sections

Added Condition Resolution (4 trigger categories with example resolved output), Session Handoff protocol, "When Things Go Wrong" (7 failure scenarios), and Re-triage rules.

### Tasks 8-9: Registration and Routing

- Registered `/ark-workflow` in CLAUDE.md under new "Workflow Orchestration" subsection
- Added Routing Rules Template — a copy-paste block projects can add to their CLAUDE.md for auto-triggering

### Task 10: Version Bump

Bumped 1.1.2 → 1.2.0 across VERSION, plugin.json, marketplace.json. Added "workflow" keyword. Wrote CHANGELOG entry.

## Issues Found During Review

### Fixed: Missing `/claude-history-ingest` in Hygiene Heavy

The spec reviewer caught a stray `9. /claude-history-ingest` line pasted into the Re-triage section (Task 7). Removed it. The final code reviewer then caught that Codebase Hygiene Heavy was missing `/claude-history-ingest` as step 9 — it had been accidentally dropped. Added it back.

### Noted (plan-level, not fixed)

- **BRE grep portability**: `grep -q "jsx\|tsx"` in the `HAS_UI` detection script uses BRE alternation that doesn't work on vanilla macOS BSD grep. Works with GNU grep (Homebrew). Plan specifies this form.
- **`HAS_CI` unused**: Detected but never referenced in any condition resolution. Future-proofing hook from the spec.
- **Example chain inconsistency**: Condition Resolution example labels itself "Greenfield Medium" but uses the Heavy pattern (`/executing-plans`). Plan specifies this exact text.

## Process Notes

- **Execution method**: Subagent-driven-development — one Sonnet implementer subagent per task, Sonnet spec reviewer after each, Opus final code reviewer
- **Total tasks**: 11 (10 implementation + 1 verification)
- **Total commits**: 11 (10 from tasks + 1 review fix)
- **Review catch rate**: Spec reviewer caught 1 issue (stray line in Task 7), final code reviewer caught 1 issue (missing step in Hygiene Heavy)

## Artifacts

- `skills/ark-workflow/SKILL.md` — the complete skill (392 lines)
- 11 commits on `ark-workflow` branch, ready for PR

## Related Pages

- [[S001-MemPalace-Integration]] — previous session
