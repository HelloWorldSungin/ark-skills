---
name: ark-update
description: Version-driven migration framework — replays pending destructive migrations then converges downstream project to the current ark-skills target profile. Runs when plugin bumps add new conventions. Distinct from /ark-onboard repair (failure-driven) and /ark-health (diagnostic-only).
---

# Ark Update

Version-driven migration framework for the ark-skills plugin. Every downstream project that installed ark-skills at an older version (or needs to catch up to HEAD) can run `/ark-update` to:

1. **Phase 1 — Replay pending destructive migrations** (rare; per-version YAML under `migrations/vX.Y.Z.yaml`)
2. **Phase 2 — Converge project to the current target profile** (every run; declarative YAML at `target-profile.yaml`)

The engine is written in Python (`scripts/migrate.py`). This SKILL.md is a thin LLM-facing wrapper that handles planning, progress rendering, user prompts, gate-flag resolution, and the `/ark-update` command surface.

## Context-Discovery Exemption

This skill is exempt from normal context-discovery. It must work when CLAUDE.md is missing, broken, or incomplete — because `/ark-update` may be the tool that *fixes* a broken CLAUDE.md through target-profile convergence. When CLAUDE.md is absent or malformed, the engine detects project state from the filesystem (via `.ark/migrations-applied.jsonl` bootstrap) and refuses to run on specific broken-file classes that require human judgment, pointing the user to `/ark-onboard repair`.

Never abort because CLAUDE.md is missing. That is one of the states this skill is designed to handle.

## Platform Support (v1.0)

**POSIX-only** (macOS + Linux + WSL2 bash). Native Windows cmd/powershell is NOT supported in v1.0. The `ARK_SKILLS_ROOT` resolver uses shell arithmetic and the Stage-5 manual runbook uses process substitution (`<(git show ...)`), both POSIX-specific. Windows-native support is a v1.1 follow-up if user demand exists.

## Command Surface

```bash
/ark-update              # full run: replay pending destructive + converge to target profile
/ark-update --dry-run    # plan report only; no writes
/ark-update --force      # skip dirty-tree refusal (use at your own risk)
```

## Boundary with Sibling Skills

| Skill | Trigger | Scope |
|-------|---------|-------|
| `/ark-onboard repair` | Failure-driven ("a /ark-health check failed, fix it") | Repair of broken state |
| `/ark-update` | Version-driven ("plugin updated, converge project conventions") | Replay destructive migrations + converge to target profile |
| `/ark-health` | Diagnostic ("what's the state?") | Read-only; surfaces version drift as "upgrade available: run /ark-update" |

`/ark-update` and `/ark-onboard repair` coexist independently — neither chains the other automatically. `/ark-update` refuses to run on malformed CLAUDE.md / `.mcp.json` / `.ark/migrations-applied.jsonl` and points back to `/ark-onboard repair`.

---

## Workflow

### Step 0: Preflight — Git Dirty-Tree Check

Before doing anything else, check whether the working tree has uncommitted changes.

```bash
git -C "$(pwd)" status --porcelain 2>/dev/null
```

- If output is **non-empty** and `--force` was NOT passed: refuse immediately.

  > "Working tree has uncommitted changes. Commit or stash your changes before running
  > /ark-update, or pass --force to override (not recommended)."

- If `--force` was passed: proceed with a warning:

  > "Warning: running /ark-update on a dirty working tree (--force). Changes made by the
  > engine may be interleaved with your uncommitted edits. Verify the result carefully."

- The engine also enforces this check internally (exit code 2), so a double-check here
  is for early user feedback only.

### Step 1: Resolve `ARK_SKILLS_ROOT`

In consumer projects (e.g., ArkNode-AI, ArkNode-Poly), this plugin's scripts live at
`~/.claude/plugins/cache/.../ark-skills/` — **not** at `./skills/` of the CWD. Resolve
once at the start; all subsequent script invocations use this absolute path.

```bash
# Already set by Claude Code when invoking a plugin skill? Prefer that.
if [ -n "${CLAUDE_PLUGIN_DIR:-}" ] && [ -d "$CLAUDE_PLUGIN_DIR" ]; then
    ARK_SKILLS_ROOT="$CLAUDE_PLUGIN_DIR"
# Otherwise, discover via the plugin marketplace.json anchor.
elif [ -f "$(pwd)/.claude-plugin/marketplace.json" ]; then
    # CWD is the ark-skills repo itself (dev/test mode)
    ARK_SKILLS_ROOT="$(pwd)"
else
    # Consumer project: search installed plugins.
    ARK_SKILLS_ROOT=$(find ~/.claude/plugins -maxdepth 6 -type d -name ark-skills 2>/dev/null | head -1)
fi

if [ -z "$ARK_SKILLS_ROOT" ] || [ ! -f "$ARK_SKILLS_ROOT/skills/ark-update/SKILL.md" ]; then
    echo "ark-skills plugin not found — cannot run /ark-update." >&2
    exit 1
fi
export ARK_SKILLS_ROOT
```

**All subsequent `python3 skills/...` invocations MUST be rewritten to
`python3 "$ARK_SKILLS_ROOT/skills/..."`.** Python modules invoked this way can
continue to use `Path(__file__).parent` for sibling-file resolution.

### Step 2: Gate-Flag Resolution

Resolve two boolean flags that gate optional target-profile entries. These are passed
to `migrate.py` as environment variables so the engine can skip inapplicable ops.

#### HAS_OMC Probe

Mirrors the probe in `skills/ark-workflow/SKILL.md` (canonical constants in
`skills/ark-workflow/references/omc-integration.md` § Section 0).

```bash
# Has OMC? (oh-my-claudecode — autonomous execution framework)
# OMC_CACHE_DIR canonical: ~/.claude/plugins/cache/omc
# (see skills/ark-workflow/references/omc-integration.md § Section 0)
if command -v omc >/dev/null 2>&1 || [ -d "$HOME/.claude/plugins/cache/omc" ]; then
    ARK_HAS_OMC=1
else
    ARK_HAS_OMC=0
fi
# ARK_SKIP_OMC=true forces HAS_OMC=false regardless of detection
# (emergency rollback — see references/omc-integration.md § Section 3)
[ "${ARK_SKIP_OMC:-}" = "true" ] && ARK_HAS_OMC=0
export ARK_HAS_OMC
```

When `ARK_HAS_OMC=0`, the engine skips target-profile entries with
`only_if_has_omc: true` (currently: the `omc-routing` managed region in CLAUDE.md).

#### Centralized-Vault Detection

Read the project's CLAUDE.md and look for a "Vault layout" row. Detection heuristic:

```bash
# Centralized-vault detection: look for 'Vault layout' row in CLAUDE.md.
# Heuristic: if CLAUDE.md exists AND contains a line matching 'Vault layout'
# (case-insensitive, as a table row or standalone heading), treat as standalone
# (project explicitly declared its layout, and standalone is the default).
# If CLAUDE.md is absent OR has no 'Vault layout' row, treat as centralized
# (older projects pre-dating the layout row, or new projects using symlink layout).
#
# Rationale: the 'Vault layout' row was introduced in /ark-onboard v1.11 to let
# projects opt into standalone mode. Projects without the row are presumed to use
# the centralized layout (symlink via scripts/setup-vault-symlink.sh). This is the
# conservative default — creating setup-vault-symlink.sh for a standalone project
# is harmless (the script checks for the symlink before writing), but skipping it
# for a centralized project would leave the vault symlink unmanaged.
CLAUDE_MD="$(pwd)/CLAUDE.md"
if [ -f "$CLAUDE_MD" ] && grep -qi "vault layout" "$CLAUDE_MD"; then
    ARK_CENTRALIZED_VAULT=0
else
    ARK_CENTRALIZED_VAULT=1
fi
export ARK_CENTRALIZED_VAULT
```

When `ARK_CENTRALIZED_VAULT=0`, the engine skips target-profile entries with
`only_if_centralized_vault: true` (currently: `scripts/setup-vault-symlink.sh`).

### Step 3: Pre-Run Warning (First-Time Marker Overwrites)

Before invoking the engine on a project that has existing managed regions, warn the
user that drift will trigger a backup:

> **Note:** If your CLAUDE.md contains managed regions (between `<!-- ark:begin ... -->`
> and `<!-- ark:end ... -->` markers) whose content differs from the current template,
> `/ark-update` will overwrite the managed content and save a backup to
> `.ark/backups/<timestamp>-<region-id>.bak`. The backup is byte-exact — no content
> is lost. Review the backup and the diff before committing. Run `/ark-update --dry-run`
> first to preview what will change without any writes.

Emit this warning only if the project CLAUDE.md exists and contains at least one
`<!-- ark:begin` marker. Skip the warning on fresh projects (no CLAUDE.md or no markers).

```bash
if [ -f "$(pwd)/CLAUDE.md" ] && grep -q '<!-- ark:begin' "$(pwd)/CLAUDE.md"; then
    echo ""
    echo "Note: managed regions detected in CLAUDE.md. Drifted content will be"
    echo "overwritten and backed up to .ark/backups/. Run --dry-run first to preview."
    echo ""
fi
```

### Step 4: Call migrate.py

Pass the resolved gate flags as environment variables:

```bash
ARK_HAS_OMC="$ARK_HAS_OMC" \
ARK_CENTRALIZED_VAULT="$ARK_CENTRALIZED_VAULT" \
python3 "$ARK_SKILLS_ROOT/skills/ark-update/scripts/migrate.py" \
    --project-root "$(pwd)" \
    --skills-root "$ARK_SKILLS_ROOT" \
    ${ARK_UPDATE_DRY_RUN:+--dry-run} \
    ${ARK_UPDATE_FORCE:+--force}
```

Where `ARK_UPDATE_DRY_RUN=1` and `ARK_UPDATE_FORCE=1` are set when the user passes
`--dry-run` or `--force` respectively to `/ark-update`.

Capture the exit code:

| Exit code | Meaning |
|-----------|---------|
| 0 | Success (or clean — nothing to do) |
| 1 | Unexpected error (I/O failure, lock held, malformed state) |
| 2 | Dirty working tree — pass `--force` to override |
| 3 | Path traversal refusal — tampered target-profile.yaml |
| 4 | Malformed `.ark/migrations-applied.jsonl` — run `/ark-onboard repair` |

### Step 5: Post-Run Summary Rendering

Parse and render the engine's stdout. The engine emits a plain-text summary; the
SKILL.md wrapper reformats it for user-facing display.

#### Dry-Run Mode

When `--dry-run` is passed, the engine prints a plan report (human-readable) followed
by a JSON plan object. Display the human-readable section and suppress the raw JSON
unless the user asks to see it:

```
Dry-run plan for /ark-update
=============================
Phase 1 — Destructive migrations: none pending
Phase 2 — Target-profile convergence:
  [would apply]  ensure_routing_rules_block (routing-rules) → CLAUDE.md
  [would apply]  ensure_gitignore_entry (.ark-workflow/) → .gitignore
  [would skip]   create_file_from_template (setup-vault-symlink) — already present
```

#### Full Run — Ops Applied Section

```
/ark-update complete
====================
Phase 1 (destructive migrations): 0 applied, 0 failed
Phase 2 (convergence): 2 applied, 0 drift-overwritten, 1 skipped, 0 failed
```

#### Drift Events Section

When one or more ops report `drifted_overwritten`, list each with backup path:

```
Drift events (managed content overwritten from canonical template):
  • omc-routing → backed up to .ark/backups/2026-04-14T10:23:11Z-omc-routing.bak
  • routing-rules → backed up to .ark/backups/2026-04-14T10:23:11Z-routing-rules.bak

Review the backups before committing. To see what changed:
  diff .ark/backups/2026-04-14T10:23:11Z-omc-routing.bak CLAUDE.md
```

#### Failures Section

When `failed_ops[]` is non-empty:

```
Failures (manual action required):
  ✗ setup-vault-symlink (create_file_from_template): SymlinkTargetError — ...
```

#### Suggested Commit Message

After a successful full run (exit 0, non-clean):

```
Suggested commit:

  git add -A && git commit -m "chore(ark): sync to plugin v$(cat $ARK_SKILLS_ROOT/VERSION)"

This records the applied migrations and converged target-profile state in source
control so collaborators' clones start from the correct installed version.
```

After a clean run (exit 0, nothing to do):

```
Already up to date — no commit needed.
```

### Step 6: Refusal-Mode Handoffs

When the engine exits with specific codes or prints specific error patterns, emit
the appropriate handoff message:

**Exit code 4 (malformed `.ark/migrations-applied.jsonl`):**

> "This file looks malformed. Run `/ark-onboard repair` then retry `/ark-update`."
> 
> `/ark-onboard repair` will restore a valid `.ark/` directory (fresh bootstrap,
> correct JSONL schema). After repair, re-run `/ark-update`.

**Exit code 1 with "Marker integrity error":**

> "This file looks malformed. Run `/ark-onboard repair` then retry `/ark-update`."
>
> Corrupted `<!-- ark:begin/end -->` markers require manual inspection. `/ark-onboard repair`
> can restore a clean CLAUDE.md section if the corruption is recoverable.

**Exit code 3 (path traversal):**

> "Path traversal detected in target-profile.yaml. This may indicate a tampered plugin
> installation. Re-install the ark-skills plugin via the Claude Code plugin manager,
> then retry `/ark-update`."

**Exit code 1 with ".ark/ is listed in .gitignore":**

> "Remove `.ark/` (or `.ark`) from your `.gitignore`, commit the change, then re-run
> `/ark-update`. The `.ark/` directory must be tracked in source control so migration
> state is shared across clones and worktrees."

**Any malformed CLAUDE.md / `.mcp.json` detected before invocation:**

> "This file looks malformed. Run `/ark-onboard repair` then retry `/ark-update`."
>
> Point user to `/ark-onboard repair` for CLAUDE.md, `.mcp.json`, and
> `.ark/migrations-applied.jsonl` malformation. `/ark-update` does not attempt to repair
> these files — it refuses and delegates repair to `/ark-onboard`.

---

## References

- Spec: `.omc/specs/deep-interview-ark-update-framework.md`
- Plan: `.omc/plans/ralplan-ark-update.md`
- Stream B handoff: `.ark-workflow/handoffs/stream-b-ark-update-framework.md`
- OMC integration constants: `skills/ark-workflow/references/omc-integration.md` § Section 0
- Target ship: v1.14.0 (combined with Stream A — OMC detection in `/ark-onboard` + `/ark-health`)
