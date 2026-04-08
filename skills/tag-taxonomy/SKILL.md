---
name: tag-taxonomy
description: Validate and normalize tags against the vault's canonical taxonomy
---

# Tag Taxonomy

Enforce consistent tagging across the vault using the canonical vocabulary in `_meta/taxonomy.md`.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/taxonomy.md` for the canonical tag list

## Modes

### Mode 1: Tag Audit

Scan all pages, extract `tags:` from frontmatter, and report:
- **Unknown tags:** Tags not in `_meta/taxonomy.md`
- **Alias tags:** Tags that should be normalized (e.g., `walkforward` -> `walk-forward`)
- **Over-tagged pages:** Pages with more than 5 tags
- **Untagged pages:** Pages missing `tags:` field

```bash
cd {vault_path}
python3 -c "
import re, os
from collections import Counter
tags = Counter()
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.obsidian','.git','.claude-plugin','.github','.notebooklm','_Templates'}]
    for f in files:
        if not f.endswith('.md'): continue
        try: content = open(os.path.join(root, f), encoding='utf-8').read()
        except: continue
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not m: continue
        in_tags = False
        for line in m.group(1).split('\n'):
            if re.match(r'^tags:', line):
                in_tags = True
                inline = re.match(r'^tags:\s*\[(.+)\]', line)
                if inline:
                    for t in inline.group(1).split(','): tags[t.strip().strip('\"').strip(\"'\")] += 1
                    in_tags = False
                continue
            if in_tags:
                item = re.match(r'^  - (.+)', line)
                if item: tags[item.group(1).strip()] += 1
                else: in_tags = False
for tag, count in tags.most_common(): print(f'{count:4d}  {tag}')
"
```

Compare output against `_meta/taxonomy.md`. Flag discrepancies.

### Mode 2: Tag Normalization

After audit, fix non-canonical tags:
1. For each page with alias tags, replace with canonical form
2. For unknown tags used on 2+ pages, suggest adding to taxonomy
3. For unknown tags on 1 page, suggest replacing with existing canonical tag

### Mode 3: Add New Tag

When a new tag is needed:
1. Check if an existing tag covers the concept
2. Determine section (Structural, Domain, Component, Session)
3. Add to `_meta/taxonomy.md` with name, purpose, and any aliases
4. Commit the taxonomy update
