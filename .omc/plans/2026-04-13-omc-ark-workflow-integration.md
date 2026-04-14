---
title: "OMC ↔ /ark-workflow Dual-Mode Integration"
date: 2026-04-13
last-revised: 2026-04-13
spec: .omc/specs/deep-interview-omc-ark-workflow-integration.md
target_version: 1.13.0
status: approved (ralplan consensus iteration 2)
iteration: 2
consensus_reached: 2026-04-13
mode: consensus (ralplan)
architect_verdict: APPROVE
critic_verdict: APPROVE
---

# OMC ↔ /ark-workflow Dual-Mode Integration — Implementation Plan

## RALPLAN-DR Summary

### Principles (5)

1. **Mirror, don't invent.** The `HAS_OMC` availability pattern reuses `/ark-context-warmup`'s `availability.py` idiom (function signature, return-dict shape, `*_skip_reason` strings). Zero new probe paradigms.
2. **Ark file is authoritative, OMC state is transient.** `.ark-workflow/current-chain.md` remains the resume SoT under Path B. `.omc/state/sessions/{id}/` is annotated in the chain's Notes section but never consumed by Ark resume logic.
3. **Graceful degradation is mandatory.** When `HAS_OMC=false`, Path B is *invisible* (not merely disabled) and the user sees exactly today's chain output plus a one-line install hint. No functionality regresses for OMC-less installs. `ARK_SKIP_OMC=true` is a user-facing emergency rollback that forces `HAS_OMC=false` regardless of detection.
4. **Variant-inherited handback with enumerated special cases.** (Renamed from "uniform handback boundary" — both Architect and Critic noted that "uniform" overclaimed the shape given Knowledge-Capture and Hygiene Audit-Only exceptions.) Every Path B chain uses the `<<HANDBACK>>` marker after `/autopilot` (execution-only), then hands control back to the variant-specific Ark closeout inherited from that variant's Path A tail. The three enumerated special cases (Ship Standalone closeout-as-normal, Knowledge-Capture closeout starts at `/wiki-update`, Hygiene Audit-Only closeout = `/wiki-update` → STOP) are first-class contracts in `references/omc-integration.md` § Section 4, not footnotes.
5. **Phased execution with ≤5 files/phase.** Agent Directive #2 is non-negotiable. Planning accepts 4–6 phases over merging work into fewer, larger phases. Iteration 2 splits Phase 2 into 2a + 2b to preserve slack.

### Decision Drivers (top 3)

1. **Dual consumers of OMC detection.** The router (bash) needs `HAS_OMC` alongside `HAS_UI`/`HAS_VAULT`/`HAS_CI` for chain branching. The Context Brief (Python, via `availability.py`) needs it for the "OMC detected: yes/no" line. These are *separate surfaces* and the plan must wire both.
2. **19 variants × variant-inherited handback = mechanical repetition risk.** A content-regression CI check (diff-based, post-edit, byte-identity on canonicalized blocks) is cheaper than a hand-audit of 19 sections. The plan includes `check_path_b_coverage.py` landing in Phase 1 — mitigation ships with the foundation.
3. **Version-release artifacts drift easily.** `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md` must bump in lockstep to `1.13.0` per user memory directive. Dedicated phase with a cross-file grep/diff verification step.

### Viable Options

#### Option A — Selected: "Probe + router prologue + per-chain Path B block, variant-inherited handback with enumerated special cases"

Extend `availability.py` to emit `has_omc`, add a bash `HAS_OMC` probe in `SKILL.md` Project Discovery, route the recommendation + 3-button override in Step 6 (Present Resolved Chain), add a `## Path B` section to each of the 19 variants whose closeout inherits from that variant's Path A tail starting at `/ark-code-review` (or the enumerated special case). New reference file `references/omc-integration.md` consolidates the per-chain skill map, the OR-any signal rule, the variant-inherited handback contract, the canonical OMC cache path literal, and the enumerated special-case closeouts.

- **Pros:** Aligns with spec's Acceptance Criteria 1:1. Mechanical, auditable, low cognitive load for executor. Closeout-by-inheritance means 16 of 19 Path B blocks are near-identical (only scenario-specific header + the `<<HANDBACK>>` anchor change); the 3 special cases (Hygiene Audit-Only, Knowledge-Capture Light, Knowledge-Capture Full) have distinct, enumerated shapes in the reference. Each phase touches ≤5 files (Phase 2a = 3 files, Phase 2b = 2 files). Graceful degradation is natural.
- **Cons:** 19 edits across 7 files. Requires a content-regression check (`check_path_b_coverage.py`) to catch missed variants — landed in Phase 1 so Phase 2a/2b cannot pass verification without it. Path B closeout inheritance requires clear prose in `references/omc-integration.md` so the executor knows the contract differs for special cases.

#### Option B — Alternative: "Generate Path B blocks programmatically at router runtime from a single template"

The router reads one canonical Path B template from `references/omc-integration.md`, applies scenario/weight-specific substitutions, and emits the Path B chain at Step 6. Chain files (`chains/*.md`) are not modified at all.

- **Pros:** Single source of truth for Path B — any handback-contract tweak is a one-file edit. Avoids the 19-variant repetition entirely. Phase count drops to ~4.
- **Cons:** Violates the established architecture where `chains/*.md` is the readable, human-auditable canonical chain definition. The existing CI check `skills/ark-context-warmup/scripts/check_chain_integrity.py` won't catch Path B regressions (it reads `chains/*.md` text). Introduces a runtime template engine where the codebase currently has pure-markdown chains. Significantly higher review surface for a feature that exists to add *user-visible* content to each chain. Rejected on discoverability: a user reading `chains/greenfield.md` should see both paths inline, not discover Path B only at runtime.

#### Option C — Rejected: "Hard-dependency OMC, collapse Path A into Path B"

Make OMC a hard dependency of the plugin; retire `/brainstorming` and `/writing-plans` from Path A in favor of the OMC pipeline uniformly.

- **Rejected because:** Spec explicitly rules this out under Non-Goals ("NOT making OMC a hard dependency," "NOT removing `/brainstorming` or `/writing-plans` from Path A"). Included here to document that the neutrality of Path A is preserved by design, not by omission.

**Selected: Option A.** Option B was the only close competitor; its discoverability loss and CI-integration friction outweighed its DRY appeal.

---

## Changelog from Iteration 1

The Critic iteration-1 review returned ITERATE with 13 required changes. All 13 are addressed below. The Architect iteration-1 review returned ITERATE with 3 findings + 2 synthesis proposals; the synthesis proposals are also absorbed.

| # | Required change | How addressed |
|---|-----------------|---------------|
| 1 | Fix `scripts/` path bug (real path is `skills/ark-context-warmup/scripts/check_chain_integrity.py`) | Every verification command in Phase 1, 2a, 2b, 3 rewritten. Global constraint clause updated. |
| 2 | Fix `probe(...)` verification to match the real keyword-only signature | Phase 1 verification now invokes `probe` with the full kwargs set (`project_repo`, `vault_path`, `tasknotes_path`, `task_prefix`, `notebooklm_cli_path`). |
| 3 | Split Phase 2 into 2a (3 files) + 2b (2 files) | Phase 2a = greenfield + bugfix + hygiene (10 variants, the vanilla template). Phase 2b = ship + knowledge-capture (3 variants with enumerated special-case shapes). Phase numbering: 1 → 2a → 2b → 3 → 4 → 5. Rationale below in Phase 2a/2b. |
| 4 | Add Pre-mortem with 3 scenarios (prob/blast-radius/detection/mitigation) | New `## Pre-mortem` section. Three scenarios from the Architect's proposal, expanded with required metadata. |
| 5 | Add Observability plan line (Path B selection + success rate telemetry) | New `## Observability` section. Router logs one line per triage invocation to `.ark-workflow/telemetry.log` with anonymized `path-selected=A|B` tag. Justification inline. |
| 6 | Add `ARK_SKIP_OMC=true` env var rollback | Wired into `SKILL.md` Project Discovery probe (Phase 1), documented in `references/omc-integration.md` § Section 3 as "Emergency rollback for downstream projects," surfaced in Principle 3. |
| 7 | Pin per-variant handback boundaries as separate contracts for `/autopilot`, `/ralph`, `/ultrawork`, `/team`; for `/team`, handback occurs after `team-verify`, before `team-fix` | `references/omc-integration.md` § Section 4 expanded to enumerate four sub-contracts. Phase 1 Concrete Changes updated. |
| 8 | Enumerate canonical OMC keyword trigger list verbatim in Section 3 (Path B Signal #1 detector) | Section 3 now includes the verbatim 12-item keyword list from `.claude/skills/omc-reference/SKILL.md` lines 89–101. Detector specified as exact-string word-boundary regex match, case-insensitive. |
| 9 | Add Commit convention section with git trailers per omc-reference lines 112–141 | New `## Commit Convention` section with a worked Phase 1 example. |
| 10 | Machine-enforced byte-identity check in `check_path_b_coverage.py`; per-variant expected-closeout table | Phase 1 ships `check_path_b_coverage.py` with canonicalize-then-hash logic; `references/omc-integration.md` § Section 4 includes the per-variant expected-closeout table; AC3 refined. |
| 11 | Centralize OMC cache path literal as `OMC_CACHE_DIR` in Section 0 | `references/omc-integration.md` § Section 0 (new) defines `OMC_CACHE_DIR=~/.claude/plugins/cache/omc`. Both the bash probe in `SKILL.md` and the Python probe in `availability.py` cite this constant by comment. |
| 12 | Rename AC15/AC16 from Acceptance Criteria to Pipeline Gates | New `## Pipeline Gates` subsection. AC15/AC16 removed from AC table, preserved as PG1/PG2. |
| 13 | Move `check_path_b_coverage.py` creation into Phase 1 | Phase 1 now touches 4 files (was 3) with the new script as the fourth file. Still ≤5 per Agent Directive #2. |

Architect synthesis proposals absorbed: (a) the variant-inherited principle is renamed (addressed via Principle 4 rename); (b) a pre-mortem with the three listed scenarios is added. Architect finding re: `HAS_OMC` false-positive on consumer CLAUDE.md is now Pre-mortem scenario (a).

---

## Commit Convention

Per `.claude/skills/omc-reference/SKILL.md` lines 112–141, every phase commit uses an intent line, optional body, and structured git trailers. Trailers required on every commit:

- `Constraint:` active constraint shaping the decision
- `Rejected:` alternative considered | reason for rejection (if any)
- `Directive:` forward-looking warning or instruction (if any)
- `Confidence:` high | medium | low
- `Scope-risk:` narrow | moderate | broad
- `Not-tested:` known verification gap (if any)

### Worked example — Phase 1 commit

```text
feat(ark-workflow): HAS_OMC probe + omc-integration reference foundation

Establish OMC detection in both consumers (bash router + availability.py),
create the consolidating reference doc, and land check_path_b_coverage.py
early so Phase 2a/2b cannot pass verification without all 19 Path B blocks.

Constraint: Agent Directive #2 — ≤5 files per phase (this phase touches 4)
Constraint: Mirror the availability.py return-dict shape; no new probe paradigms
Rejected: Inline OMC cache path literal in both consumers | drift risk; use OMC_CACHE_DIR constant in references/omc-integration.md §0 instead
Directive: ARK_SKIP_OMC=true is the emergency rollback; document in Section 3 and wire into the bash probe
Confidence: high
Scope-risk: narrow
Not-tested: End-to-end smoke with a real OMC install on a fresh profile (Phase 3 covers)
```

Subsequent phase commits follow the same shape with phase-appropriate constraints.

---

## Phased Plan

**Global constraints all phases honor:**
- ≤5 files touched per phase (Agent Directive #2).
- Each phase ends with a verification step; next phase does not start until verification passes.
- Every phase runs `python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains` and (once Phase 1 lands) `python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains` if chain files were touched.
- Every phase commit follows the Commit Convention above.

---

### Phase 1 — Foundation: probe + router prologue + reference + coverage check

**Goal.** Establish `HAS_OMC` detection in both consumers (router bash + `availability.py`), write the consolidating reference doc that subsequent phases reference by link, and land the content-regression CI check so Phase 2a/2b cannot pass verification without all 19 Path B blocks.

**Files touched (4):**
1. `skills/ark-context-warmup/scripts/availability.py`
2. `skills/ark-workflow/SKILL.md`
3. `skills/ark-workflow/references/omc-integration.md` (**NEW**)
4. `skills/ark-context-warmup/scripts/check_path_b_coverage.py` (**NEW**)

**Concrete changes:**

- `availability.py`:
  - Add two new keyword-only parameters: `omc_cache_dir: Path | None = None` (the `OMC_CACHE_DIR` cited from `references/omc-integration.md` § Section 0; default resolves to `Path.home() / ".claude" / "plugins" / "cache" / "omc"` at call time) and `omc_cli_path: str | None = None` (mirrors `notebooklm_cli_path` idiom; callers resolve via `shutil.which("omc")` upstream so the probe is pure).
  - Probe logic: `has_omc = (omc_cli_path is not None) or (omc_cache_dir is not None and omc_cache_dir.exists())`.
  - Result dict gains `"has_omc": bool` and on False `"has_omc_skip_reason": "OMC CLI not on PATH and OMC_CACHE_DIR ({path}) not present"` with the resolved path interpolated.
  - Add a comment above the new parameters: `# OMC_CACHE_DIR canonical constant lives in skills/ark-workflow/references/omc-integration.md § Section 0.`
  - Mirror the exact return-shape idiom of the existing notebooklm/wiki/tasknotes keys. No new paradigms.
- `skills/ark-workflow/SKILL.md`:
  - Project Discovery section: add a `HAS_OMC` bash probe alongside `HAS_UI`/`HAS_VAULT`/`HAS_CI`. Probe snippet (add a comment cross-referencing Section 0 of the reference doc):
    ```bash
    # OMC_CACHE_DIR canonical: ~/.claude/plugins/cache/omc
    # (references/omc-integration.md § Section 0)
    if command -v omc >/dev/null 2>&1 || [ -d "$HOME/.claude/plugins/cache/omc" ]; then
      HAS_OMC=true
    else
      HAS_OMC=false
    fi
    # ARK_SKIP_OMC=true forces HAS_OMC=false regardless of detection
    # (emergency rollback for downstream projects — see Section 3 of the reference doc)
    [ "$ARK_SKIP_OMC" = "true" ] && HAS_OMC=false
    export HAS_OMC
    ```
  - Add a new sub-section under "Workflow → Step 6" titled **"Step 6 (continued): Dual-path presentation when HAS_OMC=true"** describing the 3-button UX (`[Accept Path B] [Use Path A] [Show me both]`), the OR-any signal rule, and the silent degradation when `HAS_OMC=false` (emit Path A only + one-line install hint).
  - Cross-link `references/omc-integration.md` for details.
- `references/omc-integration.md` (new) — sections and content:
  - **Section 0: Canonical constants.** Single-source-of-truth table: `OMC_CACHE_DIR = ~/.claude/plugins/cache/omc`, `OMC_CLI_BIN = omc`, `INSTALL_HINT_URL = <pending — executor fills from user memory or the OMC README>`. All other files reference these by comment pointer; no inline re-quotation.
  - **Section 1:** Two-philosophies axis (user-facing) vs checkpoint-density axis (implementation-side).
  - **Section 2:** Per-chain skill map — table mapping each of 19 variants to its OMC primary pipeline. Variants that fit better with `/ralph` (loop-to-verified: Bugfix Heavy, Performance Medium/Heavy), `/ultrawork` (parallel: Greenfield Heavy multi-module), or `/team` (coordinated agents: Migration Heavy) are noted per row.
  - **Section 3:** When Path B beats Path A. Includes:
    - The 4 signals + OR rule + discoverability-over-neutrality rationale.
    - **Signal #1 detector specification (verbatim keyword list from `.claude/skills/omc-reference/SKILL.md` lines 89–101):**
      > `"autopilot"→autopilot`
      > `"ralph"→ralph`
      > `"ulw"→ultrawork`
      > `"ccg"→ccg`
      > `"ralplan"→ralplan`
      > `"deep interview"→deep-interview`
      > `"deslop" / "anti-slop"→ai-slop-cleaner`
      > `"deep-analyze"→analysis mode`
      > `"tdd"→TDD mode`
      > `"deepsearch"→codebase search`
      > `"ultrathink"→deep reasoning`
      > `"cancelomc"→cancel`
      > Team orchestration is explicit via `/team`.

      Detector: case-insensitive regex with word-boundary anchors, matching any of: `autopilot`, `ralph`, `ulw`, `ultrawork`, `ccg`, `ralplan`, `deep interview`, `deep-interview`, `deslop`, `anti-slop`, `deep-analyze`, `tdd`, `deepsearch`, `ultrathink`, `cancelomc`, `/team`, `team`. The unquoted two-word form (`deep interview`) matches as a phrase; the slash form (`/team`) and the bare form (`team`) both trigger. Regex: `\b(autopilot|ralph|ulw|ultrawork|ccg|ralplan|deep[- ]interview|deslop|anti-slop|deep-analyze|tdd|deepsearch|ultrathink|cancelomc|/?team)\b`, flags `re.IGNORECASE`.
    - **Emergency rollback: `ARK_SKIP_OMC=true`.** Downstream projects can force Path B invisibility by exporting this env var. Document one-line recipe: `ARK_SKIP_OMC=true /ark-workflow "<prompt>"`. Intended for incident response and downstream projects that explicitly opt out.
  - **Section 4:** Variant-inherited handback contract. Four sub-contracts, one per autopilot variant:
    - **4.1 `/autopilot` handback** (vanilla, used by Greenfield/Bugfix/Hygiene/Ship/Migration/Performance non-special variants): `<<HANDBACK>>` fires after `/autopilot`'s internal Phase 4 (execution) completes; `/autopilot`'s internal Phase 5 (docs/ship) is SKIPPED. Control returns to Ark at `/ark-code-review --thorough` (Heavy) or `/ark-code-review --quick` (Medium/Light).
    - **4.2 `/ralph` handback** (Bugfix Heavy, Performance Medium/Heavy alternates): `<<HANDBACK>>` fires after `/ralph`'s loop-to-verified exits with success; Ark closeout inherits from the variant's Path A tail as above.
    - **4.3 `/ultrawork` handback** (Greenfield Heavy multi-module alternates): `<<HANDBACK>>` fires after the last parallel lane's completion signal; Ark closeout as above.
    - **4.4 `/team` handback** (Migration Heavy alternate): `<<HANDBACK>>` fires **after `team-verify`**, **before `team-fix`** (which is the bounded-remediation loop per `.claude/skills/omc-reference/SKILL.md` lines 106–108). If `team-verify` reports failures, Ark's `/ark-code-review --thorough` + normal Ark closeout happen first; bounded `team-fix` remediation is invoked from within Ark's review only if Ark's own review concurs there are remaining defects. This keeps Ark as the last-word reviewer and avoids OMC-internal bounded-remediation running on the far side of the handback.
    - **Per-variant expected-closeout table** (what `check_path_b_coverage.py` validates against — byte-identity on canonicalized blocks, N allowed shapes):

      | Variant | Closeout shape | Starts at | Ends at |
      |---------|----------------|-----------|---------|
      | Greenfield Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
      | Bugfix Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
      | Hygiene Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
      | Hygiene Audit-Only | Special-A | `/wiki-update` | STOP (no code review, no ship) |
      | Ship Standalone | Vanilla | `/ark-code-review --thorough` | `/claude-history-ingest` |
      | Knowledge-Capture Light | Special-B | `/wiki-update` | `/claude-history-ingest` |
      | Knowledge-Capture Full | Special-B | `/wiki-update` | `/claude-history-ingest` |
      | Migration Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
      | Performance Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |

      Total: 19 rows. Three distinct shapes (Vanilla, Special-A Hygiene-Audit-Only, Special-B Knowledge-Capture). `check_path_b_coverage.py` canonicalizes each block (strip scenario headers/weight) and hashes it; expected distinct hashes = 3 (one per shape); expected total blocks = 19.
  - **Section 5:** Per-chain Path B block template (skeletons that Phase 2a/2b copy into each variant). Three templates parameterized by `{scenario}`, `{weight}`, `{path_a_closeout_start_step}`:
    - **Template Vanilla** — 16 variants.
    - **Template Special-A Hygiene-Audit-Only** — 1 variant.
    - **Template Special-B Knowledge-Capture** — 2 variants (Light, Full).

- `skills/ark-context-warmup/scripts/check_path_b_coverage.py` (new):
  - Reads each file in `skills/ark-workflow/chains/*.md`.
  - Extracts every `### Path B (OMC-powered` section body up to the next `##` or `### ` heading.
  - **Canonicalization:** strip scenario header line, strip `{weight}` references, strip leading/trailing whitespace, normalize inner whitespace.
  - **Byte-identity hash:** `hashlib.sha256(canonical_body.encode()).hexdigest()`.
  - **Assertions:** total blocks = 19; distinct canonicalized hashes = 3; each block contains literal `/deep-interview` OR `/claude-history-ingest` (Knowledge-Capture substitutes) and literal `<<HANDBACK>>`.
  - **Allowed-shapes table** embedded as module-level `ALLOWED_SHAPES = {"vanilla": <count=16>, "special-a-hygiene-audit-only": 1, "special-b-knowledge-capture": 2}`; assertion on distribution, not just total.
  - CLI: `--chains PATH` (required); exits 0 on success, 1 with per-variant error messages on failure.

**Verification:**

- Python probe (correct keyword-only signature):
  ```bash
  cd skills/ark-context-warmup/scripts && python3 -c "
  from pathlib import Path
  from availability import probe
  result = probe(
      project_repo=Path('/tmp/fake-repo'),
      vault_path=Path('/tmp/fake-vault'),
      tasknotes_path=Path('/tmp/fake-tasknotes'),
      task_prefix='Fake-',
      notebooklm_cli_path=None,
      omc_cli_path='/usr/local/bin/omc',
      omc_cache_dir=Path('/tmp/fake-omc'),
  )
  assert 'has_omc' in result, f'missing has_omc key; got {sorted(result.keys())}'
  print('OK: has_omc key present;', sorted(result.keys()))
  "
  ```
  Expected: `OK: has_omc key present; [...,'has_omc',...]`.
- Bash probe (live repo, OMC is installed per user env):
  ```bash
  cd /Users/sunginkim/.superset/worktrees/ark-skills/OMC-integration
  bash -c 'source <(sed -n "/# OMC_CACHE_DIR canonical/,/export HAS_OMC/p" skills/ark-workflow/SKILL.md | grep -v "^#"); echo $HAS_OMC'
  # Expected: true
  bash -c 'ARK_SKIP_OMC=true source <(sed -n "/# OMC_CACHE_DIR canonical/,/export HAS_OMC/p" skills/ark-workflow/SKILL.md | grep -v "^#"); echo $HAS_OMC'
  # Expected: false (ARK_SKIP_OMC wins)
  ```
- CI coverage check (runs empty-chain-blocks precondition — no blocks yet, should NOT fail with "total blocks = 19" because Phase 1 only lands the script, not the blocks):
  - Run `python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains` with a `--phase=foundation` flag that relaxes the 19-block assertion; OR invert and assert "total blocks = 0" at end of Phase 1. **Decision:** add a `--expected-blocks N` CLI flag (default 19). Phase 1 verification calls with `--expected-blocks 0`; Phase 2a calls with `--expected-blocks 10`; Phase 2b calls with `--expected-blocks 13`; Phase 3 calls with default 19.
- Existing integrity check unaffected:
  ```bash
  python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains
  ```
  Expected: `OK: 7 chain files check clean`.
- Markdown lint of the new reference file (no broken links).

**Rollback:** Revert the 4 files. No downstream consumer yet depends on `has_omc` or the coverage check.

---

### Phase 2a — Chain variants batch 1 (vanilla template, 3 files, 10 variants)

**Rationale for split.** Phases 2a and 2b were a single dense Phase 2 in iteration 1 (5 files, at Agent Directive #2 ceiling, zero slack). Critic flagged this as zero-tolerance for a mid-phase discovery. Split preserves slack: 2a = 3 files (vanilla template only; mechanical, homogeneous); 2b = 2 files (special-case templates; heterogeneous, needs careful template selection).

**Goal.** Add the Vanilla Path B template to every variant in Greenfield, Bugfix, and Hygiene (non-Audit-Only). 10 variants total, all using the Vanilla closeout shape.

**Files touched (3):**
1. `skills/ark-workflow/chains/greenfield.md` (3 variants: Light, Medium, Heavy)
2. `skills/ark-workflow/chains/bugfix.md` (3 variants: Light, Medium, Heavy)
3. `skills/ark-workflow/chains/hygiene.md` (4 variants: Audit-Only uses Special-A in Phase 2b; Light/Medium/Heavy use Vanilla here)

**Wait — Hygiene has 4 variants with 1 being special.** Decision: Phase 2a edits 3 of hygiene's 4 variants (Light, Medium, Heavy) using Vanilla; Phase 2b edits the 4th (Audit-Only) using Special-A. Hygiene file is touched in BOTH phases. This is a trade — a file touched twice vs. a phase over the ceiling. Rationale: hygiene.md's 4 variants are physically separated in the file; the 2a edits and 2b edit are non-overlapping line ranges; the second touch is a one-variant append, which is mechanically the same as any other single-variant edit. Verification between 2a and 2b (coverage check with `--expected-blocks 10`) confirms 2a did not accidentally edit the Audit-Only variant. This trade is preferable to violating the ≤5 files ceiling.

**Concrete changes per variant (Vanilla template from `references/omc-integration.md` § Section 5):**

After each existing `## {Weight}` section's body, append:

```markdown
### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — execution only; skips autopilot's internal Phase 5 (docs/ship). See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --{weight}` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).
```

Variant-specific weight substitution: Light→`--quick`, Medium→`--quick`, Heavy→`--thorough`.

**Verification:**
- `python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains --expected-blocks 10` exits 0.
- `grep -c "### Path B" skills/ark-workflow/chains/greenfield.md` → 3.
- `grep -c "### Path B" skills/ark-workflow/chains/bugfix.md` → 3.
- `grep -c "### Path B" skills/ark-workflow/chains/hygiene.md` → 3 (NOT 4 yet — Audit-Only is Phase 2b).
- `python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains` → `OK`.
- Manually diff 3 random Vanilla blocks against the Section 5 template to confirm `<<HANDBACK>>` marker and closeout-inheritance clause are present.

**Rollback:** Revert the 3 chain files. Phase 1 foundation remains; coverage check's `--expected-blocks 0` invocation still passes.

---

### Phase 2b — Chain variants batch 2 (special-case templates, 2 files, 3 variants)

**Goal.** Add the Special-A (Hygiene Audit-Only) and Special-B (Knowledge-Capture Light/Full) templates. These three variants have distinct closeout shapes and get separate, attention-requiring edits.

**Files touched (2):**
1. `skills/ark-workflow/chains/hygiene.md` (1 variant: Audit-Only — second touch; see Phase 2a rationale)
2. `skills/ark-workflow/chains/knowledge-capture.md` (2 variants: Light, Full)

**Concrete changes:**

- **Hygiene Audit-Only** — Special-A template:
  ```markdown
  ### Path B (OMC-powered — if HAS_OMC=true)

  *Findings-only — no code review, no ship.*

  0. `/ark-context-warmup` — same as Path A
  1. `/deep-interview` — converge on audit scope (ambiguity threshold 20%)
  2. `/omc-plan --consensus` — multi-agent consensus audit plan
  3. `/autopilot` — execution only; produces findings document
  4. `<<HANDBACK>>` — Ark resumes authority
  5. **Ark closeout (Special-A):** `/wiki-update` (record findings in vault) → STOP. No code review, no ship — findings-only chain. See `references/omc-integration.md` § Section 4 (Special-A row).
  ```
- **Knowledge-Capture Light and Full** — Special-B template. `/deep-interview` is inapplicable (capture is reflective, not prospective); substitute with `/claude-history-ingest` as step 1:
  ```markdown
  ### Path B (OMC-powered — if HAS_OMC=true)

  *Reflective capture with front-loaded mining + autonomous synthesis.*

  0. `/ark-context-warmup` — same as Path A
  1. `/claude-history-ingest` — mine recent conversations as capture source (substitutes for `/deep-interview` since capture is reflective)
  2. `/omc-plan --consensus` — plan the capture (wiki pages, tags, cross-links)
  3. `/autopilot` — execution only; runs `/wiki-ingest` + `/cross-linker` + `/tag-taxonomy`
  4. `<<HANDBACK>>` — Ark resumes authority
  5. **Ark closeout (Special-B):** `/wiki-update` (finalize session log + epic) → `/claude-history-ingest` (final mining sweep). No code review, no ship — capture-only chain. See `references/omc-integration.md` § Section 4 (Special-B row).
  ```

**Verification:**
- `python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains --expected-blocks 13` exits 0.
- `grep -c "### Path B" skills/ark-workflow/chains/hygiene.md` → 4 (all hygiene variants covered now).
- `grep -c "### Path B" skills/ark-workflow/chains/knowledge-capture.md` → 2.
- `python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains` → `OK`.
- Canonicalized-hash check: distinct shapes so far = 3 (Vanilla + Special-A + Special-B).

**Rollback:** Revert the 2 files; Phase 2a and Phase 1 remain intact.

---

### Phase 3 — Chain variants batch 3 (Migration + Performance + Ship Standalone, 3 files, 7 variants)

Wait — Ship Standalone is 1 variant, Migration is 3, Performance is 3. That's 7 variants in 3 files. Original iteration 1 batched Ship into Phase 2 (that batch); now that Phase 2 is split, Ship moves to Phase 3 alongside Migration + Performance to keep Phase 2a at 3 files and Phase 2b at 2 files. All 7 variants in Phase 3 use the Vanilla template.

**Goal.** Complete the remaining 7 Vanilla-template variants: Migration (Light/Medium/Heavy), Performance (Light/Medium/Heavy), Ship (Standalone).

**Files touched (3):**
1. `skills/ark-workflow/chains/migration.md`
2. `skills/ark-workflow/chains/performance.md`
3. `skills/ark-workflow/chains/ship.md`

**Concrete changes:**

Apply the Vanilla Path B template from Phase 2a to every variant. Per-variant autopilot-flavor annotations:
- **Migration Heavy:** annotate that `/team` is a suitable autopilot variant (coordinated cross-module migrations benefit from multi-agent parallelism). Handback contract: Section 4.4 (after `team-verify`, before `team-fix`).
- **Performance Medium/Heavy:** annotate that `/ralph` is suitable when the success criterion is a measurable benchmark (loop-to-verified semantics). Handback contract: Section 4.2.
- **Migration Light / Performance Light / Ship Standalone:** Path B is discouraged for these shapes — include the block but note it's unusual. Do not hide the option; discoverability > neutrality per spec. Open Question #3 (resolved: show-always).

**Verification:**
- `python3 skills/ark-context-warmup/scripts/check_path_b_coverage.py --chains skills/ark-workflow/chains --expected-blocks 19` exits 0 (full 19-variant coverage; distinct shapes = 3).
- `grep -c "### Path B" skills/ark-workflow/chains/migration.md` → 3.
- `grep -c "### Path B" skills/ark-workflow/chains/performance.md` → 3.
- `grep -c "### Path B" skills/ark-workflow/chains/ship.md` → 1.
- **Full 19-variant audit:** `grep -l "### Path B" skills/ark-workflow/chains/*.md | wc -l` returns `7` (all chain files); per-file count sum = 19.
- `python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains` → `OK`.
- Smoke-test: simulate `/ark-workflow` with a Greenfield Heavy prompt twice — once with `HAS_OMC=true` exported, once with `ARK_SKIP_OMC=true`. Verify Path B rendered vs suppressed with install hint.

**Rollback:** Revert the 3 files; Phase 1 + Phase 2a + Phase 2b remain intact.

---

### Phase 4 — Release artifacts bump to v1.13.0

**Goal.** Version + changelog update in lockstep per user memory directive ("always bump VERSION, plugin.json, marketplace.json, CHANGELOG on every push to master").

**Files touched (4):**
1. `VERSION` — `1.12.0` → `1.13.0`
2. `.claude-plugin/plugin.json` — `"version": "1.12.0"` → `"version": "1.13.0"` (key path verified: root-level `version`)
3. `.claude-plugin/marketplace.json` — `plugins[0].version: "1.12.0"` → `"1.13.0"`
4. `CHANGELOG.md` — prepend v1.13.0 entry

**CHANGELOG v1.13.0 sections (model after v1.12.0 entry style):**

- **Added**
  - Dual-mode routing in `/ark-workflow`: every chain now emits Path A (Ark-native, step-by-step, user-in-the-loop) and Path B (OMC-powered: `/deep-interview` → `/omc-plan --consensus` → `/autopilot` execution-only → `<<HANDBACK>>` → variant-inherited Ark closeout) when OMC is installed.
  - `HAS_OMC` availability probe in `skills/ark-workflow/SKILL.md` (bash; mirrors `HAS_UI`/`HAS_VAULT` pattern). Honors `ARK_SKIP_OMC=true` env var as emergency rollback.
  - `has_omc` key added to `skills/ark-context-warmup/scripts/availability.py` probe result; Context Brief now includes an "OMC detected: yes/no" line.
  - `skills/ark-workflow/references/omc-integration.md` consolidates Section 0 canonical constants, two-philosophies axis, per-chain skill map, OR-any signal rule, variant-inherited handback contract (four sub-contracts: `/autopilot`, `/ralph`, `/ultrawork`, `/team`), and per-variant expected-closeout table.
  - `skills/ark-context-warmup/scripts/check_path_b_coverage.py` — CI check enforcing 19 Path B blocks across 7 chain files with 3 distinct canonicalized shapes (Vanilla + Special-A Hygiene-Audit-Only + Special-B Knowledge-Capture).
- **Changed**
  - All 19 variants across all 7 chain files gained a `### Path B (OMC-powered)` section.
  - Step 6 of `/ark-workflow` now renders the 3-button recommendation UX (`[Accept Path B] [Use Path A] [Show me both]`) when `HAS_OMC=true` and ≥1 of the 4 signals fires (OR-any rule; discoverability over neutrality).
- **Degradation contract**
  - `HAS_OMC=false` emits Path A only, plus a one-line install hint. `ARK_SKIP_OMC=true` forces this path regardless of detection. Zero behavioral change vs v1.12.0 on OMC-less installs. OMC remains optional.

**Verification:**
- `diff <(grep -o '1\.13\.0' VERSION) <(grep -o '1\.13\.0' .claude-plugin/plugin.json)` — both present.
- `grep -c '"version": "1.13.0"' .claude-plugin/marketplace.json` returns 1.
- `head -5 CHANGELOG.md` shows `## [1.13.0] - 2026-04-13`.

**Rollback:** Revert the 4 files. No consumer has yet resolved v1.13.0.

---

### Phase 5 — Upstream vault artifacts

**Goal.** Satisfy the spec's done-bar ("Complete + upstream integration"): TaskNote epic, session log, Compiled Insight. These are vault-local and follow existing frontmatter conventions.

**Files touched (3):**
1. `vault/TaskNotes/Tasks/Epic/Arkskill-003-omc-integration.md` (**NEW** — counter is at 3, this claim consumes it)
2. `vault/Session-Logs/S007-OMC-Integration-Design.md` (**NEW** — prev session was S006)
3. `vault/Compiled-Insights/Execution-Philosophy-Dual-Mode.md` (**NEW**)

**Concrete changes:**

- **Arkskill-003 epic** (model after `Arkskill-002-ark-context-warmup.md`):
  - Frontmatter: `task-id: "Arkskill-003"`, `status: done` (on merge), `project: "ark-skills"`, `task-type: epic`, `session: "S007"`, `source-sessions: [[S007-OMC-Integration-Design]]`.
  - Sections: Summary, Spec & Plan (linking this plan + the deep-interview spec), Implementation checklist (phases 1 → 2a → 2b → 3 → 4 → 5 restated as done checkboxes on merge), Tests, Next Steps.
  - Increment `vault/TaskNotes/meta/Arkskill-counter` from `3` → `4` after claiming `003`.
- **S007 session log** (model after `S006-Ark-Context-Warmup-Ship.md`):
  - Frontmatter: `session: "S007"`, `status: complete`, `date: 2026-04-13`, `prev: "[[S006-Ark-Context-Warmup-Ship]]"`, `epic: "[[Arkskill-003-omc-integration]]"`, `source-tasks: [[Arkskill-003-omc-integration]]`.
  - Sections: Objective, Context (5-round deep interview → 8% ambiguity), Work Done (one sub-section per phase 1/2a/2b/3/4/5), Decisions Made (6 resolved assumptions from spec table + the iteration-2 principle rename + ARK_SKIP_OMC rollback + four handback sub-contracts, each as a bullet), Issues & Discoveries, Next Steps.
- **Compiled Insight: Execution-Philosophy-Dual-Mode** (model after `Development-Workflow-Patterns.md`):
  - Frontmatter: `type: compiled-insight`, `tags: [compiled-insight, skill, workflow, omc, dual-mode]`, `source-sessions: [[S007-OMC-Integration-Design]]`.
  - Sections: Summary, Key Insights (checkpoint-density axis; variant-inherited handback with enumerated special cases; OR-any signal rule + discoverability bias; dual-consumer probe pattern; release-artifact lockstep rule; emergency-rollback env var pattern; per-autopilot-variant handback contract divergence), Evidence, Implications.
  - Implications cross-link: any new orchestrator skill should inherit the probe idiom, the OMC_CACHE_DIR canonical-constant pattern, and the variant-inherited handback boundary rule.

**Verification:**
- Front-matter YAML lint on all 3 new vault files (`python3 -c "import yaml; yaml.safe_load(open(f).read().split('---')[1])"` for each).
- `/wiki-lint` clean on the new files (no broken wikilinks to Arkskill-003 / S007 / Execution-Philosophy-Dual-Mode).
- `/cross-linker` run surfaces the new pages without reporting orphans.
- Regenerate `index.md` via `_meta/generate-index.py` to include the 3 new pages.

**Rollback:** Remove the 3 files. Does not affect code paths.

---

## Pre-mortem

Three failure scenarios with probability / blast radius / detection signal / mitigation.

### Scenario A — Consumer CLAUDE.md hardcodes `HAS_OMC=false` via grep; false positive on upgrade

- **Probability:** Medium. Downstream projects that adopted a strict-grep hardening recipe during v1.12.0 integration may have pinned `HAS_OMC=false` to suppress noise.
- **Blast radius:** Narrow (single downstream repo). Does not affect this repo or propagate.
- **Detection signal:** On v1.13.0 upgrade, downstream user reports "I installed OMC but Path B never appears in `/ark-workflow` output." Telemetry (see Observability): `path-selected=A` with `has_omc=true` in the log for a prompt containing an OMC keyword.
- **Mitigation:** (1) `ARK_SKIP_OMC=true` env var is the opt-in disable — downstream should use it instead of grep-pinning. Document prominently in `references/omc-integration.md` § Section 3. (2) CHANGELOG v1.13.0 Degradation Contract explicitly calls out `ARK_SKIP_OMC`. (3) Phase 1 probe snippet in `SKILL.md` is inside a clearly-commented block so a grep-pinning recipe can be targeted for removal.

### Scenario B — User picks Path B without realizing `/autopilot` runs blackbox for hours

- **Probability:** Medium. Discoverability bias (show-always Path B) combined with first-time Path B users means someone WILL click `[Accept Path B]` on a Heavy greenfield without reading the small print.
- **Blast radius:** Moderate. User session loses hours to autonomous execution with reduced judgment checkpoints. Recoverable via `.ark-workflow/current-chain.md` (Ark SoT) but costly in user time.
- **Detection signal:** User reports "I didn't realize this would run for 2 hours without asking me anything." Telemetry: high `path-selected=B` rate followed by `session-ended-early=true` signals.
- **Mitigation:** (1) Step 6 presentation includes a one-line estimated-duration and checkpoint-density blurb next to `[Accept Path B]` (e.g., "autonomous execution, ~1-4 hours, ~3 checkpoints"). Specify this concretely in `SKILL.md` Step 6 sub-section. (2) `[Show me both]` button lets the user compare before committing. (3) Telemetry enables a soft-limit alert if Path B acceptance rate >80% without any `[Show me both]` clicks — suggests users aren't reading.

### Scenario C — Orphaned `.omc/state/` after a Path B crash; Ark resume from chain file succeeds but user assumes OMC state is canonical

- **Probability:** Low-Medium. Path B's `/autopilot` writes to `.omc/state/sessions/{id}/` and the chain file annotates the path. After a crash, the user might manually inspect the OMC state, see it's incomplete, and abandon the Ark chain file — despite Ark resume being the correct recovery path.
- **Blast radius:** Narrow (single session). Data loss is limited to the work the user abandons; Ark chain file + git history covers the rest.
- **Detection signal:** User reports "OMC state is incomplete, I can't resume." Telemetry: `resume-attempted=true` with `resume-from=omc-state` instead of `resume-from=ark-chain`.
- **Mitigation:** (1) Principle 2 codified in the spec AND prominently in `references/omc-integration.md` § Section 4 ("Ark chain file is single source of truth; `.omc/state/` is transient."). (2) The Path B template annotates `<<HANDBACK>>` step with explicit "Ark resume uses `.ark-workflow/current-chain.md`; `.omc/state/` is not consulted" prose. (3) Handoff markers in `.ark-workflow/current-chain.md` include the OMC state path so the user can cross-reference without relying on it as SoT.

---

## Observability

**Rationale.** Path B's show-always discoverability bias + blackbox autonomous execution means we need telemetry to detect Scenario A (false Path A pinning) and Scenario B (accept-without-reading). Without a log line, the iteration-2 decisions are unverifiable in production.

**Plan.** Router (the `/ark-workflow` Step 6 emission logic) writes ONE structured log line per triage invocation to `.ark-workflow/telemetry.log` (append-only, newline-delimited JSON). Fields:

```json
{
  "ts": "2026-04-13T10:15:23Z",
  "has_omc": true,
  "ark_skip_omc": false,
  "signals_matched": ["keyword", "heavy_weight"],
  "recommendation": "path_b",
  "path_selected": "path_b",
  "variant": "greenfield-heavy"
}
```

**Destination rationale.** `.ark-workflow/telemetry.log` (NOT stderr, NOT session log):
- stderr would pollute user-facing chain output.
- Session logs are user-authored narrative; telemetry is machine-structured.
- `.ark-workflow/` is already a tracked directory for chain state; telemetry fits the neighborhood.

**Anonymization.** No prompt text, no user identifier, no file paths from the prompt. Only: signals-matched list (the category names, not the matched text), variant name, recommendation vs. actual selection. `ARK_SKIP_OMC` state is logged to debug Scenario A.

**Retention + privacy.** `.ark-workflow/telemetry.log` is `.gitignore`d (like `.ark-workflow/current-chain.md` presumably already is — Phase 1 verification confirms). Rotation: append-only; no automatic rotation in v1.13.0 (follow-up). Users can `rm .ark-workflow/telemetry.log` at any time.

**Enables answering:**
- Path B selection rate per variant.
- Path B recommendation accuracy (recommended vs. actually selected).
- `[Show me both]` click rate as a proxy for Scenario B mitigation effectiveness.
- Downstream `ARK_SKIP_OMC=true` usage rate (Scenario A signal).

**Phase mapping.** Wired into Phase 1's `SKILL.md` Step 6 sub-section changes. Documented in `references/omc-integration.md` § Section 3 (one paragraph).

---

## Testing Strategy

### 1. Smoke test (end-to-end)

Invoke `/ark-workflow` with a Greenfield Heavy prompt in three states:

- **State A (OMC installed, no opt-out):** Expected output contains both `## Path A` and `### Path B (OMC-powered)` content, the 3-button override line, and no install hint. Telemetry line written with `has_omc=true`, `ark_skip_omc=false`.
- **State B (OMC absent):** Simulate by temporarily moving `~/.claude/plugins/cache/omc` aside and unsetting `omc` from PATH. Expected output contains Path A only, plus exactly this line: `NOTE: OMC not detected. Autonomous-execution chains hidden. Install: <URL>`. Telemetry: `has_omc=false`.
- **State C (OMC installed, `ARK_SKIP_OMC=true`):** Expected output identical to State B. Telemetry: `has_omc=false`, `ark_skip_omc=true`. Validates the emergency rollback.

Restore OMC before continuing.

### 2. Probe unit test (availability.py)

Add to `skills/ark-context-warmup/scripts/` test suite:

- `test_has_omc_true_when_cli_on_path` — pass `omc_cli_path="/fake/path/omc"` + `omc_cache_dir=None`; assert `has_omc is True`.
- `test_has_omc_true_when_cache_dir_exists` — pass `omc_cli_path=None` + `omc_cache_dir=tmp_path` (exists); assert `has_omc is True`.
- `test_has_omc_false_when_neither` — pass both as None / nonexistent; assert `has_omc is False` and `has_omc_skip_reason` matches `r"^OMC CLI not on PATH and OMC_CACHE_DIR .* not present$"`.

### 3. Chain-content regression (diff-based CI)

`skills/ark-context-warmup/scripts/check_path_b_coverage.py` (landed in Phase 1):

- Asserts per-variant byte-identity on canonicalized blocks; expected distinct hashes = 3; expected total blocks = `--expected-blocks` (default 19).
- Asserts every Path B section contains both (`/deep-interview` OR `/claude-history-ingest`) and literal `<<HANDBACK>>`.
- Fails CI on regression.

### 4. Bash probe unit test

`bats` test (or equivalent) that sources the `HAS_OMC` probe snippet in `SKILL.md` under 4 environments:
- Real OMC install (CLI + cache-dir): `HAS_OMC=true`.
- Cache-dir-only (CLI not on PATH): `HAS_OMC=true`.
- Neither: `HAS_OMC=false`.
- Real install + `ARK_SKIP_OMC=true`: `HAS_OMC=false` (rollback wins).

### 5. Observability contract test

Assert `.ark-workflow/telemetry.log` receives exactly one line per `/ark-workflow` invocation; assert JSON parses; assert required fields present.

---

## Dependencies & Risks

### Ordering constraints

1. **Phase 1 must precede Phase 2a/2b/3.** Chain Path B blocks reference `references/omc-integration.md`; that file is created in Phase 1. `check_path_b_coverage.py` lands in Phase 1 (Critic Required Change #13) so Phase 2a/2b/3 cannot pass verification without it.
2. **Phase 2a must precede Phase 2b.** They touch the same file (`hygiene.md`); Phase 2b verification uses `--expected-blocks 13` which requires Phase 2a's 10 to already be present.
3. **Phase 3 must follow Phase 2b.** Its `--expected-blocks 19` verification requires all prior blocks.
4. **Phase 4 must follow Phase 3.** CHANGELOG describes completed work, so version bump is last-but-one.
5. **Phase 5 can run in parallel with Phase 4** (vault artifacts are independent of code). Default sequential for reviewability.

### Risks

- **R1: Variant heterogeneity** — not every Path B block is mechanically identical (the 3 special cases in Phase 2b have scenario-specific adjustments). Mitigation: three enumerated templates (Vanilla + Special-A + Special-B) in reference Section 5; `check_path_b_coverage.py` enforces byte-identity within each template group. PASS (per Critic).
- **R2: Content-regression CI may lag** — addressed in Iteration 2: `check_path_b_coverage.py` lands in Phase 1 (Critic Required Change #13). Mitigation now ships with the foundation. PASS.
- **R3: OMC cache path literal drift** — addressed in Iteration 2: `OMC_CACHE_DIR` is a single-source canonical constant in `references/omc-integration.md` § Section 0 (Critic Required Change #11). Both consumers cite by comment pointer. PASS.
- **R4: `/autopilot` execution-only mode mechanism** — addressed conditionally in Iteration 2 via (a) fallback plan through `ARK_SKIP_OMC=true` env var (downstream can opt out entirely if the mechanism proves costly) and (b) pinned per-variant handback contracts in reference Section 4 (four sub-contracts: `/autopilot`, `/ralph`, `/ultrawork`, `/team`). Mitigated conditionally on Required Changes #6 and #7. Mechanism itself remains an open question (see Open Questions #1) — the Architect should pin `/autopilot`'s execution-only invocation flag before Phase 2a executor dispatches.
- **R5: Counter race** — if another task claims Arkskill-003 between plan approval and Phase 5, the counter will conflict. Mitigation: Phase 5 starts with `cat vault/TaskNotes/meta/Arkskill-counter` to verify `3`; if drifted, re-run `/ark-tasknotes` claim flow to get the next ID. PASS.

---

## Acceptance Criteria (mapped to phases)

| # | Spec Acceptance Criterion | Delivered in |
|---|----------------------------|--------------|
| AC1 | `SKILL.md` contains `HAS_OMC` availability probe (bash; `command -v omc` OR `~/.claude/plugins/cache/omc`; honors `ARK_SKIP_OMC=true`) | **Phase 1** |
| AC2 | All 7 chain files / 19 variants render Path A and Path B when `HAS_OMC=true` | **Phase 2a + 2b + 3** |
| AC3 | Every Path B chain uses variant-inherited handback with enumerated special cases. Validated by `check_path_b_coverage.py` against the per-variant expected-closeout table in `references/omc-integration.md` § Section 4 (byte-identity on canonicalized blocks, 3 distinct shapes allowed) | **Phase 2a + 2b + 3** (content), **Phase 1** (reference doc contract + CI check) |
| AC4 | Triage output when OMC installed recommends Path B on OR-any of 4 signals; renders `[Accept Path B] [Use Path A] [Show me both]`; Signal #1 detector matches the verbatim omc-reference keyword list | **Phase 1** (router Step 6 logic + Section 3 detector regex), **Phase 2a + 2b + 3** (chain-level block exists to be emitted) |
| AC5 | Triage output when OMC absent (or `ARK_SKIP_OMC=true`) emits only Path A + one-line install hint | **Phase 1** (router logic) |
| AC6 | `.ark-workflow/current-chain.md` during Path B shows Path B as the single checklist; `/autopilot` step notes `.omc/state/sessions/{id}/` but Ark file remains SoT | **Phase 1** (router Step 6 + reference doc authoritative-state clause) |
| AC7 | New `skills/ark-workflow/references/omc-integration.md` documents Section 0 (canonical constants), axis, skill map, when-B-beats-A, variant-inherited handback contract (four sub-contracts), 4 signals + OR rule, per-variant expected-closeout table, emergency-rollback | **Phase 1** |
| AC8 | `availability.py` extended to emit `has_omc`; Context Brief includes "OMC detected: yes/no" line | **Phase 1** |
| AC9 | `VERSION` bumped to `1.13.0`; `plugin.json` + `marketplace.json` aligned | **Phase 4** |
| AC10 | `CHANGELOG.md` v1.13.0 entry | **Phase 4** |
| AC11 | `vault/TaskNotes/Tasks/Epic/Arkskill-003-omc-integration.md` created | **Phase 5** |
| AC12 | `vault/Session-Logs/S007-OMC-Integration-Design.md` created | **Phase 5** |
| AC13 | `vault/Compiled-Insights/Execution-Philosophy-Dual-Mode.md` created | **Phase 5** |
| AC14 | Smoke test: Greenfield Heavy prompt output changes between OMC-detected, OMC-absent, `ARK_SKIP_OMC=true` states | **Testing Strategy § 1** |

All 14 machine-verifiable acceptance criteria map to a concrete phase or testing step. No AC is orphaned. Former AC15 and AC16 moved to Pipeline Gates below (Critic Required Change #12).

---

## Pipeline Gates

Process gates — NOT machine-verifiable ACs. Preserved as first-class pipeline checkpoints per Ark doctrine ("brainstorm → spec → `/codex` review → plan → `/codex` review → implement").

| # | Gate | Timing |
|---|------|--------|
| PG1 | `/codex review` on this plan | **Pre-Phase-1** (consensus completes → plan ships to codex) |
| PG2 | `/codex review` on the accumulated diff | **Post-Phase-4 / Pre-ship** |

---

## Open Questions (for Architect)

1. **`/autopilot` execution-only invocation mechanism.** Does `/autopilot` expose a flag (`--skip-phase-5`, `--execution-only`, etc.) to suppress its internal docs/ship Phase 5, or does Path B need to invoke autopilot and then signal a mid-flight handback via some other mechanism (checkpoint marker, environment variable)? The spec mandates skipping autopilot's Phase 5 but does not pin the mechanism. This affects the Path B Vanilla template wording in `references/omc-integration.md` § Section 5 and each Vanilla variant's Path B step 3. Conditionally mitigated by R4 (`ARK_SKIP_OMC=true` is a downstream escape hatch if the mechanism proves costly) and by Section 4.1's handback contract (if no flag exists, we document the manual-interrupt workaround).

2. **Step 6 emission shape when `HAS_OMC=true` and no signal fires.** If all 4 Path B signals are negative, should Step 6 still show a `[Show me both]` button, or emit Path A only silently? **Iteration 2 proposed default:** show `[Show me both]` as a small footer even without recommendation, to preserve discoverability. Architect to confirm before Phase 1 executor dispatches.

3. **Per-variant Path B appropriateness.** The plan marks Ship Standalone, Migration Light, Performance Light as "Path B discouraged but still shown." **Iteration 2 resolution:** show-always per spec's discoverability-over-neutrality principle. Knowledge-Capture Light is handled by the Special-B template (not discouraged).

---

## ADR — OMC ↔ /ark-workflow Dual-Mode Integration

**Status:** Accepted (ralplan consensus iteration 2, 2026-04-13). Architect and Critic both APPROVE.

### Decision

Integrate OMC into `/ark-workflow` via **Option A: per-chain Path B block with variant-inherited handback and enumerated special cases**, gated by an `HAS_OMC` availability probe mirroring the `/ark-context-warmup` probe idiom. All 19 chain variants across 7 scenario files gain a Path B block (`/deep-interview` → `/omc-plan --consensus` → `/autopilot` | `/ralph` | `/ultrawork` | `/team` execution-only → `<<HANDBACK>>` → variant-inherited Ark closeout starting at `/ark-code-review`). OMC remains optional with graceful degradation: when `HAS_OMC=false` OR `ARK_SKIP_OMC=true`, chains emit Path A only plus a one-line install hint.

### Drivers

1. **Dual-probe consumer lockstep.** `HAS_OMC` must be consumed by both the bash router (for chain branching alongside `HAS_UI`/`HAS_VAULT`) and the Python `availability.py` (for `/ark-context-warmup` Context Brief). Centralized `OMC_CACHE_DIR` constant in `references/omc-integration.md` § Section 0 prevents drift between the two implementations.
2. **Discoverability over neutrality.** User explicitly held aggressive OR-any signal recall across all 4 Path B triggers during deep-interview Round 4 Contrarian challenge. Integration must surface Path B when ANY signal matches, mitigated by the `[Show me both]` override button.
3. **Variant-inherited handback boundary.** All Path B chains must delegate planning + execution to OMC but return control to Ark for vault, ship, session log, and canary closeout. `/team` specifically hands back at the `team-verify → team-fix` boundary (bounded-remediation reserved for Ark's own review).

### Alternatives Considered

- **Option B — Runtime template generation** (one template + `{{include path-b-block}}` markers in each chain file): DRY-safer and cheaper to mutate when `/autopilot` invocation contract shifts in a future OMC release. **Rejected:** breaks human auditability of `chains/*.md`, which is load-bearing for Ark's user-in-the-loop philosophy; the new byte-identity CI check in `check_path_b_coverage.py` achieves most of Option B's drift-safety at ~19 file edits of one-time cost.
- **Option C — Hard OMC dependency** (chain files reference OMC skills without `HAS_OMC` guards): simplest code. **Rejected:** violates spec Non-Goal "OMC is an optional dependency." ark-skills plugin must remain installable and usable without OMC on consumer projects.

### Why Chosen

Option A is locally optimal under three constraints that no alternative satisfies simultaneously: (a) preserve human auditability of chain markdown; (b) enforce machine-verifiable dual-mode coverage across all 19 variants; (c) ship in a single PR with ≤5 files per phase (Agent Directive #2). The byte-identity CI check retroactively gives Option A's static chain files the drift-safety benefit of Option B's template approach without the runtime-engine coupling.

### Consequences

**Positive:**
- All 19 Ark chain variants gain autonomous-execution path without changing the stepwise Ark-native default.
- OMC installation remains optional; Ark chains execute identically on systems without OMC, with a surfaced install hint.
- `.ark-workflow/current-chain.md` remains single source of truth; `.omc/state/` is transient, preserving Ark's resume semantics.
- Telemetry at `.ark-workflow/telemetry.log` (gitignored) enables post-hoc measurement of Path B selection rate + success rate.
- `ARK_SKIP_OMC=true` env var provides user-facing rollback without requiring a plugin downgrade.
- Commit protocol with git trailers (`Constraint:`, `Rejected:`, `Directive:`, `Confidence:`, `Scope-risk:`, `Not-tested:`) enforces durable decision-context trails in future maintenance.

**Negative / accepted trade-offs:**
- Migration path: v1.12.0 → v1.13.0 consumers see new output when OMC is detected. Consumers hardcoding `grep "HAS_OMC=false"` may silently suppress Path B — documented in Section 3 and Pre-mortem Scenario A.
- Phase 2 hygiene.md double-touch (Phase 2a + Phase 2b) — disclosed in plan line 266–268; non-overlapping line ranges with CI gate between phases.
- `/autopilot` execution-only mechanism unresolved (Open Question #1) — conditionally mitigated by `ARK_SKIP_OMC` rollback + pinned `/autopilot` handback contract in Section 4.1.
- Aggressive OR-any signal recall may over-surface Path B for users whose early tasks hit 1 signal (typically Heavy weight) — mitigated by `[Accept Path B]`/`[Use Path A]`/`[Show me both]` override UX.

### Follow-ups (post-merge)

1. **Pin `/autopilot` execution-only mechanism** before Phase 2a dispatches. Architect to confirm flag-or-marker; fallback is `OMC_EXECUTION_ONLY=1` env var wrapper if no OMC-side flag exists.
2. **Telemetry rotation policy** for `.ark-workflow/telemetry.log` (v1.14.x follow-up per Architect note). Current plan writes unbounded; retention limit to be added.
3. **Evaluate fifth Section 4 sub-contract** if `/ccg` (tri-model consensus) enters Path B as its own execution engine variant. Currently Path B lists 4 execution engines (`/autopilot` / `/ralph` / `/ultrawork` / `/team`); `/ccg` would be the 5th with its own handback semantics.
4. **Absorb Architect executor-level concerns during Phase 1 execution:**
   - Regex-strip `--(quick|thorough)` in `check_path_b_coverage.py` canonicalization (not just `{weight}` placeholder).
   - Add explicit `.gitignore` grep assertion in Phase 1 verification (not "presumably").
   - Add Audit-Only byte-identity assertion between Phase 2a and Phase 2b.
5. **Downstream grep-pinning detection** — identify consumer CLAUDE.md files that hardcode `HAS_OMC=false` checks; proactively notify maintainers before v1.13.0 ships (tracked in `open-questions.md`).

### References

- Spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md`
- RALPLAN-DR summary: lines 15–60 of this plan
- Ralplan consensus iterations: Architect iter 1 ITERATE (3 findings) → Critic iter 1 ITERATE (13 required changes) → Planner iter 2 revision → Architect iter 2 APPROVE (3 executor concerns) → Critic iter 2 APPROVE
- Agent Directives: `~/.claude/CLAUDE.md` (phased execution, forced verification, no semantic search)
- Commit Protocol reference: `.claude/omc-reference/SKILL.md` lines 112–141
