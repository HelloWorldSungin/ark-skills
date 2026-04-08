---
name: wiki-query
description: Query vault knowledge with tiered retrieval using index.md and summary fields
---

# Wiki Query

Answer questions by searching the project's Obsidian vault for knowledge.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand vault structure
3. Read `{vault_path}/index.md` to get the full page catalog with summaries

## Workflow

### Step 1: Classify Query

Determine query type:
- **Factual lookup** — "What is X?", "How does Y work?"
- **Relationship** — "How does X relate to Y?"
- **Synthesis** — "What have we learned about X?"
- **Gap** — "What don't we know about X?"

### Step 2: Tiered Retrieval

**Tier 1 — Index scan (always):**
Read `index.md`. Search for pages matching the query by title, tags, and summary. Build a candidate list of 5-10 pages.

**Tier 2 — Summary scan (if needed):**
For each candidate, read the `summary:` field from frontmatter. Filter to the 3-5 most relevant pages based on summary content.

**Tier 3 — Full read (selective):**
Read full content of the top 3 candidates only. Follow up to 1 wikilink hop for additional context.

### Step 3: Synthesize Answer

Compose the answer with citations using `[[page-name]]` wikilink notation. Include:
- Direct answer to the question
- Supporting evidence from vault pages
- Related pages for further reading
- If the vault doesn't contain the answer, say so explicitly

### Quick Mode

If the user says "quick answer" or "just scan": use only Tier 1 (index scan). Return matching page titles and summaries without reading full pages.
