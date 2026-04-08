# Obsidian Vault Audit: obsidian-wiki Three-Layer Assessment

**Date:** 2026-04-07
**Vaults audited:** Arknode-AI-Obsidian-Vault (321 files), Arknode-Poly-Obsidian-Vault (181 files)
**Framework:** obsidian-wiki (Karpathy's LLM Wiki pattern, 13 skills, three-layer architecture)
**Recommendation:** Option C — Partial Restructure

---

## 1. Three-Layer Assessment

The obsidian-wiki framework defines three layers: **Raw Sources** (immutable user documents), **Wiki** (LLM-maintained compiled knowledge with wikilinks and frontmatter), and **Schema** (the rules governing vault structure — categories, conventions, templates, and workflows).

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

**Key gap across both:** No self-documenting schema layer. An LLM arriving cold would need to read `00-Home.md`, guess at folder conventions, and infer the TaskNotes schema from examples rather than reading a spec.

---

## 2. Knowledge Quality Audit

### Content Quality Assessment

Based on 16 representative pages read across both vaults:

| Category | AI Vault | Poly Vault | Assessment |
|----------|----------|------------|------------|
| **Architecture docs** | Excellent. `Database-Architecture.md` (110KB) is a definitive schema reference with migration changelog. `Source-Code-Architecture.md` documents 24 modules with entry points. | Good. `System-Topology.md`, `API-Reference.md`, `Database-Schema.md` cover the stack. Younger but well-structured. | Both produce **synthesized knowledge**, not raw notes. Architecture docs are genuine reference material. |
| **Research pages** | Strong. `Market-Condition-Analysis`, `Walk-Forward-Validation` contain methodology + results. Research index categorizes by status (Implemented/Analysis/Reference). | Strong. `Trading-Strategy.md` (150+ lines) details 5-stage pipeline with risk gates. `Calibration-Evaluation.md` covers Brier scoring. | Compiled and actionable. |
| **Session logs** | Raw work journals. Chronological, detailed, excellent for audit trail. But insights stay buried — e.g., Session-329's discovery that "spot-to-perp volume swap doesn't help" is only findable by reading that specific session. | Same pattern. Session-019's lesson "dashboards hide frozen pipelines" is documented in-session but not extracted. | **Primary knowledge decay risk.** Signal-to-noise worsens as sessions accumulate. AI vault's 103 sessions are already hard to mine. |
| **TaskNotes** | Excellent. `ArkSignal-092` shows exhaustive caller-map analysis. `ArkSignal-034` documents a definitive "TFT does NOT help" verdict with 4-way deployment matrices. | Good. `ArkPoly-116` documents root cause, workaround, and 6 diagnostic paths. Epics like `ArkPoly-122` have clear acceptance criteria. | TaskNotes are **the strongest knowledge artifact** in both vaults — they capture decisions with evidence. |

### Cross-Linking Density

| Metric | AI Vault | Poly Vault |
|--------|----------|------------|
| Total wikilinks | 1,639 | ~800 (est.) |
| Links per file | 5.1 avg | ~4.4 avg |
| Orphaned files | 0 | 12 (6.6%) — mostly recent stories created 2026-04-07, plus 2 operational guides |
| Session chaining | `prev:` field links each session to prior | Same pattern |

### Tag Consistency

- **Shared conventions:** Both use `session-log`, `task` (with subtypes), infrastructure tags, domain-specific tags
- **Drift detected:** AI vault has `walk-forward` AND `walkforward` (spelling variant). Poly vault uses `ci-cd` and `eslint` tags the AI vault doesn't need. Neither has a governing taxonomy doc.
- **YAML format:** Both use array format (`tags: [a, b, c]`) — no style drift
- **TaskNotes field drift:** AI vault uses `related:` and `component:`. Poly vault uses `parent:` and `depends-on:`. Core schema fields (`task-id`, `status`, `priority`, `project`, `work-type`, `task-type`) are aligned, but optional fields have diverged.

### Session Log Compilation Verdict

Insights are being extracted into TaskNotes (good) and periodically into architecture docs (good), but there's no systematic "lessons learned" compilation step. The AI vault's 103 sessions contain years of institutional knowledge that's only accessible by reading individual sessions sequentially.

---

## 3. LLM Consumption Fitness

### Navigation Assessment

| Criterion | AI Vault | Poly Vault |
|-----------|----------|------------|
| **Entry point** | `00-Home.md` links to 5 subsystems. Clear starting point. | `00-Home.md` links to project overview, research, sessions. Clear. |
| **Index coverage** | `00-Home.md` -> `00-Project-Overview.md` -> subdomain MOCs (Research Index, Session Logs). Covers ~70% of vault. Infrastructure docs reachable but require 2-3 hops. | `00-Home.md` -> `00-Project-Overview.md` -> Architecture Index, Session Index, Research Index. Covers ~85% (smaller, better indexed). |
| **Dead ends** | Session logs link backward (`prev:`) but not forward. An LLM following Session-001 can't discover Session-002 without searching. TaskNotes link to related tasks but not to the knowledge pages they informed. | Same session log limitation. Orphaned operational docs (`Deployment-Guide.md`, `CT110-Setup.md`) unreachable from any index. |
| **Tiered retrieval possible?** | No. No `summary:` field in frontmatter. No machine-readable `index.md`. MOCs list links without describing what each link contains. | Same limitations. |

### Key LLM Navigation Gaps

1. **No frontmatter summaries.** obsidian-wiki expects every page to have `summary: "One or two sentences, <=200 chars"`. Neither vault has this. An LLM doing tiered retrieval (read summaries first, open pages only when needed) can't work — it must open every page, which is expensive.

2. **No vault-level `index.md`.** The MOCs (`00-Home.md`) are human-oriented navigation hubs, not machine-readable catalogs. obsidian-wiki's `index.md` lists every page with category, tags, and summary in a scannable format.

3. **Session logs are opaque to retrieval.** 103 AI sessions and 24 Poly sessions are titled `Session-NNN.md`. An LLM (or NotebookLM) has no way to know which session contains the TFT verdict, the volume divergence discovery, or the dashboard-hiding-frozen-pipelines lesson without reading each one. Tags help (`tft`, `perp-data`) but aren't searchable via wikilink traversal.

4. **TaskNotes are the best LLM-readable artifact.** Their frontmatter (`task-id`, `status`, `priority`, `component`) makes them filterable and scannable. An LLM can grep for `status: done` + `task-type: epic` to find all completed initiatives. This is better than what obsidian-wiki typically produces.

### NotebookLM Impact Assessment

NotebookLM ingests full documents and builds its own retrieval index. Current vault structure works reasonably well for it because architecture docs are self-contained and comprehensive, TaskNotes have rich frontmatter metadata, and wikilinks create implicit relationships NotebookLM can follow.

Restructuring would improve NotebookLM quality through:
- **Session log compilation** — instead of 103 raw logs, NotebookLM would retrieve compiled insight pages that are denser signal
- **Vault schema doc** — would give NotebookLM a "map" to understand how the vault is organized, improving its ability to contextualize answers

---

## 4. obsidian-wiki Gap Analysis

### Missing Features

| Feature | Status in Both Vaults | Impact | Priority |
|---------|----------------------|--------|----------|
| **`.manifest.json`** (delta tracking) | Missing. No record of what sources have been ingested or when. | Can't compute deltas — re-processes everything on each ingestion. | **High** |
| **`wiki-lint`** | Never run. No broken link detection, orphan detection, stale content flagging, or frontmatter validation. | AI vault: likely clean (zero orphans). Poly vault: 12 orphaned files, possible broken links from recent task creation. | **High** |
| **`tag-taxonomy`** (`_meta/taxonomy.md`) | Missing. Tags are organic/emergent. | AI vault has `walk-forward`/`walkforward` drift. Neither vault governs which tags are canonical. | **High** |
| **`_sources/` layer** | Missing. No dedicated area for unprocessed material. | Source material mixed with compiled docs or not stored at all. | **High** |
| **`summary:` frontmatter field** | Missing from all pages. | Blocks tiered retrieval. Every LLM query requires full page reads. | **Medium** |
| **`cross-linker`** | Never run. Cross-linking is manual. | Marginal gain given existing link density (5.1 and ~4.4/file), but useful for session logs specifically. | **Medium** |
| **`index.md`** (machine-readable catalog) | Missing. `00-Home.md` serves as human MOC but isn't a flat scannable index. | Blocks efficient LLM navigation. Can be auto-generated. | **Medium** |
| **`provenance` markers** | Not used. | Less critical for engineering notebooks than research wikis. Pages are primarily first-party work. | **Low** |
| **`log.md`** (operation log) | Missing. | Redundant — session logs already serve this purpose better. | **Low** |

### Current Conventions BETTER Than obsidian-wiki Defaults

These should be preserved regardless of restructuring choice:

1. **TaskNotes schema.** obsidian-wiki has no equivalent to the `task-id`, `status`, `priority`, `task-type`, `component`, `related`, `depends-on` frontmatter pattern. This is richer than obsidian-wiki's generic page template and directly integrated with Linear. **Do not replace with obsidian-wiki's page template.**

2. **Session log chaining.** The `prev:` / `session:` / `epic:` frontmatter creates a navigable timeline. obsidian-wiki's `journal/` category is simpler — just timestamped observations without the chain structure.

3. **MOC hierarchy.** `00-Home.md` -> `00-Project-Overview.md` -> domain indexes is a clear human navigation pattern. obsidian-wiki's flat `index.md` is better for machines but worse for humans. Keep both — add machine-readable `index.md` alongside existing MOCs.

4. **Canvas diagrams.** The AI vault's 5 canvas files (Architecture, Strategy Overview, Data Pipeline, Trading Pipeline) provide visual navigation that obsidian-wiki doesn't address.

5. **Frontmatter coverage.** 99.1% (AI) and 96%+ (Poly) frontmatter coverage is higher than most obsidian-wiki vaults achieve even after running lint.

---

## 5. Restructuring Recommendation

### Option C — Partial Restructure

Add a raw sources layer, compile session log insights, adopt obsidian-wiki maintenance tooling. Keep TaskNotes, folder hierarchy, and existing conventions intact.

### Phase 1: Adopt Tooling Without Changing Structure

**Effort:** ~1 session per vault

- Run `wiki-lint` on both vaults. Fix broken links, validate frontmatter fields.
- Create `_meta/taxonomy.md` in each vault — codify canonical tags, resolve spelling variants.
- Run `cross-linker` on both vaults — find unlinked mentions, especially in session logs.
- Initialize `.manifest.json` — register existing pages so future ingestion can compute deltas.
- Harmonize TaskNotes optional fields between vaults — decide on `related` vs `depends-on` vs `parent` vs `blockedBy` and document the canonical set.

### Phase 2: Targeted Structural Additions

**Effort:** ~2-3 sessions per vault (AI vault higher due to 103 session logs)

- **Add `_sources/` directory** in each vault for raw material (PDFs, external research, conversation exports, screenshots not yet processed). Establish the raw/compiled boundary.
- **Add `_meta/vault-schema.md`** — a self-documenting page that explains folder structure, frontmatter conventions, TaskNotes schema, session log format, and navigation patterns. This is the schema layer an LLM or new team member reads first.
- **Add `summary:` field to frontmatter** — backfill in bulk via a one-time skill run. Start with architecture docs and research pages (highest retrieval value), then TaskNotes, then session logs.
- **Generate `index.md`** at vault root — machine-readable flat catalog of all pages with category, tags, and summary. Auto-generated from frontmatter, kept alongside existing `00-Home.md` MOCs.
- **Compile session log insights** (AI vault priority):
  - Create `Trading-Signal-AI/Research/Compiled-Insights/` for extracted lessons.
  - Target highest-value buried knowledge: TFT verdict, volume divergence finding, condition filter being the sole alpha source, spot-to-perp migration outcome.
  - Each compiled page links back to source sessions for provenance.
  - Establish convention: every 10-15 sessions, run a compilation pass.

### What Stays Untouched

- TaskNotes folder structure, frontmatter schema, and Linear sync — zero changes
- Session log format and `prev:`/`epic:` chaining — preserved
- Existing folder hierarchy (`Infrastructure/`, `Trading-Signal-AI/`, `ArkNode-Poly/`) — no reorganization into `concepts/`/`entities/`
- Canvas diagrams — kept as-is
- `00-Home.md` and MOC hierarchy — kept, with `index.md` added alongside

### Effort Estimate

| Phase | AI Vault | Poly Vault |
|-------|----------|------------|
| Phase 1 (tooling) | ~1 session | ~1 session |
| Phase 2 (structural) | ~3 sessions (103 session logs to mine) | ~2 sessions (24 sessions, smaller vault) |
| **Total** | **~4 sessions** | **~3 sessions** |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `wiki-lint` / `cross-linker` makes unwanted edits | Low | Review diffs before committing. Both tools are read-then-propose, not auto-apply. |
| `summary:` backfill produces low-quality summaries | Medium | Review a sample batch, tune prompt, then bulk-apply. |
| Session log compilation creates redundancy | Low | Compiled pages link to source sessions — they're indexes, not copies. |
| NotebookLM sync breaks on new files | Low | `.notebooklm/` config may need path updates for `_sources/` and `_meta/`. Test with one vault first. |
| Linear-updater breaks | Very low | TaskNotes structure is untouched. Only new directories and new files are added. |

### What NOT To Do

- Don't rename existing files or folders — breaks wikilinks and external references
- Don't adopt obsidian-wiki's `projects/` pattern — existing project separation already works
- Don't add `provenance` markers — vaults are first-party engineering notebooks, not multi-source research compilations
- Don't create `log.md` — session logs already serve this purpose better
