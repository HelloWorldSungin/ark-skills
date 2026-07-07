<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-13 | Updated: 2026-04-13 -->

# docs

## Purpose

Plugin-level documentation that is too long for `README.md` but not a skill itself: the vault restructuring audit and the superpowers planning artifacts (historical design records).

## Key Files

| File | Description |
|------|-------------|
| `vault-audit.md` | Findings from the vault restructuring audit (session log burial problem, incremental adoption recommendation). Historical artifact. Referenced by `project_vault_audit_findings.md` in auto-memory. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `agents/` | GitHub-Issues conventions consumed by mattpocock skills + `/ark-consult` (`issue-tracker.md`, `triage-labels.md`, `domain.md`). |
| `superpowers/` | Historical superpowers planning archive — `plans/` and `specs/` from the v1 design work. Dated records; retain historical mentions. |

## For AI Agents

### Working In This Directory

- `vault-audit.md` is a historical artifact of a specific audit. Do not rewrite it — if the audit's conclusions change, add a follow-up document and link it from the top of `vault-audit.md` rather than editing findings in place.
- `superpowers/plans/` and `superpowers/specs/` are a historical design archive. Do not rewrite them to match the current skill set — they record what was designed at the time (they retain mentions of retired skills by design).

### Testing Requirements

None — these are narrative documents. Verify by reading and confirming the guidance matches current skill behavior.

## Dependencies

### Internal

- `agents/*.md` → `/ark-consult`, `/ark-onboard`, and the mattpocock issue skills.
- `vault-audit.md` → historical; its subjects (the v1 vault-maintenance skills) were retired in v2.0.0.

<!-- MANUAL: -->
