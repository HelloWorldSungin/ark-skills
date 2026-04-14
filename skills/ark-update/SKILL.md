---
name: ark-update
description: Version-driven migration framework — replays pending destructive migrations then converges downstream project to the current ark-skills target profile. Runs when plugin bumps add new conventions. Distinct from /ark-onboard repair (failure-driven) and /ark-health (diagnostic-only).
---

# Ark Update

**Status: v1.0 skeleton — engine implementation in progress.** This stub establishes the skill directory, context-discovery exemption, command surface, and POSIX-only declaration. Full engine lands in Step 1+ of the ralplan build sequence (`.omc/plans/ralplan-ark-update.md`).

Version-driven migration framework for the ark-skills plugin. Every downstream project that installed ark-skills at an older version (or needs to catch up to HEAD) can run `/ark-update` to:

1. **Phase 1 — Replay pending destructive migrations** (rare; per-version YAML under `migrations/vX.Y.Z.yaml`)
2. **Phase 2 — Converge project to the current target profile** (every run; declarative YAML at `target-profile.yaml`)

The engine is written in Python (`scripts/migrate.py`). This SKILL.md is a thin LLM-facing wrapper that handles planning, progress rendering, user prompts, and the `/ark-update` command surface.

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete — because `/ark-update` may be the tool that *fixes* a broken CLAUDE.md through target-profile convergence. When CLAUDE.md is absent or malformed, the engine detects project state from the filesystem (via `.ark/migrations-applied.jsonl` bootstrap) and refuses to run on specific broken-file classes that require human judgment, pointing the user to `/ark-onboard repair`.

Never abort because CLAUDE.md is missing. That is one of the states this skill is designed to handle.

## Platform Support (v1.0)

**POSIX-only** (macOS + Linux + WSL2 bash). Native Windows cmd/powershell is NOT supported in v1.0. The `ARK_SKILLS_ROOT` resolver uses shell arithmetic and the Stage-5 manual runbook uses process substitution (`<(git show ...)`), both POSIX-specific. Windows-native support is a v1.1 follow-up if user demand exists.

## Command Surface (planned)

```bash
/ark-update              # full run: replay pending destructive + converge to target profile
/ark-update --dry-run    # plan report only; no writes
/ark-update --force      # skip dirty-tree refusal (use at your own risk)
```

## Boundary with Sibling Skills

| Skill | Trigger | Scope |
|-------|---------|-------|
| `/ark-onboard repair` | Failure-driven ("a /ark-health check failed, fix it") | Repair of broken state |
| `/ark-update` | Version-driven ("plugin updated, converge project conventions") | Replay destructive migrations + converge to target profile |
| `/ark-health` | Diagnostic ("what's the state?") | Read-only; surfaces version drift as "upgrade available: run /ark-update" |

`/ark-update` and `/ark-onboard repair` coexist independently — neither chains the other automatically. `/ark-update` refuses to run on malformed CLAUDE.md / `.mcp.json` / `.ark/migrations-applied.jsonl` and points back to `/ark-onboard repair`.

## References

- Spec: `.omc/specs/deep-interview-ark-update-framework.md`
- Plan: `.omc/plans/ralplan-ark-update.md`
- Stream B handoff: `.ark-workflow/handoffs/stream-b-ark-update-framework.md`
- Target ship: v1.14.0 (combined with Stream A — OMC detection in `/ark-onboard` + `/ark-health`)
