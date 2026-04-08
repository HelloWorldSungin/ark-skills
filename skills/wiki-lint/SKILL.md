---
name: wiki-lint
description: Audit vault health — broken links, missing frontmatter, stale index, tag violations
---

# Wiki Lint

Audit the project's Obsidian vault for structural issues and produce a health report.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/taxonomy.md` for canonical tag list
3. Read `{vault_path}/index.md` for page inventory

## Lint Checks

Run all checks in sequence. Report findings as a structured list.

### Check 1: Broken Wikilinks

```bash
cd {vault_path}
grep -roh '\[\[[^]]*\]\]' --include="*.md" . | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u | while read link; do
  base=$(echo "$link" | sed 's/#.*//')
  [ -z "$base" ] && continue
  found=$(find . -name "${base}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "BROKEN: [[${link}]]"
done
```

### Check 2: Orphaned Pages

Find pages with zero incoming wikilinks (excluding index.md, 00-Home.md, templates):

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  basename=$(basename "$f" .md)
  incoming=$(grep -rl "\[\[$basename" --include="*.md" . 2>/dev/null | grep -v "$f" | wc -l | tr -d ' ')
  [ "$incoming" -eq 0 ] && echo "ORPHAN: $f"
done
```

### Check 3: Missing Frontmatter

Check all pages have required fields: `title`, `type` (or `task-type`), `tags`

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  head -1 "$f" | grep -q "^---" || echo "NO FRONTMATTER: $f"
done
```

### Check 4: Missing Summary

Check for `summary:` field on all pages. Report count of pages without it.

### Check 5: Tag Violations

Compare all tags in use against `_meta/taxonomy.md`. Flag:
- Tags not in taxonomy
- Alias tags that should be normalized

### Check 6: Index Freshness

Compare page count in `index.md` vs actual `.md` files on disk. If they differ, the index is stale.

### Check 7: Summary Length

Find pages where `summary:` exceeds 200 characters.

## Report Format

```
Wiki Lint Report: {project_name}
================================
Broken wikilinks: N
Orphaned pages: N
Missing frontmatter: N
Missing summary: N
Tag violations: N
Index stale: yes/no
Summary too long: N

Details:
[list each issue with file path]
```

## Skipped Checks (not applicable to Ark vaults)

- Provenance drift — Ark vaults don't use `provenance:` markers
- Stale content by timestamp — no source-tracking manifest
- Contradiction detection — too expensive for routine lint
