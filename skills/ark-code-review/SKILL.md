---
name: ark-code-review
description: Comprehensive multi-agent code review that orchestrates Claude Code agents (code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer) into a unified review. Includes an epic review mode that pulls Obsidian TaskNotes epics, stories, and session logs to cross-reference planned work against actual code changes. Also includes a plan review mode that cross-references code against implementation plans and design specs. Includes a full review mode (--full) that combines thorough code analysis with auto-detected epic context. Use this skill whenever the user mentions "code review", "review my changes", "review before deploy", "check my code", "ark review", "/ark-code-review", "pre-deploy review", "review this branch", "review these files", "review this epic", "does the code match the plan", "review against plan", "review against spec", "check plan completion", "did I implement the plan", "full review", "complete review", "review everything", or any request to get feedback on code quality. Also triggers on "what did I break", "is this safe to deploy", "sanity check", or "second opinion on this code". Do NOT use for: PR reviews on GitHub (use code-review:code-review directly), codebase maintenance/cleanup (use codebase-maintenance), or general questions about the codebase.
---

# Ark Code Review

Multi-agent code review that fans out to specialized reviewers, then aggregates findings into a single actionable report. Designed for pre-merge review of branch changes.

Supporting references (load on demand):

- `references/agent-prompts.md` — full agent prompt templates for Step 2 fan-out
- `references/report-formats.md` — per-mode report templates for Step 3 aggregation
- `references/external-second-opinion.md` — framing, cost notice, and vendor capacity caveat (operational rules stay inline in § External Second Opinion)

## Project Discovery

Before running this skill, discover project context per the plugin CLAUDE.md:

1. Read the project's CLAUDE.md: project name, task prefix, vault path, TaskNotes path
2. Read the vault's `_meta/vault-schema.md` for the vault structure
3. Detect the base branch: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'` (fallback to `master`)
4. Use discovered values throughout — never hardcode project names or paths

## Quick Reference

```
/ark-code-review                              # Default: review current branch vs {base_branch}
/ark-code-review --quick                      # Fast: code-reviewer only, <60s
/ark-code-review --thorough                   # Full: all agents + external second opinion
/ark-code-review --thorough --no-multi-vendor # Thorough WITHOUT external Codex/Gemini (alias: --no-xv)
/ark-code-review --full                       # Thorough + auto-detected epic context
/ark-code-review --epic {task_prefix}001      # Review epic + stories + sessions vs code
/ark-code-review --plan some-feature-slug     # Review code against plan + spec docs
/ark-code-review --pr 123                     # Review a GitHub PR
/ark-code-review src/foo.py bar.py            # Review specific files only
```

## How It Works

Fan out parallel agents scoped to the changed files; aggregate findings into one report.

| Agent | subagent_type | When | Role |
|-------|---------------|------|------|
| Code Reviewer | `feature-dev:code-reviewer` | all modes (solo in `--quick`) | Bugs, logic, security. Confidence ≥ 80. `--epic` and `--plan` use shorter variants. |
| Code Architect | `feature-dev:code-architect` | all modes except `--quick` | Pattern consistency, integration risks. `--epic` / `--plan` use dedicated variants. |
| Test Coverage Checker | `Explore` | default, `--thorough`, `--full`, `--plan` (not `--quick` / `--epic`) | Maps source → test files, flags gaps. |
| Silent Failure Hunter | `code-simplifier:code-simplifier` | `--thorough` + `--full` only | Broad catches, missing logging, swallowed exceptions. |
| Test Analyzer | — | `--thorough` + `--full` only | Deep test-gap analysis: edge cases, error paths, negatives. |

After all agents complete, deduplicate overlapping findings (prefer the more specific one) and sort by severity.

---

## Execution Steps

### Step 1: Determine scope

```bash
git diff {base_branch}...HEAD --stat          # overview
git diff {base_branch}...HEAD --name-only     # changed files list
git diff {base_branch}...HEAD                 # full diff
```

If the user provided specific files, scope all agents to those files only. If `--pr N` was passed, use `gh pr diff N` instead.

### Step 2: Fan out agents

Spawn the agents from the How It Works table **in parallel** using the Agent tool. Prompt bodies live in `references/agent-prompts.md` — for each agent, read § `<Agent Name>` and substitute `<FILE_LIST>` and `<DIFF>`.

Mode variants override the default prompt for Code Architect (`--epic`) or for both Architect + Code Reviewer (`--plan`). See `references/agent-prompts.md` § Mode variants.

### Step 3: Aggregate and present

Produce the final report using the Default template from `references/report-formats.md` § Default mode. Other modes switch templates per the rule below:

| Mode | Template |
|------|----------|
| default, `--thorough`, `--pr N` | `references/report-formats.md` § Default mode |
| `--full` | § `--full` mode |
| `--epic` | § `--epic` mode |
| `--plan` | § `--plan` mode |
| `--quick` | § `--quick` mode |

Report header always includes: **Branch**, **Files changed**, **Reviewers** (list active agents, adding `codex-cli` / `gemini-cli` if External Second Opinion ran). Each finding line: `- [file:line] Description — Found by: <agent>`.

### Step 4: Offer follow-up (MANDATORY — do not skip)

After presenting the report, offer follow-up actions. All modes **except** `--quick`:

- "Want me to fix the critical/high issues?"
- "Want me to write/update the missing tests?" (if test coverage checker found gaps)
- "Want me to run `/simplify` on the suggestions?"

Mode-specific additions:

| Mode | Additional offers |
|------|-------------------|
| `--pr N` | "Post these findings as inline comments on PR #N?" (via `gh pr review N --comment`); "Request changes on the PR?" (via `gh pr review N --request-changes`); "Or leave the review here locally?" |
| `--full` | "Update the epic/story statuses in the vault?" |
| `--epic` | "Update the epic/story statuses in the vault?"; "Fix the code quality issues?" |
| `--plan` | "Fix the code quality issues?"; "Implement the incomplete tasks?" (if tasks remain unchecked); "Update the plan checkboxes to reflect current status?" |

`--quick` mode does NOT offer follow-up — the quick report stands alone.

---

## Mode-Specific Behavior

### `--quick` mode

**Goal: finish in under 60 seconds with a short, actionable report.**

1. **Scope down aggressively.** Do NOT review the full branch diff:
   - If the user mentions specific files or "the changes I just made", scope to only those.
   - Otherwise, use `git diff --name-only` (unstaged) / `git diff --cached --name-only` (staged) for the most recent uncommitted changes. If nothing is uncommitted, use only the last commit (`git diff HEAD~1 --name-only`).
   - Never review more than ~10 files in quick mode. If the scope is larger, tell the user to use default mode.
2. **Skip code-architect and test coverage checker.**
3. **Run only `feature-dev:code-reviewer`** scoped to the narrowed list. Do NOT spawn a subagent — review inline to save overhead.
4. **Produce the Quick report** per `references/report-formats.md` § `--quick` mode. No follow-up offers.

### `--thorough` mode

Run all 5 agents (default 3 + Silent Failure Hunter + Test Analyzer). Use for significant changes, new features, or pre-merge reviews.

**Inherits External Second Opinion:** when `HAS_OMC=true` and at least one of `codex`/`gemini` is on PATH, `--thorough` also solicits a vendor-training-biased second opinion via `omc ask`. Disable with `--no-multi-vendor` (alias `--no-xv`). See § External Second Opinion below.

### `--full` mode

Combines `--thorough` (all 5 agents) with `--epic` (vault cross-referencing), auto-detecting the epic from the current branch name. **Inherits External Second Opinion from `--thorough`.**

#### Step 0: Auto-detect epic from branch name

```
1. Get current branch: git branch --show-current
2. Strip prefix (feature/, improve/, epic/, fix/, bugfix/) → branch_slug
3. Lowercase branch_slug, tokenize by splitting on "-"
4. For each epic file in {tasknotes_path}/Tasks/Epic/*.md:
   a. Strip task-id prefix (e.g., "{task_prefix}043-") → epic_slug
   b. Lowercase epic_slug, tokenize by splitting on "-"
   c. Score = |branch_tokens ∩ epic_tokens| / |branch_tokens ∪ epic_tokens|
5. Pick the best match:
   - If best score ≥ 0.6 and no tie → use that epic
   - If tie or best score < 0.6 → fall back to Step 0b
```

**Step 0b: in-progress-epics fallback**

1. Search `{tasknotes_path}/Tasks/Epic/*.md` for frontmatter `status: in-progress`
2. 1 match → use it. 0 matches → warn "No epic found, falling back to --thorough only". 2+ matches → present the list, ask the user.

#### Steps 1-4: Combined thorough + epic

Once the epic is resolved:

1. **Gather vault context** — same as `--epic` mode (via `obsidian-cli`)
2. **Determine scope** — same as default (Step 1 above)
3. **Fan out all 5 agents in parallel.** Agent 2 (Code Architect) uses the `--epic` variant prompt from `references/agent-prompts.md` and receives the epic context document.
4. **Produce `--full` report** per `references/report-formats.md` § `--full` mode.

### `--epic {task_prefix}001` mode

Reviews an Obsidian TaskNotes epic against the actual code on the branch — the most context-rich mode.

#### Step 1: Gather vault context (via `obsidian:obsidian-cli`)

```
1. Read the epic:           obsidian read file="<TASK-ID>-*"
   → title, status, priority, goals, child story wikilinks
2. Find child stories:      obsidian backlinks file="<TASK-ID>-*"
   → all stories whose `projects` frontmatter references the epic
3. For each child story:    obsidian property:read name="status" file="<story-id>-*"
   → task-id, title, status, session, completion criteria
4. Collect session refs from: epic's `session` property + each story's `session` property. Deduplicate.
5. For each session:        obsidian read file="Session-###"
   → objective, key accomplishments, next steps
```

#### Step 2: Build the review-context document

```markdown
## Epic: <TASK-ID> — <title>
Status: <status> | Priority: <priority>
Goals: <from epic body>

## Stories
### <story-id> — <title> [status]
Description: <from story body>
Completion criteria: <checkboxes>

## Session History
### Session-###: <title>
Key accomplishments: <summary>
Next steps: <from session>

## Branch Changes
<git diff {base_branch}...HEAD --stat>
<changed files list>
```

#### Step 3: Fan out reviewers (parallel)

- **Agent 1** — Code Architect (`--epic` variant prompt, `references/agent-prompts.md` § Code Architect variant). Receives the review-context document + diff.
- **Agent 2** — Code Reviewer (`--epic` variant prompt, `references/agent-prompts.md` § Code Reviewer variant). Shorter than default — the epic context carries the framing. Receives file list + diff.

#### Step 4: Epic review report

Per `references/report-formats.md` § `--epic` mode.

### `--plan SLUG` mode

Reviews code against an in-repo implementation plan and companion design spec. In-repo counterpart to `--epic` — epics live in the vault, plans live in the repo.

#### Step 1: Discover plan and spec files

Argument accepts a full filename, slug, or partial match:

```
/ark-code-review --plan research-pipeline
/ark-code-review --plan 2026-03-24-research-pipeline
/ark-code-review --plan pipeline       # partial match
```

1. Search `*{SLUG}*.md` in project root, `docs/`, `plans/`
2. Multiple matches → pick the most recent by date prefix; if ambiguous, ask
3. For the matched plan, look for a companion `-design` or `-spec` file
4. No spec file → proceed plan-only (warn the user)

#### Step 2: Parse plan and spec

**From the plan:**
- Goal statement (top of document)
- Chunks and tasks (`## Chunk N` / `### Task N` headers)
- Individual steps with checkbox status (`- [ ]` / `- [x]`)
- File paths mentioned in each task
- Commit messages (from `git commit -m` lines in steps)

**From the spec:**
- Problem statement, solution overview, design-decisions table
- Architecture (before/after data flow)
- Component descriptions with file paths and code snippets
- Performance targets, testing requirements

#### Step 3: Fan out reviewers (parallel)

- **Agent 1** — Plan Conformance Reviewer (`--plan` Code Architect variant, `references/agent-prompts.md`). Receives plan+spec context doc + diff.
- **Agent 2** — Code Reviewer (`--plan` variant prompt). Receives file list + diff + "these changes implement the plan described below" context.
- **Agent 3** — Test Coverage Checker (default Explore prompt).

#### Step 4: Plan review report

Per `references/report-formats.md` § `--plan` mode. Plan completion must be ≥ 80% for the merge recommendation to read READY.

### `--pr N` mode

1. Use `gh pr diff N` for the diff (not `git diff`).
2. Run `gh pr view N --json title,url,headRefName,baseRefName` for the report header.
3. Run full default review (all default agents in parallel).
4. In the report header, include the PR number, title, and URL (see `references/report-formats.md` § `--pr N` additions).
5. After the report, offer GitHub actions per § Step 4 table.

---

## External Second Opinion (Vendor CLIs via `omc ask`)

When `--thorough` (or an inheriting mode like `--full`) runs on a host with external vendor CLIs (`codex` and/or `gemini`) installed alongside OMC, the review solicits a second opinion from each available vendor. Claude (parent) synthesizes all streams — native + vendor — into the unified report.

**Opt-out:** pass `--no-multi-vendor` (alias `--no-xv`). This is **not a convention-aware review** — the vendors do not see CLAUDE.md, plugin skills, vault, or TaskNotes. They bring a vendor-training-biased code-quality perspective as a complementary stream to the native CC agents. For framing, synthesis detail, cost notice, and the Gemini capacity caveat, see `references/external-second-opinion.md`.

### Trust Boundary Notice

Sending the diff to external vendors **widens the trust boundary** beyond the local machine. By default, `--thorough` performs this fan-out whenever `codex` or `gemini` is on PATH. Before accepting the default on a new repository, confirm:

- The code in the diff is not regulated, proprietary-under-NDA, or containing secrets. Scan with `git diff --name-only` and inspect changed files.
- Installed vendor CLIs are authenticated to accounts that align with your organization's policy for external AI access.
- If unsure, pass `--no-multi-vendor` (alias `--no-xv`) for this invocation. For a persistent per-project opt-out, add a line to your project CLAUDE.md routing rules.

The vendor streams receive only: `<diff_path>`, `<changed_files_list>`, and a **1-paragraph neutral branch description** written by Claude from public signals (commit messages + filenames). They do **NOT** receive CLAUDE.md, plugin skills, vault content, TaskNotes, or project secrets. Passing those would dilute the vendor-diversity value and widen the trust boundary further.

### Trigger conditions (ALL must be true)

1. `--thorough` is set (or inherited via `--full`)
2. `--no-multi-vendor` / `--no-xv` is NOT present
3. `HAS_OMC=true` (OMC CLI on PATH or cache present; honors `ARK_SKIP_OMC=true` per `skills/ark-workflow/SKILL.md`)
4. At least one of `codex` / `gemini` is on PATH

If conditions 3 or 4 fail, skip with a one-line notice (see Degradation Table). If only one vendor is present, only that vendor's `omc ask` runs.

### Fan-out (parallel with native CC agents in Step 2)

**Preparation (single-shot, before fan-out):**

- `DIFF_PATH` — persisted diff path from Step 1 (e.g., `.ark-workflow/review-diff-<ts>.patch`)
- `CHANGED_FILES` — newline-separated list from `git diff {base_branch}...HEAD --name-only`
- `BRANCH_DESC` — 1-paragraph neutral summary from commit messages + filenames only. **No CLAUDE.md, no vault content, no secrets.**

**Codex fan-out — external second opinion (code-quality lens):**

```bash
omc ask codex "You are an independent external reviewer with no project-specific context. Give a second opinion on the diff at ${DIFF_PATH}.

Changed files:
${CHANGED_FILES}

Branch description (public signals only):
${BRANCH_DESC}

Lens: general code quality — bugs, logic errors, security concerns, architecture smells. You do NOT know this project's conventions; do not invent rules to enforce. Only report findings with confidence >= 80. For each finding include [file:line], a one-line description, severity (critical/high/medium), and the reasoning. Skip style/formatting issues — linters handle those. Skip anything that requires seeing code outside the diff to judge confidently."
```

**Gemini fan-out — external second opinion (UI / docs lens):**

```bash
omc ask gemini "You are an independent external reviewer with no project-specific context. Give a second opinion on the diff at ${DIFF_PATH}.

Changed files:
${CHANGED_FILES}

Branch description (public signals only):
${BRANCH_DESC}

Lens: UI/UX consistency (only if UI files are touched) and documentation hygiene — code-comment drift, missing API docs, README staleness. You do NOT know this project's conventions; do not invent rules to enforce. Only report findings with confidence >= 80. For each finding include [file:line], a one-line description, severity (critical/high/medium), and the reasoning. Skip style/formatting issues — linters handle those. Skip anything that requires seeing code outside the diff to judge confidently."
```

Both invocations run in parallel with the native CC agents. Each returns the artifact path on stdout; wait for all to complete before synthesis. See `references/external-second-opinion.md` § Synthesis detail for reading artifacts into the unified report.

### Degradation table

| `omc` | `codex` | `gemini` | Behavior | Notice |
|---|---|---|---|---|
| ✗ | — | — | Skip. Native CC review only. | "External second opinion skipped (OMC not installed). See https://github.com/anthropics/oh-my-claudecode." |
| ✓ | ✗ | ✗ | Skip. Native CC review only. | "External second opinion skipped (no vendor CLI on PATH). Install `@openai/codex` and/or `@google/gemini-cli` to enable." |
| ✓ | ✓ | ✗ | Codex only. | "Gemini second opinion skipped (CLI not on PATH). Install `@google/gemini-cli` to include it." |
| ✓ | ✗ | ✓ | Gemini only. | "Codex second opinion skipped (CLI not on PATH). Install `@openai/codex` to include it." |
| ✓ | ✓ | ✓ | Full fan-out (both vendors in parallel). | (none) |

Same skip-with-notice applies when `--no-multi-vendor` / `--no-xv` is present ("External second opinion disabled by `--no-multi-vendor` flag."). `ARK_SKIP_OMC=true` cascades into this table via the `HAS_OMC=false` row.

Per-vendor runtime failures (exit ≠ 0 from `omc ask`) downgrade to "synthesize on remaining streams"; failed-vendor notes appear in the report's footer.

---

## Post-Review Actions

**If the project's CLAUDE.md defines deployment targets:**
- Check deployed commit drift on each target
- Verify service health endpoints
- Run staging smoke tests

**If no deployment targets are defined:** skip deployment checks.

## Important Notes

- **Linters handle style.** All agents skip formatting/style issues.
- **Confidence threshold.** `feature-dev:code-reviewer` uses ≥ 80. Other agents also avoid low-confidence findings.
- **Large diffs.** If > 4000 lines, split the review by directory or module.
- **Don't auto-fix.** This skill is advisory. Present findings; let the user decide what to fix.
