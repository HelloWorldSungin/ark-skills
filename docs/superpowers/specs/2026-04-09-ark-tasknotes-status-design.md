# Design: `/ark-tasknotes status` Subcommand

**Date:** 2026-04-09
**Status:** Draft

## Problem

When starting a session or mid-work, there's no quick way to see the state of TaskNotes tickets and get a recommendation on what to work on next. The Obsidian Bases views provide dashboards inside Obsidian, but nothing exists for the CLI workflow.

## Solution

Add a `status` mode to the existing `/ark-tasknotes` skill that produces an opinionated standup-style report with task overview and triage recommendations.

## Approach

**MCP-first with LLM triage.** Pull structured data via MCP tools (`get_stats` + `query_tasks`), fall back to direct markdown reads when Obsidian is offline. The LLM synthesizes an opinionated work plan from the raw data — no algorithmic scoring to maintain.

## Skill Modes

The skill gets a top-level "Modes" section:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Create** (existing) | `/ark-tasknotes` or `/ark-tasknotes create` | Current task creation workflow, unchanged |
| **Status** (new) | `/ark-tasknotes status` | Gather data, produce report, recommend next work |

## Data Gathering

### Step 1: Project Discovery

Standard context-discovery — read CLAUDE.md for vault path, TaskNotes path, task prefix.

### Step 2: Collect Data

| Step | MCP Tool | Fallback (Obsidian offline) |
|------|----------|---------------------------|
| Health check | `tasknotes_health_check` | If fails, switch to fallback path |
| Aggregate stats | `tasknotes_get_stats` | Count `.md` files in `Tasks/` subdirectories |
| Open tasks (status != done) | `tasknotes_query_tasks` with status filter | Read frontmatter from all `Tasks/**/*.md` |
| Recently completed | `tasknotes_query_tasks` (status=done, sort by updated desc, limit 5) | Read files in `Archive/` sorted by mtime |

### Step 3: Enrich

For each open task, extract: `task-id`, `title`, `status`, `priority`, `urgency`, `created`, `last-updated`, `blockedBy`, `depends-on`, `component`, `work-type`, `session`.

### Step 4: Compute Derived Signals

The LLM computes from raw data:

- **Staleness**: days since `last-updated` for in-progress tasks (flag if > 3 days)
- **Blocked chain**: tasks whose `blockedBy` points to an open task
- **Velocity**: tasks completed in last 7 days vs created in last 7 days
- **Quick wins**: task/bug types with medium or lower priority

## Report Format

```
TaskNotes Status: {project_name} ({task_prefix})
═══════════════════════════════════════════════════

Overview
  backlog: N  |  todo: N  |  in-progress: N  |  done: N
  Total open: N  |  Completed this week: N  |  Created this week: N

Active Work (in-progress)
  {task-id}  {title}  [{priority}] {N}d active
  ...

Needs Attention
  {task-id}  Stale {N}d -- no update since {date}     [{priority}]
  {task-id}  Blocked by {blocker-id}                    [{priority}]
  ...
  (omit section if nothing needs attention)

Up Next (todo, by priority)
  {task-id}  {title}  [{priority}, {urgency}]
  ...

Recently Completed (last 7d)
  {task-id}  {title}  -- done {date}
  ...
  (omit section if none completed recently)

Recommendation
  1. {action} {task-id} ({reasoning})
  2. {action} {task-id} ({reasoning})
  3. Defer {task-id} ({reasoning})
```

## Triage Heuristics

The LLM generates recommendations using these ordered priorities:

1. **Unblock first** — finish in-progress items that block other tasks
2. **Highest priority x urgency** — critical/blocking items before medium/normal
3. **Batch related work** — group tasks by component or work-type
4. **Quick wins between heavy items** — maintain momentum with small tasks

## Guardrails

- **Read-only** — status mode never creates, updates, or closes tasks
- **Graceful degradation** — if MCP and fallback both fail (no vault), report "No TaskNotes found" with fix instructions
- **No emoji in output** — plain text formatting only (user preference)

## Files to Modify

1. `skills/ark-tasknotes/SKILL.md` — add Modes section and Status mode instructions
2. `CLAUDE.md` — update skill description to mention status subcommand

## Verification

1. Run `/ark-tasknotes status` with Obsidian running (MCP path)
2. Run `/ark-tasknotes status` with Obsidian closed (fallback path)
3. Verify `/ark-tasknotes` (no args) still triggers create mode
4. Check that the report renders correctly with the current vault data
