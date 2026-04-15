# OMC Integration Reference

Consolidating reference for the `/ark-workflow` ↔ OMC (oh-my-claudecode) dual-mode
integration. This file is the single source of truth for canonical constants, axis
definitions, per-chain skill maps, signal rules, and variant-inherited handback
contracts. Other files cite this one by comment pointer; nothing is re-quoted
inline.

---

## Section 0 — Canonical Constants

Single-source-of-truth table. All other files reference these by comment pointer;
no inline re-quotation.

| Constant | Value | Used by |
|----------|-------|---------|
| `OMC_CACHE_DIR` | `~/.claude/plugins/cache/omc` | `skills/ark-workflow/SKILL.md` (bash), `skills/ark-context-warmup/scripts/availability.py` (Python) |
| `OMC_CLI_BIN` | `omc` | `skills/ark-workflow/SKILL.md` (bash probe uses `command -v omc`) |
| `INSTALL_HINT_URL` | `https://github.com/anthropics/oh-my-claudecode` | `/ark-workflow` Step 6 degradation footer |
| `HANDBACK_MARKER` | `<<HANDBACK>>` | Every Path B block in `skills/ark-workflow/chains/*.md` |

Any literal duplication of these values in code or docs is a drift risk and should
be replaced with a comment pointer to this section.

---

## Section 1 — Two Philosophies

User-facing axis vs. implementation-side axis — these are orthogonal.

**User-facing axis: _Ark-native_ vs. _OMC-powered_.**

- **Ark-native (Path A):** step-by-step, user-in-the-loop, discrete skills at every
  decision point. User sees each step, approves each transition. This is the
  default and is never removed.
- **OMC-powered (Path B):** front-loaded judgment (`/deep-interview`), consensus
  planning (`/omc-plan --consensus`), autonomous execution via `/autopilot`
  (uniform default, auto-skips Phase 0+1 when Path B's pre-placed artifacts
  are present) or `/team` (Migration Heavy only — see § Section 4.2), then
  handback to Ark for closeout. Per the 2026-04-14 uniformity decision, Path B
  no longer routes directly to `/ralph` or `/ultrawork` as standalone engines;
  those engines are invoked internally inside autopilot's Phase 2 (Execution).

**Implementation-side axis: _checkpoint-density_.** Path A is high checkpoint-density
(user approves every step); Path B is low checkpoint-density (user approves the
spec + plan, then the executor runs mostly unattended until handback). The
discoverability bias in Step 6 (show Path B when any signal fires) is a *user-facing*
axis decision; the *implementation-side* axis governs how many interruptions each
path inserts per hour of executor work.

---

## Section 2 — Per-Chain Skill Map

Which OMC engine is the natural fit per chain variant.

| Variant | Primary OMC engine | Rationale |
|---------|--------------------|-----------|
| Greenfield Light / Medium | `/autopilot` | Vanilla pipeline; single module |
| Greenfield Heavy | `/autopilot` | Heavy multi-module parallelism handled inside autopilot's Phase 2 (Execution via internal /ultrawork) |
| Bugfix Light / Medium | `/autopilot` | Linear investigation + fix |
| Bugfix Heavy | `/autopilot` | Reproduction-finicky bugs handled inside autopilot's Phase 2 (Execution via internal /ralph loop) |
| Hygiene Light / Medium / Heavy | `/autopilot` | Cleanup follows consensus plan deterministically |
| Hygiene Audit-Only | `/autopilot` (findings mode) | Findings-only; no code mutation |
| Knowledge-Capture Light | `/autopilot` | Capture + synthesis fits consensus-then-execute |
| Knowledge-Capture Full | — (no Path B) | Full capture is too broad/branchy for auto-routed single-engine execution; users invoke `/omc-teams 1:gemini` manually when desired |
| Migration Light | `/autopilot` | Linear upgrade path |
| Migration Medium | `/autopilot` | Linear upgrade path; R10 prepends `/external-context` as pre-step 1 to gather authoritative framework migration guides (counters stale training-data reasoning) |
| Migration Heavy | `/team` | Cross-module coordination benefits from multi-agent (sole non-/autopilot chain variant); R10 prepends `/external-context` as pre-step 1 for the same framework-doc authoritativeness reason |
| Performance Light | `/autopilot` | Discouraged but available |
| Performance Medium / Heavy | `/autopilot` | Benchmark-target loops handled inside autopilot's Phase 2 (Execution via internal /ralph loop) |

Migration Heavy uses `/team`; all other Path B variants use `/autopilot`
(the 2026-04-14 uniformity decision — see memory file
`project_ark_workflow_uniform_path_b.md` and audit R5). Engine-specific
handback-boundary semantics are documented in § Section 4.

---

## Section 3 — When Path B Beats Path A

### The 4 signals (OR rule)

Path B is recommended when **any** of these fires:

1. **Keyword** — prompt contains an OMC keyword.
2. **Heavy weight** — triaged class is Heavy.
3. **Multi-module scope** — task touches ≥3 independent modules (LLM-judgment
   call during triage — no mechanical counter exists in SKILL.md or any
   helper script; grep-verified).
4. **Explicit autonomy** — user explicitly requests hands-off execution.

### Signal #1 detector specification

Superset of the canonical keyword list at `.claude/skills/omc-reference/SKILL.md`
lines 89–101. Ark adds the following non-canonical keywords to trigger Path B
recommendation:

- `team` / `/team` — explicit team-orchestration invocation
- `ultrawork` — long-form of the canonical `ulw`
- `deep-interview` — hyphenated form alongside the canonical `deep interview`

Canonical omc-reference list (verbatim):

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

**Detector:** case-insensitive regex with word-boundary anchors:

```
\b(autopilot|ralph|ulw|ultrawork|ccg|ralplan|deep[- ]interview|deslop|anti-slop|deep-analyze|tdd|deepsearch|ultrathink|cancelomc|/?team)\b
```

Flags: `re.IGNORECASE`. The unquoted two-word form `deep interview` matches as a
phrase; the slash form `/team` and the bare form `team` both trigger.

### Discoverability over neutrality

User explicitly held aggressive OR-any recall during deep-interview Round 4
(Contrarian challenge). Over-surfacing is mitigated by the 3-button UX
(`[Accept Path B] [Use Path A] [Show me both]`), not by narrowing the signal set.

### Emergency rollback: `ARK_SKIP_OMC=true`

Downstream projects can force Path B invisibility by exporting this env var
regardless of detection:

```bash
ARK_SKIP_OMC=true /ark-workflow "<prompt>"
```

Intended for incident response and downstream projects that explicitly opt out.
The `HAS_OMC` bash probe in `skills/ark-workflow/SKILL.md` honors this env var.

### Telemetry

One newline-delimited JSON line per triage invocation, appended to
`.ark-workflow/telemetry.log`. Fields:

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

No prompt text, no user identifier, no file paths from the prompt.
`.ark-workflow/telemetry.log` is `.gitignore`d (the `.ark-workflow/` line already
covers it — Phase 1 verifies). No automatic rotation in v1.13.0; follow-up item.

---

## Section 4 — Variant-Inherited Handback Contract

Every Path B chain uses `<<HANDBACK>>` after the OMC engine completes its
autonomous portion. Control then returns to Ark, which resumes that variant's
Path A tail starting at the variant-specific closeout step.

Two engine-specific sub-contracts follow plus a crash-recovery procedure. The
retired `/ralph` and `/ultrawork` subsections have been removed per the
2026-04-14 uniformity decision; their handback boundaries are now
encapsulated inside `/autopilot`'s internal Phase 2 (Execution via Ralph +
Ultrawork).

### 4.1 `/autopilot` handback (uniform engine)

**Used by:** all Path B chain variants except Migration Heavy. Engine-specific
subsections for `/ralph` and `/ultrawork` have been retired — see the
2026-04-14 uniformity decision at
`~/.claude/projects/-Users-sunginkim--superset-projects-ark-skills/memory/project_ark_workflow_uniform_path_b.md`
and audit recommendation R5 at `.ark-workflow/audits/omc-routing-audit-2026-04-14.md`.

**Handback boundary.** `/autopilot` runs all six of its internal phases
(0 Expansion → 1 Planning → 2 Execution → 3 QA → 4 Validation → 5 Cleanup
per `~/.claude/plugins/cache/omc/oh-my-claudecode/4.11.5/skills/autopilot/SKILL.md:39-72`).
Because every Path B in ark-workflow pre-places `.omc/specs/deep-interview-*.md`
and `.omc/plans/ralplan-*.md` as steps 1 + 2, `/autopilot` **auto-skips its
Phase 0 and Phase 1** (autopilot SKILL.md:41-42) and starts at Phase 2
(Execution via Ralph + Ultrawork internally).

`<<HANDBACK>>` fires **after `/autopilot`'s Phase 5 (Cleanup) completes** —
i.e., after the full internal pipeline exits. Control returns to Ark at the
variant's closeout:

- Heavy → `/ark-code-review --thorough`
- Light / Medium → `/ark-code-review --quick`

**On intentional defense-in-depth.** Ark's closeout `/ark-code-review` is a
**second-layer review** by design. Autopilot's internal Phase 4 (Validation)
is an OMC-internal gate optimized for the consensus plan's invariants; Ark's
`/ark-code-review` is Ark-project-specific and enforces Ark conventions
(vault frontmatter, taxonomy, etc.) that OMC does not know about. The
two-layer review is the canonical ark-workflow posture — it is not
accidental duplication.

### 4.2 `/team` handback

**Used by:** Migration Heavy (sole `/team` chain variant).

`<<HANDBACK>>` fires **after `team-verify`, before `team-fix`** (the bounded
remediation loop per `.claude/skills/omc-reference/SKILL.md` lines 106–108).

- If `team-verify` reports failures, Ark's `/ark-code-review --thorough` runs
  first; bounded `team-fix` remediation is only invoked from within Ark's review
  if Ark's own review concurs there are remaining defects.
- This keeps Ark as the last-word reviewer and avoids OMC-internal
  bounded-remediation running on the far side of the handback.

### 4.3 Mid-execution crash recovery

If the OMC engine crashes, stalls, or exits abnormally before emitting
`<<HANDBACK>>`, the chain is stuck at step 3 (or step 4 if `<<HANDBACK>>`
partially emitted). Recovery procedure:

1. **Inspect `.omc/state/sessions/{id}/`** for the engine's last-known state
   (checkpoint files, exit codes, partial artifacts). This is OMC-internal
   and not authoritative, but gives a hint about whether the engine made
   durable progress.
2. **Read `.ark-workflow/current-chain.md`** — this is Ark's authoritative
   SoT. The `handoff_marker` frontmatter field and the step checklist show
   exactly where the chain stopped.
3. **Choose one of three recovery paths:**
   - **Re-run step 3 from scratch** — safe for idempotent engines; the OMC
     session is discarded and a fresh `/deep-interview` + `/omc-plan` +
     engine execution replays.
   - **Resume within step 3** — if the engine supports resume (e.g.,
     `/autopilot` reads `.omc/state/autopilot-state.json`), the engine's own
     resume flow continues. Ark's chain file is unchanged; it waits for
     `<<HANDBACK>>` as if the original attempt never paused.
   - **Abandon Path B, finish Path A** — pivot the chain file to the
     variant's Path A tail. Manually edit `current-chain.md` to replace
     steps 3-5 with the Path A closeout sequence and proceed.

The principle: **`.ark-workflow/current-chain.md` remains the single source
of truth** for recovery. `.omc/state/sessions/` is advisory-only — never
consult it for "is the chain complete" determination.

### Per-Variant Expected Closeout Table

What `check_path_b_coverage.py` validates against — byte-identity on
canonicalized blocks, 4 allowed shapes (post-uniformity: Vanilla + /team +
Special-A + Special-B; the previously-enumerated /ralph and /ultrawork
shapes were retired in R2).

Rows are grouped — variants sharing identical shape/engine/closeout collapse
into a single row. Expand parenthetical labels against the variant column to
recover the 17 per-variant assignments. Knowledge-Capture Full has no Path B
(removed in v1.14.0); Ship Standalone has no Path B (removed in R17 of the
2026-04-15 uniformity refactor) — neither has a row in this table.

| Variants (grouped) | Shape | Engine (step 3) | Starts at | Ends at |
|---|---|---|---|---|
| Greenfield Light / Medium / Heavy | Vanilla | `/autopilot` | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Bugfix Light / Medium / Heavy | Vanilla | `/autopilot` | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Hygiene Light / Medium / Heavy | Vanilla | `/autopilot` | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Hygiene Audit-Only | Special-A | `/autopilot` | `/wiki-update` | STOP (findings-only) |
| Knowledge-Capture Light | Special-B | `/autopilot` | `/wiki-update` | `/claude-history-ingest` |
| Migration Light / Medium | Vanilla | `/autopilot` | `/ark-code-review --quick` | `/claude-history-ingest` |
| Migration Heavy | /team | `/team` | `/ark-code-review --thorough` | `/claude-history-ingest` |
| Performance Light / Medium / Heavy | Vanilla | `/autopilot` | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |

8 rows representing **17 variants** across **4 distinct classifier shapes**
(Vanilla 14 + /team 1 + Special-A 1 + Special-B 1). `check_path_b_coverage.py`
canonicalizes each block (strip scenario headers and weight markers) and
hashes it; expected total blocks = 17. The CI script reads chain files
directly, so row-grouping in this table does not affect coverage enforcement.

**Note on hash count vs shape count.** Raw-text canonicalized hashes
currently total **5**, not 4. Migration Medium + Migration Heavy prepend
`/external-context` as pre-step 1 (R10), making their block bodies one line
longer than other variants — distinct hashes from the base vanilla/team
forms. The `_classify_shape` classifier keys on engine + closeout markers
(not step count), so classifier-visible shapes remain 4; hash ceiling in
`check_path_b_coverage.py` is 5 to accommodate the raw-text variant. Adding
more pre-step variants in the future would raise this ceiling further
unless canonicalization is extended to strip step-count-variance.

---

## Section 5 — Path B Block Templates

Three templates the chain files copy in verbatim (with per-variant weight/headline
substitution). These are what `check_path_b_coverage.py` hashes against.

### Template Vanilla (14 variants)

```markdown
### Path B (OMC-powered — if HAS_OMC=true)

*Front-loaded judgment + autonomous execution + Ark closeout.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on spec (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus plan (Planner → Architect → Critic)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts from steps 1+2. See `references/omc-integration.md` § Section 4.1 for the handback boundary.
4. `<<HANDBACK>>` — Ark resumes authority; `.ark-workflow/current-chain.md` remains SoT. `.omc/state/sessions/{id}/` annotated in Notes; never consumed by Ark resume logic.
5. **Ark closeout** — run Path A's closeout steps from `/ark-code-review --{weight}` onward for this same variant. Closeout terminates at `/claude-history-ingest`. See `references/omc-integration.md` § Section 4 expected-closeout table (Vanilla row).
```

Variant-specific weight substitution: Light → `--quick`, Medium → `--quick`,
Heavy → `--thorough`.

### Template Special-A (Hygiene Audit-Only)

```markdown
### Path B (OMC-powered — if HAS_OMC=true)

*Findings-only — no code review, no ship.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — converge on audit scope (ambiguity threshold 20%)
2. `/omc-plan --consensus` — multi-agent consensus audit plan
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts; produces findings document
4. `<<HANDBACK>>` — Ark resumes authority
5. **Ark closeout (Special-A):** `/wiki-update` (record findings in vault) → STOP. No code review, no ship — findings-only chain. See `references/omc-integration.md` § Section 4 (Special-A row).
```

### Template Special-B (Knowledge-Capture Light / Full)

`/deep-interview` is inapplicable (capture is reflective, not prospective);
substitute `/claude-history-ingest` as step 1.

```markdown
### Path B (OMC-powered — if HAS_OMC=true)

*Reflective capture with front-loaded mining + autonomous synthesis.*

0. `/ark-context-warmup` — same as Path A
1. `/claude-history-ingest` — mine recent conversations as capture source (substitutes for `/deep-interview` since capture is reflective)
2. `/omc-plan --consensus` — plan the capture (wiki pages, tags, cross-links)
3. `/autopilot` — full pipeline; auto-skips Phase 0+1 when it detects the pre-placed artifacts; runs `/wiki-ingest` + `/cross-linker` + `/tag-taxonomy`
4. `<<HANDBACK>>` — Ark resumes authority
5. **Ark closeout (Special-B):** `/wiki-update` (finalize session log + epic) → `/claude-history-ingest` (final mining sweep). No code review, no ship — capture-only chain. See `references/omc-integration.md` § Section 4 (Special-B row).
```

---

## Section 6 — `/autopilot` Invocation (uniformity, no env var)

**Open Question #1 from the v1.13.0 implementation plan is now resolved.**
There is no need for an execution-only flag or env var. Under the 2026-04-14
uniformity decision, Path B invokes `/autopilot` as a full-pipeline run; the
artifacts pre-placed by steps 1 + 2 cause `/autopilot` to auto-skip its
internal Phase 0 and Phase 1 (see § Section 4.1). Phase 5 (Cleanup)
completes normally; `<<HANDBACK>>` fires after it, and Ark resumes for the
closeout `/ark-code-review` as a second-layer review.

**The fictional env-var fallback from v1.13.0** (an "execution-only" gate
intended to keep autopilot from running its Phase 5) **is retired.** It was
never implemented in OMC runtime — a cache-wide grep of OMC v4.11.5 source
returns zero matches for the proposed env-var name. The mechanism never
existed.

**No operator burden.** No probe, no env export, no interactive verification
is required before enabling Path B. The handback boundary is defined by
autopilot's Phase 5 exit, which is engine-native exit semantics.

**Migration Heavy exception.** `/team` has its own handback boundary (see
§ Section 4.2 — handback after `team-verify`, before `team-fix`). It does
not compose through the same auto-skip mechanism.

---

## Cross-References

- Implementation plan: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md`
- Spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md`
- OMC reference: `.claude/skills/omc-reference/SKILL.md`
- Availability probe: `skills/ark-context-warmup/scripts/availability.py`
- Bash probe + Step 6 logic: `skills/ark-workflow/SKILL.md`
- CI coverage check: `skills/ark-context-warmup/scripts/check_path_b_coverage.py`
