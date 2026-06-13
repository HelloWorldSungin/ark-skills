#!/usr/bin/env bash
# seed_workarounds.sh — Phase 3: workaround-retirement registry seeder
# Emits JSON Lines per collector-contract.md §4.
# READ-ONLY against references/workarounds.yaml — proposals go to stdout and
# .omc/skill-healer/proposals.yaml ONLY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
REGISTRY="$SCRIPT_DIR/../references/workarounds.yaml"
PROPOSALS_DIR="$REPO_ROOT/.omc/skill-healer"
PROPOSALS_FILE="$PROPOSALS_DIR/proposals.yaml"

# --- contract banner (must be first line of stdout) ---
printf '{"_contract": 1, "_collector": "seed_workarounds"}\n'

# --- helpers ---
# Escape a string for JSON double-quoted value (strips newlines, escapes \ and ")
json_escape() {
  printf '%s' "$1" | tr -d '\n' | sed 's/\\/\\\\/g' | sed 's/"/\\"/g'
}

emit_proposal() {
  local dep="$1" issue_ref="$2" found_in="$3" description="$4" carrier="$5"
  local dep_prefix="${issue_ref%%#*}"
  local retire_when="${dep_prefix}#${issue_ref#*#} closed upstream"
  printf '{"kind":"workaround_proposal","dep":"%s","issue_ref":"%s","found_in":"%s","in_registry":false,"proposed_entry":{"description":"%s","upstream_issue_ref":"%s","carrier_file":"%s","retire_when":"%s"}}\n' \
    "$(json_escape "$dep")" \
    "$(json_escape "$issue_ref")" \
    "$(json_escape "$found_in")" \
    "$(json_escape "$description")" \
    "$(json_escape "$issue_ref")" \
    "$(json_escape "$carrier")" \
    "$(json_escape "$retire_when")"
}

# --- load registered refs ---
registered_refs=""
if [ -f "$REGISTRY" ]; then
  registered_refs="$(grep 'upstream_issue_ref:' "$REGISTRY" | sed 's/.*upstream_issue_ref:[[:space:]]*//' | tr -d '"' | tr '\n' ' ')"
fi

is_registered() {
  case " $registered_refs " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

# --- normalize a raw grep hit line to dep#NNN refs ---
# Accepts a line of text; prints one dep#NNN per line (may print zero lines).
# Two forms recognized:
#   1. Explicit:   mempalace#1457   chromadb#1092  gstack#42  superpowers#7  omc#99
#   2. GitHub URL: MemPalace/mempalace/(issues|pull)/NNNN  →  mempalace#NNNN
normalize_refs() {
  local line="$1"
  # Form 1: explicit dep#NNN
  printf '%s' "$line" | grep -oE '(mempalace|chromadb|gstack|superpowers|omc)#[0-9]+' || true
  # Form 2: GitHub URLs for mempalace repo (two passes to avoid nested-group portability issues)
  { printf '%s' "$line" | grep -oE 'MemPalace/mempalace/issues/[0-9]+' || true; \
    printf '%s' "$line" | grep -oE 'MemPalace/mempalace/pull/[0-9]+' || true; } \
    | sed 's|MemPalace/mempalace/issues/|mempalace#|; s|MemPalace/mempalace/pull/|mempalace#|'
}

# --- search target files ---
SEARCH_TARGETS=()
[ -d "$REPO_ROOT/skills" ]     && SEARCH_TARGETS+=("$REPO_ROOT/skills")
[ -f "$REPO_ROOT/CLAUDE.md" ]  && SEARCH_TARGETS+=("$REPO_ROOT/CLAUDE.md")
[ -f "$REPO_ROOT/CHANGELOG.md" ] && SEARCH_TARGETS+=("$REPO_ROOT/CHANGELOG.md")

# Combined search pattern: explicit refs OR GitHub URLs.
# POSIX ERE (plain alternation, no PCRE) so the grep fallback works on
# BSD/macOS grep, which lacks -P. rg's default (Rust) engine handles ERE too.
GREP_PATTERN='(mempalace|chromadb|gstack|superpowers|omc)#[0-9]+|MemPalace/mempalace/(issues|pull)/[0-9]+'

if command -v rg &>/dev/null; then
  grep_lines() { rg --no-heading -n "$GREP_PATTERN" "${SEARCH_TARGETS[@]}" 2>/dev/null || true; }
else
  grep_lines() { grep -rEn "$GREP_PATTERN" "${SEARCH_TARGETS[@]}" 2>/dev/null || true; }
fi

declare -A seen_refs
proposals_yaml_body=""

while IFS= read -r match_line; do
  [ -z "$match_line" ] && continue

  # Parse filepath:lineno:text  (rg --no-heading -n  or  grep -rn)
  filepath="${match_line%%:*}"
  rest="${match_line#*:}"
  lineno="${rest%%:*}"
  linetext="${rest#*:}"

  rel_path="${filepath#$REPO_ROOT/}"
  found_in="${rel_path}:${lineno}"

  # Normalize all refs on this line
  all_refs="$(normalize_refs "$linetext")"
  [ -z "$all_refs" ] && continue

  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    is_registered "$ref" && continue
    [ "${seen_refs[$ref]+x}" ] && continue
    seen_refs[$ref]=1

    # Dep label
    dep_prefix="${ref%%#*}"
    case "$dep_prefix" in
      mempalace)  dep="mempalace-cli" ;;
      chromadb)   dep="chromadb" ;;
      gstack)     dep="gstack" ;;
      superpowers) dep="superpowers" ;;
      omc)        dep="oh-my-claudecode" ;;
      *)          dep="$dep_prefix" ;;
    esac

    # Stub description: up to ~50 chars of context on each side of the ref number
    issue_num="${ref#*#}"
    snippet="$(printf '%s' "$linetext" | grep -oE ".{0,50}${issue_num}.{0,50}" | head -1 || true)"
    if [ -n "$snippet" ]; then
      description="Context: ${snippet}"
    else
      description="Upstream ref ${ref} found in source; review and add description."
    fi

    emit_proposal "$dep" "$ref" "$found_in" "$description" "$rel_path"

    retire_when="${dep_prefix}#${issue_num} closed upstream"
    proposals_yaml_body+="  - issue_ref: \"${ref}\"\n"
    proposals_yaml_body+="    found_in: \"${found_in}\"\n"
    proposals_yaml_body+="    dep: \"${dep}\"\n"
    proposals_yaml_body+="    in_registry: false\n"
    proposals_yaml_body+="    proposed_entry:\n"
    proposals_yaml_body+="      upstream_issue_ref: \"${ref}\"\n"
    proposals_yaml_body+="      carrier_file: \"${rel_path}\"\n"
    proposals_yaml_body+="      retire_when: \"${retire_when}\"\n"
    proposals_yaml_body+="      description: >\n"
    proposals_yaml_body+="        ${description}\n"
    proposals_yaml_body+="\n"

  done <<< "$all_refs"

done < <(grep_lines)

# --- write proposals.yaml (gitignored write surface, NEVER workarounds.yaml) ---
mkdir -p "$PROPOSALS_DIR"

{
  printf '# Generated by seed_workarounds.sh — DO NOT edit manually.\n'
  printf '# Review proposals and add approved entries to references/workarounds.yaml by hand.\n'
  if [ -n "$proposals_yaml_body" ]; then
    printf 'proposals:\n'
    printf '%b' "$proposals_yaml_body"
  else
    printf 'proposals: []\n'
  fi
} > "$PROPOSALS_FILE"
