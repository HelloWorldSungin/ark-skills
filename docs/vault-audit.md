# Obsidian Vault Audit: Structure, Knowledge Quality, and LLM Fitness

**Date:** 2026-04-07
**Vaults audited:** Arknode-AI-Obsidian-Vault (321 files), Arknode-Poly-Obsidian-Vault (181 files)
**Reference framework:** obsidian-wiki (Karpathy's LLM Wiki pattern)
**Recommendation:** Targeted improvements driven by identified problems, adopting obsidian-wiki tooling where it solves those problems

---

## Framing

This audit evaluates two production Obsidian vaults on their own terms: what's working, what's decaying, and what specific problems justify intervention. The obsidian-wiki framework is used as a reference point for its tooling and patterns, not as a compliance target. Both vaults already outperform typical obsidian-wiki deployments in several areas (cross-linking density, frontmatter coverage, TaskNotes schema richness). The goal is to identify concrete problems and recommend proportional fixes.

Each vault is independently maintained with its own TaskNotes schema, conventions, and Linear sync. Recommendations are per-vault; no cross-vault harmonization is proposed.

---

## 1. Three-Layer Assessment

The obsidian-wiki framework defines three layers: **Raw Sources** (immutable user documents), **Wiki** (LLM-maintained compiled knowledge with wikilinks and frontmatter), and **Schema** (the rules governing vault structure). This assessment evaluates each vault against this model to identify structural gaps, not to prescribe conformity.

### Arknode-AI (Trading Signal AI) — 321 files

| Layer | Status | Detail |
|-------|--------|--------|
| **Raw Sources** | Missing | No `_sources/` directory. Session logs (103 files) serve as de facto raw material but live alongside compiled docs in `Trading-Signal-AI/`. `_Attachments/` holds 28 research PNGs but no PDFs, papers, or conversation exports. |
| **Wiki** | Strong but unstructured | Architecture docs, research pages, and project overviews are high-quality compiled knowledge. Organized by project/function (`Infrastructure/`, `Trading-Signal-AI/Research/`) rather than by entity/concept. 1,639 wikilinks, zero orphans, 5.1 links/file average. |
| **Schema** | Implicit | `00-Home.md` and `00-Project-Overview.md` serve as MOCs. TaskNotes schema is well-defined via templates and frontmatter conventions. But no explicit vault schema doc — an LLM would need to explore directory structure to understand navigation patterns. |

### Arknode-Poly (Prediction Markets) — 181 files

| Layer | Status | Detail |
|-------|--------|--------|
| **Raw Sources** | Missing | Same pattern — no raw material staging. Session logs (24 files) are the closest equivalent. Empty `Strategies/` and `Models/` directories suggest planned-but-not-yet-populated knowledge areas. |
| **Wiki** | Good, growing | 44 knowledge pages with clear architecture/research/operations subdivision. 93.4% interlinked. Newer vault so less accumulated knowledge, but well-organized from the start. |
| **Schema** | Partially explicit | `00-Project-Management-Guide.md` documents TaskNotes schema. Architecture and session log indexes exist. But no vault-wide schema doc. `_Templates/` directory provides structural guidance. |

**Practical impact:** The missing schema layer is the most actionable gap. Both vaults are well-linked and well-maintained, but an LLM (or a new collaborator) arriving cold has to reverse-engineer the vault's organization from examples. A single `_meta/vault-schema.md` would fix this cheaply.

---

## 2. Knowledge Quality Audit

### Content Quality Assessment

Based on 16 pages read across both vaults. Sample selection: 2-3 pages per category (architecture, research, session logs, TaskNotes) per vault, targeting both high-quality and potentially weak areas. This sample is sufficient to identify patterns but not to make statistical claims about the full corpus.

| Category | AI Vault | Poly Vault | Assessment |
|----------|----------|------------|------------|
| **Architecture docs** | Excellent. `Database-Architecture.md` (110KB) is a definitive schema reference with migration changelog. `Source-Code-Architecture.md` documents 24 modules with entry points. | Good. `System-Topology.md`, `API-Reference.md`, `Database-Schema.md` cover the stack. Younger but well-structured. | Both produce **synthesized knowledge**, not raw notes. |
| **Research pages** | Strong. `Market-Condition-Analysis`, `Walk-Forward-Validation` contain methodology + results. Research index categorizes by status (Implemented/Analysis/Reference). | Strong. `Trading-Strategy.md` (150+ lines) details 5-stage pipeline with risk gates. `Calibration-Evaluation.md` covers Brier scoring. | Compiled and actionable. |
| **Session logs** | Raw work journals. Chronological, detailed, excellent for audit trail. But insights stay buried — e.g., Session-329's discovery that "spot-to-perp volume swap doesn't help" is only findable by reading that specific session. | Same pattern. Session-019's lesson "dashboards hide frozen pipelines" is documented in-session but not extracted. | **Primary knowledge decay risk.** See below. |
| **TaskNotes** | Excellent. `ArkSignal-092` shows exhaustive caller-map analysis. `ArkSignal-034` documents a definitive "TFT does NOT help" verdict with 4-way deployment matrices. | Good. `ArkPoly-116` documents root cause, workaround, and 6 diagnostic paths. Epics like `ArkPoly-122` have clear acceptance criteria. | Strongest knowledge artifact in both vaults. |

### The Core Problem: Session Log Knowledge Burial

This is the primary finding of the audit. Both vaults accumulate session logs as raw chronological work journals. Insights, decisions, and hard-won lessons are documented within sessions but never extracted into standalone, retrievable knowledge pages.

**AI vault impact (critical):** 103 session logs spanning ~6 months of work. Key findings buried in specific sessions include:
- TFT conclusively does not help (Session/ArkSignal-034, 4-way deployment matrices)
- Spot-to-perp volume swap provides no benefit (Session-329)
- Condition filters are the sole alpha source, +1.0 to +2.5 Sharpe lift (multiple sessions)
- Specific model architecture decisions and their evidence

An LLM or human trying to answer "what did we learn about TFT?" must read individual sessions sequentially. As sessions accumulate, this becomes increasingly impractical.

**Poly vault impact (moderate):** 24 sessions — still manageable to read through, but the same pattern will compound. Session-019's "dashboards hide frozen pipelines" lesson is already only findable by reading that session.

### Cross-Linking Density

| Metric | AI Vault | Poly Vault |
|--------|----------|------------|
| Total wikilinks | 1,639 | ~800 (est.) |
| Links per file | 5.1 avg | ~4.4 avg |
| Orphaned files | 0 | 12 (6.6%) — mostly recent stories created 2026-04-07, plus 2 operational guides |
| Session chaining | `prev:` field links each session to prior | Same pattern |

Both vaults are well above typical cross-linking thresholds. This is a strength to preserve.

### Tag Consistency

- **Within each vault:** High consistency for structural tags (`session-log`, `task`, subtypes). Moderate for domain tags.
- **AI vault issue:** `walk-forward` and `walkforward` spelling variant used interchangeably.
- **Neither vault has a tag taxonomy doc.** Tags are organic/emergent. This hasn't caused material problems yet but will compound as vaults grow.

---

## 3. LLM Consumption Fitness

### Navigation Assessment

| Criterion | AI Vault | Poly Vault |
|-----------|----------|------------|
| **Entry point** | `00-Home.md` links to 5 subsystems. Clear starting point. | `00-Home.md` links to project overview, research, sessions. Clear. |
| **Index coverage** | `00-Home.md` -> `00-Project-Overview.md` -> subdomain MOCs. Covers ~70% of vault. Infrastructure docs reachable but require 2-3 hops. | `00-Home.md` -> `00-Project-Overview.md` -> Architecture Index, Session Index, Research Index. Covers ~85%. |
| **Dead ends** | Session logs link backward (`prev:`) but not forward. TaskNotes link to related tasks but not to the knowledge pages they informed. | Same session log limitation. Orphaned operational docs unreachable from any index. |
| **Tiered retrieval** | Not possible. No `summary:` field in frontmatter. MOCs list links without descriptions. | Same limitation. |

### Key LLM Navigation Gaps

1. **No frontmatter summaries.** An LLM doing tiered retrieval (scan summaries first, open pages only when needed) must instead open every page body. This is the biggest retrieval cost multiplier.

2. **No machine-readable vault catalog.** The MOCs (`00-Home.md`) are human navigation hubs — link lists without content descriptions. A flat `index.md` listing every page with category, tags, and summary would enable cheap LLM scanning.

3. **Session logs are opaque to retrieval.** Titled `Session-NNN.md` with no content preview. Tags help (`tft`, `perp-data`) but frontmatter doesn't summarize what was discovered or decided.

4. **TaskNotes are the best LLM-readable artifact.** Rich frontmatter (`task-id`, `status`, `priority`, `component`) makes them filterable and scannable. An LLM can grep for `status: done` + `task-type: epic` to find all completed initiatives. This is better than obsidian-wiki's generic page template.

### NotebookLM Assessment

NotebookLM builds its own retrieval index from full document text. The current vault structure works reasonably well for it — architecture docs are self-contained, TaskNotes have rich metadata, and wikilinks create implicit relationships.

The primary improvement for NotebookLM would be **session log compilation** — replacing 103 raw journals with dense, compiled insight pages gives NotebookLM much higher signal-to-noise material to index. Frontmatter summaries and machine-readable indexes would not significantly improve NotebookLM (it reads full text anyway) but would benefit other LLM tools that use tiered retrieval.

---

## 4. obsidian-wiki Gap Analysis

### Features Evaluated Against Actual Problems

| Feature | Current Gap | Solves Which Problem? | Priority |
|---------|------------|----------------------|----------|
| **Session log compilation** (manual process, not an obsidian-wiki feature) | Insights buried in 103+ session logs, inaccessible to retrieval | **Knowledge decay** — the core problem | **High** |
| **`summary:` frontmatter field** | No summaries on any page. LLMs must read full bodies. | **LLM retrieval cost** — every query is expensive | **High** |
| **`wiki-lint`** | Never run. No broken link detection, orphan detection, frontmatter validation. | **Maintenance scalability** — catches drift before it compounds | **High** |
| **`_meta/vault-schema.md`** | No self-documenting schema. LLMs and humans must reverse-engineer vault structure. | **Onboarding and LLM navigation** — cheap to create, high value | **High** |
| **`index.md`** (machine-readable catalog) | No flat catalog. MOCs are human-oriented link lists. | **LLM retrieval cost** — enables cheap scanning before expensive reads | **Medium** |
| **`tag-taxonomy`** (`_meta/taxonomy.md`) | Tags organic/emergent. Minor spelling drift in AI vault. | **Maintenance scalability** — prevents tag entropy as vaults grow | **Medium** |
| **`cross-linker`** | Never run. Cross-linking is manual. | **Marginal** — both vaults already have excellent link density (5.1 and ~4.4/file) | **Low** |
| **`.manifest.json`** (delta tracking) | No source tracking. | **Future ingestion only** — no current pain point unless batch ingestion is planned | **Low** |
| **`_sources/` directory** | No raw material staging area. | **Future workflow only** — useful if you start ingesting external research, but adding a folder without an ingestion process is premature | **Low** |
| **`provenance` markers** | Not used. | **Not applicable** — vaults are first-party engineering notebooks, not multi-source research compilations | **None** |
| **`log.md`** (operation log) | Not present. | **Not applicable** — session logs serve this purpose with richer structure | **None** |

### Current Conventions Better Than obsidian-wiki Defaults

These are strengths to preserve:

1. **TaskNotes schema.** Each vault's `task-id`, `status`, `priority`, `task-type`, `component`, `related`/`depends-on` frontmatter is richer than obsidian-wiki's generic page template and directly integrated with Linear. Each vault maintains its own schema independently.

2. **Session log chaining.** The `prev:` / `session:` / `epic:` frontmatter creates a navigable timeline. obsidian-wiki's `journal/` category is simpler.

3. **MOC hierarchy.** `00-Home.md` -> `00-Project-Overview.md` -> domain indexes is clear human navigation. Keep both human MOCs and machine-readable `index.md`.

4. **Canvas diagrams.** The AI vault's 5 canvas files provide visual architecture navigation that obsidian-wiki doesn't address.

5. **Frontmatter coverage.** 99.1% (AI) and 96%+ (Poly) is higher than most obsidian-wiki vaults achieve even after running lint.

---

## 5. Restructuring Recommendation

### Problem-Driven Approach

The audit identified three concrete problems, in priority order:

1. **Knowledge decay in session logs** (High, AI vault critical) — hard-won insights are buried in chronological work journals and inaccessible to retrieval
2. **LLM retrieval inefficiency** (Medium) — no summaries or flat indexes, so every LLM query requires expensive full-page reads
3. **No automated maintenance** (Medium) — link validation, orphan detection, and tag consistency are manual

The recommendation addresses these three problems. Items that don't solve an identified problem are deferred.

### Phase 1: Session Log Knowledge Extraction (AI vault priority)

**What:** Mine the 103 AI vault session logs for high-value insights and compile them into standalone knowledge pages.

**Effort:** ~3 AI-assisted work sessions (define "session" as ~2-4 hours of focused work with Claude Code). This is the most labor-intensive step because it requires judgment about what's worth extracting.

**Deliverables:**
- Create `Trading-Signal-AI/Research/Compiled-Insights/` directory
- Extract 10-15 compiled insight pages from the highest-value buried knowledge:
  - TFT performance verdict (from ArkSignal-034 and related sessions)
  - Volume divergence analysis (Session-327, 329)
  - Condition filter alpha attribution (multiple sessions)
  - Spot-to-perp migration outcomes (Sessions 327-329)
  - Model architecture decisions and their evidence
  - Failure modes and post-mortems
- Each compiled page links back to source sessions for provenance
- Add compiled pages to the Research Index MOC

**For the Poly vault:** Not urgent at 24 sessions. Revisit when session count reaches ~50, or when specific buried insights become hard to find.

**Ongoing process:** After each major epic or every ~20 sessions (whichever comes first), do a compilation pass. This cadence should be adjusted based on how quickly insights become hard to find — there's no universal right number.

### Phase 2: LLM Navigation Improvements (both vaults)

**What:** Add frontmatter summaries, generate machine-readable index, write vault schema doc.

**Effort:** ~2 work sessions per vault. The `summary:` backfill can be largely automated (LLM reads each page, generates a <=200 char summary, writes to frontmatter) but needs human review of a sample batch before bulk application.

**Deliverables:**
- Add `summary:` field to frontmatter across all pages. Prioritize: architecture docs and research pages first (highest retrieval value), then TaskNotes, then session logs.
- Generate `index.md` at vault root — flat catalog of all pages with title, category, tags, and summary. Auto-generated from frontmatter. Kept alongside existing `00-Home.md` MOCs (human MOCs are better for humans; `index.md` is better for machines).
- Write `_meta/vault-schema.md` — explains folder structure, frontmatter conventions, TaskNotes schema, session log format, and navigation patterns. This is what an LLM or new collaborator reads first.

**Ongoing process:** `index.md` should be regenerated after adding new pages. Can be automated via a post-commit hook or periodic skill run.

### Phase 3: Automated Maintenance Tooling (both vaults)

**What:** Run obsidian-wiki's lint and tag tools. Set up for ongoing use.

**Effort:** ~1 work session per vault.

**Deliverables:**
- Run `wiki-lint` on both vaults. Fix any broken links, validate frontmatter fields, flag stale content.
- Create `_meta/taxonomy.md` in each vault — codify canonical tags for that vault. Fix the AI vault's `walk-forward`/`walkforward` drift.
- Run `cross-linker` once on both vaults — review proposed additions, accept the good ones. Marginal value given existing link density, but worth a single pass.

**Ongoing process:** Run `wiki-lint` periodically (monthly or before major milestones). Tag taxonomy is a living doc — update when new tag categories emerge.

### What's Deferred (and Why)

| Item | Why deferred |
|------|-------------|
| **`_sources/` directory** | Adding an empty folder doesn't solve a problem. Revisit when you have an actual ingestion workflow (e.g., batch-importing research papers or conversation exports). The directory is trivial to add later; the process design is the hard part. |
| **`.manifest.json`** | No current delta ingestion pain. Useful if/when `_sources/` and batch ingestion are adopted. |
| **Provenance markers** (`^[inferred]`, `^[ambiguous]`) | Not applicable to first-party engineering notebooks. |
| **`log.md`** | Session logs serve this purpose with richer structure (frontmatter, epic linking, session chaining). |
| **Cross-vault harmonization** | Each vault is independently maintained with its own TaskNotes schema and conventions. Different projects may legitimately need different optional fields. |

### What Stays Untouched

- TaskNotes folder structure, frontmatter schema, and Linear sync in each vault — zero changes
- Session log format and `prev:`/`epic:` chaining — preserved
- Existing folder hierarchy (`Infrastructure/`, `Trading-Signal-AI/`, `ArkNode-Poly/`) — no reorganization
- Canvas diagrams — kept as-is
- `00-Home.md` and MOC hierarchy — kept, with `index.md` added alongside
- File and folder names — no renames (existing wikilinks and external references depend on current names)

### Effort Summary

| Phase | AI Vault | Poly Vault | Notes |
|-------|----------|------------|-------|
| Phase 1 (session log extraction) | ~3 sessions (~6-12h) | Deferred | Judgment-intensive. AI vault is critical; Poly vault revisit at ~50 sessions. |
| Phase 2 (LLM navigation) | ~2 sessions (~4-8h) | ~2 sessions (~4-8h) | `summary:` backfill is automatable but needs review. |
| Phase 3 (maintenance tooling) | ~1 session (~2-4h) | ~1 session (~2-4h) | Mostly automated. Review lint/cross-linker output before committing. |
| **Total** | **~6 sessions (~12-24h)** | **~3 sessions (~6-12h)** | Phases are independent; can be done in any order. |
| **Ongoing maintenance** | ~1h/month (lint, index regen) + compilation pass every ~20 sessions | ~1h/month (lint, index regen) | Can be partially automated via skills. |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `summary:` backfill produces low-quality summaries | Medium | Review a 10-page sample batch, tune the prompt, then bulk-apply. Reject and redo if quality is poor. |
| `wiki-lint` / `cross-linker` makes unwanted edits | Low | Both tools propose changes for review. Never auto-commit. |
| Session log compilation creates redundancy with TaskNotes | Low | Compiled insight pages cover cross-cutting lessons (spanning multiple sessions/epics). TaskNotes cover individual work items. Different purpose, minimal overlap. |
| NotebookLM sync breaks on new files/directories | Low | New files (`index.md`, `_meta/`, compiled insights) should sync normally. Test with one vault first. |
| Linear-updater breaks | Very low | TaskNotes structure is untouched. Only new directories and files are added outside TaskNotes. |

---

## Appendix: Codex Review

This spec was reviewed by OpenAI Codex (gpt-5.4) in adversarial consult mode. Key feedback incorporated:

1. **Reframed as need-driven** — original version assumed obsidian-wiki compliance as the goal. Revised to identify concrete problems first, adopt framework tooling only where it solves those problems.
2. **Narrowed recommendation scope** — removed items that don't solve identified problems (`_sources/`, `.manifest.json`) from active phases; moved to deferred list with rationale.
3. **Fixed effort estimates** — defined "session" as ~2-4 hours, added hour ranges, included ongoing maintenance budget, split per-phase more realistically.
4. **Resolved priority inconsistencies** — `summary:` and vault schema elevated to High (they directly solve identified LLM navigation problems). `.manifest.json` and `_sources/` deprioritized (no current pain point).
5. **Dropped cross-vault harmonization** — each vault maintains its own independent TaskNotes schema.
6. **Acknowledged sample limitations** — explicit about what the 16-page sample can and cannot claim.
