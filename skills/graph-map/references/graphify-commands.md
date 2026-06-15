# graphify CLI cheatsheet (verified against graphifyy 0.8.39, 2026-06-15)

Official PyPI package: `graphifyy` (double-y). CLI command: `graphify`.
Repo: https://github.com/safishamsi/graphify

## Install / version
```bash
uv tool install graphifyy            # or: pipx install graphifyy
graphify --version                   # must be >= 0.8.39
graphify install --project           # installs graphify's own skill into .claude/skills/graphify/
```

## Map (agent-driven — first run extracts via subagents)
```bash
graphify . --obsidian                # produces graphify-out/{graph.json,graph.html,GRAPH_REPORT.md} + obsidian export dir
graphify . --update                  # re-extract only changed files
```
Output dir `graphify-out/` (incl. `graph.json`) is meant to be COMMITTED.
Ignore `graphify-out/cost.json`.

## Query
```bash
graphify query "what connects X to Y?"
python -m graphify.serve graphify-out/graph.json        # MCP stdio (opt-in)
```

## Hooks (deterministic AST rebuild, zero API cost)
```bash
graphify hook install                # installs post-commit AND post-checkout + merge driver (.gitattributes + .git/config)
graphify hook status                 # verify
GRAPHIFY_SKIP_HOOK=1 git commit ...  # suppress hook for a graph-only commit
```
Merge driver: `.gitattributes` is portable; `.git/config` registration is per-clone — every fresh clone must re-run `graphify hook install`.

## Ignore
`.graphifyignore` (gitignore syntax). NOTE: once present it OVERRIDES `.gitignore`
inheritance in that directory — so mirror critical ignores. See `graphifyignore.defaults`.
