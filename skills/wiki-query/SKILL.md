---
name: wiki-query
description: Query vault knowledge with tiered retrieval using index.md and summary fields
---

# Wiki Query

Answer questions by searching the project's Obsidian vault for knowledge.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand vault structure
3. Read CLAUDE.md's "Vault Retrieval Defaults" section for tier definitions. If absent, default to T4 only and skip the availability check.

## Tier Availability Check

Before routing, check which backends are available:

```bash
# Derive vault_path from context-discovery
VAULT_PATH="<from CLAUDE.md>"

# T1: NotebookLM — check vault path and project root for config
HAS_T1=false
if command -v notebooklm &>/dev/null; then
    if [ -f "$VAULT_PATH/.notebooklm/config.json" ] || [ -f ".notebooklm/config.json" ]; then
        HAS_T1=true
    fi
fi

# T2: MemPalace — check for the specific project wing
HAS_T2=false
if command -v mempalace &>/dev/null; then
    if [ -L "$VAULT_PATH" ]; then
        PROJECT_WING=$(readlink -f "$VAULT_PATH" | sed 's|[/.]|-|g')
    else
        PROJECT_WING=$(echo "$PWD" | sed 's|[/.]|-|g')
    fi
    if mempalace status 2>/dev/null | grep -q "WING: $PROJECT_WING"; then
        HAS_T2=true
    fi
fi

# Conversation wing (for shared vaults where vault wing ≠ conversation wing)
CONVO_WING=$(echo "$PWD" | sed 's|[/.]|-|g')

# T3: Obsidian-CLI — will check by invoking obsidian:obsidian-cli skill
HAS_T3="check-at-use"

# T4: index.md — always available
HAS_T4=false
[ -f "$VAULT_PATH/index.md" ] && HAS_T4=true
```

Log unavailable tiers:
- If T1 unavailable: "T1 not available — NotebookLM config not found at {vault_path}/.notebooklm/config.json or .notebooklm/config.json. Falling back to T4."
- If T2 unavailable: "T2 not available — MemPalace wing '{wing}' not found. Run: bash skills/shared/mine-vault.sh. Falling back to T4."
- If T4 unavailable (no index.md): "No retrieval backends available. Run `/wiki-update` to generate index.md or configure T1/T2/T3."

## Workflow

### Step 1: Classify Query

Determine query type:
- **Factual lookup** — "What is X?", "How does Y work?", "What did we decide about X?"
- **Relationship** — "How does X relate to Y?"
- **Synthesis** — "What have we learned about X?", "Why did we decide X?"
- **Gap** — "What don't we know about X?"
- **Search** — "Find all mentions of X"
- **Browse** — "What pages exist about X?"

### Step 2: Route to Best Available Tier

**Factual lookup:**
1. If T1 available → query NotebookLM:
   - Read `.notebooklm/config.json` (check `{vault_path}/.notebooklm/` first, then project root `.notebooklm/`) to get notebook ID
   - Run: `notebooklm ask "{query}" --notebook {notebook_id}`
   - If answer is sufficient, return it with NotebookLM citations. Done.
2. Fallback → T4 (Step 3 below)

**Synthesis / Relationship:**
1. If T2 available → query MemPalace:
   - Derive wing name (same logic as availability check above)
   - For shared vaults, also search the conversation wing: `$(echo "$PWD" | sed 's|[/.]|-|g')`
   - Run: `mempalace search "{query}" --wing="$PROJECT_WING" --results 10`
   - If shared vault, also: `mempalace search "{query}" --wing="$CONVO_WING" --results 5`
   - Synthesize answer from returned chunks. Cite source files. Done.
2. Fallback → T4 (Step 3 below)

**Gap (what don't we know):**
1. If T2 available → query MemPalace (surfaces what WAS discussed/tried)
2. If T1 available → query NotebookLM (cross-reference what's documented vs what MemPalace found)
3. Synthesize the gap: what T2 found (experiential) vs what T1/T4 found (documented) reveals what's known but not yet captured. Done.
4. If neither T2 nor T1 available → Fallback → T4 (Step 3 below)

**Search (find all mentions):**
1. If T3 available → invoke `obsidian:obsidian-cli` skill:
   - Run: `obsidian search query="{search term}" limit=10`
   - Read top 3-5 results with `obsidian read file="{name}"`
   - Done.
2. Fallback → T4 (Step 3 below). **Note:** T4 searches index.md titles/tags/summaries only — it returns likely matches, not an exhaustive search. Inform the user: "Obsidian not available for full-text search. Showing likely matches from index.md."

**Browse (what pages exist):**
- Always → T4 (Step 3 below). index.md is the structured catalog.

### Step 3: T4 Fallback — index.md Scan

This is the existing retrieval flow, renamed from "Tiered Retrieval" to avoid collision with T1-T4.

**Step 3a — Index scan (always):**
Read `{vault_path}/index.md`. Search for pages matching the query by title, tags, and summary. Build a candidate list of 5-10 pages.

**Step 3b — Summary scan (if needed):**
For each candidate, read the `summary:` field from frontmatter. Filter to the 3-5 most relevant pages based on summary content.

**Step 3c — Full read (selective):**
Read full content of the top 3 candidates only. Follow up to 1 wikilink hop for additional context.

### Step 4: Synthesize Answer

Compose the answer with citations using `[[page-name]]` wikilink notation. Include:
- Direct answer to the question
- Which tier was used (e.g., "Source: NotebookLM" or "Source: MemPalace search")
- Supporting evidence from vault pages or search results
- Related pages for further reading
- If the vault doesn't contain the answer, say so explicitly

### Quick Mode

If the user says "quick answer" or "just scan": use only T4 Step 3a (index scan). Return matching page titles and summaries without reading full pages.
