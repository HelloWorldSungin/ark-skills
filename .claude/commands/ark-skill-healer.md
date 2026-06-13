---
description: Heal ark-skills against upstream dependency changes — inventory referenced deps, diff upstream changelogs, surface required changes, opportunities, and retire-able workarounds as a ranked advisory report plus staged patches.
---

# /ark-skill-healer

Project-level skill. This command is the authoritative invocation surface (the
repo does NOT rely on `.claude/skills/` auto-discovery).

**Run the playbook at `.claude/skills/ark-skill-healer/SKILL.md`.** Read that file
and follow its Workflow steps 0–6 exactly. It is ADVISORY-ONLY: every write goes
to the gitignored `.omc/skill-healer/` surface; it must never edit ark-skills
source files.

Arguments (optional), forwarded to the SKILL.md workflow:
- `--dep <name>`   restrict the run to a single inventoried dependency
- `--dry-run`      inventory + diff only; skip patch staging
