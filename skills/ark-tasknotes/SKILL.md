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

## Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| Create | `/ark-tasknotes` or `/ark-tasknotes create` | Create and manage tasks (default) |
| Status | `/ark-tasknotes status` | Task overview and triage recommendations |

---

## Create Mode

### When to Create Tasks

| Trigger | Task Type | Priority |
|---------|-----------|----------|
| Bug discovered during code review | Bug | Based on severity |
| Feature completed, needs verification | Story | medium |
| Tech debt identified during maintenance | Task | low-medium |
| Incident debugged, root cause found | Bug | Based on impact |
| Research finding needs follow-up | Story | medium |

### Workflow

#### Step 1: Check for Duplicates

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

#### Step 2: Get Next Task ID

```bash
COUNTER=$(cat {vault_path}/TaskNotes/meta/{task_prefix}counter)
TASK_ID="{task_prefix}$(printf '%03d' $COUNTER)"
echo "Next task ID: $TASK_ID"
```

#### Step 3: Create the Task

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

#### Step 4: Increment Counter

```bash
echo $((COUNTER + 1)) > {vault_path}/TaskNotes/meta/{task_prefix}counter
```

#### Step 5: Announce and Commit

Tell the user: "Created {task_type} {TASK_ID}: {title}"

```bash
cd {vault_path}
git add TaskNotes/
git commit -m "task: create {TASK_ID} — {title}"
git push
```

### Guardrails

- **Never auto-close tasks** — only create and update to in-progress
- **Critical/blocking tasks:** Ask user for confirmation before creating
- **Announce creation:** Always tell the user what was created (no silent side-effects)
- **Verify vault identity:** Before creating, check that `TaskNotes/meta/{task_prefix}counter` exists. If missing, alert user that the vault may be misconfigured.

---

## Status Mode

Display a task overview with opinionated triage recommendations. Read-only — never creates, updates, or closes tasks.

### Step 1: Project Discovery

Read the project's CLAUDE.md to find: task prefix, vault path, TaskNotes path (same as Create Mode).

### Step 2: Gather Data

**If MCP available** (preferred):

1. Call `tasknotes_health_check` to verify MCP is running
2. Call `tasknotes_get_stats` for aggregate counts by status and priority
3. Query open tasks:
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
  sortKey: "priority",
  sortDirection: "desc"
})
```
4. Query recently completed tasks:
```
tasknotes_query_tasks({
  conjunction: "and",
  children: [{
    type: "condition",
    id: "1",
    property: "status",
    operator: "is",
    value: "done"
  }],
  sortKey: "updated",
  sortDirection: "desc"
})
```
Take only the 5 most recent from the results.

**If MCP unavailable** (fallback):

1. Read frontmatter from all `{vault_path}/TaskNotes/Tasks/**/*.md` files
2. Read frontmatter from recent files in `{vault_path}/TaskNotes/Archive/**/*.md` (sort by mtime, limit 5)
3. Count files by status manually

### Step 3: Enrich

For each open task, extract these fields from frontmatter:
`task-id`, `title`, `status`, `priority`, `urgency`, `created`, `last-updated`, `blockedBy`, `depends-on`, `component`, `work-type`, `session`

### Step 4: Compute Derived Signals

From the raw data, compute:
- **Staleness**: days since `last-updated` (or `created` if never updated) for in-progress tasks. Flag if > 3 days.
- **Blocked chains**: tasks whose `blockedBy` references another open task
- **Velocity**: tasks completed in last 7 days vs tasks created in last 7 days
- **Quick wins**: tasks with type `task` or `bug` and priority `medium` or lower

### Step 5: Output Report

Print the report using this format:

```
TaskNotes Status: {project_name} ({task_prefix})

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

Up Next (todo, by priority)
  {task-id}  {title}  [{priority}, {urgency}]
  ...

Recently Completed (last 7d)
  {task-id}  {title}  -- done {date}
  ...

Recommendation
  1. {action} {task-id} ({reasoning})
  2. {action} {task-id} ({reasoning})
  3. Defer {task-id} ({reasoning})
```

**Section rules:**
- Omit "Needs Attention" if nothing is stale or blocked
- Omit "Recently Completed" if nothing was completed in the last 7 days
- "Recommendation" always appears with 2-3 items

### Triage Heuristics

Generate the Recommendation section using these priorities in order:

1. **Unblock first** — finish in-progress items that block other tasks
2. **Highest priority x urgency** — critical/blocking before medium/normal
3. **Batch related work** — group tasks by component or work-type when priorities are close
4. **Quick wins between heavy items** — suggest small tasks to maintain momentum

### Status Mode Guardrails

- **Read-only** — never modify task files, counter, or vault state
- **Graceful degradation** — if MCP fails and no vault files exist, print: "No TaskNotes found. Run `/ark-tasknotes` to create your first task, or `/ark-health` to check vault configuration."

---

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

## Warmup Contract

Machine-readable subcontract consumed by `/ark-context-warmup`. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`. Calling convention: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` D6.

```yaml
warmup_contract:
  version: 1
  commands:
    - id: status-and-search
      shell: 'python3 "$ARK_SKILLS_ROOT/skills/ark-tasknotes/scripts/warmup_search.py" --tasknotes {{tasknotes_path}} --prefix {{task_prefix}} --task-normalized {{task_normalized}} --scenario {{scenario}} --json'
      inputs:
        tasknotes_path:
          from: env
          env_var: WARMUP_TASKNOTES_PATH
          required: true
        task_prefix:
          from: env
          env_var: WARMUP_TASK_PREFIX
          required: true
        task_normalized:
          from: env
          env_var: WARMUP_TASK_NORMALIZED
          required: true
        scenario:
          from: env
          env_var: WARMUP_SCENARIO
          required: true
      output:
        format: json
        extract:
          matches: '$.matches'
          status_summary: '$.status_summary'
          extracted_component: '$.extracted_component'
        required_fields: [matches, status_summary]
```
