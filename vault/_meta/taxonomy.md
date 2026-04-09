---
title: "Tag Taxonomy"
type: meta
tags:
  - meta
  - taxonomy
summary: "Canonical tag vocabulary for ark-skills vault. All tags should come from this list."
created: 2026-04-08
last-updated: 2026-04-08
---

# Tag Taxonomy — ark-skills

## Structural Tags

These tags describe what a page IS:

| Tag | Description |
|-----|-------------|
| `home` | Home/dashboard page |
| `moc` | Map of Content — navigation hub |
| `session-log` | Session log entry |
| `compiled-insight` | Synthesized knowledge from multiple sessions |
| `task` | Task, story, epic, or bug |
| `bug` | Bug report (used alongside `task`) |
| `research` | Research findings |
| `service` | Service/infrastructure documentation |
| `meta` | Vault metadata (schema, taxonomy, tooling) |
| `template` | Page template |

## Status Tags

| Tag | Description |
|-----|-------------|
| `dashboard` | Overview/status page |
| `archive` | Archived/completed content |

## Domain Tags

Project-specific tags — extend as needed:

| Tag | Description |
|-----|-------------|
| `skill` | Related to skill authoring or design |
| `plugin` | Claude Code plugin system |
| `vault` | Vault management and tooling |
| `infrastructure` | Deployment, CI/CD, hosting |
| `context-discovery` | Context-discovery pattern |
| `retrieval` | Vault retrieval backends and tier routing |

## Conventions

1. Tags are lowercase, hyphen-separated
2. Prefer existing tags over creating new ones
3. Add new domain tags here before using them
4. Every page should have at least one structural tag
