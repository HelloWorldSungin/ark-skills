# Ark Workflow Context Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add step-boundary context-budget awareness to `/ark-workflow` via a single Python helper (`context_probe.py`) with six CLI modes that read the Claude Code statusline cache, surface a three-option mitigation menu at chain boundaries, and atomically maintain `.ark-workflow/current-chain.md`.

**Architecture:** All probe logic (threshold math, chain-file parsing, menu rendering, frontmatter mutations, checklist mutations, session/freshness checks) lives in `skills/ark-workflow/scripts/context_probe.py` with stdlib-only imports. SKILL.md invokes the helper and prints stdout — no parsing or rendering in shell. All `.ark-workflow/current-chain.md` mutations go through one shared `chain_file.atomic_update(path, mutator_fn)` helper using `fcntl.flock(LOCK_EX)` + temp-file + `os.replace` to prevent torn writes and lost updates between concurrent frontmatter (record-proceed/record-reset) and checklist (check-off) writes.

**Tech Stack:** Python 3.9+ stdlib (`json`, `pathlib`, `sys`, `argparse`, `os`, `tempfile`, `fcntl`, `re`, `time`, `typing`), pytest, bats, YAML for `target-profile.yaml`.

**Spec reference:** `docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md`

**Revision:** Plan revised after one /ccg review round (2026-04-17). Codex caught two P1 correctness bugs (`_set_proceed_past_level` not block-scalar safe; `record-proceed` destroying suppression on probe failure) and two P2 TDD-discipline drifts (Task 1 stub accepted future kwargs; Task 11 entry-render tests started green because Task 10 implemented the branch). All four are addressed: Task 1 stub is signature-minimal, Task 2/3/4/5 add kwargs in lockstep with their tests, Task 9 includes block-scalar + unknown-preserves regression tests, Task 10 renders only mid-chain so Task 11's tests start red, and Task 14's atomic stress test asserts `proceed_past_level` is one of `{null, nudge}` (no garbage).

---

## File Structure

**New files:**

- `skills/ark-workflow/scripts/context_probe.py` — main helper (~140-170 LOC). Exposes `probe()`, `ProbeResult`, `chain_file.atomic_update()`, six CLI modes.
- `skills/ark-workflow/scripts/test_context_probe.py` — pytest unit tests for `probe()`, threshold math, parse/schema, session/freshness, atomic helper.
- `skills/ark-workflow/scripts/test_step_boundary_render.py` — pytest unit tests for menu assembly against fixture `current-chain.md`.
- `skills/ark-workflow/scripts/fixtures/context-probe/*.json` — ~17 statusline-cache fixtures covering all level/reason cases.
- `skills/ark-workflow/scripts/fixtures/chain-files/*.md` — sample `current-chain.md` files for render tests.
- `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` — bats integration test for all six CLI modes + reset-lifecycle + atomic-write stress.
- `skills/ark-workflow/scripts/smoke-test.md` — manual reactive-probe dry-run runbook.

**Modified files:**

- `skills/ark-workflow/SKILL.md` — Step 6 dual-path: add Path B acceptance probe call. Step 6.5: add chain-entry probe and rewrite "after each step" bullet to call probe + check-off. Add new "Session Habits" section between "When Things Change" and "Routing Rules Template".
- `skills/ark-workflow/references/routing-template.md` — append "### Session habits" subsection.
- `skills/ark-update/templates/routing-template.md` — sync byte-equality with the source above (validator enforces this).
- `skills/ark-update/target-profile.yaml` — bump `routing-rules` entry version: `1.12.0` → `1.17.0`.
- `VERSION` — `1.16.0` → `1.17.0`.
- `.claude-plugin/plugin.json` — `"version": "1.16.0"` → `"1.17.0"`.
- `.claude-plugin/marketplace.json` — `"version": "1.16.0"` → `"1.17.0"`.
- `CHANGELOG.md` — prepend new `## [1.17.0]` section.

---

## Task 1: Bootstrap test scaffold and first OK-level fixture

**Files:**
- Create: `skills/ark-workflow/scripts/__init__.py`
- Create: `skills/ark-workflow/scripts/fixtures/context-probe/ok-fresh.json`
- Create: `skills/ark-workflow/scripts/test_context_probe.py`
- Create: `skills/ark-workflow/scripts/context_probe.py` (stub only)

- [ ] **Step 1.1: Create the empty `__init__.py` so pytest picks up the package**

```bash
mkdir -p skills/ark-workflow/scripts/fixtures/context-probe
mkdir -p skills/ark-workflow/scripts/fixtures/chain-files
mkdir -p skills/ark-workflow/scripts/integration
touch skills/ark-workflow/scripts/__init__.py
```

- [ ] **Step 1.2: Create the OK-level fixture**

Write to `skills/ark-workflow/scripts/fixtures/context-probe/ok-fresh.json`:

```json
{
  "session_id": "test-session-ok-fresh",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "used_percentage": 5,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 100,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

- [ ] **Step 1.3: Write the failing test**

Write to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
"""Tests for context_probe.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_probe as cp  # noqa: E402

FIXTURES = SCRIPTS_DIR / "fixtures" / "context-probe"


class TestProbeLevels:
    def test_ok_fresh(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        assert result["level"] == "ok"
        assert result["pct"] == 5
```

- [ ] **Step 1.4: Create the stub `context_probe.py` so the import resolves but the test still fails**

Write to `skills/ark-workflow/scripts/context_probe.py`:

```python
"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

from pathlib import Path


def probe(state_path):
    raise NotImplementedError
```

**TDD note:** the stub takes only `state_path` (no `**kwargs` placeholder). Each later task that adds an optional argument (Task 2: `nudge_pct`/`strong_pct`; Task 5: `max_age_seconds`/`expected_cwd`/`expected_session_id`) must do so as part of implementing the test that exercises it — keeping every red phase real.

- [ ] **Step 1.5: Run the test to confirm it fails with NotImplementedError**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeLevels::test_ok_fresh -v
```

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 1.6: Implement minimal `probe()` to pass the test**

Replace the body of `skills/ark-workflow/scripts/context_probe.py` with the smallest implementation that handles the OK case only — no thresholds, no kwargs, no error reasons (those land in subsequent tasks):

```python
"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

import json
from pathlib import Path


def probe(state_path):
    """Read Claude Code statusline cache and return a budget recommendation."""
    data = json.loads(Path(state_path).read_text())
    pct = data["context_window"]["used_percentage"]
    return {"level": "ok", "pct": pct, "tokens": None, "warnings": [], "reason": None}
```

- [ ] **Step 1.7: Run the test to verify it passes**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeLevels::test_ok_fresh -v
```

Expected: PASS.

- [ ] **Step 1.8: Commit**

```bash
git add skills/ark-workflow/scripts/__init__.py \
        skills/ark-workflow/scripts/fixtures/context-probe/ok-fresh.json \
        skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): scaffold context_probe.py with ok-level threshold"
```

---

## Task 2: Add full threshold coverage (nudge / strong / over-100 / boundaries)

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/context-probe/{ok-warm,nudge-low,nudge-mid,nudge-high,strong-low,strong-high,over-100}.json`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 2.1: Create the seven additional threshold fixtures**

For each fixture below, write to `skills/ark-workflow/scripts/fixtures/context-probe/<name>.json` using the same skeleton as `ok-fresh.json` with `used_percentage` set as noted. Keep `session_id`, `cwd`, `workspace`, and `current_usage` identical to `ok-fresh.json` unless stated.

| File | `used_percentage` | Expected level |
|------|-------------------|----------------|
| `ok-warm.json` | `19` | `ok` |
| `nudge-low.json` | `20` | `nudge` |
| `nudge-mid.json` | `28` | `nudge` |
| `nudge-high.json` | `34` | `nudge` |
| `strong-low.json` | `35` | `strong` |
| `strong-high.json` | `72` | `strong` |
| `over-100.json` | `105` | `strong` (clamped to 100) |

Example (`nudge-low.json`):

```json
{
  "session_id": "test-session-nudge-low",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "used_percentage": 20,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 100,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

- [ ] **Step 2.2: Add failing tests for all seven thresholds**

Add to `TestProbeLevels` in `skills/ark-workflow/scripts/test_context_probe.py`:

```python
    def test_ok_warm_just_below_nudge(self):
        result = cp.probe(FIXTURES / "ok-warm.json")
        assert result["level"] == "ok"
        assert result["pct"] == 19

    def test_nudge_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "nudge-low.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 20

    def test_nudge_mid(self):
        result = cp.probe(FIXTURES / "nudge-mid.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28

    def test_nudge_high_just_below_strong(self):
        result = cp.probe(FIXTURES / "nudge-high.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 34

    def test_strong_low_inclusive_boundary(self):
        result = cp.probe(FIXTURES / "strong-low.json")
        assert result["level"] == "strong"
        assert result["pct"] == 35

    def test_strong_high(self):
        result = cp.probe(FIXTURES / "strong-high.json")
        assert result["level"] == "strong"
        assert result["pct"] == 72

    def test_over_100_clamped(self):
        result = cp.probe(FIXTURES / "over-100.json")
        assert result["level"] == "strong"
        assert result["pct"] == 100  # clamped

    def test_threshold_overrides(self):
        # Custom thresholds: 10/25 instead of 20/35.
        result = cp.probe(FIXTURES / "nudge-mid.json", nudge_pct=10, strong_pct=25)
        assert result["level"] == "strong"  # 28 >= 25 with custom strong
```

- [ ] **Step 2.3: Run tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeLevels -v
```

Expected: 8 of the 9 tests FAIL — the OK case from Task 1 still passes; the rest fail because the Task 1 stub returns `level: "ok"` unconditionally and doesn't accept `nudge_pct`/`strong_pct` kwargs.

- [ ] **Step 2.4: Add threshold logic + override kwargs to `probe()`**

Replace the body of `probe()` in `skills/ark-workflow/scripts/context_probe.py` with:

```python
def probe(state_path, *, nudge_pct: int = 20, strong_pct: int = 35):
    """Read Claude Code statusline cache and return a budget recommendation."""
    data = json.loads(Path(state_path).read_text())
    pct = data["context_window"]["used_percentage"]
    pct = max(0, min(100, pct))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": None, "warnings": [], "reason": None}
```

- [ ] **Step 2.5: Run the tests to confirm all nine pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeLevels -v
```

Expected: 9 PASSED (1 from Task 1 + 8 new).

- [ ] **Step 2.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/context-probe/*.json \
        skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): probe threshold logic with nudge/strong overrides"
```

---

## Task 3: Add token sum + warnings handling

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/context-probe/{missing-current-usage,non-integer-token}.json`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`
- Modify: `skills/ark-workflow/scripts/context_probe.py`

- [ ] **Step 3.1: Create the two token-edge fixtures**

`skills/ark-workflow/scripts/fixtures/context-probe/missing-current-usage.json`:

```json
{
  "session_id": "test-session-missing-usage",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "used_percentage": 28,
    "context_window_size": 1000000
  }
}
```

`skills/ark-workflow/scripts/fixtures/context-probe/non-integer-token.json`:

```json
{
  "session_id": "test-session-non-int-token",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "used_percentage": 28,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": null,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

- [ ] **Step 3.2: Add failing tests for token computation**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
class TestProbeTokens:
    def test_tokens_summed_when_all_subfields_present(self):
        result = cp.probe(FIXTURES / "ok-fresh.json")
        # 6 + 100 + 1000 + 50000 = 51106
        assert result["tokens"] == 51106
        assert result["warnings"] == []

    def test_tokens_unavailable_when_current_usage_missing(self):
        result = cp.probe(FIXTURES / "missing-current-usage.json")
        assert result["level"] == "nudge"
        assert result["pct"] == 28
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]

    def test_tokens_unavailable_when_subfield_non_integer(self):
        result = cp.probe(FIXTURES / "non-integer-token.json")
        assert result["level"] == "nudge"
        assert result["tokens"] is None
        assert "tokens_unavailable" in result["warnings"]
```

- [ ] **Step 3.3: Run tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeTokens -v
```

Expected: 3 FAIL (tokens currently always None, warnings currently always empty).

- [ ] **Step 3.4: Implement tokens summation in `probe()`**

In `skills/ark-workflow/scripts/context_probe.py`, replace `probe()` with the version below and add the new helper `_sum_tokens` next to it. Threshold and override kwargs from Task 2 are preserved; session/cwd/freshness kwargs are intentionally NOT added yet (Task 5 adds them):

```python
def probe(state_path, *, nudge_pct: int = 20, strong_pct: int = 35):
    """Read Claude Code statusline cache and return a budget recommendation."""
    data = json.loads(Path(state_path).read_text())
    cw = data["context_window"]
    pct = max(0, min(100, cw["used_percentage"]))

    tokens, warnings = _sum_tokens(cw.get("current_usage"))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": tokens, "warnings": warnings, "reason": None}


def _sum_tokens(current_usage):
    """Sum the four token subfields. Return (None, ['tokens_unavailable']) if any is bad."""
    if not isinstance(current_usage, dict):
        return None, ["tokens_unavailable"]
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    total = 0
    for k in keys:
        v = current_usage.get(k)
        if not isinstance(v, int):
            return None, ["tokens_unavailable"]
        total += v
    return total, []
```

- [ ] **Step 3.5: Run all probe tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py -v
```

Expected: 12 PASSED (9 thresholds + 3 tokens).

- [ ] **Step 3.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/context-probe/missing-current-usage.json \
        skills/ark-workflow/scripts/fixtures/context-probe/non-integer-token.json \
        skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): sum context-window tokens with graceful fallback"
```

---

## Task 4: Add parse / schema / filesystem error handling

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/context-probe/{malformed,truncated,missing-field,wrong-type}.json`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`
- Modify: `skills/ark-workflow/scripts/context_probe.py`

- [ ] **Step 4.1: Create the four content-error fixtures**

`malformed.json`:

```
{this is not valid json
```

`truncated.json`:

```
{"session_id": "x", "context_window": {"used_perce
```

`missing-field.json`:

```json
{
  "session_id": "test-missing-field",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 100,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

`wrong-type.json`:

```json
{
  "session_id": "test-wrong-type",
  "cwd": "/tmp/test-project",
  "workspace": {"current_dir": "/tmp/test-project"},
  "context_window": {
    "used_percentage": "twelve",
    "context_window_size": 1000000
  }
}
```

- [ ] **Step 4.2: Add failing tests for parse/schema/filesystem error reasons**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
import os
import stat
import tempfile


class TestProbeErrors:
    def test_malformed_json(self):
        result = cp.probe(FIXTURES / "malformed.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "parse_error"

    def test_truncated_json(self):
        result = cp.probe(FIXTURES / "truncated.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "parse_error"

    def test_missing_used_percentage(self):
        result = cp.probe(FIXTURES / "missing-field.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "schema_mismatch"

    def test_wrong_type_used_percentage(self):
        result = cp.probe(FIXTURES / "wrong-type.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "schema_mismatch"

    def test_missing_file(self, tmp_path):
        result = cp.probe(tmp_path / "does-not-exist.json")
        assert result["level"] == "unknown"
        assert result["reason"] == "file_missing"

    def test_directory_instead_of_file(self, tmp_path):
        result = cp.probe(tmp_path)  # tmp_path is a directory
        assert result["level"] == "unknown"
        assert result["reason"] == "not_a_file"

    def test_permission_denied(self, tmp_path):
        f = tmp_path / "noperm.json"
        f.write_text('{"context_window": {"used_percentage": 5}}')
        original_mode = f.stat().st_mode
        try:
            os.chmod(f, 0)
            result = cp.probe(f)
        finally:
            os.chmod(f, original_mode)
        assert result["level"] == "unknown"
        assert result["reason"] == "permission_error"
```

- [ ] **Step 4.3: Run tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeErrors -v
```

Expected: All FAIL — current implementation returns `parse_error` for missing files / directories / permission denied since they all bubble up as `Exception`.

- [ ] **Step 4.4: Implement reason-code disambiguation**

In `skills/ark-workflow/scripts/context_probe.py`, replace the existing `probe()` function (keep `_sum_tokens` as is) and add the new `_unknown` helper. Signature still excludes session/cwd/freshness kwargs (Task 5 adds those):

```python
def probe(state_path, *, nudge_pct: int = 20, strong_pct: int = 35):
    p = Path(state_path)

    # Filesystem-level checks first.
    if not p.exists():
        return _unknown("file_missing")
    if p.is_dir():
        return _unknown("not_a_file")

    try:
        raw = p.read_text()
    except PermissionError:
        return _unknown("permission_error")
    except OSError:
        return _unknown("permission_error")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _unknown("parse_error")

    cw = data.get("context_window", {})
    pct = cw.get("used_percentage")
    if not isinstance(pct, int):
        return _unknown("schema_mismatch")
    pct = max(0, min(100, pct))

    tokens, warnings = _sum_tokens(cw.get("current_usage"))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": tokens, "warnings": warnings, "reason": None}


def _unknown(reason: str):
    return {"level": "unknown", "pct": None, "tokens": None, "warnings": [], "reason": reason}
```

- [ ] **Step 4.5: Run all probe tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py -v
```

Expected: 19 PASSED.

- [ ] **Step 4.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/context-probe/malformed.json \
        skills/ark-workflow/scripts/fixtures/context-probe/truncated.json \
        skills/ark-workflow/scripts/fixtures/context-probe/missing-field.json \
        skills/ark-workflow/scripts/fixtures/context-probe/wrong-type.json \
        skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): distinct reason codes for probe error cases"
```

---

## Task 5: Add session-id, cwd, and freshness checks

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/context-probe/{cwd-mismatch,workspace-mismatch}.json`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`
- Modify: `skills/ark-workflow/scripts/context_probe.py`

- [ ] **Step 5.1: Create cwd/workspace mismatch fixtures**

`cwd-mismatch.json`:

```json
{
  "session_id": "test-cwd-mismatch",
  "cwd": "/tmp/some-other-project",
  "workspace": {"current_dir": "/tmp/some-other-project"},
  "context_window": {
    "used_percentage": 28,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 100,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

`workspace-mismatch.json` (no top-level `cwd`, only `workspace.current_dir`):

```json
{
  "session_id": "test-workspace-mismatch",
  "workspace": {"current_dir": "/tmp/some-other-project"},
  "context_window": {
    "used_percentage": 28,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 100,
      "cache_creation_input_tokens": 1000,
      "cache_read_input_tokens": 50000
    },
    "context_window_size": 1000000
  }
}
```

- [ ] **Step 5.2: Add failing tests for session/cwd/freshness rejection**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
import time


class TestProbeSession:
    def test_cwd_mismatch(self):
        result = cp.probe(FIXTURES / "cwd-mismatch.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_cwd_match_passes(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "ok"

    def test_workspace_falls_back_when_cwd_absent(self):
        result = cp.probe(FIXTURES / "workspace-mismatch.json", expected_cwd="/tmp/test-project")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_session_id_mismatch(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_session_id="DIFFERENT-SESSION")
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_session_id_match_passes(self):
        result = cp.probe(FIXTURES / "ok-fresh.json", expected_session_id="test-session-ok-fresh")
        assert result["level"] == "ok"

    def test_session_id_check_supersedes_mtime(self, tmp_path):
        # When expected_session_id is provided, mtime check is bypassed.
        f = tmp_path / "fresh.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        os.utime(f, (time.time() - 999999, time.time() - 999999))  # very old
        result = cp.probe(
            f,
            expected_session_id="test-session-ok-fresh",
            max_age_seconds=60,
        )
        assert result["level"] == "ok"  # session match wins

    def test_stale_file_rejected_when_no_session_id(self, tmp_path):
        f = tmp_path / "stale.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        os.utime(f, (time.time() - 999999, time.time() - 999999))
        result = cp.probe(f, max_age_seconds=60)
        assert result["level"] == "unknown"
        assert result["reason"] == "stale_file"

    def test_fresh_file_passes_ttl(self, tmp_path):
        f = tmp_path / "fresh.json"
        f.write_text((FIXTURES / "ok-fresh.json").read_text())
        # mtime defaults to "now" — should pass.
        result = cp.probe(f, max_age_seconds=60)
        assert result["level"] == "ok"
```

- [ ] **Step 5.3: Run tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestProbeSession -v
```

Expected: All FAIL because current `probe()` ignores `expected_cwd` / `expected_session_id` / `max_age_seconds`.

- [ ] **Step 5.4: Implement session/cwd/freshness rejection**

Two changes to `skills/ark-workflow/scripts/context_probe.py`:

**(a)** Add this import at the TOP of the file (immediately after `import json`):

```python
import time
```

**(b)** Replace the entire `probe()` function with the version below. This adds three new keyword-only parameters (`max_age_seconds`, `expected_cwd`, `expected_session_id`) and a session/cwd/freshness check block between JSON parsing and `cw` extraction. The pre-existing `_sum_tokens` and `_unknown` helpers are unchanged:

```python
def probe(
    state_path,
    *,
    nudge_pct: int = 20,
    strong_pct: int = 35,
    max_age_seconds=None,
    expected_cwd=None,
    expected_session_id=None,
):
    p = Path(state_path)

    if not p.exists():
        return _unknown("file_missing")
    if p.is_dir():
        return _unknown("not_a_file")

    try:
        raw = p.read_text()
    except (PermissionError, OSError):
        return _unknown("permission_error")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _unknown("parse_error")

    # Session-id check supersedes everything else when provided.
    cache_session_id = data.get("session_id") or data.get("sessionId")
    if expected_session_id is not None:
        if cache_session_id != expected_session_id:
            return _unknown("session_mismatch")
    else:
        # Mtime-based staleness fallback only when session-id wasn't checked.
        if max_age_seconds is not None:
            try:
                mtime = p.stat().st_mtime
            except OSError:
                return _unknown("permission_error")
            if (time.time() - mtime) > max_age_seconds:
                return _unknown("stale_file")

    # Cwd check (independent of session-id).
    if expected_cwd is not None:
        cache_cwd = data.get("cwd") or data.get("workspace", {}).get("current_dir")
        if cache_cwd != expected_cwd:
            return _unknown("session_mismatch")

    cw = data.get("context_window", {})
    pct = cw.get("used_percentage")
    if not isinstance(pct, int):
        return _unknown("schema_mismatch")
    pct = max(0, min(100, pct))

    tokens, warnings = _sum_tokens(cw.get("current_usage"))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": tokens, "warnings": warnings, "reason": None}
```

- [ ] **Step 5.5: Run all probe tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py -v
```

Expected: 27 PASSED.

- [ ] **Step 5.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/context-probe/cwd-mismatch.json \
        skills/ark-workflow/scripts/fixtures/context-probe/workspace-mismatch.json \
        skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): session-id + cwd + mtime freshness checks"
```

---

## Task 6: Implement `chain_file.atomic_update` helper

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 6.1: Add failing test for the atomic helper**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
class TestAtomicUpdate:
    def test_apply_mutator_writes_result(self, tmp_path):
        f = tmp_path / "chain.md"
        f.write_text("hello")
        cp.chain_file.atomic_update(f, lambda s: s + " world")
        assert f.read_text() == "hello world"

    def test_missing_file_creates(self, tmp_path):
        f = tmp_path / "newchain.md"
        cp.chain_file.atomic_update(f, lambda s: "fresh content")
        assert f.read_text() == "fresh content"

    def test_no_intermediate_state_visible(self, tmp_path):
        # Verify the temp-file-then-rename pattern: the original file is never partially written.
        f = tmp_path / "chain.md"
        f.write_text("initial")

        def slow_mutator(s):
            return s.upper() + "_DONE"

        cp.chain_file.atomic_update(f, slow_mutator)
        assert f.read_text() == "INITIAL_DONE"

    def test_concurrent_updates_serialize(self, tmp_path):
        # Spawn multiple threads doing atomic_update; verify count is exactly N.
        import threading
        f = tmp_path / "counter.md"
        f.write_text("0")

        def increment(_):
            cp.chain_file.atomic_update(f, lambda s: str(int(s.strip()) + 1))

        threads = [threading.Thread(target=increment, args=(None,)) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert int(f.read_text().strip()) == 20
```

- [ ] **Step 6.2: Run tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestAtomicUpdate -v
```

Expected: FAIL — `cp.chain_file` does not exist yet.

- [ ] **Step 6.3: Implement the atomic helper**

Add to the bottom of `skills/ark-workflow/scripts/context_probe.py`:

```python
import os
import tempfile

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


class chain_file:
    """Namespace for atomic chain-file mutations."""

    @staticmethod
    def atomic_update(chain_path, mutator_fn):
        """Read chain_path, apply mutator_fn(text) -> text, write atomically.

        Uses fcntl.flock(LOCK_EX) on a sibling .lock file to serialize concurrent
        read-modify-write sequences (prevents lost updates), plus temp-file +
        os.replace for torn-write protection.

        Falls back to temp-file + rename without locking on platforms lacking fcntl.
        """
        chain_path = Path(chain_path)
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = chain_path.with_suffix(chain_path.suffix + ".lock")

        if _HAS_FCNTL:
            with open(lock_path, "w") as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                try:
                    _do_update(chain_path, mutator_fn)
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        else:
            _do_update(chain_path, mutator_fn)


def _do_update(chain_path: Path, mutator_fn):
    try:
        original = chain_path.read_text()
    except FileNotFoundError:
        original = ""
    new_content = mutator_fn(original)
    fd, tmp_name = tempfile.mkstemp(
        prefix=chain_path.name + ".",
        suffix=".tmp",
        dir=str(chain_path.parent),
    )
    try:
        with os.fdopen(fd, "w") as tmp_f:
            tmp_f.write(new_content)
        os.replace(tmp_name, chain_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
```

- [ ] **Step 6.4: Run all tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py -v
```

Expected: 31 PASSED (27 from earlier + 4 atomic).

- [ ] **Step 6.5: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): atomic chain-file update helper with fcntl lock"
```

---

## Task 7: Add CLI mode 1 (raw)

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 7.1: Add failing test invoking the script via subprocess**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
import subprocess
import json as _json

SCRIPT_PATH = SCRIPTS_DIR / "context_probe.py"


def _run_cli(*args):
    """Run context_probe.py CLI; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["python3", str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestCliRaw:
    def test_raw_ok_fixture(self):
        rc, out, err = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
        )
        assert rc == 0, f"stderr: {err}"
        result = _json.loads(out)
        assert result["level"] == "ok"
        assert result["pct"] == 5

    def test_raw_strong_fixture(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "strong-low.json"),
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["level"] == "strong"

    def test_raw_with_expected_cwd_mismatch(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["level"] == "unknown"
        assert result["reason"] == "session_mismatch"

    def test_raw_missing_file_exits_zero(self):
        rc, out, _ = _run_cli(
            "--format", "raw",
            "--state-path", "/tmp/__definitely_does_not_exist__.json",
        )
        assert rc == 0
        result = _json.loads(out)
        assert result["reason"] == "file_missing"
```

- [ ] **Step 7.2: Run the test to confirm it fails**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliRaw -v
```

Expected: FAIL — no `__main__` / argparse yet.

- [ ] **Step 7.3: Add CLI entry point with the `raw` mode**

Append to `skills/ark-workflow/scripts/context_probe.py`:

```python
import argparse
import sys


def _cmd_raw(args) -> int:
    result = probe(
        Path(args.state_path),
        max_age_seconds=args.max_age_seconds,
        expected_cwd=args.expected_cwd,
        expected_session_id=args.expected_session_id,
    )
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


def _build_parser():
    p = argparse.ArgumentParser(description="Ark Workflow context-budget probe")
    p.add_argument("--format", required=True,
                   choices=["raw", "step-boundary", "path-b-acceptance",
                            "record-proceed", "record-reset", "check-off"])
    p.add_argument("--state-path", default=".omc/state/hud-stdin-cache.json")
    p.add_argument("--chain-path", default=".ark-workflow/current-chain.md")
    p.add_argument("--expected-cwd", default=None)
    p.add_argument("--expected-session-id", default=None)
    p.add_argument("--max-age-seconds", type=int, default=None)
    p.add_argument("--step-index", type=int, default=None,
                   help="1-based step index for --format check-off")
    p.add_argument("--nudge-pct", type=int, default=20)
    p.add_argument("--strong-pct", type=int, default=35)
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.format == "raw":
        return _cmd_raw(args)
    sys.stderr.write(f"format {args.format!r} not implemented\n")
    return 0  # spec: all modes exit 0 even on missing implementation


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7.4: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliRaw -v
```

Expected: 4 PASSED.

- [ ] **Step 7.5: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): context_probe CLI raw mode + argparse skeleton"
```

---

## Task 8: Add CLI mode 6 (check-off)

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 8.1: Add failing tests for check-off behavior**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
SAMPLE_CHAIN = """\
---
scenario: bugfix
weight: medium
chain_id: TEST123
proceed_past_level: null
---
# Current Chain: bugfix-medium
## Steps
- [ ] /ark-context-warmup
- [ ] /investigate
- [ ] Fix
- [ ] /ship
## Notes
"""


class TestCliCheckOff:
    def test_check_off_first_step(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "check-off",
            "--step-index", "1",
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        body = chain.read_text()
        assert "- [x] /ark-context-warmup" in body
        assert "- [ ] /investigate" in body  # untouched

    def test_check_off_third_step(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, _ = _run_cli(
            "--format", "check-off",
            "--step-index", "3",
            "--chain-path", str(chain),
        )
        assert rc == 0
        body = chain.read_text()
        assert "- [x] Fix" in body
        assert "- [ ] /ark-context-warmup" in body
        assert "- [ ] /ship" in body

    def test_check_off_index_zero_no_op(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "check-off",
            "--step-index", "0",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == SAMPLE_CHAIN  # unchanged

    def test_check_off_index_too_large_no_op(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, _ = _run_cli(
            "--format", "check-off",
            "--step-index", "99",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == SAMPLE_CHAIN

    def test_check_off_idempotent_on_already_checked(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        # First check-off
        _run_cli("--format", "check-off", "--step-index", "1", "--chain-path", str(chain))
        first = chain.read_text()
        # Second check-off of the same step
        _run_cli("--format", "check-off", "--step-index", "1", "--chain-path", str(chain))
        assert chain.read_text() == first
```

- [ ] **Step 8.2: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliCheckOff -v
```

Expected: FAIL — `--format check-off` is not implemented.

- [ ] **Step 8.3: Implement check-off via the atomic helper**

In `skills/ark-workflow/scripts/context_probe.py`, add this function above `_build_parser()`:

```python
import re


_CHECKLIST_LINE_RE = re.compile(r"^(- \[)([ x])(\] .*)$", re.MULTILINE)


def _cmd_check_off(args) -> int:
    if args.step_index is None or args.step_index < 1:
        return 0  # silent no-op

    target_index = args.step_index

    def mutator(text: str) -> str:
        lines = text.split("\n")
        count = 0
        for i, line in enumerate(lines):
            m = _CHECKLIST_LINE_RE.match(line)
            if m:
                count += 1
                if count == target_index:
                    if m.group(2) == "x":
                        return text  # already checked, no-op
                    lines[i] = m.group(1) + "x" + m.group(3)
                    return "\n".join(lines)
        # Index too large — silent no-op.
        return text

    chain_file.atomic_update(Path(args.chain_path), mutator)
    return 0
```

In `main()`, add the dispatch line after the `raw` branch:

```python
    if args.format == "check-off":
        return _cmd_check_off(args)
```

- [ ] **Step 8.4: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliCheckOff -v
```

Expected: 5 PASSED.

- [ ] **Step 8.5: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): check-off CLI mode flips Nth checklist item"
```

---

## Task 9: Add CLI modes 4 and 5 (record-proceed, record-reset)

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 9.1: Add failing tests**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
class TestCliRecordProceed:
    def test_record_proceed_at_nudge_writes_nudge(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, _, err = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        assert "proceed_past_level: nudge" in chain.read_text()

    def test_record_proceed_at_strong_writes_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "strong-low.json"),
            "--chain-path", str(chain),
        )
        body = chain.read_text()
        assert "proceed_past_level: null" in body  # strong never silenced

    def test_record_proceed_at_ok_writes_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
            "--chain-path", str(chain),
        )
        assert "proceed_past_level: null" in chain.read_text()

    def test_record_proceed_no_stdout(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        _, out, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert out == ""

    def test_record_proceed_idempotent(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        before = chain.read_text()
        _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert chain.read_text() == before

    def test_record_proceed_unknown_level_preserves_existing(self, tmp_path):
        # Spec: probe failures degrade silently; record-proceed must not
        # destroy existing suppression state when the cache is gone.
        chain = tmp_path / "current-chain.md"
        initial = SAMPLE_CHAIN.replace("proceed_past_level: null",
                                       "proceed_past_level: nudge")
        chain.write_text(initial)
        rc, _, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(tmp_path / "no-such-cache.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert chain.read_text() == initial  # unchanged

    def test_set_proceed_past_level_block_scalar_safe(self, tmp_path):
        # Regression: a chain file whose frontmatter has a block scalar
        # (`task_summary: |-`) with an indented line that literally contains
        # "proceed_past_level:" must NOT have that indented line clobbered.
        chain = tmp_path / "current-chain.md"
        chain.write_text(
            "---\n"
            "scenario: bugfix\n"
            "weight: medium\n"
            "task_summary: |-\n"
            "  Mention proceed_past_level: in user prose — must stay verbatim\n"
            "proceed_past_level: null\n"
            "---\n"
            "## Steps\n"
            "- [ ] /investigate\n"
        )
        rc, _, _ = _run_cli(
            "--format", "record-proceed",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        body = chain.read_text()
        assert "proceed_past_level: nudge" in body
        # The indented block-scalar line must be preserved exactly.
        assert "  Mention proceed_past_level: in user prose — must stay verbatim" in body


class TestCliRecordReset:
    def test_reset_clears_nudge(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, _, _ = _run_cli(
            "--format", "record-reset",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "proceed_past_level: null" in chain.read_text()
        assert "proceed_past_level: nudge" not in chain.read_text()

    def test_reset_idempotent_on_null(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)  # already null
        before = chain.read_text()
        _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert chain.read_text() == before

    def test_reset_no_stdout(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        _, out, _ = _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert out == ""

    def test_reset_preserves_checklist_body(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        body_with_progress = SAMPLE_CHAIN.replace("- [ ] /ark-context-warmup",
                                                  "- [x] /ark-context-warmup") \
                                         .replace("proceed_past_level: null",
                                                  "proceed_past_level: nudge")
        chain.write_text(body_with_progress)
        _run_cli("--format", "record-reset", "--chain-path", str(chain))
        assert "- [x] /ark-context-warmup" in chain.read_text()
```

- [ ] **Step 9.2: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliRecordProceed skills/ark-workflow/scripts/test_context_probe.py::TestCliRecordReset -v
```

Expected: All FAIL — modes not implemented.

- [ ] **Step 9.3: Implement frontmatter mutation + the two CLI modes**

In `skills/ark-workflow/scripts/context_probe.py`, add above `_build_parser()`:

```python
def _set_proceed_past_level(text: str, value: str) -> str:
    """Set proceed_past_level in YAML frontmatter to 'nudge' or 'null'.

    Only matches lines that start at column 0 with `proceed_past_level:` — this
    avoids clobbering an indented content line inside a block scalar (e.g.,
    `task_summary: |-` followed by indented text containing the literal string
    `proceed_past_level:`). Top-level YAML keys never have leading whitespace.

    If the field is missing from the frontmatter, insert it before the closing '---'.
    Operates only on the frontmatter region (text between the first two '---' lines).
    """
    if not text.startswith("---"):
        return text  # no frontmatter; refuse to mutate

    lines = text.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return text  # malformed; refuse

    fm_lines = lines[1:end_idx]
    new_field = f"proceed_past_level: {value}"
    found = False
    for i, line in enumerate(fm_lines):
        # Anchor at column 0 — top-level YAML keys have no leading whitespace.
        # `line.startswith(...)` (NOT `line.strip().startswith(...)`) so that an
        # indented occurrence inside a block scalar like `task_summary: |-` is
        # never matched.
        if line.startswith("proceed_past_level:"):
            fm_lines[i] = new_field
            found = True
            break
    if not found:
        fm_lines.append(new_field)

    return "\n".join([lines[0]] + fm_lines + lines[end_idx:])


def _cmd_record_proceed(args) -> int:
    result = probe(Path(args.state_path),
                   nudge_pct=args.nudge_pct,
                   strong_pct=args.strong_pct)
    # Probe failure (missing/stale/malformed cache) -> silent no-op so existing
    # suppression state is preserved. Spec: probe failures degrade silently.
    if result["level"] == "unknown":
        return 0
    # Strong or ok -> persist null. Only nudge persists "nudge".
    value = "nudge" if result["level"] == "nudge" else "null"
    chain_file.atomic_update(
        Path(args.chain_path),
        lambda text: _set_proceed_past_level(text, value),
    )
    return 0


def _cmd_record_reset(args) -> int:
    chain_file.atomic_update(
        Path(args.chain_path),
        lambda text: _set_proceed_past_level(text, "null"),
    )
    return 0
```

In `main()`, add dispatch lines after the `check-off` branch:

```python
    if args.format == "record-proceed":
        return _cmd_record_proceed(args)
    if args.format == "record-reset":
        return _cmd_record_reset(args)
```

- [ ] **Step 9.4: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliRecordProceed skills/ark-workflow/scripts/test_context_probe.py::TestCliRecordReset -v
```

Expected: 11 PASSED (5 record-proceed core + 1 unknown-preserves + 1 block-scalar + 4 record-reset).

- [ ] **Step 9.5: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): record-proceed / record-reset frontmatter mutators"
```

---

## Task 10: Add menu rendering helpers (mid-chain forward brief)

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md`
- Create: `skills/ark-workflow/scripts/test_step_boundary_render.py`
- Modify: `skills/ark-workflow/scripts/context_probe.py`

- [ ] **Step 10.1: Create the chain fixture (2 of 4 done)**

Write to `skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md`:

```
---
scenario: bugfix
weight: medium
chain_id: FIXTUREMID
proceed_past_level: null
---
# Current Chain: bugfix-medium
## Steps
- [x] /ark-context-warmup
- [x] /investigate
- [ ] /ark-code-review
- [ ] /ship
## Notes
```

- [ ] **Step 10.2: Add failing render test**

Write to `skills/ark-workflow/scripts/test_step_boundary_render.py`:

```python
"""Tests for the menu-rendering helper inside context_probe.py."""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import context_probe as cp  # noqa: E402

CHAIN_FIXTURES = SCRIPTS_DIR / "fixtures" / "chain-files"


class TestMidChainRender:
    def test_render_includes_completed_next_remaining(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge",
            pct=28,
            tokens=200_000,
            chain_text=chain_text,
        )
        assert "Context at 28%" in menu
        assert "(~200k)" in menu
        assert "/ark-context-warmup" in menu  # completed
        assert "/investigate" in menu  # completed
        assert "/ark-code-review" in menu  # next
        assert "/ship" in menu  # remaining
        assert "Resuming bugfix chain (medium)" in menu

    def test_render_strong_level_escalates(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="strong",
            pct=42,
            tokens=420_000,
            chain_text=chain_text,
        )
        assert "Context at 42%" in menu
        assert "attention-rot zone" in menu

    def test_render_offers_three_options(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=28, tokens=200_000, chain_text=chain_text,
        )
        assert "(a) /compact focus on the forward brief" in menu
        assert "(b) /clear" in menu
        assert "(c) Delegate Next step to a subagent" in menu
        assert "[a/b/c/proceed]" in menu

    def test_tokens_unavailable_renders_unknown(self):
        chain_text = (CHAIN_FIXTURES / "midchain-2of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=28, tokens=None, chain_text=chain_text,
        )
        assert "Context at 28%" in menu
        # When tokens unknown, the parenthetical is omitted (no ~k suffix)
        assert "(~" not in menu
```

- [ ] **Step 10.3: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_step_boundary_render.py -v
```

Expected: FAIL — `render_step_boundary_menu` does not exist.

- [ ] **Step 10.4: Implement the chain parser + mid-chain render only**

Add to `skills/ark-workflow/scripts/context_probe.py` (entry-render branch is intentionally OMITTED — Task 11 adds it):

```python
def _parse_chain_file(text: str):
    """Return dict: scenario, weight, completed, next_skill, remaining, all_steps, proceed_past_level."""
    fm = {}
    body = text
    if text.startswith("---"):
        lines = text.split("\n")
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for fl in lines[1:i]:
                    if ":" in fl:
                        k, _, v = fl.partition(":")
                        fm[k.strip()] = v.strip()
                body = "\n".join(lines[i + 1:])
                break

    completed = []
    remaining = []
    all_steps = []
    for line in body.split("\n"):
        m = _CHECKLIST_LINE_RE.match(line)
        if not m:
            continue
        label = m.group(3)[2:].strip()  # everything after "] "
        all_steps.append(label)
        if m.group(2) == "x":
            completed.append(label)
        else:
            remaining.append(label)
    next_skill = remaining[0] if remaining else None
    rest = remaining[1:] if remaining else []
    return {
        "scenario": fm.get("scenario", "unknown"),
        "weight": fm.get("weight", "unknown"),
        "completed": completed,
        "next_skill": next_skill,
        "remaining": rest,
        "all_steps": all_steps,
        "proceed_past_level": fm.get("proceed_past_level", "null"),
    }


def render_step_boundary_menu(*, level: str, pct: int, tokens, chain_text: str) -> str:
    """Render the three-option mitigation menu for mid-chain step boundaries.

    Task 10 only handles the mid-chain case (>=1 [x] step). Task 11 adds the
    zero-completed entry branch.
    """
    info = _parse_chain_file(chain_text)
    return _render_midchain_menu(level=level, pct=pct, tokens=tokens, info=info)


def _format_pct_tokens(pct: int, tokens) -> str:
    if isinstance(tokens, int):
        return f"Context at {pct}% (~{tokens // 1000}k)"
    return f"Context at {pct}%"


def _render_midchain_menu(*, level, pct, tokens, info) -> str:
    completed = ", ".join(info["completed"]) or "(none)"
    remaining = ", ".join(info["remaining"]) or "(none)"
    next_skill = info["next_skill"] or "(unknown)"
    next_step_num = len(info["completed"]) + 1
    scenario = info["scenario"]
    weight = info["weight"]
    pct_tokens = _format_pct_tokens(pct, tokens)

    if level == "strong":
        header = (
            f"⚠ {pct_tokens} — entering the attention-rot zone (~300k+ tokens) "
            f"where reasoning quality degrades. One of (a)/(b)/(c) is strongly "
            f"recommended before continuing."
        )
    else:
        header = f"⚠ {pct_tokens}. Options before continuing to Next:"

    forward_brief = (
        f'  "Resuming {scenario} chain ({weight}). Completed: {completed}.\n'
        f'   Next: step {next_step_num} — {next_skill}. Remaining: {remaining}.\n'
        f'   Key findings so far: <fill in>."'
    )

    return (
        f"{header}\n\n"
        f"Forward brief (auto-assembled from current-chain.md):\n"
        f"{forward_brief}\n\n"
        f"  (a) /compact focus on the forward brief above.\n"
        f"  (b) /clear, then paste the forward brief above as your opening message.\n"
        f"  (c) Delegate Next step to a subagent (keeps this session lean — only the\n"
        f"      subagent's conclusion returns, not its tool output).\n\n"
        f"Which option? [a/b/c/proceed]"
    )
```

- [ ] **Step 10.5: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_step_boundary_render.py -v
```

Expected: 4 PASSED.

- [ ] **Step 10.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md \
        skills/ark-workflow/scripts/test_step_boundary_render.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): mid-chain mitigation-menu rendering"
```

---

## Task 11: Add zero-completed entry menu rendering

**Files:**
- Create: `skills/ark-workflow/scripts/fixtures/chain-files/entry-0of4.md`
- Modify: `skills/ark-workflow/scripts/test_step_boundary_render.py`

- [ ] **Step 11.1: Create the entry-time chain fixture (0 of 4 done)**

Write to `skills/ark-workflow/scripts/fixtures/chain-files/entry-0of4.md`:

```
---
scenario: greenfield
weight: heavy
chain_id: FIXTUREENTRY
proceed_past_level: null
---
# Current Chain: greenfield-heavy
## Steps
- [ ] /ark-context-warmup
- [ ] /brainstorming
- [ ] /writing-plans
- [ ] /executing-plans
## Notes
```

- [ ] **Step 11.2: Add failing entry-render tests**

Append to `skills/ark-workflow/scripts/test_step_boundary_render.py`:

```python
class TestEntryRender:
    def test_zero_completed_uses_entry_template(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=24, tokens=240_000, chain_text=chain_text,
        )
        assert "before chain has started" in menu
        assert "Starting greenfield chain (heavy)" in menu
        assert "/ark-context-warmup" in menu  # in plan list
        assert "/executing-plans" in menu  # in plan list
        # No Completed/Remaining lines in entry rendering
        assert "Completed:" not in menu
        assert "Remaining:" not in menu
        assert "Plan:" in menu

    def test_entry_option_a_unavailable(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="nudge", pct=24, tokens=240_000, chain_text=chain_text,
        )
        assert "(a) /compact — unavailable" in menu
        assert "Which option? [b/c/proceed]" in menu  # constrained answer set

    def test_entry_strong_escalates(self):
        chain_text = (CHAIN_FIXTURES / "entry-0of4.md").read_text()
        menu = cp.render_step_boundary_menu(
            level="strong", pct=42, tokens=420_000, chain_text=chain_text,
        )
        assert "attention-rot zone" in menu
        assert "(b)/(c) is strongly recommended" in menu
```

- [ ] **Step 11.3: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_step_boundary_render.py::TestEntryRender -v
```

Expected: 3 FAIL — Task 10's `render_step_boundary_menu` always routes to `_render_midchain_menu`, so an empty-`completed` chain renders the wrong template (Plan: line absent, "before chain has started" missing).

- [ ] **Step 11.4: Implement the entry-render branch + helper**

Two changes to `skills/ark-workflow/scripts/context_probe.py`:

**(a)** In `render_step_boundary_menu`, add the zero-completed dispatch BEFORE the existing return:

```python
def render_step_boundary_menu(*, level: str, pct: int, tokens, chain_text: str) -> str:
    info = _parse_chain_file(chain_text)
    if not info["completed"] and info["all_steps"]:
        return _render_entry_menu(level=level, pct=pct, tokens=tokens, info=info)
    return _render_midchain_menu(level=level, pct=pct, tokens=tokens, info=info)
```

**(b)** Append the new `_render_entry_menu` helper next to `_render_midchain_menu`:

```python
def _render_entry_menu(*, level, pct, tokens, info) -> str:
    plan = ", ".join(info["all_steps"]) or "(no steps)"
    scenario = info["scenario"]
    weight = info["weight"]
    pct_tokens = _format_pct_tokens(pct, tokens)

    if level == "strong":
        header = (
            f"⚠ {pct_tokens} — entering the attention-rot zone (~300k+ tokens) "
            f"before chain has started. One of (b)/(c) is strongly recommended."
        )
    else:
        header = f"⚠ {pct_tokens} before chain has started."

    forward_brief = (
        f'  "Starting {scenario} chain ({weight}). Plan: {plan}.\n'
        f'   Key context to preserve: <fill in>."'
    )

    return (
        f"{header}\n\n"
        f"Forward brief (auto-assembled):\n"
        f"{forward_brief}\n\n"
        f"  (a) /compact — unavailable (no progress to summarize yet).\n"
        f"  (b) /clear, then paste the forward brief above as your opening message.\n"
        f"  (c) Delegate Step 1 to a subagent (keeps this session lean — only the\n"
        f"      subagent's conclusion returns, not its tool output).\n\n"
        f"Which option? [b/c/proceed]"
    )
```

- [ ] **Step 11.5: Run tests to confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_step_boundary_render.py -v
```

Expected: 7 PASSED (4 mid-chain from Task 10 + 3 entry from Task 11).

- [ ] **Step 11.6: Commit**

```bash
git add skills/ark-workflow/scripts/fixtures/chain-files/entry-0of4.md \
        skills/ark-workflow/scripts/test_step_boundary_render.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): entry-render branch for zero-completed chains"
```

---

## Task 12: Add CLI mode 2 (step-boundary)

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 12.1: Add failing CLI tests**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
class TestCliStepBoundary:
    def test_ok_level_prints_nothing(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_nudge_level_prints_menu(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace(
            "- [ ] /ark-context-warmup", "- [x] /ark-context-warmup"
        ).replace(
            "- [ ] /investigate", "- [x] /investigate"
        ))
        rc, out, err = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0, f"stderr: {err}"
        assert "Context at 28%" in out
        assert "Which option? [a/b/c/proceed]" in out

    def test_nudge_suppressed_by_proceed_past_level(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_strong_not_suppressed_by_proceed_past_level(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN.replace("proceed_past_level: null",
                                              "proceed_past_level: nudge"))
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "strong-low.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "Context at 35%" in out
        assert "attention-rot zone" in out

    def test_zero_completed_uses_entry_render(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)  # all unchecked
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert "before chain has started" in out
        assert "(a) /compact — unavailable" in out

    def test_session_mismatch_silent(self, tmp_path):
        chain = tmp_path / "current-chain.md"
        chain.write_text(SAMPLE_CHAIN)
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
            "--chain-path", str(chain),
        )
        assert rc == 0
        assert out == ""

    def test_missing_chain_file_emits_degraded_menu(self, tmp_path):
        rc, out, _ = _run_cli(
            "--format", "step-boundary",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
            "--chain-path", str(tmp_path / "does-not-exist.md"),
        )
        assert rc == 0
        # Degraded menu still warns at the right level even with no chain context.
        assert "Context at 28%" in out
```

- [ ] **Step 12.2: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliStepBoundary -v
```

Expected: FAIL — step-boundary mode not implemented.

- [ ] **Step 12.3: Implement the step-boundary CLI mode**

Add to `skills/ark-workflow/scripts/context_probe.py`:

```python
def _cmd_step_boundary(args) -> int:
    result = probe(
        Path(args.state_path),
        nudge_pct=args.nudge_pct,
        strong_pct=args.strong_pct,
        max_age_seconds=args.max_age_seconds,
        expected_cwd=args.expected_cwd,
        expected_session_id=args.expected_session_id,
    )
    if result["level"] in ("ok", "unknown"):
        return 0  # silent

    # Read chain file (degraded if missing).
    try:
        chain_text = Path(args.chain_path).read_text()
    except FileNotFoundError:
        chain_text = "---\nscenario: unknown\nweight: unknown\n---\n## Steps\n"
        sys.stderr.write(f"chain file missing: {args.chain_path}\n")
    except Exception as exc:
        chain_text = "---\nscenario: unknown\nweight: unknown\n---\n## Steps\n"
        sys.stderr.write(f"chain file unreadable: {exc}\n")

    # Suppression: if proceed_past_level == 'nudge' and current level is 'nudge', skip.
    info = _parse_chain_file(chain_text)
    if result["level"] == "nudge" and info.get("proceed_past_level") == "nudge":
        return 0

    menu = render_step_boundary_menu(
        level=result["level"],
        pct=result["pct"],
        tokens=result["tokens"],
        chain_text=chain_text,
    )
    sys.stdout.write(menu + "\n")
    return 0
```

In `main()`, add:

```python
    if args.format == "step-boundary":
        return _cmd_step_boundary(args)
```

- [ ] **Step 12.4: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliStepBoundary -v
```

Expected: 7 PASSED.

- [ ] **Step 12.5: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): step-boundary CLI mode with suppression and degraded fallback"
```

---

## Task 13: Add CLI mode 3 (path-b-acceptance)

**Files:**
- Modify: `skills/ark-workflow/scripts/context_probe.py`
- Modify: `skills/ark-workflow/scripts/test_context_probe.py`

- [ ] **Step 13.1: Add failing tests**

Append to `skills/ark-workflow/scripts/test_context_probe.py`:

```python
class TestCliPathBAcceptance:
    def test_ok_level_prints_nothing(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "ok-fresh.json"),
        )
        assert rc == 0
        assert out == ""

    def test_nudge_level_prints_one_line_warning(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "nudge-mid.json"),
        )
        assert rc == 0
        assert "Context at 28%" in out
        assert "Path B" in out
        assert "/clear" in out or "/compact" in out
        # Should be a single line of output (plus terminating newline).
        assert out.count("\n") <= 2

    def test_strong_level_prints_warning(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "strong-low.json"),
        )
        assert rc == 0
        assert "Context at 35%" in out

    def test_session_mismatch_silent(self):
        rc, out, _ = _run_cli(
            "--format", "path-b-acceptance",
            "--state-path", str(FIXTURES / "cwd-mismatch.json"),
            "--expected-cwd", "/tmp/test-project",
        )
        assert rc == 0
        assert out == ""
```

- [ ] **Step 13.2: Run the tests to confirm they fail**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliPathBAcceptance -v
```

Expected: FAIL — mode not implemented.

- [ ] **Step 13.3: Implement the path-b-acceptance CLI mode**

Add to `skills/ark-workflow/scripts/context_probe.py`:

```python
def _cmd_path_b_acceptance(args) -> int:
    result = probe(
        Path(args.state_path),
        nudge_pct=args.nudge_pct,
        strong_pct=args.strong_pct,
        max_age_seconds=args.max_age_seconds,
        expected_cwd=args.expected_cwd,
        expected_session_id=args.expected_session_id,
    )
    if result["level"] in ("ok", "unknown"):
        return 0
    pct = result["pct"]
    tokens = result["tokens"]
    if isinstance(tokens, int):
        suffix = f"(~{tokens // 1000}k)"
    else:
        suffix = ""
    msg = (
        f"⚠ Context at {pct}% {suffix}. Path B adds parent-session coordination "
        f"on top — consider /clear or /compact before accepting."
    ).replace("  ", " ").strip()
    sys.stdout.write(msg + "\n")
    return 0
```

In `main()`, add:

```python
    if args.format == "path-b-acceptance":
        return _cmd_path_b_acceptance(args)
```

- [ ] **Step 13.4: Run the tests; confirm pass**

```bash
python3 -m pytest skills/ark-workflow/scripts/test_context_probe.py::TestCliPathBAcceptance -v
```

Expected: 4 PASSED.

- [ ] **Step 13.5: Run the entire pytest suite to confirm nothing regressed**

```bash
python3 -m pytest skills/ark-workflow/scripts/ -v
```

Expected: All tests pass (~58 total).

- [ ] **Step 13.6: Commit**

```bash
git add skills/ark-workflow/scripts/test_context_probe.py \
        skills/ark-workflow/scripts/context_probe.py
git commit -m "feat(ark-workflow): path-b-acceptance CLI mode"
```

---

## Task 14: Bats integration tests (CLI invocation + reset lifecycle + atomic stress)

**Files:**
- Create: `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats`

- [ ] **Step 14.1: Write the bats integration test file**

Write to `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats`:

```bash
#!/usr/bin/env bats

setup() {
    TMPDIR=$(mktemp -d)
    export TMPDIR
    SCRIPT="skills/ark-workflow/scripts/context_probe.py"
    FIXTURES="skills/ark-workflow/scripts/fixtures/context-probe"
    CHAIN_FIXTURES="skills/ark-workflow/scripts/fixtures/chain-files"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "raw mode: ok fixture prints level=ok" {
    run python3 "$SCRIPT" --format raw --state-path "$FIXTURES/ok-fresh.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"level": "ok"'* ]]
}

@test "step-boundary mode: ok fixture is silent" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/ok-fresh.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "step-boundary mode: nudge fixture renders mid-chain menu" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Context at 28%"* ]]
    [[ "$output" == *"Resuming bugfix chain (medium)"* ]]
    [[ "$output" == *"[a/b/c/proceed]"* ]]
}

@test "step-boundary mode: zero-completed renders entry menu" {
    cp "$CHAIN_FIXTURES/entry-0of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"before chain has started"* ]]
    [[ "$output" == *"(a) /compact — unavailable"* ]]
    [[ "$output" == *"[b/c/proceed]"* ]]
}

@test "step-boundary mode: nudge with proceed_past_level=nudge is silent" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "step-boundary mode: strong fires even when proceed_past_level=nudge" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/strong-low.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"attention-rot zone"* ]]
}

@test "path-b-acceptance: nudge prints one-line warning" {
    run python3 "$SCRIPT" --format path-b-acceptance \
        --state-path "$FIXTURES/nudge-mid.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Context at 28%"* ]]
    [[ "$output" == *"Path B"* ]]
}

@test "path-b-acceptance: ok is silent" {
    run python3 "$SCRIPT" --format path-b-acceptance \
        --state-path "$FIXTURES/ok-fresh.json"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "record-proceed at nudge writes proceed_past_level: nudge" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"
}

@test "record-proceed at strong leaves proceed_past_level: null" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/strong-low.json" \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"
}

@test "record-reset clears proceed_past_level back to null" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"
    ! grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"
}

@test "end-to-end reset lifecycle: nudge -> proceed -> reset -> menu fires again" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"

    # 1. Record-proceed at nudge => proceed_past_level: nudge
    python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"

    # 2. Step-boundary at nudge => suppressed (empty output)
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ -z "$output" ]

    # 3. Record-reset
    python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"

    # 4. Step-boundary at nudge => menu fires again
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [[ "$output" == *"Context at 28%"* ]]
}

@test "atomic write stress: concurrent check-off + record-proceed never corrupts" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"

    # Background loop: rapid check-off / reset cycles for ~2 seconds
    (
        end=$(($(date +%s) + 2))
        while [ "$(date +%s)" -lt "$end" ]; do
            python3 "$SCRIPT" --format check-off --step-index 3 \
                --chain-path "$TMPDIR/current-chain.md"
        done
    ) &
    bg_pid=$!

    # Foreground loop: rapid frontmatter mutations
    end=$(($(date +%s) + 2))
    while [ "$(date +%s)" -lt "$end" ]; do
        python3 "$SCRIPT" --format record-proceed \
            --state-path "$FIXTURES/nudge-mid.json" \
            --chain-path "$TMPDIR/current-chain.md"
        python3 "$SCRIPT" --format record-reset \
            --chain-path "$TMPDIR/current-chain.md"
    done

    wait $bg_pid

    # Final state must still be valid: opens with frontmatter delimiter, has "## Steps".
    head -1 "$TMPDIR/current-chain.md" | grep -q "^---$"
    grep -q "^## Steps$" "$TMPDIR/current-chain.md"
    # proceed_past_level must be in a valid terminal state (null OR nudge — never garbage).
    # Tight regex catches torn writes like "proceed_past_level: nuxxxx".
    [ "$(grep -Ec '^proceed_past_level: (null|nudge)$' "$TMPDIR/current-chain.md")" -eq 1 ]
    # Step 3 was the check-off target — must end checked.
    grep -q "^- \[x\] Fix$" "$TMPDIR/current-chain.md"
}

@test "all six modes exit 0 on missing state file" {
    for fmt in raw step-boundary path-b-acceptance record-proceed; do
        run python3 "$SCRIPT" --format "$fmt" \
            --state-path "$TMPDIR/nope.json" \
            --chain-path "$TMPDIR/current-chain.md"
        [ "$status" -eq 0 ]
    done
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    run python3 "$SCRIPT" --format check-off --step-index 1 \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
}
```

- [ ] **Step 14.2: Verify bats is available, then run the integration suite**

```bash
which bats || brew install bats-core
bats skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats
```

Expected: All ~14 tests PASS. If `bats` is not installed and cannot be installed, document that in the smoke-test runbook (Task 21) and move on.

- [ ] **Step 14.3: Commit**

```bash
git add skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats
git commit -m "test(ark-workflow): bats integration suite for context_probe CLI"
```

---

## Task 15: Update SKILL.md — rewrite "after each step" bullet in Step 6.5

**Files:**
- Modify: `skills/ark-workflow/SKILL.md` (around line 314)

- [ ] **Step 15.1: Replace the existing single-line "after each step" bullet**

In `skills/ark-workflow/SKILL.md`, find this line (around line 314):

```markdown
- After each step: check off the step in the file (`[ ]` → `[x]`), update the TodoWrite task to `completed`, announce `Next: [skill] — [purpose]`, mark next task `in_progress`
```

Replace it with the multi-substep block:

```markdown
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
     - If `(a)` or `(b)`: after `/compact` or `/clear`, invoke `--format record-reset` to explicitly clear `proceed_past_level: null` so the next boundary probes fresh.
     - If `(c)`: no state write; subagent wraps Next step.
     If `$MENU` is empty, proceed silently.
  4. Mark the next TodoWrite task `in_progress`
  5. Announce `Next: [skill] — [purpose]`
```

- [ ] **Step 15.2: Verify the replacement landed in the right place**

```bash
grep -n "Run the step-boundary probe" skills/ark-workflow/SKILL.md
```

Expected: one match in the "After each step" subsection.

- [ ] **Step 15.3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "docs(ark-workflow): wire step-boundary probe into Step 6.5 'after each step'"
```

---

## Task 16: Update SKILL.md — add chain-entry probe + SESSION_ID resolution

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 16.1: Add the SESSION_ID resolution block at the top of Step 6.5**

In `skills/ark-workflow/SKILL.md`, find the Step 6.5 header:

```markdown
### Step 6.5: Activate Continuity
```

Immediately after that header line, insert:

```markdown

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

```

- [ ] **Step 16.2: Verify both blocks landed**

```bash
grep -n "Chain-entry probe" skills/ark-workflow/SKILL.md
grep -n "SESSION_FLAG=" skills/ark-workflow/SKILL.md
```

Expected: one match each.

- [ ] **Step 16.3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "docs(ark-workflow): add chain-entry probe + SESSION_ID resolution to Step 6.5"
```

---

## Task 17: Update SKILL.md — add Path B acceptance probe to Step 6 dual-path

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 17.1: Add the path-b-acceptance probe inside the Step 6 dual-path block**

In `skills/ark-workflow/SKILL.md`, find the recommendation UX block:

```markdown
**Recommendation UX (when any signal fires):**

```
Recommended: Path B (OMC-powered — autonomous execution, ~1–4 hours, ~3 checkpoints)

  [Accept Path B]   [Use Path A]   [Show me both]
```
```

Immediately AFTER that fenced block (and BEFORE the "Include an inline one-line checkpoint-density …" paragraph), insert:

```markdown

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

```

- [ ] **Step 17.2: Verify the block landed**

```bash
grep -n "Path B acceptance probe" skills/ark-workflow/SKILL.md
```

Expected: one match.

- [ ] **Step 17.3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "docs(ark-workflow): add path-b-acceptance probe to Step 6 dual-path"
```

---

## Task 18: Update SKILL.md — add Session Habits section

**Files:**
- Modify: `skills/ark-workflow/SKILL.md`

- [ ] **Step 18.1: Insert the Session Habits section between "When Things Change" and "Routing Rules Template"**

In `skills/ark-workflow/SKILL.md`, find this line:

```markdown
## Routing Rules Template
```

Immediately BEFORE that line, insert:

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

- [ ] **Step 18.2: Verify**

```bash
grep -n "## Session Habits" skills/ark-workflow/SKILL.md
```

Expected: one match, located before `## Routing Rules Template`.

- [ ] **Step 18.3: Commit**

```bash
git add skills/ark-workflow/SKILL.md
git commit -m "docs(ark-workflow): add Session Habits coaching section"
```

---

## Task 19: Update routing-template.md — append "Session habits" subsection

**Files:**
- Modify: `skills/ark-workflow/references/routing-template.md`

- [ ] **Step 19.1: Append the Session habits subsection inside the managed code block**

In `skills/ark-workflow/references/routing-template.md`, find this line (line 44 currently):

```markdown
6. If the chain is complete, move the file to `.ark-workflow/archive/YYYY-MM-DD-[scenario].md`
```

Immediately AFTER that line (still INSIDE the `````markdown ... ````` quintuple-backtick fence), insert:

```markdown

### Session habits

Three habits keep context healthy across long chains:

- **Rewind beats correction.** When a step produces a wrong result, prefer
  `/rewind` (double-Esc) over replying "that didn't work, try X." Rewind drops
  the failed attempt from context; correction stacks it.
- **New task, new session.** When the current chain completes and the next
  task is unrelated, `/clear` and start fresh.
- **`/compact` with a forward brief.** When compacting mid-chain, steer the
  summary: `/compact focus on the auth refactor; drop the test debugging`.
  `/ark-workflow`'s step-boundary probe pre-fills this template from chain
  state when context crosses the nudge or strong threshold.
```

- [ ] **Step 19.2: Verify the subsection is inside the fenced block**

```bash
grep -n "Session habits" skills/ark-workflow/references/routing-template.md
```

Expected: one match.

- [ ] **Step 19.3: Commit**

```bash
git add skills/ark-workflow/references/routing-template.md
git commit -m "docs(ark-workflow): add Session habits subsection to routing-template.md"
```

---

## Task 20: Sync templates/routing-template.md and bump target-profile.yaml version

**Files:**
- Modify: `skills/ark-update/templates/routing-template.md` (sync byte-equality)
- Modify: `skills/ark-update/target-profile.yaml`

- [ ] **Step 20.1: Sync the template byte-for-byte**

```bash
cp skills/ark-workflow/references/routing-template.md \
   skills/ark-update/templates/routing-template.md
```

- [ ] **Step 20.2: Bump the routing-rules version in target-profile.yaml**

In `skills/ark-update/target-profile.yaml`, find:

```yaml
  - id: routing-rules
    op: ensure_routing_rules_block
    file: CLAUDE.md
    since: 1.3.0
    version: 1.12.0
```

Replace the `version: 1.12.0` line with `version: 1.17.0`:

```yaml
  - id: routing-rules
    op: ensure_routing_rules_block
    file: CLAUDE.md
    since: 1.3.0
    version: 1.17.0
```

- [ ] **Step 20.3: Run the validator to confirm byte-equality + structure**

```bash
python3 skills/ark-update/scripts/check_target_profile_valid.py
```

Expected: `OK: target-profile.yaml valid (...)`.

If the validator fails on the `since: 1.17.0` reference (it doesn't yet exist in CHANGELOG.md), note that the `since:` field for routing-rules stays at `1.3.0` (only `version:` bumps). The validator only checks `since:` values — `1.3.0` is already in CHANGELOG so this passes.

- [ ] **Step 20.4: Commit**

```bash
git add skills/ark-update/templates/routing-template.md \
        skills/ark-update/target-profile.yaml
git commit -m "feat(ark-update): bump routing-rules to v1.17.0 with Session habits subsection"
```

---

## Task 21: Add manual smoke-test runbook

**Files:**
- Create: `skills/ark-workflow/scripts/smoke-test.md`

- [ ] **Step 21.1: Write the smoke-test runbook**

Write to `skills/ark-workflow/scripts/smoke-test.md`:

```markdown
# Manual smoke test: context_probe.py

Use this when you want a hands-on sanity check that the probe surfaces the
mitigation menu, suppresses correctly, and resets cleanly.

## Setup

```bash
TMPSTATE=$(mktemp -d)
TMPCHAIN=$(mktemp -d)
cp skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md \
   "$TMPCHAIN/current-chain.md"
```

## 1. Manually craft a "≥35% strong" cache

```bash
cat > "$TMPSTATE/hud-stdin-cache.json" <<EOF
{
  "session_id": "smoke-session",
  "cwd": "$(pwd)",
  "workspace": {"current_dir": "$(pwd)"},
  "context_window": {
    "used_percentage": 42,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 200,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 415000
    },
    "context_window_size": 1000000
  }
}
EOF
```

## 2. Step-boundary probe should render the strong-level menu

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected:
- Header includes `Context at 42%` and `attention-rot zone`.
- Forward brief shows `Resuming bugfix chain (medium)` with the right Completed / Next / Remaining lists.
- Three options shown; answer prompt is `[a/b/c/proceed]`.

## 3. Record-proceed at strong should NOT silence anything

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-proceed \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md"

grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: null` (strong never persists suppression).

## 4. Lower the cache to nudge, record proceed, verify suppression

```bash
sed -i.bak 's/"used_percentage": 42/"used_percentage": 24/' \
  "$TMPSTATE/hud-stdin-cache.json"
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-proceed \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md"
grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: nudge`.

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected: empty output (suppressed).

## 5. Bump back to strong, verify menu fires regardless

```bash
sed -i.bak 's/"used_percentage": 24/"used_percentage": 42/' \
  "$TMPSTATE/hud-stdin-cache.json"
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected: strong-level menu prints (suppression doesn't apply at strong).

## 6. Reset clears suppression

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-reset \
  --chain-path "$TMPCHAIN/current-chain.md"
grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: null`.

## Cleanup

```bash
rm -rf "$TMPSTATE" "$TMPCHAIN"
```

## Notes

- If `bats` is not installed locally, this manual runbook substitutes for the
  integration suite at `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats`.
  Install via `brew install bats-core` to run the automated tests.
- The probe degrades silently when `HAS_OMC=false` (Step 6.5 doesn't invoke it
  in that case). To simulate that path, just don't run the probe.
```

- [ ] **Step 21.2: Verify the runbook is well-formed markdown**

```bash
test -s skills/ark-workflow/scripts/smoke-test.md && echo OK
```

Expected: `OK`.

- [ ] **Step 21.3: Commit**

```bash
git add skills/ark-workflow/scripts/smoke-test.md
git commit -m "docs(ark-workflow): manual smoke-test runbook for context_probe"
```

---

## Task 22: Bump plugin version to v1.17.0 and add CHANGELOG entry

**Files:**
- Modify: `VERSION`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `CHANGELOG.md`

- [ ] **Step 22.1: Bump VERSION**

Replace the contents of `VERSION` with:

```
1.17.0
```

- [ ] **Step 22.2: Bump .claude-plugin/plugin.json**

In `.claude-plugin/plugin.json`, change `"version": "1.16.0"` to `"version": "1.17.0"`.

- [ ] **Step 22.3: Bump .claude-plugin/marketplace.json**

In `.claude-plugin/marketplace.json`, change `"version": "1.16.0"` to `"version": "1.17.0"`.

- [ ] **Step 22.4: Prepend the v1.17.0 CHANGELOG entry**

In `CHANGELOG.md`, immediately AFTER the `# Changelog` header and `All notable changes...` line, BEFORE the `## [1.16.0]` section, insert:

```markdown
## [1.17.0] - 2026-04-17

### Added

- **Context-budget probe in `/ark-workflow`.** New helper `skills/ark-workflow/scripts/context_probe.py` reads the Claude Code statusline cache at `.omc/state/hud-stdin-cache.json` and surfaces a three-option mitigation menu (compact / clear / subagent) at chain entry, each step boundary (Path A only), and Path B acceptance. Six CLI modes: `raw`, `step-boundary`, `path-b-acceptance`, `record-proceed`, `record-reset`, `check-off`. Stdlib only. Thresholds: nudge at 20%, strong at 35% of `context_window.used_percentage`.
- **Atomic chain-file mutation helper.** All `.ark-workflow/current-chain.md` mutations (frontmatter writes via `record-proceed`/`record-reset`, checklist `[ ]` → `[x]` writes via `check-off`) now go through one shared `chain_file.atomic_update(path, mutator_fn)` helper using `fcntl.flock(LOCK_EX)` + temp-file + `os.replace` to prevent torn writes and lost updates between concurrent frontmatter and checklist edits.
- **Nudge-fatigue suppression** via new optional `proceed_past_level` field in `current-chain.md` frontmatter. `record-proceed` self-detects the current level and persists `proceed_past_level: nudge` only when current level is `nudge`; strong-level proceed never persists suppression. Lifecycle is explicit (no inference) — caller invokes `record-reset` after the user takes option (a) `/compact` or (b) `/clear`.
- **Session / freshness rejection layers.** Probe accepts `--expected-cwd`, `--expected-session-id`, and `--max-age-seconds`. Session-id (when resolvable from `$CLAUDE_SESSION_ID` or `.omc/state/hud-state.json`) is the primary check; cwd is the secondary check; mtime-based TTL (300s for entry-time probes) is the tertiary fallback. All session/freshness mismatches degrade to silent no-op via `level: unknown`.
- **"Session Habits" coaching block** in `/ark-workflow` SKILL.md (between "When Things Change" and "Routing Rules Template") and as a "### Session habits" subsection in `references/routing-template.md`. Three habits: rewind-before-correction, new-task-means-new-session, compact-with-forward-brief. Pushed to downstream projects via `/ark-update`.
- **Manual smoke-test runbook** at `skills/ark-workflow/scripts/smoke-test.md` for hands-on validation when bats is not installed.
- **Bats integration suite** at `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` covering all six CLI modes, end-to-end reset lifecycle, atomic-write stress test (concurrent check-off + record-proceed for ~2 seconds), and exit-0-on-missing-state guarantee.

### Changed

- **`/ark-workflow` Step 6.5** "Activate Continuity" now resolves `SESSION_ID` once at the top, runs a chain-entry probe (with `--max-age-seconds 300`) before executing step 1, and replaces the single-line "after each step" bullet with a 5-substep block that calls the atomic `check-off` helper, runs the step-boundary probe, and handles the proceed/reset/(c) decision.
- **`/ark-workflow` Step 6** dual-path presentation now invokes the `path-b-acceptance` probe and renders a one-line warning above the `[Accept Path B]` button when the session is already at nudge or strong level.
- **`/ark-update` `routing-rules` managed region** version bumped from `1.12.0` → `1.17.0` because `references/routing-template.md` gained the Session habits subsection. Downstream projects pull the block via `/ark-update`.

### Degradation contract

- Probe is gated behind `HAS_OMC=true`. When OMC is not installed, Step 6.5 falls back to today's behavior (no menu, no probe call). All probe failure modes (missing file, malformed JSON, schema mismatch, session mismatch, stale file, permission denied) degrade silently to no menu.

### Spec & Plan

- Spec: `docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md`
- Plan: `docs/superpowers/plans/2026-04-17-ark-workflow-context-probe.md`

```

- [ ] **Step 22.5: Run the full test suite once more to confirm nothing regressed**

```bash
python3 -m pytest skills/ark-workflow/scripts/ -v
python3 skills/ark-update/scripts/check_target_profile_valid.py
```

Expected: All pytest tests PASS, validator emits `OK`.

- [ ] **Step 22.6: Commit the version bump and changelog**

```bash
git add VERSION \
        .claude-plugin/plugin.json \
        .claude-plugin/marketplace.json \
        CHANGELOG.md
git commit -m "release: v1.17.0 — ark-workflow context-budget probe"
```

---

## Self-review notes

**Spec coverage:** Each spec section maps to tasks above:

| Spec section | Covered by |
|--------------|-----------|
| Component 1: `context_probe.py` | Tasks 1-13 (probe(), CLI modes, atomic helper, rendering) |
| Component 2: SKILL.md Step 6.5 changes | Tasks 15, 16 |
| Component 2: Step 6 dual-path / Path B acceptance | Task 17 |
| Component 3: Mitigation menu template + Zero-Completed Entry Rendering | Tasks 10, 11 |
| Component 4: Chain file frontmatter `proceed_past_level` lifecycle | Task 9 + Task 12 (suppression integration) |
| Component 5: Session Habits coaching block | Tasks 18, 19 |
| Component 6: `/ark-update` migration version bump | Task 20 |
| Data Contract (used_percentage, current_usage, cwd, workspace, mtime) | Tasks 1-5 |
| Session & Freshness Policy (session-id primary, cwd secondary, TTL tertiary) | Task 5 + Task 16 (SESSION_ID resolution snippet) |
| Edge Cases & Error Handling table (12 rows) | Tasks 4, 5, 12 (degraded chain), 14 (reset lifecycle + atomic stress) |
| Testing Strategy: unit threshold/parse/schema/session/filesystem fixtures | Tasks 2-5 |
| Testing Strategy: integration bats with reset-lifecycle + atomic-stress | Task 14 |
| Testing Strategy: step 6.5 text-generation test | Tasks 10, 11 |
| Testing Strategy: manual smoke test | Task 21 |
| Rollout: plugin version + CHANGELOG | Task 22 |

**Type / signature consistency check:**

- `probe()` signature is identical across all references: `(state_path, *, nudge_pct=20, strong_pct=35, max_age_seconds=None, expected_cwd=None, expected_session_id=None)`.
- `chain_file.atomic_update(path, mutator_fn)` signature stable across record-proceed, record-reset, check-off.
- `render_step_boundary_menu(*, level, pct, tokens, chain_text)` keyword-only signature stable.
- `_parse_chain_file(text)` returns dict with stable keys: `scenario`, `weight`, `completed`, `next_skill`, `remaining`, `all_steps`, `proceed_past_level`.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-17-ark-workflow-context-probe.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
