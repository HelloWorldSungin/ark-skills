# Vault Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address three concrete problems in two Obsidian vaults: session log knowledge burial (AI vault), LLM retrieval inefficiency (both vaults), and lack of automated maintenance (both vaults).

**Architecture:** Three independent phases targeting each problem. Each vault is treated independently with its own TaskNotes schema, conventions, and Linear sync. No cross-vault harmonization. obsidian-wiki skills are used as tooling where they solve identified problems, not as a compliance target.

**Tech Stack:** Obsidian markdown, YAML frontmatter, Python 3 (for index generation script), obsidian-wiki skills (wiki-lint, cross-linker, tag-taxonomy)

**Spec:** `docs/vault-audit.md`

**Constraints:**
- TaskNotes folders, structure, and Linear-synced fields (`task-id`, `status`, `priority`, `task-type`, `project`, etc.): ZERO changes to existing fields
- Adding `summary:` as a NEW field to TaskNotes and session logs is allowed — it does not conflict with Linear sync (Linear ignores unknown frontmatter fields) and does not modify any existing field
- Session log format and `prev:`/`epic:` chaining: preserved
- Existing folder hierarchy: no reorganization
- File and folder names: no renames
- Canvas diagrams: untouched
- `00-Home.md` and MOC hierarchy: kept as-is

---

## Phase 0: Setup

### Task 0: Create Feature Branches in Both Vault Repos

**Files:**
- No file changes — git branch operations only

Each vault is a git submodule with its own history. All restructuring work happens on feature branches, not directly on the main branch.

- [ ] **Step 1: Create feature branch in AI vault**

```bash
cd Arknode-AI-Obsidian-Vault
git checkout -b vault-restructure
```

- [ ] **Step 2: Create feature branch in Poly vault**

```bash
cd Arknode-Poly-Obsidian-Vault
git checkout -b vault-restructure
```

- [ ] **Step 3: Verify both branches are active**

```bash
echo "AI vault:" && cd Arknode-AI-Obsidian-Vault && git branch --show-current
echo "Poly vault:" && cd Arknode-Poly-Obsidian-Vault && git branch --show-current
```

Expected: Both show `vault-restructure`.

**Note:** After each phase completes, update the parent repo to record the new submodule SHAs:

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/HelloWorldSungin/create-ark-skills
git add Arknode-AI-Obsidian-Vault Arknode-Poly-Obsidian-Vault
git commit -m "chore: update vault submodule refs after restructure phase N"
```

---

## Phase 1: Session Log Knowledge Extraction (AI Vault)

### Task 1: Create Compiled-Insights Directory and Page Template

**Files:**
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/.gitkeep`
- Create: `Arknode-AI-Obsidian-Vault/_Templates/Compiled-Insight-Template.md`

- [ ] **Step 1: Create the Compiled-Insights directory**

```bash
mkdir -p Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights
touch Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/.gitkeep
```

- [ ] **Step 2: Create the compiled insight page template**

Write to `Arknode-AI-Obsidian-Vault/_Templates/Compiled-Insight-Template.md`:

```markdown
---
title: "{{title}}"
type: compiled-insight
tags:
  - compiled-insight
  - {{domain-tag}}
summary: "{{summary <=200 chars}}"
source-sessions: []
source-tasks: []
created: {{date}}
last-updated: {{date}}
---

# {{title}}

## Key Finding

One-paragraph summary of the core insight. State the conclusion first, then the evidence.

## Evidence

Detailed evidence supporting the finding. Include specific numbers, metrics, and experimental results from the source sessions.

## Context

What problem or question prompted this investigation. Link to the relevant epic or task.

## Implications

What this finding means for future work. What should be done differently based on this knowledge.

## Sources

- [[Session-NNN]] — what was learned in this session
- [[ArkSignal-NNN]] — related task/epic
```

- [ ] **Step 3: Verify template**

```bash
head -20 Arknode-AI-Obsidian-Vault/_Templates/Compiled-Insight-Template.md
ls Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/
```

Expected: Template file shows frontmatter; directory exists with `.gitkeep`.

- [ ] **Step 4: Commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add Trading-Signal-AI/Research/Compiled-Insights/.gitkeep _Templates/Compiled-Insight-Template.md
git commit -m "feat: add Compiled-Insights directory and page template"
```

---

### Task 2: Extract TFT Performance Verdict

**Files:**
- Read: `Arknode-AI-Obsidian-Vault/TaskNotes/Tasks/Story/ArkSignal-034*.md`
- Read: Session logs referencing TFT (search below)
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/TFT-Performance-Verdict.md`

- [ ] **Step 1: Find all TFT-related sessions and tasks**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rl "tft\|TFT\|Temporal Fusion Transformer" Trading-Signal-AI/Session-Logs/ --include="*.md" | sort
grep -rl "tft\|TFT" TaskNotes/ --include="*.md" | sort
```

- [ ] **Step 2: Read ArkSignal-034 (the definitive TFT verdict task)**

Read the full content of the ArkSignal-034 story file. This contains 4-way deployment matrices (Filter ON/OFF x TFT ON/OFF) across multiple strategies. Extract:
- The exact performance numbers from each matrix
- The conclusion: "TFT conclusively does NOT help"
- Which strategies were tested (Mean Rev, MACD+RSI, Blend Mo/MR, Donchian)
- The evidence: NoTFT wins 2/3 or 3/3 across all strategies

- [ ] **Step 3: Read 2-3 supporting session logs**

Read the session logs identified in Step 1 that contain TFT experimental results. Extract any additional context, such as:
- When TFT testing began
- What the hypothesis was
- Any intermediate results before the final verdict

- [ ] **Step 4: Write the compiled insight page**

Write to `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/TFT-Performance-Verdict.md` following the template from Task 1. Include:
- **Key Finding:** "TFT (Temporal Fusion Transformer) conclusively does not improve trading signal quality. Across 4 strategies and 3 ticker sets, NoTFT configurations won 2/3 or 3/3 comparisons."
- **Evidence:** The 4-way deployment matrices with actual Sharpe ratios
- **Implications:** Do not revisit TFT for signal generation. Condition filters are the sole alpha source.
- Frontmatter `source-sessions:` and `source-tasks:` populated with actual references
- Frontmatter `summary:` field <=200 chars

- [ ] **Step 5: Verify wikilinks resolve**

```bash
cd Arknode-AI-Obsidian-Vault
# Check that all [[wikilinks]] in the new file point to existing files
grep -oP '\[\[([^\]]+)\]\]' Trading-Signal-AI/Research/Compiled-Insights/TFT-Performance-Verdict.md | sed 's/\[\[//;s/\]\]//' | while read link; do
  find . -name "${link}.md" -o -name "${link}" | head -1 | grep -q . || echo "BROKEN: $link"
done
```

Expected: No broken links.

- [ ] **Step 6: Commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add Trading-Signal-AI/Research/Compiled-Insights/TFT-Performance-Verdict.md
git commit -m "feat: compile TFT performance verdict from session logs and ArkSignal-034"
```

---

### Task 3: Extract Condition Filter Alpha Attribution

**Files:**
- Read: Session logs referencing condition filters, metalabel, alpha (search below)
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Condition-Filter-Alpha-Attribution.md`

- [ ] **Step 1: Find all condition-filter-related sessions**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rl "condition.filter\|alpha.source\|Sharpe.lift\|metalabel\|MetaLabel" Trading-Signal-AI/Session-Logs/ --include="*.md" | sort
grep -rl "condition.filter\|metalabel" Trading-Signal-AI/Research/ --include="*.md" | sort
```

- [ ] **Step 2: Read identified sessions and research pages**

Read each identified file. Extract:
- The finding: condition filters provide +1.0 to +2.5 Sharpe lift
- Which experiments established this
- How condition filters compare to other signal components (TFT, model changes, feature engineering)
- The conclusion: "condition filters are the sole alpha source"

- [ ] **Step 3: Write the compiled insight page**

Write to `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Condition-Filter-Alpha-Attribution.md` following the template. Include:
- **Key Finding:** Condition filters are the sole alpha source, contributing +1.0 to +2.5 Sharpe lift across all tested strategies.
- **Evidence:** Specific Sharpe ratios with and without filters, across strategies
- **Implications:** Focus optimization efforts on filter quality, not model architecture
- Populated `source-sessions:` and `source-tasks:` with actual references

- [ ] **Step 4: Verify wikilinks and commit**

```bash
cd Arknode-AI-Obsidian-Vault
grep -oP '\[\[([^\]]+)\]\]' Trading-Signal-AI/Research/Compiled-Insights/Condition-Filter-Alpha-Attribution.md | sed 's/\[\[//;s/\]\]//' | while read link; do
  find . -name "${link}.md" -o -name "${link}" | head -1 | grep -q . || echo "BROKEN: $link"
done
git add Trading-Signal-AI/Research/Compiled-Insights/Condition-Filter-Alpha-Attribution.md
git commit -m "feat: compile condition filter alpha attribution from session logs"
```

---

### Task 4: Extract Volume Divergence and Spot-to-Perp Migration

**Files:**
- Read: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Session-Logs/Session-327.md`
- Read: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Session-Logs/Session-328.md`
- Read: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Session-Logs/Session-329.md`
- Read: `Arknode-AI-Obsidian-Vault/TaskNotes/Tasks/Epic/ArkSignal-083*.md`
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Spot-to-Perp-Migration-Outcomes.md`

- [ ] **Step 1: Read Sessions 327-329 and ArkSignal-083**

These sessions document the spot-to-perp data migration epic. Extract:
- Session-327: Discovery of spot vs perp volume divergence (5-50x difference)
- Session-328: Fill parser, candle backfill, BinanceFuturesKlinesFetcher
- Session-329: Live perp pipeline, XGBoost volume feature swap, walk-forward A/B results
- ArkSignal-083: Epic summary with "all three perp variants lost to pure spot on donchian_breakout"

- [ ] **Step 2: Write the compiled insight page**

Write to `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Spot-to-Perp-Migration-Outcomes.md`. Include:
- **Key Finding:** Spot-to-perp volume swap provides no benefit. All three perp variants lost to pure spot on donchian_breakout.
- **Evidence:** Volume divergence (5-50x between spot and perp), A/B walk-forward results
- **Context:** The hypothesis was that perp volume would be a better signal for perp trading
- **Implications:** Continue using spot data for signals. Perp data may have value for other features but not volume.

- [ ] **Step 3: Verify and commit**

```bash
cd Arknode-AI-Obsidian-Vault
grep -oP '\[\[([^\]]+)\]\]' Trading-Signal-AI/Research/Compiled-Insights/Spot-to-Perp-Migration-Outcomes.md | sed 's/\[\[//;s/\]\]//' | while read link; do
  find . -name "${link}.md" -o -name "${link}" | head -1 | grep -q . || echo "BROKEN: $link"
done
git add Trading-Signal-AI/Research/Compiled-Insights/Spot-to-Perp-Migration-Outcomes.md
git commit -m "feat: compile spot-to-perp migration outcomes from Sessions 327-329"
```

---

### Task 5: Extract Model Architecture Decisions

**Files:**
- Read: Sessions referencing model architecture, XGBoost, Platt calibration, donchian_breakout
- Read: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Models/` (all files)
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Model-Architecture-Decisions.md`

- [ ] **Step 1: Find model architecture decision sessions**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rl "architecture.decision\|model.selection\|XGBoost\|Platt.calibration\|per-direction\|unified.pipeline" Trading-Signal-AI/Session-Logs/ --include="*.md" | sort
ls Trading-Signal-AI/Models/
```

- [ ] **Step 2: Read identified sessions and model docs**

Extract:
- Why XGBoost was chosen over alternatives
- The evolution from unified pipeline to per-direction PnL regressors
- Why Platt calibration is used
- The strategy consolidation (8 -> 1 strategies, Sessions 253-299)
- Current production model: donchian_breakout with per-direction PnL regressor

- [ ] **Step 3: Write the compiled insight page**

Write to `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Model-Architecture-Decisions.md`. Include:
- **Key Finding:** Summary of current model architecture and why it was chosen
- **Evidence:** Performance comparisons from strategy consolidation
- **Context:** Evolution from V1 unified pipeline to current per-direction approach
- **Implications:** What constraints the current architecture creates for future work

- [ ] **Step 4: Verify and commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add Trading-Signal-AI/Research/Compiled-Insights/Model-Architecture-Decisions.md
git commit -m "feat: compile model architecture decisions from session history"
```

---

### Task 6: Extract Failure Modes and Post-Mortems

**Files:**
- Read: Sessions referencing failures, bugs, post-mortems, incidents
- Read: Bug-type TaskNotes for patterns
- Create: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Failure-Modes-and-Lessons.md`

- [ ] **Step 1: Find failure-related sessions and bugs**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rl "failure\|post.mortem\|incident\|regression\|broke\|hotfix" Trading-Signal-AI/Session-Logs/ --include="*.md" | sort
ls TaskNotes/Tasks/Bug/
```

- [ ] **Step 2: Read identified sessions and bug reports**

Extract recurring patterns:
- Common failure modes (data pipeline breaks, model degradation, configuration errors)
- Lessons learned from each incident
- Preventive measures identified but not yet implemented

- [ ] **Step 3: Write the compiled insight page**

Write to `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/Compiled-Insights/Failure-Modes-and-Lessons.md`. Include:
- **Key Finding:** Categorized failure modes with frequency and severity
- **Evidence:** Specific incidents with links to source sessions and bug reports
- **Implications:** Which failure modes need systemic fixes vs. which are one-offs

- [ ] **Step 4: Verify and commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add Trading-Signal-AI/Research/Compiled-Insights/Failure-Modes-and-Lessons.md
git commit -m "feat: compile failure modes and post-mortem lessons from session history"
```

---

### Task 7: Update Research Index MOC

**Files:**
- Modify: `Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/00-Research-Index.md`

- [ ] **Step 1: Read current Research Index**

```bash
cat Arknode-AI-Obsidian-Vault/Trading-Signal-AI/Research/00-Research-Index.md
```

- [ ] **Step 2: Add Compiled Insights section**

Add a new `## Compiled Insights` section to the Research Index, after the existing sections. Include all compiled pages created in Tasks 2-6:

```markdown
## Compiled Insights

Cross-cutting findings extracted from session logs. Each page synthesizes evidence from multiple sessions into a standalone, retrievable knowledge page.

- [[TFT-Performance-Verdict]] — TFT conclusively does not improve signal quality across 4 strategies
- [[Condition-Filter-Alpha-Attribution]] — Condition filters are the sole alpha source (+1.0 to +2.5 Sharpe lift)
- [[Spot-to-Perp-Migration-Outcomes]] — Perp volume swap provides no benefit; spot data remains superior
- [[Model-Architecture-Decisions]] — Evolution from unified pipeline to per-direction PnL regressors
- [[Failure-Modes-and-Lessons]] — Categorized failure patterns from incident history
```

- [ ] **Step 3: Update the last-updated field in frontmatter**

Update the `last-updated:` field to today's date.

- [ ] **Step 4: Verify and commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add Trading-Signal-AI/Research/00-Research-Index.md
git commit -m "feat: add Compiled Insights section to Research Index"
```

---

### Phase 1 Checkpoint: Update Parent Repo

After all Phase 1 tasks are complete:

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/HelloWorldSungin/create-ark-skills
git add Arknode-AI-Obsidian-Vault
git commit -m "chore: update AI vault submodule ref after Phase 1 session log extraction"
```

---

## Phase 2: LLM Navigation Improvements (Both Vaults)

### Task 8: Write Vault Schema for AI Vault

**Files:**
- Create: `Arknode-AI-Obsidian-Vault/_meta/vault-schema.md`

- [ ] **Step 1: Create _meta directory**

```bash
mkdir -p Arknode-AI-Obsidian-Vault/_meta
```

- [ ] **Step 2: Read existing vault structure for reference**

```bash
cd Arknode-AI-Obsidian-Vault
find . -maxdepth 2 -type d ! -path './.obsidian*' ! -path './.git*' ! -path './.claude*' ! -path './.github*' ! -path './.notebooklm*' | sort
```

Also read `00-Home.md` and `_Templates/` to understand current conventions.

- [ ] **Step 3: Write vault-schema.md**

Write to `Arknode-AI-Obsidian-Vault/_meta/vault-schema.md`:

```markdown
---
title: Vault Schema
type: schema
tags:
  - meta
  - schema
summary: "Self-documenting guide to this vault's structure, conventions, and navigation patterns for LLMs and new collaborators."
created: 2026-04-07
last-updated: 2026-04-07
---

# ArkNode-AI Vault Schema

This document describes how this vault is organized. Read this first before navigating the vault.

## Entry Point

Start at [[00-Home]] for the top-level navigation hub. It links to all major subsystems.

## Folder Structure

| Directory | Purpose | Content Type |
|-----------|---------|-------------|
| `Infrastructure/` | Hardware, networking, containers, services | Reference docs with `type: reference` or `type: hardware` |
| `Infrastructure/Hardware/` | Physical server specs | Hardware reference pages |
| `Infrastructure/Networking/` | VPN, DNS, proxy config | Networking reference pages |
| `Infrastructure/Containers/` | CT100/CT110/CT120 container docs | Container reference pages |
| `Infrastructure/Services/` | Running services (MLflow, Grafana, etc.) | Service reference pages |
| `Trading-Signal-AI/` | Core ML trading project | Mixed: MOCs, research, session logs |
| `Trading-Signal-AI/Session-Logs/` | Chronological work journals | Session logs with `type: session-log` |
| `Trading-Signal-AI/Research/` | Research findings and analysis | Research pages with `type: research` |
| `Trading-Signal-AI/Research/Compiled-Insights/` | Cross-cutting findings extracted from session logs | Compiled insight pages with `type: compiled-insight` |
| `Trading-Signal-AI/Models/` | ML model documentation | Model reference pages |
| `Trading-Signal-AI/Strategies/` | Trading strategy docs | Strategy pages |
| `Trading-Signal-AI/Training/` | Training pipeline docs | Training reference pages |
| `Trading-Signal-AI/Operations/` | Deployment, monitoring guides | Operational guides |
| `TaskNotes/` | Work tracking (synced with Linear) | Epic/Story/Bug/Task pages |
| `TaskNotes/Tasks/Epic/` | Large initiatives | Epic task pages |
| `TaskNotes/Tasks/Story/` | Sprint-scoped work | Story task pages |
| `TaskNotes/Tasks/Bug/` | Bug reports | Bug task pages |
| `TaskNotes/Tasks/Task/` | Standalone tasks | Task pages |
| `TaskNotes/Archive/` | Completed work | Archived task pages |
| `_Templates/` | Page templates | Markdown templates |
| `_Attachments/` | Images, diagrams | Binary attachments (PNG) |
| `_meta/` | Vault metadata and governance | Schema, taxonomy docs |

## Frontmatter Conventions

### Standard Pages
All non-TaskNote pages use:
```yaml
title: "Page Title"
type: moc|reference|hardware|guide|research|session-log|compiled-insight|schema
tags: [array of strings]
last-updated: YYYY-MM-DD
summary: "<=200 char description for LLM retrieval"
```

### Session Logs
```yaml
date: YYYY-MM-DD
tags: [session-log, domain-tags, SNNN]
session: NNN
status: complete|in-progress
epic: "[[Epic-Name]]"
prev: "[[Session-NNN]]"
summary: "<=200 char description of what was discovered/decided"
```

### TaskNotes (DO NOT MODIFY existing fields — synced with Linear)

Core fields (present in nearly all TaskNotes):
```yaml
title: "Task Title"
tags: [task, epic|story|bug|task]
task-id: "ArkSignal-NNN"
task-type: epic|story|bug|task
status: backlog|todo|in-progress|done
priority: low|medium|high|critical
project: "trading-signal-ai"
work-type: docs|research|deployment|development
urgency: blocking|high|normal|low
created: "YYYY-MM-DD"
```

Common optional fields:
```yaml
component: module_name              # ~116 files
session: "NNN"                      # ~117 files — links to session log
scheduled: "YYYY-MM-DD"            # ~81 files
due: "YYYY-MM-DD"                  # ~81 files
projects: ["project-name"]         # ~83 files (array form)
blockedBy: ["[[Task-ID]]"]         # ~43 files
related: ["[[Task-ID]]"]           # ~19 files
resolved: "YYYY-MM-DD"            # ~7 files
severity: low|medium|high|critical # bugs only, ~11 files
pr: "#NNN"                         # ~6 files
```

### Compiled Insights
```yaml
title: "Insight Title"
type: compiled-insight
tags: [compiled-insight, domain-tag]
summary: "<=200 char finding summary"
source-sessions: [session numbers]
source-tasks: [task IDs]
created: YYYY-MM-DD
last-updated: YYYY-MM-DD
```

## Navigation Patterns

- **Human navigation:** `00-Home.md` -> `00-Project-Overview.md` -> domain-specific MOCs -> individual pages
- **LLM navigation:** Read `index.md` (flat catalog with summaries) -> use `summary:` fields to decide which pages to open -> read full pages only when needed
- **Session history:** Follow `prev:` links backward through session chain, or use `epic:` field to find all sessions for an epic
- **Task tracking:** Filter TaskNotes by `status:`, `priority:`, `task-type:`, or `component:` in frontmatter

## Cross-Linking Convention

Use `[[wikilinks]]` for all internal references. Every page should link to related pages. Session logs link to their epic and previous session. TaskNotes link to related tasks via the `related:` field.
```

Adjust the content based on what you observe in the actual vault structure.

- [ ] **Step 4: Verify and commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add _meta/vault-schema.md
git commit -m "feat: add vault schema doc for LLM and collaborator onboarding"
```

---

### Task 9: Write Vault Schema for Poly Vault

**Files:**
- Create: `Arknode-Poly-Obsidian-Vault/_meta/vault-schema.md`

- [ ] **Step 1: Create _meta directory**

```bash
mkdir -p Arknode-Poly-Obsidian-Vault/_meta
```

- [ ] **Step 2: Read existing vault structure**

```bash
cd Arknode-Poly-Obsidian-Vault
find . -maxdepth 2 -type d ! -path './.obsidian*' ! -path './.git*' ! -path './.claude*' ! -path './.github*' ! -path './.notebooklm*' | sort
```

Also read `00-Home.md`, `ArkNode-Poly/00-Project-Overview.md`, and `TaskNotes/00-Project-Management-Guide.md`.

- [ ] **Step 3: Write vault-schema.md**

Write to `Arknode-Poly-Obsidian-Vault/_meta/vault-schema.md` following the same structure as Task 8, but reflecting this vault's specific:
- Directory layout (`ArkNode-Poly/Architecture/`, `ArkNode-Poly/Research/`, etc.)
- TaskNotes frontmatter: uses the same core fields as AI vault (`task-id`, `status`, `priority`, `task-type`, `project`, `work-type`, `urgency`, `created`) PLUS Poly-specific optional fields: `parent:` (~5 files), `depends-on:` (~4 files), `updated:` (~11 files), `completed:` (~5 files). Also uses `component:` (~53 files), `blockedBy:` (~30 files), `related:` (~53 files) — do NOT claim these were replaced.
- Session log conventions (24 sessions, `S001`-`S024`)
- The Poly vault's specific `type` values

- [ ] **Step 4: Verify and commit**

```bash
cd Arknode-Poly-Obsidian-Vault
git add _meta/vault-schema.md
git commit -m "feat: add vault schema doc for LLM and collaborator onboarding"
```

---

### Task 10: Summary Backfill — Sample Batch (AI Vault, 10 Pages)

**Files:**
- Modify: 10 pages in `Arknode-AI-Obsidian-Vault/` (architecture and research docs first)

- [ ] **Step 1: Identify the 10 highest-value pages for sample batch**

These are the architecture and research pages that LLMs would most benefit from having summaries for:

```bash
cd Arknode-AI-Obsidian-Vault
echo "=== Architecture docs ==="
ls Infrastructure/Database-Architecture.md
ls Infrastructure/Hardware/Proxmox-Server.md
ls Trading-Signal-AI/Source-Code-Architecture.md
ls Trading-Signal-AI/00-Project-Overview.md
echo "=== Research docs ==="
ls Trading-Signal-AI/Research/00-Research-Index.md
ls Trading-Signal-AI/Research/Market-Condition-Analysis.md 2>/dev/null || true
ls Trading-Signal-AI/Research/Walk-Forward-Validation.md 2>/dev/null || true
echo "=== MOCs ==="
ls 00-Home.md
ls 00-Onboarding.md
echo "=== Models ==="
ls Trading-Signal-AI/Models/*.md 2>/dev/null | head -1
```

- [ ] **Step 2: For each page, read content and write a summary**

For each of the 10 pages:
1. Read the full page content
2. Write a summary of <=200 characters that captures the page's core purpose and content
3. Add `summary:` field to the YAML frontmatter, after `tags:` and before any other fields

Example edit for `00-Home.md`:

Before:
```yaml
---
title: ArkNode-AI Knowledge Base
type: moc
tags:
  - home
  - dashboard
last-updated: 2026-02-10
---
```

After:
```yaml
---
title: ArkNode-AI Knowledge Base
type: moc
tags:
  - home
  - dashboard
summary: "Navigation hub for ArkNode-AI: links to Infrastructure, Trading Signal AI, Ark-Trade, Ark-Line, TinyClaw, and key service URLs."
last-updated: 2026-02-10
---
```

Repeat for all 10 pages. Each summary must be:
- <=200 characters
- Descriptive enough that an LLM can decide whether to open the page
- Not just the title restated

- [ ] **Step 3: Review summary quality**

Read back the frontmatter of all 10 modified pages. Check:
- Is each summary <=200 chars?
- Does each summary describe what's IN the page, not just what the page IS?
- Would an LLM scanning summaries be able to decide which pages to read?

If any summary is weak, rewrite it.

- [ ] **Step 4: Commit the sample batch**

```bash
cd Arknode-AI-Obsidian-Vault
# Stage only the 10 specific files modified in this batch
git add 00-Home.md 00-Onboarding.md Infrastructure/Database-Architecture.md Infrastructure/Hardware/Proxmox-Server.md Trading-Signal-AI/Source-Code-Architecture.md Trading-Signal-AI/00-Project-Overview.md Trading-Signal-AI/Research/00-Research-Index.md
# Add the remaining 3 files from the sample batch
git add <remaining-files-modified>
git commit -m "feat: add summary: frontmatter to 10 high-value pages (sample batch)"
```

- [ ] **Step 5: User review gate**

Ask the user to review the 10 summaries. If the quality and style are approved, proceed to Task 11 for bulk backfill. If adjustments are needed, revise and re-commit before continuing.

---

### Task 11: Summary Backfill — Remaining AI Vault Pages

**Files:**
- Modify: All remaining `.md` files in `Arknode-AI-Obsidian-Vault/` (excluding `_Templates/`, `.obsidian/`, already-done pages, and TaskNotes)

- [ ] **Step 1: List all pages needing summaries**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rL "^summary:" --include="*.md" . | grep -v '.obsidian/' | grep -v '_Templates/' | grep -v '.git/' | grep -v '.claude' | grep -v '.github' | grep -v '.notebooklm' | sort
```

- [ ] **Step 2: Process pages in batches of 20**

For each batch:
1. Read each page's content
2. Generate a <=200 char summary
3. Add `summary:` to frontmatter
4. After each batch of 10, commit only the files modified in that batch:

```bash
cd Arknode-AI-Obsidian-Vault
git add <list each modified file explicitly>
git commit -m "feat: add summary: frontmatter to pages (batch N of M)"
```

**Note on effort:** This is AI-assisted work. Claude Code reads each page and generates the summary; the human reviews and approves. At ~10 pages per batch with review, expect ~30 batches for the AI vault. This is not hand-authoring 321 summaries — it's reviewing AI-generated summaries for accuracy.

**Important:** For TaskNotes pages, the summary should describe the task outcome/finding, not just restate the title. Example:
- Bad: "Bug report for signal pipeline"
- Good: "binance_funding_rate tables are dead code with zero active readers; docs-only resolution"

**Important:** For Session Logs, the summary should capture what was discovered or decided, not what was worked on. Example:
- Bad: "Session working on perp data migration"
- Good: "Discovered spot vs perp volume diverges 5-50x; implemented BinanceFuturesKlinesFetcher with TDD"

- [ ] **Step 3: Verify all pages now have summaries**

```bash
cd Arknode-AI-Obsidian-Vault
echo "Pages WITHOUT summary:"
grep -rL "^summary:" --include="*.md" . | grep -v '.obsidian/' | grep -v '_Templates/' | grep -v '.git/' | grep -v '.claude' | grep -v '.github' | grep -v '.notebooklm' | wc -l
echo "Pages WITH summary:"
grep -rl "^summary:" --include="*.md" . | grep -v '.obsidian/' | grep -v '_Templates/' | wc -l
```

Expected: 0 pages without summary (excluding templates and config directories).

---

### Task 12: Summary Backfill — Poly Vault

**Files:**
- Modify: All `.md` files in `Arknode-Poly-Obsidian-Vault/` (excluding `_Templates/`, `.obsidian/`)

- [ ] **Step 1: List all pages needing summaries**

```bash
cd Arknode-Poly-Obsidian-Vault
grep -rL "^summary:" --include="*.md" . | grep -v '.obsidian/' | grep -v '_Templates/' | grep -v '.git/' | grep -v '.claude' | grep -v '.github' | grep -v '.notebooklm' | sort
```

- [ ] **Step 2: Process all pages in batches of 20**

Same approach as Task 11. Read each page, generate <=200 char summary, add to frontmatter, commit in batches.

Apply the same quality guidelines:
- TaskNotes: describe outcome, not title
- Session Logs: describe discovery/decision, not activity
- Architecture docs: describe what the page documents and its scope

- [ ] **Step 3: Verify and final commit**

```bash
cd Arknode-Poly-Obsidian-Vault
echo "Pages WITHOUT summary:"
grep -rL "^summary:" --include="*.md" . | grep -v '.obsidian/' | grep -v '_Templates/' | grep -v '.git/' | grep -v '.claude' | grep -v '.github' | grep -v '.notebooklm' | wc -l
```

Expected: 0 pages without summary.

---

### Task 13: Generate index.md for AI Vault

**Files:**
- Create: `Arknode-AI-Obsidian-Vault/index.md`

- [ ] **Step 1: Write index generation script**

Write to `Arknode-AI-Obsidian-Vault/_meta/generate-index.py`:

```python
#!/usr/bin/env python3
"""Generate index.md from frontmatter across all vault pages."""

import os
import re
from pathlib import Path
from datetime import datetime, timezone

VAULT_ROOT = Path(__file__).parent.parent
# Only exclude non-content dirs; _meta IS content (schema, taxonomy)
EXCLUDE_DIRS = {'.obsidian', '.git', '.claude-plugin', '.github', '.notebooklm', '_Templates', '_Attachments'}

def extract_frontmatter(filepath):
    """Extract YAML frontmatter fields from a markdown file.
    
    Handles both flat fields (key: value) and list fields (tags: [a, b])
    as well as multi-line list syntax (tags:\\n  - a\\n  - b).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        return None

    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    fm = {}
    lines = match.group(1).split('\n')
    current_key = None

    for line in lines:
        # Multi-line list item: "  - value"
        list_item = re.match(r'^  - (.+)', line)
        if list_item and current_key:
            if current_key not in fm:
                fm[current_key] = []
            if isinstance(fm[current_key], list):
                fm[current_key].append(list_item.group(1).strip())
            continue

        # Flat key: value
        kv = re.match(r'^(\w[\w-]*):\s*(.*)', line)
        if kv:
            key = kv.group(1)
            value = kv.group(2).strip().strip('"').strip("'")
            current_key = key
            if value:
                # Inline list: [a, b, c]
                inline_list = re.match(r'^\[(.+)\]$', value)
                if inline_list:
                    fm[key] = [v.strip().strip('"').strip("'") for v in inline_list.group(1).split(',')]
                else:
                    fm[key] = value
            else:
                # Empty value — might be start of multi-line list
                fm[key] = []
        else:
            current_key = None

    return fm

def main():
    pages = []

    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            filepath = Path(root) / fname
            rel_path = filepath.relative_to(VAULT_ROOT)

            fm = extract_frontmatter(filepath)
            if fm is None:
                continue

            title = fm.get('title', fname.replace('.md', '').replace('-', ' '))
            category = fm.get('type', fm.get('task-type', 'uncategorized'))
            summary = fm.get('summary', '')
            if isinstance(summary, list):
                summary = ''

            # Use relative path as wikilink to avoid ambiguity from duplicate basenames
            wikilink = str(rel_path).replace('.md', '')

            # Extract tags as comma-separated string
            tags = fm.get('tags', [])
            if isinstance(tags, list):
                tags_str = ', '.join(tags)
            else:
                tags_str = str(tags)

            pages.append({
                'wikilink': wikilink,
                'title': title,
                'category': category,
                'path': str(rel_path.parent),
                'tags': tags_str,
                'summary': summary,
            })

    # Group by category
    categories = {}
    for page in pages:
        cat = page['category']
        categories.setdefault(cat, []).append(page)

    # Generate index with UTC timestamp
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        '---',
        'title: Vault Index',
        'type: index',
        'tags:',
        '  - index',
        '  - auto-generated',
        f'summary: "Machine-readable catalog of all {len(pages)} pages in this vault, grouped by type."',
        f'generated: {now_utc}',
        '---',
        '',
        '# Vault Index',
        '',
        f'Auto-generated catalog of {len(pages)} pages. For human navigation, see [[00-Home]].',
        '',
    ]

    for cat in sorted(categories.keys()):
        cat_pages = sorted(categories[cat], key=lambda p: p['title'])
        lines.append(f'## {cat} ({len(cat_pages)} pages)')
        lines.append('')
        for p in cat_pages:
            parts = [f'[[{p["wikilink"]}]]']
            if p['tags']:
                parts.append(f'`{p["tags"]}`')
            if p['summary']:
                parts.append(p['summary'])
            lines.append(f'- {" — ".join(parts)}')
        lines.append('')

    output_path = VAULT_ROOT / 'index.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'Generated index.md with {len(pages)} pages across {len(categories)} categories')

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the script**

```bash
cd Arknode-AI-Obsidian-Vault
python3 _meta/generate-index.py
```

Expected output: `Generated index.md with ~321 pages across N categories`

- [ ] **Step 3: Review generated index.md**

```bash
head -50 Arknode-AI-Obsidian-Vault/index.md
wc -l Arknode-AI-Obsidian-Vault/index.md
```

Verify: frontmatter is valid, categories are sensible, summaries are populated for pages that have them.

- [ ] **Step 4: Commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add index.md _meta/generate-index.py
git commit -m "feat: add machine-readable index.md and generation script"
```

---

### Task 14: Generate index.md for Poly Vault

**Files:**
- Create: `Arknode-Poly-Obsidian-Vault/index.md`
- Create: `Arknode-Poly-Obsidian-Vault/_meta/generate-index.py`

- [ ] **Step 1: Copy and adapt the index generation script**

```bash
mkdir -p Arknode-Poly-Obsidian-Vault/_meta
cp Arknode-AI-Obsidian-Vault/_meta/generate-index.py Arknode-Poly-Obsidian-Vault/_meta/generate-index.py
```

The script is vault-agnostic (uses `Path(__file__).parent.parent` for vault root), so no modifications needed.

- [ ] **Step 2: Run the script**

```bash
cd Arknode-Poly-Obsidian-Vault
python3 _meta/generate-index.py
```

Expected output: `Generated index.md with ~181 pages across N categories`

- [ ] **Step 3: Review and commit**

```bash
head -50 Arknode-Poly-Obsidian-Vault/index.md
cd Arknode-Poly-Obsidian-Vault
git add index.md _meta/generate-index.py
git commit -m "feat: add machine-readable index.md and generation script"
```

---

### Phase 2 Checkpoint: Update Parent Repo

After all Phase 2 tasks are complete:

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/HelloWorldSungin/create-ark-skills
git add Arknode-AI-Obsidian-Vault Arknode-Poly-Obsidian-Vault
git commit -m "chore: update vault submodule refs after Phase 2 LLM navigation improvements"
```

---

## Phase 3: Automated Maintenance Tooling (Both Vaults)

### Task 15: Create Tag Taxonomy for AI Vault

**Files:**
- Create: `Arknode-AI-Obsidian-Vault/_meta/taxonomy.md`

- [ ] **Step 1: Audit existing tags**

Extract tags from YAML frontmatter only (not prose bullets). This script reads each file, finds the `tags:` block in frontmatter, and extracts only those values:

```bash
cd Arknode-AI-Obsidian-Vault
python3 -c "
import re, os
from pathlib import Path
from collections import Counter

tags = Counter()
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.obsidian','.git','.claude-plugin','.github','.notebooklm'}]
    for f in files:
        if not f.endswith('.md'): continue
        try:
            content = open(os.path.join(root, f), encoding='utf-8').read()
        except: continue
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not m: continue
        fm = m.group(1)
        # Find tags section and extract list items
        in_tags = False
        for line in fm.split('\n'):
            if re.match(r'^tags:', line):
                in_tags = True
                # Check inline: tags: [a, b, c]
                inline = re.match(r'^tags:\s*\[(.+)\]', line)
                if inline:
                    for t in inline.group(1).split(','):
                        tags[t.strip().strip('\"').strip(\"'\")] += 1
                    in_tags = False
                continue
            if in_tags:
                item = re.match(r'^  - (.+)', line)
                if item:
                    tags[item.group(1).strip()] += 1
                else:
                    in_tags = False

for tag, count in tags.most_common(50):
    print(f'{count:4d}  {tag}')
"
```

This correctly extracts only YAML frontmatter tags, ignoring prose bullets and checklists.

- [ ] **Step 2: Write taxonomy.md**

Based on the tag audit, write `Arknode-AI-Obsidian-Vault/_meta/taxonomy.md`:

```markdown
---
title: Tag Taxonomy
type: schema
tags:
  - meta
  - taxonomy
summary: "Canonical tag vocabulary for ArkNode-AI vault. Source of truth for tag normalization."
created: 2026-04-07
last-updated: 2026-04-07
---

# Tag Taxonomy

Canonical tags for this vault. When adding tags to a page, use these exact spellings.

## Structural Tags

| Tag | Purpose | Used On |
|-----|---------|---------|
| `session-log` | Session log pages | Session-Logs/ |
| `task` | Work tracking pages | TaskNotes/ |
| `compiled-insight` | Extracted knowledge pages | Research/Compiled-Insights/ |
| `home` | Vault entry point | 00-Home.md |
| `moc` | Map of Content pages | Index/overview pages |

## Domain Tags

| Tag | Purpose | Aliases (normalize to canonical) |
|-----|---------|----------------------------------|
| `xgboost` | XGBoost model references | |
| `donchian-breakout` | Donchian breakout strategy | |
| `walk-forward` | Walk-forward validation | `walkforward` (normalize to `walk-forward`) |
| `metalabel` | MetaLabel filtering | |
| `paper-trading` | Paper trading system | |
| `backtest` | Backtesting references | `backtesting` (normalize to `backtest`) |
| `infrastructure` | Hardware/networking/services | |
| `deployment` | Deployment operations | |
| `training` | ML training pipeline | |

## Component Tags

| Tag | Purpose |
|-----|---------|
| `ct100` | CT100 Trading container |
| `ct110` | CT110 Research container |
| `ct120` | CT120 Database container |

## Session Tags

Session logs use `SNNN` format (e.g., `S329`) for unique identification.
```

Adjust based on actual tag audit results. Resolve the `walk-forward`/`walkforward` inconsistency by choosing `walk-forward` as canonical.

- [ ] **Step 3: Fix tag spelling inconsistencies**

```bash
cd Arknode-AI-Obsidian-Vault
grep -rl "  - walkforward" --include="*.md" . | head -20
```

For each file using `walkforward`, replace with `walk-forward`:

```bash
# Example for each file found
sed -i '' 's/  - walkforward/  - walk-forward/' <filepath>
```

- [ ] **Step 4: Commit**

```bash
cd Arknode-AI-Obsidian-Vault
git add _meta/taxonomy.md
# Stage only the files where walkforward was replaced
git add <list each file with normalized tags>
git commit -m "feat: add tag taxonomy and normalize walk-forward spelling"
```

---

### Task 16: Create Tag Taxonomy for Poly Vault

**Files:**
- Create: `Arknode-Poly-Obsidian-Vault/_meta/taxonomy.md`

- [ ] **Step 1: Audit existing tags**

Use the same frontmatter-only tag extraction as Task 15:

```bash
cd Arknode-Poly-Obsidian-Vault
python3 -c "
import re, os
from collections import Counter

tags = Counter()
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in {'.obsidian','.git','.claude-plugin','.github','.notebooklm'}]
    for f in files:
        if not f.endswith('.md'): continue
        try:
            content = open(os.path.join(root, f), encoding='utf-8').read()
        except: continue
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if not m: continue
        fm = m.group(1)
        in_tags = False
        for line in fm.split('\n'):
            if re.match(r'^tags:', line):
                in_tags = True
                inline = re.match(r'^tags:\s*\[(.+)\]', line)
                if inline:
                    for t in inline.group(1).split(','):
                        tags[t.strip().strip('\"').strip(\"'\")] += 1
                    in_tags = False
                continue
            if in_tags:
                item = re.match(r'^  - (.+)', line)
                if item:
                    tags[item.group(1).strip()] += 1
                else:
                    in_tags = False

for tag, count in tags.most_common(50):
    print(f'{count:4d}  {tag}')
"
```

- [ ] **Step 2: Write taxonomy.md**

Write `Arknode-Poly-Obsidian-Vault/_meta/taxonomy.md` following the same structure as Task 15, but with this vault's specific tags (e.g., `polymarket`, `forecaster`, `enrichment`, `ci-cd`, `kimi-k`, `openspace`, etc.).

- [ ] **Step 3: Commit**

```bash
cd Arknode-Poly-Obsidian-Vault
git add _meta/taxonomy.md
git commit -m "feat: add tag taxonomy for ArkNode-Poly vault"
```

---

### Task 17: Run Wiki-Lint on AI Vault

**Files:**
- Read: All `.md` files in `Arknode-AI-Obsidian-Vault/`
- Modify: Files with broken links or missing frontmatter (as identified by lint)

- [ ] **Step 1: Set up environment for obsidian-wiki skills**

The wiki-lint skill expects `OBSIDIAN_VAULT_PATH` to be set. Since we're running manually, we'll perform the lint checks directly.

- [ ] **Step 2: Check for broken wikilinks**

```bash
cd Arknode-AI-Obsidian-Vault
# Extract all wikilinks and check if target files exist
grep -roh '\[\[[^]]*\]\]' --include="*.md" . | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u | while read link; do
  # Skip links with # (section links)
  base=$(echo "$link" | sed 's/#.*//')
  [ -z "$base" ] && continue
  found=$(find . -name "${base}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "BROKEN: [[${link}]]"
done
```

- [ ] **Step 3: Check for pages missing frontmatter**

```bash
cd Arknode-AI-Obsidian-Vault
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './.claude*' ! -path './.github/*' ! -path './.notebooklm/*' | while read f; do
  head -1 "$f" | grep -q "^---" || echo "NO FRONTMATTER: $f"
done
```

- [ ] **Step 4: Fix identified issues**

For each broken link or missing frontmatter issue:
1. Read the file to understand context
2. Fix the broken link (correct spelling, add missing page, or remove dead link)
3. Add frontmatter to pages missing it

- [ ] **Step 5: Commit fixes**

```bash
cd Arknode-AI-Obsidian-Vault
# Stage only files that were fixed
git add <list each fixed file>
git commit -m "fix: resolve broken wikilinks and missing frontmatter (wiki-lint pass)"
```

---

### Task 18: Run Wiki-Lint on Poly Vault

**Files:**
- Read: All `.md` files in `Arknode-Poly-Obsidian-Vault/`
- Modify: Files with issues (as identified by lint)

- [ ] **Step 1: Check for broken wikilinks**

```bash
cd Arknode-Poly-Obsidian-Vault
grep -roh '\[\[[^]]*\]\]' --include="*.md" . | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u | while read link; do
  base=$(echo "$link" | sed 's/#.*//')
  [ -z "$base" ] && continue
  found=$(find . -name "${base}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "BROKEN: [[${link}]]"
done
```

- [ ] **Step 2: Check for pages missing frontmatter**

```bash
cd Arknode-Poly-Obsidian-Vault
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './.claude*' ! -path './.github/*' ! -path './.notebooklm/*' | while read f; do
  head -1 "$f" | grep -q "^---" || echo "NO FRONTMATTER: $f"
done
```

- [ ] **Step 3: Regenerate full orphan list and fix**

The audit identified 12 orphaned files (6.6%) but only named 5. Regenerate the complete list:

```bash
cd Arknode-Poly-Obsidian-Vault
# Find all pages that are never referenced by a [[wikilink]] from another page
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './.claude*' ! -path './.github/*' ! -path './.notebooklm/*' ! -path './_Templates/*' | while read f; do
  basename=$(basename "$f" .md)
  # Count incoming wikilinks from OTHER files
  incoming=$(grep -rl "\[\[$basename" --include="*.md" . 2>/dev/null | grep -v "$f" | wc -l | tr -d ' ')
  [ "$incoming" -eq 0 ] && echo "ORPHAN: $f"
done
```

For each orphan found:
1. Determine if it should be linked from an existing MOC, parent epic, or index page
2. Add the appropriate `[[wikilink]]` from the parent page
3. If it's a template or config file, it's expected to be orphaned — skip it

- [ ] **Step 4: Commit fixes**

```bash
cd Arknode-Poly-Obsidian-Vault
# Stage only files that were fixed
git add <list each fixed file>
git commit -m "fix: resolve broken wikilinks, orphans, and missing frontmatter (wiki-lint pass)"
```

---

### Task 19: Run Cross-Linker on Both Vaults

**Files:**
- Modify: Pages in both vaults where unlinked mentions of other pages exist

- [ ] **Step 1: Cross-link pass on AI vault**

For the AI vault, the cross-linker has marginal value (5.1 links/file already). Focus on session logs, which are most likely to mention concepts without linking them:

```bash
cd Arknode-AI-Obsidian-Vault
# Find pages that are mentioned by name in session logs but not wikilinked
for page in $(find Trading-Signal-AI/Research Trading-Signal-AI/Models Trading-Signal-AI/Strategies Infrastructure -name "*.md" | sed 's|.*/||;s|\.md$||'); do
  unlinked=$(grep -rl "$page" Trading-Signal-AI/Session-Logs/ --include="*.md" | xargs grep -L "\[\[$page\]\]" 2>/dev/null)
  [ -n "$unlinked" ] && echo "UNLINKED: $page in: $unlinked"
done
```

For each unlinked mention found, add the `[[wikilink]]` around the first natural occurrence in the text.

- [ ] **Step 2: Cross-link pass on Poly vault**

Same approach for the Poly vault:

```bash
cd Arknode-Poly-Obsidian-Vault
for page in $(find ArkNode-Poly/Architecture ArkNode-Poly/Research ArkNode-Poly/Operations -name "*.md" | sed 's|.*/||;s|\.md$||'); do
  unlinked=$(grep -rl "$page" ArkNode-Poly/Session-Logs/ --include="*.md" | xargs grep -L "\[\[$page\]\]" 2>/dev/null)
  [ -n "$unlinked" ] && echo "UNLINKED: $page in: $unlinked"
done
```

- [ ] **Step 3: Review and commit**

Review all proposed link additions. Accept only high-confidence matches (exact page name mentioned in body text).

```bash
cd Arknode-AI-Obsidian-Vault
git add <list each file with new wikilinks>
git commit -m "feat: add missing wikilinks discovered by cross-linker pass"

cd ../Arknode-Poly-Obsidian-Vault
git add <list each file with new wikilinks>
git commit -m "feat: add missing wikilinks discovered by cross-linker pass"
```

- [ ] **Step 4: Update parent repo submodule refs**

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/HelloWorldSungin/create-ark-skills
git add Arknode-AI-Obsidian-Vault Arknode-Poly-Obsidian-Vault
git commit -m "chore: update vault submodule refs after Phase 3 maintenance"
```

---

## Task Dependency Map

```
Phase 0 (setup):
  Task 0 (create branches) → all other tasks

Phase 1 (AI Vault only):
  Task 1 → Task 2, 3, 4, 5, 6 (parallel) → Task 7 → Phase 1 Checkpoint

Phase 2 (both vaults, independent):
  Task 8, 9 (parallel, independent vaults)
  Task 10 → Task 11 (sample must be approved before bulk)
  Task 12 (Poly vault, independent of AI)
  Task 11 → Task 13 (AI index needs AI summaries)
  Task 12 → Task 14 (Poly index needs Poly summaries)
  Task 13 → Task 14 (Poly copies generate-index.py from AI vault)

Phase 3 (both vaults, independent):
  Task 15, 16 (parallel, independent vaults)
  Task 17, 18 (parallel, independent vaults, after taxonomy)
  Task 19 (after lint fixes, can be parallel across vaults)
```

Phases 1, 2, and 3 are independent and can be done in any order. Within each phase, the dependencies above apply.
