# MANUAL_STAGE5.md — Stage-5 Self-Test Runbook for /ark-update

This runbook is the **Stage-5 ship gate** for the `/ark-update` framework.
It must be executed manually before opening the v1.14.0 release PR.
All steps are mandatory. Do not skip.

Estimated time: ~30 minutes.

---

## Part 0: Prerequisites

- Branch `ark-update` checked out at tip (confirm with `git log --oneline -3`).
- `python3 -m pytest skills/ark-update/tests/ -v` must pass 100% (run it now if not recently run).
- `ARK_SKILLS_ROOT` or `--skills-root` must point to this repo root.
- `python3` 3.9+ with `pyyaml` and `packaging` installed (`pip install pyyaml packaging`).

Set variables used in commands below:

```bash
SKILLS_ROOT="$(pwd)"   # run from ark-skills repo root
MIGRATE="$SKILLS_ROOT/skills/ark-update/scripts/migrate.py"
FIXTURES="$SKILLS_ROOT/skills/ark-update/tests/fixtures"
```

---

## Part 1: Fixture Authenticity Check

> **This substep must run BEFORE the convergence runbook (Part 2).**
>
> **Fixture authenticity check.** For each of `pre-v1.11/`, `pre-v1.12/`, `pre-v1.13/`,
> compare the fixture's `CLAUDE.md` against the actual CLAUDE.md from the matching
> historical git tag (if it exists in this repo), or visually inspect for structural
> realism. Not byte-equality (fixtures are minimized to relevant content) but
> structural realism — "does the fixture represent a believable pre-v(N) project shape?"
>
> Reviewer signs off that differences are intentional (e.g., trimmed to minimum
> relevant content) before Stage-5 proceeds.

Run the following diffs. If the tags don't exist in this repo, skip the diff
and do a visual inspection of each fixture CLAUDE.md instead.

```bash
# For pre-v1.11: compare against the state at v1.10.x (or closest tag)
diff "$FIXTURES/pre-v1.11/CLAUDE.md" <(git show v1.10.1:CLAUDE.md 2>/dev/null || echo "(tag not found)")

# For pre-v1.12: compare against the state at v1.11.x
diff "$FIXTURES/pre-v1.12/CLAUDE.md" <(git show v1.11.0:CLAUDE.md 2>/dev/null || echo "(tag not found)")

# For pre-v1.13: compare against the state at v1.12.x
diff "$FIXTURES/pre-v1.13/CLAUDE.md" <(git show v1.12.0:CLAUDE.md 2>/dev/null || echo "(tag not found)")
```

**Expected:** Differences are intentional (fixtures are trimmed to minimum content).
The fixture CLAUDE.md must have the same structural shape as the real project's
CLAUDE.md at that version point — same section headers, same table rows, same
managed regions (or absence thereof) for that version.

**Reviewer sign-off required.** Note any deviations in the "Observed" section below.

---

## Part 2: Convergence Runbook — Three Historical Fixtures

For each of the three pre-vN fixtures, follow this procedure:

### Step A: Copy fixture to /tmp/

```bash
cp -r "$FIXTURES/pre-v1.11" /tmp/stage5-pre-v1.11
cp -r "$FIXTURES/pre-v1.12" /tmp/stage5-pre-v1.12
cp -r "$FIXTURES/pre-v1.13" /tmp/stage5-pre-v1.13
```

### Step B: Remove expected-post/ from each copy

```bash
rm -rf /tmp/stage5-pre-v1.11/expected-post
rm -rf /tmp/stage5-pre-v1.12/expected-post
rm -rf /tmp/stage5-pre-v1.13/expected-post
```

### Step C: Run engine on each fixture

```bash
# pre-v1.11
python3 "$MIGRATE" \
  --project-root /tmp/stage5-pre-v1.11 \
  --skills-root "$SKILLS_ROOT" \
  --force

# pre-v1.12
python3 "$MIGRATE" \
  --project-root /tmp/stage5-pre-v1.12 \
  --skills-root "$SKILLS_ROOT" \
  --force

# pre-v1.13
python3 "$MIGRATE" \
  --project-root /tmp/stage5-pre-v1.13 \
  --skills-root "$SKILLS_ROOT" \
  --force
```

**Expected engine output for pre-v1.11:**
```
Phase 2 (convergence): 4 applied, 0 drift-overwritten, 0 skipped, 0 failed
```

**Expected engine output for pre-v1.12:**
```
Phase 2 (convergence): 3 applied, 0 drift-overwritten, 1 skipped, 0 failed
```

**Expected engine output for pre-v1.13:**
```
Phase 2 (convergence): 2 applied, 0 drift-overwritten, 2 skipped, 0 failed
```

### Step D: Diff post-state against expected-post/ byte-exact

```bash
diff -rq --exclude='.ark' \
  /tmp/stage5-pre-v1.11 \
  "$FIXTURES/pre-v1.11/expected-post"

diff -rq --exclude='.ark' \
  /tmp/stage5-pre-v1.12 \
  "$FIXTURES/pre-v1.12/expected-post"

diff -rq --exclude='.ark' \
  /tmp/stage5-pre-v1.13 \
  "$FIXTURES/pre-v1.13/expected-post"
```

**Expected:** No diff output (byte-exact match for all three fixtures).

### Step E: Verify .ark/ state for each fixture

```bash
for FIX in pre-v1.11 pre-v1.12 pre-v1.13; do
  echo "=== /tmp/stage5-$FIX/.ark/ ==="
  cat /tmp/stage5-$FIX/.ark/migrations-applied.jsonl
  echo "plugin-version: $(cat /tmp/stage5-$FIX/.ark/plugin-version)"
  ls /tmp/stage5-$FIX/.ark/backups/ 2>/dev/null && echo "(no backups — correct)" || true
done
```

**Expected:**
- `migrations-applied.jsonl` has a `"phase": "convergence"` entry with `"ops_ran" > 0`.
- `plugin-version` matches `$SKILLS_ROOT/VERSION` (currently `1.13.0`).
- No `.bak` files in `backups/` (no drift was seeded in these fixtures).

---

## Part 3: Idempotency Proof — healthy-current Fixture

Run the engine twice on the healthy-current fixture and confirm zero writes on
the second run:

```bash
cp -r "$FIXTURES/healthy-current" /tmp/stage5-healthy
rm -rf /tmp/stage5-healthy/expected-post

# First run (should be clean immediately since fixture is already converged)
python3 "$MIGRATE" \
  --project-root /tmp/stage5-healthy \
  --skills-root "$SKILLS_ROOT" \
  --force

# Second run (MUST be clean)
python3 "$MIGRATE" \
  --project-root /tmp/stage5-healthy \
  --skills-root "$SKILLS_ROOT" \
  --force
```

**Expected for both runs:** `clean — nothing to do (all ops idempotent, no pending migrations)`

Verify no backups written:
```bash
ls /tmp/stage5-healthy/.ark/backups/
```
**Expected:** Empty or no `.bak` files.

---

## Part 4: Drift Detection Proof — drift-inside-markers Fixture

```bash
cp -r "$FIXTURES/drift-inside-markers" /tmp/stage5-drift
rm -rf /tmp/stage5-drift/expected-post

python3 "$MIGRATE" \
  --project-root /tmp/stage5-drift \
  --skills-root "$SKILLS_ROOT" \
  --force
```

**Expected:** Summary shows `drift-overwritten > 0`. Backup files exist in `.ark/backups/`.

Verify backup provenance sidecars:
```bash
ls /tmp/stage5-drift/.ark/backups/*.meta.json
cat /tmp/stage5-drift/.ark/backups/*.meta.json
```

**Expected:** Each `.bak` has a `.bak.meta.json` with `op`, `region_id`, `run_id`,
`pre_hash`, `reason` fields.

---

## Part 5: Evidence Capture

Record the following in the session log:

1. **Fixture authenticity sign-off** — note which tags existed / which were visually inspected.
2. **pre-v1.11 convergence output** — paste the engine stdout.
3. **pre-v1.12 convergence output** — paste the engine stdout.
4. **pre-v1.13 convergence output** — paste the engine stdout.
5. **healthy-current idempotency proof** — paste both runs' stdout.
6. **drift-inside-markers proof** — paste stdout + `ls .ark/backups/` output.
7. **Any deviations** — note here; open a fix commit if any.

```
## Observed in Stage-5 self-test

Date: YYYY-MM-DD
Executor: <name>

### Fixture authenticity check
- pre-v1.11/CLAUDE.md: [inspected / diff against tag <tag>] — OK / DEVIATION: <note>
- pre-v1.12/CLAUDE.md: [inspected / diff against tag <tag>] — OK / DEVIATION: <note>
- pre-v1.13/CLAUDE.md: [inspected / diff against tag <tag>] — OK / DEVIATION: <note>

### Convergence results
- pre-v1.11: [PASS / FAIL] — <paste stdout>
- pre-v1.12: [PASS / FAIL] — <paste stdout>
- pre-v1.13: [PASS / FAIL] — <paste stdout>

### Idempotency proof (healthy-current)
- Run 1: [clean / not-clean]
- Run 2: [clean / not-clean]
- No backups: [yes / no]

### Drift detection proof
- drift-overwritten count: N
- Backup files: [list]
- Meta sidecars present: [yes / no]

### Overall verdict: PASS / FAIL
```

---

## Blockers (any → must fix before shipping)

- Any test failure → fix in a dedicated commit, loop back to Part 0.
- Any fixture post-state deviation → fix fixture or engine, re-run.
- Any `.ark/backups/*.bak` written on non-drift fixture → engine bug, fix.
- Any refusal-mode behavior not matching spec → fix.
- Second run not clean → P1-2 regression, fix.

---

*Runbook version: Step 6 — ark-update framework v1.14.0 pre-release*
