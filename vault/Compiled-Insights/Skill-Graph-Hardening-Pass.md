---
title: "Skill-Graph Hardening Pass — Design Rationale"
type: compiled-insight
tags:
  - skill-design
  - lint
  - composition
  - codex
summary: "Why the ark-skills plugin is rejecting a wikilink-traversal/tier-frontmatter graph rebuild in favor of a smaller composition-contract + lint pass. Records the /codex consult+challenge transcripts that drove the v3 plan."
session: ""
source-sessions: []
source-tasks:
  - "[[Arkskill-012-skill-graph-hardening-pass]]"
created: 2026-04-24
last-updated: 2026-04-24
---

# Skill-Graph Hardening Pass — Design Rationale

## TL;DR

Two skill-graph design patterns (Heinrich's `[[wikilinks]]` traversal, Shiv's atom/molecule/compound tiers) circulated in early 2026. A prior session proposed adopting elements of both for ark-skills. A `/codex` consult + challenge session against this repo overruled the proposal and surfaced **catalog drift + brittle section-anchor refs + no internal/external skill classification + oversized active SKILL.md bodies** as the actual failure modes worth hardening. The v3 plan is a composition-contract + lint pass, not a graph rebuild. Tracked under [[Arkskill-012-skill-graph-hardening-pass]].

## Two Patterns Considered

### Heinrich (Feb 2026) — "Skill Graphs > SKILL.md"

A network of small markdown files connected by `[[wikilinks]]`. YAML frontmatter `description` fields act as the index. MOCs cluster sub-topics. Progressive disclosure: index → descriptions → links → sections → full content. Agent traverses the graph at runtime. Plugin: ~250 connected files.

### Shiv (Apr 2026) — "Skill Graphs 2.0"

Tested Heinrich's idea; reported empirical failure: "agents stop reliably calling skills past 2–3 hops" + circular dependencies. Fix: stop relying on agent traversal, tier the abstraction explicitly:

- **Atoms** — single-purpose primitives, near-deterministic, don't call other skills
- **Molecules** — 2–10 atoms with chaining hardcoded
- **Compounds** — orchestrate multiple molecules, human drives, ceiling ~8–10 molecules

The two posts disagree on **where intelligence lives**: Heinrich → agent traverses at runtime; Shiv → composition is hardcoded into the skill.

## Where ark-skills Already Sits

By inspection, ark-skills is ~70% structurally aligned to Shiv's tier model already, without naming it:

- **Compound layer** — `/ark-workflow` triages and outputs a numbered chain; **does not invoke downstream skills itself** (Step 7 of its SKILL.md says so verbatim). User or agent follows the chain.
- **Molecules** — `skills/ark-workflow/chains/*.md` (bugfix.md, greenfield.md, etc.) sequence step-by-step; explicit, not agent-judged.
- **Atoms** — `/wiki-status` (64 lines, reads `index.md`, no skill calls), `/tag-taxonomy`, `/cross-linker`.
- **MOC** — `skills/AGENTS.md` is structurally a 5-group table-of-contents.
- **Progressive disclosure** — `references/` subdirectories per skill (e.g., `skills/ark-health/references/check-implementations.md`).

The catalogs claimed 18 or 19 skills (depending on which file you read). Filesystem ground truth via `find skills -maxdepth 2 -name SKILL.md`: **20**.

## /codex Consult — Round 1 (Empirical Check)

Codex was consulted with the prompt: *"Heinrich vs Shiv on skill graphs — which approach better fits an 18-skill orchestration plugin where SKILL.md frontmatter is the only routing signal Claude Code reads?"* (Session ID `019dc31a-7bef-7e03-886c-1d26b5eb5f83`, recorded under `.context/codex-session-id`.)

Key findings cited by Codex:

1. **No published evidence** for agent-traversal of `[[wikilinks]]` or "fails past N hops." Both posts are anecdotal. Vendor docs (https://code.claude.com/docs/en/skills, https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) say the **opposite**: skill descriptions are loaded into context for selection; supporting files load on demand **after** the skill is invoked. The `description` field is the only routing signal.
2. **Existence of an external `skill-graph-mcp` pip package** that adds explicit `follow_links` / `get_skill_chain` tools is itself evidence raw markdown wikilinks aren't a runtime primitive. If they were, the package wouldn't need to exist.
3. **Shiv's tier model leaks at the boundaries** in this repo:
   - `ark-context-warmup` is not an atom — it queries NotebookLM/wiki/TaskNotes (fan-out, infra-shape molecule / "prelude"). Calling it atom because it's step 0 hides complexity.
   - `wiki-update` is not a hidden compound — shelling to `cli_promote.py` is implementation detail. Compound = agent coordinates separately-routable skills.
   - `ark-onboard` is compound — "compound" should mean orchestration scope, not "called from `/ark-workflow`."

Codex's verdict: do **C** (neither post's package). Build a smaller repo-specific hardening pass: tier labels only if lint consumes them; skip wikilink conversion; document composition rules as guardrails not ontology; build a real router/composition lint.

## /codex Challenge — Round 2 (Adversarial)

The "v2" plan derived from Round 1 was challenged adversarially in the same session. Codex tore down most of it:

1. **Catalog drift is in 3 places, not 2.** README.md (5 mention sites at lines 3, 132, 151, 176–177) and CLAUDE.md (Available Skills section + check count) were both stale on top of the AGENTS.md drift originally identified. README's "Verification Checks" block at line 176 contained a stale assertion command (`find skills -name SKILL.md | wc -l  # → 19`).
2. **`/ark-health` check count drift across 3 files.** AGENTS.md said "19-check"; CLAUDE.md said "20 checks"; README.md said "22 checks." Source of truth = `ark-health/SKILL.md` says 22 (and `ark-onboard/SKILL.md` confirms 22). AGENTS.md and CLAUDE.md were both wrong.
3. **The proposed `ark-workflow` length-budget refactor was wrong as stated.** Codex enumerated load-bearing sections (line numbers in `ark-workflow/SKILL.md`): Project Discovery (10), Scenario Detection (122), Triage (166), Chain Lookup (244), Condition Resolution Dispatch (251), Condition Definitions (505). These are required every invocation; moving them to `references/` either breaks behavior (the agent must follow a path at runtime, which we just established is unreliable) or is metric-gaming. Only batch-triage (already gated, line 239) and long troubleshooting (already referenced, line 588) are truly conditional.
4. **The proposed composition guardrail "compounds do not invoke other compounds" was false today.** Live counterexamples in this repo: `bugfix.md:32` and `greenfield.md:41` chains call `/ark-code-review` (which `ark-code-review/SKILL.md` describes as "Multi-agent code review with fan-out"); `hygiene.md:8` calls `/codebase-maintenance` (multi-step); `ark-workflow/SKILL.md:444` conditionally invokes `/wiki-handoff`. The guardrail breaks immediately.
5. **The proposed deferral of frontmatter metadata was infeasible.** Chain reachability lint needs internal-vs-external classification on day one. Plugin manifest doesn't carry external skills. `~/.claude/` is off-limits per the filesystem boundary established for `/codex` calls. Therefore: **a checked-in registry is mandatory**, not deferrable.
6. **The "must contain Use when / Do NOT use" description rule was invalid.** Three canonical atoms (`wiki-status`, `tag-taxonomy`, `cross-linker`) don't have those phrases — and they're correct skills. The rule should be a heuristic warn, not a phrase-match fail.
7. **Section-anchor refs are already brittle.** Chains repeatedly cite `references/omc-integration.md § Section 4.1`. Codex's grep didn't surface a `Section 4.1` heading in that file — only `Section 4`. May already be silently broken. Worth lint coverage.

## v3 Plan (Adopted)

This is the surviving plan after both Codex passes:

### Firm

1. **Drift fix first** — landed in v1.21.5: README.md (5 sites), AGENTS.md (3 sites), CLAUDE.md (3 sites), version-bump bookkeeping. Filesystem ground truth: `find skills -maxdepth 2 -name SKILL.md` returns 20.
2. **External skills registry** — checked-in YAML at `skills/ark-workflow/references/external-skills.yaml`. Lists gstack/OMC/superpowers/vendor-CLI skills with their condition gates. **Mandatory** for any reachability lint.
3. **`/wiki-lint` skill-graph rules:** catalog drift (filesystem vs three docs, hard error on count mismatch), section-anchor refs (verify cited headings exist), description-shape heuristics (soft warn), active-body length warn at 500, chain reachability against the registry, compound-to-compound calls as soft warn.
4. **Section-anchor cleanup** — fix any broken `§ Section X.Y` refs surfaced by the new lint rule.

### Soft

- Description-shape lint: warn-only, never error.
- Length budget: warn-only on active SKILL.md, do not force splitting.
- Composition guardrails: descriptive and exception-aware.

### Wrong (out of scope, do not reopen)

- **`[[wikilink]]` conversion in `chains/*.md` for routing purposes.** Vendor docs are clear: router consumes `description` only. Wikilinks would be documentation polish, not a routing improvement. Skipped.
- **`ark-workflow/SKILL.md` refactor to hit 500-line cap.** Treadmill on a number that wasn't measured to fail; load-bearing sections cannot move without behavior loss.
- **Tier frontmatter as a hard contract.** Optional metadata that feeds S3 lint heuristics is acceptable; phrase-matched tier classification is not.
- **Version-state lint inside `wiki-lint`.** Belongs in `/ark-update` or a separate release-lint script. State is currently consistent.

## Composition Guardrail (Final Wording)

For inclusion in `skills/AGENTS.md` (Arkskill-012-S4):

> Top-level orchestrators may sequence other orchestrating skills only through explicit chain steps, with conditions resolved before presentation. Do not rely on implicit nested routing. Avoid compound-to-compound calls unless the target has a bounded mode/argument and a documented handback point.

The "molecules sequence atoms" sentence is dropped — `/ark-context-warmup` is a molecule-shaped prelude that runs as step 0 of every chain, so the sentence is technically false.

## Failure Modes This Pass Targets

1. **Broad/overlapping descriptions** that confuse the router on similar-sounding intents.
2. **Catalog drift** between filesystem, `skills/AGENTS.md`, `README.md`, `CLAUDE.md`.
3. **Brittle section-anchor refs** in chain prose (`§ Section X.Y` style).
4. **Chain references to renamed/missing/external skills** with no machine-checkable signal of which is which.
5. **Oversized active SKILL.md bodies** that hurt context after compaction.

These are the empirically-near risks at 20 skills. The pass deliberately does **not** target Shiv's "fails past 2–3 hops" failure mode because it requires a deeper graph topology this plugin doesn't have.

## When to Revisit Skip List

- If skill count crosses ~30–40, re-evaluate the wikilink-traversal question against vendor doc updates.
- If a single compound starts orchestrating >8 molecules, revisit Shiv's "compound reliability ceiling" claim with measurement.
- If `description` field similarity becomes a routing problem (lint flags it repeatedly), consider description-shape contracts beyond heuristics.

## Related Pages

- `[[Arkskill-012-skill-graph-hardening-pass]]` — epic + stories
- `[[SKILL-Shrink-to-Core-Pattern]]` — v1.21.0 audit that already trimmed Layer 3 verbosity
- `[[Codex-Review-Non-Convergence]]` — why `/codex` and `/review` sometimes disagree
- `[[Plugin-Architecture-and-Context-Discovery]]` — the context-discovery pattern the lint must respect
- `[[Session-Capability-Plugin-Detection-Pattern]]` — relevant for the external-skills registry's condition-gate field
