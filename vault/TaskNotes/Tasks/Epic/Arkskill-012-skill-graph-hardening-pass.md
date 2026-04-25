---
title: "Arkskill-012: Skill-Graph Hardening Pass"
type: epic
tags:
  - epic
  - skill-design
  - lint
  - composition
summary: "Hardening pass for the ark-skills plugin: catalog drift lint, external skill registry, anchor-ref lint, exception-aware composition guardrails. Replaces the rejected wikilink-graph and tier-only-frontmatter proposals."
task-id: Arkskill-012
status: done
priority: medium
component: skills, wiki-lint
session: ""
source-sessions: []
source-tasks: []
created: 2026-04-24
last-updated: 2026-04-24
---

# Arkskill-012: Skill-Graph Hardening Pass

## Background

Two recently-popular "skill graph" patterns surfaced in early 2026:

- **Heinrich (Feb 2026)** — agent traverses a `[[wikilinks]]` graph at runtime; ~250 connected files in his arscontexta plugin.
- **Shiv (Apr 2026)** — empirical pushback: agents stop reliably traversing past 2–3 hops; tier abstraction explicitly into atoms / molecules / compounds with composition hardcoded into the skill.

A prior session proposed three changes for ark-skills: tier frontmatter labels, wikilink conversion in `chains/*.md`, and a depth cap. A `/codex` consult + challenge session against this repo (transcripts referenced in `Compiled-Insights/Skill-Graph-Hardening-Pass.md`) overruled most of that plan and surfaced concrete drift the original framing had missed. See the design doc for the full reasoning trail.

## Goal

Replace the rejected wikilink/tier-only proposal with a **composition-contract + lint** approach that targets the failure modes this repo is actually close to (broad/overlapping descriptions, oversized skills, catalog drift, brittle section-anchor refs, missing internal-vs-external classification) rather than failure modes from a deeper graph topology that doesn't apply at 20 skills.

## Stories

### Arkskill-012-S1 — Drift fix (LANDED)

**Status:** done in v1.21.5 (this commit/PR).

Three catalogs (`README.md`, `skills/AGENTS.md`, `CLAUDE.md`) disagreed on skill counts and were missing entries for `/ark-update` and `/wiki-handoff`. `/ark-health` check count was misreported in two places (19 in AGENTS.md, 20 in CLAUDE.md; correct is 22 per `ark-health/SKILL.md`). All three catalogs and the four version files (VERSION, plugin.json, marketplace.json, CHANGELOG) updated.

### Arkskill-012-S2 — External skills registry (LANDED in v1.22.0)

**Status:** done.

Added `skills/ark-workflow/references/external-skills.yaml` with 33 entries covering every external slash-command referenced in `chains/*.md`. Schema `{slash, family, condition_gate}` per epic. Codex consult caught two arg-bearing backtick spans (`/ask codex`, `/omc-plan --consensus`) that the initial single-token grep missed; registry stores bare commands only.

Mandatory before S3 — chain reachability lint cannot run without it.

### Arkskill-012-S3 — `/wiki-lint` extension: skill-graph audit mode (LANDED in v1.22.0)

**Status:** done — `skills/wiki-lint/scripts/skill_graph_audit.py` implements all six rules below; `skills/wiki-lint/SKILL.md` documents the mode.

Subcommand or default-on rules. Each is a soft warn unless noted:

1. **Catalog drift (HARD).** Filesystem ground truth = `find skills -maxdepth 2 -name SKILL.md`. Compare against parsed catalog rows in `skills/AGENTS.md`, `README.md`, `CLAUDE.md`. Exclude `shared/`. Error on count mismatch; warn on description-row drift.
2. **Section-anchor refs.** Find `references/<file>.md § Section X.Y` patterns in chains and SKILL.md files. Verify each cited section exists as a heading in the target file. The repo currently has at least one suspect ref (`omc-integration.md § Section 4.1`).
3. **Description shape — heuristic, not phrase-match.** Warn when a `description:` is unusually short, lacks trigger verbs, has high-overlap with another skill's description, or omits a negative-routing clause when the skill is genuinely ambiguous. Don't error on absent literal "Use when / Do NOT use" — three canonical atom skills don't have it.
4. **Active-body length budget.** Warn at 500 lines for any active SKILL.md (Anthropic's published guidance). Do not auto-trigger refactor; do not error.
5. **Chain reachability with internal/external classification.** Parse `skills/ark-workflow/chains/*.md` for backtick slash-commands; cross-check against `find skills -maxdepth 2 -name SKILL.md` (internal) and `external-skills.yaml` (external + condition gate). Warn on unclassified slash-commands. Note any chain step gated on a missing condition gate as informational.
6. **Compound-to-compound calls — soft warn, not block.** Flag instances; don't refuse them. The repo currently has live examples (`/ark-code-review`, `/codebase-maintenance`, conditional `/wiki-handoff`) and they're correct.

### Arkskill-012-S4 — Composition guardrails text in `skills/AGENTS.md` (LANDED in v1.22.0)

**Status:** done — added as `### Composition Guardrails` subsection under `## For AI Agents`. The "rejected v2 wording" was never actually in `skills/AGENTS.md` (it lived only in the epic + design doc as a proposal), so S4 was an addition rather than a replacement.

Replace the (rejected) "Compounds do not invoke other compounds" wording with the exception-aware version:

> Top-level orchestrators may sequence other orchestrating skills only through explicit chain steps, with conditions resolved before presentation. Do not rely on implicit nested routing. Avoid compound-to-compound calls unless the target has a bounded mode/argument and a documented handback point.

Drop the "molecules sequence atoms" tier sentence — `/ark-context-warmup` is a molecule-shaped prelude that runs as step 0 of every chain, so the sentence is technically false.

### Arkskill-012-S5 — Section-anchor refactor (NO WORK, v1.22.0)

**Status:** done (no-op). The S3 lint resolver (with dual-scheme heading match: `## Section N` and `### N.M`) found zero broken anchor refs across the repo. The design doc's flagged candidate (`omc-integration.md § Section 4.1`) resolves cleanly to the `### 4.1 ...` sub-heading at line 186. Codex's earlier "may already be silently broken" was based on a literal-string grep for "Section 4.1" that didn't account for the sub-numbering convention. No surgical cleanup needed.

### Arkskill-012-S6 — Out-of-scope (DO NOT DO)

Explicitly rejected so the next session doesn't reopen them:
- Do not convert `chains/*.md` prose to `[[wikilinks]]` for routing purposes — Anthropic's docs say the router consumes `description` only.
- Do not refactor `ark-workflow/SKILL.md` into `references/` to hit the 500-line cap. Codex enumerated load-bearing sections that cannot move (Project Discovery, Scenario Detection, Triage, Chain Lookup, Condition Resolution Dispatch, Condition Definitions). Moving them either breaks behavior or is metric-gaming.
- Do not add `tier:` frontmatter as a hard contract. Optional metadata feeding S3 lint heuristics is fine; phrase-matched tier classification is not.
- Do not put version-state lint inside `wiki-lint` — that belongs in a separate release lint or `/ark-update`. (VERSION/plugin.json/marketplace.json/CHANGELOG verified consistent at v1.21.4 by `/codex`.)

## Decision Trail

The design doc captures the consult + challenge transcripts, the Heinrich vs Shiv tradeoff, and why each rejected item was rejected. Read it before reopening any of the S6 items.

## Related Pages

- `[[Skill-Graph-Hardening-Pass]]` — design rationale and `/codex` transcripts
- `[[SKILL-Shrink-to-Core-Pattern]]` — prior `ark-workflow` length-budget thinking (v1.21.0 audit)
- `[[Plugin-Architecture-and-Context-Discovery]]` — context-discovery pattern that the lint must respect
- `[[Codex-Review-Non-Convergence]]` — why a `/codex` consult sometimes diverges from `/review`; relevant background for trusting the consult+challenge transcript
