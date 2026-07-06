---
title: "Session 17: gstack install scoping (claude+codex) in /ark-onboard + /ark-health"
type: session-log
tags:
  - session-log
  - "S017"
  - gstack
  - ark-onboard
  - ark-health
  - ccg-review
description: "Repaired a broken Claude gstack install (deleted runtime root), then taught /ark-onboard to actively install gstack scoped to claude+codex and /ark-health to detect the failure class (Check 2a). /ccg review + live bash verification caught a find -type d symlink miss and a zsh word-split bug. Shipped v1.28.0, PR #29."
session: "S017"
status: complete
date: 2026-06-15
prev: "[[S016-Ark-Skill-Healer-Tracked-Rebuild]]"
epic: ""
source-tasks: []
created: 2026-06-15
last-updated: 2026-06-15
timestamp: 2026-06-15T00:00:00Z
---

# Session 17: gstack install scoping (claude+codex) in /ark-onboard + /ark-health

## Objective
Stop gstack from flooding non-target agents' context windows, and make future setup install gstack for only Claude Code + Codex. Started as a live repair of a broken Claude gstack install, then hardened the ark-skills onboarding/diagnostic skills so it can't recur.

## Context
gstack installs **per-host** via `setup --host <name>`, one host per skill dir (`~/.claude/skills/gstack`, `~/.codex/skills/gstack-*`, `~/.cursor/skills/gstack`, `~/.gemini/skills/gstack`). The user had deleted what looked like duplicate per-platform copies to declutter cursor-agent's context. That cleanup removed `~/.claude/skills/gstack` — which is not a duplicate but Claude's shared **runtime root** (`bin/`, `browse/dist`, `gstack-upgrade`, `ETHOS.md`, `review/`), referenced by 50+ skills. Result: every gstack skill that shells out to `~/.claude/skills/gstack/bin/*` broke.

## Work Done

### Live repair (Approach A)
- Diagnosed the missing runtime root: 52 gstack SKILL.md files reference `~/.claude/skills/gstack/...`; the dir was gone while the source repo at `~/.gstack/repos/gstack` was intact.
- Re-ran `cd ~/.gstack/repos/gstack && ./setup --host claude` (rebuilt runtime root + relinked 54 skills) and `./setup --host codex` (installed 52 `gstack-*` skills into `~/.codex/skills`).
- Verified: gemini/cursor untouched; `bin/gstack-config` executes; browse binary resolves. 3 leftover dangling links (`just`, `claude-bowser`, `playwright-bowser`) are unrelated bowser project skills, left alone.
- Found auto-upgrade drift: `auto_upgrade: true` in `~/.gstack/config.yaml`, but auto-upgrade runs a bare `./setup` defaulting to `--host claude` only — Codex is NOT re-synced on upgrade, so it needs a manual `./setup --host codex` after each gstack upgrade.

### Skill changes (v1.28.0)
- **`skills/ark-onboard/SKILL.md`**: new "gstack Setup (claude + codex only)" subsection wired into Entry-Flow Step 2. Confirm-then-run, idempotent, self-repairing (only runs `setup` for a host whose install is missing/partial, so it doubles as the runtime-root repair). Guardrail documenting the runtime root is not a deletable duplicate. Added a `2a` row to the Shared Diagnostic Checklist summary.
- **`skills/ark-health/SKILL.md`**: new **Check 2a — gstack install integrity** (warn-only sub-check; headline "23 checks" unchanged). Detects (1) missing/partial Claude runtime root, (2) over-broad install under `~/.cursor`/`~/.gemini`. Check 2 fail-action now points at `/ark-onboard`. Added 2a to scorecard, classification warn-list, advisory list.
- **`/ark-update` left untouched** — gstack install is user-machine state, not project convention (respects the established scope boundary).

### Review + verification
- `/ccg` (Codex + Gemini). Codex read the real `setup` source and hardened: locator `cd && pwd -P` instead of `readlink` (robust to relative/non-symlink/stale symlinks); stronger Claude sentinel (also checks `_gstack-command/SKILL.md`); Codex presence gate `command -v codex || [ -d ~/.codex ]`. Gemini: confirm-then-run prompt; visceral over-broad warning. Rejected Gemini's "modify the gstack repo / rename root" (we don't own gstack) and unverified `gstack teardown` command.
- Live verification caught two more bugs beyond CCG: `find -type d` matched zero Codex skill dirs because they are **symlinks** (type `l`) → fixed with `find -L`, preventing a redundant codex reinstall on every onboard; and a **zsh word-splitting** bug in the over-broad `rm` list (inline `$(…)` loop produced `rm -rf ~/. cursor gemini/skills/gstack`) → rebuilt the list in the literal-list loop. Both blocks verified in bash AND zsh: PASS / idempotent-skip on healthy state, correct WARN with well-formed remediation on broken/over-broad state.
- Shipped v1.28.0 via `/ship`: merged master, version state `ALREADY_BUMPED`, pre-landing review clear, pushed, PR #29 (https://github.com/HelloWorldSungin/ark-skills/pull/29).

## Decisions Made
- **claude + codex is deliberate policy**, not a default to "improve" toward `--host auto` (which would also target kiro/droid/opencode). ark-skills' downstream consumers are all the user's own projects, so encoding the host policy in shared onboarding is appropriate.
- **Active install over guidance**: ark-onboard runs `setup` itself (confirm-then-run), per user choice, refined by Gemini's "don't silently auto-run."
- **Placement**: user-machine concern → `/ark-onboard` + `/ark-health`, never `/ark-update`. Confirmed by both advisors.
- **Verification beats review**: live-running the bash in the actual shell (zsh) caught two bugs that a tri-model design review missed (one was in Codex's own recommended snippet).

## Open Questions
- Should the pre-existing "22 checks" (ark-onboard summary intro) vs "23 checks" (ark-health) drift be reconciled, and the missing Check 23 summary row backfilled? Flagged but deferred this session.
- Should ark-skills track the gstack auto-upgrade codex-drift more actively (e.g., an ark-health check that warns when Codex gstack skills are stale relative to the repo VERSION)?

## Next Steps
- Land PR #29 (`/land-and-deploy`).
- gstack toolkit upgrade 1.56.0.0 → 1.58.1.0 is available; run `/gstack-upgrade` separately (and re-run `./setup --host codex` afterward to avoid codex drift).
