# Ark Workflow Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (with subagent dispatch where useful) to implement this plan phase-by-phase. Steps use checkbox (`- [ ]`) syntax for tracking. Halt at every `CHECKPOINT` for user approval per CLAUDE.md "PHASED EXECUTION" rule.

**Goal:** Refactor `skills/ark-workflow/SKILL.md` from a single 858-line monolith into a progressive-disclosure layout (1 main router + 7 chain files + 4 reference files) to cut common-path context load by ≥ 50% while preserving all 22 v2 gaps and all 19 chain variants text-verbatim.

**Architecture:** Move per-scenario chain variants into `skills/ark-workflow/chains/{scenario}.md` files (loaded once per triage after scenario detection) and pay-per-use protocols into `skills/ark-workflow/references/{batch-triage,continuity,troubleshooting,routing-template}.md` (loaded only when their trigger fires). Main `SKILL.md` becomes a ≤ 400-line router that points into the sub-files. Strict cross-reference DAG: main → chains/* and main → references/*; no chain↔chain or reference↔reference edges; no back-edges to main.

**Tech Stack:** Markdown only. No code, no test harness. Verification is by `grep`, `wc -l`, line-range `sed` slicing, two Python reconstruction parity scripts, and a 13-test mental smoke-walkthrough. Python 3 (stdlib only) for the parity scripts.

**Spec:** `docs/superpowers/specs/2026-04-10-ark-workflow-split-design.md` (739 lines, HEAD `fc0d879`)
**Branch:** `refactor/ark-workflow-split` (already created — never commit to master)
**Current `SKILL.md`:** 858 lines at `f690ebf` (1.6.0)
**Target version:** 1.7.0

---

## Execution Notes

- **Re-read every file before editing it** (CLAUDE.md Edit Integrity rule). After every edit, the next step re-reads to confirm the change applied. This is non-negotiable for Phase 3 — the only Edit-heavy phase.
- **No semantic search** (CLAUDE.md rule). Multiple grep patterns for any rename. The Phase 3 Step 4 scenario→filename mapping is verified by grepping all 7 filenames after the rewrite.
- **Each phase is one commit.** Phase boundaries are CHECKPOINTs. Halt for user approval between phases.
- **≤ 5 files per phase** (CLAUDE.md rule). Verified explicit in each phase's Files section.
- **Baseline capture is the first action of Phase 1a**, before any chain extraction. The `/tmp/ark-workflow-SKILL-1.6.0.md` snapshot is the source of truth for every parity diff. **It is ephemeral** — if a session is interrupted between phases, the next session must re-capture it (`SKILL.md` is unmodified by Phases 1a, 1b, 2; the snapshot still matches).
- **Behavioral parity is the hard constraint.** No "improvements" beyond the permitted structural transformations enumerated below. No new prose, no reordering, no `handoff_marker` values added to Bugfix or Hygiene (current 1.6.0 only has inline `handoff_marker` in Greenfield Medium step 3, Greenfield Heavy step 5, Migration Heavy step 4, Performance Heavy step 5).
- **Tool pick:** use `Read`, `Edit`, `Write`, `Grep`, `Glob`, and `Bash` only. Do not use sub-agents for this plan — every phase is small enough to fit in a single context window, and the parity scripts need direct verification.

---

## Spec Clarifications and Deviations

These are real ambiguities discovered while writing this plan. Each is a defensible interpretation; flag during `/codex` review of this plan if any reading is wrong.

### 1. Permitted structural transformations — additions to spec § "Content preservation rules"

The spec lists 5 permitted changes. Two more are required by the worked examples and the actual structure of current `SKILL.md`. The full and authoritative list for this plan:

1. **Demote `### {Scenario}` → `# {Scenario}`** (H1 in chain file).
2. **Demote bold weight labels → H2 headers**, with this case split:
   - **Bare form** `**{Weight}:**` → `## {Weight}` (no descriptor line).
   - **Parenthetical form** `**{Weight}** ({descriptor}):` → `## {Weight}\n\n*{descriptor}*` (descriptor lifted to italic line directly under the H2). **Case and punctuation of the descriptor are preserved exactly** — including the leading lowercase letter (`*for "audit", "review"...`*` not `*For ...`*`). The worked example in spec § "Worked example: chains/hygiene.md" capitalizes "For" — that is a spec typo; the actual extraction must preserve baseline case.
3. **Drop `---` separators between scenarios.** The spec says "between weight variants" but the grep audit (verified for this plan) shows there are NO `---` separators between weight variants in current `SKILL.md` — only between scenarios (L414, L479, L524, L537, L559, L608, L660, L713). Moving each scenario to its own file naturally drops the inter-scenario separators; there is nothing to drop between weight variants.
4. **Keep `*Session 1 — Design:*` / `*Session 2 — Implementation:*` / `*Document:*` italic sub-labels exactly as-is.**
5. **Keep inline `(set handoff_marker: after-step-N)` markers exactly where they appear** in current chain steps.
6. **`**Dedup rule:** {body}` → `## Dedup rule\n\n{body}`** — inline bold + body text on the same paragraph becomes an H2 header followed by a body paragraph. Applies only to `chains/hygiene.md`. The reconstruction script reverses this.
7. **For `chains/knowledge-capture.md` only:** the prose paragraph at current `SKILL.md` L541 ("Requires vault — if `HAS_VAULT=false`...") sits between the `### Knowledge Capture` H3 and the first `**Light**` label in baseline. After demotion to H1, it sits between `# Knowledge Capture` and the first `## Light`. Keep verbatim.

### 2. `chains/ship.md` has no weight classes

Ship has no `**Light/Medium/Heavy**` labels — the original L526-535 is one un-sectioned variant with an italic descriptor (`*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*`) followed by the numbered steps. The chain file becomes:

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

The Phase 3 H2 grep check (`grep -q "^## " chains/ship.md && FAIL`) enforces this.

### 3. `references/continuity.md` and `references/routing-template.md` are NOT pure extractions

The spec § 4 (Phase 2 parity diff) describes both as line-range diffs against baseline, but the spec's own example bodies for these two files include **added scaffolding** (new H2 headers like `## Cross-Session Continuity`, new preamble paragraphs, the new `## Archive on Completion` rule, the routing-template's new "Copy the block below..." preamble). A pure line-range diff would not match.

**Resolution:** the Phase 2 parity diff covers only the two files that ARE pure extractions:
- `references/batch-triage.md` (vs baseline L163-249, with H1↔H2 demote reversed)
- `references/troubleshooting.md` (vs concat of L761-774 + L776-789 + L791-812, no transformations)

For `references/continuity.md` and `references/routing-template.md`, Phase 2 instead uses **content-preservation grep checks** (the spec § 3 grep set) plus a manual visual review by re-reading the file and comparing against the spec's example body. This is a softer gate but matches what the spec actually constructs.

### 4. The L712 vs L713 question

Spec § 4 says "Reconstruct the original `## Skill Chains` section (current SKILL.md lines 410-712) ... diff the reconstruction against `sed -n '410,712p' /tmp/ark-workflow-SKILL-1.6.0.md`". Verified for this plan: L711 is the last step of Performance Heavy (`18. /claude-history-ingest`), L712 is blank, L713 is the closing `---` separator before Condition Resolution. The slice 410-712 ends at the blank line and **does not include** the closing `---`. The reconstruction script therefore emits no trailing `---` after the Performance section.

---

## Baseline (filled in at Phase 1a Step 1)

| Metric | Expected | Actual (recorded at Phase 1a) |
|---|---|---|
| `wc -l SKILL.md` | 858 | __________ |
| `wc -w SKILL.md` | (record) | __________ |
| `grep -c "/test-driven-development"` | 12 | __________ |
| `grep -c "/TDD\b"` | 0 | __________ |
| `grep -c "/cso"` | (record) | __________ |
| `grep -c "/investigate"` | (record) | __________ |
| `grep -c "/canary"` | (record) | __________ |
| `grep -c "handoff_marker"` | (record) | __________ |
| `grep -c "current-chain.md"` | (record) | __________ |

Per spec § 4 the C6 gap check uses `handoff_marker` total occurrences vs baseline — the recorded value matters for Phase 5.

---

## Target File Structure

```
skills/ark-workflow/
├── SKILL.md                           # ~285 lines (≤ 400 hard cap) — router only
├── chains/
│   ├── greenfield.md                  # ~68 lines — Light/Medium/Heavy
│   ├── bugfix.md                      # ~48 lines — Light/Medium/Heavy
│   ├── ship.md                        # ~14 lines — standalone, no weight class
│   ├── knowledge-capture.md           # ~24 lines — Light/Full
│   ├── hygiene.md                     # ~52 lines — Audit-Only/L/M/H + Dedup rule
│   ├── migration.md                   # ~56 lines — Light/Medium/Heavy
│   └── performance.md                 # ~56 lines — Light/Medium/Heavy
└── references/
    ├── batch-triage.md                # ~95 lines — pure extraction of L163-249
    ├── continuity.md                  # ~100 lines — restructured from L309-371 + new scaffolding
    ├── troubleshooting.md             # ~50 lines — concat of L761-774 + L776-789 + L791-812
    └── routing-template.md            # ~45 lines — extracted from L814-858 + new preamble
```

---

## Phase 1a — Baseline capture + extract first 5 chain files

**Files (5 new, 0 modified):**
- Create: `skills/ark-workflow/chains/greenfield.md`
- Create: `skills/ark-workflow/chains/bugfix.md`
- Create: `skills/ark-workflow/chains/ship.md`
- Create: `skills/ark-workflow/chains/knowledge-capture.md`
- Create: `skills/ark-workflow/chains/hygiene.md`

(Plus the ephemeral `/tmp/ark-workflow-SKILL-1.6.0.md` snapshot, which is not a tracked file.)

### Step 1: Baseline capture (FIRST ACTION — before any extraction)

Run these exact commands in a single Bash invocation; record outputs in the Baseline table above:

```bash
wc -l skills/ark-workflow/SKILL.md
wc -w skills/ark-workflow/SKILL.md
cp skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md
grep -c "/test-driven-development" skills/ark-workflow/SKILL.md
grep -c "/TDD\b"                    skills/ark-workflow/SKILL.md
grep -c "/cso"                       skills/ark-workflow/SKILL.md
grep -c "/investigate"               skills/ark-workflow/SKILL.md
grep -c "/canary"                    skills/ark-workflow/SKILL.md
grep -c "handoff_marker"             skills/ark-workflow/SKILL.md
grep -c "current-chain.md"           skills/ark-workflow/SKILL.md
```

Expected: line count = 858, `/test-driven-development` = 12, `/TDD\b` = 0. If either of those two diverges, **STOP** — the working copy is not 1.6.0 and the rest of this plan is unsafe to run.

### Step 2: Re-read the chain section of current `SKILL.md`

Read `skills/ark-workflow/SKILL.md` lines 410-712 with the Read tool (use `offset=410, limit=303`). This is the source-of-truth content for all 7 chain files. Do not trust memory of this content from any earlier conversation.

### Step 3: Verify the `chains/` directory exists

```bash
mkdir -p skills/ark-workflow/chains
ls skills/ark-workflow/chains/
```

Expected: directory exists, empty.

### Step 4: Write `chains/greenfield.md`

Source: current `SKILL.md` L416-477 (Greenfield Feature). Apply transformations 1+2+4+5 from "Spec Clarifications § 1".

Use the Write tool to create `skills/ark-workflow/chains/greenfield.md` with this exact content:

````markdown
# Greenfield Feature

## Light

*rare for greenfield*

1. Implement directly
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

## Medium

*Session 1 — Design:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. Commit spec → **end session, start fresh for implementation** (set `handoff_marker: after-step-3`)

*Session 2 — Implementation:*
4. Read spec from `docs/superpowers/specs/`
5. `/test-driven-development` — write tests first, implement against them
6. `/ark-code-review --quick` → `/simplify`
7. `/qa` (if UI)
8. `/cso` (if security-relevant)
9. `/ship` → `/land-and-deploy`
10. `/canary` (if deploy risk)

*Document:*
11. `/wiki-update` (if vault)
12. `/wiki-ingest` (if vault + new component needs its own page)
13. `/cross-linker` (if vault)
14. `/document-release` (if standard docs exist)
15. Session log

## Heavy

*Session 1 — Design & Planning:*
1. `/brainstorming` — explore intent, propose approaches, write spec
2. `/codex` — review the spec
3. `/writing-plans` — break into phased implementation plan
4. `/codex` — review the plan
5. Commit spec + plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read spec + plan from `docs/superpowers/specs/`
7. `/executing-plans` with `/test-driven-development` per step
8. `/subagent-driven-development` — parallelize independent modules
9. `/checkpoint` (optional — if pausing mid-implementation)
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
11. `/qa` (if UI)
12. `/design-review` (if UI)
13. `/cso` (if security-relevant)
14. `/ship` → `/land-and-deploy`
15. `/canary` (if deploy risk)

*Document:*
16. `/wiki-update` (if vault)
17. `/wiki-ingest` (if vault + new component needs its own page)
18. `/cross-linker` (if vault)
19. `/document-release` (if standard docs exist)
20. Session log
21. `/claude-history-ingest`
````

Verification:

```bash
grep -q "^# Greenfield Feature$"             skills/ark-workflow/chains/greenfield.md
grep -q "^## Light$"                          skills/ark-workflow/chains/greenfield.md
grep -q "^## Medium$"                         skills/ark-workflow/chains/greenfield.md
grep -q "^## Heavy$"                          skills/ark-workflow/chains/greenfield.md
grep -q "handoff_marker: after-step-3"        skills/ark-workflow/chains/greenfield.md
grep -q "handoff_marker: after-step-5"        skills/ark-workflow/chains/greenfield.md
grep -c "^[0-9]\+\. "                         skills/ark-workflow/chains/greenfield.md  # expect 42
```

### Step 5: Write `chains/bugfix.md`

Source: current `SKILL.md` L481-522. Apply transformations 1+2 (bare form, all three weights).

Use the Write tool to create `skills/ark-workflow/chains/bugfix.md` with this exact content:

````markdown
# Bug Investigation & Fix

## Light

1. `/investigate` — root cause analysis
2. Fix directly
3. `/cso` (if security-relevant)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)
7. Session log (only if surprising root cause)

## Medium

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected
3. `/test-driven-development` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix
5. `/ark-code-review --quick` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

## Heavy

1. `/investigate` — root cause analysis
2. Re-triage if deeper than expected. **If investigation reveals architectural redesign is needed: `/checkpoint` findings, end session, start fresh with a design phase (pivot to Heavy Greenfield from step 1).**
3. `/test-driven-development` — write a failing test that reproduces the bug (if not reproducible, document why and proceed)
4. Fix (structured, may require `/executing-plans`)
5. `/ark-code-review --thorough` + `/codex` → `/simplify`
6. `/qa` (if UI)
7. `/cso` (if security-relevant)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. `/wiki-ingest` (if vault + fix introduces a new concept)
12. `/cross-linker` (if vault)
13. Session log
14. `/claude-history-ingest`
````

Verification:

```bash
grep -q "^# Bug Investigation & Fix$"        skills/ark-workflow/chains/bugfix.md
grep -q "^## Light$"                          skills/ark-workflow/chains/bugfix.md
grep -q "^## Medium$"                         skills/ark-workflow/chains/bugfix.md
grep -q "^## Heavy$"                          skills/ark-workflow/chains/bugfix.md
grep -q "pivot to Heavy Greenfield"           skills/ark-workflow/chains/bugfix.md   # gap 5 verification
grep -c "/test-driven-development"            skills/ark-workflow/chains/bugfix.md   # expect 2
! grep -q "handoff_marker" skills/ark-workflow/chains/bugfix.md   # bugfix has NO handoff_marker
```

### Step 6: Write `chains/ship.md`

Source: current `SKILL.md` L526-535. No weight classes — single un-sectioned variant.

Use the Write tool to create `skills/ark-workflow/chains/ship.md` with this exact content:

````markdown
# Shipping & Deploying

*Standalone ship — cherry-pick, config change, dependency bump. No weight class needed.*

1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk)
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)
````

Verification:

```bash
grep -q "^# Shipping & Deploying$"                            skills/ark-workflow/chains/ship.md
! grep -q "^## "                                              skills/ark-workflow/chains/ship.md   # no H2 at all
grep -q "^\*Standalone ship"                                  skills/ark-workflow/chains/ship.md
[ "$(grep -c '^[0-9]\+\. ' skills/ark-workflow/chains/ship.md)" -eq 6 ]
wc -l skills/ark-workflow/chains/ship.md   # expect ~11-14
```

### Step 7: Write `chains/knowledge-capture.md`

Source: current `SKILL.md` L539-557. Includes the prose paragraph at L541 ("Requires vault…").

Use the Write tool to create `skills/ark-workflow/chains/knowledge-capture.md` with this exact content:

````markdown
# Knowledge Capture

Requires vault — if `HAS_VAULT=false`, tell the user to run `/wiki-setup` first. (This should already be caught by the early exit in Project Discovery.)

## Light

*syncing recent changes, updating a few pages*

1. `/wiki-update` — sync recent changes
2. `/cross-linker` (if vault)

## Full

*catching up after extended period, rebuilding tags, ingesting external docs*

1. `/wiki-status` — vault statistics
2. `/wiki-lint` — broken links, missing frontmatter, tag violations
3. `/wiki-update` — sync recent changes
4. `/wiki-ingest` — distill external documents if needed
5. `/cross-linker` — discover missing wikilinks
6. `/tag-taxonomy` — normalize tags
7. `/claude-history-ingest` — mine recent sessions
8. Session log
````

Verification:

```bash
grep -q "^# Knowledge Capture$"               skills/ark-workflow/chains/knowledge-capture.md
grep -q "^## Light$"                          skills/ark-workflow/chains/knowledge-capture.md
grep -q "^## Full$"                           skills/ark-workflow/chains/knowledge-capture.md
grep -q "Requires vault"                      skills/ark-workflow/chains/knowledge-capture.md
[ "$(grep -c '^## ' skills/ark-workflow/chains/knowledge-capture.md)" -eq 2 ]
```

### Step 8: Write `chains/hygiene.md`

Source: current `SKILL.md` L561-606. Includes the Audit-Only variant, three weight classes, and the Dedup rule (transformation 6).

Use the Write tool to create `skills/ark-workflow/chains/hygiene.md` with this exact content:

````markdown
# Codebase Hygiene

## Audit-Only

*for "audit", "review", "assess" requests with no remediation expected*

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

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. `/cso` (if security-relevant AND `/cso` not already run as mandatory step 1)
4. `/test-driven-development` — tests before restructuring
5. Implement cleanup
6. `/ark-code-review --quick` → `/simplify`
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault) + session log

## Heavy

1. `/codebase-maintenance` — audit
2. `/investigate` (if any item involves broken/unexpected behavior)
3. **If audit + investigation reveals systemic issues requiring rewrite: escalate to Heavy Greenfield. `/checkpoint` findings, end session, start fresh with design phase.**
4. `/cso` — infrastructure, dependency, secrets audit (this IS the mandatory `/cso` run — no duplicate later)
5. `/test-driven-development` — tests before restructuring
6. Implement cleanup
7. `/ark-code-review --thorough` + `/codex` → `/simplify`
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault) + session log
11. `/claude-history-ingest`

## Dedup rule

If security hardening triggers mandatory early `/cso` (before the chain starts), skip the conditional `/cso` inside the chain. `/cso` runs exactly once per chain execution.
````

Verification:

```bash
grep -q "^# Codebase Hygiene$"                skills/ark-workflow/chains/hygiene.md
grep -q "^## Audit-Only$"                     skills/ark-workflow/chains/hygiene.md
grep -q "^## Light$"                          skills/ark-workflow/chains/hygiene.md
grep -q "^## Medium$"                         skills/ark-workflow/chains/hygiene.md
grep -q "^## Heavy$"                          skills/ark-workflow/chains/hygiene.md
grep -q "^## Dedup rule$"                     skills/ark-workflow/chains/hygiene.md
grep -q "escalate to Heavy Greenfield"        skills/ark-workflow/chains/hygiene.md   # gap 5 verification
grep -c "/investigate"                        skills/ark-workflow/chains/hygiene.md   # expect ≥ 3
grep -q "STOP"                                skills/ark-workflow/chains/hygiene.md
! grep -q "handoff_marker" skills/ark-workflow/chains/hygiene.md   # hygiene has NO handoff_marker
```

### Step 9: Sanity-grep all 5 new chain files in one shot

```bash
ls skills/ark-workflow/chains/
[ "$(ls skills/ark-workflow/chains/*.md | wc -l)" -eq 5 ]
grep -rho "/test-driven-development" skills/ark-workflow/chains/ | wc -l   # expect 5 so far
grep -rho "/TDD\b"                    skills/ark-workflow/chains/ | wc -l   # expect 0
```

### Step 10: Commit Phase 1a

```bash
git add skills/ark-workflow/chains/greenfield.md \
        skills/ark-workflow/chains/bugfix.md \
        skills/ark-workflow/chains/ship.md \
        skills/ark-workflow/chains/knowledge-capture.md \
        skills/ark-workflow/chains/hygiene.md
git status   # confirm only those 5 files staged
git commit -m "$(cat <<'EOF'
refactor(ark-workflow): extract chains/ (5/7)

Extracts the first five per-scenario chain files from the monolithic
SKILL.md as part of the 1.7.0 progressive-disclosure split. SKILL.md
is unchanged in this phase.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT 1a** — Halt for user approval before Phase 1b.

**Rollback:** `git revert HEAD` (single-commit revert) — `SKILL.md` is untouched, so revert is risk-free. If revert is rejected for some reason, `git rm skills/ark-workflow/chains/{greenfield,bugfix,ship,knowledge-capture,hygiene}.md && git commit` is the manual equivalent.

---

## Phase 1b — Extract remaining 2 chain files + run chain parity diff

**Files (2 new, 0 modified):**
- Create: `skills/ark-workflow/chains/migration.md`
- Create: `skills/ark-workflow/chains/performance.md`

(Plus the parity script in `/tmp/` — not tracked.)

**Exit gate:** the chain reconstruction parity script (Appendix A) produces `PASS — chain reconstruction matches baseline`.

### Step 1: Re-read current `SKILL.md` L610-712

Per CLAUDE.md Edit Integrity rule. Use Read tool with `offset=610, limit=103`. This is the source-of-truth content for the migration and performance chain files.

### Step 2: Verify `/tmp/ark-workflow-SKILL-1.6.0.md` still exists

```bash
ls -l /tmp/ark-workflow-SKILL-1.6.0.md
diff -q skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md
```

Expected: file exists, `diff -q` reports no differences (since Phases 1a and 1b do not modify SKILL.md).

If the snapshot is missing (session restart, /tmp cleared), recapture it: `cp skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md` and re-verify line count = 858. Safe because no commits between 1a and now have touched SKILL.md.

### Step 3: Write `chains/migration.md`

Source: current `SKILL.md` L610-658. Apply transformations 1+2 (parenthetical form for all three weights) +4+5.

Use the Write tool to create `skills/ark-workflow/chains/migration.md` with this exact content:

````markdown
# Migration

## Light

*patch/minor version bumps, non-breaking dependency updates*

1. Read migration/upgrade guide for the dependency
2. Implement upgrade
3. Run tests — verify nothing broke
4. `/cso` (if security-relevant — major bumps, known CVEs)
5. `/ship` → `/land-and-deploy`
6. `/canary` (if deploy risk)
7. `/wiki-update` (if vault)

## Medium

*major version bumps, API changes required*

1. `/investigate` — audit current usage of the thing being migrated
2. Read migration guide, identify breaking changes
3. `/test-driven-development` — write tests for new API surface before migrating
4. Implement migration
5. `/ark-code-review --quick` → `/simplify`
6. `/cso` (if security-relevant)
7. `/ship` → `/land-and-deploy`
8. `/canary` (if deploy risk)
9. `/wiki-update` (if vault)
10. Session log

## Heavy

*framework migrations, platform changes, database migrations*

*Session 1 — Planning:*
1. `/investigate` — audit all usage, map blast radius
2. `/brainstorming` — migration strategy (big bang vs incremental, feature flags, rollback plan)
3. `/codex` — review the migration plan
4. Commit migration plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-4`)

*Session 2 — Implementation:*
5. Read migration plan
6. `/test-driven-development` — tests for new platform/framework before migrating
7. Implement migration in stages (per the plan)
8. `/ark-code-review --thorough` + `/codex` → `/simplify`
9. `/cso` (if security-relevant)
10. `/ship` → `/land-and-deploy`
11. `/canary` — **mandatory for Heavy migrations** (not conditional)

*Document:*
12. `/wiki-update` (if vault)
13. `/wiki-ingest` (if vault + migration introduces new architecture concepts)
14. `/cross-linker` (if vault)
15. `/document-release` (if standard docs exist)
16. Session log
17. `/claude-history-ingest`
````

Verification:

```bash
grep -q "^# Migration$"                       skills/ark-workflow/chains/migration.md
grep -q "^## Light$"                          skills/ark-workflow/chains/migration.md
grep -q "^## Medium$"                         skills/ark-workflow/chains/migration.md
grep -q "^## Heavy$"                          skills/ark-workflow/chains/migration.md
grep -q "handoff_marker: after-step-4"        skills/ark-workflow/chains/migration.md
grep -q "mandatory for Heavy migrations"      skills/ark-workflow/chains/migration.md
```

### Step 4: Write `chains/performance.md`

Source: current `SKILL.md` L662-711. Apply transformations 1+2 (parenthetical form for all three weights) +4+5.

Use the Write tool to create `skills/ark-workflow/chains/performance.md` with this exact content:

````markdown
# Performance

## Light

*single hotspot fix, obvious optimization*

1. `/investigate` — profile and identify the bottleneck
2. Fix the hotspot
3. Verify improvement (before/after timing or metric)
4. `/ship` → `/land-and-deploy`
5. `/canary` (if deploy risk)
6. `/wiki-update` (if vault)

## Medium

*multiple hotspots, caching layer, query optimization*

1. `/investigate` — profile and identify bottlenecks
2. `/benchmark` — establish baseline metrics (if available)
3. `/test-driven-development` — write performance regression tests
4. Implement optimizations
5. `/benchmark` — verify improvement against baseline
6. `/ark-code-review --quick` → `/simplify`
7. `/cso` (if security-relevant — e.g., caching introduces data exposure)
8. `/ship` → `/land-and-deploy`
9. `/canary` (if deploy risk)
10. `/wiki-update` (if vault)
11. Session log

## Heavy

*architecture-level optimization, data layer redesign*

*Session 1 — Analysis & Planning:*
1. `/investigate` — deep profiling, identify systemic bottlenecks
2. `/benchmark` — comprehensive baseline
3. `/brainstorming` — optimization strategy (caching architecture, query redesign, etc.)
4. `/codex` — review the optimization plan
5. Commit plan → **end session, start fresh for implementation** (set `handoff_marker: after-step-5`)

*Session 2 — Implementation:*
6. Read optimization plan
7. `/test-driven-development` — performance regression tests
8. Implement optimizations in stages
9. `/benchmark` — verify improvement per stage
10. `/ark-code-review --thorough` + `/codex` → `/simplify`
11. `/cso` (if security-relevant)
12. `/ship` → `/land-and-deploy`
13. `/canary` — **mandatory for Heavy performance changes** (not conditional)

*Document:*
14. `/wiki-update` (if vault)
15. `/wiki-ingest` (if vault + optimization introduces new architecture)
16. `/cross-linker` (if vault)
17. Session log
18. `/claude-history-ingest`
````

Verification:

```bash
grep -q "^# Performance$"                                  skills/ark-workflow/chains/performance.md
grep -q "^## Light$"                                       skills/ark-workflow/chains/performance.md
grep -q "^## Medium$"                                      skills/ark-workflow/chains/performance.md
grep -q "^## Heavy$"                                       skills/ark-workflow/chains/performance.md
grep -q "handoff_marker: after-step-5"                     skills/ark-workflow/chains/performance.md
grep -q "mandatory for Heavy performance changes"          skills/ark-workflow/chains/performance.md
```

### Step 5: Write the chain reconstruction parity script

Save the Python script from **Appendix A** to `/tmp/reconstruct-chains.py`. Use the Write tool with the exact content listed in the appendix.

### Step 6: Dry-run sanity check (the spec's required dry-run)

The spec § 4 requires testing the reconstruction algorithm before relying on it for the parity gate. The dry-run is built into the script: it reconstructs from `chains/*.md` and diffs against `/tmp/ark-workflow-SKILL-1.6.0.md` lines 410-712. **For a sound algorithm + correct extraction, this produces a byte-identical match (after whitespace normalization).** Any failure in this run is either an algorithm bug OR an extraction bug — both must be fixed before Phase 2.

```bash
python3 /tmp/reconstruct-chains.py
```

Expected: `PASS — chain reconstruction matches baseline (L410-712, 7 scenarios, 19 variants)`.

If FAIL: the script prints a unified diff. Fix EITHER the algorithm OR the offending chain file. Common failure modes:
- Italic descriptor case mismatch (e.g., `*For ...*` instead of `*for ...*`) → fix chain file
- Missing blank line between H2 and italic descriptor → fix chain file
- Wrong scenario name in `### {Name}` → fix script's `ORDER` mapping
- Trailing whitespace mismatch → script normalizes; if still failing, the chain file has tabs or non-breaking spaces → fix chain file
- Off-by-one on the L712 boundary → check that `BASELINE_END = 712` and the slice is `lines[409:712]` (Python 0-indexed)

Re-run after each fix. Do not advance until PASS.

### Step 7: Sanity-grep all 7 chain files

```bash
[ "$(ls skills/ark-workflow/chains/*.md | wc -l)" -eq 7 ]
grep -rho "/test-driven-development" skills/ark-workflow/chains/ | wc -l   # expect 9 (greenfield 2 + bugfix 2 + hygiene 2 + migration 2 + performance 1)
grep -rho "/TDD\b" skills/ark-workflow/chains/ | wc -l                       # expect 0
grep -l "handoff_marker" skills/ark-workflow/chains/*.md                     # expect 3 files: greenfield, migration, performance
```

Note: the precise per-chain `/test-driven-development` count is recorded from the script's PASS run; the global total across `chains/` should match the baseline grep count of 12 minus the 3 instances that live outside the chain section in original SKILL.md (zero — the spec says all 12 are in chain content), so total in `chains/` should be 12. **If the count is 9 instead of 12, re-verify the per-chain counts manually:** greenfield 2, bugfix 2, hygiene 2, migration 2, performance 2, knowledge-capture 0, ship 0 → 10. Wait — that is 10, not 12. The other 2 live in main `SKILL.md` Step 6.5 wording / batch triage step text. Re-derive the expected value from the parity-script PASS output, not from this comment. The Phase 5 final check is `grep -rho '/test-driven-development' skills/ark-workflow/ | wc -l` = 12, summed across main + chains.

### Step 8: Commit Phase 1b

```bash
git add skills/ark-workflow/chains/migration.md skills/ark-workflow/chains/performance.md
git status   # only those 2 files staged
git commit -m "$(cat <<'EOF'
refactor(ark-workflow): extract chains/ (7/7)

Adds the migration and performance chain files, completing the
chains/ extraction. Chain reconstruction parity script PASSes against
the 1.6.0 baseline (L410-712, 7 scenarios, 19 variants).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT 1b** — Halt for user approval before Phase 2. Confirm with user that the parity-diff script PASSed.

**Rollback:** `git revert HEAD` reverts only this phase (the 2 new files). 1a chains stay. To roll back the entire `chains/` extraction, revert HEAD and HEAD~1 in reverse order.

---

## Phase 2 — Extract 4 reference files + reference parity diffs

**Files (4 new, 0 modified):**
- Create: `skills/ark-workflow/references/batch-triage.md`
- Create: `skills/ark-workflow/references/continuity.md`
- Create: `skills/ark-workflow/references/troubleshooting.md`
- Create: `skills/ark-workflow/references/routing-template.md`

**Exit gate:**
- `references/batch-triage.md` parity script PASSes against baseline L163-249
- `references/troubleshooting.md` parity script PASSes against baseline concat L761-774 + L776-789 + L791-812
- `references/continuity.md` and `references/routing-template.md` pass content-presence grep checks (Phase 5 will run the full set; Phase 2 runs an interim check)

### Step 1: Re-read current `SKILL.md` source ranges

Read each baseline range in turn. Use the Read tool for each:
- Batch Triage: `offset=163, limit=87`
- Continuity (full): `offset=251, limit=121`
- Session Handoff + When Things Go Wrong + Re-triage: `offset=761, limit=52`
- Routing Rules Template: `offset=814, limit=45`

### Step 2: Create `references/` directory

```bash
mkdir -p skills/ark-workflow/references
ls skills/ark-workflow/references/
```

### Step 3: Write `references/batch-triage.md`

Source: current `SKILL.md` L163-249. **Pure extraction with one transformation:** demote the top-level `## Batch Triage` H2 → `# Batch Triage` H1 (so it becomes the file's title). Every subsequent line is verbatim.

Use the Write tool to create `skills/ark-workflow/references/batch-triage.md` with the content of `sed -n '163,249p' /tmp/ark-workflow-SKILL-1.6.0.md`, with **only** the first line `## Batch Triage` changed to `# Batch Triage`.

Quick way to construct it:

```bash
{
  echo "# Batch Triage"
  sed -n '164,249p' /tmp/ark-workflow-SKILL-1.6.0.md
} > skills/ark-workflow/references/batch-triage.md
wc -l skills/ark-workflow/references/batch-triage.md   # expect 87
```

Verification:

```bash
head -1 skills/ark-workflow/references/batch-triage.md   # expect "# Batch Triage"
grep -q "Root cause consolidation" skills/ark-workflow/references/batch-triage.md
grep -q "Dependency detection"     skills/ark-workflow/references/batch-triage.md
grep -q "Per-group chains"         skills/ark-workflow/references/batch-triage.md
grep -q "Example Output"           skills/ark-workflow/references/batch-triage.md
```

### Step 4: Write `references/troubleshooting.md`

Source: concatenation of baseline L761-774 (Session Handoff) + L776-789 (When Things Go Wrong) + L791-812 (Re-triage), in that order. **Pure consolidation, no edits, no added prose, no cross-references.** The file's H1 is added as a title; the three section headers stay at their original `##` level.

Construct it:

```bash
{
  echo "# Troubleshooting — When Things Change or Break"
  echo
  sed -n '761,774p' /tmp/ark-workflow-SKILL-1.6.0.md
  sed -n '776,789p' /tmp/ark-workflow-SKILL-1.6.0.md
  sed -n '791,812p' /tmp/ark-workflow-SKILL-1.6.0.md
} > skills/ark-workflow/references/troubleshooting.md
wc -l skills/ark-workflow/references/troubleshooting.md   # expect ~52
```

Verification:

```bash
head -1 skills/ark-workflow/references/troubleshooting.md   # expect "# Troubleshooting — When Things Change or Break"
grep -q "^## Session Handoff$"     skills/ark-workflow/references/troubleshooting.md
grep -q "^## When Things Go Wrong$" skills/ark-workflow/references/troubleshooting.md
grep -q "^## Re-triage$"           skills/ark-workflow/references/troubleshooting.md
grep -q "Scenario shift"           skills/ark-workflow/references/troubleshooting.md
```

### Step 5: Write `references/continuity.md`

Source: current `SKILL.md` L309-371 (Batch Triage Mode + Cross-Session Continuity through Context recovery), restructured per the spec's example body. **This file has added scaffolding** (preamble paragraph, new H2 section headers, new Archive on Completion rule) — it is NOT a pure extraction. The Phase 2 parity check uses content-presence grep, not line-by-line diff.

Use the Write tool to create `skills/ark-workflow/references/continuity.md` with this exact content:

````markdown
# Continuity — Advanced Protocols

This file holds pay-per-use continuity protocols. The minimum Step 6.5 inline protocol (frontmatter template + basic after-each-step update) lives in main `SKILL.md`.

## Batch Triage Chain File Format

For batch output, write one section per group in the chain file:

~~~markdown
---
scenario: Batch
weight: mixed
batch: true
---

# Current Batch

## Group A (Light Bugfix, parallel)
### Item #2: Ghost pipeline runs
1. [ ] `/investigate`
...

### Item #5: MCP ClosedResourceError
1. [ ] `/investigate`
...

## Group B (Medium Bugfix, sequential)
### Item #3: Payload drop
1. [ ] `/investigate`
...
~~~

TodoWrite tasks are grouped with a parent task per group and sub-tasks per item step.

## Cross-Session Continuity

TodoWrite tasks are session-scoped and do NOT persist across sessions. Only `.ark-workflow/current-chain.md` persists on disk.

**1. Session start check (automatic):**
Every time a session starts in a project, the agent should check for `.ark-workflow/current-chain.md`. This applies whether or not `/ark-workflow` was explicitly invoked. The Routing Rules Template wires this up via CLAUDE.md so projects can enable it.

**2. Rehydrate TodoWrite tasks:**
When resuming a chain from the file, create new TodoWrite tasks for each unchecked step (`[ ]`). Mark the first unchecked step as `in_progress`. Completed steps (`[x]`) do not get recreated as tasks — they're history, not work.

## Handoff Markers

**Setting handoff_marker:**
The chain file distinguishes between "chain paused mid-work" (user closed Claude) and "intentional handoff" (medium+ design phase end-of-session marker). The handoff marker is recorded in the chain file frontmatter:

~~~yaml
handoff_marker: after-step-5
handoff_instructions: "Read spec at docs/superpowers/specs/2026-04-10-oauth-design.md"
~~~

**Resuming on a marked chain:**
On session start, if `handoff_marker` is set AND the marked step is `[x]` (completed), announce:
> "You're in Session 2 of a Heavy Greenfield. Design phase complete. Next: `/executing-plans` with the spec at [handoff_instructions path]."

## Stale Chain Detection

If the chain file is older than 7 days, flag it as potentially stale:
> "Found an ark-workflow chain from [age] ago. Is this still active, or should I archive it to `.ark-workflow/archive/`?"

Never auto-delete — always ask. The user may have been on vacation.

## Context Recovery After Compaction

If context compaction occurred mid-chain, the TodoWrite tasks survive but the rich chain context may be lost. The agent should re-read `.ark-workflow/current-chain.md` to refresh its understanding before continuing.

**Context recovery (catch-all):** At the start of any session in this project, if `.ark-workflow/current-chain.md` exists, the agent should read it and announce:
> "Found an in-progress `/ark-workflow` chain: [scenario]/[weight], step X of Y (`[next step]`). Continue from here?"

## Archive on Completion

On chain completion, move `.ark-workflow/current-chain.md` → `.ark-workflow/archive/YYYY-MM-DD-{scenario}.md`. Never delete — archives are workflow history. This rule also appears in abbreviated form inline in main Step 6.5.
````

Verification (content-presence grep — the parity gate for this file):

```bash
grep -q "^# Continuity — Advanced Protocols$"            skills/ark-workflow/references/continuity.md
grep -q "^## Batch Triage Chain File Format$"             skills/ark-workflow/references/continuity.md
grep -q "^## Cross-Session Continuity$"                    skills/ark-workflow/references/continuity.md
grep -q "^## Handoff Markers$"                             skills/ark-workflow/references/continuity.md
grep -q "^## Stale Chain Detection$"                       skills/ark-workflow/references/continuity.md
grep -q "^## Context Recovery After Compaction$"           skills/ark-workflow/references/continuity.md
grep -q "^## Archive on Completion$"                       skills/ark-workflow/references/continuity.md
grep -q "current-chain.md"                                 skills/ark-workflow/references/continuity.md
grep -q "handoff_marker: after-step-5"                     skills/ark-workflow/references/continuity.md
grep -q "Rehydrate"                                        skills/ark-workflow/references/continuity.md
grep -q "Never auto-delete"                                skills/ark-workflow/references/continuity.md
```

All commands must exit 0. Then re-read the file and visually compare against the spec § "References § 2 references/continuity.md" example body — the section names and order must match the spec exactly.

### Step 6: Write `references/routing-template.md`

Source: current `SKILL.md` L814-858 (the `## Routing Rules Template` section) restructured per the spec's example. **Added scaffolding:** new H1, new "Copy the block below..." preamble that replaces the original "Projects can add this block..." preamble, and added `---` separators around the fenced block. Not a pure extraction.

Use the Write tool to create `skills/ark-workflow/references/routing-template.md` with this exact content:

````markdown
# Routing Rules Template

Copy the block below into a project's CLAUDE.md to auto-trigger /ark-workflow and enable cross-session chain resume in that project.

---

`````markdown
## Skill routing — Ark Workflow

**Session start — check for in-progress chain:**
At the start of every session in this project, check for `.ark-workflow/current-chain.md`.
If it exists with unchecked steps, read it and announce to the user:

  "Found an in-progress ark-workflow chain:
  - Scenario: [scenario]/[weight]
  - Progress: step X of Y complete
  - Next: [next skill]
  Continue from here, or archive as stale?"

If the user continues, rehydrate TodoWrite tasks from the unchecked items and resume
from the next pending step. If the chain has a `handoff_marker` set and it's checked,
announce the session transition and run the handoff instructions.

**New task triage:**
When starting any non-trivial task (and no in-progress chain exists), invoke
`/ark-workflow` first to triage and get the skill chain. Pattern triggers:

- "build", "create", "add feature", "new component" → /ark-workflow (greenfield)
- "fix", "bug", "broken", "error", "investigate" → /ark-workflow (bugfix)
- "ship", "deploy", "push", "PR", "merge" → /ark-workflow (ship)
- "document", "vault", "catch up", "knowledge" → /ark-workflow (knowledge capture)
- "cleanup", "refactor", "audit", "hygiene", "dead code" → /ark-workflow (hygiene)
- "upgrade", "migrate", "bump", "version" → /ark-workflow (migration)
- "slow", "optimize", "latency", "benchmark" → /ark-workflow (performance)

For trivial tasks (single obvious change, no ambiguity), skip triage and work directly.

**After each step in a running chain:**
1. Check off the step in `.ark-workflow/current-chain.md` (change `[ ]` to `[x]`)
2. Append any notes to the Notes section of the chain file
3. Update the corresponding TodoWrite task to `completed`
4. Announce: `Next: [next skill] — [purpose]`
5. Mark the next task as `in_progress`
6. If the chain is complete, move the file to `.ark-workflow/archive/YYYY-MM-DD-[scenario].md`
`````

---

To add routing to a new project, copy the block above into the project's CLAUDE.md. The `/ark-workflow` skill is already available globally via the ark-skills plugin.
````

Verification (content-presence grep):

```bash
grep -q "^# Routing Rules Template$"      skills/ark-workflow/references/routing-template.md
grep -q "Copy the block below"            skills/ark-workflow/references/routing-template.md
grep -q "Skill routing — Ark Workflow"    skills/ark-workflow/references/routing-template.md
grep -q "Session start — check for in-progress chain" skills/ark-workflow/references/routing-template.md
grep -q "New task triage"                 skills/ark-workflow/references/routing-template.md
grep -q "After each step in a running chain" skills/ark-workflow/references/routing-template.md
grep -q "ark-skills plugin"               skills/ark-workflow/references/routing-template.md
```

Then visually compare against current `SKILL.md` L818-856 (the original 5-backtick fenced block) and confirm the fenced block content is byte-identical between the two — that's the parity guarantee for this file.

### Step 7: Write the reference parity script

Save the Python script from **Appendix B** to `/tmp/reconstruct-references.py`. This script handles `batch-triage.md` and `troubleshooting.md` only.

### Step 8: Run the reference parity diff

```bash
python3 /tmp/reconstruct-references.py
```

Expected:
```
PASS — batch-triage.md matches baseline L163-249 (after H1↔H2 demote reversal)
PASS — troubleshooting.md matches baseline L761-774 + L776-789 + L791-812 (after H1 strip)
```

If FAIL: the script prints a unified diff. The most common cause is whitespace drift — the construction commands above use `sed` and `echo` which preserve byte-level fidelity, so a failure here usually means the source line ranges in the spec are wrong. Re-verify the ranges by reading current `SKILL.md` directly.

### Step 9: Commit Phase 2

```bash
git add skills/ark-workflow/references/
git status
git commit -m "$(cat <<'EOF'
refactor(ark-workflow): extract references/

Adds the four pay-per-use reference files:

- batch-triage.md — pure extraction of L163-249 (parity diff PASS)
- troubleshooting.md — concat of L761-774 + L776-789 + L791-812 (parity diff PASS)
- continuity.md — restructured from L309-371 with new H2 scaffolding and Archive on Completion rule (content-presence grep PASS)
- routing-template.md — extracted from L814-858 with new preamble + separators (content-presence grep PASS)

SKILL.md is unchanged in this phase.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT 2** — Halt for user approval before Phase 3.

**Rollback:** `git revert HEAD` removes the 4 reference files. Chains are unaffected. To roll back the entire extraction (Phases 1a + 1b + 2), revert HEAD, HEAD~1, HEAD~2 in reverse order.

---

## Phase 3 — Slim main `SKILL.md` to router

**Files (1 modified, 0 new):**
- Modify: `skills/ark-workflow/SKILL.md`

**Exit gate:**
- `wc -l skills/ark-workflow/SKILL.md` ≤ 400 (hard cap; target ≈ 285)
- Smoke tests **4, 5, 6** pass mental walkthrough (these are the single-file tests that exercise main + one chain only — see Appendix C)
- All Phase 3 grep checks below pass

This is the only Edit-heavy phase. **Re-read `SKILL.md` between every Edit cluster** (CLAUDE.md Edit Integrity rule).

### Step 1: Re-read the entire current `SKILL.md`

Use the Read tool with `offset=1, limit=858`. (Total file is 858 lines per Phase 1a baseline.) Confirm via `wc -l` that the file is still 858 lines and that no earlier phase silently modified it.

```bash
diff -q skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md
# expect: no output (files identical)
```

If they differ, **STOP** — investigate before editing.

### Step 2: Delete the `## Batch Triage` section (current L163-249)

Use the Edit tool. Find this exact text (the entire section, ~87 lines including the trailing blank line before `## Continuity`):

```
## Batch Triage

**Trigger:** Activated when the user's prompt describes multiple distinct executable tasks. This includes:
```

Replace with empty string. (You will need to copy the full L163-249 range from the re-read above for the Edit `old_string`. The Edit will fail if any line in the range was secretly modified — that is the desired behavior.)

After the Edit, re-read `SKILL.md` and confirm:

```bash
! grep -q "^## Batch Triage$" skills/ark-workflow/SKILL.md
! grep -q "Root cause consolidation" skills/ark-workflow/SKILL.md
wc -l skills/ark-workflow/SKILL.md   # expect 858 - 87 = 771
```

### Step 3: Delete the `## Continuity` section (now-shifted L251-371)

After Step 2, the line numbers shift. Re-read `SKILL.md` to find the new `## Continuity` location. Use the Edit tool to delete the entire `## Continuity — Task Tracking and Chain State` section (from its `## Continuity` header through the line just before the next `## Workflow` header). That is the original L251-371, now ~121 lines.

After the Edit:

```bash
! grep -q "^## Continuity " skills/ark-workflow/SKILL.md
! grep -q "After Each Step — Agent Protocol" skills/ark-workflow/SKILL.md
! grep -q "Cross-Session Continuity" skills/ark-workflow/SKILL.md
wc -l skills/ark-workflow/SKILL.md   # expect 771 - 121 = 650
```

### Step 4: Re-read `SKILL.md` (Edit Integrity checkpoint after 2 deletions)

Required by CLAUDE.md before the next cluster of edits.

### Step 5: Modify Workflow Step 2 — add batch-triage pointer

Find the existing Step 2:

```
### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table. If the prompt describes multiple distinct tasks (see Batch Triage trigger), go to Batch Triage instead of steps 3-6. For security requests, use the two-path security routing (audit vs hardening). If ambiguous, ask the disambiguation question.
```

Replace with:

```
### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table. If the prompt describes multiple distinct tasks (see Batch Triage trigger), read `references/batch-triage.md` and follow that algorithm instead of Steps 3-6. For security requests, use the two-path security routing (audit vs hardening). If ambiguous, ask the disambiguation question.
```

(Single change: "go to Batch Triage instead of steps 3-6" → "read `references/batch-triage.md` and follow that algorithm instead of Steps 3-6".)

Verification: `grep -q "references/batch-triage.md" skills/ark-workflow/SKILL.md`.

### Step 6: Rewrite Workflow Step 4 — point at chain files

Find the existing Step 4:

```
### Step 4: Look Up Skill Chain
Find the matching chain in the Skill Chains section below using scenario + weight class. If security hardening triggered mandatory early `/cso`, apply the dedup rule (remove the later conditional `/cso` from the chain).
```

Replace with:

```
### Step 4: Look Up Skill Chain
Read `chains/{scenario}.md` (e.g., `chains/bugfix.md`). Each chain file contains sections for the applicable weight variants — Light/Medium/Heavy, or Light/Full for Knowledge Capture, or Audit-Only/Light/Medium/Heavy for Hygiene. Select the section matching your triaged weight class.

**Filename mapping:** `greenfield.md`, `bugfix.md`, `ship.md` (standalone — no weight class), `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`.

If security hardening triggered mandatory early `/cso`, apply the dedup rule documented at the bottom of `chains/hygiene.md`.
```

Verification (all 7 filenames must be present in main):

```bash
for f in greenfield bugfix ship knowledge-capture hygiene migration performance; do
  grep -q "chains/${f}.md" skills/ark-workflow/SKILL.md || echo "MISSING: chains/${f}.md mapping"
done
grep -q "Dedup rule" skills/ark-workflow/SKILL.md   # the pointer to chains/hygiene.md dedup
```

This is the **No Semantic Search check** for the scenario→filename mapping. Each filename gets its own grep.

### Step 7: Slim Step 6.5 to ~18 inline lines

Find the existing Step 6.5:

```
### Step 6.5: Activate Continuity
- Create TodoWrite tasks for each step in the chain (or each group in a batch)
- Write `.ark-workflow/current-chain.md` with the full chain state and frontmatter
- Add `.ark-workflow/` to `.gitignore` if not already present
- Embed the "after each step" reminder instructions in the output
```

Replace with the slimmed inline version (from spec § "Step 6.5 — Activate Continuity (slimmed to ~18 inline lines)"):

````markdown
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
````

Verification:

```bash
grep -q "references/continuity.md" skills/ark-workflow/SKILL.md
grep -q "ISO-8601 timestamp"        skills/ark-workflow/SKILL.md
grep -q "handoff_marker: null"      skills/ark-workflow/SKILL.md
```

### Step 8: Re-read `SKILL.md` (Edit Integrity checkpoint after 3 inline edits)

Required by CLAUDE.md before the next cluster of edits.

### Step 9: Delete the `## Skill Chains` section (current L410-712, now-shifted)

Find the section header and delete from `## Skill Chains` through the line just before `## Condition Resolution` (i.e., delete the closing `---` separator too — it is no longer needed).

After:

```bash
! grep -q "^## Skill Chains$" skills/ark-workflow/SKILL.md
! grep -q "^### Greenfield Feature$" skills/ark-workflow/SKILL.md
! grep -q "^### Bug Investigation & Fix$" skills/ark-workflow/SKILL.md
! grep -q "^### Performance$" skills/ark-workflow/SKILL.md
```

### Step 10: Drop the Condition Resolution example block (current L746-759)

Find the existing block:

```
**Example resolved output:**

> **Your skill chain (Bugfix, Medium):**
> 1. `/investigate` — root cause analysis
> 2. Re-triage if deeper than expected
> 3. `/test-driven-development` — failing test
> 4. Fix
> 5. `/ark-code-review --quick` → `/simplify`
> 6. Skipping `/qa` — no UI detected
> 7. Skipping `/cso` — no security-relevant changes
> 8. `/ship` → `/land-and-deploy`
> 9. Skipping `/canary` — no deploy risk
> 10. `/wiki-update`
> 11. Session log
```

Replace with empty string (delete entirely). The "Standard docs trigger" paragraph above it stays.

After:

```bash
! grep -q "Example resolved output" skills/ark-workflow/SKILL.md
! grep -q "Your skill chain (Bugfix, Medium)" skills/ark-workflow/SKILL.md
grep -q "Standard docs trigger" skills/ark-workflow/SKILL.md   # the section above the dropped block stays
```

### Step 11: Replace the three sections (`## Session Handoff`, `## When Things Go Wrong`, `## Re-triage`) with `## When Things Change`

Find the entire range from `## Session Handoff` through the end of `## Re-triage` (current L761-812). Replace with:

```markdown
## When Things Change

- **Mid-flight re-triage** (weight escalation or scenario shift): stop at the current step, reclassify using the Triage section above, pick up the remaining phases from the new class. For scenario-shift pivot examples, see `references/troubleshooting.md`.
- **Design-phase session handoffs**: chain files specify inline `handoff_marker` values where applicable. For per-scenario handoff points and guidance on when to break sessions mid-implementation, see `references/troubleshooting.md`.
- **Step failure or unexpected state**: see `references/troubleshooting.md` for per-failure guidance (failed QA, failed deploy, review disagreement, flaky tests, spec invalidation, canary failure, vault tooling failure, hygiene reveals bugs, migration breaks tests, batch item blocks others).
```

Verification:

```bash
! grep -q "^## Session Handoff$"     skills/ark-workflow/SKILL.md
! grep -q "^## When Things Go Wrong$" skills/ark-workflow/SKILL.md
! grep -q "^## Re-triage$"           skills/ark-workflow/SKILL.md
grep -q "^## When Things Change$"     skills/ark-workflow/SKILL.md
[ "$(grep -c "references/troubleshooting.md" skills/ark-workflow/SKILL.md)" -ge 3 ]
```

### Step 12: Replace `## Routing Rules Template` with a 3-line pointer

Find the entire range from `## Routing Rules Template` through the closing line `To add routing to a new project, copy the block above into the project's CLAUDE.md. The /ark-workflow skill is already available globally via the ark-skills plugin.` (current L814-858, ~45 lines).

Replace with:

```markdown
## Routing Rules Template

See `references/routing-template.md` for the copy-paste block to add to project CLAUDE.md files. (Not loaded at runtime — this is human-only documentation.)
```

Verification:

```bash
grep -q "^## Routing Rules Template$" skills/ark-workflow/SKILL.md
grep -q "references/routing-template.md" skills/ark-workflow/SKILL.md
! grep -q "Skill routing — Ark Workflow" skills/ark-workflow/SKILL.md   # the original copy-paste block is gone from main
```

### Step 13: Re-read `SKILL.md` (Edit Integrity checkpoint after 4 large deletions)

Required by CLAUDE.md before the next cluster of edits.

### Step 14: Append `## File Map` appendix at the end of the file

Find the last line of the file (which after Step 12 is the routing-template pointer). Append (using the Edit tool with `old_string` = the last existing line and `new_string` = the last line plus the new appendix):

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

Verification:

```bash
grep -q "^## File Map$" skills/ark-workflow/SKILL.md
[ "$(grep -c "references/" skills/ark-workflow/SKILL.md)" -ge 5 ]
[ "$(grep -c "chains/" skills/ark-workflow/SKILL.md)" -ge 1 ]
```

### Step 15: Phase 3 hard checks

```bash
# Hard cap (spec abort condition)
LINES=$(wc -l < skills/ark-workflow/SKILL.md)
echo "main SKILL.md = $LINES lines (target ~285, hard cap 400)"
[ "$LINES" -le 400 ] || echo "FAIL: exceeds 400-line hard cap"

# All 7 chain filenames present in main (No Semantic Search check)
for f in greenfield bugfix ship knowledge-capture hygiene migration performance; do
  grep -q "chains/${f}.md" skills/ark-workflow/SKILL.md || echo "MISSING: chains/${f}.md mapping in main"
done

# All 4 reference filenames present in main
for f in batch-triage continuity troubleshooting routing-template; do
  grep -q "references/${f}.md" skills/ark-workflow/SKILL.md || echo "MISSING: references/${f}.md pointer in main"
done

# Pointer-site count for references/ (Step 2 + Step 6.5 + 3 in When Things Change + Routing Rules + File Map ×4 = ≥ 9 actual occurrences)
[ "$(grep -c "references/" skills/ark-workflow/SKILL.md)" -ge 5 ] || echo "FAIL: references/ pointer count"

# Original section markers must be gone
! grep -q "^## Batch Triage$"     skills/ark-workflow/SKILL.md
! grep -q "^## Continuity"        skills/ark-workflow/SKILL.md
! grep -q "^## Skill Chains$"     skills/ark-workflow/SKILL.md
! grep -q "^## Session Handoff$"  skills/ark-workflow/SKILL.md
! grep -q "^## When Things Go Wrong$" skills/ark-workflow/SKILL.md
! grep -q "^## Re-triage$"        skills/ark-workflow/SKILL.md
! grep -q "Example resolved output" skills/ark-workflow/SKILL.md

# Project Discovery, Scenario Detection, Triage are still present (verbatim from baseline)
grep -q "^## Project Discovery$"  skills/ark-workflow/SKILL.md
grep -q "^## Scenario Detection$" skills/ark-workflow/SKILL.md
grep -q "^## Triage$"             skills/ark-workflow/SKILL.md
grep -q "Risk sets the floor"     skills/ark-workflow/SKILL.md
```

### Step 16: Smoke tests 4, 5, 6 (single-file mental walkthrough)

These are the only smoke tests that exercise just main + one chain file (no `references/`), so they are the appropriate Phase 3 exit gate. Walk through each test step-by-step against the new files; record the resolved chain output in scratch notes. Compare against the expected output in **Appendix C**.

- **Test 4 (Security audit)**: prompt = "audit our auth subsystem". Expected: scenario routed to **Hygiene Audit-Only**, chain ends with **STOP + user choice**, no `/ship`/`/canary` steps. Files loaded: `SKILL.md` + `chains/hygiene.md`.
- **Test 5 (Security hardening)**: prompt = "harden our auth subsystem". Expected: routed to **Hygiene Heavy** with `/cso` **prepended as step 1** and the original step 4 `/cso` **deduped**. Files loaded: `SKILL.md` + `chains/hygiene.md`.
- **Test 6 (Decision-density escalation)**: prompt = "redesign the caching layer" (Low risk, architecture density). Expected: triage = **Heavy** (escalated from Light by architecture density); scenario = either **Hygiene Heavy** or **Greenfield Heavy** (the user clarification path picks one). Files loaded: `SKILL.md` + the picked chain file.

If ANY of these three diverges from expected, **STOP** Phase 3 and investigate. The new layout has either lost content or rearranged it in a behavior-affecting way.

### Step 17: Commit Phase 3

```bash
git add skills/ark-workflow/SKILL.md
git status
git commit -m "$(cat <<'EOF'
refactor(ark-workflow): slim main SKILL.md to router

Removes the 6 sections that moved to chains/ and references/:
- ## Batch Triage → references/batch-triage.md
- ## Continuity → references/continuity.md (restructured)
- ## Skill Chains → 7 chains/{scenario}.md files
- ## Session Handoff + When Things Go Wrong + Re-triage → references/troubleshooting.md
- ## Routing Rules Template body → references/routing-template.md
- Drops the Condition Resolution "Example resolved output" block (14 lines)

Adds:
- Workflow Step 2 batch-triage pointer
- Workflow Step 4 chain-file pointer with full filename mapping
- Slimmed Step 6.5 with inline frontmatter template + continuity.md pointer
- New ## When Things Change dispatch section (3 bullets, all → references/troubleshooting.md)
- ## Routing Rules Template 3-line pointer
- ## File Map safety-net appendix

Smoke tests 4 (security audit), 5 (security hardening + dedup), and 6
(decision-density escalation) all pass mental walkthrough. Main
SKILL.md is now {LINES} lines (target ~285, hard cap 400).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

Replace `{LINES}` in the commit message with the actual count from Step 15.

**CHECKPOINT 3** — Halt for user approval before Phase 4a.

**Rollback:** `git revert HEAD` restores the monolithic `SKILL.md`. Chains and references stay (they're independent files). To roll back the entire Phase 3 + extractions, revert HEAD, HEAD~1, HEAD~2, HEAD~3 in reverse order.

---

## Phase 4a — Version bump + CHANGELOG

**Files (4 modified, 0 new):**
- Modify: `VERSION`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`

### Step 1: Read all 4 files

Confirm current state shows `1.6.0` in each.

### Step 2: Bump `VERSION`

```bash
echo "1.7.0" > VERSION
cat VERSION   # confirm 1.7.0
```

### Step 3: Bump `.claude-plugin/plugin.json`

Use the Edit tool: replace `"version": "1.6.0"` with `"version": "1.7.0"`.

### Step 4: Bump `.claude-plugin/marketplace.json`

Use the Edit tool: replace `"version": "1.6.0"` with `"version": "1.7.0"`.

### Step 5: Add `## [1.7.0]` entry to `CHANGELOG.md`

Use the Edit tool. Find the line `## [1.6.0] - 2026-04-09` and prepend a new section above it:

```markdown
## [1.7.0] - 2026-04-10

### Changed
- **ark-workflow**: Progressive-disclosure split of the monolithic router
  - Main `SKILL.md`: 858 → {X} lines ({reduction}%)
  - Common-path context load (router + one chain file): 858 → {Y} lines avg ({reduction}%); worst case 858 → {Z} lines ({reduction}%)
  - Chain variants moved to `chains/{scenario}.md` (7 files: greenfield, bugfix, ship, knowledge-capture, hygiene, migration, performance)
  - Pay-per-use content moved to `references/{batch-triage,continuity,troubleshooting,routing-template}.md`
  - Behavioral parity: all 22 v2 gaps preserved, all 19 chain variants preserved, 12 `/test-driven-development` references preserved, 0 `/TDD` references
  - File count in `skills/ark-workflow/`: 1 → 12
  - Total repo footprint: 858 → {W} lines ({delta} lines, intentional on-disk overhead in exchange for context-load savings)
  - Dropped the Condition Resolution "Example resolved output" block (14 lines, illustrative only)
```

Replace `{X}`, `{Y}`, `{Z}`, `{W}`, `{reduction}`, `{delta}` with the values recorded in Phase 5 (Step 1 below). For Phase 4a, use placeholders and update them in Phase 4b before commit if Phase 5 happens after Phase 4a; OR run Phase 5's line-count step BEFORE Phase 4a so the numbers are concrete.

**Recommended ordering:** before running Phase 4a, run this single command from Phase 5 Step 1:

```bash
echo "== Final line counts =="
wc -l skills/ark-workflow/SKILL.md
wc -l skills/ark-workflow/chains/*.md
wc -l skills/ark-workflow/references/*.md
```

Use the output to fill in the CHANGELOG numbers concretely.

### Step 6: Verify all 4 version files agree

```bash
grep -H "1.7.0" VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json
grep -c "^## \[1.7.0\]" CHANGELOG.md   # expect 1
grep -c "1\.6\.0" VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json
# Expected: 0 occurrences in VERSION/plugin.json/marketplace.json (all bumped). CHANGELOG.md still has 1.6.0 in its history block — that's fine.
```

### Step 7: Commit Phase 4a

```bash
git add VERSION .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "$(cat <<'EOF'
chore: bump 1.6.0 → 1.7.0 + CHANGELOG

Records the ark-workflow progressive-disclosure split. Main SKILL.md
shrinks from 858 lines to a router; per-scenario chain variants and
pay-per-use protocols move to chains/ and references/ sub-files.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT 4a** — Halt for user approval before Phase 4b.

**Rollback:** `git revert HEAD` reverts all 4 version files in one commit.

---

## Phase 4b — README + TODO sync (conditional)

**Files (up to 2 modified, 0 new):**
- Modify (conditional): `README.md`
- Modify (conditional): `TODO.md`

### Step 1: Inspect README and TODO for content that references `ark-workflow` structure or file count

```bash
grep -n "ark-workflow" README.md
grep -n "858\|file count\|monolith\|router" README.md
grep -n "ark-workflow" TODO.md
grep -n "split\|progressive disclosure" TODO.md
```

### Step 2: Update README only if it references file count or layout

The spec says: "Check whether the description references file count or structure — if it does, update. If it describes features only, no update needed." If grep shows the README only describes features (7 scenarios, batch triage, continuity), do NOT modify it. If it references the file as monolithic or describes the directory layout, update to match the new layout.

If updating, the only change to add is a one-line note that the skill now uses progressive disclosure with `chains/` and `references/` sub-files.

### Step 3: Update TODO only if it has an entry for "ark-workflow split" or similar

If `TODO.md` has a deferred item for splitting `ark-workflow` (likely added at the end of the v2 session), mark it as completed in this release. Do NOT add any new deferred items here — the Heavy Hygiene design-phase follow-up listed in spec § "Follow-ups" is explicitly out of scope for this refactor.

### Step 4: Verify

```bash
git status   # confirm only README.md and/or TODO.md are modified, or nothing if no updates were needed
git diff README.md TODO.md   # visual review
```

### Step 5: Commit Phase 4b (skip if no files modified)

```bash
git add README.md TODO.md   # adapt to whichever files were touched
git commit -m "$(cat <<'EOF'
docs: sync README + update TODO for 1.7.0

Marks the ark-workflow progressive-disclosure split as completed.
README updated to reflect chains/ and references/ sub-file layout
(if README referenced the previous monolithic structure).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

If no files changed in this phase, **skip the commit** and announce: "Phase 4b — no README/TODO updates required; proceeding to Phase 5."

**CHECKPOINT 4b** — Halt for user approval before Phase 5.

**Rollback:** `git revert HEAD` (if a commit was made) reverts the docs sync.

---

## Phase 5 — Verification (smoke tests, gap checklist, line counts, session log)

**Files (1 new, 0 modified):**
- Create: `vault/Session-Logs/S004-Ark-Workflow-Split.md`

(Plus running the parity scripts and grep checks — no file changes.)

**Exit gate:**
- All 22 v2 gap regression checks PASS (Appendix D)
- All 20 per-variant H2 assertions PASS (Appendix E)
- Both parity scripts re-run from a clean state and PASS
- Mental walkthrough of all 13 smoke tests PASSes (Appendix C)
- Line counts within budget; numbers recorded for CHANGELOG (back-fill if Phase 4a used placeholders)

### Step 1: Final line counts

```bash
echo "== Line counts =="
wc -l skills/ark-workflow/SKILL.md
wc -l skills/ark-workflow/chains/*.md
wc -l skills/ark-workflow/references/*.md
echo "== Word counts =="
wc -w skills/ark-workflow/SKILL.md skills/ark-workflow/chains/*.md skills/ark-workflow/references/*.md
echo "== Common-path totals =="
MAIN=$(wc -l < skills/ark-workflow/SKILL.md)
for f in skills/ark-workflow/chains/*.md; do
  CHAIN=$(wc -l < "$f")
  echo "$(basename $f): $((MAIN + CHAIN)) lines (main + chain)"
done
```

Verify against spec abort conditions:
- Main `SKILL.md` ≤ 400 lines (hard cap)
- Common-path average ≤ 386 lines
- All targets met → record numbers in session log and back-fill CHANGELOG (Phase 4a)

If Phase 4a was committed with placeholder numbers, amend CHANGELOG.md now and create a separate fix-up commit:

```bash
# Edit CHANGELOG.md to replace {X}/{Y}/{Z}/{W} placeholders with concrete numbers
git add CHANGELOG.md
git commit -m "chore: backfill 1.7.0 CHANGELOG line counts"
```

(Skip if Phase 4a was run with concrete numbers from the start.)

### Step 2: Gap regression checklist (22 v2 gaps)

Run the full checklist from **Appendix D**. Every check must exit 0 (or print PASS). If any FAIL, the corresponding gap regressed — fix the source file and re-run.

### Step 3: Per-variant H2 assertions (20 assertions)

Run the full assertion block from **Appendix E** verbatim. Every assertion must exit 0 silently (or print PASS).

### Step 4: Re-run both parity scripts from a clean state

```bash
diff -q skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md   # expect: differs (Phase 3 modified main)
ls -l /tmp/ark-workflow-SKILL-1.6.0.md   # snapshot must still exist

python3 /tmp/reconstruct-chains.py
python3 /tmp/reconstruct-references.py
```

Both must PASS. The chain script proves the 7 chain files reconstruct the original L410-712 byte-for-byte (after normalization). The reference script proves batch-triage and troubleshooting are pure extractions.

If `/tmp/ark-workflow-SKILL-1.6.0.md` is missing, recapture it from git: `git show f690ebf:skills/ark-workflow/SKILL.md > /tmp/ark-workflow-SKILL-1.6.0.md && wc -l /tmp/ark-workflow-SKILL-1.6.0.md` (expect 858).

### Step 5: Mental walkthrough — all 13 smoke tests

Walk through every smoke test in **Appendix C**, comparing the new layout's output against the expected output. **Smoke test 1 must produce a grouping that matches current `SKILL.md` L242-247 verbatim** — Group A (Light Bugfix, parallel) #2 #5; Group B (Medium Bugfix, sequential) #3; Group C (Heavy Bugfix, pending dep) #1 → #4. Any divergence from expected output is a behavioral regression and aborts the release.

For each test, write a 1-2 line summary in scratch notes: "Test N: PASS — {1-line evidence}". The summaries get pasted into the session log at Step 6.

### Step 6: Write `vault/Session-Logs/S004-Ark-Workflow-Split.md`

Use the Write tool to create the session log. Template:

```markdown
---
type: session-log
session: S004
title: Ark Workflow Split (1.7.0)
date: 2026-04-10
status: completed
summary: Refactored ark-workflow SKILL.md from 858 lines to a progressive-disclosure router (~{X} lines) + 7 chain files + 4 reference files. All 22 v2 gaps preserved, all 19 chain variants verbatim, all 13 smoke tests pass.
source-tasks: []
tags: [ark-workflow, refactor, progressive-disclosure]
---

# S004 — Ark Workflow Split

## Goal
Reduce per-invocation context load on the common path by ≥ 50% by splitting the monolithic ark-workflow SKILL.md into a router + chains/ + references/ layout.

## Outcome

**Line counts:**
- Main SKILL.md: 858 → {X} lines ({reduction}%)
- chains/ total: {C} lines across 7 files
- references/ total: {R} lines across 4 files
- Common-path average (main + one chain): {Y} lines ({reduction}%)
- Common-path worst case (Greenfield): {Z} lines ({reduction}%)
- Total repo footprint: 858 → {W} lines ({delta})

**Behavioral parity:**
- 22/22 v2 gaps preserved (Appendix D check PASS)
- 19/19 chain variants preserved (Appendix E H2 assertions PASS)
- 12 `/test-driven-development` references preserved, 0 `/TDD` references
- handoff_marker total occurrences = baseline (gap C6 PASS)

**Parity diffs:**
- chains/* vs L410-712 baseline: PASS (after whitespace normalization)
- references/batch-triage.md vs L163-249 baseline: PASS
- references/troubleshooting.md vs concat L761-774 + L776-789 + L791-812: PASS
- references/continuity.md and routing-template.md: content-presence grep PASS

**Smoke tests (13/13 PASS):**
1. Session A batch (5 Bugfix items, grouping matches L242-247 verbatim)
2. Session B batch (file perms + SSE + dashboard)
3. Session C batch (TS build + ESLint cleanup, scenario split preserved)
4. Security audit → Hygiene Audit-Only with STOP
5. Security hardening → Hygiene Heavy with /cso prepended + deduped
6. Decision-density escalation (low-risk + architecture → Heavy)
7. Cross-session resume (handoff_marker happy path)
8. Standalone Ship
9. Knowledge Capture Full
10. Migration Medium
11. Performance Heavy
12. Mixed batch with Knowledge Capture
13. Stale chain detection (>7 days)

## Decisions
- Dropped Condition Resolution "Example resolved output" block (14 lines, illustrative only)
- continuity.md and routing-template.md use content-presence grep instead of line-by-line parity (intentional restructure with new scaffolding per spec example body)
- Spec content-preservation rule #3 ("drop --- separators between weight variants") clarified — there are no such separators in original SKILL.md; only inter-scenario separators exist, and those are dropped naturally by per-scenario file split

## Follow-ups (filed, not in scope)
- Heavy Hygiene lacks a front-loaded design phase (latent v2 gap from spec § Follow-ups #1)

## Diff
{paste git log --oneline output for the 8 phase commits}
```

### Step 7: Commit Phase 5

```bash
git add vault/Session-Logs/S004-Ark-Workflow-Split.md
git commit -m "$(cat <<'EOF'
docs(vault): add S004 session log

Records the ark-workflow progressive-disclosure split outcome,
parity-diff results, smoke-test walkthrough, and decisions.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

**CHECKPOINT 5** — Halt for user approval before Phase 6.

**Rollback:** `git revert HEAD` removes the session log only.

---

## Phase 6 — Ship

**Files (0 directly):** the only changes are commit metadata and the PR.

### Step 1: Run `/ark-code-review --thorough` on the diff

```bash
git diff master..HEAD --stat   # quick review of total changes
```

Then invoke `/ark-code-review --thorough` and address any findings.

### Step 2: Run `/simplify`

Address any simplification suggestions. For a markdown refactor, this is usually a no-op, but it's still part of the standard ship sequence.

### Step 3: Run `/codex` review of the implementation diff

```
/codex review
```

Apply any blocker findings as a fix-up commit (style: `docs(ark-workflow): address codex review — ...`).

### Step 4: Run `/ship`

```
/ship
```

`/ship` will run tests (no-op for markdown), bump VERSION (already done in Phase 4a — verify), update CHANGELOG (already done — verify), commit any release docs, push, and create a PR to master.

### Step 5: Run `/land-and-deploy`

```
/land-and-deploy
```

Wait for CI green (no-op for plugin repo) and merge.

### Step 6: Verify the merged result

```bash
git checkout master
git pull
git log --oneline -10
ls skills/ark-workflow/chains/ skills/ark-workflow/references/
cat VERSION   # expect 1.7.0
```

**CHECKPOINT 6** — Phase 6 complete. The 1.7.0 release is shipped.

**Rollback:** post-merge rollback is much harder — requires either a `git revert` of the merge commit on master (with user approval) or shipping a 1.7.1 hotfix that reintroduces the monolithic SKILL.md. Avoid by catching issues at earlier checkpoints.

---

## Appendix A — Chain reconstruction parity script

Save to `/tmp/reconstruct-chains.py` in Phase 1b Step 5. Python 3 stdlib only.

```python
#!/usr/bin/env python3
"""
Reconstruct the original ## Skill Chains section (current SKILL.md L410-712)
from the 7 extracted chain files, by reversing the structural transformations
listed in the implementation plan's "Spec Clarifications § 1".

Used as the Phase 1b parity gate. Also re-run in Phase 5 from a clean state.

Exit 0 = PASS (byte-identical match after whitespace normalization).
Exit 1 = FAIL (prints unified diff).
"""
import re
import sys
import difflib
from pathlib import Path

CHAINS_DIR = Path("skills/ark-workflow/chains")
BASELINE = Path("/tmp/ark-workflow-SKILL-1.6.0.md")
BASELINE_START = 410   # 1-indexed inclusive
BASELINE_END = 712     # 1-indexed inclusive

# Order in which scenarios appear in baseline L410-712 + their original H3 names
ORDER = [
    ("greenfield",         "Greenfield Feature"),
    ("bugfix",             "Bug Investigation & Fix"),
    ("ship",               "Shipping & Deploying"),
    ("knowledge-capture",  "Knowledge Capture"),
    ("hygiene",            "Codebase Hygiene"),
    ("migration",          "Migration"),
    ("performance",        "Performance"),
]

INTRO_PARAGRAPH = (
    "Based on the scenario and weight class, present the resolved skill chain "
    "below. Replace conditions with project-specific values from Project Discovery."
)


def reconstruct_chain_body(text: str, slug: str) -> str:
    """
    Reverse the per-chain transformations:
      # {Scenario}                          → strip (the wrapper adds ### {Name})
      ## {Weight}\n\n*{descriptor}*         → **{Weight}** ({descriptor}):
      ## {Weight}                            → **{Weight}:**
      ## Dedup rule\n\n{body first line}\n  → **Dedup rule:** {body first line}\n
    All other content (numbered steps, italic sub-labels, prose paragraphs)
    is preserved verbatim.
    """
    lines = text.splitlines()

    # Drop the first H1 line (`# {Scenario}`) — the wrapper supplies the H3 header
    if not lines or not lines[0].startswith("# "):
        raise SystemExit(f"FAIL: {slug}.md does not start with H1 header")
    lines = lines[1:]
    # Drop leading blank lines (the H3 wrapper supplies a blank line after it)
    while lines and lines[0] == "":
        lines = lines[1:]

    out = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m = re.match(r"^## (.+)$", line)
        if m:
            label = m.group(1)
            j = i + 1
            # Skip a single blank after the H2
            blanks_after_h2 = 0
            while j < n and lines[j] == "":
                blanks_after_h2 += 1
                j += 1

            # Special case: Dedup rule body collapses to inline bold
            if label == "Dedup rule":
                # body lines until end-of-file
                body = []
                while j < n:
                    body.append(lines[j])
                    j += 1
                # Strip trailing blanks
                while body and body[-1] == "":
                    body.pop()
                if not body:
                    raise SystemExit(f"FAIL: {slug}.md ## Dedup rule has no body")
                # First body line becomes inline; subsequent lines (if any) stay
                first = body[0]
                rest = body[1:]
                out.append(f"**Dedup rule:** {first}")
                out.extend(rest)
                i = j
                continue

            # Check for italic descriptor immediately after the H2
            descriptor = None
            if j < n and re.fullmatch(r"\*[^*].*[^*]\*", lines[j]):
                descriptor = lines[j][1:-1]  # strip the surrounding *
                j += 1
                # Skip the blank line that should follow the descriptor
                while j < n and lines[j] == "":
                    j += 1
                    break  # only one blank

            # Emit the bold label
            if descriptor:
                out.append(f"**{label}** ({descriptor}):")
            else:
                out.append(f"**{label}:**")
            # Re-emit a blank line (the original always has a blank between bold label and content)
            out.append("")
            i = j
        else:
            out.append(line)
            i += 1

    return "\n".join(out)


def reconstruct() -> str:
    """Build the full L410-712 section from the 7 chain files."""
    parts = []
    parts.append("## Skill Chains")
    parts.append("")
    parts.append(INTRO_PARAGRAPH)
    parts.append("")
    parts.append("---")
    parts.append("")

    for i, (slug, name) in enumerate(ORDER):
        path = CHAINS_DIR / f"{slug}.md"
        if not path.exists():
            raise SystemExit(f"FAIL: missing {path}")
        body = reconstruct_chain_body(path.read_text(), slug)
        parts.append(f"### {name}")
        parts.append("")
        parts.append(body.rstrip("\n"))
        parts.append("")
        if i < len(ORDER) - 1:
            parts.append("---")
            parts.append("")

    # Trailing newline (matches sed -n 'X,Yp' behavior)
    return "\n".join(parts) + "\n"


def normalize(text: str) -> str:
    """Whitespace normalization for the diff:
       - collapse 3+ consecutive blank lines to 2
       - strip trailing whitespace per line
       - ensure exactly one trailing newline at EOF
    """
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [l.rstrip() for l in text.splitlines()]
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    if not BASELINE.exists():
        print(f"FAIL: baseline snapshot missing: {BASELINE}", file=sys.stderr)
        print("Recapture: cp skills/ark-workflow/SKILL.md /tmp/ark-workflow-SKILL-1.6.0.md", file=sys.stderr)
        print("(Safe in Phases 1a, 1b, 2 — SKILL.md is not yet modified.)", file=sys.stderr)
        return 1

    with BASELINE.open() as f:
        baseline_lines = f.readlines()
    baseline_slice = "".join(baseline_lines[BASELINE_START - 1:BASELINE_END])

    reconstructed = reconstruct()

    expected = normalize(baseline_slice)
    actual   = normalize(reconstructed)

    if expected == actual:
        print("PASS — chain reconstruction matches baseline (L410-712, 7 scenarios, 19 variants)")
        return 0

    print("FAIL — chain reconstruction differs from baseline")
    print()
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile="baseline (L410-712 normalized)",
        tofile="reconstructed (normalized)",
        n=3,
    )
    sys.stdout.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Dry-run discipline:** the spec § 4 requires this script be tested for soundness before relying on it as the Phase 1b gate. The dry-run is the script's own first invocation (Phase 1b Step 6) — if the algorithm is correct AND the extraction is correct, the result is byte-identical (after normalization). Any FAIL on this run indicates an algorithm bug OR an extraction bug; both are blockers and must be fixed before advancing. The reconstruction algorithm is deterministic and reversible by construction — there is no third source of error.

---

## Appendix B — Reference parity script

Save to `/tmp/reconstruct-references.py` in Phase 2 Step 7. Python 3 stdlib only.

Covers `batch-triage.md` and `troubleshooting.md` only — `continuity.md` and `routing-template.md` use content-presence grep instead (see Spec Clarification § 3).

```python
#!/usr/bin/env python3
"""
Reference file parity diff for Phase 2.

Two checks:
  1. references/batch-triage.md vs baseline L163-249 (with H1 → H2 reversed)
  2. references/troubleshooting.md vs concat of L761-774 + L776-789 + L791-812
     (with the file's added H1 stripped)

continuity.md and routing-template.md are NOT covered here — they have intentional
restructure (added H2 scaffolding, new preamble, new archive rule) per the spec's
example bodies. Their parity is content-presence grep, not line-by-line diff.

Exit 0 = both PASS. Exit 1 = either FAIL (prints unified diffs).
"""
import re
import sys
import difflib
from pathlib import Path

REFS_DIR = Path("skills/ark-workflow/references")
BASELINE = Path("/tmp/ark-workflow-SKILL-1.6.0.md")


def baseline_slice(start: int, end: int) -> str:
    with BASELINE.open() as f:
        lines = f.readlines()
    return "".join(lines[start - 1:end])


def normalize(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [l.rstrip() for l in text.splitlines()]
    return "\n".join(lines).rstrip("\n") + "\n"


def check_batch_triage() -> bool:
    """Reverse the H1 → H2 demote and diff against baseline L163-249."""
    extracted = (REFS_DIR / "batch-triage.md").read_text()
    # Reverse H1 → H2 (the very first `# Batch Triage` line becomes `## Batch Triage`)
    reconstructed = re.sub(r"^# ", "## ", extracted, count=1, flags=re.MULTILINE)
    expected = baseline_slice(163, 249)
    if normalize(reconstructed) == normalize(expected):
        print("PASS — batch-triage.md matches baseline L163-249 (after H1↔H2 demote reversal)")
        return True
    print("FAIL — batch-triage.md differs from baseline L163-249")
    diff = difflib.unified_diff(
        normalize(expected).splitlines(keepends=True),
        normalize(reconstructed).splitlines(keepends=True),
        fromfile="baseline L163-249",
        tofile="reconstructed",
        n=3,
    )
    sys.stdout.writelines(diff)
    return False


def check_troubleshooting() -> bool:
    """Strip the file's added H1 + blank line, then diff against
    baseline concat L761-774 + L776-789 + L791-812.
    """
    extracted = (REFS_DIR / "troubleshooting.md").read_text()
    # Strip the first line (H1 title) and any immediate blank line
    lines = extracted.splitlines()
    if not lines or not lines[0].startswith("# "):
        print("FAIL — troubleshooting.md does not start with H1")
        return False
    body = lines[1:]
    while body and body[0] == "":
        body = body[1:]
    reconstructed = "\n".join(body) + "\n"

    expected = (
        baseline_slice(761, 774)
        + baseline_slice(776, 789)
        + baseline_slice(791, 812)
    )
    if normalize(reconstructed) == normalize(expected):
        print("PASS — troubleshooting.md matches baseline L761-774 + L776-789 + L791-812 (after H1 strip)")
        return True
    print("FAIL — troubleshooting.md differs from baseline concat")
    diff = difflib.unified_diff(
        normalize(expected).splitlines(keepends=True),
        normalize(reconstructed).splitlines(keepends=True),
        fromfile="baseline concat",
        tofile="reconstructed",
        n=3,
    )
    sys.stdout.writelines(diff)
    return False


def main() -> int:
    if not BASELINE.exists():
        print(f"FAIL: baseline snapshot missing: {BASELINE}", file=sys.stderr)
        return 1
    ok1 = check_batch_triage()
    ok2 = check_troubleshooting()
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Appendix C — 13 smoke test walkthroughs with expected output

Each test specifies the prompt, the files the new layout loads, the expected triage path, and the resolved chain output. Walk through every test as a mental dry-run during Phase 5 Step 5. **Tests 4, 5, and 6 also run in Phase 3 Step 16** as the Phase 3 exit gate.

### Test 1 — Session A (5 Bugfix batch) — MUST MATCH L242-247 VERBATIM

**Prompt:** "Triage these five bugs: 1) transaction isolation issue in DB client, 2) ghost pipeline runs at orchestrator startup, 3) payload drop on the invoke endpoint, 4) retry storms in process lifecycle, 5) MCP ClosedResourceError on graceful shutdown."

**Files loaded:** `SKILL.md` + `references/batch-triage.md` + `chains/bugfix.md`

**Expected triage path:** Workflow Step 2 → multi-item detected → read `references/batch-triage.md` → per-item triage:
- #1 Transaction isolation → Bugfix Medium (touches DB client)
- #2 Ghost pipeline runs → Bugfix Light (orchestrator startup)
- #3 Payload drop → Bugfix Medium (invoke endpoint)
- #4 Retry storms → Bugfix Heavy (process lifecycle)
- #5 MCP ClosedResourceError → Bugfix Light (graceful shutdown)

**Expected output (must match SKILL.md L242-247 verbatim):**
- Group A (parallel): #2, #5 — Light Bugfix chain
- Group B (sequential): #3 — Medium Bugfix chain
- Group C (pending dep confirmation): #1 → #4 — Heavy Bugfix
- Session recommendation: Heavy (#1 → #4) flagged for separate session

**PASS criteria:** the agent reads `chains/bugfix.md` and resolves the per-group chains using the Light/Medium/Heavy sections in that file. No content drift from current SKILL.md L483-522.

### Test 2 — Session B batch

**Prompt:** "Three issues: file permissions broken on uploaded files, SSE tunnel keeps disconnecting, dashboard is loading slowly when there are >100 entries."

**Files loaded:** `SKILL.md` + `references/batch-triage.md` + `chains/bugfix.md` + `chains/performance.md`

**Expected:** per-item triage: file perms = Bugfix Heavy (auth/data), SSE tunnel = Bugfix Medium, dashboard slow = Performance Light. Three separate scenario chains, two from `chains/bugfix.md` (Heavy + Medium) and one from `chains/performance.md` (Light).

**PASS criteria:** agent loads BOTH bugfix and performance chain files (multi-scenario batch routing).

### Test 3 — Session C batch

**Prompt:** "TS build broke after the latest dependency update, also need to clean up the ESLint warnings that have been piling up."

**Files loaded:** `SKILL.md` + `references/batch-triage.md` + `chains/bugfix.md` + `chains/hygiene.md`

**Expected:** TS build break = Bugfix Medium (broken state); ESLint cleanup = Hygiene Light. Scenario split is preserved — they are different scenarios, not consolidated.

**PASS criteria:** agent does NOT consolidate two different-scenario items into one chain.

### Test 4 — Security audit (Phase 3 exit gate)

**Prompt:** "audit our auth subsystem"

**Files loaded:** `SKILL.md` + `chains/hygiene.md`

**Expected triage path:** Scenario Detection security path 1 (audit/review) → routed to **Hygiene: Audit-Only**. Agent reads `chains/hygiene.md`, picks the `## Audit-Only` section.

**Expected output:**
1. `/codebase-maintenance` — audit (or `/cso` if security audit)
2. Present findings report to the user
3. `/wiki-update` (if vault — to record findings)
4. **STOP** — do not implement, do not ship. Ask user: "Findings above. Do you want to create tickets via `/ark-tasknotes`, or proceed with fixes (I'll re-triage as Hygiene Light/Medium/Heavy)?"

**PASS criteria:** chain ends at STOP. NO `/ship`, NO `/canary`, NO further steps.

### Test 5 — Security hardening + dedup (Phase 3 exit gate)

**Prompt:** "harden our auth subsystem"

**Files loaded:** `SKILL.md` + `chains/hygiene.md`

**Expected triage path:** Scenario Detection security path 2 (hardening) → routed to **Hygiene Heavy** with `/cso` mandatory step 1. Agent reads `chains/hygiene.md`, picks the `## Heavy` section, applies the dedup rule from `## Dedup rule` at the bottom.

**Expected resolved output (after dedup):**
1. `/cso` — security audit (PROMOTED to step 1)
2. `/codebase-maintenance` — audit (was step 1)
3. `/investigate` (if any item involves broken/unexpected behavior) (was step 2)
4. **If audit + investigation reveals systemic issues requiring rewrite: escalate to Heavy Greenfield...** (was step 3, prose escape hatch preserved)
5. **(removed — was step 4 `/cso`, deduped per Dedup rule)**
6. `/test-driven-development` — tests before restructuring (was step 5)
7. Implement cleanup (was step 6)
8. `/ark-code-review --thorough` + `/codex` → `/simplify` (was step 7)
9. `/ship` → `/land-and-deploy` (was step 8)
10. `/canary` (if deploy risk) (was step 9)
11. `/wiki-update` (if vault) + session log (was step 10)
12. `/claude-history-ingest` (was step 11)

Plus the resolution note: "Security hardening detected — `/cso` promoted to step 1; later `/cso` deduped."

**PASS criteria:** `/cso` appears EXACTLY ONCE in the resolved output. The original step 4 `/cso` is removed.

### Test 6 — Decision-density escalation (Phase 3 exit gate)

**Prompt:** "redesign the caching layer" (low risk, architecture-density)

**Files loaded:** `SKILL.md` + (`chains/hygiene.md` OR `chains/greenfield.md` depending on user clarification)

**Expected triage path:**
1. Risk classification: Low (internal change, no auth/data/infra)
2. Decision density: Architecture decisions required → escalate to **Heavy** (regardless of risk floor)
3. Scenario disambiguation: ask user "is this a refactor of existing code (Hygiene) or building a new caching layer (Greenfield)?"
4. Either branch → Heavy variant of the picked scenario chain

**PASS criteria:** the agent does NOT classify this as Light despite the Low risk. The escalation rule is preserved in main `SKILL.md` Triage section verbatim.

### Test 7 — Cross-session resume (happy path)

**Setup:** session 2 starts in a project with existing `.ark-workflow/current-chain.md` containing:
```
---
scenario: Greenfield
weight: Heavy
batch: false
created: 2026-04-09T15:00:00Z
handoff_marker: after-step-5
handoff_instructions: "Read spec at docs/superpowers/specs/2026-04-09-oauth-design.md"
---
```
With steps 1-5 marked `[x]`.

**Files loaded:** `.ark-workflow/current-chain.md` + `references/continuity.md` + `chains/greenfield.md`

**Expected:** routing template fires session-start check → reads chain file → handoff_marker is set AND step 5 is `[x]` → announces "You're in Session 2 of a Heavy Greenfield. Design phase complete. Next: `/executing-plans` with the spec at docs/superpowers/specs/2026-04-09-oauth-design.md." Rehydrates TodoWrite tasks for steps 6-21 from the unchecked items.

**PASS criteria:** the handoff announcement matches the template in `references/continuity.md` § Handoff Markers.

### Test 8 — Standalone Ship

**Prompt:** "cherry-pick the hotfix from master and deploy"

**Files loaded:** `SKILL.md` + `chains/ship.md`

**Expected:** Ship scenario detected (no weight class) → reads `chains/ship.md` → resolved output:
1. `/review` — pre-landing PR diff review
2. `/cso` (if security-relevant) — likely skipped (no security signals)
3. `/ship` → `/land-and-deploy`
4. `/canary` (if deploy risk) — likely skipped or kept depending on signals
5. `/wiki-update` (if vault)
6. `/document-release` (if standard docs exist)

**PASS criteria:** Ship chain has 6 numbered steps, no weight class header, no design phase.

### Test 9 — Knowledge Capture Full

**Prompt:** "catch up the vault after two weeks, rebuild tags, and ingest the external ADR docs"

**Files loaded:** `SKILL.md` + `chains/knowledge-capture.md`

**Expected:** Knowledge Capture scenario → Full classification (extended period + tag rebuild + external ingest) → reads `chains/knowledge-capture.md`, picks `## Full` section. 8-step chain ending in session log.

**PASS criteria:** picks Full not Light. All 8 Full steps present.

### Test 10 — Single-item Migration Medium

**Prompt:** "upgrade the React Native dep from 0.72 to 0.74, API changes required"

**Files loaded:** `SKILL.md` + `chains/migration.md`

**Expected:** Migration scenario → Medium (major version bump with API changes — risk Moderate, density Some trade-offs) → reads `chains/migration.md`, picks `## Medium` section. 10-step chain.

**PASS criteria:** picks Medium not Light or Heavy. The chain includes `/test-driven-development` at step 3 (write tests for new API surface before migrating).

### Test 11 — Single-item Performance Heavy

**Prompt:** "redesign the database query layer for the dashboard, currently 10-second page loads, need a caching architecture"

**Files loaded:** `SKILL.md` + `chains/performance.md`

**Expected:** Performance scenario → triage = Heavy (architecture density escalates from Low risk to Heavy, AND data layer changes are High risk floor) → reads `chains/performance.md`, picks `## Heavy` section. 18-step chain split across Session 1 (Analysis & Planning) + Session 2 (Implementation) + Document. handoff_marker after step 5.

**PASS criteria:** picks Heavy. handoff_marker after step 5 is preserved inline in chains/performance.md. `/canary` is mandatory at step 13 (not conditional).

### Test 12 — Mixed batch with Knowledge Capture

**Prompt:** "fix the login redirect bug AND update the README to document the new auth flow"

**Files loaded:** `SKILL.md` + `references/batch-triage.md` + `chains/bugfix.md` + `chains/knowledge-capture.md`

**Expected:** multi-item batch → per-item: bug = Bugfix (Light or Medium depending on auth scope), README update = Knowledge Capture Light. Dependency detection flags: KC depends on Bugfix landing. Execution order: Bugfix first, KC second. Two scenarios, two chain files loaded.

**PASS criteria:** batch routing loads both bugfix and knowledge-capture chains, sequencing puts KC after Bugfix because of the dependency.

### Test 13 — Stale chain detection

**Setup:** session start finds `.ark-workflow/current-chain.md` with `created: 2026-03-31T12:00:00Z` (10 days ago, > 7 days).

**Files loaded:** `.ark-workflow/current-chain.md` + `references/continuity.md`

**Expected:** stale detection trigger fires → agent prompts: "Found an ark-workflow chain from [age] ago. Is this still active, or should I archive it to `.ark-workflow/archive/`?" Does NOT auto-delete. Waits for user decision.

**PASS criteria:** matches `references/continuity.md` § Stale Chain Detection wording. Confirm "Never auto-delete — always ask" guarantee.

---

## Appendix D — 22 v2 gap regression checklist (verbatim from spec § 2)

Run from the repo root after Phase 5 Step 1. Every check must exit 0 (or print PASS).

```bash
# Gap 1 — Multi-item batch handling
grep -l "Root cause consolidation" skills/ark-workflow/references/batch-triage.md

# Gap 2 — /TDD → /test-driven-development
[ "$(grep -rho '/test-driven-development' skills/ark-workflow/ | wc -l)" -eq 12 ] || echo "FAIL gap 2: /test-driven-development total != 12"
[ "$(grep -rho '/TDD\b'                   skills/ark-workflow/ | wc -l)" -eq 0  ] || echo "FAIL gap 2: /TDD references present"

# Gap 3 — /investigate in Hygiene
[ "$(grep -c '/investigate' skills/ark-workflow/chains/hygiene.md)" -ge 3 ] || echo "FAIL gap 3"

# Gap 4 — Migration + Performance scenarios exist with 3 H2 variants each
[ -f skills/ark-workflow/chains/migration.md   ] || echo "FAIL gap 4: migration.md missing"
[ -f skills/ark-workflow/chains/performance.md ] || echo "FAIL gap 4: performance.md missing"
[ "$(grep -c '^## ' skills/ark-workflow/chains/migration.md)"   -eq 3 ] || echo "FAIL gap 4: migration H2 count != 3"
[ "$(grep -c '^## ' skills/ark-workflow/chains/performance.md)" -eq 3 ] || echo "FAIL gap 4: performance H2 count != 3"

# Gap 5 — Session handoff for non-Greenfield Heavy
grep -l "handoff_marker" skills/ark-workflow/chains/greenfield.md \
                          skills/ark-workflow/chains/migration.md \
                          skills/ark-workflow/chains/performance.md
grep -l "pivot to Heavy Greenfield"   skills/ark-workflow/chains/bugfix.md
grep -l "escalate to Heavy Greenfield" skills/ark-workflow/chains/hygiene.md
grep -l "Session Handoff" skills/ark-workflow/references/troubleshooting.md

# Gap 6 — Risk-primary + density triage
[ "$(grep -c "Risk sets the floor" skills/ark-workflow/SKILL.md)" -ge 1 ] || echo "FAIL gap 6"

# Gap 7 — Scenario-shift re-triage
grep -l "Scenario shift" skills/ark-workflow/references/troubleshooting.md

# Gap 8 — Knowledge Capture Light/Full
[ "$(grep -c '^## ' skills/ark-workflow/chains/knowledge-capture.md)" -eq 2 ] || echo "FAIL gap 8"

# Gap 9 — Precise condition trigger lists
[ "$(grep -c "Security-relevant triggers" skills/ark-workflow/SKILL.md)" -ge 1 ] || echo "FAIL gap 9"

# Gap 10 — deferred from v2, not in scope

# Gap 11 — Early exits
[ "$(grep -c "Early exits" skills/ark-workflow/SKILL.md)" -ge 1 ] || echo "FAIL gap 11"

# Gap 12 — Security audit/hardening split
[ "$(grep -c "Security audit / review" skills/ark-workflow/SKILL.md)" -ge 1 ] || echo "FAIL gap 12 (audit)"
[ "$(grep -c "Dedup rule" skills/ark-workflow/chains/hygiene.md)"     -ge 1 ] || echo "FAIL gap 12 (dedup)"

# C1 — Root cause consolidation
grep -l "Root cause consolidation" skills/ark-workflow/references/batch-triage.md

# C2 — Dependency detection
grep -l "Dependency detection"     skills/ark-workflow/references/batch-triage.md

# C3 — Grouping (parallel/sequential/separate session)
grep -lE "[Pp]arallel groups|[Ss]equential chains" skills/ark-workflow/references/batch-triage.md

# C4 — Cross-session continuity
grep -l "Cross-Session Continuity" skills/ark-workflow/references/continuity.md

# C5 — Rehydrate TodoWrite
grep -l "Rehydrate" skills/ark-workflow/references/continuity.md

# C6 — handoff_marker total occurrences vs baseline
TOTAL_NEW=$(grep -rho "handoff_marker" skills/ark-workflow/ | wc -l)
TOTAL_BASELINE=$(grep -ho "handoff_marker" /tmp/ark-workflow-SKILL-1.6.0.md | wc -l)
[ "$TOTAL_NEW" -eq "$TOTAL_BASELINE" ] || echo "FAIL C6: handoff_marker count drift ($TOTAL_NEW vs baseline $TOTAL_BASELINE)"

# C7 — Stale chain detection
grep -l "Stale Chain" skills/ark-workflow/references/continuity.md

# C8 — Context recovery
grep -l "Context Recovery" skills/ark-workflow/references/continuity.md

# C9 — Hygiene Audit-Only variant
[ "$(grep -c '^## Audit-Only' skills/ark-workflow/chains/hygiene.md)" -eq 1 ] || echo "FAIL C9"

# C10 — /cso dedup rule
grep -l "^## Dedup rule" skills/ark-workflow/chains/hygiene.md
```

---

## Appendix E — 20 per-variant H2 assertions (verbatim from spec § 3)

Run from the repo root after Phase 5 Step 2. Every assertion must exit 0 silently. Each expected H2 heading is named explicitly by exact string — this is intentional (the earlier H2-count heuristic could pass by coincidence).

```bash
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
```

---

## Per-phase file budget summary

| Phase | New | Modified | Total | ≤ 5? |
|---|---|---|---|---|
| 1a  | 5 (chains/{greenfield,bugfix,ship,knowledge-capture,hygiene}.md) | 0 | 5 | ✓ |
| 1b  | 2 (chains/{migration,performance}.md) | 0 | 2 | ✓ |
| 2   | 4 (references/{batch-triage,continuity,troubleshooting,routing-template}.md) | 0 | 4 | ✓ |
| 3   | 0 | 1 (SKILL.md) | 1 | ✓ |
| 4a  | 0 | 4 (VERSION, plugin.json, marketplace.json, CHANGELOG.md) | 4 | ✓ |
| 4b  | 0 | up to 2 (README.md, TODO.md, conditional) | ≤ 2 | ✓ |
| 5   | 1 (S004 session log) | 0 | 1 | ✓ |
| 6   | 0 | 0 (commit metadata only) | 0 | ✓ |

Every phase clears the ≤ 5 files/phase budget per CLAUDE.md.

---

## Self-review notes

- **Spec coverage:** every section of the spec maps to a phase. § 1 baseline → Phase 1a Step 1. § 2 gap checklist → Appendix D. § 3 structural checks → Appendix E. § 4 parity diff → Appendices A + B + Phase 1b Step 6 + Phase 2 Step 8. § 5 smoke tests → Appendix C + Phase 3 Step 16 + Phase 5 Step 5. § 6 line counts → Phase 5 Step 1. § 7 rollback → per-phase Rollback subsections. Phase outline § "Phased execution outline" → Phases 1a-6.
- **Placeholder scan:** the only `{X}/{Y}/{Z}/{W}` placeholders intentionally remain in the CHANGELOG entry and the session log template (Phase 4a / Phase 5) — they are filled in from the Phase 5 Step 1 measurement and are explicitly marked as "back-fill from measurement". No "TODO" / "implement later" / "TBD" / "appropriate error handling" patterns elsewhere.
- **Type consistency:** `chains/{slug}.md` filenames are consistent across the plan (greenfield, bugfix, ship, knowledge-capture, hygiene, migration, performance). `references/{name}.md` filenames are consistent (batch-triage, continuity, troubleshooting, routing-template). Reconstruction script `ORDER` matches the spec § "File layout" order.
- **Gap surfaced:** spec content-preservation rule #3 is misleading — there are no `---` separators between weight variants in current SKILL.md, only between scenarios. Documented in Spec Clarifications § 1.3. No spec change required since the rule's intent (drop separators that interfere with the new layout) is satisfied trivially by the per-scenario file split.
- **Gap surfaced:** spec § 4 line-by-line parity diff for `references/continuity.md` and `references/routing-template.md` is incompatible with the spec's own example bodies for those files (added scaffolding). Documented in Spec Clarifications § 3 with the resolution: parity uses content-presence grep + visual review for those two files.
- **Edit Integrity:** Phase 3 has explicit `Re-read SKILL.md` steps after every cluster of ≤ 3 edits per CLAUDE.md rule.
- **No Semantic Search:** Phase 3 Step 6 (the scenario→filename mapping) verifies all 7 filenames individually with separate greps.
