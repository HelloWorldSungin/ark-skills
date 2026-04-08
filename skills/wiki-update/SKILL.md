---
name: wiki-update
description: Sync project knowledge into vault and regenerate index
---

# Wiki Update

Sync the current project's knowledge into its Obsidian vault. This covers documenting new architecture decisions, research findings, and operational changes.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand folder structure
3. Read `{vault_path}/index.md` to know what's already documented

## Workflow

### Step 1: Understand What Changed

Scan the project for recent changes:
```bash
git log --oneline -20
git diff HEAD~5 --stat
```

Also check:
- Recent session logs in `{vault_path}/Session-Logs/`
- Open TaskNotes in `{vault_path}/TaskNotes/Tasks/`
- Any new or modified architecture docs

### Step 2: Decide What to Document

Extract knowledge worth documenting:
- Architecture decisions and their rationale
- New patterns, abstractions, or conventions
- Research findings and experimental results
- Lessons learned from incidents or debugging

Do NOT document: boilerplate changes, minor bug fixes, config tweaks, routine dependency updates.

### Step 3: Write or Update Vault Pages

For each piece of knowledge:
1. Check if an existing page covers this topic (search `index.md`)
2. If yes: read the page, merge new information, update `last-updated:` and `summary:`
3. If no: create a new page in the appropriate domain folder (see vault-schema.md)
4. Use Ark frontmatter schema:
   ```yaml
   ---
   title: "Page Title"
   type: research|reference|guide|compiled-insight
   tags: [domain-tags from _meta/taxonomy.md]
   summary: "<=200 char description"
   created: YYYY-MM-DD
   last-updated: YYYY-MM-DD
   ---
   ```
5. Add wikilinks to related pages (minimum 2-3 per page)

### Step 4: Regenerate Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

Verify the new pages appear in `index.md`.

### Step 5: Commit Vault Changes

```bash
cd {vault_path}
git add -A
git commit -m "docs: sync project knowledge — {brief description of what was updated}"
git push
```
