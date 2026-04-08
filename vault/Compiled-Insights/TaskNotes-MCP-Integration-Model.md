---
title: "TaskNotes MCP Integration — Architecture & Limitations"
type: compiled-insight
tags:
  - compiled-insight
  - plugin
  - infrastructure
summary: "TaskNotes MCP is an HTTP endpoint inside Obsidian (not standalone), with limited schema — custom frontmatter requires post-edit or direct markdown write."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# TaskNotes MCP Integration — Architecture & Limitations

## Summary

The tasknotes MCP integration is an HTTP endpoint (`POST /mcp`) inside the Obsidian plugin itself, NOT a standalone Node server. This means Obsidian must be running for MCP to work. The MCP `create_task` tool uses a simplified schema that doesn't support Ark-specific frontmatter fields (task-id, task-type, component), requiring workaround strategies.

## Key Insights

### Architecture: Embedded in Obsidian, Not Standalone

```
Claude Code agent → ark-tasknotes skill → MCP HTTP POST /mcp
    → Obsidian plugin (tasknotes) creates .md files
    → linear-updater polls vault repo (5-min interval)
    → Syncs to Linear
```

Each MCP request is stateless — a new `McpServer` instance is created per request via `StreamableHTTPServerTransport`. Obsidian must be running with `enableAPI: true` and `enableMCP: true`.

**This was a critical correction during spec review.** The initial design assumed a standalone MCP server. The /codex review caught that the tasknotes MCP is an embedded endpoint, which changes deployment assumptions entirely.

### Custom Frontmatter Limitation

`tasknotes_create_task` accepts: title (required), status, priority, due, scheduled, tags, contexts, projects, recurrence, timeEstimate, details.

It does **NOT** accept: `task-id`, `task-type`, `work-type`, `component`, `urgency`, `severity`. Neither does `tasknotes_update_task`.

**Two workaround strategies:**
1. Create via MCP, then edit the markdown file to add custom frontmatter
2. Write the markdown file directly with full frontmatter, using MCP only for queries and status updates

### Error Handling Patterns

- **Obsidian not running**: `tasknotes_health_check` fails → fall back to direct markdown write with correct frontmatter
- **Counter races**: Two agents incrementing `TaskNotes/meta/{Prefix}-counter` simultaneously → accept occasional ID gaps (IDs need not be strictly sequential)
- **Wrong vault targeted**: Verify vault identity by checking counter file exists before creating tasks

### Per-Project Routing

Each project's `.claude/settings.json` registers an MCP endpoint. Since each vault may run in its own Obsidian instance (potentially on different ports), the port in the URL differentiates which vault is targeted.

## Evidence

- Design spec §3: `docs/superpowers/specs/2026-04-07-ark-skills-plugin-design.md`
- MCP tool definitions: `tasknotes/src/services/MCPService.ts`
- Memory: `project_ark_skills_plugin.md` — documents the correction from /codex review

## Implications

- The ark-tasknotes skill must implement the fallback pattern (MCP → direct write) to be reliable.
- Task ID management is the skill's responsibility, not MCP's — read counter, increment, write to frontmatter.
- When adding custom frontmatter fields to the Ark ecosystem, they will always require post-creation markdown editing since MCP schema is fixed.
- linear-updater integration works regardless of creation method since it reads vault files, not MCP state.
