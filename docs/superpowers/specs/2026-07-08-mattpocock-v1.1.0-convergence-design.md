# Spec: Converge ark-skills onto mattpocock v1.1.0

**Date:** 2026-07-08
**Status:** Draft — CCG-reviewed (spec + plan; Codex GO-WITH-CHANGES, Antigravity scope "Just Right"); all must-fixes folded in; native epic sub-issues (Phase 3b) added at user request; pending user review gate.
**Scope decision (settled):** Minimal label model — keep `epic→story→task` + component + `P1–P3`; adopt `to-tickets` as the child-cutting engine; do **not** adopt `wayfinder:*` labels.

## Problem

mattpocock/skills v1.1.0 renamed the skills ark-skills routes to and depends on.
ark-skills still references the **retired** names in 9 tracked files. This is a live
correctness regression, not just a missed enhancement:

| Retired (gone) | v1.1.0 replacement |
|---|---|
| `to-issues` | `to-tickets` |
| `to-prd` | `to-spec` |
| `to-plan` | folded into `to-tickets` |
| `review` | `code-review` |
| `decision-mapping` | `wayfinder` |
| `qa` | retired, no replacement |

Verified on disk: the retired names are **absent** from `~/.agents/skills/` and
`~/.claude/skills/`; the new names are present.

**Concrete failures today:**
- `skills/ark-health/SKILL.md` Check 3 greps `~/.claude/skills` for
  `to-issues triage to-prd setup-matt-pocock-skills` and passes on `≥3`. On an
  upgraded install only **2/4** are present (`to-issues`, `to-prd` absent) → the
  check **fails a false negative**.
- `skills/ark-consult/SKILL.md` routes child-cutting to `/to-issues` (retired) and
  names `to-prd` in a known-overlap rule.
- `.omc/drafts/mattpocock-contract.md` documents `to-issues`/`to-prd` behavior —
  skills that no longer exist. This file is **tracked** (not gitignored) and is
  pointed at by `ark-consult` and `docs/agents/issue-tracker.md`.

## Goals

1. **Phase 1 — Rename fix.** Replace every retired reference with its v1.1.0 name;
   restore `/ark-health` Check 3 to a passing state on upgraded installs.
2. **Phase 2 — `to-tickets` engine (Minimal).** Document that ark-skills' mattpocock
   lane cuts children via `to-tickets` (native blocking edges + sub-issues +
   expand-contract), while `/ark-consult` keeps owning the epic + component + priority
   labels.
3. **Phase 3 — `research` → vault wire-up.** Make mattpocock's `research` output a
   first-class `/vault` ingestion source, so the mattpocock lane produces durable OKF
   knowledge.
4. **Phase 3b — Native epic sub-issues.** Make `/ark-consult` attach each cut child to
   the epic as a **native GitHub sub-issue** (the `sub_issues` API — a parent-side write
   the epic owner performs), in addition to the existing markdown checkboxes. Closes the
   gap where the epic→child hierarchy was checkbox-text only.
5. **Phase 4 — version + changelog.** Bump 2.2.1 → 2.3.0. No push.

## Non-goals

- No `wayfinder:*` label adoption; no change to `epic→story→task`. (Adopting
  `wayfinder` as a native map workflow is the content of a future "Additive" bump.)
- No changes to `/ark-update` — the renames are ark-skills' own internal references
  (fixed in Phase 1); `/ark-update` converges *downstream* repos onto OKF + GitHub
  Issues, which mattpocock skill names never touch.
- Do not patch mattpocock's installed skill files (e.g. `/triage`'s hardcoded
  disclaimer string, `wayfinder`'s hardcoded labels).
- No push, no PR — Phase 4 stages the version bump only.
- **Deferred cheap wins (CCG-Antigravity, declined for this bump):** wiring
  `claude-handoff` into `/ark-consult`'s handoff step; adding a local-`research`
  routing archetype; installing `git-guardrails` hooks via `/ark-onboard` + asserting
  them in `/ark-health`. All three *expand behavior* beyond the three approved
  opportunities and are held for a future additive bump — noted here so they are not
  silently lost.

---

## Phase 1 — Rename fix (mechanical, correctness repair)

Pure name substitution, no semantic change. Split into two passes of ≤5 files each
so each pass can be verified independently.

### Pass 1a — load-bearing routing + health (4 files)

- `skills/ark-consult/SKILL.md`
  - L70: `mattpocock grill-with-docs → to-prd` → `grill-with-docs → to-spec`
  - L109, L116, L119: `/to-issues` → `/to-tickets`
- `skills/ark-health/SKILL.md`
  - L51: **harden the roster (CCG-Codex #1).** The old `≥3-of-4` shape can
    false-*pass* if `to-tickets` — the skill Phase 2 makes load-bearing — is the
    one missing. Replace with a required-set + soft-count:
    ```bash
    req=0; for s in to-tickets setup-matt-pocock-skills; do [ -d "$HOME/.claude/skills/$s" ] && req=$((req+1)); done
    opt=0; for s in to-spec triage implement; do [ -d "$HOME/.claude/skills/$s" ] && opt=$((opt+1)); done
    { [ "$req" -eq 2 ] && [ "$opt" -ge 2 ]; } && echo "PASS: to-tickets+setup present, $opt/3 optional" || echo "FAIL: req=$req/2 opt=$opt/3"
    ```
  - L56: "Unlocks: `/to-issues` + `/triage`" → "`/to-tickets` + `/triage`"
  - L248–249 sample output ("mattpocock skills -- only 1/4 present"): illustrative;
    update the fix hint if it names a retired skill, otherwise leave.
  - **Do NOT touch L43** — its `qa`/`review` are gstack session-detection tokens,
    not mattpocock skill names (see the classification guard below).
- `skills/ark-onboard/SKILL.md`
  - L12: `/to-issues` → `/to-tickets`
- `docs/agents/issue-tracker.md`
  - L31: `(to-issues, triage, to-prd, qa)` → `(to-tickets, triage, to-spec, code-review)`
    (drop retired `qa`; add `code-review`)
  - L48: `/to-issues` → `/to-tickets`
  - L72: `/to-issues` → `/to-tickets`

### Classification guard — `review` and `qa` are NOT blanket renames (CCG-Codex #2)

`to-issues`/`to-prd`/`to-plan`/`decision-mapping` are unambiguous mattpocock skill
names → replace every occurrence. But `review` and `qa` are **generic words** with
live non-mattpocock meanings in this repo, so they are **classified, not
blanket-replaced**:

- `skills/ark-health/SKILL.md` L43 — `qa`, `review` are **gstack session-detection
  tokens**. Leave untouched.
- `skills/ark-consult/SKILL.md` L49 — "design-system + review **tooling**" is prose.
  Leave untouched.
- `docs/superpowers/specs/2026-04-08-*.md` — historical spec referencing `/review`,
  `/qa`. Out of scope (historical record). Leave untouched.
- **The only mattpocock-context edit** is `docs/agents/issue-tracker.md` L31, where
  `qa` appears in the mattpocock-contract skill list → drop it, add `code-review`
  (already covered in Pass 1a). There is **no** ark-skills reference to a mattpocock
  `/review` skill to rename.

### Pass 1b — docs + contract (4 files)

- `README.md` L45: `/to-issues` → `/to-tickets`
- `AGENTS.md` L65: `/to-issues` → `/to-tickets`
- `skills/AGENTS.md` L97: `/to-issues` → `/to-tickets`
- `.omc/drafts/mattpocock-contract.md` — **full rewrite** against the real installed
  SKILL.md files for `to-tickets`, `to-spec`, `triage`, `code-review`. Preserve the
  load-bearing invariants, updated to new names:
  - All target skills are `disable-model-invocation: true` (no ambient routing;
    handoff = explicit slash invocation).
  - `to-tickets` states "Do NOT close or modify any parent issue" — children only
    reference the parent; `/ark-consult` owns epic + child-checklist maintenance.
  - Component labels (`consultant`/`conventions`/`vault`/`onboarding`) are
    ark-specific and outside mattpocock's vocabulary; `/ark-consult` applies them.
  - The `/triage` disclaimer-string discrepancy stays documented as-is (both
    `> *This was generated by AI.*` and `> *This was generated by AI during triage.*`
    are valid; do not reconcile).
  - Update the header provenance line (currently cites
    `~/.claude/skills/{to-issues,triage,to-prd,setup-matt-pocock-skills}`).

### Stale-draft flag (decision folded into plan)

`.omc/drafts/issue-tracker-ark-additions.md` (L24, L46) also carries retired refs and
appears to be a superseded staging draft of the now-final `docs/agents/issue-tracker.md`.
**Default:** sweep it in the rename (cheap, keeps the grep clean) rather than delete it.

### Phase 1 completion criterion

```
git grep -nE "to-issues|to-prd|to-plan|decision-mapping" -- ':!vault/**' ':!docs/superpowers/**' ':!CHANGELOG.md'
```
returns **zero** matches. Three paths are excluded because they legitimately name the
old skills: `vault/**` (historical pages), `docs/superpowers/**` (this spec + plan,
which document the rename map), and `CHANGELOG.md` (which records the rename). Every
*live* reference must be clean. This grep is the test — the changes are Markdown, so
there is no compiler/unit test to run.

---

## Phase 2 — `to-tickets` as child-cutting engine (Minimal)

Light: `/ark-consult` already delegates child-cutting to mattpocock. Semantic
additions only.

**Implementation note (CCG, both models):** `skills/ark-consult/SKILL.md` and
`.omc/drafts/mattpocock-contract.md` are each touched in Phase 1 *and* Phase 2. Do
each file's rename + semantic edits in **one pass** to avoid re-reading/re-editing
churn — the phase split is logical, not a mandate to open each file twice.

- `skills/ark-consult/SKILL.md`
  - In the child-cutting section: note that delegating to `/to-tickets` now yields
    children with **native blocking edges + sub-issue relationships**, filed in
    dependency order, and that **wide refactors** are sequenced as **expand-contract**
    rather than forced into a single tracer-bullet ticket.
  - `/ark-consult` still owns the epic + `component` + `P1–P3` labels; children still
    carry `story`/`task` + "Part of #epic". The `gh` direct fallback remains.
  - Sharpen the mattpocock lane entry points: held-in-head build → `/to-spec` →
    `/to-tickets`; already-filed issue → `/implement`.
- `.omc/drafts/mattpocock-contract.md`
  - Document `to-tickets`' native blocking / sub-issue behavior and expand-contract.
  - Record `wayfinder` as **available but not wired** into `/ark-consult` routing
    under the Minimal profile, because it hardcodes `wayfinder:map` / `wayfinder:*`
    labels that the Minimal model does not adopt. The mattpocock build lane stays
    `to-spec` → `to-tickets` → `implement`.
- **Wayfinder escape hatch (CCG-Codex #3).** `skills/ark-consult/SKILL.md` must state
  where **foggy, multi-session** work goes now that `wayfinder` is off-profile: it
  routes to the **OMC lane** (`ralplan`/`autopilot`), which the matrix already owns
  for greenfield/large efforts — make that explicit so huge ambiguous efforts have a
  home. A user may still invoke `/wayfinder` manually as an off-profile/additive
  choice; `/ark-consult` names it but does not auto-route there.

### Phase 2 completion criterion

`ark-consult` and the contract describe the `to-tickets` engine and the
wayfinder-deferred boundary with no reference to `wayfinder:*` labels being applied by
ark-skills. Manual consistency read.

---

## Phase 3 — `research` → vault wire-up

**Seam correction (CCG-Antigravity).** A background `research` agent has no reason to
read `docs/agents/issue-tracker.md`, so a pointer buried there would never reach it.
`research` resolves "where the repo keeps such notes" against the **Context-Discovery
surface** — `CLAUDE.md`. So the landing path is registered where discovery actually
looks:

- `CLAUDE.md` **Project Configuration** table: add a row
  `**Research notes** | vault/Research/` (the discoverable, authoritative pointer the
  `research` skill resolves against). This is the primary seam.
- `skills/vault/SKILL.md` §2 (Document ingestion): add `research`-produced cited
  Markdown as a first-class ingest source — it lands in `vault/Research/`, and
  `/vault` distills/normalizes it into OKF-conformant pages (`type:`, `description:`,
  `source-tasks:` populated with the originating GitHub issue number). Use
  `description:` — the field the vault skill and `okf_lint.py` enforce (not `summary:`).
- `docs/agents/issue-tracker.md` "ark-skills additions": one cross-reference line
  pointing at the CLAUDE.md row (so the tracker doc stays internally complete). No new
  file.

### Phase 3 completion criterion

`CLAUDE.md` carries the `Research notes → vault/Research/` config row; `skills/vault/
SKILL.md` §2 names `research` output as an ingest source with that landing path;
`docs/agents/issue-tracker.md` cross-references it. Manual consistency read.

---

## Phase 3b — Native epic sub-issues

Today `/ark-consult` links epic→children with **markdown checkboxes only** (`- [ ] #NNN`
+ "Part of #epic" text). GitHub's native sub-issue hierarchy is unused, so the epic gets
no hierarchy panel or progress roll-up.

**Key constraint / resolution.** A native sub-issue is a **parent-side write** (POST to
the epic's `/sub_issues`). The contract's "never touch the parent" rule binds
*mattpocock's child-cutter*, not the epic owner — and `/ark-consult` **owns** the epic.
So `/ark-consult` performs the attach itself; no doctrine violation.

**Mechanics (verified).** `gh` 2.86.0 + the `sub_issues` REST endpoint is GA and
reachable. `sub_issue_id` is the child's **REST integer id** (`gh api .../issues/<n>
--jq .id`, e.g. `4831116462`) — NOT the issue number and NOT the `gh issue list --json
id` node id (`I_kwDO…`).

**Graceful degradation.** The attach is **non-fatal**: an already-attached child returns
HTTP 422, and some personal-account/tracker configurations don't fully support the
endpoint. In both cases `/ark-consult` swallows the error (`… --silent 2>/dev/null ||
true`) and the markdown checkboxes remain the working fallback — the workflow never fails
on a sub-issue attach.

- `skills/ark-consult/SKILL.md`: after children are cut, attach each as a native
  sub-issue; keep the checkboxes as the human-readable fallback.
- `docs/agents/issue-tracker.md`: add the `sub_issues` `gh api` call to the conventions
  crib.
- `.omc/drafts/mattpocock-contract.md`: note that the parent-side sub-issue attach is
  `/ark-consult`'s job (the epic owner), distinct from mattpocock's "never touch parent".

Stays within the Minimal label model — no new labels, no epic→story→task change.

### Phase 3b completion criterion

`git grep -n "sub_issues" -- skills/ark-consult/SKILL.md docs/agents/issue-tracker.md`
shows the attach paragraph + crib bullet; the contract carries the ownership note.
Runtime attach is exercised when `/ark-consult` next files an epic.

## Phase 4 — version + changelog

Bump 2.2.1 → **2.3.0** (new convergence behavior, minor):
- `VERSION`, `plugin.json`, `marketplace.json`, `CHANGELOG.md`.
- **No push, no PR.** Pushing is a separate explicit step.

### Phase 4 completion criterion

All four version surfaces read `2.3.0`; `CHANGELOG.md` has a `2.3.0` entry summarizing
the mattpocock v1.1.0 convergence.

---

## Verification (whole spec)

All changes are Markdown/JSON — no executable test suite applies. Verification is:

1. **Unambiguous-name sweep:** `git grep -nE "to-issues|to-prd|to-plan|decision-mapping"
   -- ':!vault/**' ':!docs/superpowers/**' ':!CHANGELOG.md'` returns zero (the three
   excluded paths legitimately name the old skills as history / rename-map).
2. **Classification audit (CCG-Codex #2):** confirm every surviving `review`/`qa` is a
   non-mattpocock use. Run and eyeball each hit against the classification guard:
   ```bash
   git grep -nE 'mattpocock.{0,80}/(review|qa)|/(review|qa).{0,80}mattpocock' -- ':!vault/**' ':!docs/superpowers/specs/**'
   ```
   Expect **zero** mattpocock-context hits (the only intended edit is dropping `qa`
   from `issue-tracker.md:31`).
3. **Cross-reference integrity:** every `.omc/drafts/mattpocock-contract.md` pointer in
   `ark-consult` and `issue-tracker.md` still resolves, and the contract now matches
   the installed skills.
4. **Hardened Check 3:** `/ark-health` Check 3 passes on this machine — required
   `to-tickets` + `setup-matt-pocock-skills` present, plus `≥2 of {to-spec, triage,
   implement}` — and would still FAIL if `to-tickets` alone were missing.
5. **Version sync:** all four version surfaces read `2.3.0` (grep the string across
   `VERSION plugin.json marketplace.json CHANGELOG.md`).
6. **Native sub-issue docs present:** `git grep -n "sub_issues" -- skills/ark-consult/SKILL.md docs/agents/issue-tracker.md` shows the attach paragraph + crib bullet (Phase 3b).
7. Manual consistency read of the semantic additions in Phases 2–3b.

## File inventory

| File | Phase | Change |
|---|---|---|
| `skills/ark-consult/SKILL.md` | 1a, 2, 3b | rename + semantic additions + native sub-issue attach |
| `skills/ark-health/SKILL.md` | 1a | rename (Check 3 roster) |
| `skills/ark-onboard/SKILL.md` | 1a | rename |
| `docs/agents/issue-tracker.md` | 1a, 3, 3b | rename + research-landing cross-ref + sub-issue crib |
| `CLAUDE.md` | 3 | `Research notes → vault/Research/` config row |
| `README.md` | 1b | rename |
| `AGENTS.md` | 1b | rename |
| `skills/AGENTS.md` | 1b | rename |
| `.omc/drafts/mattpocock-contract.md` | 1b, 2 | full rewrite |
| `.omc/drafts/issue-tracker-ark-additions.md` | 1b | rename (stale draft) |
| `skills/vault/SKILL.md` | 3 | research ingest source |
| `VERSION`, `plugin.json`, `marketplace.json`, `CHANGELOG.md` | 4 | version bump |
