---
name: ark-skill-healer
description: Upstream-dependency healing for ark-skills. Inventories the external plugins/CLIs ark-skills integrates with, diffs each upstream changelog/releases/commits against a last-seen snapshot, and surfaces required changes, new-feature opportunities, and retire-able workarounds as a ranked ADVISORY report plus staged patches. Project-level skill (not distributed). Invoke via /ark-skill-healer. Triggers on "heal skills upstream", "check upstream deps", "what upstream changed", "did upstream fix our workaround".
---

# ark-skill-healer

Project-level, **advisory-only** skill. The upstream-facing mirror of `/ark-update`.
Load `references/architecture.md` for the full model.

## Boundary

| Skill | Direction | Scope |
|-------|-----------|-------|
| `/ark-update` | downstream | converge a project to ark-skills' target profile |
| `/ark-health` | local | read-only session-capability diagnostic |
| **`/ark-skill-healer`** | **upstream** | **watch upstream deps; advise what ark-skills should change** |

## Structural safety invariant (AC11)
The **entire** run-write surface is the gitignored `.omc/skill-healer/`
(snapshots, staged patches, proposals, run-manifest). This skill **never** uses
Edit/Write on ark-skills source. After any run, `git -C <repo> status --porcelain`
on tracked files MUST be empty. The staging dir is the only permitted write target.

## Command surface
- `/ark-skill-healer` — full pass over every inventoried dep
- `--dep <name>` — restrict to one dep
- `--dry-run` — inventory + diff only; skip patch staging

## References (load on demand)
- `references/architecture.md` — model, cascade, snapshot lifecycle, ranking
- `references/collector-contract.md` — JSON record shapes + evidence-integrity rule
- `references/source-map.md` — per-dep source_url / tiers (probe-confirmed)
- `references/cascade.md` — cascade decision tree + offline/rate-limit handling

Lineage: `tests/` from `ark-update`; `references/` from `ark-health`.

---

## Workflow

### Step 0 — Resolve dirs + run manifest
- Repo root = `git rev-parse --show-toplevel`. Skill dir = `.claude/skills/ark-skill-healer/`.
- Ensure `.omc/skill-healer/{state/last-seen,staged-patches}/` exist (create if missing).
- Read `.omc/skill-healer/run-manifest.json`. If `status: in_progress`, this is a
  RESUME — skip deps already in `deps_done`.

### Step 1 — Inventory
- Run `bash scripts/collect_inventory.sh`. Assert the leading `_contract == 1`.
- This is the positive allowlist (collector-contract §1). The dep universe for the
  rest of the run is exactly these records. Do not add deps the collector didn't emit.

### Step 2 — Upstream deltas + workaround seeds
- Run `bash scripts/collect_upstream.sh` and `bash scripts/seed_workarounds.sh`.
- For each `upstream_delta` with `quiet: true`, produce **no finding** (record the
  quiet_reason for the run summary only).
- Append each processed dep to the run-manifest's `deps_done`.

### Step 3 — Impact Analysis (must-change) — JUDGMENT
For each non-quiet `upstream_delta`, decide whether the prose delta forces a change
in ark-skills (a breaking change, a deprecation, a version-pin bump, a removed flag):
- Assign `impact (1–5)` and `confidence (0–1)`. **Down-weight confidence for
  `source_tier == commit`** (coarse evidence) — sink, never drop.
- Name the concrete ark-skills target file + the change.
- Draft a **staged** patch into `.omc/skill-healer/staged-patches/<dep>-<n>.patch`.
  NEVER apply it. NEVER Edit/Write a tracked file.
- ⚠️ **Version-authority guardrail (S015 lesson).** A version/fix claim sourced from
  a **fork** changelog tier is NOT a shipped release. Specifically: a `mempalace-plugin`
  changelog finding (the milla-jovovich fork runs ahead of PyPI — see
  `references/source-map.md`) must NEVER drive a pin-bump or "fixed upstream" claim on
  its own. Before recommending any version-pin change, cross-check the authoritative
  release source (`mempalace-cli` PyPI release tier for mempalace; the dep's own
  release tier otherwise) and confirm the version is actually published AND installable.
  When in doubt, recommend "verify against PyPI/releases" rather than a concrete bump.
- A `source_tier == install_lag` finding means the *installed* copy is behind the
  authoritative upstream latest — recommend an upgrade of the install, not a pin edit.

### Step 4 — Opportunity Discovery (could-improve) — JUDGMENT
Best-effort: from the same deltas, surface new upstream features ark-skills could
adopt. Same `impact × confidence` scoring. These rank among the must-change findings.

### Step 5 — Workaround Retirement — JUDGMENT
- Read `references/workarounds.yaml` (the tracked seed registry — **read-only**).
- For each entry, interpret its `upstream_issue_ref` against the `evidence_refs`
  from Step 2: if upstream shows the issue closed/fixed, flag the workaround
  **retire-able** (impact from how much debt it sheds).
- ⚠️ **A closed GitHub issue is NOT a shipped fix (S015 lesson).** Only flag a
  workaround retire-able when the fix is published to the AUTHORITATIVE release
  channel (PyPI for mempalace-cli) **AND** the installed copy has it. A fork-changelog
  or a closed-issue ref alone is insufficient — `#1457` was closed-as-issue yet its
  fix never shipped to PyPI (latest `3.3.5`), so its workaround must stay. Honor each
  entry's `retire_when` literally.
- Surface `workaround_proposal` records (untracked refs) as **proposals** for the
  human to add to the registry — never write `workarounds.yaml`.

### Step 6 — Render Report
- One list, sorted **descending by `impact × confidence`**. **No top-N truncation** —
  every finding (incl. down-weighted commit-tier and low-value ones) appears.
- Each row: `[score] dep — category — title`, the **verbatim** evidence ref
  (select/reorder only; if none, `evidence: none` — never fabricate), and for
  must-change rows the staged-patch path.
- Footer: list of `quiet` deps + reasons; staged-patch dir; proposals path; and an
  explicit line: **"ADVISORY — review and apply manually. Nothing was applied."**
- Final sanity: run `git -C <repo> status --porcelain` and confirm it is empty for
  tracked files (AC11). If not, STOP and report — a write leaked.
