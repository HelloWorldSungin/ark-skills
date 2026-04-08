---
title: "Vault Schema"
type: meta
tags:
  - meta
  - schema
summary: "Self-documenting vault structure, frontmatter conventions, and navigation patterns for ark-skills."
created: 2026-04-08
last-updated: 2026-04-08
---

# Vault Schema — ark-skills

## Directory Structure

```
vault/
├── 00-Home.md                  # Navigation hub (MOC)
├── index.md                    # Machine-generated flat catalog
├── _Templates/                 # Page templates
│   ├── Session-Template.md
│   ├── Compiled-Insight-Template.md
│   ├── Bug-Template.md
│   ├── Task-Template.md
│   ├── Research-Template.md
│   └── Service-Template.md
├── _Attachments/               # Images, files, non-markdown assets
├── _meta/                      # Vault metadata and tooling
│   ├── vault-schema.md         # This file
│   ├── taxonomy.md             # Canonical tag vocabulary
│   └── generate-index.py       # Index regeneration script
└── TaskNotes/                  # Task tracking
    ├── 00-Project-Management-Guide.md
    ├── Tasks/                  # Active tasks
    │   ├── Epic/
    │   ├── Story/
    │   ├── Bug/
    │   └── Task/
    ├── Archive/                # Completed tasks
    │   ├── Epic/
    │   ├── Story/
    │   ├── Bug/
    │   └── Enhancement/
    ├── Templates/              # Task-specific templates
    ├── Views/                  # Dataview queries or saved views
    └── meta/
        └── Arkskill-counter    # Next task ID counter
```

## Frontmatter Conventions

All pages use YAML frontmatter. Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title |
| `type` | string | Page type (see taxonomy) |
| `tags` | list | Tags from taxonomy |
| `summary` | string | <=200 char description |
| `created` | date | Creation date (YYYY-MM-DD) |
| `last-updated` | date | Last modification date |

### Type-specific fields

**Session logs:** `prev`, `epic`, `session`, `source-tasks`
**Tasks/Bugs:** `task-id`, `status`, `priority`, `component`
**Compiled insights:** `source-sessions`, `source-tasks`
**Research:** `source-sessions`, `source-tasks`

### Important conventions

- Use `type:` (NOT `category:`)
- Use `source-sessions:` and `source-tasks:` (NOT `sources:`)
- Do NOT use `provenance:` markers

## Navigation

- `00-Home.md` is the main entry point (MOC pattern)
- `index.md` is machine-generated — do not edit manually
- Wikilinks (`[[Target]]`) for internal navigation
