---
name: wiki-ingest
description: Distill documents into vault pages using Ark folder structure and frontmatter
---

# Wiki Ingest

Ingest documents (markdown, text, PDF, images) into the project's Obsidian vault by distilling knowledge into interconnected pages.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand folder structure and content placement
3. Read `{vault_path}/index.md` to know what's already documented

## Workflow

### Step 1: Read Source

Accept source material in any format:
- Markdown (`.md`), plain text (`.txt`)
- PDF (`.pdf`) — use Read tool with pages parameter
- Images (`.png`, `.jpg`, `.webp`) — use Read tool for visual content
- Web pages — use WebFetch

### Step 2: Extract Knowledge

Identify:
- Concepts and definitions
- Architecture decisions and rationale
- Procedures and workflows
- Entities (people, services, systems)
- Relationships between entities
- Open questions and unknowns

### Step 3: Determine Placement

Use `_meta/vault-schema.md` to decide where pages belong. Ark vaults use **domain-specific folders**, not generic categories:

| Content Type | Placement |
|-------------|-----------|
| Architecture decisions | `{project_area}/Architecture/` |
| Research findings | `{project_area}/Research/` |
| Operational guides | `{project_area}/Operations/` |
| Cross-cutting insights | `{project_area}/Research/Compiled-Insights/` |
| Infrastructure docs | `Infrastructure/` (if applicable) |

Do NOT create `concepts/`, `entities/`, `skills/`, `references/`, or `synthesis/` folders — these are obsidian-wiki conventions, not Ark conventions.

### Step 4: Write Pages

For each piece of knowledge:

1. Check `index.md` for existing pages on this topic
2. If exists: read the page, merge new info, update `last-updated:` and `summary:`
3. If new: create page with Ark frontmatter:
   ```yaml
   ---
   title: "Page Title"
   type: research|reference|guide|compiled-insight|architecture
   tags: [use canonical tags from _meta/taxonomy.md]
   summary: "<=200 char description of what this page contains"
   source-sessions: []
   source-tasks: []
   created: YYYY-MM-DD
   last-updated: YYYY-MM-DD
   ---
   ```
4. Add 2-3 wikilinks to related existing pages
5. Do NOT add `provenance:` markers — Ark vaults don't use them

### Step 5: Update Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

### Step 6: Commit

```bash
cd {vault_path}
git add -A
git commit -m "docs: ingest {source_description} — {N} pages created/updated"
git push
```
