# graphify CLI cheatsheet (verified against graphifyy 0.8.39, 2026-06-15)

Official PyPI package: `graphifyy` (double-y). CLI command: `graphify`.
Repo: https://github.com/safishamsi/graphify

## Install / version
```bash
uv tool install graphifyy            # or: pipx install graphifyy
graphify --version                   # must be >= 0.8.39
graphify install --project           # installs graphify's own skill into .claude/skills/graphify/
```

## Backend (semantic pass needs an LLM key; pick a NON-reasoning chat model)
Reasoning models (Kimi/GLM/Qwen-Thinking) burn the output budget and truncate;
use Gemma / DeepSeek-V3 etc. For an OpenAI-compatible provider (e.g. Chutes):
```bash
uv tool install "graphifyy[openai]" --force
graphify provider add chutes --base-url https://llm.chutes.ai/v1 \
    --default-model google/gemma-4-31B-turbo-TEE --env-key CHUTES_API_KEY
# raise output cap to fit context (default 8192 truncates dense docs):
#   edit ~/.graphify/providers.json -> "max_completion_tokens": 32000   (131K model)
```

## Map, then export (verified flow)
```bash
graphify . --backend chutes          # AST + semantic; on a semantic run it CHECKPOINTS at graph.json
graphify export obsidian             # -> graphify-out/obsidian/ (note per node + graph.canvas)
graphify cluster-only . --backend chutes   # optional: name communities + GRAPH_REPORT.md
graphify . --update --backend chutes # re-extract only changed files (then re-run export obsidian)
```
The bare `--obsidian` flag does NOT emit the export on a semantic run — use
`graphify export obsidian`. Output dir `graphify-out/` (incl. `graph.json`) is
meant to be COMMITTED. Ignore `graphify-out/cost.json` and `graphify-out/cache/`.

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
