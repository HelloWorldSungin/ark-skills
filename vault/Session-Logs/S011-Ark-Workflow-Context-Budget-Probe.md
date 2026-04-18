---
title: "Session 11: /ark-workflow Context-Budget Probe (v1.17.0 ship)"
type: session-log
tags:
  - session-log
  - S011
  - skill
  - ark-workflow
  - context-management
  - statusline-cache
  - atomic-writes
  - nudge-suppression
  - session-habits
  - release
summary: "Shipped v1.17.0: stdlib-only context_probe.py with 6 CLI modes + atomic chain-file helper + session habits coaching block. 22 atomic commits on branch context-management, merged via PR #19 as squash commit 8d42bd8. No P1 blockers in final /ccg review; 7 P2 + 4 P3 follow-ups filed."
session: "S011"
status: complete
date: 2026-04-17
prev: "[[S010-Path-B-Uniformity-Refactor]]"
epic: "[[Arkskill-007-context-budget-probe]]"
source-tasks:
  - "[[Arkskill-007-context-budget-probe]]"
  - "[[Arkskill-003-omc-integration]]"
created: 2026-04-17
last-updated: 2026-04-17
---

# Session 11: /ark-workflow Context-Budget Probe (v1.17.0 ship)

## Objective

Implement the step-boundary context-budget probe designed in spec
`docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md` —
a single stdlib-only Python helper that reads the Claude Code statusline
cache and surfaces a three-option mitigation menu at chain boundaries,
preventing long chains from silently pushing the parent session past the
attention-rot zone (~300-400k tokens on a 1M window). Ship as v1.17.0.

## Context

Entry state:
- Spec and plan had already been authored and passed two `/ccg` review
  rounds before implementation (catching two P1 correctness bugs in
  `_set_proceed_past_level` block-scalar handling and `record-proceed`
  suppression-preservation, plus two P2 TDD-discipline drifts — all
  addressed in the plan revision).
- Branch `context-management` held 22 atomic implementation commits
  covering the full plan, with 69/69 pytest + 14/14 bats green and
  `/ark-update` validator passing.
- The session began at the "review → PR → merge" gate, not implementation.

## Work Done

### 1. Final `/ccg` review round

Dispatched Codex (architecture correctness, security/concurrency review
of `context_probe.py` + the bats atomic-stress test, completeness vs the
plan's 22 tasks) and Gemini (SKILL.md readability for a cold pickup,
CHANGELOG entry quality, smoke-test runbook usability) in parallel via
`omc ask`.

Artifacts saved to `.omc/artifacts/ask/`:
- `codex-review-the-architecture-correctness-and-security-concurrency-2026-04-18T04-55-55-371Z.md`
- `gemini-review-documentation-quality-for-ark-skills-v1-17-0-context--2026-04-18T04-52-58-298Z.md`

**Codex verdict: "No P1s found."** Four P2s:
1. `open(lock_path, "w")` at `context_probe.py:117-123` follows symlinks
   and truncates — precreated `.ark-workflow/current-chain.md.lock`
   symlink could clobber arbitrary user-writable file. Fix: `os.open(…
   O_NOFOLLOW)` + `fstat` regular-file check.
2. `_cmd_record_proceed` at `:328-331` re-probes without
   `expected_cwd`/`expected_session_id`/TTL — inconsistent with the
   step-boundary guard (harmless given `level == unknown` preserves
   existing state, but cheap to match).
3. Session-policy drift at `:45-58` — when `--expected-session-id` given
   but cache lacks `session_id/sessionId`, probe returns
   `session_mismatch` immediately instead of falling through to
   cwd → TTL tiers per spec.
4. Checklist parser at `:176-189`, `:359-372` treats every
   `- [ ]`/`- [x]` after frontmatter as a chain step. If `## Notes` ever
   contains checklists, `check-off --step-index N` flips the wrong item.

Two P3s: invalid `--step-index` silent instead of stderr-error per spec;
`isinstance(..., int)` accepts JSON booleans.

**Gemini verdict: "Proceed with ship."** One "P1" flagged (smoke-test
fixture dependency) but re-classified as P2 — smoke-test.md explicitly
states it's a dev fallback and fixtures live alongside it in the repo.
Two P2s: SKILL.md `SESSION_FLAG` used in Step 6 before Step 6.5 defines
it; "pause for user decision" mechanism ambiguous for non-interactive
agents. Two P3s: Session Habits callout weight, CHANGELOG one-liner for
each mode.

### 2. Follow-ups filed

Wrote `docs/superpowers/followups/2026-04-17-ark-workflow-context-probe-review-notes.md`
capturing all P2/P3 items with fix sketches and rationale. Committed
alongside the previously-untracked plan file as `3ecc1c9`
(`docs(followups): record post-ship P2/P3 items from v1.17.0 ccg review`).

### 3. Ship

- `git fetch origin master` — branch already fast-forwardable, no merge
  needed.
- `git push -u origin context-management` — 23 commits pushed.
- `gh pr create --base master --title "feat(ark-workflow): v1.17.0 —
  context-budget probe"` → PR #19, body references spec+plan+followups
  paths, includes the no-P1-blockers posture and the full test plan.

### 4. Land

- `gh pr view 19 --json state,mergeable,mergeStateStatus,statusCheckRollup`
  → `CLEAN`, `MERGEABLE`, no configured CI checks.
- `gh pr merge 19 --squash --delete-branch` — first attempt failed with
  `'master' is already used by worktree at …/projects/ark-skills`
  because `--delete-branch` triggers a local checkout. Second attempt
  (`gh pr merge 19 --squash`) reported "already merged" — the squash-
  merge on GitHub had actually completed before the local-cleanup step
  errored. Verified via `gh pr view 19 --json state,mergedAt,mergeCommit`:
  `state: MERGED`, `mergeCommit.oid: 8d42bd85b3ce18b8fe2327dd5e015e37c93a06c4`
  at 2026-04-18T04:59:34Z.
- Cleaned up the stale remote branch manually:
  `git push origin --delete context-management`.

### 5. Wiki update

Created a new branch `session-log-s011` off the fresh `origin/master` for
vault work (the merged branch was deleted remotely and `/wiki-update`'s
push step needed a live branch). Wrote this log plus the
`Arkskill-007-context-budget-probe` epic plus two compiled-insight pages:

- [[Session-Habits-For-Context-Longevity]] — the rewind/new-session/
  forward-brief triad from the Step 6.5 coaching block, promoted out of
  SKILL.md so vault retrieval can surface it without reading the whole
  skill file.
- [[Atomic-Chain-File-Mutation-Pattern]] — the `fcntl.flock(LOCK_EX)` +
  temp-file + `os.replace` shape, reusable for any stdlib-only atomic
  read-modify-write against a shared markdown file.

Counter bumped 7 → 8. Index regenerated.

## Decisions Made

- **Separate follow-ups file instead of inline TODOs.** The P2/P3 items
  live at `docs/superpowers/followups/…` rather than scattered `# TODO`
  comments in `context_probe.py`, so a future follow-up release can
  work off a single organized document.
- **Merge with `gh` despite local worktree collision.** The
  `--delete-branch` local step errors when master is checked out in a
  sibling worktree, but the server-side squash-merge completed. Verified
  via `gh pr view` before moving on. Cleaned up remote branch manually.
- **Session log written on a new branch off post-merge master**, not
  appended to the merged context-management branch. The merged branch is
  deleted remotely; any further commits on it would be orphaned.

## Issues & Discoveries

- **`gh pr merge --delete-branch` isn't worktree-aware.** When the repo
  has multiple worktrees and the base branch (`master`) is checked out
  in another worktree, the `--delete-branch` flag's local-cleanup step
  fails. The server-side merge still happens; skip `--delete-branch`
  (use `gh pr merge --squash` alone) and clean up the remote branch
  with `git push origin --delete <branch>` as a follow-up.
- **`git ls-files` inside a subdirectory with relative glob.** Running
  `git ls-files | grep "^vault"` from `cwd=vault/` gives zero matches
  because paths are reported relative to cwd. Not a bug — but worth
  flagging because it led to several minutes of false "vault isn't
  tracked" confusion. Use `git ls-files` from repo root or pass an
  absolute path.

## Next Steps

Deferred to a v1.17.x or v1.18.0 follow-up release (see
`docs/superpowers/followups/2026-04-17-ark-workflow-context-probe-review-notes.md`):

1. **P2 hardening pass** — all 7 P2 items in one focused PR. Cheap to
   implement (each is <20 LOC), high-leverage for robustness. Symlink
   hardening (P2-1), session-policy drift (P2-2), and Steps-scoped
   checklist parsing (P2-3) should ship together since they're all
   in `context_probe.py`.
2. **P3 polish pass** — either fold into the P2 release or handle as a
   docs-only PR for P3-3 (Session Habits callout) and P3-4 (CHANGELOG
   mode one-liners).
3. **Observe the probe in the wild.** No telemetry yet. Let the next
   few `/ark-workflow` invocations surface real-world behavior before
   opening the sccope for "better menu text" / "smarter thresholds" /
   "env-var override for thresholds."

Not on the near-term list (intentionally):
- No plan to auto-invoke `/compact` or `/clear` from the probe. The
  spec is firm that the helper only surfaces the menu; the decision
  remains with the user.
- No plan to extend the probe beyond `/ark-workflow` (e.g., into other
  long-running skills). Wait for evidence the pattern is worth
  generalizing.
