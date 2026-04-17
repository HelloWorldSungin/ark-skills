# Ark Workflow — Context Probe Design Spec

**Date:** 2026-04-17
**Scope:** Add step-boundary context-budget awareness to `/ark-workflow` by reading the Claude Code statusline payload cached at `.omc/state/hud-stdin-cache.json`. Includes one new helper script with six CLI modes (`raw`, `step-boundary`, `path-b-acceptance`, `record-proceed`, `record-reset`, `check-off`), targeted changes to `/ark-workflow`'s SKILL.md, a "Session habits" coaching block appended to the skill body + routing template, and a `/ark-update` version bump to ship the coaching block to downstream projects.
**Status:** Approved (brainstorming phase); revised after first `/ccg` advisor round; spec awaiting user review before `writing-plans`.

> **Terminology note.** **Step 6.5** in this spec refers to the "Activate Continuity" section inside `/ark-workflow`'s `SKILL.md` — the bullet list that runs between chain steps to check off progress, update TodoWrite state, and announce Next. This spec modifies the "after each step" bullet inside Step 6.5 and adds one probe call at Step 6's Path B dual-path presentation.

## Problem

`/ark-workflow` emits a skill chain and hands off. Between steps, the agent (or user) invokes each skill in order. At no point does the workflow surface the **actual context budget** of the session. In practice, long chains silently push the parent session past the context-rot zone (~300-400k tokens on a 1M window — the zone where attention spreads thin enough to degrade reasoning), producing the symptoms described in Thariq's Claude Code session-management article: bad compactions, dropped findings, blind re-reads of files, and degraded reasoning quality precisely when the stakes are highest (Heavy chains — migrations, hardening, redesigns).

The Claude Code statusline hook writes a live snapshot of token usage to `.omc/state/hud-stdin-cache.json` (when OMC is installed). `/ark-workflow` does not read it. The result: `/ark-workflow` is flying blind about the same data Claude Code already computes and caches for free.

## Goal

At each chain step boundary — i.e., the "after each step" bullet inside Step 6.5 — read the cached statusline payload and, if the session has crossed a budget threshold, surface a **three-option mitigation menu** before announcing the next step:

1. `/compact focus on [pre-filled forward brief]`
2. `/clear` and restart with the forward brief as the opening message
3. Delegate the next step to a subagent so the parent stays lean

Probe also fires at two other discrete boundaries:
- **Chain entry** (once, as the first action inside Step 6.5): detects "starting a chain at 30%+" so the user can `/clear` before the chain begins.
- **Path B acceptance** (inside Step 6's dual-path presentation): detects "user is about to accept a 1-4 hour autonomous run while already near the rot zone." Most actionable moment for the autonomous path.

(A chain-exit informational probe was considered and dropped from v1: the next chain's entry probe will read the same cache anyway, so an explicit exit probe adds surface area without new signal.)

The probe is **measurement, not prediction** — it reports what the session actually consumed, not what it might consume based on per-step estimates. This is deliberate: estimates drift, measurements don't.

Separately, ship a short "Session habits" coaching block (rewind-before-correction, new-task-means-new-session, compact-with-forward-brief) in `/ark-workflow`'s SKILL.md and in `references/routing-template.md` so downstream projects adopt it via `/ark-update`.

## Non-Goals

- Not a cost projection engine. No per-step estimates, no cost table, no cumulative-tokens column.
- Not a runtime monitor. The probe runs at discrete boundaries (chain entry, step boundaries, Path B acceptance), not continuously. No daemon, no hooks into Claude Code internals beyond reading the cached JSON file.
- Not a blocker. A probe failure (missing file, malformed JSON, `HAS_OMC=false`, stale cache, session mismatch) degrades silently to today's behavior.
- Not a Path B inner-loop concern. OMC's autonomous loop manages its own context via subagents; the probe does NOT fire inside Path B — only at Path B acceptance and chain entry.
- Not a solution for free-form (non-chain) sessions. Users running ad-hoc prompts outside `/ark-workflow` chains are not covered. If telemetry later shows that's a real pain point, a cross-cutting `/ark-session` skill can be extracted.

## Scope Decisions (from brainstorming, revised after first /ccg round)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Ambition ceiling | **B** — metadata + runtime budget layer inside `/ark-workflow` | Option C (full session-management overlay with new `/ark-session` skill) was deferred as premature without telemetry data; Option A (annotate-only) was superseded by the reactive approach once `.omc/state/hud-stdin-cache.json` was identified as ground-truth data |
| Data source | `.omc/state/hud-stdin-cache.json` via `HAS_OMC` gate | Already populated by the Claude Code statusline; no new hooks; graceful fallback when unavailable |
| Measurement vs prediction | **Measurement**. No cost table, no per-step estimates | Estimation drifts; measurement adapts to each session's actual composition (CLAUDE.md size, vault size, prior turns, tool-output volume) |
| When the probe runs | Three discrete boundaries: chain entry, each step boundary (Path A only), Path B acceptance | Step 6.5 already interjects between steps to check off progress and announce Next; the acceptance boundary is the most actionable moment for Path B — before the user commits to an autonomous run while already near rot zone (Codex advisor point). Chain exit was considered and dropped as redundant with the next chain's entry probe. |
| Path A/B rendering | Path A: probe at chain entry + every step boundary. Path B: probe at chain entry + Path B acceptance only | Path B is autonomous; inline interjection would break the hands-off contract, and OMC already has its own checkpoint protocol |
| Suppression state lifecycle | Helper provides explicit `--format record-proceed` and `--format record-reset` modes. Caller writes `proceed_past_level` when user picks `proceed`, and writes `null` when user picks option (a) `/compact` or (b) `/clear`. No state inference from observed token levels — if the reset is needed, the caller must explicitly request it (Codex advisor round-2 point) | Inference-based reset would leave nudge suppression stuck indefinitely if `/compact` fails to drop below the threshold. Explicit writes are cheap and correct. |
| Recommendation surface | Three-option menu (compact / clear / subagent) emitted as plain text before "Next: [skill] — [purpose]" | Article's three session-management decisions map 1:1; user chooses, probe never decides |
| Forward brief | Pre-filled template derived from chain state (scenario, completed steps, remaining steps) with a `<fill in>` slot for key findings | Removes the most common friction of `/compact` — staring at a blank prompt when context is already degraded |
| Subagent hint | Listed as an always-available option (c) in the menu; no skill-specific "heavy" classification | Subagents get fresh context windows by construction; whether to wrap is a function of the parent's current state, not the child's expected cost |
| Nudge-fatigue suppression | Track `proceed_past_level` in `current-chain.md` frontmatter. Once the user picks `proceed` at nudge, suppress future nudge-level menus for the remainder of the chain. Strong-level menus still fire. Any `/compact` or `/clear` taken via the menu (options a/b) resets the state | Gemini advisor point: current spec would menu-spam a user who intentionally runs a long chain. Escalation to `strong` is still surfaced — `proceed` at nudge doesn't silence rot-zone warnings |
| Freshness & session policy | Reject the cache file if (a) its `cwd` or `workspace.current_dir` doesn't match the current project root, or (b) its mtime is older than a configurable TTL for entry-time probes. Reason codes: `session_mismatch`, `stale_file` | Codex advisor point: on session start or after `/clear`, the cache can be parseable but describe the previous session — the most likely bad read |
| Coverage | All 7 chain scenarios at once | Rendering logic is centralized in the probe helper; one change applies to all chains without per-chain edits |
| Session habits coaching | Short block in `/ark-workflow` SKILL.md + `references/routing-template.md`, pushed via `/ark-update` | SKILL.md is the source of truth for behavior; routing-template gets the always-loaded copy-paste block for downstream CLAUDE.md files |
| Threshold values | Nudge at **20%** of total context, Strong at **35%** | On a 1M window, 20% ≈ 200k (early planning nudge — cheap to checkpoint here, not a danger signal); 35% ≈ 350k (defensive signal — aligns with lower bound of cited 300-400k rot zone). Because `used_percentage` scales with `context_window_size`, these thresholds adapt correctly across models without code changes |
| Threshold overrides | Hardcoded defaults, but exposed as kwargs on `probe()` for tests and future tuning | Codex advisor point: 20% may fire on medium chains with headroom; keep defaults, allow override |
| Implementation split | All probe logic (threshold math, chain-file parsing, menu rendering, session check, suppression-state mutations) in `context_probe.py` with six CLI modes. SKILL.md invokes the helper and prints stdout — no inline parsing or rendering in shell | Codex advisor point: Step 6.5 is an instruction file, not a shell implementation. Inline parsing+rendering would drift from the Python contract |

## Architecture

Chain rendering is unchanged from today's `/ark-workflow`. Path A and Path B emit identical chains to v1.16. The probe is a boundary concern; it does not touch rendering.

```
   /ark-workflow Step 4 (look up chain) → Step 5 (resolve conditions)
                    │
                    ▼
   Step 6 — present chain:
     Chain entry probe  ─── (NEW) context_probe.py --format step-boundary
                             └── if nudge/strong: prepend header warning
                                  "Context already at 24%. Consider /clear
                                   before starting this chain."
     Render chain as today
     If HAS_OMC=true:
        Path B acceptance probe  ─── (NEW) context_probe.py --format path-b-acceptance
                                      └── if nudge/strong: inline warning
                                           next to the [Accept Path B] button
                    │
                    ▼
   Step 6.5 — activate continuity, start execution
                    │
                    ▼
   Agent executes step 1
                    │
                    ▼
   Step 6.5 boundary protocol (per step):
     1. Check off step in current-chain.md              (as today)
     2. Update TodoWrite task to completed              (as today)
     3. Run step-boundary probe                         (NEW)
        └── context_probe.py --format step-boundary
            └── reads .omc/state/hud-stdin-cache.json
            └── checks session/cwd + optional TTL
            └── checks proceed_past_level in chain frontmatter
            └── if menu warranted: prints menu text
            └── if not: prints nothing
     4. If probe stdout non-empty:
          Display the stdout verbatim
          Pause for user / agent decision
          If decision was `proceed`:
            context_probe.py --format record-proceed       (writes frontmatter)
          If decision was (a) /compact or (b) /clear:
            context_probe.py --format record-reset         (clears frontmatter)
     5. Mark next TodoWrite task in_progress            (as today)
     6. Announce "Next: [skill] — [purpose]"            (as today)
                    │
                   ...
```

**Probe is a pure function over one JSON file + one chain file.** No hidden state, no network, no cross-invocation memory beyond the explicit `proceed_past_level` field in `current-chain.md`. Each probe invocation is independent.

## Components

### 1. `skills/ark-workflow/scripts/context_probe.py`

Single helper script. Six CLI modes (`raw`, `step-boundary`, `path-b-acceptance`, `record-proceed`, `record-reset`, `check-off`). Stdlib only (`json`, `pathlib`, `sys`, `argparse`, `typing`, `os`, `tempfile`). ~140-170 lines of logic.

All mutations of `.ark-workflow/current-chain.md` (frontmatter writes via `record-proceed`/`record-reset`, checklist `[ ]` → `[x]` writes via `check-off`) go through a single internal helper `chain_file.atomic_update(chain_path, mutator_fn)`. The helper acquires an **exclusive advisory file lock** on a sibling lock file (`.ark-workflow/current-chain.md.lock`) using `fcntl.flock(..., LOCK_EX)` for the entire read-modify-write cycle. It then: reads the file, applies the mutator in memory, writes to a temp file in the same directory, `os.replace`s the temp into place, and releases the lock. The lock-plus-atomic-rename combination prevents both torn writes (covered by temp+rename) AND lost updates (covered by the lock serializing concurrent read-modify-write sequences). Without the lock, two writers reading the same base state would each write their own mutation, losing one.

The helper uses stdlib only (`fcntl`) and degrades gracefully on platforms lacking fcntl (Windows — out of scope for Ark skills, which are macOS/Linux-only) by falling back to temp+rename without locking.

**Python API:**

```python
from typing import TypedDict, Optional, Literal

class ProbeResult(TypedDict, total=False):
    level: Literal["ok", "nudge", "strong", "unknown"]
    pct: Optional[int]                          # context_window.used_percentage (int, clamped to [0, 100])
    tokens: Optional[int]                       # sum of current_usage.* subfields (None if any missing/non-int)
    warnings: list[str]                         # e.g. ["tokens_unavailable"]
    reason: Optional[str]                       # unknown-level diagnostic: file_missing | parse_error | schema_mismatch | session_mismatch | stale_file | permission_error | not_a_file


def probe(
    state_path: Path,
    *,
    nudge_pct: int = 20,
    strong_pct: int = 35,
    max_age_seconds: Optional[int] = None,           # None disables TTL check
    expected_cwd: Optional[str] = None,              # None disables cwd check
    expected_session_id: Optional[str] = None,       # None disables session-id check
) -> ProbeResult:
    """
    Read the Claude Code statusline cache and return a budget recommendation.

    Decision signal: context_window.used_percentage.
    If used_percentage is valid but token subfields are missing/malformed,
    the probe still returns the level with tokens=None and warnings=["tokens_unavailable"].

    Session/freshness rejection (any of these trigger unknown/session_mismatch
    or unknown/stale_file):
      - If expected_session_id is provided AND cache's session_id/sessionId
        doesn't match, return {level: unknown, reason: session_mismatch}.
        This supersedes the mtime check when available.
      - If expected_cwd is provided AND cache's cwd/workspace.current_dir
        doesn't match, return {level: unknown, reason: session_mismatch}.
      - If expected_session_id is NOT provided AND max_age_seconds is provided
        AND file mtime is older than that, return {level: unknown, reason: stale_file}.
        (Mtime is a fallback when session id is unavailable.)

    Thresholds (v1 defaults, overrideable):
      used_percentage >= strong_pct  -> "strong"  (default 35)
      used_percentage >= nudge_pct   -> "nudge"   (default 20)
      otherwise                      -> "ok"

    Fields:
      pct:    context_window.used_percentage from the cache file (integer, clamped to [0, 100])
      tokens: sum of context_window.current_usage.{input_tokens, output_tokens,
              cache_creation_input_tokens, cache_read_input_tokens}. None if any
              subfield is absent or non-integer (level is still computed).
    """
```

**CLI modes (invoked from SKILL.md):**

```bash
# Session-id resolution, computed once at the top of Step 6.5 and passed to
# every probing invocation. Graceful fallback to mtime-based staleness check
# when unavailable. Uses a bash array for SESSION_FLAG to avoid word-splitting
# and glob-expansion hazards when expanded into each invocation.
SESSION_ID="${CLAUDE_SESSION_ID:-$(python3 -c '
import json, pathlib
p = pathlib.Path(".omc/state/hud-state.json")
try:
    data = json.loads(p.read_text())
    # Accept either key name; reject null/non-string.
    sid = data.get("sessionId") or data.get("session_id") or ""
    if isinstance(sid, str) and sid.strip():
        print(sid.strip())
except Exception:
    pass
' 2>/dev/null)}"

# Array-form flag: empty array if SESSION_ID is blank, otherwise two args.
# Expand with "${SESSION_FLAG[@]}" (quoted) at every invocation.
SESSION_FLAG=()
if [ -n "$SESSION_ID" ]; then
  SESSION_FLAG=(--expected-session-id "$SESSION_ID")
fi

# Mode 1: raw probe. Prints the ProbeResult dict as JSON to stdout.
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format raw \
  --state-path .omc/state/hud-stdin-cache.json \
  --expected-cwd "$(pwd)" \
  "${SESSION_FLAG[@]}"

# Mode 2: step-boundary. Reads probe result + current-chain.md + frontmatter state;
# if a menu is warranted (level != ok AND not suppressed by proceed_past_level),
# prints the fully-assembled menu text to stdout. Otherwise prints nothing.
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format step-boundary \
  --state-path .omc/state/hud-stdin-cache.json \
  --chain-path .ark-workflow/current-chain.md \
  --expected-cwd "$(pwd)" \
  "${SESSION_FLAG[@]}"

# Mode 3: path-b-acceptance. Only emits text if level is nudge or strong.
# TTL kicks in only if SESSION_FLAG could not be resolved.
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format path-b-acceptance \
  --state-path .omc/state/hud-stdin-cache.json \
  --expected-cwd "$(pwd)" \
  "${SESSION_FLAG[@]}" \
  --max-age-seconds 300

# Mode 4: record-proceed. Writes proceed_past_level into current-chain.md
# frontmatter. Helper self-detects current level from the cache file — caller
# does not pass --level. Atomic write (temp file + rename). Idempotent. No stdout.
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format record-proceed \
  --state-path .omc/state/hud-stdin-cache.json \
  --chain-path .ark-workflow/current-chain.md

# Mode 5: record-reset. Clears proceed_past_level in current-chain.md
# frontmatter (sets to null). Called when the user picks option (a) /compact
# or (b) /clear via the menu, so subsequent boundaries probe fresh.
# Atomic write. Idempotent. No stdout.
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format record-reset \
  --chain-path .ark-workflow/current-chain.md

# Mode 6: check-off. Flips step N's checklist item from [ ] to [x] in the
# chain file body. Invoked by Step 6.5's "after each step" bullet in place
# of hand-editing the file. Goes through the same atomic helper so it does
# not race with record-proceed/record-reset frontmatter writes. No stdout.
#
# --step-index is 1-based (matches the user-facing step numbering in the
# rendered chain: "step 1", "step 2", ...). Passing --step-index 3 checks
# off the third step. Helper rejects values < 1 or > total step count with
# a stderr error and exit 0 (no side effect).
python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
  --format check-off \
  --step-index 3 \
  --chain-path .ark-workflow/current-chain.md
```

All modes exit 0 regardless of outcome. SKILL.md interprets stdout: non-empty → display verbatim and pause; empty → proceed silently. Modes 4 and 5 never write to stdout; they mutate the chain file via atomic temp-file-plus-rename to prevent interleaving with Step 6.5's step-checkoff writes.

**Note on level detection in `record-proceed`:** the helper re-reads the cache at write time and records whichever level is currently active (`nudge` or `strong`). Only `nudge` is persisted as a suppression flag (`proceed_past_level: nudge`); if the current level is `strong` at the time of `record-proceed`, the helper writes `proceed_past_level: null` — we never silence rot-zone warnings. Caller does not need to know which level was shown in the menu.

### 2. SKILL.md Step 6.5 changes (final — simplified)

**Current text** (`skills/ark-workflow/SKILL.md:314`):

> - After each step: check off the step in the file (`[ ]` → `[x]`), update the TodoWrite task to `completed`, announce `Next: [skill] — [purpose]`, mark next task `in_progress`

**New text:**

> - After each step:
>   1. Check off the step in `.ark-workflow/current-chain.md` via the atomic helper (not by hand-editing):
>      ```bash
>      python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
>        --format check-off --step-index {N} \
>        --chain-path .ark-workflow/current-chain.md
>      ```
>   2. Update the TodoWrite task to `completed`
>   3. **Run the step-boundary probe** (only when `HAS_OMC=true`):
>      ```bash
>      MENU=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
>        --format step-boundary \
>        --state-path .omc/state/hud-stdin-cache.json \
>        --chain-path .ark-workflow/current-chain.md \
>        --expected-cwd "$(pwd)" 2>/dev/null)
>      ```
>      If `$MENU` is non-empty, display it verbatim and pause for user decision. Then:
>      - If `proceed`: invoke `--format record-proceed` (no extra args; helper self-detects current level and persists `proceed_past_level: nudge` only when current level is `nudge`; strong is never silenced).
>      - If `(a)` or `(b)`: after `/compact` or `/clear`, invoke `--format record-reset` to explicitly clear `proceed_past_level: null` so the next boundary probes fresh.
>      - If `(c)`: no state write; subagent wraps Next step.
>      If `$MENU` is empty, proceed silently.
>   4. Mark the next TodoWrite task `in_progress`
>   5. Announce `Next: [skill] — [purpose]`

**Chain entry probe** (added as the very first action of Step 6.5, before step 1 is executed):

> At the start of Step 6.5, before executing step 1 of the chain, run the entry probe (only when `HAS_OMC=true`):
> ```bash
> ENTRY=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
>   --format step-boundary \
>   --state-path .omc/state/hud-stdin-cache.json \
>   --chain-path .ark-workflow/current-chain.md \
>   --expected-cwd "$(pwd)" \
>   --max-age-seconds 300 2>/dev/null)
> ```
> Entry-time probes pass `--max-age-seconds 300` (5 minutes) to reject cache files left over from a previous session while tolerating the time the user spends reading the chain before accepting. The step-boundary mode is reusable at entry, but the helper **explicitly detects "zero completed steps"** and renders a simplified menu (see Zero-Completed Entry Rendering below).

**Path B acceptance probe** (added inside Step 6's dual-path presentation, rendered just above the `[Accept Path B]` button when `HAS_OMC=true`):

> ```bash
> PATHB_WARN=$(python3 "$ARK_SKILLS_ROOT/skills/ark-workflow/scripts/context_probe.py" \
>   --format path-b-acceptance \
>   --state-path .omc/state/hud-stdin-cache.json \
>   --expected-cwd "$(pwd)" \
>   --max-age-seconds 300 2>/dev/null)
> ```
> Path B acceptance is also an entry-time probe; `--max-age-seconds 300` is passed. If `$PATHB_WARN` is non-empty, display it above the `[Accept Path B]` button. Example output: `"⚠ Context at 32% (~320k). Path B adds parent-session coordination on top — consider /clear or /compact before accepting."`

### 3. Mitigation menu template

Emitted only by `context_probe.py --format step-boundary`. The helper reads `current-chain.md` to fill in scenario, weight, completed steps, next skill, and remaining steps. The three options reuse the same forward-brief string — written once, referenced in (a) and (b):

```
⚠ Context at {pct}% (~{tokens_k}k). Options before continuing to Next:

Forward brief (auto-assembled from current-chain.md):
  "Resuming {scenario} chain ({weight}). Completed: {steps 1..N}.
   Next: step {N+1} — {next_skill}. Remaining: {steps N+2..end}.
   Key findings so far: <fill in>."

  (a) /compact focus on the forward brief above.
  (b) /clear, then paste the forward brief above as your opening message.
  (c) Delegate Next step to a subagent (keeps this session lean — only the
      subagent's conclusion returns, not its tool output).

Which option? [a/b/c/proceed]
```

At `level = strong`, the leading line escalates to: `"⚠ Context at {pct}% — entering the attention-rot zone (~300k+ tokens) where reasoning quality degrades. One of (a)/(b)/(c) is strongly recommended before continuing."`

**Zero-Completed Entry Rendering:** when the helper detects zero `[x]` steps in the chain file (chain-entry probe), it emits a simplified menu. Option (a) is shown as unavailable rather than hidden, so the letter mapping stays consistent with mid-chain menus. Option (c) keeps the same meaning (delegate next step to a subagent) — at chain entry that means delegate Step 1:

```
⚠ Context at {pct}% (~{tokens_k}k) before chain has started.

Forward brief (auto-assembled):
  "Starting {scenario} chain ({weight}). Plan: {all_steps_as_comma_list}.
   Key context to preserve: <fill in>."

  (a) /compact — unavailable (no progress to summarize yet).
  (b) /clear, then paste the forward brief above as your opening message.
  (c) Delegate Step 1 to a subagent (keeps this session lean — only the
      subagent's conclusion returns, not its tool output).

Which option? [b/c/proceed]
```

Entry rendering:
- Keeps option (a) visible but labeled unavailable (not typed by the user) so letter mapping matches mid-chain.
- Drops the "Completed:" and "Remaining:" lines from the brief (everything is "Plan:").
- Keeps option (c) semantically identical to mid-chain — the SKILL.md handler for (c) is the same in both cases, so a user choosing (c) always gets subagent delegation.
- `proceed` at this boundary is "accept the entry-level nudge and run the chain normally." It is distinct from (c) — proceed continues in-session without delegation; (c) delegates.
- Answer set is `[b/c/proceed]` — (a) is typed in the menu but not offered as an answer.

At strong-level entry rendering, the leading line escalates identically to the mid-chain strong banner but ends with "One of (b)/(c) is strongly recommended" to match the constrained answer set.

**Template variables resolved by the helper:**
- `{scenario}`, `{weight}` — from `.ark-workflow/current-chain.md` frontmatter
- `{steps 1..N}`, `{steps N+2..end}` — from the checklist body of `current-chain.md` (steps with `[x]` vs `[ ]`)
- `{next_skill}` — the first unchecked step in `current-chain.md`
- `<fill in>` — user completes this slot. v1 does not auto-populate findings (see Deferred).

### 4. Chain file frontmatter extension (nudge-fatigue tracking)

`/ark-workflow` Step 6.5 already writes `.ark-workflow/current-chain.md` with frontmatter fields including `scenario`, `weight`, `chain_id`, `task_hash`, `handoff_marker`. This spec adds one optional field:

```yaml
proceed_past_level: null   # null | "nudge"
```

Semantics:
- `null` (default): all menu levels fire per their thresholds.
- `"nudge"`: `nudge`-level menus suppressed for the rest of the chain. `strong`-level menus still fire regardless.

Lifecycle (explicit writes only — no inference from observed levels):
- **Created** as `null` when `/ark-workflow` writes the chain file at the end of Step 6.5's initial setup.
- **Written to `"nudge"`** when the caller invokes `--format record-proceed` and the current level at write time is `nudge`. If the current level at write time is `strong`, the helper writes `null` instead (strong-level proceed never silences anything). The helper self-detects level from the cache file; the caller does not pass a level argument.
- **Cleared to `null`** when the caller explicitly invokes `--format record-reset`. The caller is expected to invoke this immediately after the user takes option (a) `/compact` or (b) `/clear` (before the next step begins) so the next boundary probes fresh. No inference — if the caller forgets to reset, suppression persists.
- **Implicitly cleared** on `/clear`: the user typically loses the chain file context on `/clear`, so the next `/ark-workflow` invocation starts with a fresh chain file. (The on-disk file may persist if not deleted, but the new chain has a different `chain_id` and overwrites.)
- **Atomicity:** all mutations of `current-chain.md` go through a shared helper `chain_file.atomic_update(chain_path, mutator_fn)` defined in `context_probe.py`. The helper does read → in-memory transform → temp-file write → `os.replace` rename. Both `record-proceed`/`record-reset` (frontmatter writes) AND Step 6.5's `[ ]` → `[x]` checklist writes MUST use this helper. SKILL.md's "check off step" bullet is updated to invoke `context_probe.py --format check-off --step-index N` instead of hand-editing the file. This prevents lost updates between concurrent frontmatter and checklist edits — both paths go through the same atomic read-modify-write. Readers (the step-boundary mode) tolerate temporary missing files during rename by retrying once.

Strong-level `proceed` never suppresses anything — we never silence rot-zone warnings.

### 5. Session habits coaching block

Added to `/ark-workflow/SKILL.md` as a new section (between "When Things Change" and "Routing Rules Template"):

```markdown
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
```

Same block appended to `skills/ark-workflow/references/routing-template.md` under a new `### Session habits` subheading so downstream CLAUDE.md files pick it up via `/ark-update`.

### 6. `/ark-update` migration

Bump the `routing-rules` managed_region version in `skills/ark-update/target-profile.yaml`:

```yaml
- id: routing-rules
  op: ensure_routing_rules_block
  file: CLAUDE.md
  since: 1.3.0
  version: 1.17.0   # was 1.12.0; bumped because routing-template.md gained Session Habits block
```

Downstream projects run `/ark-update` → `/ark-update` detects the version drift → replays the `ensure_routing_rules_block` op with the updated template → CLAUDE.md gains the Session Habits section. Idempotent: re-running `/ark-update` after the block is in place is a no-op.

**Managed-block behavior (explicit):** `ensure_routing_rules_block` operates only on content inside the `<!-- ark:begin id=routing-rules -->` ... `<!-- ark:end -->` markers. Edits outside those markers in downstream CLAUDE.md files are preserved. Edits inside the managed region are treated as drift: they are backed up to `.ark/backups/` and replaced with the authoritative template. Users who want to customize must do so outside the markers. (Confirmed against `skills/ark-update/scripts/ops/ensure_claude_md_section.py`.)

No other `target-profile.yaml` entries change.

## Data Contract

The probe consults these fields in `.omc/state/hud-stdin-cache.json`:

```json
{
  "session_id": "8a956d02-...",
  "cwd": "/Users/.../project-root",
  "workspace": {
    "current_dir": "/Users/.../project-root"
  },
  "context_window": {
    "used_percentage": 12,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 623,
      "cache_creation_input_tokens": 2585,
      "cache_read_input_tokens": 118279
    },
    "context_window_size": 1000000
  }
}
```

**Primary decision signal:** `context_window.used_percentage` (integer). This is the only field whose absence/corruption forces `level: unknown`.

**Secondary display fields** (best-effort; failure does NOT block level determination):
- `context_window.current_usage.*` — summed for the `tokens` display field. If any subfield is absent or non-integer, probe returns the level with `tokens: null` and `warnings: ["tokens_unavailable"]`.
- `context_window.context_window_size` — informational only; not used for threshold math (thresholds compare `used_percentage` directly, which is already context-window-scaled).

**Session/freshness signal fields:**
- `cwd` and/or `workspace.current_dir` — checked against `--expected-cwd` CLI arg when provided. Mismatch → `level: unknown`, `reason: session_mismatch`.
- File mtime — checked against `--max-age-seconds` CLI arg when provided. Older → `level: unknown`, `reason: stale_file`.

## Session & Freshness Policy

The statusline cache describes **whatever session last updated it**. On session start, after `/clear`, or after switching to a different project in the same terminal, the cache is either absent, present but stale, or present and describing a prior session. These states must not leak into the probe's decision.

**Rules:**
1. SKILL.md passes `--expected-cwd "$(pwd)"` at every invocation. The helper compares this against the cache's `cwd` (or `workspace.current_dir` if `cwd` is absent). Mismatch → `unknown/session_mismatch`; SKILL.md proceeds silently.
2. SKILL.md **also** passes `--expected-session-id "$SESSION_ID"` whenever it can resolve the current session's id. The helper compares this against the cache's `session_id` / `sessionId` (depending on Claude Code version — the helper accepts either). Mismatch → `unknown/session_mismatch`. This is the primary protection against "same project, different session" stale reads and supersedes the mtime check whenever the session id is available.
3. SKILL.md resolves `SESSION_ID` in this order, falling back silently if unavailable:
   - `$CLAUDE_SESSION_ID` environment variable (if Claude Code exposes it).
   - `session_id` field from `.omc/state/hud-state.json` (OMC's own session snapshot — distinct from the statusline input cache being probed).
   - Unavailable → `--expected-session-id` is omitted; helper falls back to cwd + mtime alone.
4. For **entry-time** probes (chain entry, Path B acceptance), SKILL.md passes `--max-age-seconds 300` (5 minutes) as a tertiary guard — kicks in only when `--expected-session-id` could not be resolved. If the cache's mtime is older than 5 minutes at chain entry, the file likely reflects a different session even if `cwd` matches. → `unknown/stale_file`.
5. For **step-boundary** probes (mid-chain), no TTL is passed (fresh same-session cache is guaranteed by the current session's own statusline firing).

**Rationale (why the layered check):** Codex round-3 advisor point: with `cwd + mtime` alone, a 4-minute-old cache left over from a different session in the same project root would be silently accepted. Because the cache already carries `session_id`, an explicit id comparison removes that leak cleanly. The TTL becomes a fallback for environments where the current session id cannot be resolved (e.g., non-OMC runners, or Claude Code versions that don't expose the env var). The `cwd` check remains and catches multi-project terminal reuse.

## Edge Cases & Error Handling

| Case | Behavior |
|------|----------|
| `HAS_OMC=false` | Probe is not invoked. Step 6.5 falls back to current behavior (no menu, no warning). |
| File missing (`.omc/state/hud-stdin-cache.json`) | `level: unknown`, `reason: file_missing`. SKILL.md proceeds silently. |
| File present, malformed JSON | `level: unknown`, `reason: parse_error`. Covers both syntax errors and truncated concurrent writes. |
| File present, missing `used_percentage` | `level: unknown`, `reason: schema_mismatch`. |
| File present, `used_percentage` wrong type (string, float, null) | `level: unknown`, `reason: schema_mismatch`. |
| File present, missing `current_usage` subfields | `level` computed from `used_percentage`; `tokens: null`, `warnings: ["tokens_unavailable"]`. SKILL.md still shows the menu if level warrants. |
| `used_percentage` is 0 or negative | Treat as `ok`. Probe does not assume corruption unless field is non-integer. |
| `used_percentage` > 100 | Treat as `strong`. Clamp to 100 for display. |
| Permission denied on file | `level: unknown`, `reason: permission_error`. |
| Path is a directory, not a file | `level: unknown`, `reason: not_a_file`. |
| Stale symlink / symlink to another worktree | Resolves to a file whose `cwd` mismatches → `level: unknown`, `reason: session_mismatch` (caught by the session check, not by following the symlink). |
| Session mismatch: cache `cwd` ≠ `--expected-cwd` | `level: unknown`, `reason: session_mismatch`. SKILL.md proceeds silently. |
| Stale file: mtime > `--max-age-seconds` (entry-time only) | `level: unknown`, `reason: stale_file`. SKILL.md proceeds silently. |
| Chain file absent at step-boundary mode | Helper cannot assemble forward brief. Emits a degraded menu with `{next_skill}: (unknown)` and omits the completed/remaining lists. Logs one stderr line. |
| Path B (OMC autonomous chain) | Probe fires at chain entry and Path B acceptance only. No inner-loop or exit probing. |
| User chose `proceed` at nudge; cumulative rises to strong | Caller invokes `--format record-proceed`; helper writes `proceed_past_level: nudge`. Subsequent nudge menus suppressed. Strong-level menus fire normally regardless. |
| User chose `proceed` at strong | Caller invokes `--format record-proceed`; helper detects current level is `strong` and writes `proceed_past_level: null` (no suppression). Strong menus continue to fire at every subsequent boundary — we never silence rot-zone warnings. |
| User takes option (a) `/compact` | Caller runs `/compact`, then explicitly invokes `--format record-reset` to clear `proceed_past_level: null`. Next boundary probes fresh, regardless of whether `used_percentage` actually dropped below `nudge_pct`. |
| User takes option (b) `/clear` | Session restarts with a fresh context. Next `/ark-workflow` invocation creates a new chain file with a fresh `chain_id`; prior `proceed_past_level` is irrelevant. Caller does not need to invoke `--format record-reset`. |
| Caller forgets to invoke `--format record-reset` after `/compact` | `proceed_past_level: nudge` persists; future nudge menus suppressed until user hits strong or chain completes. This is a chain-agent bug, not a helper bug — the integration test in the test plan catches this. |
| `record-proceed` or `record-reset` invoked during concurrent `[x]` checklist write | Helper uses temp file + `os.replace` atomic rename. Readers re-read once on file-missing. No lost writes, no interleaved state. |

## Testing Strategy

### Unit tests for `context_probe.py`

`skills/ark-workflow/scripts/test_context_probe.py` — pytest, follows the plugin's existing test pattern (see `skills/ark-context-warmup/scripts/test_*.py`).

Fixture directory: `skills/ark-workflow/scripts/fixtures/context-probe/`

**Threshold fixtures:**
- `ok-fresh.json` — `used_percentage: 5` → level = ok
- `ok-warm.json` — `used_percentage: 19` → level = ok (boundary below nudge)
- `nudge-low.json` — `used_percentage: 20` → level = nudge (boundary inclusive)
- `nudge-mid.json` — `used_percentage: 28` → level = nudge
- `nudge-high.json` — `used_percentage: 34` → level = nudge (boundary below strong)
- `strong-low.json` — `used_percentage: 35` → level = strong (boundary inclusive)
- `strong-high.json` — `used_percentage: 72` → level = strong
- `over-100.json` — `used_percentage: 105` → level = strong, clamped

**Parse/schema fixtures:**
- `malformed.json` — invalid JSON → level = unknown, reason = parse_error
- `truncated.json` — valid-JSON-prefix then EOF → level = unknown, reason = parse_error
- `missing-field.json` — valid JSON but no `used_percentage` → level = unknown, reason = schema_mismatch
- `wrong-type.json` — `used_percentage: "twelve"` → level = unknown, reason = schema_mismatch
- `missing-current-usage.json` — valid `used_percentage: 28`, no `current_usage` → level = nudge, tokens = None, warnings include `tokens_unavailable`
- `non-integer-token.json` — one `current_usage` subfield is `null` → level computed normally, tokens = None, warnings include `tokens_unavailable`

**Session / freshness fixtures:**
- `cwd-mismatch.json` — cache `cwd` points to another project path → with `expected_cwd` set, level = unknown, reason = session_mismatch
- `workspace-mismatch.json` — cache `cwd` missing, `workspace.current_dir` mismatches → level = unknown, reason = session_mismatch
- `stale-file` (filesystem-based) — file mtime older than `max_age_seconds=60` → level = unknown, reason = stale_file. Created via `os.utime` in test setup.

**Filesystem fixtures:**
- `missing-file` (path does not exist) → level = unknown, reason = file_missing
- `directory-instead-of-file` — target path is a directory → level = unknown, reason = not_a_file
- `permission-denied` — `chmod 000` test fixture, wrapped in `try/finally` restore → level = unknown, reason = permission_error

### Integration test

`skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` — runs each of the six CLI modes against fixture JSONs and asserts stdout/side effects:
- `--format raw` with `ok` fixture: prints JSON with `"level": "ok"`.
- `--format step-boundary` with `nudge` fixture + sample `current-chain.md` (2 of 4 steps done): prints standard menu with forward brief listing completed/next/remaining.
- `--format step-boundary` with `nudge` fixture + sample `current-chain.md` (0 of 4 steps done): prints entry-rendered menu (option (a) unavailable, Plan: line instead of Completed/Remaining).
- `--format step-boundary` with `ok` fixture: prints nothing (exit 0).
- `--format step-boundary` with `nudge` fixture + `proceed_past_level: nudge` in chain file: prints nothing (suppressed).
- `--format step-boundary` with `strong` fixture + `proceed_past_level: nudge`: prints strong-level menu (not suppressed).
- `--format path-b-acceptance` with `nudge` fixture: prints one-line warning. With `ok` fixture: prints nothing.
- `--format record-proceed` with `nudge` fixture + chain file with `proceed_past_level: null`: chain file's frontmatter now has `proceed_past_level: nudge`; step checklist body unchanged.
- `--format record-proceed` with `strong` fixture + chain file with `proceed_past_level: null`: frontmatter stays `null` (strong never silenced).
- `--format record-reset` with chain file having `proceed_past_level: nudge`: frontmatter cleared to `null`; step checklist body unchanged.
- **Integration end-to-end (reset lifecycle):** script sequence: record-proceed (nudge) → assert frontmatter nudge → record-reset → assert frontmatter null → probe step-boundary with nudge fixture → assert menu fires again (not suppressed).
- **Atomic write stress:** script spawns a background loop rewriting the chain file's checklist body for 2 seconds while record-proceed + record-reset run in parallel. Assert frontmatter field and checklist body both end in valid states; no truncated file, no partial YAML.

### Step 6.5 text-generation test

`skills/ark-workflow/scripts/test_step_boundary_render.py` — unit test that exercises the helper's menu assembly against a fixture `current-chain.md` file:
- Fixture chain: bugfix/Medium with 4 steps, 2 checked off.
- Assert rendered menu contains `"Completed: /ark-context-warmup, /investigate"`, `"Next: step 3 — /ark-code-review"`, `"Remaining: /ship"`.
- Assert the forward-brief block is syntactically one-paste-ready (no unbalanced quotes, no orphan template vars).

### Manual smoke test

Update `skills/ark-workflow/scripts/smoke-test.md` (create if absent) to include a reactive-probe dry-run: set `hud-stdin-cache.json` fixture manually to ≥35%, invoke `/ark-workflow` on a bugfix request, step through, verify the menu appears at the correct boundary, verify `proceed` is recorded and suppresses future nudge menus, verify strong-level still fires.

## Rollout

1. Implementation in feature branch (current: `context-management`).
2. Plugin version bump to v1.17.0 in `VERSION`, `plugin.json`, `marketplace.json`.
3. CHANGELOG entry:
   ```
   ## v1.17.0 (2026-04-XX)
   - Add reactive context-budget probe to /ark-workflow. The probe reads
     .omc/state/hud-stdin-cache.json and surfaces a three-option mitigation
     menu (compact / clear / subagent) at chain entry, each step boundary
     (Path A), and Path B acceptance. Thresholds: nudge at 20%, strong at
     35%. Graceful fallback when HAS_OMC=false or cache is stale/session-
     mismatched.
   - Track proceed_past_level in .ark-workflow/current-chain.md to suppress
     repeated nudge-level menus when the user intentionally runs a long
     chain. Strong-level menus still fire.
   - Add "Session Habits" coaching block to /ark-workflow SKILL.md and
     routing-template.md. Downstream projects: run /ark-update to pull the
     block into project CLAUDE.md.
   ```
4. Downstream projects run `/ark-update` to pick up the routing-template change.
5. Post-ship: one-week observation window. If the menu rarely fires for users who actually hit rot-zone symptoms, revisit thresholds (currently 20% / 35%). If users report the nudge menu is still noisy despite `proceed_past_level`, consider raising the nudge default to 25%.

## Deferred / Open

- **Telemetry.** No telemetry lands in v1. If we later want to measure "how often do users take (a) vs (b) vs (c) vs proceed," we can log one line to `.ark-workflow/telemetry.log` (already gitignored) per probe emission. Deferred.
- **Non-chain sessions.** The probe only fires inside `/ark-workflow` chains. Free-form sessions (user typing ad-hoc prompts outside a chain) don't benefit. If this becomes a pain point, consider a Claude Code hook that runs the same probe on `PostToolUse` boundaries — but only after the chain-scoped version proves its value.
- **Forward-brief auto-population.** v1 pre-fills the template with chain state but leaves key findings as `<fill in>`. v2 could scrape the last N TodoWrite completions / tool outputs to auto-populate findings. Deferred as premature; the user is better at summarizing findings than we are, and the `<fill in>` friction is mild.
- **Path B inner-loop probing.** OMC autonomous chains manage their own context. If we later want visibility into Path B context state, coordinate with OMC's team rather than bolting on.
- **Threshold tuning from data.** 20% / 35% are rationally-defensible ballpark values, not empirically-tuned. Tuning requires telemetry; telemetry is deferred.
- **Multi-notebook / multi-root workspaces.** The session/cwd check assumes one project root per session. Claude Code's `workspace.added_dirs` field is not consulted. Deferred until we see a downstream project that hits this.

## Files Changed

| File | Change |
|------|--------|
| `skills/ark-workflow/SKILL.md` | Step 6 dual-path presentation: add Path B acceptance probe invocation. Step 6.5 "Activate Continuity": add chain-entry probe and "after each step" step-boundary probe invocation. Add new "Session Habits" section between "When Things Change" and "Routing Rules Template". |
| `skills/ark-workflow/scripts/context_probe.py` | **NEW** — probe module with `probe()` API, `ProbeResult` TypedDict, six CLI modes (`raw`, `step-boundary`, `path-b-acceptance`, `record-proceed`, `record-reset`, `check-off`). Shared `chain_file.atomic_update` helper wraps ALL mutations of `current-chain.md`. Stdlib only. Atomic writes via temp-file + `os.replace`. ~140-170 lines. |
| `skills/ark-workflow/scripts/test_context_probe.py` | **NEW** — unit tests covering thresholds, parse/schema, session/freshness, filesystem cases (~17 fixtures). |
| `skills/ark-workflow/scripts/test_step_boundary_render.py` | **NEW** — menu-assembly test against a fixture `current-chain.md`. |
| `skills/ark-workflow/scripts/fixtures/context-probe/*.json` | **NEW** — ~17 fixtures covering all level/reason cases. |
| `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` | **NEW** — integration smoke for all six CLI modes + end-to-end reset-lifecycle and atomic-write stress tests. |
| `skills/ark-workflow/scripts/smoke-test.md` | **NEW/UPDATED** — reactive probe dry-run. |
| `skills/ark-workflow/references/routing-template.md` | Append "### Session habits" subsection. |
| `skills/ark-update/target-profile.yaml` | Bump `routing-rules` entry `version: 1.12.0` → `1.17.0`. |
| `VERSION` | Bump to `1.17.0`. |
| `plugin.json` | Bump `version` to `1.17.0`. |
| `.claude-plugin/marketplace.json` | Bump `version` to `1.17.0`. |
| `CHANGELOG.md` | New v1.17.0 section. |
