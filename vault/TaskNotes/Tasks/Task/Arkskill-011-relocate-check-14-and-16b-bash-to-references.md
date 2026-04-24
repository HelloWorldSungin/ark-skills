---
title: "Relocate Check 14a/14b/14c/14d/16b bash blocks to references/ (shrink-to-core follow-up)"
tags:
  - task
  - refactor
  - ark-health
task-id: "Arkskill-011"
task-type: "task"
status: backlog
priority: "low"
project: "ark-skills"
work-type: "refactor"
component: "ark-health"
urgency: "normal"
created: "2026-04-23"
summary: "v1.21.0 Shrink-to-Core moved heavy bash to references/. v1.21.1/2 added new checks inline. Relocate them to honor the original direction once they've stabilized."
---

# Relocate Check 14a/14b/14c/14d/16b bash blocks to references/

## Description

v1.21.0 established a "Shrink-to-Core" pattern for `/ark-health`: longer bash implementations live in `skills/ark-health/references/check-implementations.md` and the main SKILL.md carries only pass/fail semantics + short-bash + pointers. v1.21.1 and v1.21.2 added five new check blocks (14a, 14b, 14c, 14d, 16b) **inline** in SKILL.md, which regresses that direction.

This was flagged by Gemini during the /ccg review for v1.21.4. It's not a correctness issue — the checks work — but the inline bash bloats the SKILL.md at-invocation footprint and breaks the Shrink-to-Core reading discipline.

## Why deferred

The checks landed in v1.21.1/2 as-inline for pragmatism (they had to work before the references extraction could be validated). Now that they're tested and stable (and v1.21.4 has hardened them), relocation is a safe refactor rather than a scope mixer.

## Acceptance criteria

- [ ] `references/check-implementations.md` gains entries § Check 14a, § 14b, § 14c, § 14d, § 16b — each carrying the full bash block
- [ ] SKILL.md Check 14a/14b/14c/14d/16b sections shrink to: block header + pass/warn/skip semantics + "Bash: references/check-implementations.md § Check X" pointer (matching the v1.21.0 pattern used for Checks 5, 6, 8, 10, 11, 16, 18, 20, 22)
- [ ] Sanity-run /ark-health on a local project; all five checks still resolve with the same pass/warn/skip outcomes they did pre-refactor
- [ ] CHANGELOG entry notes the LOC reduction (expect ~200 LOC net removed from SKILL.md)
- [ ] VERSION bump (patch, since behavior unchanged)

## Non-goals

- Don't touch the pass/warn/skip semantics — keep them inline in SKILL.md
- Don't consolidate the five checks into fewer — each has a distinct purpose
- Don't relocate Check 16's bash (the existing pointer already covers it per v1.21.0)

## Related

- v1.21.1 introduced 14a-d: commit c521167
- v1.21.2 introduced 16b: commit 37d284c
- v1.21.3 fixed 16b path-resolver: commit 2c75f07
- v1.21.4 hardened 14d + the palace-global mutex: current branch
- Gemini advisor artifact: `.omc/artifacts/ask/gemini-review-this-pre-push-branch-stack-for-documentation-ux-and-c-2026-04-24T01-38-04-165Z.md` (review #6, verdict "ship after considering")
