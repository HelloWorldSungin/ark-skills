# TODO — ark-skills

Deferred work items. Add new entries at the top.

---

## Split `skills/ark-workflow/SKILL.md` into main + chains/ + references/

**Status:** Deferred (post-1.6.0)
**Scenario:** Hygiene Medium (mechanical refactor, no design decisions)
**Rationale:** After the v2 rewrite in 1.6.0, `SKILL.md` is 858 lines. Only ~320 lines (core router) are needed on every triage; the rest is pay-per-use content loaded for all invocations.

### Target structure

```
skills/ark-workflow/
├── SKILL.md                  # ~350 lines — triage router
├── chains/
│   ├── greenfield.md         # L/M/H
│   ├── bugfix.md             # L/M/H
│   ├── ship.md
│   ├── knowledge-capture.md  # Light/Full
│   ├── hygiene.md            # Audit-Only/L/M/H + dedup rule
│   ├── migration.md          # L/M/H
│   └── performance.md        # L/M/H
└── references/
    ├── batch-triage.md       # Full algorithm + example output
    ├── continuity.md         # State file format + cross-session resume
    └── routing-template.md   # CLAUDE.md copy-paste block
```

**Main SKILL.md keeps:** Project Discovery, Scenario Detection, Triage (risk + density), Workflow Steps (with read-on-demand pointers), Condition Resolution, Session Handoff, Re-triage, When Things Go Wrong.

**Workflow Step 4 becomes:** "Read `chains/{scenario}.md` and select the variant matching the weight class."

**Workflow Step 6.5 becomes:** "Create TodoWrite tasks, write `.ark-workflow/current-chain.md`, see `references/continuity.md` for the state file format."

**Batch Triage trigger becomes:** "If multi-item, read `references/batch-triage.md` and follow the algorithm."

### Trade-offs

**Pro:**
- Per-triage context cost drops from ~858 → ~350 + one chain file (~30) ≈ 55% reduction on the common path
- Chains are easier to edit in isolation
- Progressive disclosure is the idiomatic Claude Code skill pattern (superpowers skills use it)

**Con:**
- Agent has to Read two files instead of one per non-trivial triage
- Indirection cost in the main SKILL.md pointers
- More files to keep in sync across chain updates

### When to do it

- After 1.6.0 has been used in practice for at least one full workflow cycle to surface any latent v2 bugs first
- Pure refactor — no new behavior — should get its own spec + plan via `/ark-workflow` in a fresh session
- Target release: 1.7.0

### Entry point for picking this up

Start by reading `docs/superpowers/specs/2026-04-09-ark-workflow-v2-design.md` and the current `skills/ark-workflow/SKILL.md` to understand what moved where in v2 before planning the split.
