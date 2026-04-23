# /ark-onboard — Centralized-Vault Repair Scenarios

Idempotent, non-destructive fixes for centralized-vault drift. Invoked by `SKILL.md § Path: Partial Ark (Repair)` when `REPAIR_REASON=centralized-vault-drift` or `centralized-vault-script-missing`. Runs BEFORE the generic 5-step repair flow.

---

## Determine `<vault_repo_path>` (ordered)

1. If `scripts/setup-vault-symlink.sh` exists, extract `VAULT_TARGET` via the grep contract, then expand `$HOME`:

```bash
SCRIPT_TARGET=$(grep -E '^VAULT_TARGET="[^"]*"\s*$' scripts/setup-vault-symlink.sh | head -1 | sed -E 's/^VAULT_TARGET="([^"]+)".*$/\1/')
VAULT_REPO_PATH_EXPANDED=$(eval "echo $SCRIPT_TARGET")
```

2. Else if `vault` is a broken symlink, use `readlink vault` as the intended target.
3. Else prompt the user with the Greenfield smart default (detect `$HOME/.superset/` etc.).

---

## Scenario: `vault` missing entirely + script present

```bash
read -rp "Recreate vault symlink to $VAULT_REPO_PATH_EXPANDED? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  if [ -d "$VAULT_REPO_PATH_EXPANDED" ]; then
    ln -s "$VAULT_REPO_PATH_EXPANDED" vault
    echo "vault symlink recreated."
  else
    echo "ERROR: $VAULT_REPO_PATH_EXPANDED not present. Clone the vault repo there first:"
    echo "  git clone <remote> $VAULT_REPO_PATH_EXPANDED"
  fi
;; esac
```

---

## Scenario: `vault` is a broken symlink

```bash
read -rp "Remove broken symlink and relink? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  TARGET=$(readlink vault)
  rm vault
  if [ -d "$TARGET" ]; then
    ln -s "$TARGET" vault
    echo "symlink recreated."
  else
    echo "Original target $TARGET missing. Clone or restore it, then rerun /ark-onboard."
  fi
;; esac
```

---

## Scenario: symlink drift (`readlink vault` != script's `VAULT_TARGET`)

```bash
SYMLINK_TARGET=$(readlink vault)
echo "Drift detected:"
echo "  vault symlink points to: $SYMLINK_TARGET"
echo "  script VAULT_TARGET expands to: $VAULT_REPO_PATH_EXPANDED"
echo ""
echo "Which is canonical? Choose one:"
echo "  [S] Trust the symlink — update the script's VAULT_TARGET to match."
echo "  [V] Trust the script — remove the symlink and recreate from VAULT_TARGET."
echo "  [N] Do nothing — leave as-is."
read -rp "Choice [S/V/N]: " ANS
case "$ANS" in
  S|s)
    # Convert back to portable form (if possible)
    PORTABLE=$(echo "$SYMLINK_TARGET" | sed "s|^$HOME|\$HOME|")
    case "$PORTABLE" in
      '$HOME/'*)
        sed -i.bak -E "s|^VAULT_TARGET=\"[^\"]*\"|VAULT_TARGET=\"$PORTABLE\"|" scripts/setup-vault-symlink.sh
        rm scripts/setup-vault-symlink.sh.bak
        echo "Script updated. Commit the change."
        ;;
      *)
        echo "ERROR: current symlink target $SYMLINK_TARGET is not under \$HOME."
        echo "Move the vault under \$HOME first, then rerun."
        ;;
    esac
    ;;
  V|v)
    rm vault
    if [ -d "$VAULT_REPO_PATH_EXPANDED" ]; then
      ln -s "$VAULT_REPO_PATH_EXPANDED" vault
      echo "Symlink recreated from script VAULT_TARGET."
    else
      echo "ERROR: $VAULT_REPO_PATH_EXPANDED not present. Fix the script OR clone to that path."
    fi
    ;;
  *) echo "No changes made." ;;
esac
```

---

## Scenario: `scripts/setup-vault-symlink.sh` missing but symlink is valid (backfill)

Covers the case where ArkNode-Poly-style hand-rolled layouts predate the canonical script.

```bash
SYMLINK_TARGET=$(readlink vault)
PORTABLE=$(echo "$SYMLINK_TARGET" | sed "s|^$HOME|\$HOME|")
case "$PORTABLE" in
  '$HOME/'*)
    read -rp "Backfill scripts/setup-vault-symlink.sh with VAULT_TARGET=$PORTABLE? [Y/n] " ANS
    case "$ANS" in n|N) ;; *)
      mkdir -p scripts
      # Write the template from references/templates.md § scripts/setup-vault-symlink.sh
      # with VAULT_TARGET set to $PORTABLE.
      chmod +x scripts/setup-vault-symlink.sh
      echo "Script backfilled."
    ;; esac
    ;;
  *) echo "Current symlink target not under \$HOME. Cannot backfill portable script."; ;;
esac
```

---

## Scenario: `<common_git_dir>/hooks/post-checkout` missing or non-executable

```bash
HOOK_PATH="$(git rev-parse --git-common-dir)/hooks/post-checkout"
read -rp "Install post-checkout hook at $HOOK_PATH? [Y/n] " ANS
case "$ANS" in n|N) ;; *)
  cat > "$HOOK_PATH" <<'HOOK_EOF'
#!/usr/bin/env bash
[ "$3" != "1" ] && exit 0
exec "$(git rev-parse --show-toplevel)/scripts/setup-vault-symlink.sh"
HOOK_EOF
  chmod +x "$HOOK_PATH"
  echo "Hook installed."
;; esac
```

---

After centralized-vault repairs complete, fall through to the generic 5-step repair flow in `SKILL.md` (it re-runs the diagnostic and catches any remaining failures).
