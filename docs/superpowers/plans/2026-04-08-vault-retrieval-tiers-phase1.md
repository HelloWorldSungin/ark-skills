# Vault Retrieval Tiers — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-backend vault retrieval (NotebookLM, MemPalace, Obsidian-CLI, index.md) to wiki-query and establish the foundation for Phase 2 skills.

**Architecture:** Retrieval tier defaults live in CLAUDE.md (context-discovery pattern). wiki-query classifies the query type, checks backend availability, and routes to the best available tier with fallback messaging. A shared mine-vault.sh script handles MemPalace indexing of vault markdown files.

**Tech Stack:** Bash (mine-vault.sh), MemPalace CLI (ChromaDB), NotebookLM CLI, Obsidian CLI (via /obsidian-cli skill), Markdown (SKILL.md instructions)

**Spec:** `docs/superpowers/specs/2026-04-08-vault-retrieval-tiers-design.md`

---

### Task 1: Create `mine-vault.sh`

**Files:**
- Create: `skills/shared/mine-vault.sh`

- [ ] **Step 1: Create the shared directory and script**

```bash
#!/bin/bash
# mine-vault.sh — Index vault markdown files into MemPalace
#
# Usage: bash skills/shared/mine-vault.sh
#
# Reads CLAUDE.md for vault path, detects symlink vs real dir,
# filters to .md files only, and mines into the correct wing.
#
# Prerequisites: mempalace installed (pipx install mempalace)

set -euo pipefail

# === STEP 1: Find vault path ===
# Accept vault path as argument (for monorepo hub setups where context-discovery
# resolves through sub-project CLAUDEs — Claude does the discovery, passes the path).
# If no argument, extract from CLAUDE.md's Project Configuration table.
if [ -n "${1:-}" ] && [ -e "$1" ]; then
    VAULT_PATH="${1%/}"
    echo "Using vault path from argument: $VAULT_PATH"
else
    if [ ! -f "CLAUDE.md" ]; then
        echo "ERROR: No CLAUDE.md in current directory. Run from project root."
        echo "Usage: bash skills/shared/mine-vault.sh [vault_path]"
        exit 1
    fi

    # Extract vault path — find the backtick-enclosed value on the "Obsidian Vault" row
    VAULT_PATH=$(grep "Obsidian Vault" CLAUDE.md | grep -o '`[^`]*`' | head -1 | tr -d '`' | sed 's|/$||')

    # Fallback: check common locations
    if [ -z "$VAULT_PATH" ] || [ ! -e "$VAULT_PATH" ]; then
        for CANDIDATE in vault Vault obsidian; do
            if [ -e "$CANDIDATE" ]; then
                VAULT_PATH="$CANDIDATE"
                break
            fi
        done
    fi
fi

# Normalize: strip trailing slash
VAULT_PATH="${VAULT_PATH%/}"

if [ ! -e "$VAULT_PATH" ]; then
    echo "ERROR: Vault not found at '$VAULT_PATH'."
    echo "Usage: bash skills/shared/mine-vault.sh [vault_path]"
    echo "Or check CLAUDE.md's 'Obsidian Vault' row, or create a symlink:"
    echo "  ln -s /path/to/your/vault ./vault"
    exit 1
fi

# === STEP 2: Check mempalace is installed ===
if ! command -v mempalace &>/dev/null; then
    echo "ERROR: mempalace not found. Install it:"
    echo "  pipx install 'mempalace>=3.0.0,<4.0.0'"
    exit 1
fi

# === STEP 3: Detect vault type and derive wing ===
if [ -L "$VAULT_PATH" ]; then
    # Shared external vault — derive wing from canonical symlink target
    CANONICAL=$(readlink -f "$VAULT_PATH")
    WING=$(echo "$CANONICAL" | sed 's|[/.]|-|g')
    echo "Detected: shared vault (symlink → $CANONICAL)"
else
    # In-repo vault — derive wing from PWD
    WING=$(echo "$PWD" | sed 's|[/.]|-|g')
    echo "Detected: in-repo vault"
fi
echo "Wing: $WING"

# === STEP 4: Create temp dir with .md files only ===
TMPDIR=$(mktemp -d)/vault-md-only
echo "Filtering .md files (excluding .obsidian/, node_modules/, _Templates/)..."

FILE_COUNT=0
find "$VAULT_PATH" -name "*.md" \
    -not -path "*/.obsidian/*" \
    -not -path "*/node_modules/*" \
    -not -path "*/_Templates/*" \
    | while IFS= read -r f; do
        REL="${f#$VAULT_PATH/}"
        DIR="$TMPDIR/$(dirname "$REL")"
        mkdir -p "$DIR"
        ln -s "$f" "$DIR/$(basename "$f")"
    done

FILE_COUNT=$(find "$TMPDIR" -name "*.md" | wc -l | tr -d ' ')
echo "Found $FILE_COUNT .md files"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "ERROR: No .md files found in $VAULT_PATH"
    rm -rf "$(dirname "$TMPDIR")"
    exit 1
fi

# === STEP 5: Init mempalace (non-interactive) ===
echo "Initializing mempalace for temp directory..."
printf '\n\n\n\n\n' | mempalace init "$TMPDIR" 2>&1 | tail -5

# === STEP 6: Mine ===
echo "Mining $FILE_COUNT files into wing '$WING'..."
mempalace mine "$TMPDIR" --mode projects --wing="$WING"

# === STEP 7: Cleanup ===
rm -rf "$(dirname "$TMPDIR")"

echo ""
echo "Done. Verify with: mempalace status"
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x skills/shared/mine-vault.sh`

- [ ] **Step 3: Test on ark-skills vault**

Run: `bash skills/shared/mine-vault.sh`

Expected: Script detects in-repo vault at `vault/`, filters to .md files, mines into the project wing, prints summary with drawer count.

Verify: `mempalace status` shows drawers in the correct wing.

- [ ] **Step 4: Commit**

```bash
git add skills/shared/mine-vault.sh
git commit -m "feat: add mine-vault.sh for MemPalace vault indexing

Indexes vault .md files into MemPalace, excluding .obsidian/, node_modules/,
_Templates/. Detects symlink (shared vault) vs real dir (in-repo vault)
and derives the correct wing name."
```

---

### Task 2: Add Vault Retrieval Defaults to CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:89` (after the Available Skills section, before end of file)

- [ ] **Step 1: Add the Vault Retrieval Defaults section**

Append after the last line of CLAUDE.md (after the `/data-ingest` entry):

```markdown

## Vault Retrieval Defaults

Four retrieval backends, ordered by richness. Check availability in order.
Use the first available backend appropriate for the query type.

| Tier | Backend | Best For | Token Cost |
|------|---------|----------|------------|
| T1 | NotebookLM | Factual lookups, pre-synthesized answers | ~500 |
| T2 | MemPalace | Deep context, synthesis, experiential recall | ~2,500 |
| T3 | Obsidian-CLI (via `obsidian:obsidian-cli` skill) | Full-text search, inline mentions | ~119 + reads |
| T4 | index.md scan | Structured browse, page discovery, zero-dep fallback | ~2,100 |

### Availability Checks

- **T1:** `notebooklm` CLI authenticated + config exists at `{vault_path}/.notebooklm/config.json` OR `.notebooklm/config.json` in project root
- **T2:** `mempalace` installed + project-specific wing exists in `mempalace status`
- **T3:** Obsidian app running. Always invoke via `obsidian:obsidian-cli` skill.
- **T4:** `{vault_path}/index.md` exists. Always available.

### Failure Messaging

When a preferred tier is unavailable, log before falling back:
- "T1 not available — NotebookLM not configured. Falling back to T4."
- "T2 not available — MemPalace wing not found. Run `bash skills/shared/mine-vault.sh` to index. Falling back to T4."
- "T3 not available — Obsidian not responsive. Falling back to T4."

### Query Routing

- "What is X?" / "What did we decide?" → T1 → T4
- "Why did we decide X?" / "Show the reasoning" → T2 → T4
- "What did we try when debugging X?" → T2
- "How does X relate to Y?" → T2 → T4
- "What don't we know about X?" → T2 → T1 → T4
- "Find all mentions of X" → T3 → T4
- "What pages exist about X?" → T4
```

- [ ] **Step 2: Verify CLAUDE.md is valid**

Run: `tail -40 CLAUDE.md`

Expected: The new section appears cleanly after the existing content. No duplicate sections. Markdown renders correctly.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Vault Retrieval Defaults to CLAUDE.md

Four-tier retrieval system: NotebookLM, MemPalace, Obsidian-CLI, index.md.
Skills reference tiers by number. Query routing guide maps question types
to the best backend with fallback chains."
```

---

### Task 3: Rewrite `wiki-query` SKILL.md with tier support

**Files:**
- Modify: `skills/wiki-query/SKILL.md` (full rewrite)

- [ ] **Step 1: Rewrite the SKILL.md**

Replace the entire contents of `skills/wiki-query/SKILL.md` with:

```markdown
---
name: wiki-query
description: Query vault knowledge with tiered retrieval using index.md and summary fields
---

# Wiki Query

Answer questions by searching the project's Obsidian vault for knowledge.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/vault-schema.md` to understand vault structure
3. Read CLAUDE.md's "Vault Retrieval Defaults" section for tier definitions

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

# T3: Obsidian-CLI — will check by invoking obsidian:obsidian-cli skill
HAS_T3="check-at-use"

# T4: index.md — always available
HAS_T4=false
[ -f "$VAULT_PATH/index.md" ] && HAS_T4=true
```

Log unavailable tiers:
- If T1 unavailable: "T1 not available — NotebookLM config not found at {vault_path}/.notebooklm/config.json or .notebooklm/config.json."
- If T2 unavailable: "T2 not available — MemPalace wing '{wing}' not found. Run: bash skills/shared/mine-vault.sh"

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
3. Fallback → T4 (Step 3 below)
The gap between T2 results (experiential) and T1/T4 results (documented) reveals what's known but not yet captured.

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
```

- [ ] **Step 2: Verify the rewrite parses correctly**

Run: `head -5 skills/wiki-query/SKILL.md`

Expected:
```
---
name: wiki-query
description: Query vault knowledge with tiered retrieval using index.md and summary fields
---
```

Run: `grep -c "Step\|Tier\|T1\|T2\|T3\|T4" skills/wiki-query/SKILL.md`

Expected: Multiple matches confirming all tiers and steps are present.

- [ ] **Step 3: Verify no hardcoded project references leaked in**

Run: `grep -n "ArkPoly\|ArkSignal\|trading-signal-ai\|CT100\|CT110\|CT120\|192\.168\|sunginkim" skills/wiki-query/SKILL.md`

Expected: No output (zero matches).

- [ ] **Step 4: Commit**

```bash
git add skills/wiki-query/SKILL.md
git commit -m "feat: add T1-T4 retrieval tiers to wiki-query

Routes factual queries to NotebookLM (T1), synthesis/relationship/gap
to MemPalace (T2), search to Obsidian-CLI (T3), browse to index.md (T4).
Old Tier 1/2/3 renamed to Step 3a/3b/3c within T4 fallback."
```

---

### Task 4: Update README.md

**Files:**
- Modify: `README.md:19-30` (Prerequisites section)
- Modify: `README.md:72-81` (Vault Maintenance section)

- [ ] **Step 1: Update the Prerequisites section**

Replace lines 19-30 (the current Prerequisites section) with:

```markdown
### Prerequisites

**Required for all skills:** None — skills are instruction-only with no external dependencies by default.

**Optional — enhances vault retrieval (see Vault Retrieval Defaults in CLAUDE.md):**

| Dependency | Skills Enhanced | Install |
|------------|----------------|---------|
| [MemPalace](https://github.com/milla-jovovich/mempalace) | `/wiki-query` (T2), `/claude-history-ingest` | `pipx install "mempalace>=3.0.0,<4.0.0"` |
| [NotebookLM CLI](https://github.com/nichochar/notebooklm-cli) | `/wiki-query` (T1), `/notebooklm-vault` | `pipx install notebooklm-cli` + `notebooklm login` |
| [Obsidian CLI](https://help.obsidian.md/cli) | `/wiki-query` (T3), `/cross-linker` (Phase 2) | Requires Obsidian app running. Uses `obsidian:obsidian-cli` skill. |

**First-time MemPalace vault setup:**

```bash
# Index vault markdown files into MemPalace (one-time)
bash skills/shared/mine-vault.sh

# Install the conversation auto-indexing hook (per-project)
bash skills/claude-history-ingest/hooks/install-hook.sh
```
```

- [ ] **Step 2: Update the Vault Maintenance section**

Replace lines 74-79 only (the paragraph starting "All 10 vault skills use the **tiered retrieval** pattern" through the "3. **Tier 3 — Full read**" line). Preserve the `/claude-history-ingest` paragraph at line 81 and everything after it.

Replace with:

```markdown
`/wiki-query` supports **multi-backend retrieval** (Phase 1) via the Vault Retrieval Defaults in CLAUDE.md:
- **T1 (NotebookLM):** Pre-synthesized answers for factual lookups (~500 tokens)
- **T2 (MemPalace):** Deep context and synthesis from vault pages + conversation history (~2,500 tokens)
- **T3 (Obsidian-CLI):** Full-text search across all vault files (~119 tokens + selective reads)
- **T4 (index.md scan):** Zero-dependency fallback using the existing 3-step index/summary/full-read pattern (~2,100 tokens)

Other vault skills continue to use the T4 (index.md scan) pattern. Multi-backend support for additional skills is planned for Phase 2.
```

Preserve the existing paragraph about key operations and `/claude-history-ingest` below it.

- [ ] **Step 3: Verify README renders correctly**

Run: `grep -n "Prerequisites\|Vault Maintenance\|MemPalace\|NotebookLM\|Obsidian-CLI\|mine-vault" README.md`

Expected: All new sections appear at the correct locations. No duplicate headers.

- [ ] **Step 4: Verify no broken markdown**

Run: `grep -c "^#" README.md`

Expected: Same number of top-level headings as before (or +1 if sub-headings were added).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README with multi-backend retrieval prerequisites

Add optional dependency table (MemPalace, NotebookLM CLI, Obsidian CLI).
Add mine-vault.sh setup instructions. Update Vault Maintenance section
to describe the T1-T4 tier system."
```

---

### Task 5: End-to-End Validation

**Files:** None (read-only verification)

- [ ] **Step 1: Run the hardcoded reference check**

Run: `grep -rn "ArkPoly\|ArkSignal\|trading-signal-ai\|CT100\|CT110\|CT120\|192\.168" skills/`

Expected: Zero matches.

- [ ] **Step 2: Verify all 14 skills still exist**

Run: `find skills -name SKILL.md | wc -l`

Expected: `14`

- [ ] **Step 3: Verify context-discovery is referenced in wiki-query**

Run: `grep -c "CLAUDE.md\|context-discovery\|Project Discovery\|vault_path" skills/wiki-query/SKILL.md`

Expected: Multiple matches (>= 5).

- [ ] **Step 4: Verify mine-vault.sh is executable**

Run: `test -x skills/shared/mine-vault.sh && echo "OK" || echo "NOT EXECUTABLE"`

Expected: `OK`

- [ ] **Step 5: Test wiki-query mentally against routing table**

Trace these queries through the new SKILL.md and verify they'd route correctly:
- "What is the plugin architecture?" → T1 (factual) → T4 fallback
- "Why did we move vaults to standalone repos?" → T2 (synthesis) → T4 fallback
- "Find all mentions of ChromaDB" → T3 (search) → T4 fallback
- "What pages exist about infrastructure?" → T4 (browse)

- [ ] **Step 6: Final commit (if any remaining changes)**

```bash
git status
# If clean: no commit needed
# If changes: stage and commit with descriptive message
```
