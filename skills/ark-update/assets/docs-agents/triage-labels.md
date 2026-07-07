# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those
roles to the label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

The strings are identical 1:1 — no remapping needed.

Additional labels exist beyond the five triage roles: type (`epic`, `story`,
`task`, `bug`), priority (`P1`/`P2`/`P3`), and component (repo-specific). These
aren't part of the triage state machine — see `docs/agents/issue-tracker.md`.

Triage flow: new issue → `needs-triage` → (`needs-info` ⇄ reporter) →
`ready-for-agent` or `ready-for-human` → closed (or `wontfix`).
