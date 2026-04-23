# /ark-onboard — Obsidian Plugin Install (Step 11)

Three-tier fallback for installing Obsidian community plugins (TaskNotes, Obsidian Git) without the user touching the Obsidian GUI. Loaded by `SKILL.md § Greenfield Step 11`.

**Order:**

1. **Primary** — Download from GitHub releases using the Obsidian community-plugins registry.
2. **Fallback 1** — Copy binaries from a reference vault the user provides.
3. **Fallback 2** — Manual GUI install. PAUSE for user.

---

## Primary: Download from GitHub releases (automatic)

Resolves plugin repos from Obsidian's community plugin registry, then downloads latest release assets.

```bash
# Step 1: Resolve plugin repos from Obsidian's community plugin registry
COMMUNITY_PLUGINS=$(curl -sfL "https://raw.githubusercontent.com/obsidianmd/obsidian-releases/master/community-plugins.json" 2>/dev/null)

if [ -n "$COMMUNITY_PLUGINS" ]; then
  TASKNOTES_REPO=$(echo "$COMMUNITY_PLUGINS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if p['id'] == 'tasknotes':
        print(p['repo']); break
" 2>/dev/null)

  GIT_REPO=$(echo "$COMMUNITY_PLUGINS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if p['id'] == 'obsidian-git':
        print(p['repo']); break
" 2>/dev/null)
fi

DOWNLOAD_OK=true

# Step 2: Download TaskNotes plugin
if [ -n "$TASKNOTES_REPO" ]; then
  for FILE in main.js manifest.json styles.css; do
    curl -sfL "https://github.com/$TASKNOTES_REPO/releases/latest/download/$FILE" \
      -o "{vault_path}/.obsidian/plugins/tasknotes/$FILE"
  done
  if [ -s "{vault_path}/.obsidian/plugins/tasknotes/main.js" ]; then
    echo "OK: TaskNotes plugin downloaded from $TASKNOTES_REPO"
  else
    echo "WARN: TaskNotes download failed"
    DOWNLOAD_OK=false
  fi
else
  echo "WARN: Could not resolve TaskNotes repo from registry"
  DOWNLOAD_OK=false
fi

# Step 3: Download Obsidian Git plugin
if [ -n "$GIT_REPO" ]; then
  for FILE in main.js manifest.json styles.css; do
    curl -sfL "https://github.com/$GIT_REPO/releases/latest/download/$FILE" \
      -o "{vault_path}/.obsidian/plugins/obsidian-git/$FILE"
  done
  if [ -s "{vault_path}/.obsidian/plugins/obsidian-git/main.js" ]; then
    echo "OK: Obsidian Git plugin downloaded from $GIT_REPO"
  else
    echo "WARN: Obsidian Git download failed"
    DOWNLOAD_OK=false
  fi
else
  echo "WARN: Could not resolve Obsidian Git repo from registry"
  DOWNLOAD_OK=false
fi
```

## Fallback 1: Copy from reference vault

If any download failed and the user has a reference vault, prompt for its path and copy plugin binaries (NOT `data.json` — that's gitignored and project-specific).

```bash
if [ "$DOWNLOAD_OK" = "false" ]; then
  echo "Some plugin downloads failed. Do you have a reference vault to copy from?"
  # If yes:
  # TaskNotes (do NOT copy data.json — it's gitignored and project-specific)
  cp {reference_vault}/.obsidian/plugins/tasknotes/main.js {vault_path}/.obsidian/plugins/tasknotes/
  cp {reference_vault}/.obsidian/plugins/tasknotes/manifest.json {vault_path}/.obsidian/plugins/tasknotes/
  cp {reference_vault}/.obsidian/plugins/tasknotes/styles.css {vault_path}/.obsidian/plugins/tasknotes/

  # Obsidian Git
  cp {reference_vault}/.obsidian/plugins/obsidian-git/main.js {vault_path}/.obsidian/plugins/obsidian-git/
  cp {reference_vault}/.obsidian/plugins/obsidian-git/manifest.json {vault_path}/.obsidian/plugins/obsidian-git/
  cp {reference_vault}/.obsidian/plugins/obsidian-git/styles.css {vault_path}/.obsidian/plugins/obsidian-git/
fi
```

## Fallback 2: Manual install (last resort)

Only reached if download AND reference-vault copy both failed. PAUSE the wizard and hand off to the user:

```
Plugin binaries could not be installed automatically. Install manually:
  1. Open the vault in Obsidian
  2. Settings > Community Plugins > Browse
  3. Install "TaskNotes" and "Obsidian Git"
  4. Enable both plugins

PAUSE — manual handoff. Continue when plugins are installed, or type "skip" to proceed without plugins.
```

---

## After install: plugin `data.json` configs

Generate both plugins' `data.json` using templates from `references/templates.md § TaskNotes plugin data.json` and `§ Obsidian Git plugin data.json`. These files are gitignored — each vault gets its own.

## After install: TaskNotes MCP config

Before touching `.mcp.json`, validate its JSON:

```bash
if [ -f .mcp.json ]; then
  python3 -c "import json; json.load(open('.mcp.json'))" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "WARNING: .mcp.json is malformed JSON. Back up and recreate."
    cp .mcp.json .mcp.json.bak
  fi
fi
```

Then add/merge the `tasknotes` entry per `references/templates.md § .mcp.json TaskNotes MCP entry`.
