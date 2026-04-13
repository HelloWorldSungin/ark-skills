---
title: "Session 6: /ark-context-warmup Ship + Codex Harden (v1.12.0)"
type: session-log
tags:
  - session-log
  - S006
  - skill
  - ark-context-warmup
  - ark-workflow
  - warmup-contract
  - codex-review
  - hardening
  - release
summary: "Shipped /ark-context-warmup as step 0 of every chain. Fixed 13 codex-raised findings across 5 review passes (YAML safety, shell-escape, shel-path resolution, 2-layer interp, availability probes, evidence pipeline, index table parser). Tests 107→143. v1.11.0 → v1.12.0. PR #14."
session: "S006"
status: complete
date: 2026-04-13
prev: "[[S005-Ark-Onboard-Centralized-Vault]]"
epic: "[[Arkskill-002-ark-context-warmup]]"
source-tasks:
  - "[[Arkskill-002-ark-context-warmup]]"
created: 2026-04-13
last-updated: 2026-04-13
---

# Session 6: /ark-context-warmup Ship + Codex Harden (v1.12.0)

## Objective

Ship `/ark-context-warmup` — an automatic context loader that runs as step 0 of every `/ark-workflow` chain — and resolve all P1 findings from successive codex review passes before merging to master.

## Context

Built on the prior 25-commit /ark-context-warmup implementation (commits `f1ffffc` through `d5b5eb8` on branch `ark-workflow-improve`), which landed the spec, plan, helpers, parser, availability probe, evidence generator, synthesizer, executor, 7-chain step 0 insertion, CI integrity checks, smoke-test runbook, and skill registration. Entry state: `/codex review --base master` returned `GATE: FAIL` with 3 P1 + 3 P2 findings.

## Work Done

### Phase 1 — fix the 6 original codex findings (TDD each)

One commit per finding, each with a regression test:

| SHA | Finding | Fix |
|---|---|---|
| `9eac660` | P1 #1 YAML-safe task_summary | Step 6.5 frontmatter uses `\|-` block scalar; test covers `:`, `#`, `\|`, quotes |
| `f0438f6` | P1 #2 notebook_id KeyError | Added `json_path_template: 'notebooks.{key}.id'` to both commands |
| `3e9095e` | P1 #3 template env interp | Extended `resolve_input` with `_TEMPLATE_VAR_RE` matching `{UPPERCASE_VAR}`; pass-through for unknowns |
| `ec3ebfd` | P2 #4 empty required fields | Changed `not extracted.get(f)` → `f not in extracted or extracted[f] is None` |
| `485bd13` | P2 #6 wiki availability | Dropped `_meta/vault-schema.md` check; only `index.md` required |
| `41fa4f6` | P2 #5 py3.9 compat | `from __future__ import annotations` on 4 files; `executor.py` uses `Optional[X]` (@dataclass + spec_from_file_location breaks on Py 3.14 with future annotations — documented) |

### Phase 2 — successive codex passes surfaced new P1s

Codex review does not converge across passes — each run samples different paths. Fixed each new P1 as it surfaced:

| SHA | Pass | New P1 |
|---|---|---|
| `3181982` | 2 | Precondition scripts use paths relative to backend skill dir (were failing when `/ark-context-warmup` ran from project root) |
| `69195a7` | 3 | `substitute_shell_template` now `shlex.quote`s values; 3 backend `shell:` templates drop surrounding quotes |
| `4d500dd` | 4 | Wiki-query's `${WARMUP_SCENARIO_QUERY_TEMPLATE}` → `{WARMUP_SCENARIO_QUERY_TEMPLATE}`; `_interpolate_template` iterates until fixed-point (two-layer indirection) |
| `619d9d9` | 5 | `warmup_scan._parse_index_line` handles table form `\| [[Page.md\|Title]] \| type \| summary \|` (generated Ark vault indices use table form) |

### Phase 3 — P2/P3 batch cleanups

- `fb39327` — cache-brief frontmatter uses `yaml.safe_dump` (same YAML-safety class as Phase 1 P1 #1); apostrophe normalization in rejection-trigger tokenization; config fallback when vault-side `.notebooklm/config.json` is malformed
- `4f44d20` — tasknotes availability keys off `Tasks/` dir existence (not counter file); component extraction follows spec D3 (first `[A-Z][a-zA-Z0-9]+` run in `task_summary`, not first lowercase token); bugfix.md Heavy pivot anchors at step 0; Step 6.5 `ARK_SKILLS_ROOT` snippet matches canonical 3-case resolution
- `7640da7` — pre-landing review finding during /ship: `evidence.py:64` active-status set now includes `backlog` (new `/ark-tasknotes` tasks default to `backlog`, so component hits were being silently dropped)

### Phase 4 — /ship (v1.11.0 → v1.12.0)

- Merged master into branch, resolved CHANGELOG conflict (master shipped v1.11.0 for centralized-vault; this branch bumped to v1.12.0 MINOR)
- Version bump across `VERSION`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Pre-landing review: 1 finding (backlog enum completeness), auto-fixed
- README sync: skill count 17→18, `/ark-health` check count 19→20 (reflects master's v1.11.0)
- PR: https://github.com/HelloWorldSungin/ark-skills/pull/14

**Final state:** 143 tests (from 107 session-start, +36 this session — every codex-raised finding has a regression test). Both CI integrity checks green (`check_chain_integrity.py`, `check_contract_extension.py`).

## Decisions Made

- **One commit per codex finding (TDD).** Every P1/P2/P3 fix got a red-then-green test pair and its own commit. Non-negotiable for bisectability and future learning mining.
- **Stop running codex after pass 5.** Advisor confirmed codex samples different paths per pass and will never converge. Fix P1s as they surface; accept cosmetic/false-positive P2s with explicit justification. Two false positives from pass 5 were verified on this macOS (`sort -V` works on Apple sort 2.3; `dict \| None` in annotations under `from __future__ import annotations` is legal on Python 3.9 per PEP 563).
- **v1.12.0 MINOR bump, not 1.11.1 or 2.0.0.** New skill + 8746 lines is feature-scale; master's concurrent v1.11.0 release meant collision was inevitable; no breaking changes rules out MAJOR.
- **Executor keeps `typing.Optional[X]`, not future annotations.** Combining `from __future__ import annotations` with `@dataclass` breaks on Python 3.14 when the module is loaded via `spec_from_file_location` without registering in `sys.modules` (dataclass internals read `sys.modules[cls.__module__].__dict__`). Documented in a module docstring.
- **Cosmetic P2 deferred**: `synthesize.assemble_brief` dumps the same `notebooklm_out` under both "Where We Left Off" and "Recent Project Activity". Real issue but needs a function-signature refactor to accept structured NotebookLM output (separate fields for session-continue vs bootstrap). Worth a follow-up commit on its own branch.

## Issues & Discoveries

- **Codex reviews don't converge.** Pass 1 found 6. Pass 2 dropped those 6 and found 1 new P1 + 2 new P2s. Pass 3 dropped pass 2's P2s and found 1 new P1 + 2 new P2s. Stochastic sampling by design. Useful to log this as an operational learning — see `~/.gstack/` learnings.
- **`@dataclass` + `from __future__ import annotations` + `spec_from_file_location` = Python 3.14 bug.** Caused an `AttributeError: 'NoneType' object has no attribute '__dict__'` when running the test suite after the initial py3.9 compat fix. Dataclass's `_is_type` helper reads `sys.modules.get(cls.__module__).__dict__` which returns None when the module isn't registered. Workaround: keep `typing.Optional[X]` in executor.py, future annotations elsewhere.
- **Shell escaping P1 was contract-convention change, not just code fix.** Needed `shlex.quote` in executor AND removal of `"{{placeholder}}"` surrounding quotes in 3 backend SKILL.md templates. Broke an existing end-to-end test that embedded the old convention.
- **False positive from codex: `sort -V` on macOS.** Apple sort 2.3 (shipped on current macOS) does support `-V`. Verified directly: `printf 'S10.md\nS2.md\nS1.md\n' | sort -V` works. Dismissed with evidence.
- **False positive from codex: `dict | None` on Python 3.9.** PEP 563's `from __future__ import annotations` stringifies annotations; they never evaluate on 3.9. `ast.parse()` + `compile()` both succeed. Dismissed with evidence.

## Next Steps

Follow-up work not in scope for v1.12.0:

1. **Refactor `synthesize.assemble_brief` signature** to accept structured NotebookLM output (separate fields for session-continue shapes — `epic_progress`, `immediate_next_steps`, `where_we_left_off`, `critical_context` — vs bootstrap — `recent_sessions`, `current_state`, `open_issues`). Each heading gets its canonical field instead of the same string duplicated.
2. **Wire `/ark-context-warmup` Step 4 to export `WARMUP_SCENARIO_QUERY_TEMPLATE`** before dispatching the wiki subagent. Prose-level documentation added in this session, but no mechanical test yet. Add a smoke-test case that exercises a real scenario-query dispatch.
3. **Bats integration tests.** Committed in `7c1549c` but `bats-core` installation was deferred. Add to CI.
4. **Smoke-test runbook drill.** `skills/ark-context-warmup/scripts/smoke-test.md` has 9 manual test cases; none have been run end-to-end against a real NotebookLM + vault. Schedule a drill before broad rollout.
5. **Gate codex reviews to P1-only mode for repeat passes.** Current behavior finds new P2/P3s on every pass. For maintenance reviews, `codex review --p1-only` or equivalent would converge.
