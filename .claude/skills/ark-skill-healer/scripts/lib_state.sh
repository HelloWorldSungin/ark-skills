#!/usr/bin/env bash
# lib_state.sh — sourced library for per-tier last-seen state.
#
# Implements the snapshot record (references/collector-contract.md §3):
#   Stored at $STATE_DIR/<dep>.json, keyed PER TIER.
#   {
#     "dep": "<dep>",
#     "tiers": {
#       "changelog": { "content_hash": "sha256:…", "captured_at": "<iso>" },
#       "release":   { "content_hash": "sha256:…", "captured_at": "<iso>" },
#       "commit":    { "head_sha": "818b7f4",      "captured_at": "<iso>" }
#     }
#   }
#
# This file is a LIBRARY: source it, no top-level side effects. Pure bash + jq + shasum.
#
# Public API:
#   lib_state__hash <string>             → "sha256:<hex>"
#   lib_state__read_tier <dep> <tier>    → prints stored identity (content_hash or
#                                          head_sha) for dep+tier, empty if cold
#   lib_state__write_tier <dep> <tier> <identity>
#                                        → upserts that tier into <dep>.json
#                                          transactionally (tmp + atomic mv),
#                                          preserving other tiers (jq merge)
#   lib_state__is_cold <dep>             → exit 0 if no <dep>.json (per-dep cold-start)
#
# State dir is overridable for tests via SKILL_HEALER_STATE_DIR.

# Default state dir is anchored to the repo root (this lib lives at
# scripts/lib_state.sh, so ../../../.. is the repo root) — NOT the caller's cwd.
# A cwd-relative default silently wrote baselines to whatever dir the collector
# was invoked from, so every run cold-started. Still overridable via
# SKILL_HEALER_STATE_DIR (tests rely on this for a hermetic state dir).
_LIB_STATE_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
STATE_DIR="${SKILL_HEALER_STATE_DIR:-$_LIB_STATE_REPO_ROOT/.omc/skill-healer/state/last-seen}"

# Path to a dep's snapshot file.
lib_state__file() {
    printf '%s/%s.json' "$STATE_DIR" "$1"
}

# Hash a string → sha256:<hex>. Uses shasum -a 256 (macOS-native).
lib_state__hash() {
    local s="$1" hex
    hex="$(printf '%s' "$s" | shasum -a 256 | awk '{print $1}')"
    printf 'sha256:%s' "$hex"
}

# The identity field name varies by tier: commit → head_sha, else content_hash.
lib_state__identity_field() {
    if [ "$1" = "commit" ]; then
        printf 'head_sha'
    else
        printf 'content_hash'
    fi
}

# Read the stored identity for dep+tier. Prints empty string when cold/absent.
lib_state__read_tier() {
    local dep="$1" tier="$2" file field
    file="$(lib_state__file "$dep")"
    [ -f "$file" ] || return 0
    field="$(lib_state__identity_field "$tier")"
    jq -r --arg tier "$tier" --arg field "$field" \
        '.tiers[$tier][$field] // empty' "$file" 2>/dev/null || true
}

# Upsert dep+tier identity transactionally, preserving any other tiers present.
lib_state__write_tier() {
    local dep="$1" tier="$2" identity="$3" file tmp field captured current
    file="$(lib_state__file "$dep")"
    field="$(lib_state__identity_field "$tier")"
    captured="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    mkdir -p "$STATE_DIR"

    # Seed from existing file (merge → preserve other tiers) or a fresh object.
    if [ -f "$file" ]; then
        current="$(cat "$file")"
    else
        current='{}'
    fi

    tmp="${file}.tmp"
    printf '%s' "$current" | jq \
        --arg dep "$dep" \
        --arg tier "$tier" \
        --arg field "$field" \
        --arg identity "$identity" \
        --arg captured "$captured" \
        '
        { dep: $dep, tiers: ( .tiers // {} ) }
        | .tiers[$tier] = { ($field): $identity, captured_at: $captured }
        ' > "$tmp"

    mv -f "$tmp" "$file"
}

# Per-dep cold-start: exit 0 if no snapshot file exists for this dep.
lib_state__is_cold() {
    local file
    file="$(lib_state__file "$1")"
    [ ! -f "$file" ]
}
