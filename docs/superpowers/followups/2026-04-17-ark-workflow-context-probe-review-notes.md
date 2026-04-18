# Context-probe post-ship follow-ups (v1.17.0)

Non-blocking findings from the final /ccg review round. P1-less ship approved; these are P2/P3 items filed for a follow-up release.

**Source reviews:**
- `.omc/artifacts/ask/codex-review-the-architecture-correctness-and-security-concurrency-2026-04-18T04-55-55-371Z.md`
- `.omc/artifacts/ask/gemini-review-documentation-quality-for-ark-skills-v1-17-0-context--2026-04-18T04-52-58-298Z.md`

**Verdict:** READY TO SHIP. No P1s. `pytest` 69/69, `bats` 14/14, validator OK.

---

## P2 — should-fix in a follow-up

### P2-1: Lock file opens with symlink-follow and truncation
`skills/ark-workflow/scripts/context_probe.py:117-123` uses `open(lock_path, "w")` which follows symlinks and truncates. In a hostile working tree, a precreated `.ark-workflow/current-chain.md.lock` symlink could clobber an arbitrary user-writable file.

**Fix:** replace with `os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)` and `fstat()` to confirm regular file. Low practical risk (attacker already has write access to the project), but cheap to harden.

### P2-2: Session-policy drift under partial schema
`skills/ark-workflow/scripts/context_probe.py:45-58` — when `--expected-session-id` is provided but the cache lacks both `session_id` and `sessionId`, the probe returns `session_mismatch` immediately and never falls through to the cwd/TTL tiers. Spec (`docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md:476-486`) promises session-id primary, cwd secondary, TTL tertiary.

**Fix:** when `cache_session_id` is falsy and an expected id is provided, skip to the cwd/TTL path instead of returning mismatch. Matches spec intent: id-check is only authoritative when both sides can produce one.

### P2-3: Checklist parser is body-wide, not Steps-scoped
`skills/ark-workflow/scripts/context_probe.py:176-189` and `:359-372` match every `- [ ]`/`- [x]` line after frontmatter. If `## Notes` (or a future section) ever contains a checklist, `check-off --step-index N` flips the wrong item and `_parse_chain_file` mis-computes `completed/remaining/next_skill`.

**Fix:** scope iteration to the region between `## Steps` and the next `## ` heading. Unit test with a chain that has checklist bullets in `## Notes`.

### P2-4: record-proceed re-probes without session/cwd guards
`skills/ark-workflow/scripts/context_probe.py:328-331` — `_cmd_record_proceed` calls `probe()` with only threshold kwargs, no `expected_cwd`/`expected_session_id`/TTL. Between menu display and record-proceed the cache can shift. Current `level == unknown` behavior already preserves existing state (silent no-op), so worst-case outcome is harmless, but the defensive guard should match the step-boundary call site.

**Fix:** thread `--expected-cwd` / `--expected-session-id` through the `record-proceed` CLI and down to the probe call. SKILL.md Step 6.5 substep 3 already has both values in scope.

### P2-5: Smoke-test runbook assumes in-repo cwd
Gemini P1.1, re-classified as P2. `skills/ark-workflow/scripts/smoke-test.md:10` copies from `skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md`. Fine for a dev running inside the repo (the explicit audience per line 123), but a heredoc-based minimal chain setup would make the runbook self-contained and robust to anyone who cloned only the SKILL.md into another project.

**Fix:** prepend a "Minimal inline chain file" alternative with a heredoc creating a 4-step `current-chain.md` with `proceed_past_level: null`. Keep the fixture-cp path as the default.

### P2-6: SKILL.md `SESSION_FLAG` forward reference
Gemini P2.2. Step 6 dual-path (`skills/ark-workflow/SKILL.md:264`) references `${SESSION_FLAG[@]}` before Step 6.5 (`:290-306`) defines it. The text notes "if Step 6.5 hasn't run yet… resolve it inline using the same snippet" but duplicates the logic.

**Fix:** hoist the `SESSION_ID` / `SESSION_FLAG` resolution snippet to a new "Step 5.5: Resolve Session Identity" or append it to Step 1's Project Discovery bash block, then reference `${SESSION_FLAG[@]}` from both sites.

### P2-7: "Pause for user decision" mechanism ambiguity
Gemini P2.1. `skills/ark-workflow/SKILL.md:379` says "display it verbatim and pause for user decision." In a non-interactive CLI, an agent may try to invoke an ask-user tool or hang.

**Fix:** reword to "Output the menu as the final text of this turn and yield — do not call any further tools until the next user message arrives with the selection (a/b/c/proceed)."

---

## P3 — polish, pick-up when convenient

### P3-1: Invalid `--step-index` silent instead of stderr
`skills/ark-workflow/scripts/context_probe.py:353-355, :371-375` return silently on `step_index < 1` or `step_index > total`. Spec (`docs/superpowers/specs/2026-04-17-ark-workflow-context-probe-design.md:250-253`) says stderr error + exit 0.

**Fix:** add `sys.stderr.write(f"check-off: --step-index {n} out of range (have {total_steps})\n")` before the silent return. Keep exit 0.

### P3-2: JSON booleans accepted as integers
`skills/ark-workflow/scripts/context_probe.py:68-79, :95-98` use `isinstance(..., int)`. `True`/`False` satisfy that. A cache with `"used_percentage": true` evaluates as `1%` instead of `schema_mismatch`; booleans inside `current_usage` count as `1`/`0`.

**Fix:** replace with `isinstance(v, int) and not isinstance(v, bool)` (or `type(v) is int` for stdlib-only purity).

### P3-3: Session Habits callout weight
Gemini P3.1. Block at SKILL.md:436 is well-written but blends into surrounding prose. An agent might skim past it as background doc instead of behavioral mandate.

**Fix:** consider `> [!IMPORTANT]` wrapper or `### Behavioral Mandate: Session Habits` heading.

### P3-4: CHANGELOG mode one-liners
Gemini P3.2. CHANGELOG lists the six CLI modes but not their purpose. Future maintainers reading the changelog must cross-reference the helper source.

**Fix:** append a single line per mode — `raw: JSON probe result; step-boundary: renders menu at boundaries; path-b-acceptance: one-line warning above Accept Path B; record-proceed/reset: suppression lifecycle; check-off: atomic checklist flip.`

---

## Dismissed / confirmed-not-applicable

- Both advisors confirmed all 22 plan tasks landed, design anchors intact, tests green.
- Codex explicitly returned "No P1s found."
- The LOC overshoot (487 vs spec's 140-170) and the bats stress test's sed-based setup were pre-acknowledged as non-blocking.
