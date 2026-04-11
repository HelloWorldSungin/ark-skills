# Ark Workflow Split — Design Spec

**Date:** 2026-04-10
**Scope:** Refactor `skills/ark-workflow/SKILL.md` from a single 858-line file into a progressive-disclosure layout: main router + 7 per-scenario chain files + 4 reference files.
**Target release:** 1.7.0
**Prior state:** 1.6.0 (`f690ebf`) — ark-workflow v2 rewrite addressing 22 gaps
**Feature branch:** `refactor/ark-workflow-split`
**Session log:** `vault/Session-Logs/S004-Ark-Workflow-Split.md`

## Problem

After the v2 rewrite in 1.6.0 ([[S003-Ark-Workflow-v2-Rewrite]]), `skills/ark-workflow/SKILL.md` grew from 391 → 858 lines to address 22 identified gaps (12 initial + 10 from Codex review). The rewrite was correct, but the entire file now loads into context on every invocation — even for a typical single-item triage that only needs the router, one chain, and the condition-resolution rules.

Token efficiency matters because this skill is the **entry point for all non-trivial work** across Ark projects. Every `/ark-workflow` invocation pays the full 858-line cost regardless of whether the triage is a 5-item batch or a simple Ship of a dependency bump. The common-path tax compounds across every triage in every session in every project.

Breaking down the current file by actual usage:

| Content class | Lines | Actual usage |
|---|---|---|
| Core router (Project Discovery, Scenario Detection, Triage, Workflow algorithm, Condition Resolution) | ~258 | every triage |
| Batch Triage | 87 | only when multi-item prompt detected |
| Continuity protocols | 121 | mostly pay-per-use (batch mode, cross-session resume, handoff markers, stale detection, compaction recovery) — only ~18 lines are common path |
| Chain variants (19 across 7 scenarios) | 298 | only one variant matches any given triage |
| Routing Rules Template | 45 | never runtime — it is a copy-paste block for project CLAUDE.md files |
| Session Handoff + When Things Go Wrong + Re-triage details + Condition Resolution example | 64 | only consulted on mid-flight events |
| Structural overhead (headers, separators, blank lines) | ~81 | — |
| **Total** | **858** | |

Only ~31% of the current file's bytes are truly common path. The rest is load-on-demand content loaded unconditionally.

## Goals

1. **Reduce per-invocation context load by ≥50% on the single-item common path.** This is the forcing function. Every design decision is judged against it.
2. **Preserve behavioral parity.** All 22 v2 gaps stay addressed. All 19 chain variants stay **text-verbatim** in their step content (see Chain file format § Content preservation rules for the exhaustive list of permitted structural changes). All 7 scenarios stay. Security routing split, Hygiene Audit-Only, `/cso` dedup rule, Batch Triage, Continuity protocols, scenario-shift re-triage, and cross-session resume all stay intact.
3. **Keep main `SKILL.md` ≤ 400 lines** (hard cap with a documented-deviation exit). Target ~285 lines.
4. **Use idiomatic progressive disclosure** — the standard Claude Code skill pattern of main router + sub-files, matching how the superpowers skills are organized.

## Non-goals

- **Do not "improve" the triage logic while refactoring.** If a v2 bug or gap is surfaced during the split, file it separately; do not fix inline.
- **Do not reformat unrelated whitespace.** The diff stays focused.
- **Do not add format contracts for chain files.** Per user direction: "if a chain file is 20 lines, it can stay 20 lines — you don't need a chain-format spec."
- **Do not create a test harness.** The skill is markdown; verification is by grep + mental walkthrough of smoke tests, not by programmatic execution.
- **Do not change the public contract.** Skill name (`ark-workflow`), invocation path, and description frontmatter all stay identical.

## Target architecture

### File layout

```
skills/ark-workflow/
├── SKILL.md                           # ~285 lines — router (common path)
├── chains/
│   ├── greenfield.md                  # ~68 lines — L/M/H
│   ├── bugfix.md                      # ~48 lines — L/M/H
│   ├── ship.md                        # ~14 lines — standalone, no weight class
│   ├── knowledge-capture.md           # ~24 lines — Light/Full
│   ├── hygiene.md                     # ~52 lines — Audit-Only/L/M/H + dedup rule
│   ├── migration.md                   # ~56 lines — L/M/H
│   └── performance.md                 # ~56 lines — L/M/H
└── references/
    ├── batch-triage.md                # ~95 lines — algorithm + example
    ├── continuity.md                  # ~100 lines — batch mode, resume, handoff, stale, compaction, archive
    ├── troubleshooting.md             # ~50 lines — Re-triage + Session Handoff summary + When Things Go Wrong
    └── routing-template.md            # ~45 lines — CLAUDE.md copy-paste block
```

### Line budget

| File | Lines | Derivation |
|---|---|---|
| Main `SKILL.md` | ~285 | Frontmatter (4) + header+purpose (5) + Project Discovery (48) + Scenario Detection (42) + Triage (63) + Workflow Steps (42, which already includes the ~18-line slim Step 6.5 inline block) + Condition Resolution minus example (31) + When Things Change new (12) + Routing Rules pointer (3) + File Map (10) + structural whitespace (~25). Sum: 285. |
| `chains/` total | ~318 | Sum of 7 scenario chain files, avg 45 lines/scenario |
| `references/` total | ~290 | batch-triage (95) + continuity (100) + troubleshooting (50) + routing-template (45) |
| **Grand total** | **~893** | +35 lines vs current 858 (structural file headers + 1-line pointer glue) |

### Common-path cost comparison

| Mode | Current (1.6.0) | After split (1.7.0) | Reduction |
|---|---|---|---|
| Single-item triage, avg scenario | 858 | main (285) + avg chain (45) = **330** | **61.5%** |
| Single-item triage, Ship (smallest) | 858 | main (285) + ship (14) = **299** | **65.2%** |
| Single-item triage, Greenfield (largest) | 858 | main (285) + greenfield (68) = **353** | **58.9%** |
| Batch triage, 5 items / 3 scenarios | 858 | main (285) + batch-triage (95) + 3 chains (~135) = **515** | **40.0%** |
| Cross-session resume | 858 | main (285) + continuity (100) + 1 chain (45) = **430** | **49.9%** |

All single-item paths clear the 50% target with 8-15% headroom. Batch triage sits below 50% by necessity (multi-Read), but it is the minority of real usage — the weighted average across typical triages stays ≥ 55%.

### Disk footprint trade

Total repo line count rises by ~35 lines (858 → ~893). This is **intentional**: we are trading ~35 lines of on-disk pointer/header overhead for ~530 lines of context-load savings on every common-path invocation. Cold file count goes from 1 → 12. The CHANGELOG calls this out explicitly.

## Main `SKILL.md` contents

### Section-by-section layout

| # | Section | Lines | Change from current (L# refs to 1.6.0 SKILL.md) |
|---|---|---|---|
| 1 | Frontmatter | 4 | Unchanged |
| 2 | `# Ark Workflow` + 1-line purpose | 5 | Unchanged |
| 3 | `## Project Discovery` | 48 | Verbatim from L10-57 |
| 4 | `## Scenario Detection` | 42 | Verbatim from L58-99 |
| 5 | `## Triage` | 63 | Verbatim from L100-162 |
| 6 | `## Workflow` (Steps 1-7 incl. Step 6.5) | ~42 | Steps 1/3/5/6/7 unchanged. **Step 2 gets +1 line** pointing at `references/batch-triage.md` on multi-item detection. **Step 4 rewritten** to point at `chains/{scenario}.md`. **Step 6.5 slimmed** to ~18 inline lines. |
| 7 | `## Condition Resolution` | ~31 | Trigger lists verbatim from L719-745. **Example Resolved Output block (L746-759) removed entirely** — 14 lines dropped from total. |
| 8 | `## When Things Change` (new, replaces 3 sections) | ~12 | Collapses Session Handoff (L761-774), When Things Go Wrong (L776-789), Re-triage (L791-812) into one dispatch block with 1-line pointers each. |
| 9 | `## Routing Rules Template` pointer | 3 | 1-line pointer replacing the 45-line copy-paste block |
| 10 | `## File Map` (new, safety net) | ~10 | Single-source-of-truth index of `chains/` and `references/` files with 1-line purpose each. Lets the agent orient if context compresses mid-chain. |
| — | Blank lines + separators | ~25 | — |
| **TOTAL** | | **~285** | |

### Key modifications in detail

#### Step 2 — Detect Scenario

Insert one additional line after the existing multi-scenario resolution paragraph:

> If the prompt describes multiple distinct tasks (see Batch Triage trigger), read `references/batch-triage.md` and follow that algorithm instead of Steps 3-6.

Current L163-249 Batch Triage section is **deleted** from main. The 1-line trigger preserves the entry point; the 95-line algorithm lives in `references/batch-triage.md`.

#### Step 4 — Look Up Skill Chain

Rewrite from:

> Find the matching chain in the Skill Chains section below using scenario + weight class. If security hardening triggered mandatory early `/cso`, apply the dedup rule (remove the later conditional `/cso` from the chain).

To:

> Read `chains/{scenario}.md` (e.g., `chains/bugfix.md`). Each chain file contains sections for the applicable weight variants — Light/Medium/Heavy, or Light/Full for Knowledge Capture, or Audit-Only/Light/Medium/Heavy for Hygiene. Select the section matching your triaged weight class.
>
> **Filename mapping:** `greenfield.md`, `bugfix.md`, `ship.md` (standalone — no weight class), `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`.
>
> If security hardening triggered mandatory early `/cso`, apply the dedup rule documented at the bottom of `chains/hygiene.md`.

Current L410-712 Skill Chains section is **deleted** from main: L410 is the `## Skill Chains` header, L414 is the first scenario sub-header (`### Greenfield Feature`), and L712 is the Performance Heavy closing separator. The 19 chain variants span L414-711 (298 lines of variant content).

#### Step 6.5 — Activate Continuity (slimmed to ~18 inline lines)

Replaces current L401-406 (the existing Step 6.5 bullet list in Workflow Steps) and pulls in a slimmed subset of the Continuity frontmatter schema currently at L264-291 (inside the `## Continuity` section). The result is a self-contained Step 6.5 that the agent can execute without a second Read:

```markdown
### Step 6.5: Activate Continuity
- Create TodoWrite tasks for each step in the resolved chain
- Write `.ark-workflow/current-chain.md` at project root with this frontmatter:

  ---
  scenario: {scenario}
  weight: {weight}
  batch: false
  created: {ISO-8601 timestamp}
  handoff_marker: null
  handoff_instructions: null
  ---
  # Current Chain: {scenario}-{weight}
  ## Steps
  [numbered checklist of chain steps, each as `- [ ]`]
  ## Notes

- Add `.ark-workflow/` to `.gitignore` if not already present
- After each step: check off the step in the file (`[ ]` → `[x]`), update the TodoWrite task to `completed`, announce `Next: [skill] — [purpose]`, mark next task `in_progress`
- For batch-mode chain file format, cross-session resume, `handoff_marker` semantics, stale-chain detection, and compaction recovery: see `references/continuity.md`
```

This is literally enough for the agent to execute Step 6.5 on every triage without a second Read. All pay-per-use continuity protocols live in `references/continuity.md` (see References section below).

#### `## When Things Change` — new 12-line dispatch section

Replaces current L761-812 (Session Handoff, When Things Go Wrong, Re-triage — ~50 lines) with:

```markdown
## When Things Change

- **Mid-flight re-triage** (weight escalation or scenario shift): stop at the current step, reclassify using the Triage section above, pick up the remaining phases from the new class. For scenario-shift pivot examples, see `references/troubleshooting.md`.
- **Design-phase session handoffs**: chain files specify inline `handoff_marker` values where applicable. For per-scenario handoff points and guidance on when to break sessions mid-implementation, see `references/troubleshooting.md`.
- **Step failure or unexpected state**: see `references/troubleshooting.md` for per-failure guidance (failed QA, failed deploy, review disagreement, flaky tests, spec invalidation, canary failure, vault tooling failure, hygiene reveals bugs, migration breaks tests, batch item blocks others).
```

#### `## File Map` appendix — new ~10-line safety net

```markdown
## File Map

**Chain files (`chains/`)** — loaded once per triage after scenario detection:
- `greenfield.md`, `bugfix.md`, `ship.md`, `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`

**References (`references/`)** — loaded only when their trigger fires:
- `batch-triage.md` — multi-item algorithm (trigger: Step 2 multi-item detection)
- `continuity.md` — batch/resume/handoff/stale/compaction protocols (trigger: pay-per-use branches of Step 6.5)
- `troubleshooting.md` — re-triage, handoff details, failure recovery (trigger: mid-flight events)
- `routing-template.md` — CLAUDE.md copy-paste block (trigger: never runtime)
```

This is a safety net: if the agent's context compresses mid-chain and it loses its place, it can scroll to File Map and orient.

## Chain file format

**Design principle: no format spec.** Chain files are plain markdown using the exact same conventions as the current `## Skill Chains` section. No frontmatter, no schema, no parser contract. Per user direction: "if a chain file is 20 lines, it can stay 20 lines — you don't need a chain-format spec."

### Generic template

```markdown
# {Scenario Name}

{Optional one-line scenario description pulled from current ### header prose,
 if it adds clarity. Ship gets this; Bugfix probably does not need it.}

## {Weight Class A}

1. step
2. step
...

## {Weight Class B}

...
```

### Content preservation rules

Each chain file's **step content** (the numbered lists, inline conditions, handoff markers, sub-labels) is copied **text-verbatim** from current `SKILL.md` L414-711 — no paraphrasing, no "improvements", no rewording. Only structural wrapping around that content changes. The exhaustive list of permitted changes:

1. Demote `### {Scenario}` → `# {Scenario}` (H1 in the chain file)
2. Demote `**Light:**` / `**Medium:**` / `**Heavy:**` bold labels → `## Light` / `## Medium` / `## Heavy` H2 headers. This is a **required style change for greppability and weight-class section selection**. It preserves exact text content that follows.
3. Drop the `---` separators between weight variants — the H2 headers take over that role.
4. Keep all `*Session 1 — Design:*` / `*Session 2 — Implementation:*` / `*Document:*` sub-labels exactly as-is (these are mid-variant sub-headers, not weight classes, and remain italic).
5. Keep all inline `(set handoff_marker: after-step-N)` markers exactly where they appear in the current chain steps.

### Worked example: `chains/hygiene.md` (most complex — shows every pattern)

```markdown
# Codebase Hygiene

## Audit-Only

*For "audit", "review", "assess" requests with no remediation expected.*

1. `/codebase-maintenance` — audit (or `/cso` if security audit)
2. Present findings report to the user
3. `/wiki-update` (if vault — to record findings)
4. **STOP** — do not implement, do not ship. Ask user: "Findings above. Do you want to create tickets via `/ark-tasknotes`, or proceed with fixes (I'll re-triage as Hygiene Light/Medium/Heavy)?"

## Light

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. Implement cleanup
4. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

## Medium

[verbatim from current SKILL.md L580-590]

## Heavy

[verbatim from current SKILL.md L592-604, including the escape hatch at step 3]

## Dedup rule

If security hardening triggers mandatory early `/cso` (before the chain starts), skip the conditional `/cso` inside the chain. `/cso` runs exactly once per chain execution.
```

### Worked example: `chains/ship.md` (minimal — no weight classes)

```markdown
# Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)
```

13 lines. That is the floor — do not inflate it with a format-spec header or metadata.

### Handoff markers and dedup rule placement

- **Inline `handoff_marker` values** stay inside the step that sets them, text-verbatim from the current SKILL.md. Only four variants have explicit `handoff_marker` values: Greenfield Medium step 3 (`after-step-3`), Greenfield Heavy step 5 (`after-step-5`), Migration Heavy step 4 (`after-step-4`), Performance Heavy step 5 (`after-step-5`). These live inline in `chains/greenfield.md`, `chains/migration.md`, and `chains/performance.md`. No separate `## Handoff` sub-section in any chain file.
- **Prose pivot escape hatches** — the existing Heavy Bugfix step 2 ("If investigation reveals architectural redesign is needed...") and Heavy Hygiene step 3 ("If audit + investigation reveals systemic issues requiring rewrite...") — stay inline as prose text-verbatim. They are **not** `handoff_marker` assignments; the current SKILL.md does not use `handoff_marker` for these cases, and the refactor must not introduce it.
- **Per-scenario handoff point summary** (the bullet list from current SKILL.md L761-774 that cross-references these inline locations) moves to `references/troubleshooting.md#session-handoff` — see References section below.
- **Dedup rule** lives at the bottom of `chains/hygiene.md` only (shown above). Main `SKILL.md` Step 4 references it by pointing at the file.

### What chain files do NOT contain

- No frontmatter
- No TOC (H2 headers are the TOC)
- No cross-references to other chain files
- No per-file version stamp (the skill's `VERSION` file is authoritative)
- No line-number hints for main (main already knows the filenames)

## `references/` file contents

### 1. `references/batch-triage.md` (~95 lines)

**Trigger:** main Workflow Step 2 detects multiple distinct tasks in the user's prompt.

**Contents:** verbatim from current `SKILL.md` L163-249 (the entire `## Batch Triage` section). Only change: demote top-level `## Batch Triage` → `# Batch Triage` as the file's H1.

```markdown
# Batch Triage

{trigger paragraph from L165-172}

## Algorithm
### Step 0 — Root cause consolidation
### Step 1 — Per-item scenario + weight classification
### Step 2 — Dependency detection (heuristic)
### Step 3 — Grouping
### Step 4 — Per-group chains

## Example Output

{table + execution plan example from L222-249}
```

### 2. `references/continuity.md` (~100 lines)

**Triggers** (any one of these):
- Multi-item prompt → batch-mode chain file format needed
- Session start finds existing `.ark-workflow/current-chain.md`
- Chain step sets `handoff_marker`
- Chain file older than 7 days detected
- Context compaction suspected mid-chain
- Chain completion → archive rule

**Contents:** verbatim from current `SKILL.md` L251-371 **minus** the ~18 lines that stay inline in main Step 6.5 (frontmatter template + basic after-each-step protocol). Specifically:
- **Drop** current L259-299 (basic state file format + basic per-step protocol — these are now inline in main Step 6.5)
- **Keep** current L309-371 (batch-mode format, cross-session continuity, rehydrate, handoff_marker, stale detection, context recovery)
- **Add** a 2-line archive rule at the bottom

```markdown
# Continuity — Advanced Protocols

This file holds pay-per-use continuity protocols. The minimum Step 6.5 inline
protocol (frontmatter template + basic after-each-step update) lives in main
`SKILL.md`.

## Batch Triage Chain File Format
{current L309-337 — batch chain file example with groups}

## Cross-Session Continuity
### Session start check
### Rehydrate TodoWrite tasks
{current L339-349}

## Handoff Markers
### Setting handoff_marker
### Resuming on a marked chain
{current L349-358}

## Stale Chain Detection
{current L360-364}

## Context Recovery After Compaction
{current L366-371}

## Archive on Completion
On chain completion, move `.ark-workflow/current-chain.md` →
`.ark-workflow/archive/YYYY-MM-DD-{scenario}.md`. Never delete — archives are
workflow history. This rule also appears in abbreviated form inline in main Step 6.5.
```

### 3. `references/troubleshooting.md` (~50 lines)

**Triggers:**
- Task changes class mid-flight (weight escalation or scenario shift)
- A chain step fails (any of 10 failure modes)
- Design phase ending — need per-scenario session handoff guidance

**Contents:** consolidates three currently separate sections (Re-triage L791-812, Session Handoff L761-774, When Things Go Wrong L776-789) into one dispatch file. **The Condition Resolution "Example Resolved Output" block (current L746-759) is dropped entirely — not moved here.**

```markdown
# Troubleshooting — When Things Change or Break

## Re-triage
### Weight escalation
{current L793-799 verbatim}
### Scenario shift
{current L801-812 verbatim — pivot examples: Bugfix→Greenfield, Performance→Migration, Hygiene→Bugfix}

## Session Handoff — Per-Scenario Guidance
{current L761-774 verbatim — per-Heavy-scenario handoff points, plus "don't rely on tool-call counts" reminder.}

## When Things Go Wrong
{current L776-789 verbatim — all 10 failure-recovery entries}
```

**Pure consolidation, no additions.** The troubleshooting.md body content is the text-verbatim concatenation of three baseline ranges (L761-774 + L776-789 + L791-812) with no added prose, cross-references, or commentary. The Phase 2 parity diff (Verification § 4) checks this against the baseline concatenation and aborts on any drift. The "Bugfix/Hygiene do not use handoff_marker" invariant that previously appeared as an added paragraph here has been removed — the invariant is documented in this spec (Chain file format § Handoff markers) and enforced by the Gap 5 verification grep, not by inline runtime prose.

### 4. `references/routing-template.md` (~45 lines)

**Trigger:** never runtime. Only read when a human is copying the block into a project's CLAUDE.md (manually or via `/ark-onboard`).

**Contents:** verbatim from current `SKILL.md` L814-858 (fenced copy-paste block + closing note).

```markdown
# Routing Rules Template

Copy the block below into a project's CLAUDE.md to auto-trigger /ark-workflow
and enable cross-session chain resume in that project.

---

{current 5-backtick fenced block, verbatim}

---

To add routing to a new project, copy the block above into the project's CLAUDE.md.
The /ark-workflow skill is already available globally via the ark-skills plugin.
```

### Cross-reference DAG

The new layout forms a strict tree fanning out from main with no cycles and no inter-reference edges:

```
main SKILL.md
 ├── chains/{greenfield,bugfix,ship,knowledge-capture,hygiene,migration,performance}.md   (Step 4)
 ├── references/batch-triage.md           (Step 2)
 ├── references/continuity.md             (Step 6.5)
 ├── references/troubleshooting.md        (When Things Change ×3)
 └── references/routing-template.md       (Routing Rules Template section pointer)
```

**Invariants:**
- Main `SKILL.md` is the only file that points into `chains/`
- Main `SKILL.md` points into all 4 reference files (5 specific pointer sites total)
- Chain files never point to other chain files or `references/`
- **No inter-reference edges:** `references/` files are independent of each other. Earlier drafts contemplated a `troubleshooting.md → continuity.md` cross-link for handoff_marker mechanics, but that would require either an addition to the pure-consolidation of troubleshooting.md (breaking the parity diff) or a normalization rule in the reconstruction script (adding complexity without commensurate benefit). The agent can reach `continuity.md` from main's File Map or Step 6.5 pointer; it does not need a reference-to-reference shortcut.
- No reference file or chain file points back to main

This strict tree makes the edit mental model trivial: editing a chain file cannot break anything outside that file; editing main requires preserving 5 pointer sites + 7 chain filenames; editing a reference file cannot break main, chains, or other references.

### Dropped content

**Condition Resolution "Example Resolved Output" block (current L746-759, 14 lines):** deleted entirely, not migrated anywhere. Rationale: it is illustrative, not load-bearing. The "Skipping X — no Y detected" format is self-evident from the trigger lists in Condition Resolution. Dropping it saves 14 lines of total disk footprint with zero behavioral cost.

## Token budget

**Measurement method:** line count (`wc -l`). Word count (`wc -w`) reported alongside for sanity check in the CHANGELOG.

**Rationale for line-count method:**
- No tokenizer dependency (no tiktoken in plan, no cl100k_base install)
- Reproducible across sessions and platforms
- Correlates tightly with token cost for prose-heavy markdown (approx 8-12 tokens/line)
- Matches the measurement method used in the v2 spec

**Common-path definition:** the set of files loaded during a single-item, single-scenario, non-batch, non-resume, non-security-hardening triage:
- Main `SKILL.md` (always)
- Exactly one `chains/{scenario}.md` file (loaded in Step 4 after scenario detection)

Not common path: `references/batch-triage.md` (only multi-item), `references/continuity.md` (only pay-per-use branches), `references/troubleshooting.md` (only mid-flight events), `references/routing-template.md` (never runtime).

**Baseline** (captured before Phase 1):
- Current `SKILL.md`: **858 lines**, measured at commit `f690ebf` (1.6.0)

**Targets:**
- Main `SKILL.md` ≤ **400 lines** (hard cap, documented-deviation exit)
- Common-path total (main + one chain file) ≤ **386 lines** (45% of 858 — floor from task spec)
- Stretch target: ≥ **60% reduction** on common path (≤ 343 lines)

**Projected (pre-implementation):**
- Main `SKILL.md`: ~285 lines
- Avg common-path total: ~330 lines
- Projected reduction: **61.5%**

**Abort conditions** (any of these halts the release, spec gets updated before retrying):
- Main `SKILL.md` > 400 lines
- Common-path average > 386 lines
- Any behavioral-parity gap check FAILs
- Any of the post-extraction parity diffs (Section 4) produces a non-empty diff after normalization
- Any smoke test (Section 5) produces divergent triage output vs current `SKILL.md`

## Verification plan

### 1. Baseline capture (before Phase 1 begins)

```bash
# Line counts
wc -l skills/ark-workflow/SKILL.md                  # expect 858
wc -w skills/ark-workflow/SKILL.md                  # record word count

# Preserve a verbatim pre-refactor copy for byte-level diffs during phases
cp skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md

# Grep-count baselines (records for post-refactor comparison)
grep -c "/test-driven-development" skills/ark-workflow/SKILL.md   # expect 12
grep -c "/TDD\b" skills/ark-workflow/SKILL.md                      # expect 0
grep -c "/cso" skills/ark-workflow/SKILL.md                        # record
grep -c "/investigate" skills/ark-workflow/SKILL.md                # record
grep -c "/canary" skills/ark-workflow/SKILL.md                     # record
grep -c "handoff_marker" skills/ark-workflow/SKILL.md              # record
grep -c "current-chain.md" skills/ark-workflow/SKILL.md            # record
```

Baseline values get written into the implementation plan (produced by `/writing-plans`) so phase assertions can compare exactly.

### 2. Behavioral parity — 22 v2 gaps regression checklist

Every v2 gap must still have observable content in the new layout. The implementation plan will include a grep-based checklist; this spec enumerates the gaps and their new locations:

| Gap | New location | Verification grep |
|---|---|---|
| 1. Multi-item batch handling | `references/batch-triage.md` | `grep -l "Root cause consolidation" references/batch-triage.md` |
| 2. `/TDD` → `/test-driven-development` | All chain files | `grep -rc "/test-driven-development" skills/ark-workflow/` sums to **12**; `grep -rc "/TDD\b"` sums to **0** |
| 3. `/investigate` in Hygiene | `chains/hygiene.md` | `grep -c "/investigate" chains/hygiene.md` ≥ **3** |
| 4. Migration + Performance scenarios | `chains/migration.md`, `chains/performance.md` | Both files exist; each has 3 H2 variant headers |
| 5. Session handoff for non-Greenfield Heavy | Inline `handoff_marker` values in `chains/greenfield.md`, `chains/migration.md`, `chains/performance.md`; prose pivot escape hatches inline in `chains/bugfix.md` and `chains/hygiene.md` (using the exact wording from current 1.6.0 — Bugfix uses "pivot to Heavy Greenfield from step 1", Hygiene uses "escalate to Heavy Greenfield"); per-scenario handoff point summary in `references/troubleshooting.md` | `grep -l "handoff_marker" skills/ark-workflow/chains/greenfield.md skills/ark-workflow/chains/migration.md skills/ark-workflow/chains/performance.md` finds all 3; `grep -l "pivot to Heavy Greenfield" skills/ark-workflow/chains/bugfix.md` finds it; `grep -l "escalate to Heavy Greenfield" skills/ark-workflow/chains/hygiene.md` finds it; `grep -l "Session Handoff" skills/ark-workflow/references/troubleshooting.md` |
| 6. Risk-primary + density triage | main `SKILL.md` Triage section | `grep -c "Risk sets the floor" SKILL.md` ≥ 1 |
| 7. Scenario-shift re-triage | `references/troubleshooting.md` | `grep -l "Scenario shift" references/troubleshooting.md` |
| 8. Knowledge Capture Light/Full | `chains/knowledge-capture.md` | `grep -c "^## " chains/knowledge-capture.md` = **2** |
| 9. Precise condition trigger lists | main `SKILL.md` Condition Resolution | `grep -c "Security-relevant triggers" SKILL.md` ≥ 1 |
| 10. *(deferred from v2 — not in scope)* | — | — |
| 11. Early exits | main `SKILL.md` Project Discovery | `grep -c "Early exits" SKILL.md` ≥ 1 |
| 12. Security audit/hardening split | main Scenario Detection + `chains/hygiene.md` dedup | `grep -c "Security audit / review" SKILL.md` ≥ 1; `grep -c "Dedup rule" chains/hygiene.md` ≥ 1 |
| C1. Root cause consolidation in batch triage | `references/batch-triage.md` | `grep -l "Root cause consolidation" references/batch-triage.md` |
| C2. Dependency detection heuristic | `references/batch-triage.md` | `grep -l "Dependency detection" references/batch-triage.md` |
| C3. Grouping into parallel / sequential / separate-session | `references/batch-triage.md` | `grep -l "parallel groups\|sequential chains" references/batch-triage.md` |
| C4. Cross-session continuity mechanism | `references/continuity.md` | `grep -l "Cross-Session Continuity" references/continuity.md` |
| C5. Rehydrate TodoWrite protocol | `references/continuity.md` | `grep -l "Rehydrate" references/continuity.md` |
| C6. `handoff_marker` logic | `references/continuity.md` (mechanics) + inline values in 3 chain files (greenfield, migration, performance) | `TOTAL_NEW=$(grep -rho "handoff_marker" skills/ark-workflow/ \| wc -l); TOTAL_BASELINE=$(grep -ho "handoff_marker" /tmp/ark-workflow-SKILL-1.6.0.md \| wc -l); [ "$TOTAL_NEW" -eq "$TOTAL_BASELINE" ]` (total occurrences equal to baseline capture) |
| C7. Stale chain detection | `references/continuity.md` | `grep -l "Stale Chain" references/continuity.md` |
| C8. Context recovery after compaction | `references/continuity.md` | `grep -l "Context Recovery" references/continuity.md` |
| C9. Hygiene Audit-Only variant | `chains/hygiene.md` | `grep -c "^## Audit-Only" chains/hygiene.md` = 1 |
| C10. `/cso` dedup rule | `chains/hygiene.md` | `grep -l "^## Dedup rule" chains/hygiene.md` |

### 3. Structural/file checks

```bash
# /TDD vs /test-driven-development — count total occurrences, not per-file
# grep -rc returns per-file counts; use grep -rho + wc -l for a real total
[ "$(grep -rho '/test-driven-development' skills/ark-workflow/ | wc -l)" -eq 12 ] \
  || echo "FAIL: /test-driven-development total not 12"
[ "$(grep -rho '/TDD\b' skills/ark-workflow/ | wc -l)" -eq 0 ] \
  || echo "FAIL: /TDD references present"

# All 7 scenario chain files exist
for f in greenfield bugfix ship knowledge-capture hygiene migration performance; do
  [ -f skills/ark-workflow/chains/$f.md ] || echo "MISSING: chains/$f.md"
done

# Per-variant H2 assertions — each expected H2 heading named explicitly by exact string.
# This replaces the earlier H2-count heuristic, which could pass by coincidence if a
# variant was dropped and an unrelated H2 added elsewhere.
grep -q "^## Light$"      skills/ark-workflow/chains/greenfield.md        || echo "FAIL: greenfield Light"
grep -q "^## Medium$"     skills/ark-workflow/chains/greenfield.md        || echo "FAIL: greenfield Medium"
grep -q "^## Heavy$"      skills/ark-workflow/chains/greenfield.md        || echo "FAIL: greenfield Heavy"

grep -q "^## Light$"      skills/ark-workflow/chains/bugfix.md            || echo "FAIL: bugfix Light"
grep -q "^## Medium$"     skills/ark-workflow/chains/bugfix.md            || echo "FAIL: bugfix Medium"
grep -q "^## Heavy$"      skills/ark-workflow/chains/bugfix.md            || echo "FAIL: bugfix Heavy"

# Ship has no H2 headers — it is a single un-sectioned variant
grep -q "^## "            skills/ark-workflow/chains/ship.md              && echo "FAIL: ship.md should have no H2 headers"

grep -q "^## Light$"      skills/ark-workflow/chains/knowledge-capture.md || echo "FAIL: knowledge-capture Light"
grep -q "^## Full$"       skills/ark-workflow/chains/knowledge-capture.md || echo "FAIL: knowledge-capture Full"

grep -q "^## Audit-Only$" skills/ark-workflow/chains/hygiene.md           || echo "FAIL: hygiene Audit-Only"
grep -q "^## Light$"      skills/ark-workflow/chains/hygiene.md           || echo "FAIL: hygiene Light"
grep -q "^## Medium$"     skills/ark-workflow/chains/hygiene.md           || echo "FAIL: hygiene Medium"
grep -q "^## Heavy$"      skills/ark-workflow/chains/hygiene.md           || echo "FAIL: hygiene Heavy"
grep -q "^## Dedup rule$" skills/ark-workflow/chains/hygiene.md           || echo "FAIL: hygiene Dedup rule"

grep -q "^## Light$"      skills/ark-workflow/chains/migration.md         || echo "FAIL: migration Light"
grep -q "^## Medium$"     skills/ark-workflow/chains/migration.md         || echo "FAIL: migration Medium"
grep -q "^## Heavy$"      skills/ark-workflow/chains/migration.md         || echo "FAIL: migration Heavy"

grep -q "^## Light$"      skills/ark-workflow/chains/performance.md       || echo "FAIL: performance Light"
grep -q "^## Medium$"     skills/ark-workflow/chains/performance.md       || echo "FAIL: performance Medium"
grep -q "^## Heavy$"      skills/ark-workflow/chains/performance.md       || echo "FAIL: performance Heavy"

# References contain required keywords (full paths for unambiguity)
grep -l "current-chain.md" skills/ark-workflow/references/continuity.md
grep -l "handoff_marker"   skills/ark-workflow/references/continuity.md
grep -l "Rehydrate\|rehydrate" skills/ark-workflow/references/continuity.md
grep -c "Step [0-4] —"     skills/ark-workflow/references/batch-triage.md   # ≥ 5
grep -l "Example Output"   skills/ark-workflow/references/batch-triage.md

# The plugin repo's own .gitignore retains .ark-workflow/ (this repo dogfoods /ark-workflow on itself).
# The runtime rule that *consumer* projects add .ark-workflow/ to their own gitignores is
# enforced by the inline instruction in main Step 6.5; it is not a build-time check.
grep -l "^\.ark-workflow/" .gitignore

# Main SKILL.md pointer sites
grep -c "chains/"     skills/ark-workflow/SKILL.md   # ≥ 1 (Step 4 + File Map)
grep -c "references/" skills/ark-workflow/SKILL.md   # ≥ 5 (Step 2, Step 6.5, ×3 When Things Change, Routing Rules, File Map)
```

### 4. Post-extraction content parity diff (Phase 1b and Phase 2 gates)

The grep checks in Section 3 only catch content that's missing from the wrong file. They do **not** catch content that moved between variants, dropped inline conditional annotations, shifted `handoff_marker` positions by one step, or reordered steps within a variant. Those are the highest-risk silent regressions for a pure-extraction refactor.

**Mitigation:** after Phase 1b and after Phase 2, run a diff-based parity check that reconstructs the original source ranges from the extracted files and compares against the baseline snapshot (`/tmp/ark-workflow-SKILL-1.6.0.md`).

**For Phase 1b (chain files):**

Reconstruct the original `## Skill Chains` section (current SKILL.md lines 410-712, including the header, chain separators, and all 7 scenario sub-sections) from the 7 chain files by reversing the permitted formatting changes:
- `# {Scenario}` (H1 in chain file) → `### {Scenario}` (H3 in original) with the original scenario name
- `## {WeightClass}` (H2 in chain file) → `**{WeightClass}:**` (bold label in original)
- Restore the `---` separators between weight variants and between scenarios
- Preserve inline bold labels like `**Dedup rule:**` as-is
- Preserve italic sub-labels like `*Session 1 — Design:*` as-is
- Preserve all other content character-for-character

Then diff the reconstruction against `sed -n '410,712p' /tmp/ark-workflow-SKILL-1.6.0.md`. Any non-empty diff (after whitespace normalization) aborts Phase 1b and requires extraction fixes before Phase 2.

**For Phase 2 (reference files):**

Reconstruct each reference file's corresponding slice of the original:
- `references/batch-triage.md` vs baseline `sed -n '163,249p'` (with H1→H2 demotion reversed)
- `references/continuity.md` vs baseline `sed -n '309,371p'` (no structural changes — the Step 6.5 inline block comes from L259-299 which is *separate* and stays in main)
- `references/troubleshooting.md` vs concatenation of baseline `sed -n '761,774p'` + `sed -n '776,789p'` + `sed -n '791,812p'` (three non-contiguous ranges merged in a specific order)
- `references/routing-template.md` vs baseline `sed -n '814,858p'` (with H1→H2 demotion reversed and the added "Copy the block below..." preamble stripped)

**Implementation plan will specify:** the concrete reconstruction scripts (Python or shell), whitespace/separator normalization rules, the exact source line ranges (re-verified against the baseline snapshot), and the exact diff commands. The plan authors should **test the reconstruction against the current SKILL.md before Phase 1b begins** to verify the reconstruction algorithm is sound — the algorithm should produce a byte-identical match for any hypothetical "perfect extraction" and should fail noisily for any drift.

**Abort condition:** any non-empty diff after documented normalization aborts the offending phase. The implementing agent reverts that phase, fixes the extraction, re-runs the check.

**What this catches:** step text moved between variants, dropped conditional annotations (`(if X)`), shifted `handoff_marker` positions, rewritten step phrases, missing or added steps, reordered steps within a variant, lost italic sub-labels like `*Session 1 — Design:*`, missing paragraphs in reference files.

**What this does NOT catch:** Phase 3 main `SKILL.md` rewrite errors (caught by Section 5 line-count verification + manual review), cross-file behavioral outcomes (caught by Section 5 smoke tests), or grep-missable content completely absent from the new layout (caught by Section 2 gap checklist).

### 5. Smoke tests — mental walkthrough

These validate that the new layout produces the same triage output as the current monolithic `SKILL.md` would, given identical Project Discovery inputs. Thirteen tests total, covering single-item paths for each scenario plus batch, security, decision-density, and cross-session resume (happy path + stale) edge cases.

| # | Test | Expected triage path | Files the agent loads |
|---|---|---|---|
| 1 | **Session A (batch)** — the 5 Bugfix items from the Batch Triage example in current SKILL.md L225-247: #1 transaction isolation (M), #2 ghost pipeline runs (L), #3 payload drop (M), #4 retry storms (H), #5 MCP shutdown (L) | Multi-item → Batch Triage → per-item M/L/M/H/L all Bugfix → grouping **must match current example verbatim**: Group A (L, parallel) #2 #5, Group B (M, sequential) #3, Group C (H, pending dep confirmation) #1 → #4, Heavy flagged for separate session | main + `references/batch-triage.md` + `chains/bugfix.md` |
| 2 | **Session B (batch)** — file permissions + SSE tunnel + dashboard blocking | Multi-item → Batch Triage → Bugfix Heavy, Bugfix Medium, Performance Light | main + `references/batch-triage.md` + `chains/bugfix.md` + `chains/performance.md` |
| 3 | **Session C (batch)** — TS build break + ESLint cleanup | Multi-item → Batch Triage → Bugfix Medium + Hygiene Light (scenario split preserved) | main + `references/batch-triage.md` + `chains/bugfix.md` + `chains/hygiene.md` |
| 4 | **Security audit** — "audit our auth subsystem" | Scenario Detection security path 1 → Hygiene Audit-Only → chain ends with STOP + user choice | main + `chains/hygiene.md` (Audit-Only section) |
| 5 | **Security hardening** — "harden our auth subsystem" | Scenario Detection security path 2 → Hygiene Heavy with `/cso` prepended + later `/cso` deduped per Dedup rule | main + `chains/hygiene.md` (Heavy + Dedup rule) |
| 6 | **Decision-density escalation** — "redesign the caching layer" (low risk, architecture density) | Triage: Low risk → Light floor; architecture decisions → escalate to Heavy; scenario Hygiene or Greenfield → Heavy variant | main + `chains/hygiene.md` or `chains/greenfield.md` |
| 7 | **Cross-session resume (happy path)** — Session 2 starts in a project with existing `.ark-workflow/current-chain.md`, `handoff_marker: after-step-5` set and checked | Routing template fires → agent reads chain file → announces "Session 2, design phase complete, next: `/executing-plans` with spec at X" → rehydrates TodoWrite from unchecked steps | `.ark-workflow/current-chain.md` + `references/continuity.md` + `chains/greenfield.md` |
| 8 | **Standalone Ship** — "cherry-pick the hotfix from master and deploy" | Ship scenario (no weight class) → Ship chain → `/review` → `/ship` → `/land-and-deploy` | main + `chains/ship.md` |
| 9 | **Knowledge Capture Full** — "catch up the vault after two weeks, rebuild tags, ingest the external ADR docs" | KC scenario → Full (not Light, based on scope signals: extended period + tag rebuild + external ingest) | main + `chains/knowledge-capture.md` (Full section) |
| 10 | **Single-item Migration Medium** — "upgrade the React Native dep from 0.72 to 0.74, API changes required" | Migration scenario → Medium (major version bump with API changes, risk moderate, density some trade-offs) | main + `chains/migration.md` (Medium section) |
| 11 | **Single-item Performance Heavy** — "redesign the database query layer for the dashboard, currently 10-second page loads, need a caching architecture" | Performance scenario → Heavy (architecture density escalates from Low risk to Heavy) | main + `chains/performance.md` (Heavy section) |
| 12 | **Mixed batch with Knowledge Capture** — "fix the login redirect bug AND update the README to document the new auth flow" | Multi-item → Batch Triage → Bugfix (Light/Medium) + Knowledge Capture Light; executed sequentially since KC depends on bug fix landing | main + `references/batch-triage.md` + `chains/bugfix.md` + `chains/knowledge-capture.md` |
| 13 | **Stale chain detection** — session start finds `.ark-workflow/current-chain.md` with `created:` 10 days old | Agent detects >7-day staleness → prompts user "still active or archive?" → does NOT auto-delete → waits for user decision | `.ark-workflow/current-chain.md` + `references/continuity.md` (stale detection section) |

Execution: the Session 2 implementing agent will trace each test step-by-step against the new files and record the chain output in the session log. No automated harness — these are markdown skills, not code. Any divergence from expected output is a behavioral regression and aborts the release.

**Coverage confirmation:** Tests 1-3 cover batch triage across the 4 scenario chain files it touches most (Bugfix, Performance, Hygiene). Test 4 covers Hygiene Audit-Only. Test 5 covers the `/cso` dedup rule. Test 6 covers the risk-density triage escalation logic. Test 7 covers the cross-session resume happy path. Tests 8-11 cover standalone single-item paths for Ship, Knowledge Capture Full, Migration, and Performance — the scenarios with the least batch exposure. Test 12 covers a mixed-scenario batch that includes KC. Test 13 covers a non-happy-path resume (stale chain). Every chain file is exercised by at least one test; every major edge case (no weight class, Light/Full split, Audit-Only, dedup, density escalation, resume, stale) has a dedicated test.

### 6. Line count verification — numbers for CHANGELOG

After all phases complete:

```bash
echo "== Line counts =="
wc -l skills/ark-workflow/SKILL.md
wc -l skills/ark-workflow/chains/*.md
wc -l skills/ark-workflow/references/*.md
echo "== Word counts =="
wc -w skills/ark-workflow/SKILL.md skills/ark-workflow/chains/*.md skills/ark-workflow/references/*.md
echo "== Common-path totals =="
# main + each chain file
```

Report shape (filled in at release):

> **1.7.0 — ark-workflow progressive-disclosure split**
>
> Main router: 858 → {X} lines ({reduction}%)
> Common-path load (router + one chain file, avg): 858 → {Y} lines ({reduction}%)
> Common-path load (worst case, Greenfield): 858 → {Z} lines ({reduction}%)
> Total repo footprint: 858 → {W} lines ({delta}%)
>
> Chain files: 7 files, {C} lines total
> Reference files: 4 files, {R} lines total
>
> Behavioral parity: all 22 v2 gaps preserved, all 19 chain variants preserved, all 12 `/test-driven-development` references preserved, 0 `/TDD` references.

### 7. Rollback plan

Each phase is an atomic commit. Rollback options in order of preference:

1. **Per-phase revert** — if a mid-stream phase breaks something: `git revert {phase-commit}` rolls back just that phase; spec and prior phases remain.
2. **Full rollback** — if the split is fundamentally wrong: `git revert` all phase commits in reverse order. The 1.6.0 `SKILL.md` is preserved in git history at `f690ebf`.
3. **Abandoned branch** — if Phase 1 reveals the design is wrong: close feature branch without merging, update spec, re-run `/codex` on updated spec, re-enter implementation phase. No changes reach master.

## Phased execution outline

The detailed implementation plan is produced by `/writing-plans` after this spec is approved. This section sketches the high-level phase structure only, per CLAUDE.md's `≤5 files per phase` rule with approval checkpoints between phases.

**Phase 0 is explicitly dropped.** The v2 rewrite shipped 4 days ago through `/codex` review; there is no dead content to clean ahead of this refactor. The CLAUDE.md Step 0 rule ("remove dead code before structural refactors of code files >300 LOC") applies to source code, not to a freshly-reviewed markdown router. If real dead content surfaces mid-refactor, handle it in Phase 3 (the main SKILL.md rewrite) where the content is already being touched. Dropping Phase 0 also preserves the baseline capture integrity — all later grep/diff checks compare against the actual shipped 1.6.0 file, not a pre-cleaned variant.

**Baseline capture** is the **first action of Phase 1a**, before any chain file extraction begins.

| Phase | Description | Files touched | Commit style |
|---|---|---|---|
| 1a | **First action:** run baseline capture commands from Verification § 1 (line counts, word counts, `/tmp/ark-workflow-SKILL-1.6.0.md` snapshot, grep baselines). **Then:** create first 5 `chains/` files with text-verbatim content extracted from current `SKILL.md`. `SKILL.md` not yet modified. | 5 new: `chains/{greenfield,bugfix,ship,knowledge-capture,hygiene}.md` | `refactor(ark-workflow): extract chains/ (5/7)` |
| 1b | Create remaining 2 `chains/` files. | 2 new: `chains/{migration,performance}.md` | `refactor(ark-workflow): extract chains/ (7/7)` |
| 2 | Create all 4 `references/` files with text-verbatim content (minus the dropped Condition Resolution example block). `SKILL.md` still not modified. | 4 new: `references/{batch-triage,continuity,troubleshooting,routing-template}.md` | `refactor(ark-workflow): extract references/` |
| 3 | Rewrite main `SKILL.md`: delete migrated content, add pointers, slim Step 6.5, add When Things Change, add File Map, update Steps 2 and 4 | 1 modified: `SKILL.md` | `refactor(ark-workflow): slim main SKILL.md to router` |
| 4a | Release core: version bump + CHANGELOG | 4 modified: `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md` | `chore: bump 1.6.0 → 1.7.0 + CHANGELOG` |
| 4b | Release docs sync: README (if it references file count or structure) + TODO.md (mark the deferred split as completed; do NOT file the Heavy Hygiene design-phase follow-up here — that is out of scope for this parity refactor) | Up to 2 modified: `README.md` (conditional), `TODO.md` | `docs: sync README + update TODO for 1.7.0` |
| 5 | Verification: baseline capture was already done at the start of Phase 1a; here we run all grep checks (Verification § 2, § 3), post-extraction parity diffs (§ 4) for chains and references, mental walkthrough of all 13 smoke tests (§ 5), record final line counts, write session log S004 | 1 new: `vault/Session-Logs/S004-Ark-Workflow-Split.md` | `docs(vault): add S004 session log` |
| 6 | Ship: feature branch `refactor/ark-workflow-split`, `/ark-code-review --thorough`, `/simplify`, `/codex` review of implementation, `/ship` → `/land-and-deploy` | 0 directly (only commit metadata) | Per `/ship` convention |

Every phase is ≤ 5 files. Every phase ends with a commit and an explicit `CHECKPOINT` marker in the written plan; the implementing session halts between phases for user approval per CLAUDE.md rule.

## Release

- **Version:** 1.6.0 → 1.7.0
- **Version-bump files:** `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- **CHANGELOG.md entry** under `## [1.7.0] - 2026-04-10` / `### Changed`:

  > **ark-workflow**: progressive-disclosure split of the monolithic router
  > - Main `SKILL.md`: 858 → {X} lines ({reduction}%)
  > - Common-path context load (router + one chain file): 858 → {Y} lines avg ({reduction}%); worst case 858 → {Z} lines ({reduction}%)
  > - Chain variants moved to `chains/{scenario}.md` (7 files)
  > - Pay-per-use content moved to `references/{batch-triage,continuity,troubleshooting,routing-template}.md`
  > - Behavioral parity: all 22 v2 gaps preserved, all 19 chain variants preserved, 12 `/test-driven-development` references preserved, 0 `/TDD` references
  > - File count in `skills/ark-workflow/`: 1 → 12
  > - Total repo footprint: 858 → {W} lines ({delta} lines, explained in the spec as on-disk overhead for context-load savings)

- **README sync:** the README mentions ark-workflow v2 with 7 scenarios, batch triage, continuity. Check whether the description references file count or structure — if it does, update. If it describes features only, no update needed.
- **Commit style:** `refactor(ark-workflow): ...` for structural phases, `chore:` for version bump and release docs. Co-Authored-By trailer. HEREDOC for multi-line messages. Matches 1.6.0 phase convention.
- **Feature branch:** `refactor/ark-workflow-split`. Required per CLAUDE.md "abort on base branch" rule in `/ship`.
- **Session log:** `vault/Session-Logs/S004-Ark-Workflow-Split.md` (increments from S003).

## Follow-ups (filed separately — not fixed in this refactor)

1. **Latent v2 gap — Heavy Hygiene lacks a front-loaded design phase.** v2's Heavy Hygiene chain is `audit → /cso → /test-driven-development → implement`. The only escape hatch is Step 3's reactive pivot-to-Heavy-Greenfield *after* audit runs. A structural refactor with genuine architecture decisions — like this split — needs `brainstorm → spec → /codex → /writing-plans → /codex → /executing-plans` up front. For markdown-only plugins the asymmetry is especially sharp because `/cso` and `/test-driven-development` do not apply. **Proposed fix for a later release:** Heavy Hygiene should fork on decision density — obvious cleanup follows the current chain; architecture refactors use the Heavy Greenfield design phase. **Not filed in this refactor** to keep scope clean: file as a separate `chore:` commit after 1.7.0 ships, or raise it during the next routine TODO.md review. Do not bundle into the release phases.

2. **Smoke tests remain mental, not executed.** The v2 verification was also mental (per S003). The skill is markdown with no test harness. Real validation comes from the next several `/ark-workflow` invocations in practice across Ark projects.

3. **Dropped Condition Resolution "Example Resolved Output" block.** 14 lines removed from the total repo footprint. If user feedback post-ship shows agents struggling to produce well-formatted resolved chain output, re-introduce a 3-line minimal example directly in Workflow Step 5 instead of bringing back the full 14-line block.
