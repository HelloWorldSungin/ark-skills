#!/usr/bin/env bash
# collect_inventory.sh — emits one inventory JSON record per dependency.
#
# Output: JSON Lines on stdout. First line is the contract banner
#   {"_contract": 1, "_collector": "collect_inventory"}
# Each subsequent line is an inventory record (see references/collector-contract.md §1).
#
# ── POSITIVE ALLOWLIST (the core discipline — AC2) ──────────────────────────
# A "dep" is ONLY one of:
#   (a) a name in ~/.claude/plugins/known_marketplaces.json that ark-skills
#       references in its OWN files (CLAUDE.md / AGENTS.md / README.md / skills/**), OR
#   (b) a pinned package in AGENTS.md / README.md / CLAUDE.md
#       (e.g. mempalace>=3.3.5, chromadb 1.5.7), OR
#   (c) a known binary/config dep with an explicit detector. gstack is branch (c) —
#       REQUIRED because gstack is ABSENT from known_marketplaces.json (verified).
#
# NOT a dep (explicitly excluded):
#   - a path-string (e.g. "docs/superpowers/plans/")
#   - an external-skills.yaml entry
#   - a .bats / test fixture
#   - ark-skills itself (it IS the project being healed)
#   - chromadb as a standalone record (it is an annotation on mempalace-cli)
#   - unrelated installed plugins (frontend-design, taches-cc-resources, code-review, …)
#
# The dep set below is GROUND TRUTH from .omc/skill-healer-build-progress.txt
# (live-probed 2026-06-05). Installed values (versions, SHAs, paths) are read
# LIVE from the json files / git clones; emission is gated on this allowlist.

set -euo pipefail

PLUGINS_DIR="${HOME}/.claude/plugins"
MARKETPLACES_JSON="${PLUGINS_DIR}/known_marketplaces.json"

# Resolve a marketplace clone path from known_marketplaces.json (live), with a
# conventional fallback so the collector still works if the json is absent.
mp_install_path() {
    local key="$1"
    local path=""
    if [ -f "$MARKETPLACES_JSON" ]; then
        path="$(jq -r --arg k "$key" '.[$k].installLocation // empty' "$MARKETPLACES_JSON" 2>/dev/null || true)"
    fi
    if [ -z "$path" ]; then
        path="${PLUGINS_DIR}/marketplaces/${key}"
    fi
    printf '%s' "$path"
}

# git short HEAD of a clone, or empty string if not a git repo.
git_head() {
    local clone="$1"
    git -C "$clone" rev-parse --short HEAD 2>/dev/null || printf ''
}

# true iff the clone is inside a git work tree (commit-range capable).
is_git_clone() {
    local clone="$1"
    git -C "$clone" rev-parse --is-inside-work-tree >/dev/null 2>&1
}

# Emit one inventory record. Arguments are pre-resolved; arrays are JSON strings.
emit() {
    local name="$1" dep_type="$2" source_url="$3" subtree_path="$4" \
          installed_version="$5" git_commit_sha="$6" install_path="$7" \
          commit_range_capable="$8" tiers_json="$9" annotations_json="${10}"

    jq -cn \
        --arg name "$name" \
        --arg dep_type "$dep_type" \
        --arg source_url "$source_url" \
        --argjson subtree_path "$subtree_path" \
        --argjson installed_version "$installed_version" \
        --argjson git_commit_sha "$git_commit_sha" \
        --argjson install_path "$install_path" \
        --argjson commit_range_capable "$commit_range_capable" \
        --argjson tiers "$tiers_json" \
        --argjson annotations "$annotations_json" \
        '{
            kind: "inventory",
            name: $name,
            dep_type: $dep_type,
            source_url: $source_url,
            subtree_path: $subtree_path,
            installed_version: $installed_version,
            git_commit_sha: $git_commit_sha,
            install_path: $install_path,
            commit_range_capable: $commit_range_capable,
            tiers: $tiers,
            annotations: $annotations
        }'
}

# JSON-encode a possibly-empty scalar as either a JSON string or null.
json_str_or_null() {
    local v="$1"
    if [ -z "$v" ]; then
        printf 'null'
    else
        printf '%s' "$v" | jq -Rs .
    fi
}

# ── banner ──────────────────────────────────────────────────────────────────
printf '%s\n' '{"_contract": 1, "_collector": "collect_inventory"}'

# ── (c) gstack — binary/config; ABSENT from known_marketplaces.json ─────────
# Detect via ~/.gstack/config.yaml + ~/.gstack/.last-setup-version (read version
# from the file). No marketplace clone, so the changelog tier has no LOCAL source —
# but the public upstream repo garrytan/gstack ships a CHANGELOG.md (probe-confirmed
# 2026-06-05; no GitHub releases/tags). source_url drives the binary-dep guarded
# REMOTE changelog fetch in collect_upstream.sh's changelog tier.
GSTACK_CONFIG="${HOME}/.gstack/config.yaml"
GSTACK_VERSION_FILE="${HOME}/.gstack/.last-setup-version"
if [ -f "$GSTACK_CONFIG" ]; then
    gstack_version=""
    if [ -f "$GSTACK_VERSION_FILE" ]; then
        gstack_version="$(tr -d '[:space:]' < "$GSTACK_VERSION_FILE")"
    fi
    emit "gstack" "binary" "garrytan/gstack" "null" \
        "$(json_str_or_null "$gstack_version")" "null" \
        "$(json_str_or_null "$GSTACK_CONFIG")" \
        "false" '["changelog","release"]' '[]'
fi

# ── (a) superpowers — plugin; clone is NOT a git repo, NO subtree ───────────
# claude-plugins-official clone has no superpowers subtree and is not a git work
# tree (verified) → commit_range_capable=false, NO commit tier.
# source_url is the UPSTREAM DEV repo obra/superpowers (from the installed plugin's
# own .claude-plugin/plugin.json repository field), NOT the claude-plugins-official
# marketplace aggregator — the aggregator publishes NO releases, the dev repo does
# (v5.1.0 …, probe-confirmed 2026-06-05). The local-clone changelog tier stays empty
# (no root CHANGELOG.md in the marketplace clone) and falls through to the release
# tier, which now resolves against obra/superpowers.
SP_CLONE="$(mp_install_path "claude-plugins-official")"
if is_git_clone "$SP_CLONE"; then
    sp_crc="true"
else
    sp_crc="false"
fi
emit "superpowers" "plugin" "obra/superpowers" "null" \
    "null" "null" "$(json_str_or_null "$SP_CLONE")" \
    "$sp_crc" '["changelog","release"]' '[]'

# ── (a) mempalace-plugin — plugin; git clone, commit-range capable ──────────
MP_CLONE="$(mp_install_path "mempalace")"
mp_sha="$(git_head "$MP_CLONE")"
if is_git_clone "$MP_CLONE"; then
    mp_crc="true"; mp_tiers='["changelog","release","commit"]'
else
    mp_crc="false"; mp_tiers='["changelog","release"]'
fi
emit "mempalace-plugin" "plugin" "milla-jovovich/mempalace" "null" \
    "null" "$(json_str_or_null "$mp_sha")" "$(json_str_or_null "$MP_CLONE")" \
    "$mp_crc" "$mp_tiers" '[]'

# ── (b) mempalace-cli — python; PyPI, no clone → releases tier ──────────────
# installed_version from `mempalace --version` (e.g. "MemPalace 3.3.5" → "3.3.5").
# chromadb is a transitive-pin ANNOTATION here, not a standalone record.
mpcli_version=""
if command -v mempalace >/dev/null 2>&1; then
    mpcli_version="$(mempalace --version 2>/dev/null | awk '{print $NF}' || true)"
fi
mpcli_path="$(command -v mempalace 2>/dev/null || true)"
emit "mempalace-cli" "python" "MemPalace/mempalace" "null" \
    "$(json_str_or_null "$mpcli_version")" "null" \
    "$(json_str_or_null "$mpcli_path")" \
    "false" '["changelog","release"]' \
    '["chromadb 1.5.7 is a transitive pin of this dep (M2/NIT-2) — not an independent cascade target"]'

# ── (a) oh-my-claudecode — plugin; git clone (marketplace key "omc") ────────
OMC_CLONE="$(mp_install_path "omc")"
omc_sha="$(git_head "$OMC_CLONE")"
if is_git_clone "$OMC_CLONE"; then
    omc_crc="true"; omc_tiers='["changelog","release","commit"]'
else
    omc_crc="false"; omc_tiers='["changelog","release"]'
fi
emit "oh-my-claudecode" "plugin" "Yeachan-Heo/oh-my-claudecode" "null" \
    "null" "$(json_str_or_null "$omc_sha")" "$(json_str_or_null "$OMC_CLONE")" \
    "$omc_crc" "$omc_tiers" '[]'

# ── (a) karpathy-skills — plugin; git clone ─────────────────────────────────
KP_CLONE="$(mp_install_path "karpathy-skills")"
kp_sha="$(git_head "$KP_CLONE")"
if is_git_clone "$KP_CLONE"; then
    kp_crc="true"; kp_tiers='["changelog","release","commit"]'
else
    kp_crc="false"; kp_tiers='["changelog","release"]'
fi
emit "karpathy-skills" "plugin" "forrestchang/andrej-karpathy-skills" "null" \
    "null" "$(json_str_or_null "$kp_sha")" "$(json_str_or_null "$KP_CLONE")" \
    "$kp_crc" "$kp_tiers" '[]'

# ── (a) obsidian-skills — plugin; git clone ─────────────────────────────────
OB_CLONE="$(mp_install_path "obsidian-skills")"
ob_sha="$(git_head "$OB_CLONE")"
if is_git_clone "$OB_CLONE"; then
    ob_crc="true"; ob_tiers='["changelog","release","commit"]'
else
    ob_crc="false"; ob_tiers='["changelog","release"]'
fi
emit "obsidian-skills" "plugin" "kepano/obsidian-skills" "null" \
    "null" "$(json_str_or_null "$ob_sha")" "$(json_str_or_null "$OB_CLONE")" \
    "$ob_crc" "$ob_tiers" '[]'
