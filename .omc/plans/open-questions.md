# Open Questions Register

Persistent record of unresolved questions, deferred decisions, and clarifications needed across plans.
Each entry notes the source plan and why resolution matters.

## OMC ↔ /ark-workflow Dual-Mode Integration — 2026-04-13

Source: `.omc/plans/2026-04-13-omc-ark-workflow-integration.md` (iteration 2)

- [ ] `/autopilot` execution-only invocation mechanism — does it expose `--skip-phase-5` / `--execution-only`, or must Path B signal handback via a checkpoint marker or env var? — Affects Vanilla template Path B step 3 wording + reference Section 4.1 contract. Conditionally mitigated in iteration 2 by `ARK_SKIP_OMC=true` rollback (R4) and by Section 4.1's explicit handback-boundary contract; mechanism itself still needs Architect pin before Phase 2a executor dispatches.
- [x] Step 6 emission shape when `HAS_OMC=true` and zero of the 4 Path-B signals fire — **Iteration 2 proposed resolution:** show `[Show me both]` as a discoverability footer (show-always). Architect to confirm before Phase 1 executor dispatches.
- [x] Per-variant Path B appropriateness for Light/Standalone variants — **Iteration 2 resolved:** show-always per spec's discoverability-over-neutrality principle. Knowledge-Capture Light handled by Special-B template (no longer "discouraged").
- [ ] Telemetry log rotation policy (currently append-only in v1.13.0) — follow-up for v1.14.x.
- [ ] Downstream CLAUDE.md `HAS_OMC` grep-pinning detection — if telemetry reveals Scenario A (false Path A pinning), Architect to decide whether to add a version-check warning in Step 6 output.

## ark-skill-healer (RALPLAN consensus) — 2026-06-05

Source: `.omc/plans/ark-skill-healer-consensus.md`

- [x] Snapshot tracking policy — RESOLVED (consensus round 1): gitignored machine-local cache under `.omc/skill-healer/state/`; cross-clone git-tracked baselines dropped as v1 non-goal (resolved C1 contradiction).
- [x] Staged-patch home — RESOLVED (consensus round 1): `.omc/skill-healer/staged-patches/`; entire run-write surface is the gitignored `.omc/skill-healer/`, making AC11 a structural invariant.
- [ ] Discovery confirmation (narrowed, executor-runnable): Phase 0 must confirm `.claude/commands/ark-skill-healer.md` slash-command triggers the workflow and resolves SKILL.md by path. `.claude/skills/` auto-loading is NOT relied upon (there is no `.claude/skills/` dir; only `.claude/omc-reference/` exists, and it is the plugin skill that loads).
- [ ] gstack upstream source for commit-range — v1 scopes gstack to config-only tracking (`~/.gstack/config.yaml` + `.last-setup-version`, no clone). Confirm whether a gstack upstream repo should be wired for a future commit-range tier.
- [ ] chromadb explicit tracking (deferred) — v1 treats chromadb as a mempalace-transitive pin (no own changelog source in-repo). Revisit declaring `chroma-core/chroma` as an independent cascade target if pin drift recurs.
