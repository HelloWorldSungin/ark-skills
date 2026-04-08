---
name: ark-tasknotes
description: Agent-driven task creation and management via tasknotes MCP or direct markdown write
---

# Ark TaskNotes

Create and manage TaskNote tickets automatically during development workflows. Tasks sync to Linear via linear-updater.

## Project Discovery

1. Read the project's CLAUDE.md to find: task prefix, vault path, TaskNotes path
2. Verify MCP is available: call `tasknotes_health_check`
3. If MCP unavailable (Obsidian not running), fall back to direct markdown write
4. Read `{vault_path}/TaskNotes/meta/{task_prefix}counter` for next available ID

## When to Create Tasks

| Trigger | Task Type | Priority |
|---------|-----------|----------|
| Bug discovered during code review | Bug | Based on severity |
| Feature completed, needs verification | Story | medium |
| Tech debt identified during maintenance | Task | low-medium |
| Incident debugged, root cause found | Bug | Based on impact |
| Research finding needs follow-up | Story | medium |

## Workflow

### Step 1: Check for Duplicates

Before creating, search for existing tasks on the same topic:

**If MCP available:**
```
tasknotes_query_tasks({
  conjunction: "and",
  children: [{
    type: "condition",
    id: "1",
    property: "status",
    operator: "is_not",
    value: "done"
  }],
  sortKey: "due",
  sortDirection: "asc"
})
```

Review results. If a matching task exists, update it instead of creating a duplicate.

**If MCP unavailable:**
```bash
grep -rl "{keyword}" {vault_path}/TaskNotes/Tasks/ --include="*.md" | head -5
```

### Step 2: Get Next Task ID

```bash
COUNTER=$(cat {vault_path}/TaskNotes/meta/{task_prefix}counter)
TASK_ID="{task_prefix}$(printf '%03d' $COUNTER)"
echo "Next task ID: $TASK_ID"
```

### Step 3: Create the Task

**Option A: MCP + post-edit (preferred when Obsidian is running)**

1. Create via MCP:
```
tasknotes_create_task({
  title: "{task title}",
  status: "backlog",
  priority: "{low|medium|high|urgent}",
  tags: ["{task_type}"],
  projects: ["{project_name}"],
  details: "{description with context}"
})
```

2. The MCP returns the file path. Edit the created file to add Ark-specific frontmatter:
```yaml
task-id: "{TASK_ID}"
task-type: "{epic|story|bug|task}"
work-type: "{development|research|deployment|docs|infrastructure}"
component: "{module_name}"
urgency: "{blocking|high|normal|low}"
summary: "<=200 char description"
```

**Option B: Direct markdown write (fallback when Obsidian is not running)**

Determine the subdirectory from task type:
- epic -> `TaskNotes/Tasks/Epic/`
- story -> `TaskNotes/Tasks/Story/`
- bug -> `TaskNotes/Tasks/Bug/`
- task -> `TaskNotes/Tasks/Task/`

Write the file `{TASK_ID}-{slug}.md`:
```yaml
---
title: "{task title}"
tags:
  - task
  - {task_type}
task-id: "{TASK_ID}"
task-type: "{epic|story|bug|task}"
status: backlog
priority: "{low|medium|high|critical}"
project: "{project_name}"
work-type: "{development|research|deployment|docs}"
component: "{module_name}"
urgency: "{blocking|high|normal|low}"
created: "{today}"
summary: "<=200 char description"
---

# {task title}

## Description

{detailed description}

## Related

- [[related-task-or-page]]
```

### Step 4: Increment Counter

```bash
echo $((COUNTER + 1)) > {vault_path}/TaskNotes/meta/{task_prefix}counter
```

### Step 5: Announce and Commit

Tell the user: "Created {task_type} {TASK_ID}: {title}"

```bash
cd {vault_path}
git add TaskNotes/
git commit -m "task: create {TASK_ID} — {title}"
git push
```

## Guardrails

- **Never auto-close tasks** — only create and update to in-progress
- **Critical/blocking tasks:** Ask user for confirmation before creating
- **Announce creation:** Always tell the user what was created (no silent side-effects)
- **Verify vault identity:** Before creating, check that `TaskNotes/meta/{task_prefix}counter` exists. If missing, alert user that the vault may be misconfigured.

## MCP Tool Reference

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `tasknotes_health_check` | Verify MCP is running | none |
| `tasknotes_create_task` | Create task | `title` (req), `status`, `priority`, `tags`, `projects`, `details` |
| `tasknotes_update_task` | Update task | task file path, properties to update |
| `tasknotes_query_tasks` | Search tasks | `conjunction`, `children` (filter conditions), `sortKey` |
| `tasknotes_get_task` | Get by file path | file path (NOT task-id) |
| `tasknotes_list_tasks` | List with pagination | page, limit |
| `tasknotes_toggle_status` | Cycle status | task file path |
| `tasknotes_get_stats` | Task statistics | none |
