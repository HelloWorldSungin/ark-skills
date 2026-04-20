---
title: "Session-Capability Plugin Detection Pattern"
type: compiled-insight
tags:
  - plugin-detection
  - session-capability
  - claude-code
  - ark-workflow
  - ark-health
  - has-probe
  - degradation
summary: "For Claude Code plugin availability detection, the canonical signal is the session skill-list (semantic probe by the agent), not filesystem inspection. Filesystem/CLI probes are advisory only — they distinguish 'absent' from 'broken-install' but don't prove the plugin is loadable in the current session. Extracted from v1.18.0 gstack integration; matches pattern already proven in /ark-health and /ark-onboard."
source-sessions:
  - "[[S012-Ark-Workflow-Gstack-Planning]]"
source-tasks:
  - "[[Arkskill-008-gstack-planning-brainstorm]]"
created: 2026-04-18
last-updated: 2026-04-20
---

# Session-Capability Plugin Detection Pattern

## The problem

Claude Code plugins expose skills via the session's `system-reminder` skill-list. When a skill needs to conditionally route based on "is plugin X installed," there are two candidate signals:

1. **Filesystem / CLI** — check for a binary on `$PATH`, a config directory under `$HOME`, or an installed cache under `~/.claude/plugins/cache/`.
2. **Session skill-list** — read the `system-reminder` entries the agent already has in context and search for skill names registered by the plugin.

These are not equivalent. Using the wrong one produces both **false positives** and **false negatives**.

## Failure modes of filesystem-only detection

- **False positive: stale install residue.** `$HOME/.gstack/config.yaml` can survive plugin uninstallation, machine migration, or a partial install. The filesystem says "installed" but the plugin is not loadable.
- **False positive: wrong version.** Filesystem check says "present" but the installed version is older than the routing logic expects.
- **False negative: plugin routing without local state.** A plugin can be registered via Claude Code's plugin system without installing a home-dir state directory. The filesystem says "absent" but the skills are fully loadable.
- **False negative: CLI-missing-but-skills-present.** The plugin provides slash-skills but no PATH binary. `command -v` fails; skills work.

The net worst case: the routing skill promises a step that fails at execution time. For a workflow orchestrator, this is the most damaging failure mode — the user sees the chain, tries to run the step, and hits a "skill not found" error.

## The pattern

Primary detection is **semantic**, executed by the agent reading its own session context:

> *Read the skill list in your current `system-reminder` context. Search for any of these skills by name: [list]. If at least one is present, set `HAS_X=true`.*

This is prose in the skill's SKILL.md, not a bash probe. It's executed by the LLM as part of skill resolution.

Filesystem check is **advisory** — used only to distinguish two failure modes, not as the primary routing signal:

```bash
X_STATE_PRESENT=false
[ -d "$HOME/.x" ] && [ -f "$HOME/.x/config.yaml" ] && X_STATE_PRESENT=true
[ "$ARK_SKIP_X" = "true" ] && X_STATE_PRESENT=false
```

Then the combination gives three operator states:

| `HAS_X` | `X_STATE_PRESENT` | State | UX |
|---------|-------------------|-------|-----|
| true | any | healthy | include the step |
| false | false | absent | silent skip (no notice) |
| false | true | broken-install | emit one notice per chain ("install detected but skills not loadable — run `/ark-health`") |

Silent-by-default prevents clippy noise for users who don't have the plugin. Explicit only when the filesystem signal and session signal disagree — that's a real operator problem that warrants telling the user.

## Where this pattern already exists in Ark

- `/ark-health` Check 2 (gstack plugin): "check if gstack skills are loadable in the current session. Look for: `browse`, `qa`, `ship`, `review`, `design-review`."
- `/ark-onboard` plugin check uses the same skill-list lookup.
- `/ark-workflow` v1.18.0 extends the pattern from **diagnostic use** (ark-health) to **routing use** (ark-workflow's condition resolver gates chain steps on `HAS_GSTACK_PLANNING`).

## When to use

When the decision is **"should I route through a skill provided by a specific plugin,"** use the session-capability probe. When the decision is **"is this user's machine configured to support this feature,"** filesystem/CLI can still be the right answer — but those are rare in the Ark context because Ark is slash-skill-oriented, not CLI-oriented.

## Known weakness

The semantic probe is prose-only and relies on the agent correctly counting skill-list entries by bare name. If the agent miscounts (e.g., misses a namespaced `gstack:office-hours` entry while looking for bare `office-hours`), the operator state is silently wrong.

Mitigation directions (all deferred):
- Prefix-anchored detection (`superpowers:*`-style enumerated list) instead of bare-name matching.
- Structural probe parity ([[Structural-Probe-Parity-Pattern]]) — byte-level equivalence between skills' detection blocks so `/ark-health` and `/ark-workflow` cannot drift apart.
- Agent-side verification step — after semantic probe, attempt to dry-run one of the target skills and confirm it's invokable. Heavier but more reliable.

## Related

- [[Structural-Probe-Parity-Pattern]] — byte-level parity for duplicated detection bash probes across sibling skills.
- [[Plugin-Architecture-and-Context-Discovery]] — how Claude Code plugins expose their skills to sessions.
- [[Plugin-Versioning-and-Cache-Pitfalls]] — the four sources of truth for a plugin version.
- Source: [[S012-Ark-Workflow-Gstack-Planning]] — v1.18.0 gstack integration.
