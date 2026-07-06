---
title: "Gstack Per-Host Install & the Runtime Root"
type: compiled-insight
tags:
  - gstack
  - install
  - plugin-management
  - runtime-root
  - guardrail
description: "gstack installs per-host via `setup --host <name>` into per-host skill dirs. `~/.claude/skills/gstack` is the shared runtime root (50+ skills reference it), NOT a deletable duplicate — deleting it breaks the Claude install. Auto-upgrade only re-syncs claude, so codex drifts."
source-sessions: ["[[S017-Gstack-Install-Scoping-Onboard-Health]]"]
source-tasks: []
created: 2026-06-15
last-updated: 2026-06-15
timestamp: 2026-06-15T00:00:00Z
---

# Gstack Per-Host Install & the Runtime Root

## The model
gstack installs **per-host**, one host per skill directory, selected by `~/.gstack/repos/gstack/setup --host <name>`:

| Host | Skill dir | Notes |
|------|-----------|-------|
| claude | `~/.claude/skills/gstack` (symlink to repo) + per-skill dirs | the primary host |
| codex | `~/.codex/skills/gstack-*` (prefixed) + `~/.codex/skills/gstack` runtime root | trimmed name+description frontmatter, `openai.yaml` metadata |
| cursor | `~/.cursor/skills/gstack` | excluded by policy |
| gemini | `~/.gemini/skills/gstack` | excluded by policy |

`setup --host auto` only auto-detects claude/codex/kiro/droid/opencode — it never targets cursor or gemini. Default `--host` is `claude`.

## The runtime root (the load-bearing gotcha)
`~/.claude/skills/gstack` is gstack's shared **runtime root**: it holds `bin/` (the `gstack-*` helper scripts), `browse/dist` (the browser binary), `gstack-upgrade`, `ETHOS.md`, and `review/` files. **52 of the gstack skills reference `~/.claude/skills/gstack/bin/*` at runtime.** It looks like a duplicate-platform copy but is not — deleting it breaks every gstack skill that shells out to that path. Repair is canonical and idempotent: `cd ~/.gstack/repos/gstack && ./setup --host claude`.

## Auto-upgrade drift
`auto_upgrade: true` in `~/.gstack/config.yaml` runs a bare `./setup` on upgrade, which defaults to `--host claude` only — there is no persisted host list. So **Codex is not re-synced on upgrade** and drifts; after each gstack upgrade, manually re-run `./setup --host codex`.

## Detection vs. integrity (orthogonal signals)
Plugin *presence* is detected via the session skill-list (see [Compiled-Insights/Session-Capability-Plugin-Detection-Pattern](Session-Capability-Plugin-Detection-Pattern.md)) — a session-capability probe, not filesystem inspection. Install *integrity* is the complement: it IS filesystem-based (does the runtime root resolve? are extra hosts installed?). `/ark-health` Check 2a covers integrity; Check 2 covers presence. A skill can be "present in session" while the runtime root is broken, so both signals are needed.

## Why claude+codex only
Installing gstack for gemini/cursor floods that agent's context window (~48% on a fresh session) with duplicate per-platform skill copies. The policy is encoded in `/ark-onboard` (active install) and `/ark-health` Check 2a (over-broad detection). Verification beats review here: live-running the detection bash in the actual shell (zsh) caught a `find -type d` symlink miss and a zsh word-split bug that a tri-model `/ccg` design review did not. See [Ecosystem-Architecture-Map](Ecosystem-Architecture-Map.md).
