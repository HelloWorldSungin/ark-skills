---
name: wiki-update
description: End-of-session workflow — create/update session log, sync project knowledge into vault, update TaskNote epic/stories, regenerate index. Triggers on "wiki update", "sync vault", "wrap up", "end session", "hand off", "session log". For warm-starting a session ("continue", "resume", "pick up where I left off"), use /notebooklm-vault session-continue instead.
---

# Wiki Update

End-of-session workflow for the current project's Obsidian vault. Creates or updates the session log, updates linked TaskNote epics and stories, extracts compiled insights from the session log (addressing session log knowledge burial), and regenerates the vault index.

This is the single entry point for end-of-session vault maintenance. Replaces the deprecated `/notebooklm-vault session-handoff` sub-command.

## Project Discovery

Per the plugin's context-discovery pattern (see plugin `CLAUDE.md`):

1. Read the project's `CLAUDE.md` to find:
   - **Project name**
   - **Vault root** (`{vault_path}`) — repo root, parent of both project docs and TaskNotes
   - **Project docs path** (`{project_docs_path}`) — where `Session-Logs/` lives. For standalone projects this equals `{vault_path}`; for shared vaults (e.g., Trading-Signal-AI monorepo) it's a subdirectory like `{vault_path}/Trading-Signal-AI/`. **Always use this path for session log operations in Step 2, not `{vault_path}`.**
   - **TaskNotes path** (`{tasknotes_path}`) — sibling of project docs, not nested under it
   - **Task prefix** (includes trailing dash, e.g., `Arkskill-`)
2. Read `{vault_path}/_meta/vault-schema.md` to understand folder structure.
3. Read `{vault_path}/index.md` to know what's already documented.
4. Resolve the counter file path: `{tasknotes_path}/meta/{task_prefix}counter`.

If any required field is missing from `CLAUDE.md`, stop and tell the user which field to add.

## Workflow

### Step 1: Understand What Changed

Scan the project for recent changes:

```bash
git log --oneline -20
git diff HEAD~5 --stat
git diff --name-only HEAD~5
```

Also check:
- Open TaskNotes in `{tasknotes_path}/Tasks/`
- Any new or modified architecture docs
- The most recent session log in `{project_docs_path}/Session-Logs/` (used by Step 2 for create-vs-continuation)

### Step 2: Create or Update Session Log

#### Locate the most recent session log

Glob `{project_docs_path}/Session-Logs/S*.md` and sort by numeric session number (not mtime — older continuations may have recent mtimes). Read the highest-numbered log and extract its `epic` and `session` frontmatter.

#### Skip detection (ad-hoc docs sync)

If there are no git commits since the last session log's date **and** the conversation has no substantive work to log (e.g., the user invoked `/wiki-update` just to add a single doc), ask:

> "No meaningful changes since Session {NNN}. Skip session log creation and jump to knowledge extraction? [y/N]"

On `y`, skip to Step 4. Otherwise continue.

#### Decide: create new or append continuation

Determine this session's epic from (in order):
1. Explicit user mention (e.g., "working on `{task_prefix}007`")
2. TaskNote IDs mentioned in the conversation
3. Cross-reference `git diff --name-only` against stories that link to candidate epics in `{tasknotes_path}/Tasks/Epic/`
4. If none match, treat as epic-less (`epic: ""`)

Then:
- **If a session log was created earlier in this conversation** — update it with final results.
- **Else if this session's epic matches the last log's `epic`** — append a continuation block to the existing log and bump `last-updated`.
- **Else** — create a new `S{N+1}-{slug}.md`.

#### Write the session log

Use the merged Ark session log schema (see `vault/_Templates/Session-Template.md` and `vault/_meta/vault-schema.md`):

```yaml
---
title: "Session {NNN}: {Title}"
type: session-log
tags:
  - session-log
  - "S{NNN}"
  - {domain-tags}
summary: "<=200 char description"
session: "S{NNN}"
status: complete      # complete | in-progress | blocked
date: YYYY-MM-DD
prev: "[[S{N-1}-{slug}]]"
epic: "[[{epic-id}-{slug}]]"
source-tasks: []
created: YYYY-MM-DD
last-updated: YYYY-MM-DD
---

# Session {NNN}: {Title}

## Objective
[What this session set out to accomplish]

## Context
[Relevant prior work; link to prev session if applicable]

## Work Done

### {Topic 1}
[Key changes, files modified, commands run]

## Decisions Made
[Decisions and rationale]

## Open Questions
[Unresolved items]

## Next Steps
[Actionable items for the next session, ordered by priority]
```

**Continuation format** (append to existing log, bump `last-updated`):

```markdown

---

## Continuation — YYYY-MM-DD — {Optional Title}

### Objective
[What this continuation set out to accomplish]

### Work Done
[Additional changes, files modified, decisions made]

### Decisions Made
[New decisions]

### Issues & Discoveries
[New bugs, gotchas]

### Updated Next Steps
[Revised action items, replacing/updating the previous Next Steps]
```

**Tooling:** use `Write` as the primary path (no Obsidian dependency). When Obsidian is running and the `obsidian:obsidian-markdown` skill is available, prefer it for proper Obsidian-flavored markdown (wikilinks, callouts, frontmatter). Mirror the conditional pattern at `skills/notebooklm-vault/SKILL.md` (Vault Access section).

**Capture rule:** Ensure all experiment results, discoveries, and architectural decisions from the conversation are captured. Do not summarize away specifics — cite file paths, commit SHAs, flag values, measurements.

**Merge conflict note:** Two parallel branches appending continuation blocks to the same session log will collide at merge time. If you know this is running from a worktree and there are in-flight sibling branches touching the same epic, prefer creating a new session log over continuation.

### Step 3: Update TaskNote Epic + Stories

After the session log is written, update the project management layer. This logic is ported from the deprecated `/notebooklm-vault session-handoff` flow.

#### Find or create the epic

If the session has a linked epic, read it:

```bash
obsidian read file="{epic-id}-{slug}"
```

If Obsidian isn't running, `Read` the file directly at `{tasknotes_path}/Tasks/Epic/{epic-id}-{slug}.md`.

If the work warrants a new epic and none exists:
1. Read the next ID from `{tasknotes_path}/meta/{task_prefix}counter`.
2. Verify it doesn't collide with existing tasks under `{tasknotes_path}/Tasks/`. Task IDs must be globally unique.
3. Increment the counter and write it back.
4. Create the epic at `{tasknotes_path}/Tasks/Epic/{id}-{slug}.md` with standard TaskNote frontmatter (see the frontmatter conventions in `skills/ark-tasknotes/SKILL.md`).
5. For bugs, create in `{tasknotes_path}/Tasks/Bug/{id}-{slug}.md` instead.

#### Append session reference to the epic body

```bash
obsidian property:set name="session" value="S{NNN}" file="{epic-id}-{slug}" silent
obsidian append file="{epic-id}-{slug}" content="\n- [[S{NNN}-{slug}]] — YYYY-MM-DD: {one-line summary}" silent
```

Obsidian-unavailable fallback: `Read` the epic file, add the session reference to the body, and `Edit` the `session:` frontmatter field.

#### Update related stories

```bash
obsidian backlinks file="{epic-id}-{slug}"
```

For each story returned:
1. Read the story's current status: `obsidian property:read name="status" file="{story-id}"`.
2. Determine if the story was worked on in this session:
   - Does the session log mention this story's topic or feature?
   - Were files related to this story changed? (cross-reference `git diff --name-only`)
3. If yes, update its status based on the session's outcome:
   - Work completed and verified → `done`
   - Work started but not finished → `in-progress`
   - Work blocked by an issue → `blocked`
4. Update the story's session reference:
   ```bash
   obsidian property:set name="session" value="S{NNN}" file="{story-id}" silent
   ```

Obsidian-unavailable fallback: `Glob` `{tasknotes_path}/Tasks/Story/*.md`, `Grep` for the epic's wikilink to find backlinking stories, and `Edit` their frontmatter directly.

#### Compute and write epic status

After updating all stories, read every story's status:

```bash
obsidian property:read name="status" file="{story-id}"
```

- If **all** stories are `done` → mark the epic as `done`
- If **any** story is `blocked` → mark the epic as `blocked`
- Otherwise → mark the epic as `in-progress`

```bash
obsidian property:set name="status" value="{computed-status}" file="{epic-id}-{slug}" silent
```

**TaskNote writes are gated on Obsidian availability.** When Obsidian is unavailable, the fallback `Read`/`Edit` path above must be executed explicitly — do not silently skip TaskNote updates.

### Step 4: Extract Compiled Insights from the Session Log

This step addresses the **session log knowledge burial** problem (see `vault/Compiled-Insights/Session-Log-Knowledge-Burial.md`): durable findings locked inside chronological session logs are invisible to vault retrieval unless promoted to dedicated insight pages.

**Input selection (depends on whether Step 2 ran):**
- **If Step 2 wrote a session log** — re-read it as the primary source for knowledge extraction. Use `git diff` as a secondary source for anything that wasn't captured in the session log body.
- **If Step 2 was skipped** (user chose to skip on the ad-hoc docs sync prompt) — there is no new session log. Use `git diff` and any docs modified in this invocation as the primary source. Do **not** mine a previous session log for extraction — that content is already accounted for by prior `/wiki-update` runs.

Identify knowledge worth promoting:
- Architecture decisions and their rationale
- New patterns, abstractions, or conventions
- Research findings and experimental results
- Lessons learned from incidents or debugging
- "Things we learned do not work" (negative results — especially valuable)

Do **not** promote: boilerplate changes, minor bug fixes, config tweaks, routine dependency updates.

For each promoted piece of knowledge:
1. Check if an existing page already covers the topic (search `index.md` + `summary:` fields).
2. **If yes:** read the page, merge new information, update `last-updated:` and `summary:`.
3. **If no:** create a new page in the appropriate domain folder (see `vault/_meta/vault-schema.md`). Use Ark frontmatter:
   ```yaml
   ---
   title: "Page Title"
   type: compiled-insight | research | reference | guide
   tags: [{domain-tags from _meta/taxonomy.md}]
   summary: "<=200 char description"
   source-sessions: ["[[S{NNN}-{slug}]]"]
   source-tasks: []
   created: YYYY-MM-DD
   last-updated: YYYY-MM-DD
   ---
   ```
4. Add at least 2–3 wikilinks to related pages (use `index.md` to find candidates).
5. Always backlink the source session via `source-sessions:`.

Secondary input: `git diff` — cover any changes that weren't mentioned in the session log body.

### Step 5: Regenerate Index

```bash
cd {vault_path}
python3 _meta/generate-index.py
```

Verify the new session log and any new/updated insight pages appear in `index.md`.

### Step 6: Commit Vault Changes

```bash
cd {vault_path}
git add -A
git commit -m "docs: session {NNN} log + knowledge sync — {brief description}"
git push
```

Use a single commit for the session log + insight extraction + index regeneration. The commit message should name the session number and summarize both the session's work and any compiled insights that were extracted.
