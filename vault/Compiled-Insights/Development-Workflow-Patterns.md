---
title: "Development Workflow Patterns"
type: compiled-insight
tags:
  - compiled-insight
  - skill
  - workflow
summary: "Workflow patterns: brainstorm→spec→codex→plan→implement, audit-first, NotebookLM queries, risk-primary triage with density escalation, hybrid TodoWrite+file continuity."
source-sessions:
  - "[[S003-Ark-Workflow-v2-Rewrite]]"
source-tasks: []
created: 2026-04-08
last-updated: 2026-04-09
---

# Development Workflow Patterns

## Summary

The ark-skills project established several workflow patterns that proved effective for complex design work. The central pipeline is: brainstorm → design spec → /codex review → implementation plan → execute. Two key feedback loops were validated: using /codex for independent spec review catches factual errors before they reach implementation, and auditing existing systems before deciding on restructuring prevents over-engineering.

## Key Insights

### Codex Review Before Implementation Plans

After writing a design spec, run `/codex review` for independent validation before writing an implementation plan. This was explicitly requested and validated on 2026-04-07.

**Evidence of value:** The codex review of the ark-skills design spec found 11 concrete issues, including a completely incorrect MCP deployment model (spec assumed standalone Node server; reality is an embedded Obsidian endpoint). This would have been baked into the implementation plan and caused significant rework.

**Pattern:** After writing any spec, offer to run /codex review. Present findings with synthesis categorizing critical vs. important vs. minor.

### Audit-First, Decide-Later

When restructuring existing systems, run an audit in a separate session before committing to an approach. Don't pre-decide the outcome in the spec.

**Evidence of value:** The vault audit changed the recommendation from what was initially assumed. The audit found that vaults were already strong in areas where obsidian-wiki would add little value (cross-linking, frontmatter coverage), and identified session log burial as the real problem — a finding that would have been missed by jumping straight to implementation.

**Pattern:** When a design involves restructuring existing systems, propose an audit phase before the implementation plan. Generate a self-contained audit prompt the user can run in a fresh session.

### NotebookLM for Vault Knowledge Queries

Use `notebooklm ask` to query vault content instead of having subagents read through individual session log files.

**Evidence of value:** The vaults have 100+ session logs. Reading them one-by-one with subagents is slow, expensive, and wastes context. NotebookLM already has all vault content indexed and returns rich, sourced answers with session numbers in seconds.

**Pattern:** For any task requiring synthesis across multiple vault files, query NotebookLM first. Verify key claims against actual files when writing final output.

### Multi-Agent Orchestration

The ark-code-review skill uses a fan-out pattern: dispatch 5 specialized agents (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) in parallel, then synthesize. This pattern proved effective for comprehensive review coverage.

### Skill Testing Strategy: Read-Only First

When testing a new plugin, follow this order: (1) smoke test visibility (skills appear in `/skill` list), (2) dry-run read-only skills like `/wiki-status` and `/wiki-lint` first, (3) test context discovery against projects with and without CLAUDE.md fields, (4) verify cross-project isolation.

### /ship Behavior for Markdown-Only Repos

The `/ship` gstack skill intelligently skips test framework detection, coverage audit, and adversarial review for markdown-only repos (like ark-skills). It only runs pre-landing review on the diff. Deploy verification is also N/A — Claude Code plugin repos have no web app or deploy target.

**Important:** `/ship` requires a feature branch, not master. If you committed directly to master, create a feature branch from the current commit, then `git branch -f master origin/master` to make the PR diff clean.

### Risk-Primary Triage with Decision-Density Escalation

When classifying a task into a weight class (light/medium/heavy), risk alone sets the floor, and decision density can only escalate — never downgrade. This replaces factor-matrix triage, which conflated risk, density, file count, and duration into a single table with ambiguous outcomes.

**Rules:**
- Low risk → Light floor; Moderate → Medium; High → Heavy
- Obvious fix keeps the floor; "some trade-offs" escalates Light → Medium; architecture decisions escalate anything → Heavy
- A Heavy risk stays Heavy even when the fix is obvious (can't downgrade a high-risk task for being a small diff)
- File count and duration are informational context only, never classification inputs

**Evidence of value:** The v2 rewrite in [[S003-Ark-Workflow-v2-Rewrite]] used this rule to fix two common misclassifications in the old factor-matrix triage:
- A 20-file test-utility rename (low risk, obvious) correctly stays Light instead of being mis-flagged Heavy by file count
- A 1-file auth validation fix (high risk) correctly stays Heavy instead of being mis-flagged Light by file count

**Pattern:** For any task classification problem, separate "what's the worst case" (floor signal — risk, blast radius) from "what decisions need to be made" (escalation signal — design work required). Let floor set the minimum, let escalation push up only.

### Hybrid Continuity: TodoWrite + Durable File

For any multi-step workflow that may span context compaction or session breaks, use a hybrid persistence model:
- **TodoWrite tasks** for in-session interactive reminders (survives compaction within a session)
- **A durable markdown file** at a known project-local path (survives session exit)

Neither mechanism alone is sufficient:
- TodoWrite is session-scoped and disappears when the session ends
- A file alone doesn't surface interactively — the agent has to remember to read it

**Implementation pattern:**
1. At workflow start, create TodoWrite tasks AND write the durable file with the full chain
2. After each step, update both: check off the file (change `[ ]` to `[x]`), mark the TodoWrite task completed
3. On session start, check for an existing durable file; if present, rehydrate TodoWrite tasks from unchecked items
4. Add `handoff_marker` frontmatter for intentional design → implementation session breaks
5. Flag files older than 7 days as potentially stale (ask, never auto-delete)
6. Add the file directory to `.gitignore` — it's per-project ongoing work, not code
7. On workflow completion, archive the file rather than delete — archives are the workflow history

**Evidence of value:** Introduced in `/ark-workflow` v2 ([[S003-Ark-Workflow-v2-Rewrite]]) as the Continuity section of the skill. Solves the "skill outputs a chain and exits, agent loses position" problem that plagued v1.

**Pattern:** Any orchestrator skill that outputs a multi-step chain should persist state to a known project-local file AND populate TodoWrite. Any skill that triggers a workflow should check for an in-progress chain at session start before starting fresh.

## Evidence

- Memory: `feedback_workflow.md` (codex review pattern, audit-first approach)
- Memory: `feedback_notebooklm_for_vault.md` (NotebookLM query pattern)
- Design spec §2a: ark-code-review multi-agent pattern preserved across generalization
- Conversations `f7f9e4ce`, `29145231`: /ship pipeline behavior and feature branch requirement
- [[S003-Ark-Workflow-v2-Rewrite]] + `docs/superpowers/specs/2026-04-09-ark-workflow-v2-design.md` (risk-primary triage + hybrid continuity patterns)

## Implications

- New features in this ecosystem should follow the brainstorm → spec → codex → plan → implement pipeline.
- Resist the urge to skip codex review for "simple" changes — the value is in catching unstated assumptions.
- When adding vault query capabilities to any skill, use NotebookLM as the primary retrieval mechanism.
- Multi-agent fan-out patterns should be preserved when generalizing skills, as they provide comprehensive coverage without sequential bottlenecks.
