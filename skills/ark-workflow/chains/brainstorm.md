# Brainstorm

*Pre-triage exploration — shape a fuzzy idea into a crisp spec or plan. Terminates with an **interactive pivot** (Continuous Brainstorm): offer to triage implementation immediately, or archive and stop. No implementation, no ship.*

## Single variant

*No weight class. Brainstorm is always one pass — if the idea proves large after exploration, the pivot at step 4 triggers re-triage into Greenfield/Migration/Performance.*

0. `/ark-context-warmup` — load recent + relevant project context
1. `/office-hours` (if gstack) — YC forcing questions (startup mode) or design-thinking exploration (builder mode); writes a design doc to `docs/superpowers/specs/`
2. `/plan-ceo-review` (if gstack, optional) — rethink scope/ambition before locking the spec; skip when the idea is obviously scoped and the question is purely mechanical
3. Commit the design doc to `docs/superpowers/specs/` (or the project's spec directory)
4. **Pivot gate (Continuous Brainstorm)** — ask the user:

   > *"Spec finalized at `docs/superpowers/specs/{filename}`. Ready to triage implementation now? [Y/n]"*

   **If Y (default):** archive this chain file — move `.ark-workflow/current-chain.md` to `.ark-workflow/archive/YYYY-MM-DD-brainstorm.md` (matches `references/continuity.md` archive convention). Then **continue applying `/ark-workflow`'s triage algorithm inline** against the committed spec as the new task prompt: re-run Project Discovery, Scenario Detection (the spec now carries creation intent, so likely Greenfield/Migration/Performance), Weight Classification, Chain Lookup, Condition Resolution, Presentation. Write a fresh `.ark-workflow/current-chain.md` for the resolved implementation chain. **Not a recursive `/ark-workflow` skill invocation** — Brainstorm's pivot is the single authorized inline re-triage per Step 7's handoff contract.

   **If N:** archive this chain file to `.ark-workflow/archive/YYYY-MM-DD-brainstorm.md`. The user can re-invoke `/ark-workflow` later with the spec to enter an implementation chain. Archival prevents session-start rehydration from offering to "continue" a finished Brainstorm (zombie-chain avoidance).

   **Non-interactive mode:** the pivot gate assumes an interactive response. In auto-mode, CI, unattended background execution, or any context where user input cannot be collected, default to **Y** (continue to triage). Archival still happens; the inline re-triage proceeds without the prompt.

### Path B (OMC-powered — if HAS_OMC=true)

*Deep ambiguity crystallization + multi-model consensus for scope exploration — no execution, no ship. Uses only OMC skills (`/deep-interview`, `/ralplan`, optional `/ccg`) — fully consistent with Path B gstack-independence.*

0. `/ark-context-warmup` — same as Path A
1. `/deep-interview` — crystallize ambiguity (ambiguity threshold 20%)
2. `/ralplan` — consensus planning for scope/approach (or `/ccg` **[probe-gated §7]** for multi-model review when vendor CLIs are available)
3. Commit scope brief
4. **Pivot gate** — same interactive prompt as Path A; same archive-then-re-invoke-or-stop semantics.

### Degradation

Brainstorm is the **single exception** to the global silent-default degradation policy (SKILL.md § gstack planning availability trigger). When a user explicitly invokes the Brainstorm scenario, they've asked for gstack-powered exploration — silently substituting would hide the capability change.

**If `HAS_GSTACK_PLANNING=false` AND `GSTACK_STATE_PRESENT=false` (gstack absent):** fall back to superpowers `/brainstorming` for step 1; skip step 2 (no gstack-independent substitute for `/plan-ceo-review`). Emit:

> "Brainstorm scenario: gstack planning skills not available. Using `/brainstorming` (superpowers) for scope exploration. The pivot gate at step 4 still fires."

**If `HAS_GSTACK_PLANNING=false` AND `GSTACK_STATE_PRESENT=true` (broken install):** emit the standard broken-install notice (SKILL.md § gstack planning availability trigger) in addition to the fallback notice above, then fall back to `/brainstorming`.

**If both `HAS_GSTACK_PLANNING=false` and `HAS_OMC=false`:** only Path A fallback is available; step 1 uses `/brainstorming`. Chain still runs, pivot gate still fires.

### Chain file semantics

Brainstorm does NOT set a `handoff_marker` in `.ark-workflow/current-chain.md`. Instead, the pivot gate archives the chain file on completion (either branch of Y/N). This is different from implementation chains, which use `handoff_marker` to signal resumable design-phase handoffs.

If the user abandons Brainstorm mid-flight (never reaches step 4), the chain file remains in `.ark-workflow/` and will be detected by the normal stale-chain logic (`references/continuity.md` § Stale Chain Detection) on next session start — same as any other abandoned chain.
