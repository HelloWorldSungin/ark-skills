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
  planning (`/omc-plan --consensus`), autonomous execution (`/autopilot` | `/ralph`
  | `/ultrawork` | `/team`), then handback to Ark for closeout.

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
| Greenfield Heavy | `/autopilot` or `/ultrawork` | Heavy multi-module benefits from parallel lanes |
| Bugfix Light / Medium | `/autopilot` | Linear investigation + fix |
| Bugfix Heavy | `/autopilot` or `/ralph` | Loop-to-verified when reproduction is finicky |
| Hygiene Light / Medium / Heavy | `/autopilot` | Cleanup follows consensus plan deterministically |
| Hygiene Audit-Only | `/autopilot` (findings mode) | Findings-only; no code mutation |
| Ship Standalone | `/autopilot` | Discouraged but available; Ship is already mechanical |
| Knowledge-Capture Light / Full | `/autopilot` | Capture + synthesis fits consensus-then-execute |
| Migration Light / Medium | `/autopilot` | Linear upgrade path |
| Migration Heavy | `/team` | Cross-module coordination benefits from multi-agent |
| Performance Light | `/autopilot` | Discouraged but available |
| Performance Medium / Heavy | `/ralph` | Loop until benchmark target met |

When the engine differs from `/autopilot`, the chain's Path B block annotates the
suggestion. All engines use the same `<<HANDBACK>>` marker but with
engine-specific handback-boundary semantics (see Section 4).

---

## Section 3 — When Path B Beats Path A

### The 4 signals (OR rule)

Path B is recommended when **any** of these fires:

1. **Keyword** — prompt contains an OMC keyword.
2. **Heavy weight** — triaged class is Heavy.
3. **Multi-module scope** — task touches ≥3 independent modules.
4. **Explicit autonomy** — user explicitly requests hands-off execution.

### Signal #1 detector specification

Verbatim keyword list from `.claude/skills/omc-reference/SKILL.md` lines 89–101:

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

Four engine-specific sub-contracts follow.

### 4.1 `/autopilot` handback (vanilla)

**Used by:** Greenfield / Bugfix / Hygiene (non-Audit-Only) / Ship / Migration
non-Heavy / Performance non-Medium-Heavy.

`<<HANDBACK>>` fires **after `/autopilot`'s internal Phase 4 (execution)
completes**; `/autopilot`'s internal Phase 5 (docs/ship) is **SKIPPED**. Control
returns to Ark at the variant's closeout:

- Heavy → `/ark-code-review --thorough`
- Light / Medium → `/ark-code-review --quick`

### 4.2 `/ralph` handback

**Used by:** Bugfix Heavy / Performance Medium+Heavy alternates.

`<<HANDBACK>>` fires **after `/ralph`'s loop-to-verified exits with success**.
Ark closeout inherits from the variant's Path A tail as in 4.1.

### 4.3 `/ultrawork` handback

**Used by:** Greenfield Heavy multi-module alternates.

`<<HANDBACK>>` fires **after the last parallel lane's completion signal**. Ark
closeout inherits as in 4.1.

### 4.4 `/team` handback

**Used by:** Migration Heavy alternate.

`<<HANDBACK>>` fires **after `team-verify`, before `team-fix`** (the bounded
remediation loop per `.claude/skills/omc-reference/SKILL.md` lines 106–108).

- If `team-verify` reports failures, Ark's `/ark-code-review --thorough` runs
  first; bounded `team-fix` remediation is only invoked from within Ark's review
  if Ark's own review concurs there are remaining defects.
- This keeps Ark as the last-word reviewer and avoids OMC-internal
  bounded-remediation running on the far side of the handback.

### Per-Variant Expected Closeout Table

What `check_path_b_coverage.py` validates against — byte-identity on
canonicalized blocks, 3 allowed shapes.

| Variant | Shape | Starts at | Ends at |
|---------|-------|-----------|---------|
| Greenfield Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Bugfix Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Hygiene Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Hygiene Audit-Only | Special-A | `/wiki-update` | STOP (no code review, no ship) |
| Ship Standalone | Vanilla | `/ark-code-review --thorough` | `/claude-history-ingest` |
| Knowledge-Capture Light | Special-B | `/wiki-update` | `/claude-history-ingest` |
| Knowledge-Capture Full | Special-B | `/wiki-update` | `/claude-history-ingest` |
| Migration Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |
| Performance Light / Medium / Heavy | Vanilla | `/ark-code-review --{quick\|thorough}` | `/claude-history-ingest` |

Total: 19 rows. Three distinct shapes (Vanilla, Special-A, Special-B).
`check_path_b_coverage.py` canonicalizes each block (strip scenario headers and
weight markers) and hashes it; expected distinct hashes = 3; expected total
blocks = 19.

---

## Section 5 — Path B Block Templates

Three templates the chain files copy in verbatim (with per-variant weight/headline
substitution). These are what `check_path_b_coverage.py` hashes against.

### Template Vanilla (16 variants)

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

Variant-specific weight substitution: Light → `--quick`, Medium → `--quick`,
Heavy → `--thorough`. (Ship Standalone always uses `--thorough`.)

### Template Special-A (Hygiene Audit-Only)

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

### Template Special-B (Knowledge-Capture Light / Full)

`/deep-interview` is inapplicable (capture is reflective, not prospective);
substitute `/claude-history-ingest` as step 1.

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

---

## Section 6 — `/autopilot` Execution-Only Invocation

Open Question #1 from the implementation plan. Final mechanism TBD; fallback
contract is:

**Fallback mechanism (v1.13.0 ships this):** the chain's step 3 invokes
`/autopilot` in an environment scope with `OMC_EXECUTION_ONLY=1` exported. If
OMC honors this env var, its internal Phase 5 is skipped; if not, the chain
relies on the user intercepting before autopilot's Phase 5 starts (documented
in the Path B block). `ARK_SKIP_OMC=true` remains the downstream escape hatch.

**Path B step 3 wording (current):** `/autopilot` — execution only; skips
autopilot's internal Phase 5 (docs/ship). See § Section 4.1.

**Post-Phase-2a ADR follow-up:** confirm whether OMC exposes a first-class flag
(`--skip-phase-5`, `--execution-only`) or a session marker. If so, replace the
env-var fallback with the first-class mechanism in v1.14.x.

---

## Cross-References

- Implementation plan: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md`
- Spec: `.omc/specs/deep-interview-omc-ark-workflow-integration.md`
- OMC reference: `.claude/skills/omc-reference/SKILL.md`
- Availability probe: `skills/ark-context-warmup/scripts/availability.py`
- Bash probe + Step 6 logic: `skills/ark-workflow/SKILL.md`
- CI coverage check: `skills/ark-context-warmup/scripts/check_path_b_coverage.py`
