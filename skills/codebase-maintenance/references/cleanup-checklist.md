# Cleanup Checklist

Reusable checklist for codebase maintenance. Copy and fill in during cleanup workflows.

## Pre-Cleanup

- [ ] Planning mode activated
- [ ] Current branch identified: ___
- [ ] Branch commits reviewed (`git log master..HEAD`)
- [ ] Local HEAD commit: ___

## Code & Scripts

- [ ] All scripts scanned for callers
- [ ] Dead scripts identified (no callers, references removed features)
- [ ] Dead source code identified (uncalled functions, broken imports)
- [ ] Untracked files categorized (commit/ignore/delete)

## Skill Sync

- [ ] Branch changes mapped to potentially affected skills
- [ ] Each affected skill audited for stale references
- [ ] Stale file paths, function names, URLs updated
- [ ] New branch functionality covered by relevant skills
- [ ] Skill descriptions still accurately trigger

## Obsidian Vault Sync

- [ ] Branch changes mapped to vault documentation areas
- [ ] Relevant vault notes checked for staleness
- [ ] Missing documentation identified for new features/models
- [ ] Session-Logs index verified for recent sessions
- [ ] TaskNotes checked for relevant task status updates
- [ ] All vault writes use obsidian-markdown conventions
- [ ] `last-updated` frontmatter updated on modified notes

## Post-Cleanup

- [ ] User approved cleanup plan
- [ ] Deletions executed
- [ ] Updates applied
- [ ] Vault notes updated/created
- [ ] Changes committed with descriptive message
- [ ] Tests passed (if available)
