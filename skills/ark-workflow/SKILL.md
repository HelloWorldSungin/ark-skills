---
name: ark-workflow
description: Task triage and skill chain orchestration. Use when starting any non-trivial task to determine the optimal workflow. Triggers on "build", "create", "fix", "bug", "ship", "deploy", "document", "cleanup", "refactor", "audit", "upgrade", "migrate", "slow", "optimize", "benchmark", "new feature", "investigate". Do NOT use for trivial single-file changes with no ambiguity.
---

# Ark Workflow

Triage any task into a weight class (light / medium / heavy), detect the scenario, and output the optimal skill chain. This is the entry point for all non-trivial work across Ark projects.

## Project Discovery

Follow the context-discovery pattern documented in this plugin's CLAUDE.md:

1. Read the `CLAUDE.md` in the current working directory
2. If it's a monorepo hub (contains a "Projects" table linking to sub-project CLAUDEs), follow the link for the active project based on your current working directory
3. Extract from the most specific CLAUDE.md:
   - Project name (from header or table)
   - Vault root (parent of project docs and TaskNotes)
   - Project docs path (from "Obsidian Vault" row)
   - TaskNotes path (from "Task Management" row)
4. If a required field is missing, note it — vault skills will be skipped for projects without vault configuration

5. Detect project characteristics:

```bash
# Has UI? Check for frontend indicators (any one is sufficient)
HAS_UI=false
if [ -f "package.json" ]; then
  grep -qE "react|vue|svelte|next|angular|@remix|solid-js" package.json 2>/dev/null && HAS_UI=true
fi
[ -f "tsconfig.json" ] && grep -q "jsx\|tsx" tsconfig.json 2>/dev/null && HAS_UI=true
echo "HAS_UI=$HAS_UI"

# Has standard docs outside docs/superpowers/?
HAS_STANDARD_DOCS=false
for f in README.md ARCHITECTURE.md CONTRIBUTING.md CHANGELOG.md; do
  [ -f "$f" ] && HAS_STANDARD_DOCS=true && break
done
echo "HAS_STANDARD_DOCS=$HAS_STANDARD_DOCS"

# Has vault? (extracted from CLAUDE.md in step 3 above)
# If vault root was found and directory exists: HAS_VAULT=true
# If no vault configured or directory missing: HAS_VAULT=false
echo "HAS_VAULT=$HAS_VAULT"

# Has CI/CD?
HAS_CI=false
[ -d ".github/workflows" ] || [ -f ".gitlab-ci.yml" ] || [ -f "Dockerfile" ] && HAS_CI=true
echo "HAS_CI=$HAS_CI"

# Has OMC? (oh-my-claudecode — autonomous execution framework)
# OMC_CACHE_DIR canonical: ~/.claude/plugins/cache/omc
# (see references/omc-integration.md § Section 0)
if command -v omc >/dev/null 2>&1 || [ -d "$HOME/.claude/plugins/cache/omc" ]; then
  HAS_OMC=true
else
  HAS_OMC=false
fi
# ARK_SKIP_OMC=true forces HAS_OMC=false regardless of detection
# (emergency rollback for downstream projects — see references/omc-integration.md § Section 3)
[ "$ARK_SKIP_OMC" = "true" ] && HAS_OMC=false
export HAS_OMC
echo "HAS_OMC=$HAS_OMC"

# Has gstack planning? — SEMANTIC probe (agent-executed, not bash).
#
# CANONICAL SIGNAL: session skill-list. This matches the detection pattern used by
# /ark-health and /ark-onboard (plugin availability = "skill loadable in current session",
# not filesystem inspection).
#
# Procedure for the agent:
#   Read the skill list in your current session's system-reminder context.
#   Search for any of these gstack planning skills by name:
#     - autoplan
#     - office-hours
#     - plan-ceo-review
#     - plan-design-review
#     - plan-eng-review
#     - plan-devex-review
#   If at least one is present, set HAS_GSTACK_PLANNING=true.
#   Otherwise set HAS_GSTACK_PLANNING=false.
#
# ADVISORY cross-check (filesystem, non-authoritative — used only to distinguish
# "gstack absent" from "gstack installed but broken"):
GSTACK_STATE_PRESENT=false
if [ -d "$HOME/.gstack" ] && [ -f "$HOME/.gstack/config.yaml" ]; then
  GSTACK_STATE_PRESENT=true
fi
[ "$ARK_SKIP_GSTACK" = "true" ] && GSTACK_STATE_PRESENT=false
export GSTACK_STATE_PRESENT
echo "GSTACK_STATE_PRESENT=$GSTACK_STATE_PRESENT"
# Agent then records HAS_GSTACK_PLANNING (from the semantic probe above) alongside
# GSTACK_STATE_PRESENT. The combination gives three operator states:
#   - absent:  HAS_GSTACK_PLANNING=false AND GSTACK_STATE_PRESENT=false  → silent
#   - healthy: HAS_GSTACK_PLANNING=true                                  → use gstack
#   - broken:  HAS_GSTACK_PLANNING=false AND GSTACK_STATE_PRESENT=true   → emit notice

# Vendor CLI availability — gates `/ask codex` and `/ccg` chain steps
# (see references/omc-integration.md § Section 7 External Advisor Probe Gates)
# Canonical binary names in § Section 0 (CODEX_CLI_BIN, GEMINI_CLI_BIN)
if command -v codex >/dev/null 2>&1; then
  HAS_CODEX=true
else
  HAS_CODEX=false
fi
if command -v gemini >/dev/null 2>&1; then
  HAS_GEMINI=true
else
  HAS_GEMINI=false
fi
export HAS_CODEX HAS_GEMINI
echo "HAS_CODEX=$HAS_CODEX"
echo "HAS_GEMINI=$HAS_GEMINI"
```

6. Store these values for condition resolution in later steps.
7. If `HAS_VAULT=false`, tell the user: "No vault configured for this project. Vault skills (`/wiki-update`, `/wiki-ingest`, `/cross-linker`, `/wiki-lint`, etc.) will be skipped. Run `/wiki-setup` to initialize a vault if needed."

8. **Early exits** — check prerequisites before proceeding to triage:
   - If the user's request is clearly Knowledge Capture (matches "document", "vault", "catch up", "knowledge", "wiki") AND `HAS_VAULT=false`: stop and tell the user to run `/wiki-setup` first. Do not proceed to Step 2 (Scenario Detection).

## Scenario Detection

Identify which scenario applies based on the user's request. Ask if ambiguous.

| Scenario | Trigger Patterns | Description |
|----------|-----------------|-------------|
| **Greenfield** | "build", "create", "add feature", "new component", "implement" | Building something new from scratch |
| **Bugfix** | "fix", "bug", "broken", "error", "investigate", "not working", "crash" | Something's broken, find and fix it |
| **Ship** | "ship", "deploy", "push", "PR", "merge", "release", "cherry-pick" | Getting code reviewed, merged, deployed |
| **Knowledge Capture** | "document", "vault", "catch up", "knowledge", "wiki", "update docs" | Catch up the vault with what's happened |
| **Hygiene** | "cleanup", "refactor", "audit", "hygiene", "dead code", "maintenance" | Cleanup, refactor, code quality |
| **Migration** | "upgrade", "migrate", "bump major", "framework upgrade", "version bump" | Upgrading dependencies, frameworks, or platform versions |
| **Performance** | "slow", "optimize", "latency", "benchmark", "profile", "performance" | Improving speed, reducing resource usage |
| **Brainstorm** | "brainstorm", "I have an idea", "should I build", "should we build", "worth building", "shape this idea", "is this worth" | Pre-triage exploration — turn fuzzy intent into a crisp spec/plan ready to re-triage (creation-intent only; "explore"/"think through" alone are NOT Brainstorm triggers — too generic) |

**Security routing — two distinct paths:**

1. **Security audit / review** (assessment only, no code changes expected): "security audit", "security review", "audit our X", "review the security of Y" → route to **Hygiene: Audit-Only** variant. Ends with findings report, no implementation or ship steps.

2. **Security hardening** (remediation expected): "harden", "fix security", "improve auth security", "address vulnerabilities" → route to **Hygiene** (Light/Medium/Heavy) with `/cso` as **mandatory step 1**.

   **How to wire the mandatory early `/cso` into the chain output (resolution rule):**
   a. Look up the standard Hygiene chain for the triaged weight (Light/Medium/Heavy)
   b. **Prepend** `/cso` as the new step 1. All original steps shift down by 1.
   c. **Dedup**: remove any later `/cso` step from the chain (whether unconditional like Hygiene Heavy's "step 4" or conditional like Hygiene Light's "if security-relevant"). `/cso` runs exactly once per chain execution.
   d. Present the resolved chain to the user with the `/cso` at step 1 and a note: "Security hardening detected — `/cso` promoted to step 1; later `/cso` deduped."

If the user's intent is ambiguous between audit and hardening, ask:
> Are you asking for an audit (findings only) or hardening (findings + fixes + ship)?

**Multi-scenario resolution:** If the user's request matches multiple scenarios (e.g., "fix this bug and ship it"), use the primary scenario (bugfix) — the ship phase is included in the bugfix workflow. If the prompt describes multiple distinct tasks (numbered, bulleted, or in prose), read `references/batch-triage.md` and follow that algorithm instead.

If no pattern matches clearly, ask:

> What kind of task is this?
> A) Greenfield — building something new
> B) Bugfix — something's broken
> C) Ship — getting code out the door
> D) Knowledge Capture — documenting what happened
> E) Hygiene — cleanup, refactor, audit
> F) Migration — upgrading dependencies or platforms
> G) Performance — optimizing speed or resources
> H) Brainstorm — shape a fuzzy idea before classifying (produces a spec, no implementation)

## Triage

**Rule:** Risk sets the floor. Decision density can escalate but never downgrade. File count and duration are informational context only.

**Step 1 — Classify by risk:**

| Risk | Floor Class | Signals |
|------|-------------|---------|
| **Low** | Light | Internal changes, non-breaking, no auth/data/infra touch points |
| **Moderate** | Medium | API surface changes, schema modifications, external integration changes |
| **High** | Heavy | Auth/permissions, data migrations, infrastructure, secrets, breaking changes to shared interfaces |

**Step 2 — Escalate by decision density:**

| Decision density | Effect |
|------------------|--------|
| Obvious fix, clear path | No change — stay at risk floor |
| Some trade-offs to consider | Escalate Light → Medium (if currently Light) |
| Architecture decisions required | Escalate to Heavy (regardless of current floor) |

**Rule:** Escalation only increases the class. A Heavy risk stays Heavy even if the fix is obvious. A Light risk with architecture decisions becomes Heavy.

**Examples:**

| Task | Risk | Decision Density | Result |
|------|------|------------------|--------|
| Rename 20 test utility functions | Low | Obvious | **Light** |
| Fix one auth validation function | High | Obvious | **Heavy** (risk floor) |
| Redesign internal caching layer (20 files) | Low | Architecture | **Heavy** (escalated) |
| Add logging to 15 modules | Low | Obvious | **Light** |
| Add feature flag infrastructure | High | Trade-offs | **Heavy** (risk floor) |
| Refactor state management across modules | Low | Trade-offs | **Medium** (escalated) |

**Context signals** (informational, not classification inputs — show to user for transparency):

| Signal | Description |
|--------|-------------|
| File count | 1-3 (small), 4-10 (moderate), 10+ (large) |
| Duration estimate | Quick (<30min), moderate (hours), extended (half-day+) |

**Disambiguation prompts:**

If risk is unclear:
> How risky is this task?
> A) Low risk — internal, non-breaking, no auth/data/infra
> B) Moderate risk — API changes, schema changes, external integrations
> C) High risk — auth, data migration, infra, secrets, permissions

If decision density is unclear:
> How many trade-offs or architecture decisions does this involve?
> A) Obvious — clear path, no real choices
> B) Some trade-offs — a few decisions to make
> C) Architecture decisions — multiple significant choices, design work needed

**Scenarios that skip the full triage:**
- Ship — no weight class needed
- Knowledge Capture — uses Light/Full split
- Hygiene Audit-Only — no weight class (it's always findings-only)
- Brainstorm — no weight class (produces spec/plan artifact, stops before implementation)

**Knowledge Capture classification:** Light if syncing recent changes or updating a few pages. Full if catching up after extended period, rebuilding tags, or ingesting external documents.

**Re-triage rule:** If a task reveals more complexity mid-flight (e.g., a "light" bug turns out to involve auth, or an investigation reveals architecture decisions are required), escalate to the appropriate class and pick up the remaining phases from there. Don't restart — just add the phases you would have run. If the scenario itself changes (e.g., Bugfix → Greenfield redesign), see `references/troubleshooting.md` § Re-triage for scenario shift handling.

## Workflow

This is the concrete algorithm. Follow these steps in order:

### Step 1: Run Project Discovery
Execute the Project Discovery section above. Record: `HAS_UI`, `HAS_VAULT`, `HAS_STANDARD_DOCS`, `HAS_CI`, `HAS_GSTACK_PLANNING` (from session skill-list probe), `GSTACK_STATE_PRESENT` (from filesystem cross-check).
Check early exits — if the user's request is clearly Knowledge Capture AND `HAS_VAULT=false`, stop and tell the user to run `/wiki-setup` first.

### Step 2: Detect Scenario
Match the user's request against the Scenario Detection table. If the prompt describes multiple distinct tasks (see Batch Triage trigger), read `references/batch-triage.md` and follow that algorithm instead of Steps 3-6. For security requests, use the two-path security routing (audit vs hardening). If ambiguous, ask the disambiguation question.

### Step 3: Classify Weight
Classify using risk-primary triage with decision-density escalation. Ship skips this step. Knowledge Capture uses Light/Full split. Hygiene Audit-Only has no weight class.

### Step 4: Look Up Skill Chain
Read `chains/{scenario}.md` (e.g., `chains/bugfix.md`). Each chain file contains sections for the applicable weight variants — Light/Medium/Heavy, or Light/Full for Knowledge Capture, or Audit-Only/Light/Medium/Heavy for Hygiene. Select the section matching your triaged weight class.

**Filename mapping:** `greenfield.md`, `bugfix.md`, `ship.md` (standalone — no weight class), `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`, `brainstorm.md` (standalone — no weight class).

If security hardening triggered mandatory early `/cso`, apply the Dedup rule documented at the bottom of `chains/hygiene.md`.

### Step 5: Resolve Conditions
Walk through the chain and resolve every conditional using Condition Resolution definitions:
- `(if UI)` → check `HAS_UI`. If false, output "Skipping `/qa` — no UI detected"
- `(if vault)` → check `HAS_VAULT`. If false, skip the step silently
- `(if standard docs exist)` → check `HAS_STANDARD_DOCS`. If false, output "Skipping `/document-release` — no standard docs found"
- `(if gstack)` → check `HAS_GSTACK_PLANNING`. If true, include the step. If false AND `GSTACK_STATE_PRESENT=false`: skip **silently** (gstack absent — not an error, no notice). If false AND `GSTACK_STATE_PRESENT=true`: emit the broken-install notice once per chain and skip the step (see Condition Resolution § gstack planning availability trigger).
- `(if security-relevant)` → evaluate against the security triggers in Condition Resolution
- `(if deploy risk)` → evaluate against the deploy risk triggers in Condition Resolution
- `(if developer-facing surface)` → evaluate against the developer-facing triggers in Condition Resolution
- `(if any item involves broken/unexpected behavior)` → evaluate against the investigation triggers in Condition Resolution

### Step 6: Present the Resolved Chain
Output the numbered skill chain with all conditions resolved. Include the session handoff marker if applicable.

**Substitution rendering rule (Path A Heavy only):** when a step carries an inline substitution note (pattern: `*(substitution: replaced by X when HAS_GSTACK_PLANNING=true — ...)*`), render per `HAS_GSTACK_PLANNING`:

- **`HAS_GSTACK_PLANNING=true`:** rewrite the step text to show the substituted skill (e.g., Greenfield Heavy step 4 renders as `` `/autoplan` — plan review (gstack multi-persona bundle) `` rather than `/ccg ...`). Drop the substitution note from user-facing output — the substitution has already been applied.
- **`HAS_GSTACK_PLANNING=false`:** render the default skill (`/ccg`) without the substitution note. The note is an agent-only rendering hint, not user-visible metadata.

Chain-file storage stays canonical (one authoritative text with the substitution note), and the user-facing render shows exactly one skill per step. No ambiguity about which skill will actually execute.

### Step 6 (continued): Dual-path presentation when HAS_OMC=true

When `HAS_OMC=true`, every chain variant has both a `## Path A` (Ark-native) and a
`### Path B (OMC-powered)` block in its chain file. Render both, then emit a
recommendation + 3-button override based on the OR-any signal rule.

**The 4 signals** (OR — ANY one firing recommends Path B):

1. **Keyword signal** — the user's prompt contains an OMC keyword from the verbatim
   list (`autopilot`, `ralph`, `ulw`, `ultrawork`, `ccg`, `ralplan`, `deep interview`,
   `deep-interview`, `deslop`, `anti-slop`, `deep-analyze`, `tdd`, `deepsearch`,
   `ultrathink`, `cancelomc`, `team`, `/team`). Detector: case-insensitive regex with
   word-boundary anchors.
2. **Heavy weight** — triaged weight class is Heavy (autonomous pipeline amortizes
   best on multi-hour work).
3. **Multi-module scope** — task touches ≥3 independent modules (mechanical
   parallelism payoff for `/ultrawork`).
4. **Explicit autonomy** — user explicitly requests hands-off execution ("just do
   it", "handle it", "run it to completion").

See `references/omc-integration.md` § Section 3 for the full detector specification.

**Recommendation UX (when any signal fires):**

```
Recommended: Path B (OMC-powered — autonomous execution, ~1–4 hours, ~3 checkpoints)

  [Accept Path B]   [Use Path A]   [Show me both]
```

**Path B acceptance probe** (only when `HAS_OMC=true`): before rendering the `[Accept Path B]` button, run:

```bash
PATHB_WARN=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format path-b-acceptance \
  --state-path .omc/state/hud-stdin-cache.json \
  --expected-cwd "$(pwd)" \
  "${SESSION_FLAG[@]}" \
  --max-age-seconds 300 2>/dev/null)
```

If `$PATHB_WARN` is non-empty, display it on its own line above the `[Accept Path B]` button. (`SESSION_FLAG` is resolved in Step 6.5 below; if Step 6.5 hasn't run yet for this invocation, resolve it inline using the same snippet.) Example output: `⚠ Context at 32% (~320k). Path B adds parent-session coordination on top — consider /clear or /compact before accepting.`

Include an inline one-line checkpoint-density + duration estimate next to the
recommendation so users know what Path B costs before accepting.

**Footer UX (when no signal fires):** render a small `[Show me both]` footer link
so discoverability is preserved for users whose first task doesn't trip a signal.

**Degradation (HAS_OMC=false):** emit Path A only, followed by exactly one line:
`NOTE: OMC not detected. Autonomous-execution chains hidden. Install: <URL>` (URL
sourced from `references/omc-integration.md` § Section 0 `INSTALL_HINT_URL`).

**Telemetry:** write one newline-delimited JSON line to `.ark-workflow/telemetry.log`
per triage invocation with fields `{ts, has_omc, ark_skip_omc, signals_matched,
recommendation, path_selected, variant}`. No prompt text, no user identifier.
`.ark-workflow/telemetry.log` is `.gitignore`d (covered by the existing
`.ark-workflow/` ignore line).

### Step 6.5: Activate Continuity

**Resolve the current session id once for all probe invocations in this section** (only when `HAS_OMC=true`):

```bash
SESSION_ID="${CLAUDE_SESSION_ID:-$(python3 -c '
import json, pathlib
p = pathlib.Path(".omc/state/hud-state.json")
try:
    data = json.loads(p.read_text())
    sid = data.get("sessionId") or data.get("session_id") or ""
    if isinstance(sid, str) and sid.strip():
        print(sid.strip())
except Exception:
    pass
' 2>/dev/null)}"
SESSION_FLAG=()
if [ -n "$SESSION_ID" ]; then
  SESSION_FLAG=(--expected-session-id "$SESSION_ID")
fi
```

**Chain-entry probe** — run before executing step 1 of the chain (only when `HAS_OMC=true`):

```bash
ENTRY=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format step-boundary \
  --state-path .omc/state/hud-stdin-cache.json \
  --chain-path .ark-workflow/current-chain.md \
  --expected-cwd "$(pwd)" \
  "${SESSION_FLAG[@]}" \
  --max-age-seconds 300 2>/dev/null)
```

If `$ENTRY` is non-empty, display it verbatim and pause for user decision before executing step 1. Apply the same proceed/reset/(c) handling as the per-step probe in the "after each step" bullet below. Entry-time probes pass `--max-age-seconds 300` (5 minutes) so a stale cache file from a previous session is rejected; the helper still prefers `--expected-session-id` when available. The step-boundary mode is reused at entry; the helper auto-detects "zero completed steps" and renders the entry menu (option (a) shown unavailable, answer set `[b/c/proceed]`).

- Create TodoWrite tasks for each step in the resolved chain
- Compute task fields for `/ark-context-warmup` (step 0 of every chain). `/ark-workflow` needs the same `ARK_SKILLS_ROOT` resolution as the warm-up skill — mirror `/ark-context-warmup` SKILL.md's Project Discovery section verbatim so dev-mode runs inside the ark-skills worktree resolve helpers from the branch under test rather than a stale installed copy:
  ```bash
  if [ -n "${CLAUDE_PLUGIN_DIR:-}" ] && [ -d "$CLAUDE_PLUGIN_DIR" ]; then
      ARK_SKILLS_ROOT="$CLAUDE_PLUGIN_DIR"
  elif [ -f "$(pwd)/.claude-plugin/marketplace.json" ]; then
      # CWD is the ark-skills repo itself (dev/test mode)
      ARK_SKILLS_ROOT="$(pwd)"
  else
      ARK_SKILLS_ROOT=$(find ~/.claude/plugins -maxdepth 6 -type d -name ark-skills 2>/dev/null | head -1)
  fi
  TASK_TEXT="<verbatim user request>"
  TASK_NORMALIZED=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" normalize "$TASK_TEXT")
  TASK_SUMMARY=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" summary "$TASK_TEXT")
  TASK_HASH=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" hash "$TASK_NORMALIZED")
  CHAIN_ID=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" chain-id)
  ```
- Write `.ark-workflow/current-chain.md` at project root with this frontmatter:

  ---
  scenario: {scenario}
  weight: {weight}
  batch: false
  created: {ISO-8601 timestamp}
  chain_id: {CHAIN_ID}
  task_text: |
    {TASK_TEXT — multi-line verbatim, indented 2 spaces}
  task_summary: |-
    {TASK_SUMMARY — single-line, indented 2 spaces; block scalar avoids YAML escaping for ':', '#', '|', quotes}
  task_normalized: {TASK_NORMALIZED}
  task_hash: {TASK_HASH}
  handoff_marker: null
  handoff_instructions: null
  ---
  # Current Chain: {scenario}-{weight}
  ## Steps
  [numbered checklist of chain steps, each as `- [ ]`]
  ## Notes

- Add `.ark-workflow/` to `.gitignore` if not already present
- After each step:
  1. Check off the step in `.ark-workflow/current-chain.md` via the atomic helper (not by hand-editing):
     ```bash
     python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
       --format check-off --step-index {N} \
       --chain-path .ark-workflow/current-chain.md
     ```
  2. Update the TodoWrite task to `completed`
  3. **Run the step-boundary probe** (only when `HAS_OMC=true`):
     ```bash
     MENU=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
       --format step-boundary \
       --state-path .omc/state/hud-stdin-cache.json \
       --chain-path .ark-workflow/current-chain.md \
       --expected-cwd "$(pwd)" \
       "${SESSION_FLAG[@]}" 2>/dev/null)
     ```
     If `$MENU` is non-empty, display it verbatim and pause for user decision. Then:
     - If `proceed`: invoke `--format record-proceed` (no extra args; helper self-detects current level and persists `proceed_past_level: nudge` only when current level is `nudge`; strong is never silenced).
     - If `(a)` or `(b)`: **before** running `/compact` or `/clear`, the LLM MUST invoke `/wiki-handoff` to flush a validated session bridge to `.omc/wiki/`. See § Wiki-handoff invariant below.

       ```bash
       python3 "$ARK_SKILLS_ROOT/skills/wiki-handoff/scripts/write_bridge.py" \
           --chain-id "$CHAIN_ID" --task-text "$TASK_TEXT" --scenario "$SCENARIO" \
           --step-index "$STEP_IDX" --step-count "$STEP_COUNT" \
           --session-id "$SESSION_ID" \
           --open-threads "<LLM-supplied, specific>" \
           --next-steps "<LLM-supplied, specific>" \
           --notes "<LLM-supplied>" --done-summary "<LLM-supplied>" \
           --git-diff-stat "$(git diff --stat HEAD~10..HEAD 2>/dev/null || echo '')"
       ```

       Verify exit code 0 before proceeding. On exit code 2 (schema rejection), re-invoke with specific file paths, decision points, and target files — do NOT proceed to `/compact`/`/clear` with an unwritten bridge.

       Then run the user's chosen action (`/compact` or `/clear`), then invoke the probe's `--format record-reset`.

     - If `(c)`: no bridge write (subagent dispatch preserves parent context). No state write; subagent wraps Next step.

**§ Wiki-handoff invariant:** Options `(a)` and `(b)` invoke `/wiki-handoff` BEFORE the destructive action and BEFORE `record-reset`. Schema rejection (exit 2) blocks the action — the LLM must re-invoke with specifics. Option `(c)` does NOT invoke `/wiki-handoff`.
     If `$MENU` is empty, proceed silently.
  4. Mark the next TodoWrite task `in_progress`
  5. Announce `Next: [skill] — [purpose]`
- For batch-mode chain file format, cross-session resume, `handoff_marker` semantics, stale-chain detection, and compaction recovery: see `references/continuity.md`

### Step 7: Hand Off
The skill is done. The user or Claude follows the chain, invoking each skill in order. `/ark-workflow` does not invoke downstream skills itself. After each step, the agent updates the chain file + task and announces the next step.

## Condition Resolution

When presenting a skill chain, resolve all conditions using Project Discovery values. Present the chain with conditions already evaluated.

**Security-relevant triggers (for `/cso`):**
- Auth/permissions changes (both read AND write paths)
- Secrets handling (creation, rotation, storage, access patterns)
- Dependency upgrades: major/breaking version bumps, packages with known CVEs, packages adding native modules
- Data exposure: new PII access, new data flows, storage changes, new data processing
- Infrastructure changes: networking, DNS, tunnels, systemd units, container configs
- External API integrations: adding OR removing
- New internal APIs that other services will call

**Deploy risk triggers (for `/canary`):**
- All security-relevant triggers above
- Database schema changes (even non-breaking — adding nullable columns, indices)
- Cache invalidation changes
- Feature flag rollouts
- Config changes affecting production
- Changes to request handling or middleware ordering

**Investigation triggers (for `/investigate` in Hygiene):**
- Broken functionality, silent failures, unexpected errors, crashes, or data loss — even when framed as "tech debt" or "cleanup"
- If the root cause isn't obvious from reading the code, investigate before fixing

**UI triggers (for `/qa`, `/design-review`):**
- Project has frontend dependencies (react, vue, svelte, next, angular, @remix, solid-js) AND the current task touches UI-facing code

**UI-with-design-reference trigger (for `/visual-verdict`, `/plan-design-review`):**
- All UI triggers above AND a design reference is present in the repo. Signals that indicate a design reference exists:
  - A `design/`, `designs/`, `mocks/`, or `mockups/` directory at repo root
  - A `DESIGN.md`, `design-system.md`, or similar design-spec file outside `docs/superpowers/`
  - A Figma export file (`.fig`, `.sketch`, `.xd`) or PNG/SVG mockup linked from README or CONTRIBUTING
  - An explicit design reference named in the user's task prompt
- If UI is present but no design reference is found, output "Skipping `/visual-verdict` — no design reference found" and continue without the step.

**Developer-facing surface trigger (for `/plan-devex-review`):**
- Task adds or modifies any of:
  - Public APIs (REST, gRPC, GraphQL endpoints consumed by external clients or other internal services)
  - CLIs, command-line tools, or shell interfaces users run directly
  - SDKs, client libraries, or language bindings
  - Plugin interfaces or extension points
  - Developer documentation for any of the above
- Not triggered by: purely internal module APIs, private helpers, or refactors that don't change external surface area.
- If no developer-facing surface is involved, output "Skipping `/plan-devex-review` — no developer-facing surface" and continue without the step.

**gstack planning availability trigger (for `/office-hours`, `/plan-ceo-review`, `/plan-design-review`, `/plan-eng-review`, `/plan-devex-review`, `/autoplan`):**

Detection is session-capability — see Project Discovery step 6. Three operator states:

- **Healthy** (`HAS_GSTACK_PLANNING=true`): include the skill as a step.
- **Absent** (`HAS_GSTACK_PLANNING=false` AND `GSTACK_STATE_PRESENT=false`): **silent skip**. No notice. Users without gstack shouldn't be reminded every chain.
- **Broken-install** (`HAS_GSTACK_PLANNING=false` AND `GSTACK_STATE_PRESENT=true`): gstack state dir exists but planning skills are not loadable in this session. Emit **once per chain** (not once per skipped step): "⚠ gstack detected at `$HOME/.gstack` but planning skills are not loadable in this session. Run `/ark-health` to diagnose, or set `ARK_SKIP_GSTACK=true` to suppress." Then skip the step.

Brainstorm scenario is the sole exception — it has a dedicated fallback to superpowers `/brainstorming` and emits a pivot-specific message. See `chains/brainstorm.md` § Degradation.

**Heavy planning authority substitution (Path A, when `HAS_GSTACK_PLANNING=true`):**

Heavy chains already include a `/ccg` plan-review step. When gstack planning is available, **replace** that `/ccg` step with the gstack planning authority — do not stack. This prevents redundant review committees (the "Review Hell" anti-pattern).

| Chain | Replaced step | Gstack substitute | Rationale |
|-------|---------------|-------------------|-----------|
| Greenfield Heavy | step 4 (`/ccg` plan review) | `/autoplan` (CEO+design+eng+DX bundle) | Greenfield has the broadest decision surface — full multi-persona review pays off |
| Migration Heavy | step 3 (`/ccg` migration plan review) | `/plan-eng-review` | Migrations are architecture-dominant; CEO/design/DX reviews rarely add value |
| Performance Heavy | step 4 (`/ccg` optimization plan review) | `/plan-eng-review` | Same as Migration — architecture-dominant |

**Spec-review `/ccg` stays:** the earlier `/ccg` step in each Heavy chain reviews the SPEC (correctness sanity-check, multi-model), not the PLAN. It serves a different purpose and is not replaced.

**Scope:** This substitution applies to **Path A only**. Path B is gstack-independent by design.

**Path B gstack-independence (product decision):**

Path B (OMC-powered) chains deliberately do NOT incorporate gstack planning skills:

- Path B's execution engines (`/autopilot`, `/team`) include their own internal review phases.
- Layering gstack planning on top would reintroduce stacked-committee ceremony — the exact anti-pattern Heavy Path A substitution avoids.
- Users who want gstack multi-persona review should select Path A.

When `HAS_OMC=true` AND `HAS_GSTACK_PLANNING=true`, both paths render. Users choose based on desired style: multi-persona alignment via gstack (Path A) vs autonomous execution via OMC (Path B).

**Standard docs trigger (for `/document-release`):**
- Project has README.md, ARCHITECTURE.md, CONTRIBUTING.md, or CHANGELOG.md outside of `docs/superpowers/`

## When Things Change

- **Mid-flight re-triage** (weight escalation or scenario shift): stop at the current step, reclassify using the Triage section above, pick up the remaining phases from the new class. For scenario-shift pivot examples, see `references/troubleshooting.md`.
- **Scope-retreat pivot (Greenfield → Brainstorm):** if step 1 `/brainstorming` reveals the user isn't sure the feature should be built at all (scope-uncertainty signals: "I don't know if this is the right thing", "should we even build this", "what's the real problem here", extended re-framing of the goal), stop, `/checkpoint` any discovery, and pivot to the Brainstorm scenario — re-invoke `/ark-workflow` with a Brainstorm-framed prompt. Brainstorm's `/office-hours` (gstack) or `/brainstorming` fallback will do the scope-challenging work, then the Continuous Brainstorm pivot gate re-triages into an implementation chain once scope is clear. This is a *downshift*, distinct from the upshift rule above — Greenfield is implementation-committed; Brainstorm is scope-challenging.
- **Design-phase session handoffs**: chain files specify inline `handoff_marker` values where applicable. For per-scenario handoff points and guidance on when to break sessions mid-implementation, see `references/troubleshooting.md`.
- **Step failure or unexpected state**: see `references/troubleshooting.md` for per-failure guidance (failed QA, failed deploy, review disagreement, flaky tests, spec invalidation, canary failure, vault tooling failure, hygiene reveals bugs, migration breaks tests, batch item blocks others).

## Session Habits

Three habits shape context longevity across a chain. The probe in Step 6.5
surfaces them contextually; keep the underlying habits in mind between probes:

- **Rewind beats correction.** When a step produces a wrong result, prefer
  `/rewind` (double-Esc) over replying "that didn't work, try X." Rewind drops
  the failed attempt from context; correction stacks it. The parent context
  stays lean, and the second try gets a cleaner prompt.
- **New task, new session.** When the current chain completes and the next
  task is unrelated, `/clear` and start fresh. Grey area: closely-coupled
  follow-ups (e.g., documenting a feature you just shipped) may reuse context.
- **`/compact` with a forward brief.** When compacting mid-chain, steer the
  summary: `/compact focus on the auth refactor; drop the test debugging`.
  The probe's mitigation menu pre-fills this template using the current chain
  state — use it verbatim or edit.

## Routing Rules Template

See `references/routing-template.md` for the copy-paste block to add to project CLAUDE.md files. (Not loaded at runtime — this is human-only documentation.)

## File Map

**Chain files (`chains/`)** — loaded once per triage after scenario detection:
- `chains/greenfield.md`, `chains/bugfix.md`, `chains/ship.md`, `chains/knowledge-capture.md`, `chains/hygiene.md`, `chains/migration.md`, `chains/performance.md`, `chains/brainstorm.md`

**References (`references/`)** — loaded only when their trigger fires:
- `batch-triage.md` — multi-item algorithm (trigger: Step 2 multi-item detection)
- `continuity.md` — batch/resume/handoff/stale/compaction protocols (trigger: pay-per-use branches of Step 6.5)
- `troubleshooting.md` — re-triage, handoff details, failure recovery (trigger: mid-flight events)
- `routing-template.md` — CLAUDE.md copy-paste block (trigger: never runtime)

### Centralized-Vault Suggestion

During triage, check the vault layout. If `vault` is a real directory (not a symlink) AND no `embedded` opt-out is present in CLAUDE.md, surface the externalization recommendation:

```bash
if [ -d vault ] && [ ! -L vault ]; then
  if ! grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md 2>/dev/null; then
    echo ""
    echo "ℹ️  Heads-up: your vault is embedded inside the project repo."
    echo "   For worktree/Obsidian-app consistency, consider running:"
    echo "   /ark-onboard  (will generate an externalization plan)"
    echo ""
  fi
fi
```

This is advisory only — does not block workflow routing.
