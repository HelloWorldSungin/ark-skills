---
title: "Hook Drift Detection Pattern"
type: compiled-insight
tags:
  - compiled-insight
  - infrastructure
  - plugin
summary: "Plugin updates don't overwrite files installed outside the plugin tree (~/.claude/hooks/, ~/.local/bin/). Drift detection requires byte-compare against a version-aware canonical path — naive globs sort alphabetically and silently pick the oldest cached version."
source-sessions: []
source-tasks:
  - "[[Arkskill-011]]"
created: 2026-04-24
last-updated: 2026-04-24
---

# Hook Drift Detection Pattern

## Summary

A Claude Code plugin can install files **outside** its own tree — under `~/.claude/hooks/`, `~/.local/bin/`, pipx venvs, or other user-machine state. Plugin upgrades through `/plugin update` do not touch those locations. A user who installs a hook at v1.20.x and upgrades to v1.21.x ends up running the old hook script while the rest of the plugin is current. The race the new hook closes is silently still open.

Three independent v1.21.x patches converged on the pattern:

1. **`/ark-health` Check 16b** (v1.21.2) added byte-compare drift detection.
2. **v1.21.3** fixed a path-resolver bug where the check picked the *oldest* cached plugin version instead of the newest.
3. **The scope rule** (already in [[Plugin-Architecture-and-Context-Discovery]] but worth pinning): `/ark-update` converges project repo state only; `~/.claude/**` drift is `/ark-health` + `/ark-onboard repair` territory.

Together they define a generalizable shape for any "managed-but-installable" file the plugin owns logically but doesn't physically host.

## The pattern, in three layers

### Layer 1 — architectural scope rule

| Scope | Where it lives | Detected by | Fixed by |
|------|----------------|-------------|----------|
| Plugin repo | `skills/`, `references/`, etc. | Plugin update mechanism | `/plugin update` |
| Downstream project repo | `CLAUDE.md` managed regions, `.gitignore`, project scripts | `/ark-update` plan phase | `/ark-update` |
| User-machine state | `~/.claude/hooks/*.sh`, `~/.local/bin/*-mcp` shims, pipx venvs | `/ark-health` checks | `/ark-onboard repair` or skill-specific install script |

Mixing the boundaries — adding a Phase 1 destructive migration in `/ark-update` to overwrite `~/.claude/hooks/` — would set a precedent that bleeds into overwriting `~/.claude/settings.json` and pipx venvs without consent. The split keeps the consent loop explicit (detect → prompt → fix).

### Layer 2 — drift detection check shape

```bash
# Resolve canonical from plugin cache
CANONICAL=$(ls -d ~/.claude/plugins/cache/ark-skills/ark-skills/*/skills/claude-history-ingest/hooks/ark-history-hook.sh 2>/dev/null \
  | sort -V | tail -1)
INSTALLED=~/.claude/hooks/ark-history-hook.sh

if [ -z "$CANONICAL" ] || [ ! -f "$INSTALLED" ]; then
  echo "skip — Check 16 already covers presence"
elif cmp -s "$CANONICAL" "$INSTALLED"; then
  echo "PASS — content matches"
else
  echo "WARN — drift; re-run install-hook.sh"
fi
```

Three properties matter:

- **Skip on missing prerequisite.** If the file isn't installed at all, an earlier check (16) already failed — don't double-report.
- **`cmp -s` over hash compare.** No external tool dependency, exit code drives the branch directly, no hash literal to keep current.
- **Warn, not fail.** Drift is a "you should re-run install-hook.sh" prompt, not a hard error. The user might be running an intentionally older hook.

### Layer 3 — version-aware path resolution

The bug v1.21.3 fixed: the original Check 16b looped over

```bash
for candidate in ~/.claude/plugins/cache/ark-skills/ark-skills/*/skills/.../hook.sh; do
  CANONICAL="$candidate"
  break
done
```

Shell glob expansion sorts **alphabetically**, not by semver. `1.16.0` sorts before `1.20.0` and before `1.21.0`. On any system that's accumulated multiple cached versions, the first match is the oldest — exactly the wrong canonical. The check could happily PASS while comparing against a stale-but-byte-identical-to-the-installed-copy.

**Fix:** `sort -V | tail -1` to pick the highest version. Six versions were cached (`1.16.0` through `1.21.0`) on the live system that surfaced the bug.

This generalizes: **anywhere a plugin reaches into its own cache to find "current" resources, prefer `sort -V | tail -1` over relying on glob order.** Glob-order is alphabetical even when the directory names look numeric.

## Why this isn't `/ark-update`'s job

The `target-profile.yaml` comment from v1.11 is the load-bearing rule: the post-checkout hook is **excluded** from `/ark-update` because re-applying it on every run risks overwriting user customization. `/ark-update` works on tracked, owned files. The hook script is owned-by-plugin-but-installed-outside-the-repo — different consent model. Touching `$HOME` from `/ark-update` is the slippery slope.

## Evidence

- `CHANGELOG.md` v1.21.2: "Plugin upgrades don't overwrite files under `~/.claude/hooks/`, so a user who installed the hook at v1.20.x and upgraded to v1.21.1 is missing the cross-wing mutex and still exposed to the HNSW write race."
- `CHANGELOG.md` v1.21.3: "the shell glob ... returns matches in **alphabetical** order, not version order — `1.16.0` sorts before `1.20.0` and `1.21.x`."
- Memory `feedback_ark_update_scope.md`: "Running `/ark-update` against `$HOME/.claude/hooks/` silently overwrites user edits without consent; the health+onboard split is consent-preserving (detect → prompt → fix). Decided 2026-04-23 while shipping v1.21.2 Check 16b."
- Commits `37d284c` (v1.21.2 introduce), `2c75f07` (v1.21.3 path-resolver fix).

## Implications

- **When a future plugin release changes a file installed under `~/.claude/**`:** add a `/ark-health` check that byte-compares against the version-sorted canonical, point users at the existing install/repair path, and note "re-run `install-X.sh` to pick up" in CHANGELOG. Do not add it to `/ark-update`.
- **Any plugin-cache glob you write should pipe through `sort -V | tail -1`** unless you explicitly want all versions. Especially if the resolver is read by checks that compare content.
- **Bash-style globs are a portability trap** — they look numeric, sort alphabetically. Make the version order explicit.
- **The "drift detected at v + 1, not at v"** pattern means each release that ships a hook change should pair the change with its own Check 16b-style detector. Otherwise the gap is silent.
