---
title: "Project Management Guide"
type: moc
tags:
  - moc
  - task
summary: "How task IDs, statuses, and task notes work in the ark-skills project."
created: 2026-04-08
last-updated: 2026-04-08
---

# Project Management Guide

## Task ID Format

All tasks use the prefix **`Arkskill-`** followed by a zero-padded 3-digit number.

- Examples: `Arkskill-001`, `Arkskill-042`, `Arkskill-100`
- Counter file: `TaskNotes/meta/Arkskill-counter`

## Creating a Task

1. Read the current counter value from `TaskNotes/meta/Arkskill-counter`
2. Create a new task file in the appropriate `TaskNotes/Tasks/{Type}/` directory
3. Use the corresponding template from `vault/_Templates/`
4. Set the `task-id` field to `Arkskill-{counter}` (zero-padded to 3 digits)
5. Increment the counter file

## Task Types

| Type | Directory | When to Use |
|------|-----------|-------------|
| Epic | `Tasks/Epic/` | Large multi-session initiatives |
| Story | `Tasks/Story/` | User-facing feature work |
| Bug | `Tasks/Bug/` | Defects and regressions |
| Task | `Tasks/Task/` | Generic work items |

## Status Values

| Status | Meaning |
|--------|---------|
| `backlog` | Identified but not started |
| `todo` | Planned for near-term work |
| `in-progress` | Actively being worked on |
| `done` | Completed |

## Archiving

When a task reaches `done` status, move it from `Tasks/{Type}/` to `Archive/{Type}/`.

## Priority Values

| Priority | Meaning |
|----------|---------|
| `critical` | Blocking other work |
| `high` | Important, do soon |
| `medium` | Normal priority |
| `low` | Nice to have |
