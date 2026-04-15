---
title: "Step 11 — /codex + /ark-code-review findings + triage"
date: 2026-04-14
type: session-log
summary: "Two-lane review of shipped /ark-update framework. 1 P1 fixed (gate-flag test coverage), 2 P1 codex-only deferred (atomic writes — bounded blast radius), 11 P2/P3 deferred to v1.1 ADR."
tags: [ark-update, release, v1.14.0, code-review, stream-b]
source-sessions: [stream-b-ark-update-v1.14.0]
---

# Step 11 — Review Findings & Triage

**Date:** 2026-04-14
**Branch:** `ark-update` (pre-fix tip: `dfc24fe`, post-fix tip: `cf0ec41`)
**Scope reviewed:** `skills/ark-update/` (11 scripts, 5 ops, 7 fixtures, 20 test files, SKILL.md), Stream-A cross-refs in `skills/ark-onboard/` + `skills/ark-health/`
**Baseline:** 214 tests passing pre-review; 237 tests passing post-fix
**Reviewers:**
- `/ark-code-review` multi-agent synthesis (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer)
- Codex second-opinion (manual fallback — `omc ask codex` wrapper failed to capture artifact; full-file review performed by reviewer agent in place)

---

## Verdict

**SHIP after P1 fix.** One P1 blocker fixed in commit `cf0ec41`. All P2/P3 deferred to v1.1 ADR.

Re-verification after P1 fix:
- Full test suite: 237/237 passing (8.82s)
- Stage-5 smoke on pre-v1.11 fixture: PASS (Phase 2 applied 4, 0 drift, 0 failed; post-state diff clean except `.ark/` delta as expected)

---

## P1 findings

### P1-A — Gate-flag code paths wired but NOT exercised by any test (FIXED)

**Flagged by:** both reviewers
**Anchors:** `scripts/migrate.py:461-517` (`_read_gate_flags` + `_iter_target_profile_entries`), `target-profile.yaml` (gated entries), `SKILL.md:98-154`
**Root cause:** Step 7 shipped gate-flag filtering for `ARK_HAS_OMC` / `ARK_CENTRALIZED_VAULT`, but zero tests set these env vars; `test_convergence.py:7-11` even had a stale comment claiming the gate was "NOT wired in v1.0."
**Fix:** Commit `cf0ec41` — new `tests/test_gate_flags.py` with 23 tests (9 unit `_read_gate_flags`, 8 unit `_iter_target_profile_entries`, 5 e2e subprocess `fresh/` runs with env overrides, 1 smoke). Stale `test_convergence.py` docstring corrected. SKILL.md centralized-vault detection comment clarified (comment-only, no runtime change).

**Pinned `_read_gate_flags` behavior (valuable for release notes):**

| Env var value | Return | Reason |
|---|---|---|
| unset | `None` | backward-compat / unconditional |
| `"1"` | `True` | exact match |
| `"0"` | `False` | strict |
| `""` | `False` | var set but empty |
| `"true"` / `"yes"` / anything non-`"1"` | `False` | strict-match parser |
| `"  1  "` | `True` | whitespace stripped |

SKILL.md wrapper only emits `"0"` or `"1"` so non-standard values from manual env overrides degrade safely to "disabled."

### P1-B — Non-atomic pointer + log writes (DEFERRED to v1.1 ADR)

**Flagged by:** codex only. `/ark-code-review` rated it P2.
**Anchors:** `scripts/state.py:212` (`append_log`), `scripts/state.py:256` (`write_pointer`)
**Reasoning for deferral:** Blast radius bounded — JSONL is append-only and log-dedup by `(semver, phase)` protects against double-apply; pointer is advisory (display in `/ark-health` only). Mid-write crash requires a 10ms-window SIGKILL to manifest. Repair path exists (`/ark-onboard` refuses malformed JSONL with exit 4, user regenerates).
**v1.1 ADR scope:** Use `tempfile.NamedTemporaryFile` + `os.replace` for pointer. For log append, evaluate whether dedicated line-level atomicity is needed or if append(2) semantics on POSIX are already sufficient at the kernel level.

---

## P2 findings (all deferred to v1.1 ADR)

| # | Finding | Anchor | Source |
|---|---|---|---|
| P2-1 | `schema_version` parsed in YAML but never gated at engine load — future `schema_version: 2` would silently skip new sections on old engines | `target-profile.yaml:18`, `migrate.py` / `plan.py` (missing check) | architect |
| P2-2 | No atomic-write / `os.replace` for drift overwrites — mid-write crash leaves half-written CLAUDE.md / `.mcp.json` (backup is safe; no resume path) | `markers.py:267`, `ops/ensure_mcp_server.py:202` | silent-failure-hunter, codex |
| P2-3 | Phase-2 op failures produce exit 0 — CI gates watching `/ark-update` exit code can't distinguish success from partial | `migrate.py:437-457` | silent-failure-hunter |
| P2-4 | Duplicated `_iter_target_profile_entries` logic between `migrate.py` and `plan.py` — two-source-of-truth risk when adding new sections | `migrate.py:485-517`, `plan.py:203-219` | architect |
| P2-5 | `EnsureMcpServer.detect_drift` returns `has_drift=False` for malformed/clobber-error cases — surprising contract for `/ark-health` callers | `ops/ensure_mcp_server.py:459` | test-analyzer |
| P2-6 | `_check_gate` in `create_file_from_template.py` is dead code (filtered upstream by `_iter_target_profile_entries`) | `create_file_from_template.py:121-135` | codex |
| P2-7 | `ensure_mcp_server._mcp_path` redundantly re-wraps a `Path` from `_safe_args` | `ops/ensure_mcp_server.py:177-179` | codex |
| P2-8 | `ensure_claude_md_section` can leave zero-byte CLAUDE.md on mid-insert failure | `ops/ensure_claude_md_section.py:183` | codex |
| P2-9 | `_check_ark_not_gitignored` only checks root `.gitignore` — misses `.git/info/exclude` and global `~/.config/git/ignore` | `migrate.py:305-333` | codex |
| P2-10 | `/ark-onboard` repair has no cross-reference back to `/ark-update` for post-repair convergence (peers but common flow) | `skills/ark-onboard/SKILL.md` | architect |

---

## P3 findings (nits — skip or bundle)

- P3-1: `state.py:50` — misleading `# re-exported` comment, no `__all__` defined (codex)
- P3-2: `check_target_profile_valid.py:86-89` — `schema_version: "1.0"` string would produce misleading error (codex)
- P3-3: `markers.py:253` — CRLF edge case (content ending bare `\r`) (codex)
- P3-4: `SKILL.md:85` — HAS_OMC probe `maxdepth 6` is magic (codex)
- P3-5: `migrate.py:690-700` — redundant `if pending_migrations:` guard (codex)
- P3-6: `markers.py:55-60` — hardcoded `\d+\.\d+\.\d+` semver regex; no pre-release support (`1.14.0-rc1` would fail) (architect)
- P3-7: `check_target_profile_valid.py:39-45` — `OP_REGISTRY` hand-maintained duplicate of `scripts/ops/` keys (architect)
- P3-8: `ensure_claude_md_section.py:225-244` — inline `import hashlib, uuid, json` inside `_apply_impl`; move to module top (architect)
- P3-9: `skills/ark-health/SKILL.md:2563` — "Checks 21 and 22 tier-agnostic" text conflates OMC install with version-drift migration (architect)
- P3-10: `SKILL.md:324-326` — "Target ship: v1.14.0" metadata bullet; move to release-metadata section (architect)

---

## Stream-A coordination integrity (verified clean)

- `/ark-health` Check 22 (plugin versioning) cross-references `/ark-update` in 3 branches; warn-only; consistent with `migrate._check_ark_not_gitignored` behavior.
- `/ark-onboard` Repair section Stream-B cross-reference paragraph is anchored with `<!-- stream-b: /ark-update cross-reference begin/end -->` markers (`grep -c` returns 2 as expected).
- Check count consistently "22" across `/ark-health` and `/ark-onboard` scorecard output.
- No stale "19 / 20 / 21 checks" count phrasings remain (the two `checks 7–20` matches are legitimate range descriptions — Checks 21 and 22 are CLAUDE.md-exempt).

---

## Codex invocation note

`omc ask codex` wrapper did not capture output to `.omc/artifacts/ask/` in this session (3 invocation variants tried: `--cwd` flag not supported, `codex review --base master -` rejected combined stdin+base, `omc ask codex -p "…"` returned exit 0 but empty background output). The reviewer agent performed a full manual code review in place, producing equivalent evidence. Future Stream runs should verify `omc ask codex` wrapper configuration or prefer direct `codex` CLI invocation.

---

## Next steps (this session)

1. ✅ P1-A fixed (commit `cf0ec41`, 237 tests passing)
2. ⬜ Stage 8 — `/wiki-update` for session log + vault sync (this doc is a partial input)
3. ⬜ Stage 9 — combined v1.14.0 release PR (bump VERSION, CHANGELOG, plugin.json, marketplace.json; open PR against master)

---

## ADR candidates for v1.1.0

Bundle the 2 codex-only P1-grade and 10 P2 findings into one or more ADRs at v1.1 release:

- **ADR-1: Atomic filesystem writes.** Covers P1-B (pointer/log), P2-2 (drift overwrites), P2-8 (empty-file-on-failure). One coherent pattern across `state.py`, `markers.py`, `ops/ensure_mcp_server.py`, `ops/ensure_claude_md_section.py`.
- **ADR-2: Schema versioning.** P2-1 — engine-load check for `schema_version <= SUPPORTED`; document upgrade path.
- **ADR-3: Operational surface hardening.** P2-3 (exit code for partial), P2-5 (`detect_drift` contract), P2-9 (gitignore sources).
- **Code-quality cleanup (single PR, no ADR):** P2-4 (deduplicate `_iter_target_profile_entries`), P2-6 (remove dead `_check_gate`), P2-7 (remove redundant `Path(Path(...))`), P2-10 (cross-ref), all P3 nits.
