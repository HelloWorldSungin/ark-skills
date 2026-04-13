# /ark-context-warmup — Smoke Test Runbook

Run before every release tag. Each step has a pass/fail check. Failing any step blocks the PR.

## Prerequisites

- Real Ark project checkout (not a stub): `ArkNode-AI`, `ArkNode-Poly`, or `ark-skills` itself
- NotebookLM CLI authenticated: `notebooklm auth check --test`
- Obsidian running locally
- `bats-core` installed: `brew install bats-core`

## Tests

### 1. Happy path — all three backends

From the real project's repo root:

```bash
/ark-context-warmup
```

**Pass criteria:**
- Brief emitted within 90 seconds
- All five sections present: `Where We Left Off`, `Recent Project Activity`, `Vault Knowledge`, `Related Tasks`, `Evidence`
- No `ERROR` / `Traceback` in output

### 2. Chain integration — bugfix prompt

```bash
/ark-workflow "Fix rate limiter returning 500 under burst load"
```

**Pass criteria:**
- Resolved chain's first step is `0. /ark-context-warmup`
- Subsequent steps renumbered starting at 1
- `.ark-workflow/current-chain.md` contains all four new frontmatter fields

### 3. Cache hit on re-run

```bash
/ark-context-warmup
# wait 5 seconds
/ark-context-warmup
```

**Pass criteria:**
- Second run completes in <2 seconds
- Identical output to first run

### 4. Cache bypass with --refresh

```bash
/ark-context-warmup --refresh
```

**Pass criteria:**
- Full fan-out runs again (~20–60s)
- Output may differ (if backends changed) or match (if nothing changed); both OK

### 5. Re-triage produces fresh cache miss

```bash
/ark-workflow "Different task this time"
/ark-context-warmup
```

**Pass criteria:**
- New `chain_id` in `.ark-workflow/current-chain.md`
- Fresh brief generated (not cached)
- Previous brief file still exists or pruned (either OK within 24h)

### 6. Concurrent run does not corrupt cache

In two terminals simultaneously:

```bash
# Terminal 1
/ark-context-warmup --refresh

# Terminal 2
/ark-context-warmup --refresh
```

**Pass criteria:**
- Both commands complete
- Exactly one `context-brief-*.md` file matches the current chain_id
- No `.tmp` files left in `.ark-workflow/` (a brief pause of up to 10 minutes is acceptable — the prune step in the next warmup will clean up orphan tmp files)

### 7. Missing backend — graceful skip

Temporarily rename `.notebooklm/`:

```bash
mv .notebooklm .notebooklm.backup
/ark-context-warmup --refresh
mv .notebooklm.backup .notebooklm
```

**Pass criteria:**
- Brief still emitted
- Brief contains `Degraded coverage` in Evidence section mentioning notebooklm
- Skip hint logged with remediation

### 8. YAML-sensitive task text — frontmatter doesn't break

Ark-workflow's Step 6.5 renders `task_summary` inline in the chain-file frontmatter. Non-alphanumeric task text (containing `:`, `#`, `|`, quotes, newlines-in-summary) must not produce an invalid YAML document.

```bash
/ark-workflow 'Review this task: fix #123 — users can\x27t log in | blocker'
# verify .ark-workflow/current-chain.md parses as YAML
python3 -c "import yaml; yaml.safe_load(open('.ark-workflow/current-chain.md').read().split('---')[1])"
```

**Pass criteria:**
- `/ark-workflow` completes without syntax error
- The chain-file frontmatter parses as valid YAML
- `task_summary` roundtrips through the YAML parser to the original human-readable text (case preserved; collapsed whitespace)

Note: task_summary is the human-display projection; LLMs writing the chain file naturally quote YAML-unsafe characters, but this smoke test is the cross-check that the convention holds in practice. If this test fails, the fix is either to quote/block-scalar `task_summary` in the Step 6.5 template, or to sanitize the summary projection in `warmup-helpers.py`.
