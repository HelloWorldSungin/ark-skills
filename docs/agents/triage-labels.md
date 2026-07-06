# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ----------------------------------------- |
| `needs-triage`              | `needs-triage`        | Maintainer needs to evaluate this issue  |
| `needs-info`                 | `needs-info`          | Waiting on reporter for more information |
| `ready-for-agent`           | `ready-for-agent`     | Fully specified, ready for an AFK agent  |
| `ready-for-human`           | `ready-for-human`     | Requires human implementation            |
| `wontfix`                    | `wontfix`             | Will not be actioned                     |

This repo's own conventions (bootstrapped in Phase 2 of the v2 restructure,
`gh label create`) use the identical strings 1:1 — no remapping needed.

Additional labels exist on this repo beyond the five canonical triage roles:
type (`epic`, `story`, `task`, `bug`), priority (`P1`/`P2`/`P3`), and
component (`consultant`, `conventions`, `vault`, `onboarding`). These aren't
part of the triage state machine — see `docs/agents/issue-tracker.md` and
the label taxonomy this repo bootstrapped for their meaning.

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use
the corresponding label string from this table.
