---
title: "Session 16: ark-skill-healer tracked rebuild — deep-interview→consensus→ralph, + S015 fix fold-in"
type: session-log
tags:
  - session-log
  - S016
  - ark-skill-healer
  - upstream-watch
  - deep-interview
  - consensus
  - ralph
summary: "Rebuilt the (lost, untracked) ark-skill-healer via deep-interview→omc-plan consensus→ralph. Consensus caught a false .claude/skills discovery path + the mempalace dual-upstream bug pre-execution. Discovered S015 had already run an untracked copy; folded its two methodology fixes (binary install-lag, fork-vs-PyPI authority) back in before committing/tracking. 28-test bats suite green."
session: "S016"
status: complete
date: 2026-06-05
prev: "[[S015-Ark-Skill-Healer-Run-Mempalace-Fork-vs-PyPI]]"
epic: ""
source-sessions: []
source-tasks: []
created: 2026-06-05
last-updated: 2026-06-05
---

# Session 16: ark-skill-healer tracked rebuild + S015 fix fold-in

## Objective
Build `ark-skill-healer` through the full gated pipeline (deep-interview → omc-plan
consensus → ralph), then commit/track it so it stops getting lost as an untracked
skill.

## Context
Follows [[S015-Ark-Skill-Healer-Run-Mempalace-Fork-vs-PyPI]]. **Key discovery mid-session:**
S015 had already built and *run* `ark-skill-healer` — but it lived **untracked** at
`.claude/skills/ark-skill-healer/` and was lost (git history shows it was never
committed). This session rebuilt it from scratch (the pipeline was blind to S015's
prior art), then reconciled against the S015 session log before committing — the whole
point of committing now is to stop the loss.

## Work Done

### 1. Gated pipeline build
- **deep-interview** (9 rounds + topology gate, ambiguity 16.5% ≤ 20%) → spec
  `.omc/specs/deep-interview-ark-skill-healer.md`. 6 confirmed components incl. the
  user-added "did upstream fix our workaround?" retirement check.
- **omc-plan consensus** (Architect SOUND-WITH-CHANGES → Critic REJECTED → revise →
  APPROVED-WITH-NITS) → plan `.omc/plans/ark-skill-healer-consensus.md`. Option C
  (hybrid: deterministic bash collectors + LLM judgment).
- **ralph** → 6 PRD stories, architect-verified, 23-test bats suite. Then +S015 fixes → 28 tests.

### 2. Consensus caught two real pre-execution defects
- **False discovery path:** plan assumed `.claude/skills/<name>/SKILL.md` auto-loads,
  citing a nonexistent `.claude/skills/omc-reference/`. Truth: no `.claude/skills/` dir
  existed; the loaded `omc-reference` is the *plugin* skill. Fix: invoke via a
  first-class `.claude/commands/ark-skill-healer.md` shim, not auto-load.
- **mempalace dual-upstream bug:** plan treated mempalace as one dep; it is two —
  `mempalace-plugin` (milla-jovovich fork clone) vs `mempalace-cli` (MemPalace/mempalace
  PyPI). The #1457/#976/#1322 signals live on the CLI. Shipping the single-dep version
  would have watched the wrong changelog.

### 3. Architecture (Option C)
Deterministic collectors (`collect_inventory`, `collect_upstream`, `lib_state`,
`seed_workarounds`) emit JSON-Lines per a versioned contract; the SKILL.md LLM layer
does impact/opportunity/workaround judgment + staged patches. Advisory-only as a
**structural invariant** — entire run-write surface is the gitignored `.omc/skill-healer/`.
Per-tier snapshot hashing keyed on `source_tier` (tier-downgrade ⇒ quiet, not a finding).
Cascade is **upstream-tip aware** (guarded `git fetch` → remote-tracking ref) so a
finding fires when upstream moves ahead of the install, not only on local pull.

### 4. Folded in the two S015 methodology fixes (before committing)
- **GAP-1 binary install-lag** (S015: gstack reported quiet while 22 releases behind):
  added an `install_lag` check in `collect_upstream.sh` that, for non-commit-capable
  deps with a known installed version, compares installed vs authoritative upstream
  latest (PyPI for `mempalace-cli`, gated on `dep_type=python` to avoid the gstack→PyPI
  `gstack` collision; `gh release` fallback). Network-guarded; hermetic test hook
  `SKILL_HEALER_FAKE_LATEST_<DEP>` + `SKILL_HEALER_DISABLE_INSTALL_LAG` keeps AC5 tests
  deterministic. Live validation: it correctly flags `mempalace-cli` installed `3.3.5`
  < PyPI latest **`3.4.0`** (PyPI moved past 3.3.5 since S015).
- **GAP-2 fork-vs-PyPI authority guardrail** (S015: fork changelog `3.3.6` caused a
  wrong floor-bump + wrong #1457 retire): added explicit guardrails to
  `source-map.md` (mempalace-plugin is a FORK ahead of PyPI, NOT version-authoritative)
  and `SKILL.md` Steps 3 & 5 (a fork-changelog version claim must cross-check the PyPI
  release tier before any pin-bump; a *closed* GitHub issue ≠ a *shipped* fix —
  retire only when published to PyPI AND installed).

## Decisions Made
- **Commit the skill to track it.** It was lost because it was untracked; tracking it
  in-repo (under the project's own `.claude/`, not the distributed `skills/`) is the fix.
  Project-level skill — not shipped to downstream plugin users.
- **Pipeline value confirmed:** the consensus loop caught two defects (dead install path,
  wrong-changelog) that would have wasted real execution cycles. Worth the cost for
  net-new skills.
- **install-lag authority = PyPI for mempalace-cli**, never the fork changelog. Reuses
  the S015 lesson structurally (in code + docs), not just in memory.

## Open Questions
- Is **superpowers** a genuine runtime integration dep, or just doc-folder history?
  Resolving this decides whether it belongs in the tracked set at all.
- **chromadb** is treated as a mempalace-transitive pin; revisit explicit tracking if
  pin drift recurs.
- **gstack install-lag** stays unresolved (no release tags upstream; changelog-remote
  only) — documented v1 limitation, not yet a version comparison.
- **mempalace-cli 3.3.5 → 3.4.0** is a real live finding surfaced by GAP-1 — a CLI
  upgrade to evaluate in a follow-up (check #1457 fix status on 3.4.0 / PyPI before any
  workaround-retire, per the S015 rule).

## Next Steps
1. (this session) commit + push + /ship the tracked skill.
2. Run a real `/ark-skill-healer` pass now that install-lag is wired — triage the
   mempalace-cli 3.3.5→3.4.0 finding and re-check #1457's PyPI status.
3. Resolve the superpowers integration-dep question.
4. Consider a gstack install-lag path (version compare against the remote CHANGELOG header).
