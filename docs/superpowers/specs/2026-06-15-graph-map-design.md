---
title: /graph-map — graphify integration for ark-skills
date: 2026-06-15
status: approved-design
skill: graph-map
upstream-dep: graphifyy (PyPI, repo safishamsi/graphify)
---

# /graph-map — graphify integration for ark-skills

## Summary

Add a new reusable ark-skill, `/graph-map`, that installs and drives the
[graphify](https://github.com/safishamsi/graphify) CLI (`graphifyy` on PyPI) to
map any Ark project repo into a queryable knowledge graph, quarantine the
generated Obsidian pages inside the project's vault, and register the graph as a
structural-query retrieval backend in the project's `CLAUDE.md`. The skill is
dogfooded by running it once on the ark-skills repo itself.

This is a **thin orchestrator** (Approach A): it shells out to the `graphify`
CLI for all heavy lifting and only adds the two Ark-specific steps the CLI
cannot do — relocating output into the vault quarantine and patching retrieval
routing. It rides graphify's upgrades rather than reimplementing them.

## Goals

- A reusable, context-discovery-driven skill any Ark project can invoke.
- Vault enrichment: browsable concept-graph pages inside the vault.
- Retrieval backend: graphify graph wired into the project's query routing for
  code-structural questions.
- Dogfood the skill on ark-skills as its first real run and verification.

## Non-goals

- Reimplementing graphify's extraction or Obsidian export (Approach B rejected).
- Stamping Ark frontmatter onto generated concept notes (Approach C deferred).
- Copying source files into the vault (runbook step 5 dropped — concept notes
  already reference source paths; we link, not duplicate).

## Background / verified facts

Established during brainstorming (2026-06-15) by inspecting the live PyPI
metadata for `graphifyy` v0.8.39:

- **Package:** `graphifyy` (double-y) is the official PyPI package; `graphify`
  (single-y) is **Not Found**. The CLI command is still `graphify`. `uv` is
  installed on this machine.
- **Map output:** `graphify <path>` produces `graphify-out/{graph.json,
  graph.html, GRAPH_REPORT.md}`. The extraction is **agent-driven** — performed
  by Claude following graphify's own installed `SKILL.md` (set up by `graphify
  install --project`). Only subsequent rebuilds (the post-commit hook) are
  deterministic AST passes with zero API cost.
- **Obsidian export:** a **flag** — `graphify <path> --obsidian` — not a
  separate `graphify obsidian` subcommand (the NotebookLM runbook was wrong on
  this). There is also `--wiki` (agent-crawlable markdown wiki).
- **Query:** `graphify query "..."` (terminal, cheap) and an MCP stdio/HTTP
  server via `python -m graphify.serve graphify-out/graph.json`.
- **Hook:** `graphify hook install` embeds the interpreter path into a
  post-commit hook (AST rebuild, no API cost) and installs a git merge driver
  that union-merges `graph.json` so it never carries conflict markers. Re-run
  after upgrading graphify.
- **Ignore:** `.graphifyignore` (gitignore syntax, `!` negation supported);
  `.gitignore` is respected automatically.
- **Shared-graph workflow:** `graphify-out/` (including `graph.json`) is meant
  to be **committed** so collaborators read the graph immediately; the merge
  driver exists precisely because `graph.json` is version-controlled.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Scope | Build reusable skill **and** dogfood on ark-skills (both) |
| Role | Vault enrichment **and** queryable retrieval backend (both) |
| Auto-sync hook | **Always auto-install** (idempotent), per user |
| Approach | **A — thin orchestrator** |
| Runbook step 5 (copy source into vault) | **Dropped** — link to source instead |
| Skill name | `/graph-map` (avoids collision with graphify's own `/graphify`) |
| Workflow wiring | **Add `/ark-workflow` trigger** + routing-table row |

## Skill structure

```
skills/graph-map/
├── SKILL.md          # context-discovery procedure, modes, prereq checks
└── references/       # (optional) graphify command cheatsheet loaded on demand
```

Follows existing ark-skills conventions (`SKILL.md` primary; `references/` and
`scripts/` sidecars as needed). Uses the standard Project Discovery procedure
from the repo `CLAUDE.md` to resolve `{project_name}`, `{vault_root}`.

## Modes

### `setup` (first run / default)

1. **Prereqs:** verify `uv` present, Python ≥3.10, current dir is a git repo.
   Install/upgrade package: `uv tool install graphifyy` (idempotent).
2. **Register graphify's native skill:** `graphify install --project` →
   writes `.claude/skills/graphify/SKILL.md` (+ `references/`). Print the
   `git add` hint graphify emits.
3. **Map (agent-driven):** `graphify . --obsidian`. Produces
   `graphify-out/{graph.json, graph.html, GRAPH_REPORT.md}` plus the Obsidian
   export directory. **Implementation task:** confirm the exact export
   directory path graphify writes (under `graphify-out/`) and use it in the
   relocate step.
4. **Relocate (quarantine):** move the Obsidian export →
   `{vault_root}/graph_imports/{project_name}/`. Deletable as a single unit.
5. **Patch routing:** add the Graph (structural) backend row to the project's
   `CLAUDE.md` retrieval routing (see "Retrieval routing").
6. **Hook:** `graphify hook install` (post-commit AST rebuild + `graph.json`
   merge driver). Idempotent; safe to re-run after upgrades.

### `update`

`graphify . --update` (re-extract only changed files), then re-relocate changed
pages into the quarantine. Used when docs/code change between commits beyond
what the post-commit AST hook covers.

### `query "<question>"`

Route a structural question to `graphify query "<question>"` (cheap, no server).
For heavy interactive sessions, the MCP server
(`python -m graphify.serve graphify-out/graph.json`) is an **opt-in** the skill
documents but does not auto-register.

## Output placement & quarantine

- `graphify-out/` (incl. `graph.json`) — **committed in repo root**. Required by
  the merge driver and shared-graph workflow.
- A repo-root `.graphifyignore` excludes `vault/`, `node_modules/`, build
  artifacts, etc. from mapping so the graph reflects source, not generated docs.
- Browsable Obsidian pages — **only** in `{vault_root}/graph_imports/{project}/`.
- That subtree is **excluded** from the three Ark vault tools, since graphify's
  frontmatter is not Ark-shaped and the quarantine must stay clean:
  - `wiki-lint` — add an ignore path.
  - `_meta/generate-index.py` — skip `graph_imports/`.
  - `tag-taxonomy` — skip `graph_imports/`.

## Retrieval routing integration

Add a parallel **Graph (structural)** backend to the project `CLAUDE.md` routing
table. **Do not renumber T1–T4** (too invasive across the ecosystem). The graph
backend owns code-structural questions; it complements T2 MemPalace
(experiential / *why*) by answering structural / *how-connected*.

- **Routing rows** (added to "Query Routing"):
  - "What calls X / what does X depend on?" → Graph → T3
  - "Show the structure/flow of X" → Graph → T4
  - "How does module A relate to module B (in code)?" → Graph → T2
- **Availability check:** `graphify-out/graph.json` exists in project root.
- **Failure message:** "Graph tier not available — graphify-out/graph.json not
  found. Run /graph-map setup. Falling back to T3/T4."

## Dogfood run (on ark-skills)

After the skill exists, run `setup` once against this repo:
- `vault/graph_imports/ark-skills/` populated with the Obsidian export.
- This repo's `CLAUDE.md` gets the Graph routing row.
- `.graphifyignore` created (excludes `vault/`).
- Post-commit hook + merge driver installed.

This run is both the first real use and the acceptance test.

## Ecosystem touchpoints

- **Register skill:** `.claude-plugin/plugin.json` + `marketplace.json`
  keywords; `README.md` skill list; `CLAUDE.md` "Available Skills".
- **`/ark-skill-healer`:** add graphify (`graphifyy`, repo `safishamsi/graphify`)
  to the tracked upstream-dependency inventory with a last-seen version snapshot
  (0.8.39) so future drift surfaces as advisory.
- **`/ark-workflow`:** add a trigger for "map this repo", "knowledge graph",
  "how does X relate structurally" → `/graph-map`.
- **Version bump:** VERSION, plugin.json, marketplace.json, CHANGELOG (per the
  always-bump rule).

## Error handling

- Missing `uv` → instruct `curl -LsSf https://astral.sh/uv/install.sh | sh` or
  `pipx install graphifyy` fallback.
- Python <3.10 → fail with clear message.
- Not a git repo → skip hook step, warn.
- Map failure → surface graphify's error, leave vault untouched, do not patch
  routing (avoid half-integrated state).
- All install/hook steps idempotent and safe to re-run.

## Verification / acceptance criteria

The dogfood run is the acceptance test. Assert:
1. `graphify-out/graph.json` exists in repo root.
2. `vault/graph_imports/ark-skills/` is populated.
3. This repo's `CLAUDE.md` contains the Graph routing row.
4. `.git/hooks/post-commit` exists and references graphify.
5. `graphify query "what skills does ark-skills define?"` returns a graph-backed
   answer.
6. `wiki-lint` still passes (quarantine correctly excluded).
7. Skill registered in plugin.json / marketplace.json / README / CLAUDE.md.

Doc/markdown edits get a manual consistency check (no executable test applies).

## Open implementation tasks (resolve during build, not blocking design)

- Confirm graphify's exact `--obsidian` output directory name/path.
- Confirm whether `graphify install --project` writes any files that should be
  git-ignored vs committed in the ark-skills repo.
