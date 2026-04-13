# /ark-context-warmup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `/ark-context-warmup` skill that runs as step 0 of every `/ark-workflow` chain, fetching recent and relevant project context from NotebookLM + vault + TaskNotes backends and emitting one unified Context Brief to the session.

**Architecture:** Standalone skill at `skills/ark-context-warmup/`. Two-lane fan-out (NotebookLM parallel, vault-local serialized). Each backend declares a machine-readable `warmup_contract` YAML block in its own SKILL.md — warm-up reads contracts, no inline reimplementation. `/ark-workflow`'s continuity frontmatter is extended with five new fields (`chain_id`, `task_text`, `task_summary`, `task_normalized`, `task_hash`) so the warm-up can do task-aware queries and correctly-keyed caching. This extends the spec's round-3 Prerequisites section by splitting the single `task_summary` role into two fields per D2: `task_summary` is human-display-only, `task_normalized` is the hash input and matching source. Cache file lives inside repo-local `.ark-workflow/` with filename `context-brief-{chain_id}-{task_hash[:8]}.md` — portable across symlinks, repo moves, machine handoff.

**Tech Stack:** Python 3.9+ for helpers (Unicode handling, JSON, hashing). Bash for shell orchestration inside SKILL.md. pytest for Python tests. bats-core for integration tests. YAML for config and contracts. `jq` for JSON parsing in bash contexts.

**Spec reference:** `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md` (commit `cb248e5`).

---

## Decisions Pinned (from spec's Open Questions)

The spec deferred six decisions to `/writing-plans`. They are now pinned below. Every task in this plan references these as authoritative.

### D1 — Task normalization + hashing algorithm

**`task_text`** — verbatim user request, unchanged. Stored in chain frontmatter as YAML block literal (`|`).

**`task_summary`** (human-display) — single-line projection of `task_text`:
- Strip leading/trailing whitespace
- Replace all `\r`, `\n`, `\t`, and runs of spaces with a single space
- Truncate to 120 chars at the last word boundary (whitespace split) before the limit; append `…` if truncated
- Case and punctuation preserved
- Empty `task_text` → empty `task_summary`

**`task_normalized`** (internal, used for hashing and matching) — deterministic projection of `task_text`:
1. Unicode NFC normalization (`unicodedata.normalize('NFC', s)`)
2. ASCII-lowercase using `str.lower()` (not locale-aware `casefold()`; avoids locale drift)
3. Strip all characters except `[a-z0-9 _-]` (replace with space)
4. Collapse whitespace runs to single space
5. Split into tokens by whitespace
6. Remove tokens that are present in `skills/ark-context-warmup/scripts/stopwords.txt` (committed wordlist)
7. Remove tokens of length ≤1
8. Rejoin tokens with single space
9. If result is empty or zero-length after step 8: use the literal string `__empty__`

**`task_hash`** — `sha256(task_normalized.encode('utf-8')).hexdigest()[:16]`.

**Immutability:** `task_hash` is computed once at chain emission by `/ark-workflow`. It is NEVER recomputed mid-chain. If the user edits the task mid-chain, they must re-invoke `/ark-workflow` to get a new `chain_id` and new `task_hash`.

### D2 — `task_summary` vs `task_normalized` role split

Both fields live in the frontmatter. `task_summary` is for human display (preserves case + punctuation). `task_normalized` is for hashing + token-overlap matching (deterministic, stable). Evidence generator uses `task_normalized` tokens for duplicate detection.

### D3 — Evidence confidence calibration (deterministic)

**`Possible duplicate`:**
- `high`: open TaskNote with `component` field exactly matching the task's extracted component (regex: first `[A-Z][a-zA-Z0-9]+` run in `task_summary`, or `None` if absent) AND status ∈ {open, in-progress, planned}
- `medium`: ≥60% token-overlap (shared tokens / tokens-in-smaller-set) between `task_normalized` and the open task's title-normalized
- `low`: 40-59% overlap with no structural match → **DROPPED** (below noise floor, not emitted)

**`Possible prior rejection`:**
- `medium`: trigger phrase ∈ {"decided against", "tried and failed", "rejected", "won't do", "abandoned"} within a 30-token window of at least 2 keyword tokens from `task_normalized`
- Anything less → **DROPPED**

**`Possible in-flight collision`:**
- `high`: another open TaskNote with `component` field matching AND status=in-progress
- `medium`: shared session tag resolvable via current epic's backlinks (obsidian backlinks on the current epic returns the other task)
- No `low` tier (too noisy)

**`work-type` alone NEVER produces high confidence.** `work-type` is categorical but too broad (e.g., "bug", "feature") to be a strong duplicate signal.

**`Stale context`** and **`Degraded coverage`** are informational (no confidence level); they always emit when triggered.

### D4 — Obsidian MCP concurrency model

Default: vault-local lane runs **serialized** (wiki-query → ark-tasknotes sequentially). A concurrency probe script (Task 18) runs in CI against a reference Obsidian instance; if the probe passes consistently across 20 runs, a follow-up plan may relax to parallel. For now: serialized is the only supported mode.

### D5 — NotebookLM multi-notebook selection

If `.notebooklm/config.json` has >1 notebook AND no `default_for_warmup` field → **NotebookLM lane is skipped entirely.** Log exact message: `"Multi-notebook NotebookLM config without default_for_warmup — lane skipped. Add 'default_for_warmup' to .notebooklm/config.json pointing at the notebook key to use."` Silent first-pick is explicitly ruled out.

If exactly one notebook: use it. If zero notebooks: lane is skipped (no backend available).

### D6 — Precondition script calling convention

`warmup_contract.commands[*].preconditions[*].script` paths are relative to the backend skill's directory. Scripts are invoked as:

- **Invocation:** executable shell file, invoked via `bash <script_path>` (no `./` prefix; bash invocation avoids permission-bit issues)
- **Environment variables (all strings, all set before invocation):**
  - `WARMUP_TASK_TEXT` — raw task_text
  - `WARMUP_TASK_NORMALIZED` — task_normalized
  - `WARMUP_TASK_HASH` — task_hash
  - `WARMUP_TASK_SUMMARY` — task_summary
  - `WARMUP_SCENARIO` — scenario from chain frontmatter
  - `WARMUP_CHAIN_ID` — chain_id
  - `WARMUP_VAULT_PATH` — absolute vault path from CLAUDE.md
  - `WARMUP_PROJECT_DOCS_PATH` — absolute project_docs_path
  - `WARMUP_PROJECT_NAME` — project_name from CLAUDE.md (used by NotebookLM prompt template)
  - `WARMUP_TASK_PREFIX` — task_prefix (e.g., `Arkskill-`)
  - `WARMUP_TASKNOTES_PATH` — absolute tasknotes_path
- **Stdin:** empty
- **Stdout:** ignored (not captured, not logged)
- **Stderr:** captured and logged verbatim if exit code is non-zero
- **Timeout:** 5 seconds (hard wall-clock). SIGTERM on timeout; if still running after 2 more seconds, SIGKILL. On timeout: treated as non-zero exit.
- **Exit code semantics:** `0` = precondition met, run the command. Non-zero = precondition not met, skip the command.

---

## File Structure

### New files

```
skills/ark-context-warmup/
├── SKILL.md                              # Main skill entry point
├── scripts/
│   ├── stopwords.txt                     # Committed wordlist for task_normalized
│   ├── warmup-helpers.py                 # Python helper module (pure logic)
│   ├── contract.py                       # warmup_contract YAML parser + validator
│   ├── executor.py                       # runtime engine: inputs, preconditions, shell, JSONPath
│   ├── availability.py                   # backend availability probe (D5 rules)
│   ├── evidence.py                       # deterministic evidence-candidate generator (D3)
│   ├── synthesize.py                     # brief assembly + atomic cache write + pruning
│   ├── test_warmup_helpers.py            # pytest tests for all of the above
│   ├── integration/
│   │   ├── test_availability.bats        # Integration: availability probe
│   │   ├── test_cache.bats               # Integration: cache identity + atomic write
│   │   ├── test_contract_missing.bats    # Integration: missing warmup_contract
│   │   └── test_concurrent.bats          # Integration: concurrent warmup runs
│   ├── mcp_concurrency_probe.sh          # Runs periodically in CI to validate D4
│   └── smoke-test.md                     # Manual release checklist
└── fixtures/
    ├── duplicate-component-hit.yaml      # Evidence regression fixtures
    ├── duplicate-token-overlap-medium.yaml
    ├── duplicate-token-overlap-low-noise.yaml
    ├── duplicate-closed-ignored.yaml
    ├── prior-rejection-structured.yaml
    ├── prior-rejection-false-positive.yaml
    ├── in-flight-collision-component.yaml
    ├── stale-context.yaml
    └── degraded-coverage.yaml
```

### Modified files

- `skills/ark-workflow/SKILL.md` — Step 6.5 frontmatter template extended
- `skills/notebooklm-vault/SKILL.md` — add `warmup_contract` block + precondition script
- `skills/notebooklm-vault/scripts/session_shape_check.sh` — new precondition script
- `skills/wiki-query/SKILL.md` — add `warmup_contract` block
- `skills/ark-tasknotes/SKILL.md` — add `warmup_contract` block
- `skills/ark-workflow/chains/greenfield.md` — prepend step 0, renumber
- `skills/ark-workflow/chains/bugfix.md` — prepend step 0, renumber
- `skills/ark-workflow/chains/ship.md` — prepend step 0, renumber
- `skills/ark-workflow/chains/knowledge-capture.md` — prepend step 0, renumber
- `skills/ark-workflow/chains/hygiene.md` — prepend step 0, renumber
- `skills/ark-workflow/chains/migration.md` — prepend step 0, renumber, shift `handoff_marker: after-step-4` → `after-step-5`
- `skills/ark-workflow/chains/performance.md` — prepend step 0, renumber, shift `handoff_marker: after-step-5` → `after-step-6`
- `.claude-plugin/marketplace.json` — register skill
- `.claude-plugin/plugin.json` — register skill
- `CLAUDE.md` — add warm-up to Available Skills list
- `VERSION` — bump
- `CHANGELOG.md` — add entry
- `.github/workflows/ci.yml` — add chain-integrity + contract-extension CI checks (if file exists; otherwise create it)

---

## Phase 1 — Prerequisite: `/ark-workflow` Continuity Contract Extension

### Task 1: Create the stopwords wordlist

**Files:**
- Create: `skills/ark-context-warmup/scripts/stopwords.txt`

- [ ] **Step 1: Create the stopwords file**

Create `skills/ark-context-warmup/scripts/stopwords.txt` with the following content (one word per line, newline-terminated, alphabetized):

```
a
about
add
all
also
an
and
any
are
as
at
be
but
by
can
could
do
does
done
fix
for
from
get
had
has
have
how
i
if
in
into
is
it
make
makes
my
need
needs
not
of
on
or
our
should
so
some
that
the
their
them
then
there
these
they
this
those
to
update
us
was
we
were
what
when
where
which
who
why
will
with
would
you
your
```

- [ ] **Step 2: Commit**

```bash
git add skills/ark-context-warmup/scripts/stopwords.txt
git commit -m "feat(warmup): add stopwords wordlist for task normalization"
```

---

### Task 2: Create `warmup-helpers.py` with task normalization + hashing

**Files:**
- Create: `skills/ark-context-warmup/scripts/warmup-helpers.py`
- Create: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing test**

Create `skills/ark-context-warmup/scripts/test_warmup_helpers.py`:

```python
"""Tests for warmup-helpers.py - Phase 1 helpers."""
import importlib.util
import hashlib
from pathlib import Path

HELPERS_PATH = Path(__file__).parent / "warmup-helpers.py"
spec = importlib.util.spec_from_file_location("warmup_helpers", HELPERS_PATH)
wh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wh)


class TestTaskNormalize:
    def test_simple(self):
        # "Add" and "to" are in the stopwords list; "API" survives as "api".
        assert wh.task_normalize("Add rate limiting to API") == "rate limiting api"

    def test_empty_string(self):
        assert wh.task_normalize("") == "__empty__"

    def test_whitespace_only(self):
        assert wh.task_normalize("   \t\n  ") == "__empty__"

    def test_all_stopwords(self):
        assert wh.task_normalize("and the of") == "__empty__"

    def test_single_letter_and_stopwords_removed(self):
        # Single letters filtered by len>1 rule; "add" is a stopword.
        assert wh.task_normalize("x y z add feature") == "feature"

    def test_punctuation_stripped(self):
        assert wh.task_normalize("Fix: users' auth!") == "users auth"

    def test_unicode_nfc(self):
        # 'é' as single codepoint U+00E9
        single = wh.task_normalize("caf\u00e9 migration")
        # 'é' as 'e' + combining acute U+0301 — NFC should merge
        decomposed = wh.task_normalize("cafe\u0301 migration")
        assert single == decomposed

    def test_case_insensitive(self):
        assert wh.task_normalize("ADD FEATURE") == wh.task_normalize("add feature")

    def test_preserves_hyphens_and_underscores(self):
        assert wh.task_normalize("fix user-auth_flow") == "user-auth_flow"

    def test_drops_non_bmp(self):
        # Emoji should be stripped, word kept
        assert wh.task_normalize("🎉 migrate database") == "migrate database"


class TestTaskSummary:
    def test_preserves_case_and_punctuation(self):
        assert wh.task_summary("Add Rate Limiting!") == "Add Rate Limiting!"

    def test_collapses_whitespace(self):
        assert wh.task_summary("foo\n\nbar\tbaz") == "foo bar baz"

    def test_truncates_at_word_boundary(self):
        long = "word " * 50  # 250 chars
        result = wh.task_summary(long)
        assert len(result) <= 121  # 120 + ellipsis
        assert result.endswith("…")
        assert " " not in result[-3:-1]  # truncated at whitespace, not mid-word

    def test_short_unchanged(self):
        assert wh.task_summary("short task") == "short task"

    def test_empty(self):
        assert wh.task_summary("") == ""


class TestTaskHash:
    def test_determinism(self):
        assert wh.task_hash("hello world") == wh.task_hash("hello world")

    def test_different_inputs_different_hashes(self):
        assert wh.task_hash("foo") != wh.task_hash("bar")

    def test_length_is_16(self):
        assert len(wh.task_hash("anything")) == 16

    def test_hash_is_hex(self):
        h = wh.task_hash("test")
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_operates_on_already_normalized(self):
        # task_hash assumes its input is already normalized
        h = wh.task_hash("add rate limiting")
        expected = hashlib.sha256("add rate limiting".encode("utf-8")).hexdigest()[:16]
        assert h == expected

    def test_empty_sentinel_hashed(self):
        assert wh.task_hash("__empty__") == hashlib.sha256(b"__empty__").hexdigest()[:16]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py -v`
Expected: FAIL with `FileNotFoundError` or `ModuleNotFoundError` on `warmup-helpers.py`.

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/warmup-helpers.py`:

```python
"""Pure helpers for /ark-context-warmup. No I/O except reading stopwords.txt."""
import hashlib
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

STOPWORDS_PATH = Path(__file__).parent / "stopwords.txt"


@lru_cache(maxsize=1)
def _load_stopwords() -> frozenset:
    with open(STOPWORDS_PATH, "r", encoding="utf-8") as f:
        return frozenset(line.strip() for line in f if line.strip())


def task_normalize(task_text: str) -> str:
    """Deterministic projection of task_text used for hashing and matching."""
    if not task_text:
        return "__empty__"
    s = unicodedata.normalize("NFC", task_text)
    s = s.lower()
    s = re.sub(r"[^a-z0-9 _-]", " ", s)
    tokens = s.split()
    stopwords = _load_stopwords()
    tokens = [t for t in tokens if len(t) > 1 and t not in stopwords]
    result = " ".join(tokens)
    return result if result else "__empty__"


def task_summary(task_text: str, limit: int = 120) -> str:
    """Human-readable single-line projection, case + punctuation preserved."""
    if not task_text:
        return ""
    s = re.sub(r"\s+", " ", task_text).strip()
    if len(s) <= limit:
        return s
    truncated = s[:limit]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "…"


def task_hash(task_normalized: str) -> str:
    """Stable 16-hex-char hash over an already-normalized string."""
    return hashlib.sha256(task_normalized.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py -v`
Expected: 17 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/warmup-helpers.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add task normalization + hashing helpers"
```

---

### Task 3: Add `chain_id` generator

**Files:**
- Modify: `skills/ark-context-warmup/scripts/warmup-helpers.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing test**

Append to `test_warmup_helpers.py`:

```python
import re


class TestChainId:
    def test_is_ulid_like_format(self):
        cid = wh.chain_id_new()
        # ULID: 26 characters, Crockford base32
        assert re.match(r"^[0-9A-HJKMNP-TV-Z]{26}$", cid)

    def test_two_calls_produce_different_ids(self):
        assert wh.chain_id_new() != wh.chain_id_new()

    def test_timestamp_prefix_non_decreasing_across_ms(self):
        # ULID timestamp prefix (first 10 chars) is non-decreasing across calls
        # separated by ≥1 ms. Within the same ms, the random tail may not sort — that
        # is acceptable for our use (chain_id is a coarse ordering, not a sequence).
        import time as _t
        cids = []
        for _ in range(10):
            cids.append(wh.chain_id_new())
            _t.sleep(0.002)  # ensure >= 1 ms between calls
        prefixes = [c[:10] for c in cids]
        assert prefixes == sorted(prefixes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestChainId -v`
Expected: FAIL with `AttributeError: module has no attribute 'chain_id_new'`.

- [ ] **Step 3: Write the implementation**

Append to `warmup-helpers.py`:

```python
import time
import secrets

# Crockford base32 alphabet (excludes I, L, O, U)
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(n: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def chain_id_new() -> str:
    """Generate a ULID. 48-bit timestamp (ms) + 80-bit randomness, Crockford base32."""
    timestamp_ms = int(time.time() * 1000)
    random_bits = secrets.randbits(80)
    ts_part = _encode_crockford(timestamp_ms, 10)
    rand_part = _encode_crockford(random_bits, 16)
    return ts_part + rand_part
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestChainId -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/warmup-helpers.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add ULID chain_id generator"
```

---

### Task 4: Add CLI wrapper for helpers (so bash can call them)

**Files:**
- Modify: `skills/ark-context-warmup/scripts/warmup-helpers.py`

- [ ] **Step 1: Write the failing test**

Append to `test_warmup_helpers.py`:

```python
import subprocess


class TestCli:
    def test_cli_normalize(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "normalize", "Add rate limiting to API"],
            capture_output=True, text=True, check=True,
        )
        assert r.stdout.strip() == "add rate limiting api"

    def test_cli_summary(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "summary", "Fix Auth!"],
            capture_output=True, text=True, check=True,
        )
        assert r.stdout.strip() == "Fix Auth!"

    def test_cli_hash(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "hash", "add rate limiting"],
            capture_output=True, text=True, check=True,
        )
        assert len(r.stdout.strip()) == 16

    def test_cli_chain_id(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "chain-id"],
            capture_output=True, text=True, check=True,
        )
        assert len(r.stdout.strip()) == 26

    def test_cli_unknown_command(self):
        r = subprocess.run(
            ["python3", str(HELPERS_PATH), "bogus"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "unknown command" in r.stderr.lower()
```

- [ ] **Step 2: Run to verify fail**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestCli -v`
Expected: FAIL (subprocess returns non-zero; file has no main block).

- [ ] **Step 3: Implement CLI dispatch**

Append to `warmup-helpers.py`:

```python
def _main(argv):
    import sys
    if len(argv) < 2:
        sys.stderr.write("usage: warmup-helpers.py <command> [args...]\n")
        return 2
    cmd = argv[1]
    if cmd == "normalize":
        if len(argv) < 3:
            sys.stderr.write("usage: normalize <task_text>\n")
            return 2
        print(task_normalize(argv[2]))
        return 0
    if cmd == "summary":
        if len(argv) < 3:
            sys.stderr.write("usage: summary <task_text>\n")
            return 2
        print(task_summary(argv[2]))
        return 0
    if cmd == "hash":
        if len(argv) < 3:
            sys.stderr.write("usage: hash <task_normalized>\n")
            return 2
        print(task_hash(argv[2]))
        return 0
    if cmd == "chain-id":
        print(chain_id_new())
        return 0
    sys.stderr.write(f"unknown command: {cmd}\n")
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv))
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py -v`
Expected: all tests pass (20+ tests total so far).

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/warmup-helpers.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add CLI dispatch for helper functions"
```

---

### Task 5: Extend `/ark-workflow` Step 6.5 frontmatter template

**Files:**
- Modify: `skills/ark-workflow/SKILL.md:196-215`

- [ ] **Step 1: Read the current Step 6.5 section**

Run: `sed -n '196,215p' skills/ark-workflow/SKILL.md`
Expected: shows current frontmatter without the four new fields.

- [ ] **Step 2: Edit the frontmatter template**

Replace the existing Step 6.5 section with this content. Use the Edit tool on `skills/ark-workflow/SKILL.md`.

Find:

```
### Step 6.5: Activate Continuity
- Create TodoWrite tasks for each step in the resolved chain
- Write `.ark-workflow/current-chain.md` at project root with this frontmatter:

  ---
  scenario: {scenario}
  weight: {weight}
  batch: false
  created: {ISO-8601 timestamp}
  handoff_marker: null
  handoff_instructions: null
  ---
  # Current Chain: {scenario}-{weight}
  ## Steps
  [numbered checklist of chain steps, each as `- [ ]`]
  ## Notes
```

Replace with:

```
### Step 6.5: Activate Continuity
- Create TodoWrite tasks for each step in the resolved chain
- Compute task fields for `/ark-context-warmup` (step 0 of every chain). `/ark-workflow` needs the same `ARK_SKILLS_ROOT` resolution as the warm-up skill — see `/ark-context-warmup` SKILL.md's Project Discovery section for the canonical snippet. Reuse it here:
  ```bash
  # Resolve ARK_SKILLS_ROOT (see /ark-context-warmup/SKILL.md for full logic)
  ARK_SKILLS_ROOT="${CLAUDE_PLUGIN_DIR:-$(find ~/.claude/plugins -maxdepth 6 -type d -name ark-skills 2>/dev/null | head -1)}"
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
  task_summary: {TASK_SUMMARY}
  task_normalized: {TASK_NORMALIZED}
  task_hash: {TASK_HASH}
  handoff_marker: null
  handoff_instructions: null
  ---
  # Current Chain: {scenario}-{weight}
  ## Steps
  [numbered checklist of chain steps, each as `- [ ]`]
  ## Notes
```

- [ ] **Step 3: Verify the edit**

Run: `sed -n '196,230p' skills/ark-workflow/SKILL.md`
Expected: shows the extended frontmatter with `chain_id`, `task_text`, `task_summary`, `task_normalized`, `task_hash`.

- [ ] **Step 4: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "feat(ark-workflow): extend current-chain.md frontmatter for warmup"
```

---

## Phase 2 — Prerequisite: Backend `warmup_contract` Blocks

### Task 6: Add `session_shape_check.sh` precondition script for notebooklm-vault

**Files:**
- Create: `skills/notebooklm-vault/scripts/session_shape_check.sh`

- [ ] **Step 1: Create the script**

Create `skills/notebooklm-vault/scripts/session_shape_check.sh`:

```bash
#!/usr/bin/env bash
# Precondition for notebooklm-vault's session-continue command.
# Exit 0: latest session log exists, is <7 days old (by file mtime), has "## Next Steps"
#         heading, and has a non-empty "epic:" frontmatter field (link resolution is done
#         later by notebooklm-vault's session-continue logic itself, not by this probe).
# Exit 1: any above check fails → warm-up should use bootstrap instead.
#
# Reads env vars (set by warm-up per D6):
#   WARMUP_PROJECT_DOCS_PATH — absolute path to project docs (parent of Session-Logs/)

set -uo pipefail

if [ -z "${WARMUP_PROJECT_DOCS_PATH:-}" ]; then
    echo "session_shape_check: WARMUP_PROJECT_DOCS_PATH not set" >&2
    exit 1
fi

LOGS_DIR="$WARMUP_PROJECT_DOCS_PATH/Session-Logs"
if [ ! -d "$LOGS_DIR" ]; then
    echo "session_shape_check: no Session-Logs directory at $LOGS_DIR" >&2
    exit 1
fi

# Find highest-numbered S*.md (per notebooklm-vault convention)
LATEST=$(find "$LOGS_DIR" -maxdepth 1 -type f -name 'S*.md' 2>/dev/null \
    | awk -F/ '{print $NF}' \
    | sort -V \
    | tail -1)

if [ -z "$LATEST" ]; then
    echo "session_shape_check: no session logs found" >&2
    exit 1
fi

LATEST_PATH="$LOGS_DIR/$LATEST"

# Age check: <7 days old
if [ "$(date +%s)" -gt 0 ]; then
    AGE_SECONDS=$(( $(date +%s) - $(stat -f %m "$LATEST_PATH" 2>/dev/null || stat -c %Y "$LATEST_PATH" 2>/dev/null) ))
    if [ "$AGE_SECONDS" -gt $((7 * 86400)) ]; then
        echo "session_shape_check: latest log $LATEST is older than 7 days (${AGE_SECONDS}s)" >&2
        exit 1
    fi
fi

# Shape check: has "Next Steps" heading
if ! grep -qE '^##[[:space:]]+Next Steps' "$LATEST_PATH"; then
    echo "session_shape_check: $LATEST missing '## Next Steps' heading" >&2
    exit 1
fi

# Shape check: has epic frontmatter field with non-empty value
# Minimal YAML-frontmatter parse: first --- ... --- block, look for "epic:" line
EPIC_VALUE=$(awk '
    /^---$/ { if (in_fm) exit; in_fm=1; next }
    in_fm && /^epic:/ { sub(/^epic:[[:space:]]*/, ""); print; exit }
' "$LATEST_PATH" | tr -d '"' | tr -d "'" | xargs)

if [ -z "$EPIC_VALUE" ]; then
    echo "session_shape_check: $LATEST has no 'epic:' frontmatter field" >&2
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make it executable + syntax check**

```bash
chmod +x skills/notebooklm-vault/scripts/session_shape_check.sh
bash -n skills/notebooklm-vault/scripts/session_shape_check.sh
```

Expected: no output (syntax OK).

- [ ] **Step 3: Smoke test against a fake layout**

```bash
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/Session-Logs"
cat > "$TMPDIR/Session-Logs/S001-test.md" <<'EOF'
---
epic: TEST-001-sample
---
## Next Steps
- Continue work
EOF
WARMUP_PROJECT_DOCS_PATH="$TMPDIR" bash skills/notebooklm-vault/scripts/session_shape_check.sh
echo "exit=$?"
rm -rf "$TMPDIR"
```

Expected: `exit=0`.

- [ ] **Step 4: Negative smoke test (missing epic)**

```bash
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/Session-Logs"
cat > "$TMPDIR/Session-Logs/S001-test.md" <<'EOF'
## Next Steps
- Continue work
EOF
WARMUP_PROJECT_DOCS_PATH="$TMPDIR" bash skills/notebooklm-vault/scripts/session_shape_check.sh
echo "exit=$?"
rm -rf "$TMPDIR"
```

Expected: `exit=1` (stderr mentions missing epic).

- [ ] **Step 5: Commit**

```bash
git add skills/notebooklm-vault/scripts/session_shape_check.sh
git commit -m "feat(notebooklm-vault): add session-continue shape precondition script"
```

---

### Task 7: Add `warmup_contract` block to notebooklm-vault/SKILL.md

**Files:**
- Modify: `skills/notebooklm-vault/SKILL.md` (append new section before "## Important Notes" or at end)

- [ ] **Step 1: Find insertion point**

Run: `grep -n '^## ' skills/notebooklm-vault/SKILL.md | tail -5`

Identify the last top-level section (likely `## Important Notes`). The `warmup_contract` section will be appended before it, as its own `## Warmup Contract` section.

- [ ] **Step 2: Add the warmup_contract section**

Use the Edit tool to insert this section before `## Important Notes` (if it exists) or at end of file:

```markdown
## Warmup Contract

Machine-readable subcontract consumed by `/ark-context-warmup`. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`. Calling convention: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` D6.

```yaml
warmup_contract:
  version: 1
  commands:
    - id: session-continue
      shell: 'notebooklm ask "{{prompt}}" --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id:
          from: config
          config_path: '.notebooklm/config.json'
          config_lookup_order: ['vault_root/.notebooklm/config.json', '.notebooklm/config.json']
          # Per D5 (plan §Decisions Pinned): if config.notebooks has exactly one entry,
          # use it. If it has >1 entry, config.default_for_warmup MUST be set —
          # otherwise the availability probe skips the lane with a remediation hint.
          # No silent fallback to "main". The executor resolves this via the lookup
          # rule, not a json_path fallback syntax.
          lookup: single_or_default_for_warmup
          required: true
        prompt:
          from: template
          template_id: session_continue_prompt
      preconditions:
        - id: recent_session_with_shape
          script: scripts/session_shape_check.sh
          description: 'Exits 0 if latest session log <7 days old AND has Next Steps section AND resolvable epic link'
      output:
        format: json
        extract:
          where_we_left_off: '$.answer.sections.where_we_left_off'
          epic_progress: '$.answer.sections.epic_progress'
          immediate_next_steps: '$.answer.sections.immediate_next_steps'
          critical_context: '$.answer.sections.critical_context'
          citations: '$.citations'
        required_fields: [where_we_left_off, immediate_next_steps]
    - id: bootstrap
      shell: 'notebooklm ask "{{prompt}}" --notebook {{notebook_id}} --json --timeout 60'
      inputs:
        notebook_id:
          from: config
          config_path: '.notebooklm/config.json'
          config_lookup_order: ['vault_root/.notebooklm/config.json', '.notebooklm/config.json']
          # Per D5 (plan §Decisions Pinned): if config.notebooks has exactly one entry,
          # use it. If it has >1 entry, config.default_for_warmup MUST be set —
          # otherwise the availability probe skips the lane with a remediation hint.
          # No silent fallback to "main". The executor resolves this via the lookup
          # rule, not a json_path fallback syntax.
          lookup: single_or_default_for_warmup
          required: true
        prompt:
          from: template
          template_id: bootstrap_prompt
      output:
        format: json
        extract:
          recent_sessions: '$.answer.sections.recent_sessions'
          current_state: '$.answer.sections.current_state'
          open_issues: '$.answer.sections.open_issues'
          citations: '$.citations'
        required_fields: [recent_sessions, current_state]
  prompt_templates:
    session_continue_prompt: |
      What sessions are related to: {WARMUP_TASK_TEXT}? Include session numbers,
      outcomes, and any gotchas. Structure the answer with these exact headings:
      "Where We Left Off", "Epic Progress", "Immediate Next Steps", "Critical Context".
    bootstrap_prompt: |
      For the {WARMUP_PROJECT_NAME} project, provide: (1) the 5 most recent session
      logs with session number, date, objective, key outcomes, unresolved items;
      (2) the current project state — what is built, what is planned; (3) the top
      open issues, ongoing experiments, or blocked work items. Structure the answer
      with these exact headings: "Recent Sessions", "Current State", "Open Issues".
  selection_rules:
    # Per spec decision D5: no silent first-pick on multi-notebook configs.
    - rule: single_notebook
      when: 'config.notebooks has exactly one entry'
      action: 'use that notebook'
    - rule: explicit_default
      when: 'config.notebooks has >1 entry AND config.default_for_warmup is set'
      action: 'use config.notebooks[config.default_for_warmup]'
    - rule: ambiguous_multi_notebook
      when: 'config.notebooks has >1 entry AND config.default_for_warmup is NOT set'
      action: 'skip entire lane; log: "Multi-notebook NotebookLM config without default_for_warmup — lane skipped. Add default_for_warmup to .notebooklm/config.json pointing at the notebook key to use."'
```

- [ ] **Step 3: Verify YAML validity**

```bash
python3 -c "import yaml; d = yaml.safe_load(open('skills/notebooklm-vault/SKILL.md').read().split('\`\`\`yaml')[1].split('\`\`\`')[0]); assert 'warmup_contract' in d; print('OK:', list(d['warmup_contract'].keys()))"
```

Expected: `OK: ['version', 'commands', 'prompt_templates', 'selection_rules']`.

- [ ] **Step 4: Commit**

```bash
git add skills/notebooklm-vault/SKILL.md
git commit -m "feat(notebooklm-vault): declare warmup_contract for /ark-context-warmup"
```

---

### Task 8: Add `warmup_contract` block to wiki-query/SKILL.md

**Files:**
- Modify: `skills/wiki-query/SKILL.md`

- [ ] **Step 1: Add the section**

Append to `skills/wiki-query/SKILL.md`:

```markdown
## Warmup Contract

Machine-readable subcontract consumed by `/ark-context-warmup`. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`. Calling convention: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` D6.

Wiki-query already exposes the right behavior as a skill — this contract just tells warm-up which scenario-aware queries to run and how to extract findings. The actual implementation lives in the /wiki-query workflow; warm-up invokes it via the inline command pattern below.

```yaml
warmup_contract:
  version: 1
  commands:
    - id: scenario-query
      # Warm-up invokes wiki-query inline via its T4 scan path (index.md + summaries).
      # For the warm-up's purposes, we only need the top-3 most relevant summaries, not the full T1/T2/T3 routing.
      shell: 'python3 "$ARK_SKILLS_ROOT/skills/wiki-query/scripts/warmup_scan.py" --vault "{{vault_path}}" --query "{{query}}" --top 3 --json'
      inputs:
        vault_path:
          from: env
          env_var: WARMUP_VAULT_PATH
          required: true
        query:
          from: template
          template_id: scenario_query
      output:
        format: json
        extract:
          matches: '$.matches'            # [{title, summary, path}]
          tier_used: '$.tier'             # always "T4" for warmup
        required_fields: [matches]
  prompt_templates:
    scenario_query: |
      ${WARMUP_SCENARIO_QUERY_TEMPLATE}
  scenario_templates:
    # Picked by warm-up based on WARMUP_SCENARIO env var; template substituted into scenario_query above.
    greenfield: 'Has anything like {WARMUP_TASK_TEXT} been built before? Existing components or prior design decisions?'
    bugfix: 'Have we seen bugs related to {WARMUP_TASK_TEXT} before? Known failure modes, incident notes, prior fixes?'
    migration: 'Past migration notes for {WARMUP_TASK_TEXT}? Rollback procedures, prior framework changes?'
    performance: 'Past optimization work on {WARMUP_TASK_TEXT}? Benchmarks, bottleneck analyses?'
    hygiene: 'Related refactors or audits on {WARMUP_TASK_TEXT}? Tech debt notes, prior cleanup?'
    ship: 'Deploy runbooks, rollback steps, prior incidents for {WARMUP_TASK_TEXT}? Environment-specific gotchas?'
    knowledge-capture: 'What vault pages already exist on {WARMUP_TASK_TEXT} topic? Recent session coverage?'
```

- [ ] **Step 2: Verify YAML validity**

```bash
python3 -c "
import yaml
content = open('skills/wiki-query/SKILL.md').read()
block = content.split('\`\`\`yaml')[1].split('\`\`\`')[0]
d = yaml.safe_load(block)
assert 'warmup_contract' in d
assert 'scenario_templates' in d['warmup_contract']
print('OK scenarios:', list(d['warmup_contract']['scenario_templates'].keys()))
"
```

Expected: shows all 7 scenarios.

- [ ] **Step 3: Commit**

```bash
git add skills/wiki-query/SKILL.md
git commit -m "feat(wiki-query): declare warmup_contract with per-scenario templates"
```

---

### Task 9: Add `warmup_scan.py` helper for wiki-query

**Files:**
- Create: `skills/wiki-query/scripts/warmup_scan.py`
- Create: `skills/wiki-query/scripts/test_warmup_scan.py`

- [ ] **Step 1: Write the failing test**

Create `skills/wiki-query/scripts/test_warmup_scan.py`:

```python
"""Tests for warmup_scan.py — T4 index.md scan for warm-up."""
import json
import subprocess
import tempfile
from pathlib import Path

SCAN_PATH = Path(__file__).parent / "warmup_scan.py"


def _make_vault(tmpdir: Path, index_content: str):
    """Write index.md to a temp vault dir."""
    (tmpdir / "index.md").write_text(index_content)


def test_returns_top_matches():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, """# Index
- [[Auth-Migration]] — tags: migration, auth — migration of auth system to new provider
- [[Cache-Layer]] — tags: performance — caching strategy for api
- [[Rate-Limiting]] — tags: api, security — rate limiting implementation notes
""")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "rate limiting api", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["tier"] == "T4"
        assert len(out["matches"]) >= 1
        titles = [m["title"] for m in out["matches"]]
        assert "Rate-Limiting" in titles


def test_no_matches():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, "# Index\n(empty)\n")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "nothing", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["matches"] == []


def test_no_index_file():
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(tmp), "--query", "foo", "--top", "3", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "index.md" in r.stderr.lower()
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/wiki-query/scripts/test_warmup_scan.py -v`
Expected: FAIL (file doesn't exist).

- [ ] **Step 3: Write the implementation**

Create `skills/wiki-query/scripts/warmup_scan.py`:

```python
#!/usr/bin/env python3
"""Minimal T4 scan of a vault's index.md for /ark-context-warmup.

Scores candidate pages by query-token overlap with the index line. Returns top-N as JSON.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _parse_index_line(line: str):
    """Return (title, summary, path) or None if the line is not a match entry."""
    # Expected patterns:
    #   - [[PageName]] — ...summary...
    #   - [[PageName]] — tags: x, y — summary
    m = re.match(r"^\s*[-*]\s*\[\[([^\]]+)\]\]\s*[—-]\s*(.*)$", line)
    if not m:
        return None
    return {"title": m.group(1).strip(), "summary": m.group(2).strip(), "path": m.group(1).strip() + ".md"}


def scan(vault_path: Path, query: str, top_n: int) -> dict:
    index = vault_path / "index.md"
    if not index.exists():
        raise FileNotFoundError(f"no index.md in {vault_path}")
    query_tokens = _tokens(query)
    candidates = []
    for line in index.read_text().splitlines():
        parsed = _parse_index_line(line)
        if not parsed:
            continue
        line_tokens = _tokens(parsed["title"] + " " + parsed["summary"])
        overlap = len(query_tokens & line_tokens)
        if overlap > 0:
            candidates.append((overlap, parsed))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return {"tier": "T4", "matches": [c[1] for c in candidates[:top_n]]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--json", action="store_true", help="emit JSON (default)")
    args = parser.parse_args()
    try:
        result = scan(args.vault, args.query, args.top)
    except FileNotFoundError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/wiki-query/scripts/test_warmup_scan.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/wiki-query/scripts/warmup_scan.py skills/wiki-query/scripts/test_warmup_scan.py
git commit -m "feat(wiki-query): add warmup_scan.py for T4-only /ark-context-warmup use"
```

---

### Task 10: Add `warmup_contract` block to ark-tasknotes/SKILL.md

**Files:**
- Modify: `skills/ark-tasknotes/SKILL.md`
- Create: `skills/ark-tasknotes/scripts/warmup_search.py`
- Create: `skills/ark-tasknotes/scripts/test_warmup_search.py`

- [ ] **Step 1: Write the failing test for warmup_search**

Create `skills/ark-tasknotes/scripts/test_warmup_search.py`:

```python
"""Tests for ark-tasknotes warmup_search.py."""
import json
import subprocess
import tempfile
import textwrap
from pathlib import Path

SCAN_PATH = Path(__file__).parent / "warmup_search.py"


def _write_task(tasks_dir: Path, name: str, frontmatter: dict, body: str = ""):
    (tasks_dir / f"{name}.md").write_text(
        "---\n"
        + "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        + "\n---\n" + body + "\n"
    )


def test_finds_matching_component():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "Auth migration", "status": "in-progress", "component": "auth"})
        _write_task(tp / "Tasks", "TEST-002", {"title": "Cache layer", "status": "open", "component": "cache"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "auth provider change", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        # component-match: "auth" is extracted from task_normalized, so TEST-001 hits
        assert any(m["id"] == "TEST-001" for m in out["matches"])


def test_skips_done_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "Auth migration", "status": "done", "component": "auth"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "auth provider change", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert all(m["status"] != "done" for m in out["matches"])


def test_status_summary_included():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "A", "status": "in-progress", "component": "x"})
        _write_task(tp / "Tasks", "TEST-002", {"title": "B", "status": "open", "component": "y"})
        _write_task(tp / "Tasks", "TEST-003", {"title": "C", "status": "done", "component": "z"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "unrelated", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["status_summary"]["in-progress"] == 1
        assert out["status_summary"]["open"] == 1
        assert out["status_summary"]["done"] == 1
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-tasknotes/scripts/test_warmup_search.py -v`
Expected: FAIL (file doesn't exist).

- [ ] **Step 3: Write the implementation**

Create `skills/ark-tasknotes/scripts/warmup_search.py`:

```python
#!/usr/bin/env python3
"""TaskNotes search + status summary for /ark-context-warmup.

Reads TaskNote markdown files directly from {tasknotes_path}/Tasks/.
Falls back from MCP; the parent skill decides when to invoke this vs MCP.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from collections import Counter


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    result = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def _extract_component(task_normalized: str) -> str:
    """Very conservative component extractor.
    Looks for the first token ≥4 chars — a reasonable proxy for component name.
    Spec D3 says: first '[A-Z][a-zA-Z0-9]+' run in task_summary OR None. But task_normalized
    is already lowercased; so we use its first meaningful token instead.
    """
    for tok in task_normalized.split():
        if len(tok) >= 4:
            return tok
    return ""


def _token_overlap(a: str, b: str) -> float:
    toks_a = set(re.findall(r"[a-z0-9]+", a.lower()))
    toks_b = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not toks_a or not toks_b:
        return 0.0
    shared = toks_a & toks_b
    smaller = min(len(toks_a), len(toks_b))
    return len(shared) / smaller


def search(tasknotes_path: Path, prefix: str, task_normalized: str, scenario: str) -> dict:
    tasks_dir = tasknotes_path / "Tasks"
    results = []
    status_counter = Counter()
    component = _extract_component(task_normalized)
    if not tasks_dir.is_dir():
        return {
            "matches": [],
            "status_summary": dict(status_counter),
            "extracted_component": component,
        }
    for md in tasks_dir.glob(f"{prefix}*.md"):
        fm = _parse_frontmatter(md)
        status = fm.get("status", "unknown")
        status_counter[status] += 1
        if status == "done":
            continue
        # Match heuristics
        matched_field = None
        title_overlap = _token_overlap(task_normalized, fm.get("title", ""))
        if component and fm.get("component", "").lower() == component:
            matched_field = "component"
        elif title_overlap >= 0.60:
            matched_field = f"title_overlap={title_overlap:.2f}"
        if matched_field:
            results.append({
                "id": md.stem,
                "title": fm.get("title", ""),
                "status": status,
                "component": fm.get("component", ""),
                "work-type": fm.get("work-type", ""),
                "matched_field": matched_field,
                "title_overlap": title_overlap,
            })
    return {
        "matches": results,
        "status_summary": dict(status_counter),
        "extracted_component": component,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasknotes", required=True, type=Path)
    parser.add_argument("--prefix", required=True, help="Task prefix including trailing dash, e.g. Arkskill-")
    parser.add_argument("--task-normalized", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out = search(args.tasknotes, args.prefix, args.task_normalized, args.scenario)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-tasknotes/scripts/test_warmup_search.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Append warmup_contract block to ark-tasknotes/SKILL.md**

Append to `skills/ark-tasknotes/SKILL.md`:

```markdown
## Warmup Contract

Machine-readable subcontract consumed by `/ark-context-warmup`. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`. Calling convention: `docs/superpowers/plans/2026-04-12-ark-context-warmup-implementation.md` D6.

```yaml
warmup_contract:
  version: 1
  commands:
    - id: status-and-search
      shell: 'python3 "$ARK_SKILLS_ROOT/skills/ark-tasknotes/scripts/warmup_search.py" --tasknotes "{{tasknotes_path}}" --prefix "{{task_prefix}}" --task-normalized "{{task_normalized}}" --scenario "{{scenario}}" --json'
      inputs:
        tasknotes_path:
          from: env
          env_var: WARMUP_TASKNOTES_PATH
          required: true
        task_prefix:
          from: env
          env_var: WARMUP_TASK_PREFIX
          required: true
        task_normalized:
          from: env
          env_var: WARMUP_TASK_NORMALIZED
          required: true
        scenario:
          from: env
          env_var: WARMUP_SCENARIO
          required: true
      output:
        format: json
        extract:
          matches: '$.matches'
          status_summary: '$.status_summary'
          extracted_component: '$.extracted_component'
        required_fields: [matches, status_summary]
```

- [ ] **Step 6: Verify YAML validity**

```bash
python3 -c "
import yaml
content = open('skills/ark-tasknotes/SKILL.md').read()
block = content.split('\`\`\`yaml')[-2].split('\`\`\`')[0] if '\`\`\`yaml' in content else ''
# Find the warmup_contract block specifically
for block in content.split('\`\`\`yaml')[1:]:
    b = block.split('\`\`\`')[0]
    if 'warmup_contract' in b:
        d = yaml.safe_load(b)
        assert 'warmup_contract' in d
        print('OK:', list(d['warmup_contract'].keys()))
        break
"
```

Expected: `OK: ['version', 'commands']`.

- [ ] **Step 7: Commit**

```bash
git add skills/ark-tasknotes/SKILL.md skills/ark-tasknotes/scripts/warmup_search.py skills/ark-tasknotes/scripts/test_warmup_search.py
git commit -m "feat(ark-tasknotes): declare warmup_contract + warmup_search helper"
```

---

## Phase 3 — Warm-Up Skill Scaffolding

### Task 11: Create warm-up skill directory + contract parser

**Files:**
- Create: `skills/ark-context-warmup/scripts/contract.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py` (extend for contract tests)

- [ ] **Step 1: Write the failing test**

Append to `skills/ark-context-warmup/scripts/test_warmup_helpers.py`:

```python
import importlib.util as _ilu
from pathlib import Path as _P

_CONTRACT_PATH = _P(__file__).parent / "contract.py"
_spec_c = _ilu.spec_from_file_location("contract", _CONTRACT_PATH)
contract = _ilu.module_from_spec(_spec_c)
_spec_c.loader.exec_module(contract)


class TestContractParser:
    SAMPLE_SKILL_MD = """\
# Sample

Some content.

## Warmup Contract

```yaml
warmup_contract:
  version: 1
  commands:
    - id: cmd-a
      shell: 'echo {{foo}}'
      inputs:
        foo:
          from: env
          env_var: FOO
          required: true
      output:
        format: json
        extract:
          result: '$.result'
        required_fields: [result]
```
"""

    def test_extracts_contract(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(self.SAMPLE_SKILL_MD)
        c = contract.load_contract(skill_md)
        assert c is not None
        assert c["version"] == 1
        assert c["commands"][0]["id"] == "cmd-a"

    def test_missing_contract_returns_none(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Skill with no contract\n")
        assert contract.load_contract(skill_md) is None

    def test_malformed_yaml_returns_none(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("## Warmup Contract\n\n```yaml\nnot: valid: yaml\n```\n")
        assert contract.load_contract(skill_md) is None

    def test_validates_required_shell(self, tmp_path):
        bad = """## Warmup Contract

```yaml
warmup_contract:
  version: 1
  commands:
    - id: no-shell
      inputs: {}
      output:
        format: json
        extract: {}
        required_fields: []
```
"""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(bad)
        assert contract.load_contract(skill_md) is None
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestContractParser -v`
Expected: FAIL (`contract.py` not found).

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/contract.py`:

```python
"""Parse and validate warmup_contract blocks from backend SKILL.md files."""
import re
from pathlib import Path

try:
    import yaml
except ImportError as e:
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml") from e


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _extract_yaml_blocks(text: str):
    return [m.group(1) for m in _YAML_BLOCK_RE.finditer(text)]


def _validate_contract(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    wc = d.get("warmup_contract")
    if not isinstance(wc, dict):
        return False
    if wc.get("version") != 1:
        return False
    cmds = wc.get("commands")
    if not isinstance(cmds, list) or not cmds:
        return False
    for cmd in cmds:
        if not isinstance(cmd, dict):
            return False
        if not cmd.get("id") or not isinstance(cmd.get("id"), str):
            return False
        if not cmd.get("shell") or not isinstance(cmd.get("shell"), str):
            return False
        out = cmd.get("output", {})
        if not isinstance(out, dict):
            return False
        if "required_fields" not in out or not isinstance(out["required_fields"], list):
            return False
    return True


def load_contract(skill_md: Path) -> dict | None:
    """Load and validate the warmup_contract block from a SKILL.md file.
    Returns the warmup_contract dict (unwrapped), or None if missing/invalid.
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for block in _extract_yaml_blocks(text):
        if "warmup_contract" not in block:
            continue
        try:
            d = yaml.safe_load(block)
        except yaml.YAMLError:
            return None
        if _validate_contract(d):
            return d["warmup_contract"]
        return None
    return None
```

- [ ] **Step 4: Install PyYAML if needed + run tests**

```bash
python3 -c "import yaml" 2>/dev/null || pip install pyyaml
pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestContractParser -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/contract.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add warmup_contract parser + validator"
```

---

### Task 12: Availability probe

**Files:**
- Create: `skills/ark-context-warmup/scripts/availability.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing test**

Append to `test_warmup_helpers.py`:

```python
_AVAIL_PATH = _P(__file__).parent / "availability.py"
_spec_a = _ilu.spec_from_file_location("availability", _AVAIL_PATH)
avail = _ilu.module_from_spec(_spec_a)
_spec_a.loader.exec_module(avail)


class TestAvailabilityProbe:
    def test_all_unavailable(self, tmp_path):
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nonexistent",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,  # not on PATH
        )
        assert p["notebooklm"] is False
        assert p["wiki"] is False
        assert p["tasknotes"] is False

    def test_wiki_detected(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "_meta").mkdir(parents=True)
        (vault / "index.md").write_text("# Index\n")
        (vault / "_meta" / "vault-schema.md").write_text("# Schema\n")
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is True

    def test_wiki_missing_schema(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "index.md").write_text("# Index\n")
        # No _meta/vault-schema.md
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=vault,
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["wiki"] is False

    def test_tasknotes_detected(self, tmp_path):
        tn = tmp_path / "tn"
        (tn / "meta").mkdir(parents=True)
        (tn / "meta" / "X-counter").write_text("1\n")
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tn,
            task_prefix="X-",
            notebooklm_cli_path=None,
        )
        assert p["tasknotes"] is True

    def test_notebooklm_detected_with_valid_config(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "abc"}}}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",  # stand-in for "CLI exists"
        )
        assert p["notebooklm"] is True

    def test_notebooklm_multi_notebook_without_default_skipped(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",
        )
        assert p["notebooklm"] is False
        assert "default_for_warmup" in p["notebooklm_skip_reason"]

    def test_notebooklm_multi_notebook_with_default(self, tmp_path):
        (tmp_path / ".notebooklm").mkdir()
        (tmp_path / ".notebooklm" / "config.json").write_text(
            '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}, "default_for_warmup": "main"}'
        )
        p = avail.probe(
            project_repo=tmp_path,
            vault_path=tmp_path / "nope",
            tasknotes_path=tmp_path / "nope",
            task_prefix="X-",
            notebooklm_cli_path="/usr/bin/echo",
        )
        assert p["notebooklm"] is True
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestAvailabilityProbe -v`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/availability.py`:

```python
"""Availability probe for /ark-context-warmup backends."""
import json
from pathlib import Path


def _load_notebooklm_config(project_repo: Path, vault_path: Path) -> dict | None:
    # Lookup order: vault_path/.notebooklm/config.json first, then project_repo/.notebooklm/config.json
    for base in (vault_path, project_repo):
        cfg = base / ".notebooklm" / "config.json"
        if cfg.exists():
            try:
                return json.loads(cfg.read_text())
            except (json.JSONDecodeError, OSError):
                return None
    return None


def probe(
    *,
    project_repo: Path,
    vault_path: Path,
    tasknotes_path: Path,
    task_prefix: str,
    notebooklm_cli_path: str | None,
) -> dict:
    """Returns a dict with keys:
    - notebooklm: bool
    - wiki: bool
    - tasknotes: bool
    - notebooklm_skip_reason, wiki_skip_reason, tasknotes_skip_reason: str (present if False)
    """
    result: dict = {}

    # NotebookLM
    if notebooklm_cli_path is None:
        result["notebooklm"] = False
        result["notebooklm_skip_reason"] = "notebooklm CLI not on PATH"
    else:
        cfg = _load_notebooklm_config(project_repo, vault_path)
        if cfg is None:
            result["notebooklm"] = False
            result["notebooklm_skip_reason"] = "no parseable .notebooklm/config.json in project repo or vault"
        else:
            notebooks = cfg.get("notebooks", {})
            if not notebooks:
                result["notebooklm"] = False
                result["notebooklm_skip_reason"] = "config has no notebooks"
            elif len(notebooks) == 1:
                result["notebooklm"] = True
            else:
                default_key = cfg.get("default_for_warmup")
                if default_key and default_key in notebooks:
                    result["notebooklm"] = True
                else:
                    result["notebooklm"] = False
                    result["notebooklm_skip_reason"] = (
                        "Multi-notebook NotebookLM config without default_for_warmup — lane skipped. "
                        "Add default_for_warmup to .notebooklm/config.json pointing at the notebook key to use."
                    )

    # Wiki
    index = vault_path / "index.md"
    schema = vault_path / "_meta" / "vault-schema.md"
    if not index.exists():
        result["wiki"] = False
        result["wiki_skip_reason"] = f"index.md missing at {index}"
    elif not schema.exists():
        result["wiki"] = False
        result["wiki_skip_reason"] = f"vault schema missing at {schema}"
    else:
        result["wiki"] = True

    # TaskNotes
    counter = tasknotes_path / "meta" / f"{task_prefix}counter"
    if not counter.exists():
        result["tasknotes"] = False
        result["tasknotes_skip_reason"] = f"counter file missing at {counter}"
    else:
        result["tasknotes"] = True

    return result
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestAvailabilityProbe -v`
Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/availability.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add availability probe with D5 multi-notebook rule"
```

---

## Phase 4 — Evidence Generator + Synthesizer

### Task 13: Evidence candidate generator (D3 rules)

**Files:**
- Create: `skills/ark-context-warmup/scripts/evidence.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing tests**

Append to `test_warmup_helpers.py`:

```python
_EV_PATH = _P(__file__).parent / "evidence.py"
_spec_e = _ilu.spec_from_file_location("evidence", _EV_PATH)
evidence = _ilu.module_from_spec(_spec_e)
_spec_e.loader.exec_module(evidence)


class TestEvidenceCandidates:
    def test_duplicate_component_match_high(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration provider",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-001", "title": "Auth rework", "status": "in-progress",
                     "component": "auth", "work-type": "feature", "matched_field": "component", "title_overlap": 0.2}
                ],
                "status_summary": {"in-progress": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert len(dups) == 1
        assert dups[0]["confidence"] == "high"
        assert dups[0]["id"] == "X-001"

    def test_duplicate_medium_overlap(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting api",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-002", "title": "rate limiting implementation api", "status": "open",
                     "component": "server", "work-type": "feature",
                     "matched_field": "title_overlap=0.75", "title_overlap": 0.75}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "rate",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert len(dups) == 1
        assert dups[0]["confidence"] == "medium"

    def test_duplicate_low_overlap_dropped(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting api",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-003", "title": "unrelated caching work", "status": "open",
                     "component": "cache", "work-type": "feature",
                     "matched_field": "title_overlap=0.45", "title_overlap": 0.45}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "rate",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert dups == []

    def test_closed_task_not_duplicate(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-004", "title": "Auth migration", "status": "done",
                     "component": "auth", "work-type": "feature",
                     "matched_field": "component", "title_overlap": 1.0}
                ],
                "status_summary": {"done": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        assert not [c for c in out if c["type"] == "Possible duplicate"]

    def test_worktype_alone_not_high(self):
        # Work-type "bug" matches but NO component or title overlap → should be dropped
        out = evidence.derive_candidates(
            task_normalized="fix authentication bug",
            scenario="bugfix",
            tasknotes={
                "matches": [
                    {"id": "X-005", "title": "completely unrelated feature", "status": "open",
                     "component": "billing", "work-type": "bug",
                     "matched_field": None, "title_overlap": 0.1}
                ],
                "status_summary": {"open": 1},
                "extracted_component": "authentication",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        dups = [c for c in out if c["type"] == "Possible duplicate"]
        assert dups == []

    def test_prior_rejection_hit(self):
        out = evidence.derive_candidates(
            task_normalized="service mesh adoption",
            scenario="greenfield",
            tasknotes={"matches": [], "status_summary": {}, "extracted_component": "service"},
            notebooklm={
                "citations": [
                    {"session": "S042", "quote": "We decided against service mesh adoption because of operational overhead."}
                ],
                "bootstrap": "",
                "session_continue": "",
            },
            wiki={"matches": []},
        )
        prs = [c for c in out if c["type"] == "Possible prior rejection"]
        assert len(prs) == 1
        assert prs[0]["confidence"] == "medium"

    def test_prior_rejection_false_positive(self):
        out = evidence.derive_candidates(
            task_normalized="rate limiting",
            scenario="greenfield",
            tasknotes={"matches": [], "status_summary": {}, "extracted_component": "rate"},
            notebooklm={
                "citations": [
                    {"session": "S042", "quote": "We decided against the old quarterly planning cadence."}
                ],
                "bootstrap": "",
                "session_continue": "",
            },
            wiki={"matches": []},
        )
        prs = [c for c in out if c["type"] == "Possible prior rejection"]
        assert prs == []  # no token overlap with task

    def test_in_flight_collision_high(self):
        out = evidence.derive_candidates(
            task_normalized="auth migration",
            scenario="greenfield",
            tasknotes={
                "matches": [
                    {"id": "X-006", "title": "Auth rework phase 2", "status": "in-progress",
                     "component": "auth", "work-type": "feature",
                     "matched_field": "component", "title_overlap": 0.3}
                ],
                "status_summary": {"in-progress": 1},
                "extracted_component": "auth",
            },
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        colls = [c for c in out if c["type"] == "Possible in-flight collision"]
        assert len(colls) == 1
        assert colls[0]["confidence"] == "high"

    def test_degraded_coverage_emitted(self):
        out = evidence.derive_candidates(
            task_normalized="anything",
            scenario="greenfield",
            tasknotes=None,  # lane unavailable
            notebooklm={"citations": [], "bootstrap": "", "session_continue": ""},
            wiki={"matches": []},
        )
        deg = [c for c in out if c["type"] == "Degraded coverage"]
        assert len(deg) == 1
        assert "tasknotes" in deg[0]["detail"].lower()
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestEvidenceCandidates -v`
Expected: FAIL (file doesn't exist).

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/evidence.py`:

```python
"""Evidence candidate generator per spec D3."""
import re

# Trigger phrases for prior-rejection detection (per D3)
_REJECTION_TRIGGERS = [
    "decided against",
    "tried and failed",
    "rejected",
    "won't do",
    "wont do",
    "abandoned",
]


def _tokens(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _has_trigger_near_keywords(quote: str, task_tokens: set, window: int = 30) -> bool:
    """True if any trigger phrase occurs within `window` tokens of ≥2 task tokens."""
    words = re.findall(r"[a-zA-Z0-9]+", quote.lower())
    for trigger in _REJECTION_TRIGGERS:
        trig_words = trigger.split()
        # Find the start index of the trigger in the word list
        for i in range(len(words) - len(trig_words) + 1):
            if words[i:i+len(trig_words)] == trig_words:
                start = max(0, i - window)
                end = min(len(words), i + len(trig_words) + window)
                win_tokens = set(words[start:end])
                if len(win_tokens & task_tokens) >= 2:
                    return True
    return False


def derive_candidates(*, task_normalized, scenario, tasknotes, notebooklm, wiki):
    """Returns a list of evidence candidates per spec D3.
    Each candidate: {type, confidence?, id?, detail, reason}

    tasknotes: dict from warmup_search OR None if lane unavailable
    notebooklm: dict with 'citations', 'bootstrap', 'session_continue' (may be empty strings)
    wiki: dict with 'matches' list
    """
    out = []

    # Duplicate + in-flight collision (from tasknotes)
    if tasknotes is not None:
        task_tokens = _tokens(task_normalized)
        extracted_component = tasknotes.get("extracted_component", "")
        for m in tasknotes.get("matches", []):
            if m["status"] == "done":
                continue
            # Duplicate
            dup_conf = None
            matched = m.get("matched_field") or ""
            if matched == "component" and m.get("status") in ("in-progress", "open", "planned"):
                dup_conf = "high"
            elif matched and matched.startswith("title_overlap="):
                overlap = float(matched.split("=", 1)[1])
                if overlap >= 0.60:
                    dup_conf = "medium"
                # <0.60 -> dropped
            if dup_conf:
                out.append({
                    "type": "Possible duplicate",
                    "confidence": dup_conf,
                    "id": m["id"],
                    "detail": m["title"],
                    "reason": f"matched {matched}; status={m['status']}",
                })
            # In-flight collision (distinct signal from duplicate)
            if m.get("status") == "in-progress":
                if extracted_component and m.get("component", "").lower() == extracted_component:
                    out.append({
                        "type": "Possible in-flight collision",
                        "confidence": "high",
                        "id": m["id"],
                        "detail": m["title"],
                        "reason": f"shared component={extracted_component}; status=in-progress",
                    })
    else:
        out.append({
            "type": "Degraded coverage",
            "detail": "tasknotes lane unavailable",
            "reason": "backend skipped per availability probe",
        })

    # Prior rejection (from notebooklm citations)
    task_tokens = _tokens(task_normalized)
    for cit in (notebooklm.get("citations") or []):
        quote = cit.get("quote", "")
        if _has_trigger_near_keywords(quote, task_tokens):
            out.append({
                "type": "Possible prior rejection",
                "confidence": "medium",
                "id": cit.get("session", ""),
                "detail": quote,
                "reason": "trigger phrase within 30 tokens of ≥2 task keywords",
            })

    # Degraded coverage for notebooklm
    if not (notebooklm.get("bootstrap") or notebooklm.get("session_continue") or notebooklm.get("citations")):
        out.append({
            "type": "Degraded coverage",
            "detail": "notebooklm lane produced no content",
            "reason": "backend skipped or returned empty",
        })

    # Degraded coverage for wiki
    if not wiki.get("matches"):
        out.append({
            "type": "Degraded coverage",
            "detail": "wiki lane produced no matches",
            "reason": "backend skipped or no vault matches",
        })

    return out
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestEvidenceCandidates -v`
Expected: 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/evidence.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add deterministic evidence candidate generator (D3 rules)"
```

---

### Task 14: Brief synthesizer + atomic cache write

**Files:**
- Create: `skills/ark-context-warmup/scripts/synthesize.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing test**

Append to `test_warmup_helpers.py`:

```python
_SYN_PATH = _P(__file__).parent / "synthesize.py"
_spec_s = _ilu.spec_from_file_location("synthesize", _SYN_PATH)
synthesize = _ilu.module_from_spec(_spec_s)
_spec_s.loader.exec_module(synthesize)


class TestSynthesize:
    def test_brief_structure(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123",
            task_hash="hash1234abcd5678",
            task_summary="Add rate limiting",
            scenario="greenfield",
            notebooklm_out="Recent sessions: S042...",
            wiki_out="Found: rate-limiting.md",
            tasknotes_out="3 in-progress, 1 open",
            evidence=[{"type": "Possible duplicate", "confidence": "high", "id": "X-01",
                       "detail": "rate limiting", "reason": "component match"}],
        )
        assert "## Context Brief" in brief
        assert "### Where We Left Off" in brief
        assert "### Recent Project Activity" in brief
        assert "### Vault Knowledge Relevant to This Task" in brief
        assert "### Related Tasks & In-flight Work" in brief
        assert "### Evidence" in brief
        assert "Possible duplicate" in brief

    def test_empty_evidence_reads_none(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        assert "### Evidence\nNone" in brief

    def test_frontmatter_fields(self):
        brief = synthesize.assemble_brief(
            chain_id="CID123", task_hash="hash1234abcd5678", task_summary="x",
            scenario="bugfix", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        # Must start with frontmatter for the cache freshness check
        assert brief.startswith("---\n")
        assert "chain_id: CID123" in brief
        assert "task_hash: hash1234abcd5678" in brief

    def test_atomic_write_and_prune(self, tmp_path):
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        # Pre-populate with a stale brief
        stale = cache_dir / "context-brief-OLD-00000000.md"
        stale.write_text("stale")
        import os, time
        old_time = time.time() - (25 * 3600)  # 25h ago
        os.utime(stale, (old_time, old_time))
        brief = "## Context Brief\nhello"
        written = synthesize.write_brief_atomic(
            cache_dir=cache_dir, chain_id="NEW",
            task_hash="abcdef1234567890", brief_text=brief,
        )
        assert written.exists()
        assert written.name == "context-brief-NEW-abcdef12.md"
        # 24h pruning happened
        assert not stale.exists()

    def test_cache_freshness_check(self, tmp_path):
        cache_dir = tmp_path / ".ark-workflow"
        cache_dir.mkdir()
        brief = synthesize.assemble_brief(
            chain_id="CID", task_hash="abcdef1234567890", task_summary="x",
            scenario="greenfield", notebooklm_out="", wiki_out="", tasknotes_out="", evidence=[],
        )
        synthesize.write_brief_atomic(cache_dir=cache_dir, chain_id="CID",
                                      task_hash="abcdef1234567890", brief_text=brief)
        assert synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="CID", task_hash="abcdef1234567890"
        ) is not None
        # Mismatched hash → cache miss
        assert synthesize.cached_brief_if_fresh(
            cache_dir=cache_dir, chain_id="CID", task_hash="DIFFERENT12345678"
        ) is None
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestSynthesize -v`
Expected: FAIL.

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/synthesize.py`:

```python
"""Synthesizer: assembles the Context Brief + handles atomic cache writes + 24h pruning."""
import time
from pathlib import Path


_CACHE_TTL_SECONDS = 2 * 3600          # 2 hours
_CACHE_PRUNE_SECONDS = 24 * 3600        # 24 hours


def _format_evidence(evidence: list) -> str:
    if not evidence:
        return "None"
    lines = []
    for ev in evidence:
        kind = ev.get("type", "Unknown")
        conf = ev.get("confidence")
        id_ = ev.get("id")
        detail = ev.get("detail", "")
        reason = ev.get("reason", "")
        parts = [f"- **{kind}**"]
        if conf:
            parts.append(f"(conf: {conf})")
        if id_:
            parts.append(f"`{id_}`")
        parts.append(f"— {detail}")
        if reason:
            parts.append(f"  \n  *{reason}*")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def assemble_brief(
    *,
    chain_id: str,
    task_hash: str,
    task_summary: str,
    scenario: str,
    notebooklm_out: str,
    wiki_out: str,
    tasknotes_out: str,
    evidence: list,
) -> str:
    return (
        "---\n"
        f"chain_id: {chain_id}\n"
        f"task_hash: {task_hash}\n"
        f"task_summary: {task_summary}\n"
        f"scenario: {scenario}\n"
        f"generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n"
        "---\n\n"
        "## Context Brief\n\n"
        "### Where We Left Off\n"
        f"{notebooklm_out or 'Fresh start — no recent session found.'}\n\n"
        "### Recent Project Activity\n"
        f"{notebooklm_out or 'Not queried — notebooklm lane unavailable.'}\n\n"
        "### Vault Knowledge Relevant to This Task\n"
        f"{wiki_out or 'Not queried — wiki backend unavailable.'}\n\n"
        "### Related Tasks & In-flight Work\n"
        f"{tasknotes_out or 'Not queried — tasknotes backend unavailable.'}\n\n"
        "### Evidence\n"
        f"{_format_evidence(evidence)}\n"
    )


def _cache_filename(chain_id: str, task_hash: str) -> str:
    return f"context-brief-{chain_id}-{task_hash[:8]}.md"


def write_brief_atomic(*, cache_dir: Path, chain_id: str, task_hash: str, brief_text: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / _cache_filename(chain_id, task_hash)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(brief_text, encoding="utf-8")
    tmp.replace(target)  # atomic on POSIX
    _prune(cache_dir)
    return target


def _prune(cache_dir: Path) -> None:
    now = time.time()
    for p in cache_dir.glob("context-brief-*.md"):
        try:
            if now - p.stat().st_mtime > _CACHE_PRUNE_SECONDS:
                p.unlink()
        except OSError:
            pass
    for p in cache_dir.glob("context-brief-*.md.tmp"):
        try:
            if now - p.stat().st_mtime > 600:  # 10 minutes — stale tmp
                p.unlink()
        except OSError:
            pass


def cached_brief_if_fresh(*, cache_dir: Path, chain_id: str, task_hash: str) -> str | None:
    path = cache_dir / _cache_filename(chain_id, task_hash)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > _CACHE_TTL_SECONDS:
        return None
    text = path.read_text(encoding="utf-8")
    # Defense-in-depth: verify frontmatter matches
    if f"chain_id: {chain_id}" not in text:
        return None
    if f"task_hash: {task_hash}" not in text:
        return None
    return text
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py::TestSynthesize -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/synthesize.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add synthesizer, atomic cache write, and 24h pruning"
```

---

## Phase 5 — Contract Executor + SKILL.md Orchestration

### Task 15: Contract Executor (engine that runs warmup_contract commands)

**Rationale:** `contract.py` parses/validates the YAML. An executor is required to actually *run* contracts — resolve inputs, run preconditions, interpolate shell templates, execute commands with timeouts, extract fields via simple JSONPath, and validate required_fields. Without it, Task 16's SKILL.md orchestration has no runtime engine. (Gap identified by `/codex` third-round review.)

**Files:**
- Create: `skills/ark-context-warmup/scripts/executor.py`
- Modify: `skills/ark-context-warmup/scripts/test_warmup_helpers.py`

- [ ] **Step 1: Write the failing tests**

Append to `test_warmup_helpers.py`:

```python
_EXEC_PATH = _P(__file__).parent / "executor.py"
_spec_ex = _ilu.spec_from_file_location("executor", _EXEC_PATH)
executor = _ilu.module_from_spec(_spec_ex)
_spec_ex.loader.exec_module(executor)


class TestInputResolution:
    def test_env_input(self, monkeypatch):
        monkeypatch.setenv("WARMUP_SCENARIO", "greenfield")
        input_spec = {"from": "env", "env_var": "WARMUP_SCENARIO", "required": True}
        assert executor.resolve_input(input_spec, config=None, templates={}) == "greenfield"

    def test_env_input_missing_required(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        input_spec = {"from": "env", "env_var": "MISSING_VAR", "required": True}
        import pytest
        with pytest.raises(executor.InputResolutionError):
            executor.resolve_input(input_spec, config=None, templates={})

    def test_config_input_simple_json_path(self):
        cfg = {"notebooks": {"main": {"id": "nb-abc"}}}
        input_spec = {"from": "config", "json_path": "notebooks.main.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-abc"

    def test_config_input_lookup_single_or_default_for_warmup(self):
        # Single notebook → use it
        cfg = {"notebooks": {"main": {"id": "nb-abc"}}}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-abc"

    def test_config_input_lookup_multi_with_default(self):
        cfg = {"notebooks": {"a": {"id": "nb-a"}, "b": {"id": "nb-b"}}, "default_for_warmup": "b"}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        assert executor.resolve_input(input_spec, config=cfg, templates={}) == "nb-b"

    def test_config_input_lookup_multi_without_default_raises(self):
        cfg = {"notebooks": {"a": {"id": "nb-a"}, "b": {"id": "nb-b"}}}
        input_spec = {"from": "config", "lookup": "single_or_default_for_warmup",
                      "json_path_template": "notebooks.{key}.id", "required": True}
        import pytest
        with pytest.raises(executor.InputResolutionError, match="default_for_warmup"):
            executor.resolve_input(input_spec, config=cfg, templates={})

    def test_template_input(self):
        input_spec = {"from": "template", "template_id": "my_prompt"}
        result = executor.resolve_input(
            input_spec, config=None,
            templates={"my_prompt": "Hello, {WARMUP_TASK_TEXT}!"},
        )
        assert result == "Hello, {WARMUP_TASK_TEXT}!"


class TestShellSubstitution:
    def test_substitute(self):
        result = executor.substitute_shell_template(
            "run {{cmd}} with id {{id}}", {"cmd": "do-thing", "id": "xyz"}
        )
        assert result == "run do-thing with id xyz"

    def test_missing_var_raises(self):
        import pytest
        with pytest.raises(KeyError):
            executor.substitute_shell_template("run {{missing}}", {})


class TestJSONPathExtract:
    def test_dotted(self):
        data = {"answer": {"sections": {"recent": "stuff"}}}
        assert executor.extract_json_path(data, "$.answer.sections.recent") == "stuff"

    def test_missing_key_returns_none(self):
        assert executor.extract_json_path({"a": 1}, "$.b.c") is None

    def test_root(self):
        assert executor.extract_json_path({"x": 1}, "$") == {"x": 1}

    def test_array_indexing_not_supported_raises(self):
        import pytest
        with pytest.raises(executor.JSONPathError, match="array"):
            executor.extract_json_path({"a": [1, 2]}, "$.a[0]")


class TestPrecondition:
    def test_script_exit_zero_runs(self, tmp_path):
        script = tmp_path / "ok.sh"
        script.write_text("#!/usr/bin/env bash\nexit 0\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=5
        )
        assert ok is True

    def test_script_nonzero_skips(self, tmp_path):
        script = tmp_path / "nope.sh"
        script.write_text("#!/usr/bin/env bash\necho skip reason >&2\nexit 1\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=5
        )
        assert ok is False
        assert "skip reason" in stderr

    def test_script_timeout_treated_as_skip(self, tmp_path):
        script = tmp_path / "slow.sh"
        script.write_text("#!/usr/bin/env bash\nsleep 10\n")
        script.chmod(0o755)
        ok, stderr = executor.run_precondition(
            script_path=script, env={}, timeout_s=1
        )
        assert ok is False
        assert "timeout" in stderr.lower() or "timed out" in stderr.lower()

    def test_script_receives_env(self, tmp_path):
        script = tmp_path / "echoenv.sh"
        script.write_text("#!/usr/bin/env bash\n[ \"$WARMUP_TASK_HASH\" = 'abc' ] && exit 0 || exit 1\n")
        script.chmod(0o755)
        ok, _ = executor.run_precondition(
            script_path=script, env={"WARMUP_TASK_HASH": "abc"}, timeout_s=5
        )
        assert ok is True


class TestShellExecute:
    def test_shell_timeout(self):
        r = executor.run_shell("sleep 10", timeout_s=1)
        assert r.timed_out is True

    def test_shell_captures_stdout(self):
        r = executor.run_shell("echo hello", timeout_s=5)
        assert r.timed_out is False
        assert r.exit_code == 0
        assert r.stdout.strip() == "hello"


class TestEndToEndExecute:
    def test_execute_command_happy_path(self, tmp_path, monkeypatch):
        # Build a fake backend skill that reads an env var and prints JSON
        script = tmp_path / "fake_backend.sh"
        script.write_text("#!/usr/bin/env bash\necho '{\"payload\": {\"value\": \"'\"$FOO\"'\"}}'\n")
        script.chmod(0o755)
        monkeypatch.setenv("FOO", "bar")
        command_spec = {
            "id": "fake",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {"value": "$.payload.value"},
                "required_fields": ["value"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result == {"value": "bar"}

    def test_execute_command_missing_required_field_returns_none(self, tmp_path):
        script = tmp_path / "empty.sh"
        script.write_text("#!/usr/bin/env bash\necho '{}'\n")
        script.chmod(0o755)
        command_spec = {
            "id": "empty",
            "shell": f"bash {script}",
            "inputs": {},
            "output": {
                "format": "json",
                "extract": {"value": "$.missing"},
                "required_fields": ["value"],
            },
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result is None

    def test_execute_command_precondition_skip(self, tmp_path):
        pre = tmp_path / "pre.sh"
        pre.write_text("#!/usr/bin/env bash\nexit 1\n")
        pre.chmod(0o755)
        shell_script = tmp_path / "main.sh"
        shell_script.write_text("#!/usr/bin/env bash\necho '{\"x\":\"should-not-run\"}'\n")
        shell_script.chmod(0o755)
        command_spec = {
            "id": "skipped",
            "shell": f"bash {shell_script}",
            "inputs": {},
            "preconditions": [{"id": "no", "script": str(pre)}],
            "output": {"format": "json", "extract": {"x": "$.x"}, "required_fields": ["x"]},
        }
        result = executor.execute_command(
            command_spec, config=None, templates={}, env_overrides={}, timeout_s=5
        )
        assert result is None  # Skipped due to precondition
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py -v -k "TestInputResolution or TestShellSubstitution or TestJSONPathExtract or TestPrecondition or TestShellExecute or TestEndToEndExecute"`
Expected: FAIL (`executor.py` not found).

- [ ] **Step 3: Write the implementation**

Create `skills/ark-context-warmup/scripts/executor.py`:

```python
"""Contract executor: runs warmup_contract commands end-to-end.

Resolves inputs (env, config JSON-path, template) → runs preconditions (D6 convention) →
substitutes shell template → runs shell with timeout → parses JSON → extracts fields via
simple dotted JSONPath → validates required_fields.
"""
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class InputResolutionError(RuntimeError):
    pass


class JSONPathError(RuntimeError):
    pass


@dataclass
class ShellResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


def extract_json_path(data: Any, path: str) -> Any:
    """Simple dotted JSONPath. Supports:
      - "$"          → the whole document
      - "$.a.b.c"    → nested key access
    Arrays are NOT supported (raises JSONPathError if requested with [N] syntax).
    Missing keys return None.
    """
    if path == "$":
        return data
    if not path.startswith("$."):
        raise JSONPathError(f"JSONPath must start with '$' or '$.': {path}")
    if "[" in path or "]" in path:
        raise JSONPathError(f"array indexing not supported in simple JSONPath: {path}")
    current = data
    for key in path[2:].split("."):
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]
    return current


def substitute_shell_template(template: str, vars_: dict) -> str:
    """Substitute {{var}} placeholders. Raises KeyError if any placeholder is unresolved."""
    def _replace(m):
        name = m.group(1).strip()
        if name not in vars_:
            raise KeyError(f"unresolved shell template variable: {name}")
        return str(vars_[name])
    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", _replace, template)


def _lookup_single_or_default(config: dict, json_path_template: str) -> Any:
    """Implements the D5 lookup: if notebooks has one key, use it; if multiple,
    require default_for_warmup to pick. Raises otherwise.
    """
    notebooks = config.get("notebooks", {})
    if not notebooks:
        raise InputResolutionError("config has no notebooks")
    if len(notebooks) == 1:
        key = next(iter(notebooks))
    else:
        key = config.get("default_for_warmup")
        if not key or key not in notebooks:
            raise InputResolutionError(
                "Multi-notebook NotebookLM config without default_for_warmup — "
                "lane skipped. Add default_for_warmup to .notebooklm/config.json "
                "pointing at the notebook key to use."
            )
    # Substitute {key} in the json_path_template, then extract
    resolved_path = json_path_template.replace("{key}", key)
    value = extract_json_path(config, "$." + resolved_path) if not resolved_path.startswith("$") else extract_json_path(config, resolved_path)
    if value is None:
        raise InputResolutionError(f"config path {resolved_path} resolved to None")
    return value


def resolve_input(input_spec: dict, *, config: dict | None, templates: dict) -> Any:
    """Resolve a single input per D6. `input_spec` is one entry from warmup_contract.commands[*].inputs."""
    source = input_spec.get("from")
    required = bool(input_spec.get("required", False))
    if source == "env":
        name = input_spec["env_var"]
        val = os.environ.get(name)
        if val is None and required:
            raise InputResolutionError(f"required env var not set: {name}")
        return val
    if source == "config":
        if config is None and required:
            raise InputResolutionError("config required but not provided")
        if config is None:
            return None
        # Two flavors: explicit json_path, or lookup rule
        if "json_path" in input_spec:
            return extract_json_path(config, "$." + input_spec["json_path"] if not input_spec["json_path"].startswith("$") else input_spec["json_path"])
        if input_spec.get("lookup") == "single_or_default_for_warmup":
            return _lookup_single_or_default(config, input_spec["json_path_template"])
        raise InputResolutionError(f"config input needs json_path or lookup: {input_spec}")
    if source == "template":
        tid = input_spec["template_id"]
        if tid not in templates:
            raise InputResolutionError(f"unknown template id: {tid}")
        return templates[tid]
    raise InputResolutionError(f"unknown input source: {source}")


def run_precondition(*, script_path: Path, env: dict, timeout_s: int = 5) -> tuple[bool, str]:
    """Run a precondition script per D6. Returns (exit_0_bool, stderr_text)."""
    if not Path(script_path).exists():
        return False, f"precondition script not found: {script_path}"
    merged_env = {**os.environ, **env}
    try:
        r = subprocess.run(
            ["bash", str(script_path)],
            env=merged_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return (r.returncode == 0), r.stderr
    except subprocess.TimeoutExpired as e:
        return False, f"precondition timeout after {timeout_s}s"


def run_shell(shell_cmd: str, *, timeout_s: int = 90, env: dict | None = None) -> ShellResult:
    """Run a resolved shell command and return its result."""
    merged_env = {**os.environ, **(env or {})}
    try:
        r = subprocess.run(
            ["bash", "-c", shell_cmd],
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ShellResult(exit_code=r.returncode, stdout=r.stdout, stderr=r.stderr, timed_out=False)
    except subprocess.TimeoutExpired as e:
        return ShellResult(exit_code=-1, stdout=(e.stdout or "").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                           stderr=(e.stderr or "").decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
                           timed_out=True)


def execute_command(
    command_spec: dict,
    *,
    config: dict | None,
    templates: dict,
    env_overrides: dict,
    timeout_s: int = 90,
) -> dict | None:
    """Execute a single warmup_contract command. Returns extracted dict on success,
    or None if the command was skipped (precondition failed) or failed validation.
    """
    # 1. Resolve inputs
    resolved: dict = {}
    for name, spec in (command_spec.get("inputs") or {}).items():
        try:
            resolved[name] = resolve_input(spec, config=config, templates=templates)
        except InputResolutionError as e:
            # Treat missing-required-input as a skip (same outcome as missing backend)
            return None

    # 2. Run preconditions (all must pass)
    for pre in (command_spec.get("preconditions") or []):
        script_path = Path(pre["script"])
        ok, _stderr = run_precondition(script_path=script_path, env=env_overrides, timeout_s=5)
        if not ok:
            return None  # Skip — not an error

    # 3. Substitute shell template
    try:
        shell_cmd = substitute_shell_template(command_spec["shell"], resolved)
    except KeyError:
        return None

    # 4. Run shell
    result = run_shell(shell_cmd, timeout_s=timeout_s, env=env_overrides)
    if result.timed_out or result.exit_code != 0:
        return None

    # 5. Parse JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    # 6. Extract fields
    extract_spec = command_spec.get("output", {}).get("extract", {})
    extracted: dict = {}
    for field, path in extract_spec.items():
        try:
            extracted[field] = extract_json_path(data, path)
        except JSONPathError:
            return None

    # 7. Validate required_fields
    required = command_spec.get("output", {}).get("required_fields", [])
    for field in required:
        if not extracted.get(field):
            return None  # Semantically empty — treat as degraded

    return extracted
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_warmup_helpers.py -v -k "TestInputResolution or TestShellSubstitution or TestJSONPathExtract or TestPrecondition or TestShellExecute or TestEndToEndExecute"`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/executor.py skills/ark-context-warmup/scripts/test_warmup_helpers.py
git commit -m "feat(warmup): add contract executor (resolves inputs, preconditions, shell, JSONPath)"
```

---

### Task 16: Write SKILL.md with frontmatter + routing

**Files:**
- Create: `skills/ark-context-warmup/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `skills/ark-context-warmup/SKILL.md`:

```markdown
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
1. If `HAS_WIKI`: load wiki-query contract, pick the scenario's template, call `executor.execute_command(...)`. On None result, record a `Degraded coverage` candidate for the wiki lane and continue to tasknotes.
2. If `HAS_TASKNOTES`: load tasknotes contract, call `executor.execute_command(...)`. Same `Degraded coverage` handling.
3. Return combined JSON: `{"wiki": ..., "tasknotes": ..., "degraded_lanes": [...]}`

Each lane has a 90s outer timeout at the subagent level (in addition to the 90s per-command timeout inside `executor.execute_command`).

### Step 5: Evidence + Synthesis

- Pass all lane outputs to `evidence.derive_candidates(...)`
- Pass the three lane outputs + evidence to `synthesize.assemble_brief(...)`
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
```

- [ ] **Step 2: Lint SKILL.md**

```bash
head -5 skills/ark-context-warmup/SKILL.md | grep -q '^name: ark-context-warmup'
head -5 skills/ark-context-warmup/SKILL.md | grep -q '^description:'
```

Expected: both succeed silently.

- [ ] **Step 3: Commit**

```bash
git add skills/ark-context-warmup/SKILL.md
git commit -m "feat(warmup): add SKILL.md orchestration with frontmatter + workflow"
```

---

## Phase 6 — Integration Tests + MCP Concurrency Probe

### Task 17: bats-core integration test for availability probe

**Files:**
- Create: `skills/ark-context-warmup/scripts/integration/test_availability.bats`

- [ ] **Step 1: Write the bats test**

Create `skills/ark-context-warmup/scripts/integration/test_availability.bats`:

```bash
#!/usr/bin/env bats

setup() {
    TMPDIR=$(mktemp -d)
    export TMPDIR
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "all backends unavailable → all three probes return false" {
    run python3 -c "
import sys
sys.path.insert(0, 'skills/ark-context-warmup/scripts')
import availability
from pathlib import Path
r = availability.probe(
    project_repo=Path('$TMPDIR'),
    vault_path=Path('$TMPDIR/nope'),
    tasknotes_path=Path('$TMPDIR/nope'),
    task_prefix='X-',
    notebooklm_cli_path=None,
)
print(r['notebooklm'], r['wiki'], r['tasknotes'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"False False False"* ]]
}

@test "multi-notebook config without default_for_warmup → notebooklm skipped with clear reason" {
    mkdir -p "$TMPDIR/.notebooklm"
    echo '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}}' > "$TMPDIR/.notebooklm/config.json"
    run python3 -c "
import sys
sys.path.insert(0, 'skills/ark-context-warmup/scripts')
import availability
from pathlib import Path
r = availability.probe(
    project_repo=Path('$TMPDIR'),
    vault_path=Path('$TMPDIR/nope'),
    tasknotes_path=Path('$TMPDIR/nope'),
    task_prefix='X-',
    notebooklm_cli_path='/usr/bin/echo',
)
print(r['notebooklm'])
print(r['notebooklm_skip_reason'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"False"* ]]
    [[ "$output" == *"default_for_warmup"* ]]
}
```

- [ ] **Step 2: Run**

```bash
command -v bats >/dev/null || { echo "install bats-core first (brew install bats-core)"; exit 1; }
bats skills/ark-context-warmup/scripts/integration/test_availability.bats
```

Expected: both tests pass.

- [ ] **Step 3: Commit**

```bash
git add skills/ark-context-warmup/scripts/integration/test_availability.bats
git commit -m "test(warmup): add bats integration tests for availability probe"
```

---

### Task 18: MCP concurrency probe (D4 validation script)

**Files:**
- Create: `skills/ark-context-warmup/scripts/mcp_concurrency_probe.sh`

- [ ] **Step 1: Write the probe**

Create `skills/ark-context-warmup/scripts/mcp_concurrency_probe.sh`:

```bash
#!/usr/bin/env bash
# MCP concurrency probe. Validates spec decision D4.
#
# Runs N parallel obsidian CLI reads against the same vault. If all succeed with
# no ClosedResourceError / connection errors, the vault-local lane *could* be
# parallelized. Current default per D4 is serialized regardless.
#
# This script is informational — used in CI to track whether the assumption
# is still warranted. Exit 0 = all parallel reads succeeded. Exit non-zero =
# at least one failure (serialized remains correct).
#
# Usage: mcp_concurrency_probe.sh <vault_path> <file_to_read> [<parallel_N>]

set -uo pipefail

VAULT="${1:-}"
FILE="${2:-}"
N="${3:-10}"

if [ -z "$VAULT" ] || [ -z "$FILE" ]; then
    echo "usage: $0 <vault_path> <file_to_read> [<parallel_N>]" >&2
    exit 2
fi

if ! command -v obsidian >/dev/null 2>&1; then
    echo "obsidian CLI not on PATH — probe cannot run" >&2
    exit 3
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Launch N parallel reads, collect exit codes
PIDS=()
for i in $(seq 1 "$N"); do
    ( obsidian read file="$FILE" >"$TMP/out.$i" 2>"$TMP/err.$i"; echo $? >"$TMP/exit.$i" ) &
    PIDS+=($!)
done

for pid in "${PIDS[@]}"; do wait "$pid"; done

FAIL_COUNT=0
for i in $(seq 1 "$N"); do
    code=$(cat "$TMP/exit.$i" 2>/dev/null || echo "unknown")
    if [ "$code" != "0" ]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "probe $i: exit=$code, stderr: $(head -c 200 "$TMP/err.$i")" >&2
    fi
done

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "probe: $N/$N parallel reads succeeded — MCP appears concurrency-safe for reads"
    exit 0
else
    echo "probe: $FAIL_COUNT/$N failures — keep serialized per D4" >&2
    exit 1
fi
```

- [ ] **Step 2: Syntax check + chmod**

```bash
bash -n skills/ark-context-warmup/scripts/mcp_concurrency_probe.sh
chmod +x skills/ark-context-warmup/scripts/mcp_concurrency_probe.sh
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add skills/ark-context-warmup/scripts/mcp_concurrency_probe.sh
git commit -m "chore(warmup): add MCP concurrency probe script (D4 validation)"
```

---

## Phase 7 — Evidence Regression Fixtures

### Task 19: Write fixture library + fixture-driven tests

**Files:**
- Create: `skills/ark-context-warmup/fixtures/*.yaml` (9 files)
- Create: `skills/ark-context-warmup/scripts/test_fixtures.py`

- [ ] **Step 1: Write the fixture-driven test**

Create `skills/ark-context-warmup/scripts/test_fixtures.py`:

```python
"""Fixture-driven regression tests for evidence candidates."""
import importlib.util
from pathlib import Path

import yaml

HERE = Path(__file__).parent
FIXTURES_DIR = HERE.parent / "fixtures"

_spec = importlib.util.spec_from_file_location("evidence", HERE / "evidence.py")
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)


def _load_fixture(name: str) -> dict:
    return yaml.safe_load((FIXTURES_DIR / name).read_text())


def _run(fixture: dict) -> list:
    return evidence.derive_candidates(
        task_normalized=fixture["input"]["task_normalized"],
        scenario=fixture["input"]["scenario"],
        tasknotes=fixture["input"].get("tasknotes"),
        notebooklm=fixture["input"].get("notebooklm") or {"citations": [], "bootstrap": "", "session_continue": ""},
        wiki=fixture["input"].get("wiki") or {"matches": []},
    )


def _match(candidate: dict, expected: dict) -> bool:
    for k, v in expected.items():
        if candidate.get(k) != v:
            return False
    return True


def _fixture_ids():
    return [p.name for p in sorted(FIXTURES_DIR.glob("*.yaml"))]


import pytest

@pytest.mark.parametrize("fixture_name", _fixture_ids())
def test_fixture(fixture_name: str):
    f = _load_fixture(fixture_name)
    got = _run(f)
    expected = f["expected"]["candidates"]
    # Every expected candidate must have at least one match in the output
    for e in expected:
        assert any(_match(g, e) for g in got), (
            f"fixture {fixture_name}: expected candidate {e} not found; got: {got}"
        )
    # If "exact" is true, no extra candidates allowed (modulo Degraded coverage)
    if f["expected"].get("exact"):
        non_degraded = [g for g in got if g.get("type") != "Degraded coverage"]
        assert len(non_degraded) == len(expected), (
            f"fixture {fixture_name}: extra candidates; got {non_degraded}"
        )
```

- [ ] **Step 2: Write fixture 1 — duplicate-component-hit**

Create `skills/ark-context-warmup/fixtures/duplicate-component-hit.yaml`:

```yaml
description: Open TaskNote with matching `component` field should emit high-confidence Possible duplicate
input:
  task_normalized: auth migration provider
  scenario: greenfield
  tasknotes:
    matches:
      - id: X-001
        title: Auth rework
        status: in-progress
        component: auth
        work-type: feature
        matched_field: component
        title_overlap: 0.2
    status_summary:
      in-progress: 1
    extracted_component: auth
expected:
  exact: false
  candidates:
    - type: Possible duplicate
      confidence: high
      id: X-001
```

- [ ] **Step 3: Write fixture 2 — duplicate-token-overlap-medium**

```yaml
description: 70% token overlap with open task, no structural match → medium-confidence duplicate
input:
  task_normalized: rate limiting api
  scenario: greenfield
  tasknotes:
    matches:
      - id: X-002
        title: rate limiting implementation api
        status: open
        component: server
        work-type: feature
        matched_field: title_overlap=0.75
        title_overlap: 0.75
    status_summary:
      open: 1
    extracted_component: rate
expected:
  exact: false
  candidates:
    - type: Possible duplicate
      confidence: medium
      id: X-002
```

Save as `skills/ark-context-warmup/fixtures/duplicate-token-overlap-medium.yaml`.

- [ ] **Step 4: Write fixture 3 — duplicate-token-overlap-low-noise**

```yaml
description: 45% overlap, no structural match → DROPPED (below noise floor)
input:
  task_normalized: rate limiting api
  scenario: greenfield
  tasknotes:
    matches:
      - id: X-003
        title: unrelated caching work
        status: open
        component: cache
        work-type: feature
        matched_field: title_overlap=0.45
        title_overlap: 0.45
    status_summary:
      open: 1
    extracted_component: rate
expected:
  exact: false
  candidates: []  # No duplicate candidate emitted
```

Save as `fixtures/duplicate-token-overlap-low-noise.yaml`.

- [ ] **Step 5: Write fixture 4 — duplicate-closed-ignored**

```yaml
description: Matching component but status=done → no candidate
input:
  task_normalized: auth migration
  scenario: greenfield
  tasknotes:
    matches:
      - id: X-004
        title: Auth migration
        status: done
        component: auth
        work-type: feature
        matched_field: component
        title_overlap: 1.0
    status_summary:
      done: 1
    extracted_component: auth
expected:
  exact: false
  candidates: []
```

Save as `fixtures/duplicate-closed-ignored.yaml`.

- [ ] **Step 6: Write fixture 5 — prior-rejection-structured**

```yaml
description: Trigger phrase near ≥2 task keywords → medium-confidence prior rejection
input:
  task_normalized: service mesh adoption
  scenario: greenfield
  tasknotes:
    matches: []
    status_summary: {}
    extracted_component: service
  notebooklm:
    citations:
      - session: S042
        quote: We decided against service mesh adoption because of operational overhead.
    bootstrap: ""
    session_continue: ""
expected:
  exact: false
  candidates:
    - type: Possible prior rejection
      confidence: medium
      id: S042
```

Save as `fixtures/prior-rejection-structured.yaml`.

- [ ] **Step 7: Write fixture 6 — prior-rejection-false-positive**

```yaml
description: "decided against" in unrelated sentence → no candidate (documents known noise pattern)
input:
  task_normalized: rate limiting
  scenario: greenfield
  tasknotes:
    matches: []
    status_summary: {}
    extracted_component: rate
  notebooklm:
    citations:
      - session: S042
        quote: We decided against the old quarterly planning cadence.
    bootstrap: ""
    session_continue: ""
expected:
  exact: false
  candidates: []
```

Save as `fixtures/prior-rejection-false-positive.yaml`.

- [ ] **Step 8: Write fixture 7 — in-flight-collision-component**

```yaml
description: Shared component + status=in-progress → high-confidence collision
input:
  task_normalized: auth migration
  scenario: greenfield
  tasknotes:
    matches:
      - id: X-006
        title: Auth rework phase 2
        status: in-progress
        component: auth
        work-type: feature
        matched_field: component
        title_overlap: 0.3
    status_summary:
      in-progress: 1
    extracted_component: auth
expected:
  exact: false
  candidates:
    - type: Possible in-flight collision
      confidence: high
      id: X-006
```

Save as `fixtures/in-flight-collision-component.yaml`.

- [ ] **Step 9: Write fixture 8 — stale-context (informational)**

```yaml
description: Fixture-driven sanity check — passing an empty tasknotes lane → Degraded coverage candidate
input:
  task_normalized: any task
  scenario: greenfield
  tasknotes: null
  notebooklm:
    citations: []
    bootstrap: "some content"
    session_continue: ""
  wiki:
    matches: [{title: "X", summary: "y", path: "X.md"}]
expected:
  exact: false
  candidates:
    - type: Degraded coverage
```

Save as `fixtures/stale-context.yaml`. (Note: "Stale context" per spec D3 is a separate informational candidate type not generated purely from lane outputs — it requires an external "last session log age" input. Deferred to a follow-up iteration; this fixture stands in as a coverage-degraded example.)

- [ ] **Step 10: Write fixture 9 — degraded-coverage (wiki empty)**

```yaml
description: Wiki lane returns no matches → Degraded coverage candidate
input:
  task_normalized: orphan task
  scenario: greenfield
  tasknotes:
    matches: []
    status_summary: {open: 1}
    extracted_component: orphan
  notebooklm:
    citations: []
    bootstrap: "content"
    session_continue: ""
  wiki:
    matches: []
expected:
  exact: false
  candidates:
    - type: Degraded coverage
      detail: wiki lane produced no matches
```

Save as `fixtures/degraded-coverage.yaml`.

- [ ] **Step 11: Run all fixture tests**

```bash
pytest skills/ark-context-warmup/scripts/test_fixtures.py -v
```

Expected: 9 fixture tests pass.

- [ ] **Step 12: Commit**

```bash
git add skills/ark-context-warmup/fixtures/ skills/ark-context-warmup/scripts/test_fixtures.py
git commit -m "test(warmup): add 9 evidence-candidate regression fixtures"
```

---

## Phase 8 — Chain Integration

### Task 20: Prepend step 0 to all 7 chain files

**Files:**
- Modify: `skills/ark-workflow/chains/greenfield.md`
- Modify: `skills/ark-workflow/chains/bugfix.md`
- Modify: `skills/ark-workflow/chains/ship.md`
- Modify: `skills/ark-workflow/chains/knowledge-capture.md`
- Modify: `skills/ark-workflow/chains/hygiene.md`
- Modify: `skills/ark-workflow/chains/migration.md`
- Modify: `skills/ark-workflow/chains/performance.md`

Each chain file has multiple weight-class sections (Light / Medium / Heavy / Full / Audit-Only / etc). Every numbered list in every section gets a new step 0 prepended and all subsequent numbers shift down by 1. The first step of each section becomes `0. \`/ark-context-warmup\` — load recent + relevant project context`.

For `handoff_marker` comments referencing step numbers, those numbers also shift.

- [ ] **Step 1: Edit greenfield.md**

For each numbered list in `skills/ark-workflow/chains/greenfield.md` (Light, Medium, Heavy), prepend `0. \`/ark-context-warmup\` — load recent + relevant project context` and increment all subsequent step numbers by 1.

Example — Light section transforms:

```
## Light
1. Implement directly
2. `/cso` (if security-relevant)
...
```

becomes

```
## Light
0. `/ark-context-warmup` — load recent + relevant project context
1. Implement directly
2. `/cso` (if security-relevant)
...
```

Medium's `handoff_marker: after-step-3` becomes `handoff_marker: after-step-4`.
Heavy's `handoff_marker: after-step-5` becomes `handoff_marker: after-step-6`.

- [ ] **Step 2: Edit bugfix.md**

Same transform for Light / Medium / Heavy sections.

- [ ] **Step 3: Edit ship.md**

Same transform. Ship has no handoff markers.

- [ ] **Step 4: Edit knowledge-capture.md**

Same transform for Light / Full sections.

- [ ] **Step 5: Edit hygiene.md**

Same transform for Audit-Only / Light / Medium / Heavy sections.

- [ ] **Step 6: Edit migration.md**

Same transform. Heavy's `handoff_marker: after-step-4` becomes `handoff_marker: after-step-5`.

- [ ] **Step 7: Edit performance.md**

Same transform. Heavy's `handoff_marker: after-step-5` becomes `handoff_marker: after-step-6`.

- [ ] **Step 8: Verify all chain files**

```bash
for f in skills/ark-workflow/chains/*.md; do
    echo "=== $f ==="
    # Every section (## heading) followed by a numbered list should start with "0. "
    python3 -c "
import re
text = open('$f').read()
sections = re.split(r'\n## ', text)[1:]  # skip preamble
for s in sections:
    heading = s.split('\n', 1)[0]
    body = s.split('\n', 1)[1] if '\n' in s else ''
    # Find the first numbered list line
    for line in body.split('\n'):
        m = re.match(r'^(\d+)\.', line.strip())
        if m:
            n = int(m.group(1))
            if n != 0:
                print(f'FAIL section {heading!r}: first step is {n}, expected 0')
            break
"
done
```

Expected: no FAIL lines.

- [ ] **Step 9: Commit**

```bash
git add skills/ark-workflow/chains/*.md
git commit -m "feat(ark-workflow): prepend /ark-context-warmup as step 0 of every chain"
```

---

### Task 21: Chain-file integrity CI check

**Files:**
- Create: `skills/ark-context-warmup/scripts/check_chain_integrity.py`
- Create: `skills/ark-context-warmup/scripts/test_check_chain_integrity.py`

- [ ] **Step 1: Write the failing test**

Create `skills/ark-context-warmup/scripts/test_check_chain_integrity.py`:

```python
"""Test the chain integrity CI check."""
import subprocess
from pathlib import Path

CHECK = Path(__file__).parent / "check_chain_integrity.py"


def test_passes_on_current_repo(tmp_path):
    # Use the actual chain dir
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", "skills/ark-workflow/chains"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"


def test_fails_when_step_0_missing(tmp_path):
    # Write a broken chain
    d = tmp_path / "chains"
    d.mkdir()
    (d / "broken.md").write_text("## Light\n1. first step\n2. second\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "step 0" in r.stderr.lower() or "first step" in r.stderr.lower()


def test_fails_on_handoff_marker_drift(tmp_path):
    d = tmp_path / "chains"
    d.mkdir()
    (d / "drift.md").write_text("## Heavy\nhandoff_marker: after-step-5\n0. warmup\n1. first\n2. second\n3. third\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "handoff_marker" in r.stderr.lower()
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_check_chain_integrity.py -v`
Expected: FAIL (check script not yet written).

- [ ] **Step 3: Write the check**

Create `skills/ark-context-warmup/scripts/check_chain_integrity.py`:

```python
#!/usr/bin/env python3
"""CI check: every chain section starts with `0. /ark-context-warmup`, handoff markers match actual step numbers."""
import argparse
import re
import sys
from pathlib import Path


def check_chain(path: Path) -> list[str]:
    """Return list of error strings (empty if OK)."""
    errors = []
    text = path.read_text()
    sections = re.split(r"\n## ", text)[1:]  # skip preamble
    for s in sections:
        heading = s.split("\n", 1)[0].strip()
        body = s.split("\n", 1)[1] if "\n" in s else ""
        step_numbers = [int(m.group(1)) for m in re.finditer(r"^(\d+)\.", body, re.MULTILINE)]
        if step_numbers and step_numbers[0] != 0:
            errors.append(f"{path.name}:section={heading!r}: first step is {step_numbers[0]}, expected 0 (warmup)")
        # handoff_marker drift: find any 'after-step-N' and verify step N exists in this section
        for m in re.finditer(r"handoff_marker:\s*after-step-(\d+)", body):
            n = int(m.group(1))
            if n not in step_numbers:
                errors.append(f"{path.name}:section={heading!r}: handoff_marker references after-step-{n} but that step doesn't exist in the section")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", required=True, type=Path)
    args = ap.parse_args()
    all_errors: list[str] = []
    for chain in sorted(args.chains.glob("*.md")):
        all_errors.extend(check_chain(chain))
    if all_errors:
        for e in all_errors:
            sys.stderr.write(f"{e}\n")
        return 1
    print(f"OK: {len(list(args.chains.glob('*.md')))} chain files check clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_check_chain_integrity.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/check_chain_integrity.py skills/ark-context-warmup/scripts/test_check_chain_integrity.py
git commit -m "test(warmup): add chain-file integrity CI check"
```

---

### Task 22: Contract-extension integrity CI check

**Files:**
- Create: `skills/ark-context-warmup/scripts/check_contract_extension.py`
- Create: `skills/ark-context-warmup/scripts/test_check_contract_extension.py`

- [ ] **Step 1: Write the failing test**

Create `skills/ark-context-warmup/scripts/test_check_contract_extension.py`:

```python
"""Verify that /ark-workflow's Step 6.5 frontmatter template still contains the four required fields."""
import subprocess
from pathlib import Path

CHECK = Path(__file__).parent / "check_contract_extension.py"


def test_passes_on_current_repo():
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", "skills/ark-workflow/SKILL.md"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"


def test_fails_when_field_missing(tmp_path):
    # Write a SKILL.md without the four fields
    f = tmp_path / "SKILL.md"
    f.write_text("---\n---\n\n### Step 6.5: Activate Continuity\nSome body without the fields.\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--skill", str(f)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "missing" in r.stderr.lower()
```

- [ ] **Step 2: Verify failure**

Run: `pytest skills/ark-context-warmup/scripts/test_check_contract_extension.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the check**

Create `skills/ark-context-warmup/scripts/check_contract_extension.py`:

```python
#!/usr/bin/env python3
"""CI check: /ark-workflow's Step 6.5 includes the four required warmup-contract fields."""
import argparse
import sys
from pathlib import Path

REQUIRED_FIELDS = ["chain_id:", "task_text:", "task_summary:", "task_normalized:", "task_hash:"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, type=Path)
    args = ap.parse_args()
    text = args.skill.read_text()
    # The check is scoped to the Step 6.5 section, which must mention all fields
    if "Step 6.5" not in text and "Activate Continuity" not in text:
        sys.stderr.write(f"{args.skill}: no Step 6.5 / Activate Continuity section found\n")
        return 1
    missing = [f for f in REQUIRED_FIELDS if f not in text]
    if missing:
        sys.stderr.write(f"{args.skill}: missing warmup-contract fields: {missing}\n")
        return 1
    print(f"OK: {args.skill} contains all required warmup-contract fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest skills/ark-context-warmup/scripts/test_check_contract_extension.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/ark-context-warmup/scripts/check_contract_extension.py skills/ark-context-warmup/scripts/test_check_contract_extension.py
git commit -m "test(warmup): add contract-extension integrity CI check"
```

---

## Phase 9 — Distribution

### Task 23: Write manual smoke-test runbook

**Files:**
- Create: `skills/ark-context-warmup/scripts/smoke-test.md`

- [ ] **Step 1: Write the runbook**

Create `skills/ark-context-warmup/scripts/smoke-test.md`:

```markdown
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
- No `.tmp` files left in `.ark-workflow/`

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
```

- [ ] **Step 2: Commit**

```bash
git add skills/ark-context-warmup/scripts/smoke-test.md
git commit -m "docs(warmup): add manual smoke-test runbook"
```

---

### Task 24: Register skill in plugin manifests + update CLAUDE.md

**Files:**
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Read current manifest files**

Run:
```bash
cat .claude-plugin/plugin.json
cat .claude-plugin/marketplace.json
```

- [ ] **Step 2: Add `ark-context-warmup` to plugin.json**

Inside the `skills:` array (or equivalent), add an entry:

```json
{
  "name": "ark-context-warmup",
  "path": "skills/ark-context-warmup",
  "description": "Load recent + relevant project context before any /ark-workflow chain"
}
```

Follow the existing formatting convention visible in the file.

- [ ] **Step 3: Add `ark-context-warmup` to marketplace.json**

Same addition in the marketplace.json skill list.

- [ ] **Step 4: Update CLAUDE.md Available Skills section**

In `CLAUDE.md`, find the `### Workflow Orchestration` or similar section that lists skills. Add a bullet:

```markdown
- `/ark-context-warmup` — Automatic context loader. Runs as step 0 of every /ark-workflow chain; queries NotebookLM + vault + TaskNotes for recent + relevant context. Also invokable standalone.
```

- [ ] **Step 5: JSON lint**

```bash
python3 -c "import json; json.loads(open('.claude-plugin/plugin.json').read())" && echo "plugin.json OK"
python3 -c "import json; json.loads(open('.claude-plugin/marketplace.json').read())" && echo "marketplace.json OK"
```

Expected: both OK.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/ CLAUDE.md
git commit -m "feat(warmup): register /ark-context-warmup in plugin manifests"
```

---

### Task 25: Version bump + CHANGELOG entry

**Files:**
- Modify: `VERSION`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Read current version**

```bash
cat VERSION
head -20 CHANGELOG.md
```

- [ ] **Step 2: Bump minor version in VERSION**

If current is `1.10.1` → bump to `1.11.0` (new feature: new skill + contract extension).

Write the new version to `VERSION` (single line, no trailing text other than newline).

- [ ] **Step 3: Add CHANGELOG entry**

Prepend to `CHANGELOG.md`:

```markdown
## [1.11.0] — 2026-04-12

### Added
- `/ark-context-warmup` skill: automatic context loader that runs as step 0 of every `/ark-workflow` chain. Queries `/notebooklm-vault`, `/wiki-query`, and `/ark-tasknotes` backends in a partial parallel fan-out, synthesizes one Context Brief, surfaces possible duplicates / prior rejections / in-flight collisions as Evidence candidates. Cache keyed on `chain_id + task_hash`, 2-hour TTL, 24-hour pruning. Spec: `docs/superpowers/specs/2026-04-12-ark-context-warmup-design.md`.
- `warmup_contract` YAML blocks in `skills/notebooklm-vault/SKILL.md`, `skills/wiki-query/SKILL.md`, `skills/ark-tasknotes/SKILL.md` describing the machine-readable interface warm-up consumes.
- `skills/ark-workflow/SKILL.md` Step 6.5 now persists four additional frontmatter fields in `.ark-workflow/current-chain.md`: `chain_id`, `task_text`, `task_summary`, `task_normalized`, `task_hash`.

### Changed
- All seven chain files (`skills/ark-workflow/chains/*.md`) prepend `0. /ark-context-warmup` as step 0; subsequent steps renumbered; `handoff_marker` values shifted accordingly in Greenfield Medium/Heavy, Migration Heavy, and Performance Heavy.

### Migration notes
Chains produced by `/ark-workflow` before 1.11.0 (legacy chain files) still work — `/ark-context-warmup` detects missing extended-contract fields, prompts for task text inline, and logs a warning that cache will be cold. Re-run `/ark-workflow` to regenerate `.ark-workflow/current-chain.md` with the new fields.
```

- [ ] **Step 4: Commit**

```bash
git add VERSION CHANGELOG.md
git commit -m "chore: bump version to 1.11.0 for /ark-context-warmup"
```

---

## Self-Review

After completing all tasks, the implementer runs the full test suite:

```bash
pytest skills/ark-context-warmup/scripts/ skills/wiki-query/scripts/ skills/ark-tasknotes/scripts/ -v
bats skills/ark-context-warmup/scripts/integration/*.bats
python3 skills/ark-context-warmup/scripts/check_chain_integrity.py --chains skills/ark-workflow/chains
python3 skills/ark-context-warmup/scripts/check_contract_extension.py --skill skills/ark-workflow/SKILL.md
```

All should pass.

Then run manual smoke tests per `skills/ark-context-warmup/scripts/smoke-test.md`.

## Post-Completion Follow-ups (out of scope for this plan)

1. Relax vault-local lane to parallel if the D4 concurrency probe passes consistently across 20 runs in CI. Needs a separate plan.
2. Add a proper "Stale context" candidate that takes the most-recent-session-log age as an input and emits when >14 days. Currently the evidence generator uses `Degraded coverage` as a stand-in.
3. Add a `/ark-context-warmup status` subcommand that shows cache state, last-run timestamp, backends available — useful for `/ark-health` to consume.
