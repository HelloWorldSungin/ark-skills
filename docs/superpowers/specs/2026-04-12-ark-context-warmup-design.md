# Ark Context Warm-Up — Design Spec

**Date:** 2026-04-12
**Scope:** New `/ark-context-warmup` skill + prerequisite extension to `/ark-workflow`'s continuity frontmatter + chain integration across all seven chains.
**Status:** Approved (brainstorming phase); revised after `/codex consult` review.

## Problem

`/ark-workflow` emits a numbered skill chain but assumes the agent running the chain already has the project's recent and relevant context in session. In practice the agent often lacks it — especially at the start of a planning session (`/brainstorming`) or after a session handoff. The three tools that could supply this context (`/notebooklm-vault`, `/wiki-query`, `/ark-tasknotes`) are never invoked automatically. The agent proceeds half-blind, duplicating tracked work, missing past decisions, and forgetting where the previous session left off.

## Goal

Before any chain executes, automatically gather the most recent and relevant project context from the three available backends and present it to the agent as a single structured `## Context Brief`. Warm-up is:

- **Unconditional** — runs as step 0 of every chain, regardless of weight class.
- **Non-blocking** — every failure mode degrades gracefully. The chain never halts on warm-up failure.
- **Reusable** — exposed as a standalone skill, invokable outside any chain.
- **Efficient** — parallel where safe, serial where the backends share Obsidian; keyed cache for intra-chain re-use.

## Non-Goals

- Not a NotebookLM sync operation. Sync staleness is `/ark-health`'s concern.
- Not a cross-project context tool. Scoped to the current project's vault.
- Not a contradiction resolver. If backends disagree, both signals surface; the agent reconciles.
- Not a gating mechanism. The warm-up informs, it does not block.

## Scope Decisions (from brainstorming, revised post-codex)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Which scenarios trigger warm-up | All scenarios `/ark-workflow` triages, every weight class | User prioritized "always have context"; no Light exemption |
| `/notebooklm-vault` sub-command | Smart pick: run `session-continue` only if a recent session log exists **AND** has the required shape (Next Steps section present + epic link resolvable); otherwise `bootstrap` | Codex noted that a recent-but-malformed session log should not drive `session-continue`. Shape-check mirrors the backend's own fallback logic. |
| `/wiki-query` scenario mapping | Every scenario gets a vault query — including Ship (deploy runbooks / prior incidents / rollback notes) and Knowledge Capture (existing vault pages on the topic); templates tuned per scenario | Codex point: ship needs vault knowledge too (deploy runbooks, rollback, env gotchas); knowledge-capture should see prior vault state to avoid regressions |
| `/ark-tasknotes` usage | `status` summary AND structured search keyed on TaskNotes `component` / `work-type` / `session` fields first, falling back to keyword search | Codex point: use the tracker's own fields as source of truth; keyword-only is noisy |
| Implementation location | New standalone skill `/ark-context-warmup`, prepended as step 0 to every `chains/*.md` | Single source of truth for warm-up logic; reusable on demand; decouples triage from context fetching |
| Overall shape | Partial fan-out + synthesized `## Context Brief` with an `Evidence` section (replaces boolean flags) | NotebookLM runs in parallel with vault-local lane; wiki-query + tasknotes are serialized inside the vault-local lane to avoid MCP/Obsidian contention |
| Flag output | Evidence-backed candidates with task ids / citations / confidence — not boolean flags | Codex point: heuristic flags are too noisy and too blind; readers need the evidence, not a verdict |
| Cache identity | Cache file is `context-brief-{chain_id}-{task_hash_short}.md` inside `.ark-workflow/`. No `project_path` in the hash — the directory is already repo-scoped. Portable across symlinks, repo moves, machine handoff. | Codex 2nd-round: absolute-path hashing was over-correction. Repo-local `.ark-workflow/` already scopes the cache. |

## Prerequisites — Changes to `/ark-workflow`'s Continuity Contract

**This is required before `/ark-context-warmup` can be implemented.** Codex's review surfaced that the warm-up spec depends on data the current `/ark-workflow` does not persist.

### Current contract (as of this spec)

`skills/ark-workflow/SKILL.md:196` writes `.ark-workflow/current-chain.md` with this frontmatter:

```yaml
scenario: {scenario}
weight: {weight}
batch: false
created: {ISO-8601 timestamp}
handoff_marker: null
handoff_instructions: null
```

No task text. No hash. No chain id. The chain's steps are captured as a markdown checklist below the frontmatter.

### Extended contract (required change)

Add four fields:

```yaml
scenario: {scenario}
weight: {weight}
batch: false
created: {ISO-8601 timestamp}
handoff_marker: null
handoff_instructions: null
chain_id: {ULID generated at chain emission}
task_text: |
  {verbatim user request that triggered /ark-workflow}
task_summary: {normalized one-line summary, <= 120 chars, lowercased, stop-words removed}
task_hash: sha256({task_summary})[:16]
```

- `chain_id` — monotonic per-chain identifier. Allows the warm-up cache to distinguish re-triage events (same project, new chain) from re-invocations (same chain).
- `task_text` — the original user request, verbatim. Source of truth for the warm-up's task-aware queries.
- `task_summary` — lowercased, stop-word-filtered, whitespace-collapsed version. Used for the hash + for human display.
- `task_hash` — short stable hash of the normalized summary. The cache key.

### Backward compatibility

`/ark-context-warmup` checks for the four new fields. If any are missing (legacy chain file from before the update), it falls back to prompting the user for the task description and treats the cache as cold. `/ark-workflow` implementation-plan step adds a one-line CHANGELOG entry documenting the frontmatter extension.

## Architecture

### New skill

- **Path:** `skills/ark-context-warmup/SKILL.md`
- **Siblings:** lives alongside other Ark skills in this plugin repo
- **Internal structure:** single SKILL.md for orchestration; a helpers module at `scripts/warmup-helpers.{sh,py}` for unit-testable logic (smart-pick shape validation, scenario-to-query mapping, cache identity computation, evidence candidate synthesis, brief assembly)
- **Subdirs (required by the testing strategy):** `scripts/` for helpers + their tests, `fixtures/` for evidence-candidate regression test inputs

### Integration into chains

Every chain file (`greenfield.md`, `bugfix.md`, `ship.md`, `knowledge-capture.md`, `hygiene.md`, `migration.md`, `performance.md`) gets a new step 0:

```
0. `/ark-context-warmup` — load recent + relevant project context
```

All existing numbered steps shift down by 1. For chains with session-handoff markers, the marker numbers referenced in comments also shift (e.g., `handoff_marker: after-step-5` → `after-step-6`). Chains affected by marker shifts: Greenfield Medium (handoff_marker: after-step-3 → after-step-4), Greenfield Heavy (after-step-5 → after-step-6), Migration Heavy (after-step-4 → after-step-5), Performance Heavy (after-step-5 → after-step-6).

### Role separation

- `/ark-workflow` triages and emits the chain. It does NOT invoke `/ark-context-warmup` itself — consistent with the existing "ark-workflow does not invoke downstream skills" policy. The chain is guidance; the agent runs the steps. **New:** `/ark-workflow` now persists the extended frontmatter described in Prerequisites.
- `/ark-context-warmup` is self-contained. It does its own Project Discovery, availability checks, fan-out, synthesis, and emits one `## Context Brief` to the session.

### Dependency direction — machine-readable backend subcontracts (strictly required)

`/ark-context-warmup` does NOT re-implement the backend skills. Codex flagged that inline reimplementation drifts from real contracts. Codex's second-round review flagged that a "fallback if contract missing" path re-introduces the same drift under a new name.

Resolution: **the contracts are strictly required, no fallback path.** If a backend skill lacks a valid `warmup_contract` block, warm-up treats that backend as unavailable (same as missing CLI or missing config) and logs a remediation hint. No inline reimplementation exists in warm-up.

Each backend skill exposes a **machine-readable subcontract** in its own `SKILL.md` — a fenced YAML block named `warmup_contract`:

```yaml
warmup_contract:
  version: 1
  commands:
    - id: session-continue
      shell: 'notebooklm ask {{prompt_file}} --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id: { from: config, path: 'notebooks.main.id', required: true }
        prompt_file: { from: template, template_id: session_continue_prompt }
      preconditions:
        - id: recent_session_log
          script: scripts/session_shape_check.sh
          description: 'Exits 0 if latest session log <7 days old AND has Next Steps section AND epic link resolves'
      output:
        format: json
        extract:
          where_we_left_off: '$.sections.where_we_left_off.text'
          epic_progress: '$.sections.epic_progress.text'
          immediate_next_steps: '$.sections.immediate_next_steps.text'
          critical_context: '$.sections.critical_context.text'
        required_fields: [where_we_left_off, immediate_next_steps]
    - id: bootstrap
      shell: 'notebooklm ask {{prompt_file}} --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id: { from: config, path: 'notebooks.main.id', required: true }
        prompt_file: { from: template, template_id: bootstrap_prompt }
      output:
        format: json
        extract:
          recent_sessions: '$.sections.recent_sessions.text'
          current_state: '$.sections.current_state.text'
          open_issues: '$.sections.open_issues.text'
        required_fields: [recent_sessions, current_state]
  prompt_templates:
    session_continue_prompt: 'What sessions are related to: {task_text}? Include session numbers, outcomes, and gotchas.'
    bootstrap_prompt: 'List the 5 most recent session logs with numbers, dates, objectives, outcomes. Current project state. Top open issues.'
```

Contract reader rules (pinned here so they don't drift across implementers):

1. **shell** is a command template with `{{var}}` substitution from `inputs`. Warm-up refuses to run if any `required: true` input is missing.
2. **preconditions** are external scripts that exit 0 for "run this command" or non-zero to skip. Scripts live in the backend skill's own `scripts/` directory.
3. **output.extract** uses JSONPath on the command's stdout to pull named fields. `required_fields` must be non-empty strings or warm-up treats the lane as semantically empty and records it in Evidence.
4. If the `warmup_contract` block is absent, malformed, or the script files it references don't exist: warm-up marks that backend as unavailable and logs `"Backend {skill} has no valid warmup_contract — skipped. Update the backend skill to include one."` No inline reimplementation.

This gives the abstraction teeth: the interface is concrete (shell templates, JSONPath, exit-code preconditions), the fallback path is gone (drift cannot re-enter), and the contract is a hard prerequisite of the implementation plan.

## Components

### 1. Project Discovery + Task Prompt Intake

Follows the plugin's standard context-discovery pattern: reads CLAUDE.md, extracts `project_name`, `vault_root`, `project_docs_path`, `task_prefix`, NotebookLM config location (project repo is authoritative per `notebooklm-vault/SKILL.md`; vault-root config is fallback).

Task intake order:

1. If `.ark-workflow/current-chain.md` exists and the extended-contract fields are present: read `task_text`, `task_summary`, `task_hash`, `scenario`, `chain_id`. Done.
2. If the file exists but the extended fields are absent (legacy chain): prompt user for task text, compute summary/hash inline, warn that the chain is legacy and cache will be cold.
3. If the file is absent (standalone invocation): prompt user for task text, derive `scenario` via a short `/ark-workflow`-style triage prompt ("What scenario? Greenfield / Bugfix / Ship / ..."), compute summary/hash.

### 2. Availability Probe

All checks are local (no network).

| Signal | Check |
|--------|-------|
| `HAS_CHAIN_CONTEXT` | `.ark-workflow/current-chain.md` exists, parseable as YAML+markdown, has at minimum `scenario` field |
| `HAS_EXTENDED_CONTRACT` | Above + all four new fields (`chain_id`, `task_text`, `task_summary`, `task_hash`) |
| `HAS_NOTEBOOKLM` | `notebooklm` CLI on PATH **AND** `.notebooklm/config.json` exists in project repo OR vault; config is parseable JSON; `notebooks` dict non-empty |
| `HAS_WIKI` | `{vault_path}/index.md` exists **AND** `{vault_path}/_meta/vault-schema.md` exists (needed for tiered retrieval per wiki-query's contract) |
| `HAS_TASKNOTES` | `{tasknotes_path}/meta/{task_prefix}counter` exists |
| `HAS_VAULT_BACKEND_AVAILABLE` | `HAS_WIKI` OR `HAS_TASKNOTES` (used to decide whether to run the vault-local lane at all) |

Each missing signal is logged once with a remediation hint. If `HAS_NOTEBOOKLM`, `HAS_WIKI`, and `HAS_TASKNOTES` are all false, the skill reports `"No context backends available — proceeding without warm-up. Run /ark-health to diagnose."` and exits cleanly.

### 3. Fan-Out (partial parallel, partial serial)

Dispatches subagents via the `Agent` tool. **Two lanes, not three:**

**Lane 1 — NotebookLM (parallel):** network-bound, single remote API, safe to run concurrently with local work. Runs as an independent subagent if `HAS_NOTEBOOKLM=true`.

**Lane 2 — Vault-local (serialized):** `wiki-query` and `ark-tasknotes` both touch Obsidian / MCP. Obsidian MCP connections can be brittle under concurrent access. Run as a single subagent that executes wiki-query → ark-tasknotes sequentially. Skipped entirely if `HAS_VAULT_BACKEND_AVAILABLE=false`.

**Consistency model — best-effort, not snapshot-isolated.** Codex's second-round review pointed out that a filename snapshot doesn't isolate warm-up from `/wiki-update` regeneration (wiki-query and ark-tasknotes need actual content, not just filenames), and snapshotting content means reimplementing the backends. So: warm-up does NOT attempt to isolate from concurrent `/wiki-update` runs. It reads vault state live with serialized reads. If a read fails mid-read (e.g., file truncated mid-regenerate), the subagent retries once; on second failure, the lane records a `Degraded coverage` Evidence candidate noting the concurrent-regenerate condition and moves on. Users who need point-in-time consistency should wait for `/wiki-update` to complete before running warm-up, or pass `--refresh` afterward.

| Lane | Subagent responsibility | Expected output |
|------|-------------------------|-----------------|
| 1: NotebookLM | Read `warmup_contract` from `notebooklm-vault/SKILL.md`; run session-continue if shape-valid recent log exists, else bootstrap | Structured markdown brief conforming to declared output_shape |
| 2a: Wiki-query | Read `warmup_contract` from `wiki-query/SKILL.md`; run scenario-specific query | Markdown with 1-3 relevant findings + citations, or "No matches" |
| 2b: TaskNotes | Read `warmup_contract` from `ark-tasknotes/SKILL.md`; run `status` + structured search (component/work-type first, then keyword fallback) | Status summary + related-tasks list with task ids |

**Scenario-to-wiki-query mapping (revised — every scenario gets a query):**

| Scenario | Query template |
|----------|----------------|
| Greenfield | "Has anything like [task] been built before? Are there existing components or prior design decisions?" |
| Bugfix | "Have we seen bugs related to [task] before? Known failure modes, incident notes, prior fixes?" |
| Migration | "Past migration notes for [task]? Rollback procedures, prior framework changes?" |
| Performance | "Past optimization work on [task]? Benchmarks, bottleneck analyses?" |
| Hygiene | "Related refactors or audits on [task]? Tech debt notes, prior cleanup efforts?" |
| Ship | "Deploy runbooks, rollback steps, prior incidents for [task]? Environment-specific gotchas?" |
| Knowledge Capture | "What vault pages already exist on [task]'s topic? Recent session coverage?" |

### 4. Synthesis

Main skill receives both lane outputs and assembles one `## Context Brief`:

```
## Context Brief

### Where We Left Off
[from notebooklm session-continue OR "Fresh start — no recent session found"]

### Recent Project Activity
[from notebooklm bootstrap, or session-continue's epic progress]

### Vault Knowledge Relevant to This Task
[from wiki-query, or "Not queried — wiki backend unavailable"]

### Related Tasks & In-flight Work
[from ark-tasknotes status + structured search, or "Not queried — tasknotes backend unavailable"]

### Evidence
[candidates with task ids / citations / confidence; see below]
```

### 5. Evidence Generator (replaces boolean Flags)

Scans results for patterns and emits **candidates with evidence**, not boolean verdicts. Each candidate includes: type, referent (task id / citation), reason/matched-field, and confidence (`high` / `medium` / `low`).

| Candidate type | Trigger | Required evidence in output |
|----------------|---------|------------------------------|
| `Possible duplicate` | Open TaskNote whose `component` or `work-type` matches the task's extracted component, OR whose title has >60% token overlap with task_summary (stop-words removed) | Task id, title, matched field (`component: X` or `token-overlap: N%`), confidence |
| `Possible prior rejection` | NotebookLM citation sentence contains "decided against", "tried and failed", "rejected", "won't do" near a noun phrase matching task_summary's keywords (within 20 tokens) | Session citation, quoted phrase, confidence |
| `Possible in-flight collision` | Another open TaskNote with `status: in-progress` sharing `component` field, OR shared session tag from the current active epic | Task id, shared field, status, confidence |
| `Stale context` | Most recent session log is >14 days old (informational only) | Last session date, age in days |
| `Degraded coverage` | One or more backends unavailable (informational only) | Which backends and why |

**Confidence calibration:**

- `high`: structured-field match (component, work-type, status) — evidence is categorical.
- `medium`: token-overlap match OR NotebookLM citation with quoted trigger phrase near matched keywords.
- `low`: keyword-only match with no structural backing.

Candidates with `low` confidence and no structural evidence are dropped (noise floor). If no candidates remain, the Evidence section reads `None`.

## Data Flow

```
[User invokes /ark-context-warmup, directly or as chain step 0]
  |
  v
[1] Project Discovery from CLAUDE.md
  |
  v
[2] Task intake: read current-chain.md extended fields OR prompt user
    -> task_text, task_summary, task_hash, scenario, chain_id
  |
  v
[3] Availability probe
    -> HAS_CHAIN_CONTEXT / HAS_EXTENDED_CONTRACT / HAS_NOTEBOOKLM /
       HAS_WIKI / HAS_TASKNOTES
    - If NotebookLM + Wiki + Tasknotes all false: emit + EXIT 0
  |
  v
[4] Cache check: compute cache_key = sha256(project_path, chain_id, task_hash)
    - If .ark-workflow/context-brief-{cache_key}.md exists, age <2h, and
      not --refresh: re-emit cached brief and EXIT 0
  |
  v
[5] Fan-out (two lanes)
    Lane 1 (parallel): NotebookLM subagent
      - Read warmup_contract from notebooklm-vault/SKILL.md
      - Smart-pick: session-continue if shape-valid recent log, else bootstrap
    Lane 2 (serial): Vault-local subagent (live reads, best-effort)
      - Run wiki-query with scenario-specific template
      - Run ark-tasknotes status + structured search
      - On mid-read failure: retry once; on second failure, record
        Degraded coverage Evidence and move on
  |
  v
[6] Fan-in: collect results (90s per-lane timeout; partial results OK)
  |
  v
[7] Evidence generator scans structured outputs for candidates
  |
  v
[8] Synthesizer assembles Context Brief
    - Atomic write: .ark-workflow/context-brief-{cache_key}.md (write to
      temp file, then rename)
    - Prune other context-brief-*.md files older than 24h
    - Emit to session
  |
  v
[9] Hand back to chain flow
```

### Cache identity and lifecycle

- **Cache filename:** `context-brief-{chain_id}-{task_hash[:8]}.md`. No hash of the absolute path. The cache file lives inside `.ark-workflow/` which is already repo-scoped. This keeps the cache portable across symlinks, repo moves, and machine handoff — codex's second-round concern.
- **Location:** `.ark-workflow/` (same directory as `current-chain.md`)
- **Fresh if:** file exists AND mtime within 2 hours AND the `chain_id` + `task_hash` in the file's own frontmatter match the current chain's values (defense-in-depth: filename can't be the only identity check because `chain_id` collisions are theoretically possible)
- **Invalidated by:**
  - File age >2 hours
  - `chain_id` change (new chain — either re-triage or new `/ark-workflow` invocation)
  - `task_hash` change (task was edited mid-chain)
  - Explicit `/ark-context-warmup --refresh`
- **Concurrent-write safety:** Synthesizer writes to `context-brief-{chain_id}-{task_hash[:8]}.md.tmp`, then atomic-renames. If two warmup instances race, last writer wins cleanly; no partial-write corruption.
- **Pruning:** On each run, delete `context-brief-*.md` files older than 24 hours. Prevents unbounded directory growth across re-triage events.

### Token and latency budget

| Case | Wall-clock | Tokens to parent session |
|------|------------|--------------------------|
| All backends available, cache miss | ~20-60s (NotebookLM parallel, vault lane serial) | ~6-10k (Context Brief only) |
| NotebookLM only (no vault) | ~15-30s | ~4-6k |
| Vault only (no NotebookLM) | ~10-25s | ~3-5k |
| All three unavailable | <2s | ~100 ("no backends" message) |
| Cache hit | <1s | ~6-10k (cached brief) |

Subagent raw outputs stay within subagent contexts — only the synthesized brief reaches the parent.

## Error Handling

### Failure matrix (expanded post-codex review)

| Failure | Detection | Response |
|---------|-----------|----------|
| CLAUDE.md missing required field | Project Discovery | Emit field-missing message; EXIT 0 (don't block chain) |
| `current-chain.md` absent | Availability probe | Treat as standalone invocation; prompt for task text |
| `current-chain.md` present but unparseable YAML | Task intake | Log `"current-chain.md is corrupt — falling back to standalone prompt"`; prompt user |
| `current-chain.md` present but missing extended-contract fields | Task intake | Log `"Legacy chain file — cache will be cold. Run updated /ark-workflow to regenerate."`; prompt user for task text |
| `.notebooklm/config.json` exists but CLI missing | Availability probe | Log skip + hint (`pipx install notebooklm-cli`); skip NotebookLM lane |
| `.notebooklm/config.json` exists but unparseable | Availability probe | Log `"NotebookLM config malformed — skipping."`; skip NotebookLM lane |
| `.notebooklm/config.json` has multiple notebooks, no selection rule | NotebookLM lane | Pick first notebook, log: `"Multiple NotebookLM notebooks configured; using [id]. Set a default in config to silence."` |
| NotebookLM config has notebook key but notebook id is null/empty | NotebookLM lane | Log `"NotebookLM config incomplete — skipping."`; skip lane |
| `notebooklm` CLI returns auth error | NotebookLM lane stderr match | Log `"NotebookLM auth expired. Run: notebooklm auth login"`; skip lane |
| `notebooklm ask` times out or 5xx | NotebookLM lane retries once with 15s backoff; second failure fatal | Log + skip lane |
| Session log glob empty | NotebookLM smart-pick | Fall through to `bootstrap` (not an error) |
| Recent session log exists but lacks Next Steps section OR resolvable epic link | NotebookLM smart-pick shape check | Fall through to `bootstrap`; log: `"Latest session log missing required shape — using bootstrap."` |
| `index.md` missing | Availability probe | Log + remediation (`/wiki-update`); skip wiki step in vault lane |
| `index.md` present but `_meta/vault-schema.md` missing | Availability probe | Log `"Vault schema missing — wiki query uses legacy retrieval. Run /wiki-setup to refresh."`; still run wiki-query (degraded) |
| Obsidian not running (MCP unavailable for tasknotes) | `tasknotes_health_check` fails | Fall back to markdown scan of `{tasknotes_path}/Tasks/`; log degraded mode |
| TaskNotes counter missing | Availability probe | Log + remediation (`/wiki-setup`); skip tasknotes step in vault lane |
| TaskNotes search returns 100+ matches | TaskNotes step | Truncate to top 10 by structural relevance (status=in-progress first, then component match); note truncation count |
| `/wiki-update` regenerating index/files while warm-up reads | Read-mid-regeneration error (truncated file, YAML parse failure, empty read) | Retry read once. On second failure, mark lane semantically empty and record a `Degraded coverage` Evidence candidate noting concurrent-regenerate. No snapshot isolation — live reads only. |
| Backend skill has no valid `warmup_contract` block (missing, malformed, or referenced script files absent) | Subcontract read + validation | Mark that backend as unavailable (same outcome as missing CLI). Log: `"Backend {skill} has no valid warmup_contract — skipped. Update the backend skill to include one."` **No inline fallback.** The contract is strictly required. |
| Any subagent lane exceeds 90s timeout | Parent timer | Kill lane; log; continue fan-in with partial results |
| Subagent returns structurally valid but semantically empty output | Evidence generator pre-scan | Include empty output in brief; add `Degraded coverage` candidate noting empty response |
| Subagent returns malformed output (doesn't validate against declared shape) | Synthesizer validation | Include raw under lane's section with `[warm-up: unstructured output follows]` prefix; skip evidence extraction for that lane |
| Concurrent warm-up writes to same `context-brief-{hash}.md` | Atomic rename | Last writer wins; no corruption. Log: `"Another warm-up completed — using latest brief."` |
| Partial cache write (skill killed mid-write) | Next run reads tmp file | `.tmp` files ignored by cache check; pruned by 24h rule |
| `.ark-workflow/` not writable | File write attempt | Skip cache write; emit brief to session anyway; log non-fatal failure |
| User interrupts (Ctrl-C) | Signal | Kill subagents; skill exits; chain resumable with `--refresh` |
| All three backends unavailable | Availability probe | Emit `"No context backends available — proceeding without warm-up. Run /ark-health to diagnose."` EXIT 0 |

### Two guarantees

1. **Never blocks the chain.** Warm-up always exits cleanly (code 0) with a user-visible message. Chain step 1 proceeds regardless.
2. **Every skip is logged with a remediation hint.** (Revised from earlier "no silent skips" phrasing — the actual promise is auditability, not verbosity.)

### Deliberately out of scope

- Stale NotebookLM sync detection (deferred to `/ark-health`).
- Cross-project context.
- Contradictory-signal resolution (surfaced, not resolved).
- Retry on partial success (report what succeeded).
- Locking against concurrent `/wiki-update` runs (handled via snapshot-before-query; we accept eventual consistency).

## Testing

### 1. Unit tests (helpers)

Pure functions extracted to `scripts/warmup-helpers.{sh,py}`, tested with bats-core or pytest:

| Function | Test cases |
|----------|------------|
| `compute_task_hash` | Deterministic output for same input; different for different tasks; stop-word filtering is consistent; whitespace-normalized |
| `compute_cache_key` | Includes project_path + chain_id + task_hash; different combos produce different keys |
| `validate_session_log_shape` | Has Next Steps + epic link → valid; missing Next Steps → invalid; has Next Steps but no epic link → invalid; pre-1.8.0 "Results" section → falls through to legacy mode |
| `should_run_session_continue` | Recent (<7d) + valid shape → session-continue; recent + invalid shape → bootstrap; old (>7d) → bootstrap; empty glob → bootstrap |
| `map_scenario_to_wiki_query` | Each of the 7 scenarios has its expected template; unknown scenario → generic fallback |
| `detect_duplicate_task_candidate` | Component match → high confidence; token-overlap >60% → medium; token-overlap 40-60% + no structural match → low (dropped); closed tasks excluded |
| `detect_prior_rejection_candidate` | Trigger phrase + keyword match within 20 tokens → medium confidence; trigger phrase alone → dropped |
| `detect_in_flight_collision_candidate` | Shared `component` + status=in-progress → high confidence; shared tag + no component → medium |
| `is_cache_fresh` | <2h + matching chain_id + matching task_hash → fresh; any mismatch → stale; missing → stale |
| `prune_stale_briefs` | Deletes `context-brief-*.md` older than 24h; preserves fresh; handles empty dir |
| `synthesize_brief` | All lanes present → full brief; one missing → "Not queried" section; malformed → raw with `[unstructured]` prefix |
| `parse_warmup_contract` | Valid YAML block → parsed struct; missing block → returns null + triggers fallback path |

### 2. Integration tests (filesystem)

bats-core against throwaway temp projects:

| Scenario | Setup | Expected |
|----------|-------|----------|
| All backends available, extended contract present | Full CLAUDE.md + configs + stubbed `notebooklm` CLI + current-chain.md with extended fields | Both lanes dispatch; cache written with full key |
| Legacy chain file (no extended fields) | current-chain.md with only old fields | Prompt-for-task path runs; log notes legacy mode; cache cold |
| Only vault available | Remove NotebookLM config + TaskNotes counter | Only wiki step in vault lane runs; skip hints logged |
| Only tasknotes available | Remove NotebookLM + index.md | Only tasknotes step runs |
| None available | Remove all three | "No context backends" message; EXIT 0 |
| Missing required CLAUDE.md field | Remove `project_docs_path` | Field-missing message; EXIT 0; no probe |
| `.ark-workflow/` not writable | `chmod -w` | Brief emitted; cache failure logged; no crash |
| Corrupt current-chain.md (invalid YAML) | Write garbage | Log + prompt-for-task fallback |
| Multi-notebook NotebookLM config | Config with 2 notebooks, no default | First notebook picked; log informs user |
| Concurrent warm-up (two instances) | Launch two warmup processes targeting same cache key | Both complete; one cache file remains; no partial-write file |
| Backend missing warmup_contract | Remove YAML block from stub SKILL.md | Fallback path runs; log recorded |

### 3. End-to-end smoke tests (manual, documented in `scripts/smoke-test.md`)

Run before every release tag:

1. Real Ark project, all three backends configured → run `/ark-context-warmup`; verify all five Context Brief sections present; under 90s.
2. Invoke `/ark-workflow` with a sample bugfix prompt → verify `current-chain.md` has the four new fields; verify resolved chain starts with `0. /ark-context-warmup`; verify subsequent steps renumbered.
3. Run `/ark-context-warmup` twice within 5 min on same chain → second run hits cache, returns in <2s with identical output.
4. Run `/ark-context-warmup --refresh` → cache bypassed, full fan-out runs.
5. Re-triage scenario: finish a chain, invoke `/ark-workflow` with a different task → verify new `chain_id` + new `task_hash` produces a cache miss.
6. Run `/ark-context-warmup` concurrently with `/wiki-update` → verify warm-up completes (possibly with a "vault regenerating" log line) and does not corrupt either process.

### 4. Evidence-candidate regression tests

Fixture library at `skills/ark-context-warmup/fixtures/`:

- `duplicate-component-hit.md` — open TaskNote with matching `component` field → emits high-confidence `Possible duplicate`
- `duplicate-token-overlap-medium.md` — 70% token overlap, no structural match → emits medium-confidence candidate
- `duplicate-token-overlap-low-noise.md` — 45% overlap, no structural match → dropped (below confidence floor)
- `duplicate-closed-ignored.md` — matching component but status=done → no candidate emitted
- `prior-rejection-structured.md` — "decided against X" near matched keyword → emits medium-confidence `Possible prior rejection`
- `prior-rejection-false-positive.md` — "decided against" in unrelated sentence → no candidate (documents known noise pattern)
- `in-flight-collision-component.md` — shared `component` + in-progress → high confidence
- `stale-context.md` — 20+ day old session log → emits `Stale context`
- `degraded-coverage.md` — one lane skipped → emits `Degraded coverage`

Each fixture pairs with an expected-candidates assertion. Catches evidence-generator regressions immediately.

### 5. Chain-file integrity test

CI grep on all `chains/*.md`:

- First numbered step must be `` 0. `/ark-context-warmup` ``
- Any `handoff_marker: after-step-N` values must match the updated step numbers

### 6. Contract-extension integrity test

CI parses `skills/ark-workflow/SKILL.md` for the frontmatter template in the continuity section. Asserts that `chain_id`, `task_text`, `task_summary`, `task_hash` are all present. Prevents regression of the prerequisite change.

### What we don't test

- NotebookLM/Obsidian backend correctness (their skills' tests, not ours).
- Parallel subagent timing precision (we test completion-or-timeout, not wall-clock numbers).
- LLM-driven synthesis quality (synthesizer is deterministic template assembly, no LLM call).

## Open Questions — to be pinned by `/writing-plans`

These are implementation-level decisions that don't change the spec's shape but must be pinned before code is written. Codex's second-round review identified these as sources of drift if left unpinned:

1. **`task_text` → `task_summary` → `task_hash` algorithm.** Pin exact normalization: NFC Unicode normalization, lowercase via `str.lower()` (not locale-dependent folds), strip punctuation except `-` and `_`, collapse whitespace, remove stop-words from a pinned wordlist (use `scripts/stopwords.txt`, committed to the repo), truncate summary to 120 chars at a word boundary. Empty or all-stop-word tasks use the literal string `__empty__` as the summary. `task_hash = sha256(task_summary.encode('utf-8'))[:16]`. `task_hash` is computed once at chain emission and NEVER updated — if the user edits the task mid-chain, they must re-trigger `/ark-workflow` to get a new chain. The implementation plan will include test fixtures covering empty strings, Unicode variants (é vs e◌́), stop-word-only tasks, and non-BMP characters.

2. **`task_summary` role split.** Per codex second-round: `task_summary` was doing too much (hash input + human display + matching). Split:
   - `task_normalized` — used as the hash input (internal only, not user-facing)
   - `task_summary` — used for human display only, formatted as a single-line truncation of `task_text` with whitespace collapsed but preserving case and punctuation (up to 120 chars)
   - Token-overlap matching for duplicate detection uses `task_normalized` as its token source
   - The frontmatter stores both fields

3. **Evidence confidence calibration rules (deterministic).** `/writing-plans` must pin:
   - Duplicate: `high` = structural field match (component, work-type) + open status. `medium` = ≥60% token-overlap on `task_normalized` with an open task's normalized title. `low` = 40-59% overlap with no structural match → dropped as noise.
   - Prior rejection: `medium` = trigger phrase ("decided against"/"tried and failed"/"rejected"/"won't do") within a 30-token window of at least 2 keyword tokens from `task_normalized`. Anything less → dropped.
   - In-flight collision: `high` = shared `component` field + status=in-progress on another TaskNote. `medium` = shared session tag resolvable via the current epic's backlinks. No `low` tier (too noisy).
   - `work-type` alone does NOT produce high confidence (too generic) — codex's call.

4. **Obsidian MCP concurrency model.** Spec assumes MCP connections are brittle enough to require serializing the vault-local lane. Implementation plan runs a concurrency probe test; if safe, `/writing-plans` can relax to parallel wiki + tasknotes inside Lane 2.

5. **NotebookLM multi-notebook selection.** Spec's current behavior ("pick first notebook + log") is not safe — silently fetches wrong context. `/writing-plans` must resolve: either (a) require a `default_for_warmup` field in `.notebooklm/config.json` and skip the lane if absent, OR (b) warm-up prompts user at runtime to pick. Defer the choice, but do NOT ship with silent first-pick.

6. **`warmup_contract` preconditions scripts — exact interface.** Spec says preconditions are external scripts that exit 0 to run / non-zero to skip. `/writing-plans` pins the exact calling convention (argv, env vars, stdin), the timeout (5s default), and what happens if the script itself errors.

## Implementation Checklist (high-level; detailed plan to follow via `/writing-plans`)

**Prerequisites (must land first):**

1. Extend `skills/ark-workflow/SKILL.md` Step 6.5 frontmatter template with the four new fields (`chain_id`, `task_text`, `task_summary`, `task_hash`). Add a helper snippet to compute them.
2. Add `warmup_contract:` YAML block to `skills/notebooklm-vault/SKILL.md` describing its session-continue + bootstrap commands and output shapes.
3. Add `warmup_contract:` YAML block to `skills/wiki-query/SKILL.md`.
4. Add `warmup_contract:` YAML block to `skills/ark-tasknotes/SKILL.md` describing its status + structured search commands.

**Warm-up skill:**

5. Create `skills/ark-context-warmup/SKILL.md` with frontmatter + command routing.
6. Add `scripts/warmup-helpers.{sh,py}` with the twelve unit-testable helper functions.
7. Add unit tests for helpers.
8. Implement availability probe (including extended-contract check).
9. Implement NotebookLM lane (parallel subagent, reads warmup_contract, smart-pick with shape validation).
10. Implement vault-local lane (serialized subagent, live reads with retry-once-then-degrade, wiki-query then tasknotes).
11. Implement evidence generator with confidence calibration.
12. Implement synthesizer with atomic cache write + 24h pruning.
13. Implement `--refresh` flag.
14. Add integration tests.
15. Add evidence-candidate regression fixtures + tests.
16. Add contract-extension integrity CI test.

**Chain wiring + distribution:**

17. Prepend `0. /ark-context-warmup` to all seven `chains/*.md` files; shift all step numbers and handoff markers.
18. Add chain-file integrity CI check.
19. Add a smoke-test runbook at `skills/ark-context-warmup/scripts/smoke-test.md`.
20. Update `skills/ark-workflow/SKILL.md` File Map if needed to reference the new step 0 expectation.
21. Register `/ark-context-warmup` in `.claude-plugin/marketplace.json` + `.claude-plugin/plugin.json`.
22. Bump `VERSION` and add `CHANGELOG` entry per the project's "always bump version" convention.
23. Write the user-facing announcement explaining the new step 0 behavior + the frontmatter contract change.
