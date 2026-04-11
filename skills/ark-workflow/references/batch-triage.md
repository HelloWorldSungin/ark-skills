# Batch Triage

**Trigger:** Activated when the user's prompt describes multiple distinct executable tasks. This includes:
- Numbered lists ("1. Fix X, 2. Fix Y")
- Bulleted lists
- Prose with multiple distinct requests ("fix the auth bug and also clean up the dead code")
- Tech debt/cleanup batches

**Not a batch:** Requirement lists, acceptance criteria, or nested sub-steps within a single task. If the "items" describe one logical unit of work (e.g., "add dark mode: toggle component, theme provider, CSS vars"), treat as a single task, not a batch. When uncertain, ask:
> Are these separate tasks to triage individually, or one task with multiple sub-steps?

### Algorithm

**Step 0 — Root cause consolidation:**
Before per-item triage, scan the items for shared root causes. If multiple items appear to be symptoms of one underlying issue, tell the user:

> Items #X, #Y, and #Z look like symptoms of a shared root cause. Would you like to consolidate them into a single investigation, or triage them separately?

Only consolidate if the user confirms. Do not auto-consolidate — the user's framing matters.

**Step 1 — Per-item scenario + weight classification:**

For each remaining item:
1. Determine scenario (from the 7-scenario table above)
2. Classify weight:
   - Ship items: **no weight class** (use standalone Ship chain)
   - Knowledge Capture items: **Light or Full**
   - Hygiene Audit-Only items: **no weight class**
   - All other scenarios: **Light/Medium/Heavy** (per risk-primary triage)
3. Present as a summary table

**Step 2 — Dependency detection (heuristic):**

Based on item descriptions and project knowledge, flag possible dependencies:
- Items that describe the same component/file/module (possible shared code)
- Items where one describes output/state that another consumes (logical dependency)
- Items with different risk levels touching the same area (risk isolation — don't ship together)

**Important:** This is heuristic based on item descriptions, not code analysis. Tell the user when flagging: "I think #X depends on #Y because they both touch the auth middleware — confirm before ordering." Ask for confirmation on uncertain dependencies before committing to an execution order.

**Step 3 — Grouping:**

Organize items into execution groups:
- **Parallel groups:** Independent items with the same scenario + weight class
- **Sequential chains:** Items with confirmed dependencies (A before B)
- **Separate session recommended:** Heavy items when the rest of the batch is Light — suggest the user split into separate sessions

**Step 4 — Per-group chains:**

For each group, look up the skill chain:
- Ship items → Ship chain
- Knowledge Capture items → Knowledge Capture Light or Full
- Hygiene Audit-Only items → Hygiene Audit-Only chain
- Scenario-and-weight items → matching scenario chain

Present the full execution plan.

### Example Output

```
## Batch Triage

| # | Item | Scenario | Weight | Notes |
|---|------|----------|--------|-------|
| 1 | Transaction isolation | Bugfix | Medium | Touches DB client |
| 2 | Ghost pipeline runs | Bugfix | Light | Orchestrator startup |
| 3 | Payload drop | Bugfix | Medium | Invoke endpoint |
| 4 | Retry storms | Bugfix | Heavy | Process lifecycle |
| 5 | MCP ClosedResourceError | Bugfix | Light | Graceful shutdown |
| 6 | Update README | Knowledge Capture | Light | - |
| 7 | Cherry-pick hotfix | Ship | - | Standalone ship |

**Root cause scan:** No shared root causes detected.

**Possible dependencies (please confirm):**
- #4 may depend on #1 (both touch process/DB lifecycle)
- #6 is independent

**Execution plan:**
- Group A (parallel): #2, #5 — Light Bugfix chain
- Group B (sequential): #3 — Medium Bugfix chain
- Group C (pending dep confirmation): #1 → #4 — Heavy Bugfix
- Standalone: #7 — Ship chain
- Standalone: #6 — Knowledge Capture Light

**Session recommendation:** Groups A+B and standalones in this session. Group C in a fresh session if Heavy (architecture work may require design phase).
```
