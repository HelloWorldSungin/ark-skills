<workflow name="sync-skills">
<title>Skill Sync / Heal</title>
<description>Analyze code changes on the current branch, then check all project-level Claude Code skills for references that have drifted. Updates stale skills so they stay accurate as the codebase evolves.</description>

<project_skills>
All project skills live in `.claude/skills/`:

| Skill | What it references |
|-------|--------------------|
| notebooklm-vault | Vault paths, sync scripts, NotebookLM config |
| ark-code-review | Branch name, source paths, vault paths, test patterns |
| codebase-maintenance | Vault paths, workflow structure, skill inventory |
</project_skills>

<steps>
<step_1>
<title>Analyze Branch Changes</title>
<actions>
<action>Run `git diff --name-only {base_branch}..HEAD` — get the list of all changed files</action>
<action>Run `git log --oneline {base_branch}..HEAD` — understand the nature of changes</action>
<action>Categorize changes into areas that skills might reference: scripts, configs, source modules, paths</action>
</actions>
</step_1>

<step_2>
<title>Map Changes to Affected Skills</title>
<description>Each code area can affect specific skills. Use this mapping to narrow down which skills need checking.</description>
<mapping>
| Code Change Area | Skills Potentially Affected |
|-----------------|---------------------------|
| `scripts/` | notebooklm-vault (if sync scripts changed) |
| ark-code-review | Branch name, source paths, vault paths, test patterns |
| `vault/` structure changes | notebooklm-vault, codebase-maintenance |
| ark-code-review | Branch name, source paths, vault paths, test patterns |
| `.claude/skills/` | codebase-maintenance (this skill's own inventory) |
| `arknode-core/`, `agents/`, `orchestrator/` | Any skill that references source code paths |
| External repo changes | Any skill that references external repos |
</mapping>
<action>Build a shortlist of skills that need checking based on the branch changes</action>
</step_2>

<step_3>
<title>Audit Each Affected Skill</title>
<description>For each skill on the shortlist, read its SKILL.md and any workflow/reference files, then verify all references are still accurate.</description>
<actions>
<action>Read the skill's SKILL.md</action>
<action>Read any workflow files (`workflows/*.md`) and reference files (`references/*.md`)</action>
<action>Extract all concrete references: file paths, function names, script names, URLs, config keys</action>
<action>For each reference, verify it still exists and is accurate in the current codebase</action>
<action>Check the skill's description — does it still accurately describe what the skill does?</action>
<action>Check if new functionality added on the branch should be covered by an existing skill but isn't mentioned</action>
</actions>
</step_3>

<step_4>
<title>Generate Skill Sync Plan</title>
<action>
Present findings:

```
## Skill Sync Plan

### Branch Summary
- Branch: `branch-name`
- Key changes affecting skills: [brief summary]

### STALE SKILLS (needs update)
| # | Skill | File | Issue | Fix |
|---|-------|------|-------|-----|
| 1 | notebooklm-vault | SKILL.md | References old vault path | Update path |
| ark-code-review | Branch name, source paths, vault paths, test patterns |

### SKILLS UP TO DATE
| # | Skill | Last Verified |
|---|-------|---------------|
| 1 | codebase-maintenance | Today |

### NEW SKILL NEEDED (optional)
| # | Suggested Skill | Reason |
|---|----------------|--------|
| 1 | research-pipeline | New research pipeline added on branch, no skill covers it |
```
</action>
</step_4>

<step_5>
<title>Execute Skill Updates</title>
<actions>
<action>For each stale skill, apply the minimum edit needed to make it accurate</action>
<action>Update file paths, function names, URLs, config keys</action>
<action>Add new functionality coverage where branch changes introduced things a skill should know about</action>
<action>Update the project_skills table in this workflow file if skills were added or removed</action>
<action>Do NOT rewrite skills that are working fine — only fix drifted references</action>
</actions>
</step_5>

<step_6>
<title>Verify Updates</title>
<actions>
<action>Re-read each modified skill file to verify edits are correct</action>
<action>Grep modified skills for any remaining references to old paths/names that were changed on the branch</action>
<action>Ensure skill descriptions still accurately trigger for their intended use cases</action>
</actions>
</step_6>
</steps>

<success_criteria>
<criterion>Branch changes mapped to potentially affected skills</criterion>
<criterion>Each affected skill audited for stale references</criterion>
<criterion>Stale references updated with minimal, targeted edits</criterion>
<criterion>No skills reference files, functions, or configs that no longer exist</criterion>
<criterion>New branch functionality covered by existing skills where appropriate</criterion>
</success_criteria>
</workflow>
