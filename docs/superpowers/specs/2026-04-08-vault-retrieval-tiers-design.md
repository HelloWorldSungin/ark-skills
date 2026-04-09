# Vault Retrieval Tiers — Multi-Backend Design

**Date:** 2026-04-08
**Status:** Approved
**Approach:** Tiered Defaults + Per-Skill Override (Approach 3)

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
| T1 | NotebookLM | Factual lookups, pre-synthesized answers | `.notebooklm/config.json` exists in vault + `notebooklm` CLI authed | ~500 |
| T2 | MemPalace | Deep context, synthesis, experiential recall (vault + convos in same search) | `command -v mempalace` + wing exists for project | ~2,500 |
| T3 | Obsidian-CLI | Full-text search, inline mentions, vault mutations | Invoke `/obsidian-cli` skill, check Obsidian is responsive | ~119 + reads |
| T4 | index.md scan | Structured browse, page discovery, zero-dep fallback | `./vault/index.md` exists | ~2,100 |

### Availability Rules

- T1 requires `.notebooklm/config.json` in vault root + `notebooklm` CLI authenticated
- T2 requires `mempalace` installed + vault mined (run `mine-vault.sh`) + conversation history indexed (auto via stop hook)
- T3 requires Obsidian app running on this machine. Always invoke via `/obsidian-cli` skill (not raw `obsidian` commands)
- T4 always available if `./vault/index.md` exists

### Query Routing Guide

- "What is X?" / "What did we decide?" → T1 → T4
- "Why did we decide X?" / "Show the reasoning" → T2 → T4
- "What did we try when debugging X?" → T2
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

Detection logic: `./vault/` is a symlink → shared vault → derive wing from symlink target path. `./vault/` is a real dir → in-repo vault → derive wing from `$PWD`.

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

The existing tiered retrieval (index scan → summary scan → full read) becomes the T4 fallback path. New tiers layer on top, not replace.

### `ark-code-review` — Add T2

Currently: reads TaskNotes/epics directly from vault.

New: unchanged vault reads + T2 (MemPalace) query for "prior bugs and fixes in {component}". Surfaces debugging history and failed approaches from conversations. Adds a "Historical Context" section to review output.

### `wiki-update` — Add T2

Currently: git log + existing vault page reads.

New: unchanged git log + vault reads + T2 query for "decisions and discoveries in {project}". Surfaces undocumented knowledge from recent conversations. Suggests new vault pages for knowledge not yet captured.

### `cross-linker` — Add T3

Currently: reads all vault pages to find unlinked mentions.

New: invoke `/obsidian-cli` skill → `obsidian search query="{page title}"` per candidate. Much faster than reading every page. Fallback: T4 (read all pages, current behavior).

### Skills NOT Changed

`ark-tasknotes`, `codebase-maintenance`, `data-ingest`, `notebooklm-vault`, `tag-taxonomy`, `wiki-ingest`, `wiki-lint`, `wiki-setup`, `wiki-status`, `claude-history-ingest` — no retrieval changes needed.

## Setup & Prerequisites

### Prerequisite Check Pattern

Skills run this at the start to know which tiers are available:

```bash
# T1: NotebookLM
HAS_NOTEBOOKLM=false
if command -v notebooklm &>/dev/null && [ -f "./vault/.notebooklm/config.json" ]; then
    HAS_NOTEBOOKLM=true
fi

# T2: MemPalace
HAS_MEMPALACE=false
if command -v mempalace &>/dev/null; then
    WING=$(mempalace status 2>/dev/null | grep -c "WING:")
    [ "$WING" -gt 0 ] && HAS_MEMPALACE=true
fi

# T3: Obsidian-CLI — invoke /obsidian-cli skill, check responsiveness
# (no bash check — skill handles connection)

# T4: index.md — always available
HAS_INDEX=false
[ -f "./vault/index.md" ] && HAS_INDEX=true
```

### Vault Symlink Setup

When a skill detects `./vault/` doesn't exist but CLAUDE.md declares an external vault path:

1. Offer: `Create symlink? ln -s {external_vault_path} ./vault/`
2. If confirmed, create symlink
3. Add `vault` to `.gitignore` (symlinks to external paths shouldn't be committed)
4. Continue with skill

### `mine-vault.sh` — One-Time Vault Mining Helper

Location: `skills/shared/mine-vault.sh`

Steps:
1. Read CLAUDE.md → extract project name
2. Check `./vault/` exists (offer symlink if missing)
3. Detect vault type:
   - Symlink → shared vault → derive wing from symlink target: `$(readlink ./vault/ | sed 's|[/.]|-|g')`
   - Real dir → in-repo vault → derive wing from PWD: `$(echo "$PWD" | sed 's|[/.]|-|g')`
4. Create temp dir with symlinked `.md` files only:
   ```bash
   find ./vault/ -name "*.md" -not -path "*/.obsidian/*" -not -path "*/node_modules/*"
   ```
5. Run `printf '\n\n\n\n' | mempalace init "$TMPDIR"`
6. Run `mempalace mine "$TMPDIR" --mode projects --wing="{wing}"`
7. Clean up temp dir
8. Print summary

### When to Re-Mine

- After significant vault changes (new compiled insights, restructuring, bulk edits)
- No auto-mining hook for vault pages — vault content changes less frequently than conversations
- Conversation indexing remains automatic via the existing stop hook

## File Changes

### Create

| File | Purpose |
|------|---------|
| `skills/shared/mine-vault.sh` | One-time vault mining helper (md-only filter, symlink detection, wing naming) |

### Modify

| File | Change |
|------|--------|
| `CLAUDE.md` | Add "Vault Retrieval Defaults" section (~20 lines): 4-tier table, availability rules, query routing guide |
| `skills/wiki-query/SKILL.md` | Add T1/T2 as primary retrieval paths, current flow becomes T4 fallback |
| `skills/ark-code-review/SKILL.md` | Add T2 query for historical context section |
| `skills/wiki-update/SKILL.md` | Add T2 query for undocumented knowledge discovery |
| `skills/cross-linker/SKILL.md` | Add T3 via `/obsidian-cli` skill for link candidate discovery |
| `README.md` | Update Prerequisites section with optional dependencies (MemPalace, NotebookLM CLI, Obsidian). Add Vault Retrieval setup guide. Update the "Vault Maintenance" section to mention multi-backend retrieval. |

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
