# /ark-onboard — Project State Detection

Detection logic the wizard runs before routing to a path. `SKILL.md` § Project State Detection holds the 4-state classification rubric; this file holds the bash and flag-derivation detail.

---

## Step 1: Scan for vault directory

```bash
# Look for vault indicators in common locations
for DIR in vault/ docs/vault/ .vault/; do
  if [ -d "$DIR" ]; then
    echo "VAULT_DIR=$DIR"
    # Check for .obsidian/ or .md files as confirmation
    ls "$DIR"/.obsidian/ 2>/dev/null && echo "has .obsidian"
    find "$DIR" -maxdepth 2 -name "*.md" 2>/dev/null | head -5
  fi
done
```

## Step 2: Check CLAUDE.md

```bash
ls CLAUDE.md 2>/dev/null && echo "CLAUDE_MD=found" || echo "CLAUDE_MD=missing"
```

If CLAUDE.md exists, extract vault root from it:

```bash
grep -i "vault" CLAUDE.md 2>/dev/null | grep -oE '`[^`]+/`' | tr -d '`' | head -1
```

## Step 3: Classify project state (bash)

```bash
# Count Ark artifacts to distinguish Non-Ark from Partial
ARK_ARTIFACTS=0
[ -f "${VAULT_DIR}_meta/vault-schema.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -f "${VAULT_DIR}_meta/taxonomy.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -f "${VAULT_DIR}index.md" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
[ -d "${VAULT_DIR}TaskNotes/meta" ] && ARK_ARTIFACTS=$((ARK_ARTIFACTS + 1))
echo "Ark artifacts found: $ARK_ARTIFACTS / 4"

# Centralized-vault detection (independent of artifact count)
IS_SYMLINK=false
SCRIPT_EXISTS=false
EMBEDDED_OPTOUT=false
SYMLINK_BROKEN=false
SYMLINK_DRIFT=false

if [ -L "${VAULT_DIR%/}" ]; then
  IS_SYMLINK=true
  if [ ! -e "${VAULT_DIR%/}" ]; then
    SYMLINK_BROKEN=true
  fi
fi

if [ -f "scripts/setup-vault-symlink.sh" ]; then
  SCRIPT_EXISTS=true
  # Extract VAULT_TARGET for drift check (grep contract)
  SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
  # Expand $HOME so we can compare against readlink output
  SCRIPT_TARGET_EXPANDED=$(eval "echo $SCRIPT_TARGET")
  if [ "$IS_SYMLINK" = "true" ] && [ -e "${VAULT_DIR%/}" ]; then
    SYMLINK_TARGET=$(readlink "${VAULT_DIR%/}")
    if [ "$SYMLINK_TARGET" != "$SCRIPT_TARGET_EXPANDED" ]; then
      SYMLINK_DRIFT=true
    fi
  fi
fi

# Check for embedded-vault opt-out row in CLAUDE.md
if [ -f CLAUDE.md ] && grep -iqE '^\|\s*\*\*Vault layout\*\*\s*\|[^|]*embedded' CLAUDE.md; then
  EMBEDDED_OPTOUT=true
fi

echo "IS_SYMLINK=$IS_SYMLINK"
echo "SCRIPT_EXISTS=$SCRIPT_EXISTS"
echo "SYMLINK_BROKEN=$SYMLINK_BROKEN"
echo "SYMLINK_DRIFT=$SYMLINK_DRIFT"
echo "EMBEDDED_OPTOUT=$EMBEDDED_OPTOUT"

# Classification
# Key rules:
#   - vault exists + no CLAUDE.md = Partial (never greenfield)
#   - broken symlink OR symlink drift OR missing script with live symlink = Partial Ark (centralized-vault repair)
#   - real vault dir + embedded opt-out present = respect opt-out, classify by artifact count only
if [ -z "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "missing" ]; then
  echo "STATE=no_vault"
elif [ -z "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "found" ]; then
  # CLAUDE.md exists but vault root missing or doesn't exist
  echo "STATE=no_vault"
elif [ "$SYMLINK_BROKEN" = "true" ] || [ "$SYMLINK_DRIFT" = "true" ]; then
  echo "STATE=partial_ark"
  echo "REPAIR_REASON=centralized-vault-drift"
elif [ "$IS_SYMLINK" = "true" ] && [ "$SCRIPT_EXISTS" = "false" ]; then
  echo "STATE=partial_ark"
  echo "REPAIR_REASON=centralized-vault-script-missing"
elif [ -n "$VAULT_DIR" ] && [ "$CLAUDE_MD" = "missing" ]; then
  # Vault exists but no CLAUDE.md — always Partial, regardless of artifact count
  echo "STATE=partial_ark"
elif [ $ARK_ARTIFACTS -ge 3 ]; then
  echo "STATE=partial_ark"
elif [ -n "$VAULT_DIR" ]; then
  echo "STATE=non_ark_vault"
else
  echo "STATE=no_vault"
fi
```

## Classification table

| State | Condition | Wizard path |
|-------|-----------|-------------|
| `no_vault` | CLAUDE.md missing AND no vault directory found, OR CLAUDE.md present but vault root field missing/path doesn't exist | Greenfield (full setup) |
| `non_ark_vault` | Vault directory exists but missing 3+ of: `_meta/vault-schema.md`, `_meta/taxonomy.md`, `index.md`, `TaskNotes/meta/` | Migration (add Ark scaffolding) |
| `partial_ark` | Has Ark structure (3+ artifacts) but some diagnostic checks fail. Also: vault exists but CLAUDE.md missing. | Repair (fix what's broken) |
| `healthy` | All Critical + Standard checks pass | Report (show status, surface upgrades) |

## Centralized-vault signals (set by classification)

| Flag | Meaning | Used by |
|------|---------|---------|
| `IS_SYMLINK` | `vault` is a symlink | Routing, check #20 |
| `SYMLINK_BROKEN` | Symlink target missing | Repair |
| `SYMLINK_DRIFT` | `readlink vault` disagrees with `VAULT_TARGET` in script | Repair |
| `SCRIPT_EXISTS` | `scripts/setup-vault-symlink.sh` present | Repair (script backfill) |
| `EMBEDDED_OPTOUT` | CLAUDE.md has `\| **Vault layout** \| embedded ... \|` row | Externalization gating, check #20 |

When `REPAIR_REASON=centralized-vault-drift` or `centralized-vault-script-missing`, Partial Ark routing prioritizes the centralized-vault repair subsection (`references/centralized-vault-repair.md`) before generic Ark-artifact repair.
