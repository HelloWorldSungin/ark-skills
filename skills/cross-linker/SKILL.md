---
name: cross-linker
description: Discover and add missing wikilinks between vault pages
---

# Cross-Linker

Scan vault pages for unlinked mentions of other pages and add missing wikilinks.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_root}/index.md` for the full page inventory

## Workflow

### Step 1: Build Page Registry

Glob all `.md` files (exclude `.obsidian/`, `.git/`, `_Templates/`, `_meta/`).
Extract per page: filename, title, aliases (if any), tags, summary.

### Step 2: Scan for Missing Links

For each page:
1. Read full content
2. Extract existing `[[wikilinks]]`
3. Search for unlinked mentions: filenames, titles without `[[...]]` wrapper
4. Skip: self-references, common words, code blocks, frontmatter
5. Match case-insensitively

### Step 3: Score and Filter

- **Exact name match in text:** High confidence — apply
- **Shared tags (2+) but no link:** Medium confidence — apply
- **Partial name match:** Low confidence — skip

### Step 4: Apply Links

**Inline (preferred):** Find first natural mention, wrap in `[[page-name]]`
**Related section (fallback):** If term not naturally mentioned but semantically related, add `## Related` section with links

### Step 5: Report

```
Cross-Linker Report:
  Pages scanned: N
  Links added: M
  Pages modified: P
  Orphans remaining: Q
```

### Step 6: Commit

```bash
cd {vault_root}
git add -A
git commit -m "docs: add N missing wikilinks from cross-linker pass"
```
