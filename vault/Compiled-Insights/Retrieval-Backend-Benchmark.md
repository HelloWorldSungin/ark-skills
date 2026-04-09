---
title: "Retrieval Backend Benchmark — index.md vs Obsidian-CLI vs MemPalace"
type: compiled-insight
tags:
  - compiled-insight
  - vault
  - skill
summary: "Benchmarked 3 retrieval backends on ArkNode-AI vault (394 pages): index.md scan won for documented decisions (~2K tokens), Obsidian-CLI matched quality but needs two-step pattern, MemPalace failed on vault queries (wrong corpus — indexes conversations, not pages)."
source-sessions: []
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-08
---

# Retrieval Backend Benchmark — index.md vs Obsidian-CLI vs MemPalace

## Summary

Three retrieval backends were benchmarked against the ArkNode-AI vault (394 pages) using the query "what kind of model have we decided for the production model?" The correct answer (per-direction PnL regressors on donchian_breakout, Sharpe 3.23→11.29) was found by index.md scan and Obsidian-CLI but missed entirely by MemPalace. The backends are complementary, not competing — each excels on a different corpus type.

## Key Insights

### index.md Scan Is the Best Default for Vault Queries

Cost ~2,100 tokens (index read + 4 page reads). Found Model-Architecture-Decisions, ArkSignal-Strategy-v1, Donchian-Breakout pages. Answer was clear and definitive. Works because compiled insights have well-written titles and summaries — the index surfaces them via keyword matching.

### Obsidian-CLI Is Powerful but Needs a Two-Step Pattern

`search:context` returned 53KB (~13,500 tokens) for 10 files — a firehose. `search` (file list only) returned ~119 tokens. The practical pattern: use `search` to get candidate file names, then `obsidian read` on the top 2-3. This matches index.md scan in efficiency while providing full-text search (catches inline mentions that title/summary scan misses).

### MemPalace Failed — Wrong Corpus, Not Wrong Tool

MemPalace indexes Claude conversation history, not vault pages. Conversations about models are dominated by TFT training experiments (which were ultimately rejected). The actual "we decided X" production model decision is a tiny signal buried in experimentation noise. 0/10 results answered the question.

### The Three Backends Are Complementary

| Backend | Best For | Corpus |
|---------|----------|--------|
| index.md scan | Documented decisions, factual lookups | Vault pages (curated knowledge) |
| Obsidian-CLI | Full-text search, inline mentions, vault mutations | Vault pages (raw + curated) |
| MemPalace | Experiential knowledge, debugging steps, "why not X?" | Conversation history (procedural memory) |

MemPalace would excel on queries like "what debugging steps did we try when TFT training failed?" — procedural knowledge that lives in conversations, not compiled insights.

## Evidence

- Benchmark run against ArkNode-AI vault on 2026-04-08
- Query: "what kind of model have we decided for the production model?"
- index.md scan: 3/5 candidates relevant, answer in Model-Architecture-Decisions.md
- Obsidian-CLI: 8/10 files relevant, XGBoost-Platt-Pipeline.md L53 has direct hit
- MemPalace: 0/10 results relevant, returned TFT training noise

## Implications

- Skills needing vault retrieval should default to index.md scan (zero external deps, ~2K tokens)
- Obsidian-CLI is a strong option when available — but requires Obsidian running
- MemPalace should NOT be used for vault queries — keep it scoped to conversation history retrieval
- A unified retrieval abstraction should route by corpus type (vault vs. conversations), not query type
- Cross-project queries remain MemPalace's unique strength — TaskNotes aren't in NotebookLM
