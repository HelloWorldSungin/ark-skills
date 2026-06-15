---
title: /graph-map — graphify integration for ark-skills
date: 2026-06-15
status: approved-design
skill: graph-map
upstream-dep: graphifyy (PyPI, repo safishamsi/graphify), min-version 0.8.39
reviewed-by: CCG (Codex gpt-5.5/xhigh + Gemini), 2026-06-15
---

# /graph-map — graphify integration for ark-skills

## Summary

Add a new reusable ark-skill, `/graph-map`, that installs and drives the
[graphify](https://github.com/safishamsi/graphify) CLI (`graphifyy` on PyPI) to
map any Ark project repo into a queryable knowledge graph, quarantine the
generated Obsidian pages inside the project's vault, and register the graph as a
code-structural retrieval backend in the project's `CLAUDE.md`. The skill is
dogfooded by running it once on the ark-skills repo itself.

This is a **thin orchestrator** (Approach A): it shells out to the `graphify`
CLI for all heavy lifting and adds the Ark-specific steps the CLI cannot do —
an ignore/preflight policy, output validation, relocating output into the vault
quarantine, patching retrieval routing, and hook guardrails. It rides
graphify's upgrades rather than reimplementing them.

## Goals

- A reusable, context-discovery-driven skill any Ark project can invoke.
- Vault enrichment: browsable concept-graph pages inside the vault.
- Retrieval backend: graphify graph wired into the project's routing for
  code-structural questions.
- Dogfood the skill on ark-skills as its first real run and verification.

## Non-goals

- Reimplementing graphify's extraction or Obsidian export (Approach B rejected).
- Stamping Ark frontmatter onto concept notes (Approach C deferred).
- Copying source files into the vault (runbook step 5 dropped — concept notes
  reference source paths; we link, not duplicate).

## Background / verified facts

Established by inspecting live PyPI metadata for `graphifyy` v0.8.39 and the
upstream README/changelog (2026-06-15):

- **Package:** `graphifyy` (double-y) is official; `graphify` (single-y) is
  Not Found. CLI command is `graphify`. `uv` is installed on this machine.
- **Map output:** `graphify <path>` produces `graphify-out/{graph.json,
  graph.html, GRAPH_REPORT.md}`. Extraction is **agent-driven** — performed by
  Claude following graphify's installed `SKILL.md` (set up by `graphify install
  --project`). Subsequent rebuilds (the git hooks) are deterministic AST passes,
  zero API cost.
- **Obsidian export:** a **flag** — `graphify <path> --obsidian` — not a
  `graphify obsidian` subcommand (the NotebookLM runbook was wrong). Also
  `--wiki` (agent-crawlable markdown).
- **Query:** `graphify query "..."` (terminal) and an MCP stdio/HTTP server via
  `python -m graphify.serve graphify-out/graph.json`. Query logs default to
  `~/.cache/graphify-queries.log` (has an opt-out).
- **Hooks:** `graphify hook install` embeds the interpreter path and installs
  **both a post-commit and a post-checkout hook** (AST rebuild, no API cost),
  plus a git merge driver registered via **`.gitattributes` (portable) and
  local `.git/config` (per-clone, NOT portable)** that union-merges
  `graph.json`. Re-run after upgrading graphify. `graphify hook status` reports
  state; a `GRAPHIFY_SKIP_HOOK=1` env var suppresses a given run.
- **Ignore:** `.graphifyignore` (gitignore syntax, `!` negation). `.gitignore`
  is respected only when **no** `.graphifyignore` exists in that directory; once
  present, `.graphifyignore` **takes priority and stops inheriting** the sibling
  `.gitignore`.
- **Shared-graph workflow:** `graphify-out/` (incl. `graph.json`) is meant to be
  **committed** so collaborators read the graph immediately; the merge driver
  exists because `graph.json` is version-controlled. Upstream also recommends
  ignoring `graphify-out/cost.json`.

## Decisions

| Decision | Choice |
|---|---|
| Scope | Reusable skill **and** dogfood on ark-skills |
| Role | Vault enrichment **and** code-structural retrieval backend |
| Auto-sync hook | **Always auto-install, WITH guardrails** (clean-worktree check, install after initial graph commit, `GRAPHIFY_SKIP_HOOK=1` documented, uninstall docs, `graphify hook status` verify) |
| Approach | **A — thin orchestrator** |
| Runbook step 5 (copy source into vault) | **Dropped** — link to source instead |
| Skill name | `/graph-map` (avoids collision with graphify's own `/graphify`) |
| Workflow wiring | **Add `/ark-workflow` trigger** + structural-retrieval routing |
| Quarantine dir | `{vault_root}/generated/graphify/` (signals tool-managed) |
| Retrieval routing | Separate **Code-Structural Retrieval** section, NOT a fake T-tier |

## Skill structure

```
skills/graph-map/
├── SKILL.md          # context-discovery procedure, modes, prereq checks
└── references/       # graphify command cheatsheet + ignore-policy defaults
```

Uses the repo's standard Project Discovery to resolve `{project_name}`,
`{vault_root}`.

## Modes

### `setup` (first run / default)

1. **Prereqs (preflight):** `uv` present; Python ≥3.10; current dir is a git
   repo (if not, run map but **skip** hooks and warn — resolves the prereq/error
   conflict). Install/upgrade: `uv tool install graphifyy` and assert
   `graphify --version` ≥ **0.8.39 (min)**; record the resolved version in skill
   state. Confirm `graphify install --platform claude` autodetect vs explicit.
2. **Ignore policy FIRST (P0):** write/merge a repo-root `.graphifyignore`
   **before any map runs**. Because it overrides `.gitignore` inheritance, it
   must mirror critical `.gitignore` patterns AND hard-code Ark defaults:
   `vault/`, `generated/`, `graphify-out/`, `.omc/`, `.notebooklm/`,
   `.claude/skills/graphify/`, `.env*`, key/cert globs, `node_modules/`, build
   dirs. This prevents the first map from ingesting the vault, secrets, or
   graphify's own generated files.
3. **Register graphify's native skill:** `graphify install --project` →
   `.claude/skills/graphify/SKILL.md` (+ `references/`). Print graphify's
   `git add` hint. Inventory exactly which files it writes (committed vs ignored).
4. **Map (agent-driven):** `graphify . --obsidian`. Produces
   `graphify-out/{graph.json, graph.html, GRAPH_REPORT.md}` + the Obsidian
   export dir. **Impl task:** confirm the exact export dir path.
5. **Validate output (fail closed):** assert `graph.json` exists and matches the
   expected schema/metadata for the recorded version; if the output layout is
   unknown, STOP before touching the vault or CLAUDE.md (avoid half-integrated
   state).
6. **Secret/size scan (P0):** scan `graphify-out/` (and the export) for secrets
   and oversized artifacts before anything is committed; surface a sensitive-file
   inventory; document the query-log opt-out for sensitive repos; note private-
   repo policy.
7. **Relocate (quarantine):** move the Obsidian export →
   `{vault_root}/generated/graphify/`. Run a **relative-path link-fixer** pass:
   relocation changes directory depth, so source/back-links written relative to
   `graphify-out/` must be rewritten relative to the new location (or made
   repo-root-relative). Write `_graphify-meta.json` (source graph.json hash +
   graphify version + timestamp) for drift detection.
8. **Patch routing:** add the Code-Structural Retrieval section to the project's
   `CLAUDE.md` (see below) — only after validation passed.
9. **Commit graph artifacts**, THEN **hook install with guardrails:**
   require a clean worktree, run `graphify hook install`, verify with `graphify
   hook status`, confirm both post-commit and post-checkout are present, document
   `GRAPHIFY_SKIP_HOOK=1` and the uninstall path. Installing after the initial
   commit avoids the hook dirtying the dogfood commit.

### `update`

`graphify . --update`, then re-relocate + re-run the link-fixer for changed
pages. The post-commit/post-checkout hooks keep `graph.json` fresh
deterministically (free); `update` is the **agent-driven** ($-cost) re-analysis
for logic/comment changes after significant refactors. SKILL.md states this
boundary explicitly for users.

### `status`

Report graph freshness: compare `graphify-out/graph.json` hash against
`_graphify-meta.json` in the quarantine and warn when the browsable vault pages
have drifted from the current graph ("Graph seems stale? Run /graph-map update").

### `query "<question>"`

Route a structural question to `graphify query "<question>"`. MCP server
(`python -m graphify.serve graphify-out/graph.json`) is an opt-in for heavy
sessions.

## Output placement & quarantine contract

- `graphify-out/` (incl. `graph.json`) — **committed in repo root**. Ignore
  `graphify-out/cost.json` and any cache; review `graph.html`/JSON diff churn so
  it doesn't pollute PRs. Acceptance includes "clean worktree after a graph-only
  commit."
- Browsable Obsidian pages — **only** in `{vault_root}/generated/graphify/`.
- **Single quarantine contract:** `generated/` is excluded by **every** vault
  scanner/syncer, not just three. Update the scan/ignore lists of: `wiki-lint`,
  `_meta/generate-index.py`, `tag-taxonomy`, `cross-linker`, `wiki-status`,
  `ark-health` index-freshness, `skills/shared/mine-vault.sh`, NotebookLM sync,
  and any raw vault glob. Deletability = remove the one `generated/graphify/`
  folder.

## External / symlinked vault handling (two-repo case)

Ark vaults are frequently a **separate, gitignored repo** (symlink or external
checkout). In that case graph artifacts (`graphify-out/`) land in the project
repo while the relocated pages land in a **different** repo. The skill must:
- detect whether `{vault_root}` is inside the project repo, a separate git repo,
  or not a git repo at all;
- stage/commit project-repo changes and vault-repo changes **separately** and
  report both;
- never silently dirty a shared vault; if the vault repo is missing/unwritable,
  warn and skip the vault commit.

The ark-skills dogfood uses a **standalone** vault (same repo), so the spec must
also document and the implementation must test the external-vault path even
though the dogfood does not exercise it.

## Retrieval routing integration

Add a separate **Code-Structural Retrieval** section to the project `CLAUDE.md`
(do NOT pose as T1–T4; `T3` is Obsidian full-text and `T4` is the vault index —
neither is a call graph). Routing:

- "What calls X / what does X depend on?" → **Graph** → `rg`/LSP/source
- "Show the structure/flow of X" → **Graph** → source
- Structural code questions in general → **Graph**; fall back to `rg`/LSP/source
- "Why was X built this way / decision?" → **T2** (MemPalace), not Graph

- **Availability check:** `graphify-out/graph.json` exists in repo root.
- **Failure message:** "Code-structural graph not available — graphify-out/
  graph.json not found. Run /graph-map setup. Falling back to rg/LSP/source."

## Dogfood run (on ark-skills)

Run `setup` once against this repo:
- `.graphifyignore` written first (excludes `vault/`, `generated/`, etc.).
- `vault/generated/graphify/` populated; `_graphify-meta.json` written.
- This repo's `CLAUDE.md` gets the Code-Structural Retrieval section.
- graph artifacts committed, then hooks installed + verified.

## Ecosystem touchpoints

- **Register skill:** `.claude-plugin/plugin.json` + `marketplace.json`
  keywords; `README.md` skill list; `CLAUDE.md` "Available Skills".
- **`/ark-skill-healer`:** track graphify (`graphifyy`, `safishamsi/graphify`,
  last-seen 0.8.39) in the upstream-dependency inventory.
- **`/ark-workflow`:** trigger on "map this repo", "knowledge graph", "how does
  X relate structurally" → `/graph-map`.
- **`/ark-health`:** add a graph health check (graph.json present + not stale vs
  quarantine meta).
- **Version bump:** VERSION, plugin.json, marketplace.json, CHANGELOG.

## Error handling

- Missing `uv` → `pipx install graphifyy` fallback or uv install instructions.
- Python <3.10 / graphify <0.8.39 → fail with clear message.
- Not a git repo → run map, skip hooks, warn (single consistent rule).
- Unknown `graph.json` layout → fail closed before vault/CLAUDE.md changes.
- Map failure → surface graphify's error, leave vault untouched, do not patch
  routing.
- All install/hook steps idempotent and safe to re-run.

## Verification / acceptance criteria

The dogfood run is the acceptance test. Assert:
1. `.graphifyignore` exists and predates the map (no `vault/`/secret nodes in
   `graph.json`).
2. `graphify-out/graph.json` exists; `cost.json`/cache ignored.
3. `vault/generated/graphify/` populated; relative links resolve (no broken
   back-links); `_graphify-meta.json` written.
4. This repo's `CLAUDE.md` has the Code-Structural Retrieval section.
5. `.gitattributes` has the merge driver; `.git/config` registers it; per-clone
   setup documented.
6. `.git/hooks/post-commit` **and** `post-checkout` exist; `graphify hook
   status` clean; worktree clean after a graph-only commit.
7. `graphify query "what skills does ark-skills define?"` returns a graph-backed
   answer.
8. Every vault scanner (`wiki-lint`, index, `tag-taxonomy`, `cross-linker`,
   `wiki-status`, `ark-health`, `mine-vault.sh`, NotebookLM sync) ignores
   `generated/`.
9. Skill registered in plugin.json / marketplace.json / README / CLAUDE.md.
10. Secret/size scan ran clean over `graphify-out/`.

Doc/markdown edits get a manual consistency check (no executable test applies).

## Open implementation tasks (resolve during build)

- Confirm graphify's exact `--obsidian` output directory path.
- Confirm the `graph.json` schema/metadata fields used for version validation.
- Confirm exact files `graphify install --project` writes (committed vs ignored).
- Confirm `graphify hook status` output format for the verification step.

## CCG review provenance

Reviewed 2026-06-15 by Codex (gpt-5.5, reasoning effort xhigh) for
architecture/correctness/risk and Gemini for docs/UX/alternatives. P0/P1 issues
(ignore-ordering, secret boundary, quarantine contract, version pinning,
external-vault, merge-driver completeness, quarantine staleness, relative-path
fragility, routing reframe) folded in above. Hook stays always-on per user with
added guardrails; quarantine dir renamed `generated/graphify/` per user.
