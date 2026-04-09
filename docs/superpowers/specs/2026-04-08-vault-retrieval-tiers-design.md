# Vault Retrieval Tiers — Multi-Backend Design

**Date:** 2026-04-08
**Status:** Approved (revised after Codex review)
**Approach:** Tiered Defaults + Per-Skill Override (Approach 3)
**Rollout:** Phased — wiki-query first, other skills after validation

## Problem

Ark-skills vault retrieval uses a single backend: read `index.md`, filter candidates, read top pages. This costs ~2,100 tokens per query and misses experiential knowledge locked in conversation history.

Benchmarking on the ArkNode-AI vault (394 pages) with the query "what kind of model have we decided for the production model?" revealed four backends with distinct strengths:

| Backend | Tokens | Answer Quality | Best For |
|---------|--------|---------------|----------|
| NotebookLM | ~480 | Pre-synthesized with citations | Factual lookups |
| MemPalace (vault pages) | ~2,500 | Answer + reasoning trail from session logs | Deep context, synthesis |
| Obsidian-CLI (two-step) | ~119 + reads | Full-text matches across all files | Inline mentions, vault mutations |
| index.md scan | ~2,100 | Compiled insights only | Structured browse, zero deps |

MemPalace over conversation history alone (without vault pages indexed) scored 0/10 on the same query — it returned TFT training noise because conversations are dominated by experimentation, not decisions. When vault pages were mined into MemPalace, it scored 8/10 and surfaced the reasoning trail (Session 269 pivot, failure modes, metalabel dead end) that other backends missed.

## Solution

Define a 4-tier retrieval defaults section in the CLAUDE.md template. Skills reference tiers by number and override as needed. No shared dispatcher skill — the tier table lives in CLAUDE.md (context-discovery pattern).

## Tier Definitions

| Tier | Backend | Best For | Check | Token Cost |
|------|---------|----------|-------|------------|
| T1 | NotebookLM | Factual lookups, pre-synthesized answers | `{vault_path}/.notebooklm/config.json` exists + `notebooklm` CLI authed | ~500 |
| T2 | MemPalace | Deep context, synthesis, experiential recall (vault + convos in same search) | `command -v mempalace` + project-specific wing exists | ~2,500 |
| T3 | Obsidian-CLI | Full-text search, inline mentions, vault mutations | Invoke `/obsidian-cli` skill, check Obsidian is responsive | ~119 + reads |
| T4 | index.md scan | Structured browse, page discovery, zero-dep fallback | `{vault_path}/index.md` exists | ~2,100 |

### Availability Rules

- T1 requires `{vault_path}/.notebooklm/config.json` + `notebooklm` CLI authenticated
- T2 requires `mempalace` installed + project-specific wing exists (check `mempalace status` for the derived wing name, not just any wing)
- T3 requires Obsidian app running on this machine. Always invoke via `/obsidian-cli` skill (not raw `obsidian` commands). External dependency from the `obsidian` plugin.
- T4 always available if `{vault_path}/index.md` exists

### Failure Messaging

When a preferred tier is unavailable, skills MUST log a clear message before falling back:
- "T1 not available — NotebookLM not configured at {vault_path}/.notebooklm/config.json. Falling back to T4."
- "T2 not available — MemPalace wing '{wing}' not found. Run mine-vault.sh to index. Falling back to T4."
- "T3 not available — Obsidian not responsive. Falling back to T4."

### Query Routing Guide

- "What is X?" / "What did we decide?" → T1 → T4
- "Why did we decide X?" / "Show the reasoning" → T2 → T4
- "What did we try when debugging X?" → T2
- "How does X relate to Y?" (relationship) → T2 → T4
- "What don't we know about X?" (gap analysis) → T2 → T1 → T4
- "Find all mentions of X" → T3 → T4
- "What pages exist about X?" → T4

## MemPalace Wing Convention

### In-Repo Vault (e.g., ark-skills)

`./vault/` is a real directory. Vault pages are mined into the same wing as conversation history. One wing per project.

```bash
# Conversation wing (auto, via stop hook):
#   -Users-sunginkim--superset-projects-ark-skills
# Vault pages mined into same wing:
mine-vault.sh  # detects real dir → uses project wing
```

### Shared External Vault (e.g., ArkNode-AI)

`./vault/` is a symlink to `~/.superset/vaults/ArkNode-AI/`. Vault pages are mined into a monorepo-level wing. Sub-projects search both their conversation wing AND the shared vault wing.

```bash
# Sub-project conversation wing (auto, via stop hook):
#   -Users-sunginkim--superset-projects-ArkNode-AI-projects-trading-signal-ai
# Shared vault wing:
#   -Users-sunginkim--superset-vaults-ArkNode-AI
# mine-vault.sh detects symlink → resolves target → derives monorepo wing
```

Detection logic: `{vault_path}` is a symlink → shared vault → derive wing from canonical symlink target: `$(readlink -f {vault_path} | sed 's|[/.]|-|g')`. `{vault_path}` is a real dir → in-repo vault → derive wing from `$PWD`: `$(echo "$PWD" | sed 's|[/.]|-|g')`. Always use `readlink -f` to resolve to canonical absolute path, avoiding relative symlink issues.

## Per-Skill Wiring

### `wiki-query` — Add T1, T2

Currently: index.md scan only (T4).

New flow:
```
Check query type →
  Factual? → T1 (NotebookLM) → done
  Synthesis? → T2 (MemPalace) → done
  Browse? → T4 (index.md scan, unchanged)
Fallback chain if preferred tier unavailable
```

The existing 3-step retrieval within T4 (Step 1: index scan → Step 2: summary scan → Step 3: full read) is unchanged. The new tiers (T1-T3) layer on top as faster primary paths, with T4's 3-step process as fallback. Note: the old "Tier 1/2/3" naming in wiki-query's SKILL.md should be renamed to "Step 1/2/3" to avoid collision with the new T1-T4 tier system.

### `ark-code-review` — Add T2 (Phase 2)

Currently: reads TaskNotes/epics directly from vault.

New: unchanged vault reads + T2 (MemPalace) query for historical context. Query is derived from changed file paths in the diff (e.g., `"prior bugs in src/trading/"` not vague component names). Cap at 5 search results. Adds an optional "Historical Context" section to review output. Results are presented as informational context, not assertions — reviewer decides relevance.

### `wiki-update` — Add T2 (Phase 2)

Currently: git log + existing vault page reads.

New: unchanged git log + vault reads + T2 query for "decisions and discoveries in {project}". **Guardrail: T2 results are suggestions only.** The skill presents discovered knowledge as candidates for new vault pages, but MUST require user confirmation before writing any page sourced from conversation history. Never auto-write vault content from MemPalace search results.

### `cross-linker` — Add T3 (Phase 2, experimental)

Currently: reads all vault pages to find unlinked mentions. Builds a registry of filenames, titles, aliases, tags, and summaries, then scans full content.

New (experimental): invoke `/obsidian-cli` skill → `obsidian search query="{page title}"` as a fast pre-filter for candidate discovery. **Current full-scan behavior remains the primary path.** Obsidian search is used only to accelerate candidate discovery, not replace the alias/inflection-aware registry scan. This is experimental because Obsidian search may miss aliases, filename-only mentions, and common-word titles that the current approach catches.

### Skills NOT Changed

`ark-tasknotes`, `codebase-maintenance`, `data-ingest`, `notebooklm-vault`, `tag-taxonomy`, `wiki-ingest`, `wiki-lint`, `wiki-setup`, `wiki-status`, `claude-history-ingest` — no retrieval changes needed.

## Setup & Prerequisites

### Prerequisite Check Pattern

Skills run this at the start to know which tiers are available:

```bash
# {vault_path} is derived from context-discovery (CLAUDE.md)
VAULT_PATH="<from context-discovery>"

# T1: NotebookLM
HAS_NOTEBOOKLM=false
if command -v notebooklm &>/dev/null && [ -f "$VAULT_PATH/.notebooklm/config.json" ]; then
    HAS_NOTEBOOKLM=true
fi

# T2: MemPalace — check for the specific project wing, not just any wing
HAS_MEMPALACE=false
if command -v mempalace &>/dev/null; then
    PROJECT_WING="<derived from vault type detection>"
    if mempalace status 2>/dev/null | grep -q "WING: $PROJECT_WING"; then
        HAS_MEMPALACE=true
    fi
fi

# T3: Obsidian-CLI — invoke /obsidian-cli skill, check responsiveness
# (no bash check — skill handles connection)

# T4: index.md — always available
HAS_INDEX=false
[ -f "$VAULT_PATH/index.md" ] && HAS_INDEX=true
```

### Vault Symlink Setup (opt-in only)

When a skill detects `{vault_path}` doesn't exist but CLAUDE.md declares an external vault path, the skill **suggests** the symlink but never auto-creates it:

1. Log: `"Vault not found at {vault_path}. CLAUDE.md declares vault at {external_path}. To create a symlink: ln -s {external_path} {vault_path}"`
2. Continue with whatever tiers are available (T4 fails gracefully, T1/T2/T3 may still work)

The symlink creation is a manual user action, not an automated skill behavior. This avoids mutating repo layout for repos where `vault/` is intentionally tracked or absent.

### `mine-vault.sh` — One-Time Vault Mining Helper

Location: `skills/shared/mine-vault.sh`

Steps:
1. Read CLAUDE.md → extract project name and `{vault_path}`
2. Check `{vault_path}` exists (log instructions if missing, do not auto-create)
3. Detect vault type:
   - Symlink → shared vault → derive wing from canonical target: `$(readlink -f {vault_path} | sed 's|[/.]|-|g')`
   - Real dir → in-repo vault → derive wing from PWD: `$(echo "$PWD" | sed 's|[/.]|-|g')`
4. Create temp dir with symlinked `.md` files only, preserving directory structure:
   ```bash
   find {vault_path} -name "*.md" \
     -not -path "*/.obsidian/*" \
     -not -path "*/node_modules/*" \
     -not -path "*/_Templates/*" \
     | while read f; do
         REL="${f#{vault_path}/}"
         mkdir -p "$TMPDIR/$(dirname "$REL")"
         ln -s "$f" "$TMPDIR/$(dirname "$REL")/$(basename "$f")"
       done
   ```
   **Include:** All vault content pages, session logs, TaskNotes, compiled insights, research
   **Exclude:** `.obsidian/` (plugin configs), `node_modules/`, `_Templates/` (boilerplate)
   Note: `mkdir -p` preserves directory structure, avoiding basename collisions.
5. Run `printf '\n\n\n\n' | mempalace init "$TMPDIR"`
6. Run `mempalace mine "$TMPDIR" --mode projects --wing="{wing}"`
7. Clean up temp dir
8. Print summary: "Mined {N} drawers into wing {wing}. Verify: mempalace status"

### When to Re-Mine

- After significant vault changes (new compiled insights, restructuring, bulk edits)
- No auto-mining hook for vault pages — vault content changes less frequently than conversations
- Conversation indexing remains automatic via the existing stop hook

## File Changes

### Phase 1: wiki-query + foundation

Ship first. Validates the tier system on the most-used retrieval skill before spreading to others.

**Create:**

| File | Purpose |
|------|---------|
| `skills/shared/mine-vault.sh` | One-time vault mining helper (md-only filter, symlink detection, wing naming) |

**Modify:**

| File | Change |
|------|--------|
| `CLAUDE.md` | Add "Vault Retrieval Defaults" section (~20 lines): 4-tier table, availability rules, query routing guide |
| `skills/wiki-query/SKILL.md` | Add T1/T2 as primary retrieval paths, rename old "Tier 1/2/3" to "Step 1/2/3", current flow becomes T4 fallback |
| `README.md` | Update Prerequisites section with optional dependencies (MemPalace, NotebookLM CLI, Obsidian). Add Vault Retrieval setup guide. Update the "Vault Maintenance" section to mention multi-backend retrieval. |

### Phase 2: remaining skills (after wiki-query validation)

Ship after running wiki-query with the new tiers across 2-3 projects and confirming the tier routing, fallback messaging, and token savings work as expected.

| File | Change |
|------|--------|
| `skills/ark-code-review/SKILL.md` | Add T2 query for historical context (derived from diff file paths, capped at 5 results) |
| `skills/wiki-update/SKILL.md` | Add T2 query for undocumented knowledge discovery (suggestions only, user confirmation required) |
| `skills/cross-linker/SKILL.md` | Add T3 via `/obsidian-cli` skill as experimental pre-filter (current full-scan remains primary) |

### Not Changed

10 skills: `ark-tasknotes`, `codebase-maintenance`, `data-ingest`, `notebooklm-vault`, `tag-taxonomy`, `wiki-ingest`, `wiki-lint`, `wiki-setup`, `wiki-status`, `claude-history-ingest`.

## Benchmark Evidence

All measurements from ArkNode-AI vault (394 pages, 2026-04-08).

Query: "what kind of model have we decided for the production model?"
Correct answer: per-direction PnL regressors (XGBRegressor) on donchian_breakout, Sharpe 3.23→11.29.

| Backend | Tokens | Precision | Answer Found |
|---------|--------|-----------|-------------|
| NotebookLM | ~480 | N/A (synthesized) | Yes — with citations, thresholds, ticker universe |
| MemPalace (vault) | ~2,500 | 8/10 | Yes — plus reasoning trail (S269 pivot, failure modes) |
| MemPalace (convos only) | ~1,300 | 0/10 | No — TFT training noise |
| Obsidian-CLI (search:context) | ~13,500 | 8/10 | Yes — but firehose output |
| Obsidian-CLI (two-step) | ~119 + reads | 8/10 | Yes — with selective reads |
| index.md scan | ~2,100 | 3/5 | Yes — via compiled insights |

Key finding: backends are complementary, not competing. Each excels on a different query type and corpus.

## Codex Review (2026-04-08)

14 findings from `/codex review`. Key fixes incorporated:

1. **`./vault/` → `{vault_path}`** — all paths now use context-discovery, not hardcoded
2. **Wing check validates specific project wing** — not just "any wing exists"
3. **Added `relationship` and `gap` query types** — were orphaned from wiki-query's classification
4. **Renamed old "Tier 1/2/3" to "Step 1/2/3"** — avoids naming collision with new T1-T4
5. **cross-linker downgraded to Phase 2 experimental** — Obsidian search misses aliases/inflections
6. **wiki-update guardrail added** — T2 results are suggestions only, require user confirmation
7. **Phased rollout** — wiki-query first (Phase 1), other skills after validation (Phase 2)
8. **ark-code-review bounded** — queries derived from diff file paths, capped at 5 results
9. **Failure messaging required** — skills must log which tier failed and why before fallback
10. **Symlink setup is opt-in** — log instructions, never auto-create
11. **`readlink -f`** — canonical path resolution for symlink wing derivation
12. **mine-vault.sh include/exclude rules explicit** — excludes `.obsidian/`, `node_modules/`, `_Templates/`
