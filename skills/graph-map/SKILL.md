---
name: graph-map
description: Map a repo into a queryable knowledge graph with graphify, quarantine the generated Obsidian pages in the vault, and register the graph as a code-structural retrieval backend. Triggers on "map this repo", "knowledge graph", "graph-map", "how does X relate structurally", "dependency map".
---

# Graph Map

Thin orchestrator around the `graphify` CLI (`graphifyy` on PyPI). It maps the
current repo into a knowledge graph, quarantines the browsable Obsidian export
inside the project's vault, and wires the graph into retrieval routing. It does
NOT reimplement graphify — see `references/graphify-commands.md`.

Helper scripts live in `scripts/` (`relink.py`, `secret_scan.py`,
`graph_status.py`). Default ignore patterns: `references/graphifyignore.defaults`.

## Project Discovery

Run the standard Project Discovery from the repo `CLAUDE.md` to resolve
`{project_name}` and `{vault_root}`. The quarantine target is
`{vault_root}/generated/graphify/`.

**Detect the vault repo relationship** (CCG: external-vault case):
- Is `{vault_root}` inside the project's git repo, a separate git repo (symlink /
  external checkout), or not a git repo at all? Stage and commit project-repo
  changes and vault-repo changes SEPARATELY and report both. If the vault repo is
  missing or unwritable, warn and skip the vault commit — never silently dirty a
  shared vault.

## Modes

`setup` (default) · `update` · `status` · `query "<question>"`

### Mode: setup

1. **Preflight.**
   - `command -v uv` (else fall back to `pipx`); `python3 --version` ≥ 3.10;
     confirm current dir is a git repo (`git rev-parse --git-dir`). If NOT a git
     repo: run the map but SKIP the hook step and warn.
   - `uv tool install graphifyy` (idempotent). Assert
     `graphify --version` ≥ **0.8.39**; capture the version string.
2. **Ignore policy FIRST (before any map).** Merge
   `references/graphifyignore.defaults` into the repo-root `.graphifyignore`
   (create if absent; append missing lines; do not duplicate). This prevents the
   first map from ingesting `vault/`, `generated/`, secrets, or graphify's own
   output.
3. **Register graphify's native skill:** `graphify install --project`. Print the
   `git add` hint graphify emits.
4. **Map (agent-driven):** `graphify . --obsidian`. Confirm `graphify-out/graph.json`
   was produced and note the Obsidian export directory path graphify wrote.
5. **Validate (fail closed):** confirm `graphify-out/graph.json` is valid JSON
   (`python3 -c "import json;json.load(open('graphify-out/graph.json'))"`). If the
   output layout is unexpected, STOP — do not touch the vault or CLAUDE.md.
6. **Secret/size scan (before any commit):**
   `python3 skills/graph-map/scripts/secret_scan.py graphify-out` (and the export
   dir). If it exits non-zero, STOP and surface the findings; do not commit.
7. **Relocate + fix links:** move the Obsidian export into
   `{vault_root}/generated/graphify/`, then
   `python3 skills/graph-map/scripts/relink.py --old-dir <export-dir> --new-dir {vault_root}/generated/graphify`.
   Verify a sample rewritten link resolves on disk.
8. **Write drift meta:**
   `python3 skills/graph-map/scripts/graph_status.py write-meta --graph graphify-out/graph.json --out {vault_root}/generated/graphify/_graphify-meta.json --version <captured> --timestamp <ISO8601 now>`.
9. **Patch routing:** add the Code-Structural Retrieval section to the project's
   `CLAUDE.md` (only after validation passed). See "Routing block" below.
10. **Commit graph artifacts** (project repo: `graphify-out/` minus `cost.json`;
    `.graphifyignore`; CLAUDE.md) and SEPARATELY the vault changes. Add
    `graphify-out/cost.json` to `.gitignore`.
11. **Hook install (guarded), AFTER the graph commit:** require a clean worktree
    (`git status --porcelain` empty), then `graphify hook install`; verify with
    `graphify hook status`; confirm `.git/hooks/post-commit` and `post-checkout`
    exist. Tell the user: `GRAPHIFY_SKIP_HOOK=1` suppresses a run, and
    `graphify hook uninstall` removes them. Every fresh clone must re-run
    `graphify hook install` (merge driver `.git/config` is per-clone).

### Mode: update

`graphify . --update`, then repeat setup steps 5–8 (validate, scan, relocate +
relink, rewrite meta). The git hooks keep `graph.json` structurally fresh for
FREE; `update` is the agent-driven ($-cost) re-analysis for logic/comment changes
after significant refactors.

### Mode: status

`python3 skills/graph-map/scripts/graph_status.py check --graph graphify-out/graph.json --meta {vault_root}/generated/graphify/_graphify-meta.json`.
Report fresh / stale / missing. If stale: "Graph drifted from the vault copy —
run `/graph-map update`."

### Mode: query

Route structural questions to `graphify query "<question>"`. For heavy sessions,
the MCP server (`python -m graphify.serve graphify-out/graph.json`) is opt-in.

## Routing block (inserted into the project CLAUDE.md)

```markdown
### Code-Structural Retrieval

The graphify knowledge graph answers code-structural questions. Availability:
`graphify-out/graph.json` exists in repo root.

- "What calls X / what does X depend on?" → **Graph** (`graphify query`) → `rg`/LSP/source
- "Show the structure/flow of X" → **Graph** → source
- General structural code questions → **Graph**; fall back to `rg`/LSP/source
- "Why was X built this way / decision?" → **T2** (MemPalace), NOT the graph

Failure: "Code-structural graph not available — graphify-out/graph.json not found.
Run /graph-map setup. Falling back to rg/LSP/source."
```

## Quarantine contract

`{vault_root}/generated/` is excluded from every vault scanner (generate-index,
mine-vault, notebooklm sync, wiki-lint, wiki-status, cross-linker, tag-taxonomy).
The whole `generated/graphify/` folder is deletable as one unit to fully remove
the integration from the vault.
