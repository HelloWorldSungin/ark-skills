---
title: "Vault Layout Detection — Structural Markers Beat Config Strings"
type: compiled-insight
tags:
  - compiled-insight
  - vault
  - skill
summary: "Three-round recurring bug in notebooklm-vault-sync.sh — symlink traversal + standalone vs wrapped layout — kept resurfacing because retrieval scripts branched on the vault_root config string. Structural detection (marker dirs at vault root) survives misconfig where config-string parsing does not, and recurring fixes in the same file family are a layout-typing architectural smell."
source-sessions: []
source-tasks: []
created: 2026-04-25
last-updated: 2026-04-25
---

# Vault Layout Detection — Structural Markers Beat Config Strings

## Summary

`notebooklm-vault-sync.sh` got three rounds of "symlinks + standalone layout" fixes (commits `a30dbbb`, `172fc39`, then `1.21.5`). Every round patched a different ad-hoc branch on the `vault_root` config string. The architectural lesson: when the same retrieval script keeps drifting from what `/ark-onboard` writes, stop adding branches and start typing the layout from disk. Marker directories (`_meta/`, `_Templates/`, `TaskNotes/`) at vault root are the structural truth; the `vault_root` field in `.notebooklm/config.json` is just an opinion that can disagree with reality, especially when two configs (project-level + vault-level) coexist.

## Key Insights

### Three vault layouts, two configs, one source of truth

The Ark vault matrix:

| Layout | vault_root in config | Markers location |
|--------|---------------------|------------------|
| Standalone (centralized) | `"."` (vault-side) OR `"vault"` (project-side, via symlink) | `_meta/`, `_Templates/`, `TaskNotes/` directly under vault root |
| Wrapped / monorepo | `"vault"` | `_meta/` etc. nested inside `vault/<ProjectDocs>/` |
| Standalone (embedded) | `"vault"` | Markers at vault root (no symlink) |

Both project-level and vault-level configs may exist. Pre-1.21.5 the script took the `vault_root` string at face value: `"."` → standalone; anything else → wrapped (walk for project subdir). For centralized + standalone projects the project-level config carries `vault_root: "vault"` (it has to — it lives in the project repo, the vault sits across a symlink), which pushed the script into the wrapped branch. There's no project subdir in a standalone vault, so it landed on whatever non-excluded subdirectory came first. For a fresh Ark vault that's `Session-Logs/`, which is empty on a greenfield project. Sync ran to completion, "Added: 0", with a misleading WARN.

The fix: detect the layout by structure, not by config string.

```bash
is_standalone_vault() {
    local root="$1"
    [[ -d "$root/_meta" ]] || [[ -d "$root/_Templates" ]] || [[ -d "$root/TaskNotes" ]]
}

if [[ "$VAULT_ROOT_REL" == "." ]] || is_standalone_vault "$VAULT_ROOT"; then
    scan_base="$VAULT_ROOT"   # standalone — scan vault root directly
else
    # walk for project subdir (wrapped layout)
fi
```

`vault_root: "."` is a valid signal but not the only one. Marker detection makes the script robust to any project-level config that disagrees with disk reality — including configs left behind from prior install attempts or migration paths.

### macOS BSD find ignores symlinks without `-L`

For centralized vaults, `vault` is a symlink to `~/.superset/vaults/<proj>/`. macOS BSD `find` (and GNU `find` on Linux) does not descend into symlinked directories without the `-L` flag:

```bash
find vault -name "*.md" -type f       # 0 — does not traverse the symlink
find -L vault -name "*.md" -type f    # 11 — follows it
```

This is independent of any layout logic — it's a one-line fix at the discovery boundary. Not exotic; just the kind of thing that gets missed when a script is written before the centralized-vault layout was the default and never revisited when it became the default in v1.11.0.

### Folding stderr into JSON breaks downstream parsers

`notebooklm-py` v0.3.3 logs runtime warnings to stderr on empty notebooks:

```
HH:MM:SS WARNING [notebooklm._sources] Sources data for <id> is not a list (type=NoneType), returning empty list (API structure may have changed)
```

If the script captures with `2>&1` and pipes the result to `jq`, the timestamped warning lands at the start of the buffer and `jq` fails parsing at column 3 (the `:` in the timestamp). The script's other source-list call sites already used `2>/dev/null` — `fetch_notebook_sources` and the `dedupe_and_heal_notebook` refresh were the two outliers.

The pattern that survives both diagnostic visibility AND parser correctness:

```bash
err_log=$(mktemp)
if ! raw=$(notebooklm source list --notebook "$nb_id" --json 2>"$err_log"); then
    err_msg=$(cat "$err_log")
    rm -f "$err_log"
    die "Failed: $err_msg"
fi
rm -f "$err_log"
```

Stderr to a tempfile, surfaced only on non-zero exit. Never `2>&1` when the captured value will be parsed.

### Recurring fixes in the same file = architectural smell, not coincidence

Three rounds of fixes for "symlinks + standalone layout" in the same script (`a30dbbb` → `172fc39` → `1.21.5`) is a signal that the abstraction is wrong, not that the bugs are unrelated. The pattern: ad-hoc branches on `vault_root` scattered through multiple call sites (`resolve_scan_base`, the project-level config detection, the mine-vault.sh sister script) keep drifting from what `/ark-onboard` and `/notebooklm-vault setup` actually write across all layout variants.

The architectural fix worth doing as a follow-up: a single `vault_layout_type()` pass that returns an enum (e.g. `STANDALONE_DIRECT | STANDALONE_CENTRALIZED | WRAPPED`) once at script start, then routes off the enum everywhere. Stops the matrix from leaking into every call site.

### Skill-side cleanup closes the loop, defense-in-depth keeps it closed

Two ways to fix layout-driven sync bugs: defend in the script (option a), or stop creating the misconfig at the source (option b). 1.21.5 ships both:

- **Script-side (a):** `is_standalone_vault()` marker detection makes the script tolerant of misconfig.
- **Skill-side (b):** `/notebooklm-vault setup` step 4 now branches on layout — for standalone vaults, it fills in the existing vault-side config (written by `/ark-onboard` Step 15) instead of creating a redundant project-level config with `vault_root: "vault"`. The `/ark-onboard` layout diagram is amended to mark the project-level config as monorepo-only.

Both fixes solve the bug in isolation. Shipping both means the next time the matrix grows a layout variant, the script keeps working even if a skill misconfigures it.

## Evidence

Source commits:

- `a30dbbb` — first round, "symlink, standalone layout, sync-state tracking bugs"
- `172fc39` — second round, "actual root causes for mine-vault symlinks and vault-sync standalone layout"
- 1.21.5 (this conversation, branch `notebooklm-vault-bug`) — three independent bugs with mechanical repros

Mechanical repro (1.21.5):

```bash
ls -la vault                                # symlink → ~/.superset/vaults/<proj>
find vault -name "*.md" | wc -l             # 0 (broken)
find -L vault -name "*.md" | wc -l          # >0 (fixed)
notebooklm source list --notebook <id> --json 2>&1 | head -1
# starts with timestamped WARNING line — folds into jq pipe
```

End-to-end success criterion: a fresh `/ark-onboard` Standalone Full-tier project syncs exactly 2 sources (`00-Home.md`, `index.md`) on the first `/notebooklm-vault setup` with no manual intervention.

## Implications

- **For sync/retrieval scripts:** Detect vault layout structurally (marker dirs at root) before parsing `vault_root`. Treat config strings as advisory, not authoritative.
- **For shell→parser pipelines:** Never `2>&1` when the captured value will be parsed by `jq` or any structural reader. Use a tempfile for stderr and surface it only on non-zero exit.
- **For symlinked-vault discovery:** Always `find -L` against `vault` paths. The centralized-vault default (v1.11.0+) means `vault` is a symlink in production for almost every Ark project.
- **For architectural refactor decisions:** Three fixes for the same bug family in the same file means the abstraction is wrong. The next round on `notebooklm-vault-sync.sh` should consolidate layout typing into a single enum-returning pass and route from there. Track this as a follow-up rather than another patch.
- **For skill design:** When a skill writes config that another skill consumes, the consumer should defend against config that disagrees with disk. `/ark-onboard` and `/notebooklm-vault setup` are two ends of the same pipeline; the sync script reads what they wrote and must work even when one of them gets a layout case wrong.
