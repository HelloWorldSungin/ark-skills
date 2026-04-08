---
name: data-ingest
description: Process logs, transcripts, chat exports, and data dumps into vault pages
---

# Data Ingest

Ingest arbitrary text data (chat exports, logs, transcripts, research papers) into the project's Obsidian vault.

## Project Discovery

1. Read the project's CLAUDE.md to find: project name, vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand placement
3. Read `{vault_path}/index.md` to check for existing coverage

## Workflow

### Step 1: Identify Source Format

Detect format from file extension and content:
- JSON/JSONL — structured data, chat exports
- Markdown — documentation, notes
- Plain text — logs, transcripts
- CSV/TSV — tabular data
- HTML — web clippings
- Images — use Read tool with vision
- Chat exports — ChatGPT, Slack, Discord

### Step 2: Extract Knowledge

Focus on substance:
- Topics discussed, decisions made, facts learned
- Procedures and workflows
- Entities and relationships
- For conversations: distill the knowledge, not the dialogue

### Step 3: Cluster and Deduplicate

Group by topic (not by source file). Check `index.md` for existing pages on the same topics. Merge with existing knowledge rather than creating duplicates.

### Step 4: Write Vault Pages

Place in appropriate domain folders per `_meta/vault-schema.md`.

For synthesized findings, use Compiled-Insight-Template:
```yaml
---
title: "{Title}"
type: compiled-insight
tags: [compiled-insight, {domain-tags}]
summary: "<=200 char description"
source-sessions: []
source-tasks: []
created: {today}
last-updated: {today}
---
```

For reference material, use:
```yaml
---
title: "{Title}"
type: reference
tags: [{domain-tags}]
summary: "<=200 char description"
created: {today}
last-updated: {today}
---
```

Add 2-3 wikilinks per page. Do NOT use `provenance:` markers.

### Step 5: Update Index and Commit

```bash
cd {vault_path}
python3 _meta/generate-index.py
git add -A
git commit -m "docs: ingest {source_description} — {N} pages created/updated"
git push
```
