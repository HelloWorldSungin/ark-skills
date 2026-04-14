<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-13 | Updated: 2026-04-13 -->

# docs

## Purpose

Plugin-level documentation that is too long for `README.md` but not a skill itself: onboarding narrative, vault restructuring audit, and the superpowers planning artifacts for in-flight work.

## Key Files

| File | Description |
|------|-------------|
| `onboarding-guide.md` | Long-form walkthrough for first-time users of the plugin — complements `/ark-onboard` and the `README.md` install section. |
| `vault-audit.md` | Findings from the vault restructuring audit (session log burial problem, incremental adoption recommendation). Referenced by `project_vault_audit_findings.md` in auto-memory. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `superpowers/` | Superpowers planning artifacts — `plans/` (implementation plans) and `specs/` (specs/requirements) for in-flight work. |

## For AI Agents

### Working In This Directory

- `onboarding-guide.md` should stay aligned with the `/ark-onboard` skill. If the skill changes its flow (new branch, new prerequisite, renamed step), update this file in the same commit.
- `vault-audit.md` is a historical artifact of a specific audit. Do not rewrite it — if the audit's conclusions change, add a follow-up document and link it from the top of `vault-audit.md` rather than editing findings in place.
- `superpowers/plans/` and `superpowers/specs/` are working documents for a single feature branch. Clean up merged/abandoned plans when the branch lands.

### Testing Requirements

None — these are narrative documents. Verify by reading and confirming the guidance matches current skill behavior.

## Dependencies

### Internal

- `onboarding-guide.md` → `/ark-onboard` (skill), `README.md` (install section).
- `vault-audit.md` → `skills/wiki-setup/`, `skills/wiki-update/`.

<!-- MANUAL: -->
