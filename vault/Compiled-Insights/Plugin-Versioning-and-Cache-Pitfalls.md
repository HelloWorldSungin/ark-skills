---
title: "Plugin Versioning & Cache Pitfalls"
type: compiled-insight
tags:
  - compiled-insight
  - plugin
  - infrastructure
summary: "Claude Code plugin versioning has 4 sources of truth (VERSION, plugin.json, marketplace.json, cache SHA) — any desync causes silent update failure."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Plugin Versioning & Cache Pitfalls

## Summary

The Claude Code plugin system has a fragile versioning model with 4 independent sources of truth. A multi-session debugging saga revealed that version desync causes `/plugin update` to silently report "already at latest" when it isn't. This page documents every pitfall encountered so they aren't repeated.

## Key Insights

### Four Sources of Truth That Must Stay in Sync

| Source | Location | Format | What Reads It |
|--------|----------|--------|---------------|
| `VERSION` | repo root | 4-segment (`1.0.2.0`) | Nothing in plugin system |
| `plugin.json` | `.claude-plugin/plugin.json` | 3-segment (`1.0.2`) | Plugin system (primary) |
| `marketplace.json` | repo root | 3-segment (`1.0.2`) | Marketplace registry |
| Cache SHA | `~/.claude/plugins/cache/{marketplace}/{plugin}/{version}/` | git commit SHA | Update checker |

Bumping only VERSION does nothing. Both `plugin.json` AND `marketplace.json` must be updated, and the cache must be refreshed.

### Cache Is Pinned to a Git Commit SHA

The plugin cache stores a `gitCommitSha`. If the cached SHA is old, the plugin system won't see newer versions on the remote — even if the remote has been pushed. After fixing version files, the cache still showed the old version because it was pinned at an old commit.

**Fix:** Manually `git pull` inside the cache directory to update to HEAD.

### Repository Field Must Match Actual GitHub Repo

The `repository` field in `plugin.json` originally pointed to `HelloWorldSungin/create-ark-skills` which didn't exist on GitHub (actual repo: `HelloWorldSungin/ark-skills`). The plugin update system couldn't find the remote, so it treated the cached version as latest.

### Marketplace Name Mismatch Requires Full Reinstall

When the marketplace name changed from `create-ark-skills` to `ark-skills`, a simple `/plugin update` wouldn't pick up the change. Required: uninstall plugin, remove old marketplace, add new marketplace with correct name, reinstall.

### `/reload-plugins` Does Not Update Cache

`/reload-plugins` only re-reads the already-cached files. It does not fetch from the remote. This is a common misconception — if your version files are wrong in the cache, reloading just re-reads the wrong files.

### Plugin Cache Path Structure

Plugins are cached at: `~/.claude/plugins/cache/{marketplace-name}/{plugin-name}/{version}/`

For ark-skills: `~/.claude/plugins/cache/create-ark-skills/ark-skills/1.0.0/skills/`

### Installation Flow

Three separate steps required:
1. `marketplace add HelloWorldSungin/ark-skills`
2. `plugin install ark-skills@ark-skills`
3. `/reload-plugins`

## Evidence

- Conversation `f7f9e4ce`: multi-step debugging of v1.0.2 update failure
- Conversation `a5ed3c76`: plugin installation discovery
- Commit `5866590`: "fix: correct plugin version and repository URL"

## Implications

- **Version bump checklist:** Always update `plugin.json`, `marketplace.json`, AND `VERSION` together. Consider a bump script.
- **After pushing a version bump:** Verify by checking the cache directory or running `/plugin update` from a clean state.
- **If `/plugin update` reports "already at latest" incorrectly:** Check all 4 sources of truth, verify the `repository` field, and consider manual cache refresh.
- **Markdown-only repos** (like ark-skills) skip test/coverage/adversarial steps in the /ship workflow since there's no runtime.
