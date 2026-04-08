---
name: claude-history-ingest
description: Mine Claude Code conversation history and memory files into compiled vault insights
---

# Claude History Ingest

Extract knowledge from Claude Code conversation history (`~/.claude/`) and distill into compiled insight pages in the project's vault.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/_Templates/Compiled-Insight-Template.md` for output format

## Workflow

### Step 1: Survey Claude History

```bash
# Find project-specific Claude data
ls ~/.claude/projects/*/
ls ~/.claude/projects/*/memory/*.md 2>/dev/null
```

Identify:
- **Memory files** (highest value) — `~/.claude/projects/*/memory/*.md`
- **MEMORY.md indexes** — `~/.claude/projects/*/MEMORY.md`
- **Conversation JSONL** — `~/.claude/projects/*/*.jsonl` (large, lower signal-to-noise)

### Step 2: Read Memory Files First

Parse YAML frontmatter from memory files. Prioritize by type:
- `type: user` -> knowledge about the developer
- `type: feedback` -> workflow preferences and corrections
- `type: project` -> project decisions and context
- `type: reference` -> external resource pointers

### Step 3: Parse Conversations (Optional)

If the user wants deeper mining, parse JSONL files:
- Extract `user` and `assistant` messages only
- Skip `thinking`, `tool_use`, `progress` entries
- Focus on messages containing decisions, discoveries, or lessons

### Step 4: Cluster by Topic

Group findings by topic across all sources. Common clusters:
- Architecture decisions
- Debugging lessons
- Workflow patterns
- Performance discoveries
- Failed approaches

### Step 5: Write Compiled Insight Pages

For each cluster, create a page in `{vault_path}/{project_area}/Research/Compiled-Insights/`:

Use the Compiled-Insight-Template:
```yaml
---
title: "{Insight Title}"
type: compiled-insight
tags:
  - compiled-insight
  - {domain-tag from taxonomy}
summary: "{<=200 char finding summary}"
source-sessions: []
source-tasks: []
created: {today}
last-updated: {today}
---
```

Write:
- **Key Finding** — one-paragraph conclusion
- **Evidence** — specific data points from conversations
- **Context** — what prompted the investigation
- **Implications** — what to do differently based on this knowledge

### Step 6: Update Index and Commit

```bash
cd {vault_path}
python3 _meta/generate-index.py
git add -A
git commit -m "docs: ingest Claude history — {N} compiled insights created"
git push
```
