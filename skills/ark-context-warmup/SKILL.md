---
name: ark-context-warmup
description: Load recent + relevant project context before any /ark-workflow chain. Runs as step 0 of every chain. Queries /notebooklm-vault (if set up), /wiki-query (if set up), and /ark-tasknotes (if set up) to emit a single Context Brief. Triggers on "warm up", "context brief", "load context", "start fresh on this project". Also invoked automatically as chain step 0 by /ark-workflow.
---

# Ark Context Warm-Up

Load recent + relevant project context. Runs as step 0 of every `/ark-workflow` chain. Emits one structured `## Context Brief` synthesizing signals from NotebookLM, the vault, and TaskNotes — with an Evidence section surfacing possible duplicates, prior rejections, and in-flight collisions.

Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`.
Pinned decisions: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` (D1–D6).

## Usage

- `/ark-context-warmup` — automatic invocation from `/ark-workflow` chain step 0; reads task context from `.ark-workflow/current-chain.md`
- `/ark-context-warmup --refresh` — bypass cache, force full fan-out
- `/ark-context-warmup` standalone (no chain file) — prompts for task text, derives scenario

## Project Discovery

Follow the plugin's context-discovery pattern (see plugin CLAUDE.md):

1. Read the project's CLAUDE.md for: `project_name`, `vault_root`, `project_docs_path`, `task_prefix`, `tasknotes_path`
2. Locate NotebookLM config: check `{vault_root}/.notebooklm/config.json` first, then `{project_root}/.notebooklm/config.json`
3. If any required field is missing, emit `"CLAUDE.md is missing [field] — context warm-up cannot run. Proceeding without warm-up."` and EXIT 0

### Resolve `ARK_SKILLS_ROOT` (required for all later script invocations)

In consumer projects (e.g., ArkNode-AI, ArkNode-Poly), this plugin's scripts live at `~/.claude/plugins/cache/.../ark-skills/` — **not** at `./skills/` of the CWD. All later script invocations in this skill must use absolute paths rooted at the plugin. Resolve once at the start:

```bash
# Already set by Claude Code when invoking a plugin skill? Prefer that.
if [ -n "${CLAUDE_PLUGIN_DIR:-}" ] && [ -d "$CLAUDE_PLUGIN_DIR" ]; then
    ARK_SKILLS_ROOT="$CLAUDE_PLUGIN_DIR"
# Otherwise, discover via the plugin marketplace.json anchor.
elif [ -f "$(pwd)/.claude-plugin/marketplace.json" ]; then
    # CWD is the ark-skills repo itself (dev/test mode)
    ARK_SKILLS_ROOT="$(pwd)"
else
    # Consumer project: search installed plugins.
    ARK_SKILLS_ROOT=$(find ~/.claude/plugins -maxdepth 6 -type d -name ark-skills 2>/dev/null | head -1)
fi

if [ -z "$ARK_SKILLS_ROOT" ] || [ ! -f "$ARK_SKILLS_ROOT/skills/ark-context-warmup/SKILL.md" ]; then
    echo "ark-skills plugin not found — context warm-up cannot run. Proceeding without warm-up." >&2
    exit 0
fi
export ARK_SKILLS_ROOT
```

**All subsequent `python3 skills/...` invocations in this skill MUST be rewritten to `python3 "$ARK_SKILLS_ROOT/skills/..."`** — including the helpers in Step 1 below, the contract executor paths passed to subagents, and the script paths referenced in `warmup_contract.preconditions`. Python modules invoked via `python3 "$ARK_SKILLS_ROOT/..."` can continue to use `Path(__file__).parent` for sibling-file resolution, so no changes inside the scripts themselves are needed.

## Workflow

### Step 1: Task intake

Read `.ark-workflow/current-chain.md` if present. The file should contain extended frontmatter with `chain_id`, `task_text`, `task_normalized`, `task_summary`, `task_hash`, `scenario`.

If any of those fields is missing (legacy chain, or file absent): prompt the user for the task text and compute the fields inline:

```bash
CHAIN_ID=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" chain-id)
TASK_NORMALIZED=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" normalize "$TASK_TEXT")
TASK_SUMMARY=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" summary "$TASK_TEXT")
TASK_HASH=$(python3 "$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts/warmup-helpers.py" hash "$TASK_NORMALIZED")
```

Log: `"Legacy chain file — cache will be cold. Run updated /ark-workflow to regenerate."`

### Step 2: Availability probe

Run `availability.py probe(...)` per D5 rules (see pinned decisions). Record which backends are available. If all three are unavailable, emit `"No context backends available — proceeding without warm-up. Run /ark-health to diagnose."` and EXIT 0.

### Step 3: Cache check

Unless `--refresh` is passed:
```bash
python3 -c "
import sys
sys.path.insert(0, '$ARK_SKILLS_ROOT/skills/ark-context-warmup/scripts')
from synthesize import cached_brief_if_fresh
from pathlib import Path
b = cached_brief_if_fresh(cache_dir=Path('.ark-workflow'), chain_id='$CHAIN_ID', task_hash='$TASK_HASH')
if b: print(b)
"
```

If cache hit: emit the cached brief to the session and EXIT 0.

### Step 4: Fan-out (uses `executor.py` from Task 15)

All shell substitution, precondition invocation, JSON parsing, and JSONPath extraction go through `executor.execute_command(...)` — the SKILL.md does NOT reimplement those. The D6 env vars (`WARMUP_TASK_TEXT`, `WARMUP_TASK_NORMALIZED`, `WARMUP_TASK_HASH`, `WARMUP_TASK_SUMMARY`, `WARMUP_SCENARIO`, `WARMUP_CHAIN_ID`, `WARMUP_VAULT_PATH`, `WARMUP_PROJECT_DOCS_PATH`, `WARMUP_PROJECT_NAME`, `WARMUP_TASK_PREFIX`, `WARMUP_TASKNOTES_PATH`) are exported before invoking either lane.

**Lane 1 (parallel if available) — NotebookLM:**
- Load `warmup_contract` via `contract.load_contract(Path("$ARK_SKILLS_ROOT/skills/notebooklm-vault/SKILL.md"))`
- Dispatch a subagent (`Agent` tool, `general-purpose` type) with these instructions:
  - Read the contract dict
  - For each command (`session-continue`, then `bootstrap` as fallback): call `executor.execute_command(cmd, config=notebooklm_config, templates=contract["prompt_templates"], env_overrides={}, timeout_s=90)`. Stop at the first command that returns non-None (not skipped).
  - Return the extracted dict as JSON

**Lane 2 (serialized) — Vault-local:**
Only run if `HAS_WIKI` or `HAS_TASKNOTES`. Dispatch one subagent that sequentially:
1. If `HAS_WIKI`: load wiki-query contract, export `WARMUP_SCENARIO_QUERY_TEMPLATE=<contract["scenario_templates"][scenario]>` into the subagent's env (this is what the contract's `scenario_query` prompt template references), then call `executor.execute_command(...)`. On None result, record a `Degraded coverage` candidate for the wiki lane and continue to tasknotes.
2. If `HAS_TASKNOTES`: load tasknotes contract, call `executor.execute_command(...)`. Same `Degraded coverage` handling.
3. Return combined JSON: `{"wiki": ..., "tasknotes": ..., "degraded_lanes": [...]}`

Each lane has a 90s outer timeout at the subagent level (in addition to the 90s per-command timeout inside `executor.execute_command`).

### Step 5: Evidence + Synthesis

- Pass all lane outputs to `evidence.derive_candidates(...)`
- Pass the three lane outputs + evidence + `has_omc` (from the `availability.probe(...)` result dict) to `synthesize.assemble_brief(..., has_omc=availability["has_omc"])`. This renders the `OMC detected: yes/no` line at the top of the Context Brief (spec AC8).
- `synthesize.write_brief_atomic(...)` to cache
- Emit the brief to the session

### Step 6: Hand off

Print: `"Context warm-up complete. Proceeding to next step: {chain's step 1}"`

## File Map

- `scripts/warmup-helpers.py` — task_normalize, task_summary, task_hash, chain_id_new, CLI dispatch
- `scripts/contract.py` — warmup_contract YAML parser + validator
- `scripts/executor.py` — runtime engine: resolves inputs, runs preconditions, substitutes shell templates, extracts JSONPath fields, validates required_fields
- `scripts/availability.py` — backend availability probe (D5-compliant multi-notebook handling)
- `scripts/evidence.py` — deterministic evidence-candidate generator (D3 rules)
- `scripts/synthesize.py` — brief assembly + atomic cache write + pruning
- `scripts/stopwords.txt` — committed stopwords wordlist
- `fixtures/` — evidence-candidate regression fixtures
- `scripts/smoke-test.md` — manual release runbook
