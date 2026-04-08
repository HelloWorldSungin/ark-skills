---
name: wiki-status
description: Show vault statistics, page counts, and health insights
---

# Wiki Status

Show current state of the project's Obsidian vault — page counts, category breakdown, and optional structural insights.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/index.md` for the machine-readable page catalog

## Workflow

### Step 1: Read Index

Read `{vault_path}/index.md`. Parse the frontmatter to get:
- Total page count (from the `summary:` field)
- Generation timestamp (from the `generated:` field)

### Step 2: Report Basic Stats

Count pages per category/type from the index sections. Report:

```
Vault Status: {project_name}
Generated: {timestamp}
Total pages: {count}

By type:
  session-log: N
  epic: N
  story: N
  bug: N
  task: N
  research: N
  compiled-insight: N
  reference: N
  ...
```

### Step 3: Check Index Freshness

```bash
cd {vault_path}
# Count .md files on disk (excluding .obsidian, .git, _Templates, _meta)
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' | wc -l
```

Compare to index page count. If they differ by more than 5, warn: "Index is stale. Run `python3 _meta/generate-index.py` to regenerate."

### Step 4: Insights Mode (Optional)

If the user asks for "insights", "hubs", or "what's central":

1. **Anchor pages:** Find the 10 pages with the most incoming wikilinks
2. **Orphan count:** Find pages with zero incoming wikilinks (excluding index.md and 00-Home.md)
3. **Summary coverage:** Count pages with vs without `summary:` field
4. **Tag coverage:** Count pages with vs without `tags:` field

Report findings as a structured table.
