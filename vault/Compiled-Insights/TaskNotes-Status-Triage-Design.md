---
title: "TaskNotes Status & Triage — Design Decisions"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - plugin
summary: "ark-tasknotes status uses MCP-first data gathering with LLM triage — no algorithmic scoring. Six-section report with opinionated work plan recommendations."
source-sessions: []
source-tasks: []
created: 2026-04-09
last-updated: 2026-04-09
---

# TaskNotes Status & Triage — Design Decisions

## Problem

Obsidian Bases views provide task dashboards inside Obsidian, but nothing exists for the CLI workflow. Users starting a session or deciding what to work on next had no quick way to get a task overview and recommendation.

## Key Design Decisions

### MCP-First with LLM Triage (No Algorithmic Scoring)

Three approaches were considered:
1. **MCP + LLM triage** — pull structured data, let the LLM reason about priorities
2. **Algorithmic scoring** — deterministic formula (priority x urgency x staleness)
3. **Hybrid** — algorithmic pre-sort, LLM commentary

Chose option 1. Rationale: LLMs handle qualitative signals (task descriptions, dependency context, "quick win" judgment) that rigid formulas cannot. Consistency matters less than nuance for standup-style recommendations. Also cheaper to maintain — no scoring formula to tune.

### Subcommand Pattern (Modes)

Rather than creating a separate skill, status was added as a mode of the existing `/ark-tasknotes` skill. The skill now has a Modes table at the top routing to Create (default) or Status based on the invocation argument. This keeps all task operations in one place and shares the [[Compiled-Insights/Plugin-Architecture-and-Context-Discovery|context-discovery]] pattern and [[Compiled-Insights/TaskNotes-MCP-Integration-Model|MCP tool reference]].

### Report Structure

Six sections, each conditionally shown:

| Section | Purpose | Omit when |
|---------|---------|-----------|
| Overview | Counts by status + velocity pulse | Never |
| Active Work | In-progress tasks with age | No in-progress tasks |
| Needs Attention | Stale (>3d) or blocked tasks | Nothing stale or blocked |
| Up Next | Todo tasks sorted by priority | No todo tasks |
| Recently Completed | Done in last 7 days | None completed recently |
| Recommendation | Opinionated 2-3 item work plan | Never |

### Triage Heuristic Ordering

The LLM generates recommendations using these priorities in order:
1. **Unblock first** — finish items that block other tasks
2. **Priority x urgency** — critical/blocking before medium/normal
3. **Batch related work** — group by component when priorities are close
4. **Quick wins** — small tasks between heavy items for momentum

### Derived Signals

Computed from raw task data, not stored:
- **Staleness**: days since `last-updated` for in-progress tasks
- **Blocked chains**: tasks whose `blockedBy` references another open task
- **Velocity**: completed vs created in last 7 days
- **Quick wins**: task/bug types with medium or lower priority

## Guardrails

- **Read-only** — status mode never modifies task files, counter, or vault state
- **Graceful degradation** — MCP failure falls back to direct markdown reads; total failure shows fix instructions

## Evidence

- Design spec: `docs/superpowers/specs/2026-04-09-ark-tasknotes-status-design.md`
- Implementation: `skills/ark-tasknotes/SKILL.md` (Status Mode section)
