---
title: "Stage-5 Self-Test Gate Evidence — ark-update v1.14.0 pre-release"
date: 2026-04-14
type: session-log
tags: [ark-update, stage5, self-test, release-gate]
summary: "Complete Stage-5 self-test gate evidence for /ark-update v1.14.0 pre-release. All parts passed."
---

# Stage-5 Self-Test Gate Evidence

**Date:** 2026-04-14  
**Executor:** Claude (Executor agent, Step 10)  
**Branch:** ark-update (tip: confirmed 17 commits)  
**Gate:** MANDATORY — must pass before v1.14.0 release PR  

---

## Part 0: Prerequisites

- Pytest suite: **214 passed in 7.99s** — 100% pass rate
- `python3` 3.9+ with `pyyaml` and `packaging` installed: confirmed
- `--skills-root` pointed to repo root for all engine invocations

---

## Part 1: Fixture Authenticity Check

No git tags exist in this repo (`git tag -l` returned empty). Tags v1.10.1, v1.11.0, v1.12.0 do not exist.
Fixtures inspected visually for structural realism.

### pre-v1.11/CLAUDE.md — Visual Inspection

The fixture represents a minimal project with:
- No vault-layout row in the Project Configuration table
- No `.ark-workflow/` gitignore entry
- No OMC routing block (`omc-routing`)
- No routing-rules block
- No `scripts/setup-vault-symlink.sh`

This accurately represents a pre-v1.11 project shape: the v1.11.0 migration adds
`setup-vault-symlink.sh` and the vault-layout row; a pre-v1.11 project would have
neither. The fixture is trimmed to minimum relevant content; structural realism preserved.

**[OK] pre-v1.11 authentic (visually inspected — no v1.10.x tag exists; structural realism preserved)**

### pre-v1.12/CLAUDE.md — Visual Inspection

The fixture represents a project that received v1.11 conventions:
- Has `Vault layout | centralized` row (added by v1.11 migration)
- Has `scripts/setup-vault-symlink.sh` (added by v1.11 migration)
- Missing routing-rules block (not yet applied)
- Missing OMC routing block
- Missing `.ark-workflow/` gitignore entry

This accurately represents the v1.12 boundary: routing-rules and OMC routing are the
v1.12/v1.13 additions. The fixture correctly omits them.

**[OK] pre-v1.12 authentic (visually inspected — no v1.11.x tag exists; structural realism preserved)**

### pre-v1.13/CLAUDE.md — Visual Inspection

The fixture represents a project that received v1.11+v1.12 conventions:
- Has `Vault layout | centralized` row
- Has `scripts/setup-vault-symlink.sh`
- Has `routing-rules` block at version=1.12.0
- Missing OMC routing block (the v1.13 addition)
- Missing `.ark-workflow/` gitignore entry

This accurately represents the v1.13 boundary: only `omc-routing` and the gitignore
entry remain to be applied.

**[OK] pre-v1.13 authentic (visually inspected — no v1.12.x tag exists; structural realism preserved)**

---

## Part 2: Convergence Runbook

### pre-v1.11

**Setup:** `cp -r fixtures/pre-v1.11 /tmp/stage5-pre-v1.11; rm -rf expected-post/`

**Engine stdout:**
```
ark-update run summary
======================
Phase 1 (destructive migrations): 0 applied, 0 failed
Phase 2 (convergence): 4 applied, 0 drift-overwritten, 0 skipped, 0 failed
```
Exit code: 0. Matches expected: `Phase 2 (convergence): 4 applied, 0 drift-overwritten, 0 skipped, 0 failed` ✓

**Post-state diff:** `diff -rq --exclude='.ark' /tmp/stage5-pre-v1.11 fixtures/pre-v1.11/expected-post/` → exit 0 (byte-exact match) ✓

**.ark/ state:**
```
migrations-applied.jsonl:
{"version":"1.13.0","applied_at":"2026-04-15T01:14:33Z","ops_ran":4,"ops_skipped":0,"failed_ops":[],"result":"clean","phase":"convergence"}

plugin-version: 1.13.0
backups/: empty (total 0) ✓
```

**Result: PASS**

---

### pre-v1.12

**Setup:** `cp -r fixtures/pre-v1.12 /tmp/stage5-pre-v1.12; rm -rf expected-post/`

**Engine stdout:**
```
ark-update run summary
======================
Phase 1 (destructive migrations): 0 applied, 0 failed
Phase 2 (convergence): 3 applied, 0 drift-overwritten, 1 skipped, 0 failed
```
Exit code: 0. Matches expected: `Phase 2 (convergence): 3 applied, 0 drift-overwritten, 1 skipped, 0 failed` ✓

**Post-state diff:** `diff -rq --exclude='.ark' /tmp/stage5-pre-v1.12 fixtures/pre-v1.12/expected-post/` → exit 0 (byte-exact match) ✓

**.ark/ state:**
```
migrations-applied.jsonl:
{"version":"1.13.0","applied_at":"2026-04-15T01:14:34Z","ops_ran":3,"ops_skipped":1,"failed_ops":[],"result":"clean","phase":"convergence"}

plugin-version: 1.13.0
backups/: empty (total 0) ✓
```

**Result: PASS**

---

### pre-v1.13

**Setup:** `cp -r fixtures/pre-v1.13 /tmp/stage5-pre-v1.13; rm -rf expected-post/`

**Engine stdout:**
```
ark-update run summary
======================
Phase 1 (destructive migrations): 0 applied, 0 failed
Phase 2 (convergence): 2 applied, 0 drift-overwritten, 2 skipped, 0 failed
```
Exit code: 0. Matches expected: `Phase 2 (convergence): 2 applied, 0 drift-overwritten, 2 skipped, 0 failed` ✓

**Post-state diff:** `diff -rq --exclude='.ark' /tmp/stage5-pre-v1.13 fixtures/pre-v1.13/expected-post/` → exit 0 (byte-exact match) ✓

**.ark/ state:**
```
migrations-applied.jsonl:
{"version":"1.13.0","applied_at":"2026-04-15T01:14:35Z","ops_ran":2,"ops_skipped":2,"failed_ops":[],"result":"clean","phase":"convergence"}

plugin-version: 1.13.0
backups/: empty (total 0) ✓
```

**Result: PASS**

---

## Part 3: Idempotency Proof — pre-v1.11 Spot-Check

(Action 5 from spec: re-run migrate.py on already-migrated /tmp/stage5-pre-v1.11)

**Second run stdout:**
```
ark-update run summary
======================
clean — nothing to do (all ops idempotent, no pending migrations)
```
Exit code: 0 ✓

**File tree diff before/after second run:** exit 0 (no changes) ✓

**migrations-applied.jsonl line count:** 1 (no new entry appended — clean-run invariant P1-2 holds) ✓

**Result: PASS — clean-run invariant confirmed**

---

## Part 3b: Idempotency Proof — healthy-current Fixture

**Run 1 stdout:**
```
ark-update run summary
======================
clean — nothing to do (all ops idempotent, no pending migrations)
```

**Run 2 stdout:**
```
ark-update run summary
======================
clean — nothing to do (all ops idempotent, no pending migrations)
```

**File tree diff Run 1 → Run 2:** exit 0 (no changes) ✓  
**backups/:** empty ✓

**Result: PASS**

---

## Part 4: Drift Detection Proof — drift-inside-markers Fixture

**Engine stdout:**
```
ark-update run summary
======================
Phase 1 (destructive migrations): 0 applied, 0 failed
Phase 2 (convergence): 0 applied, 2 drift-overwritten, 2 skipped, 0 failed

Drift events:
  drift: omc-routing (backup: /private/tmp/stage5-drift/.ark/backups/CLAUDE.md.omc-routing.20260415T011459Z.bak)
  drift: routing-rules (backup: /private/tmp/stage5-drift/.ark/backups/CLAUDE.md.routing-rules.20260415T011459Z.bak)
```
Exit code: 0 ✓

**backups/ contents:**
```
CLAUDE.md.omc-routing.20260415T011459Z.bak
CLAUDE.md.omc-routing.20260415T011459Z.bak.meta.json
CLAUDE.md.routing-rules.20260415T011459Z.bak
CLAUDE.md.routing-rules.20260415T011459Z.bak.meta.json
```

**meta.json sidecars (all required fields present):**

omc-routing:
```json
{
  "op": "ensure_claude_md_section",
  "region_id": "omc-routing",
  "run_id": "7783df18-4e38-49f5-aaa0-e31ec51bc9f4",
  "pre_hash": "0c4c9f29f3cb8216304e326730e98fb1349e4e8cb7331717b7340a85b6ec9686",
  "reason": "Region content differs from template (user edit or template update)."
}
```

routing-rules:
```json
{
  "op": "ensure_routing_rules_block",
  "region_id": "routing-rules",
  "run_id": "6b808f1b-a751-4d05-9fbe-dcf51f4ffa62",
  "pre_hash": "b259ba1cbf1b0e0d7465ee460c812645d81720ceee1f28b8fc7773b59cedc1e6",
  "reason": "Stale version= in begin-marker: marker has version='1.11.0', target expects '1.12.0'. Content is byte-identical but re-stamp is required (codex P2-3)."
}
```

All required fields present: `op`, `region_id`, `run_id`, `pre_hash`, `reason` ✓

**Result: PASS**

---

## Part 5: Overall Verdict

| Check | Result |
|-------|--------|
| pytest 214 tests | PASS |
| pre-v1.11 fixture authenticity | OK (visual inspection) |
| pre-v1.12 fixture authenticity | OK (visual inspection) |
| pre-v1.13 fixture authenticity | OK (visual inspection) |
| pre-v1.11 convergence (4 applied) | PASS |
| pre-v1.12 convergence (3 applied, 1 skipped) | PASS |
| pre-v1.13 convergence (2 applied, 2 skipped) | PASS |
| All post-state diffs byte-exact | PASS |
| plugin-version = 1.13.0 for all | PASS |
| No backups on non-drift fixtures | PASS |
| Idempotency spot-check (pre-v1.11) | PASS |
| Idempotency (healthy-current, 2 runs) | PASS |
| Drift detection (2 overwrites, 2 backups) | PASS |
| meta.json sidecars all fields present | PASS |

### Stage-5 verdict: **PASS**

All blockers clear. Branch `ark-update` is cleared for Step 11 (codex review + /ark-code-review) and the v1.14.0 release PR.
