#!/usr/bin/env bash
# collect_upstream.sh — Phase 2: upstream fetch & diff cascade collector.
#
# Emits JSON Lines (one object per line) on stdout per the collector contract
# (references/collector-contract.md §2 upstream-delta, §3 snapshot). First line
# is the banner {"_contract": 1, "_collector": "collect_upstream"}.
#
# Input: inventory records from collect_inventory.sh (run live, banner skipped).
#
# Per dep, runs the CASCADE over the tiers in the dep's tiers[] field, in order,
# stopping at the first tier that yields content (references/cascade.md):
#   changelog → release → commit
#
# Per-tier diff semantics (AC5 linchpin):
#   - per-dep cold start            → quiet:baselined        (baseline active tier)
#   - active-tier identity unchanged → quiet:no_change
#   - tier downgrade, lower tier identity unmoved → quiet:evidence_coarsened (MF2)
#   - active-tier identity moved     → non-quiet upstream_delta + snapshot write
#
# Run manifest (.omc/skill-healer/run-manifest.json) makes a partial run
# resumable rather than mistaken for "quiet".
#
# Advisory-only: the entire write surface is the gitignored .omc/skill-healer/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

# shellcheck source=lib_state.sh
. "$SCRIPT_DIR/lib_state.sh"

# Inventory source is overridable for hermetic tests (fixture inventory). The
# override must emit the same JSONL contract as collect_inventory.sh.
INVENTORY_SCRIPT="${SKILL_HEALER_INVENTORY_SCRIPT:-$SCRIPT_DIR/collect_inventory.sh}"
RUN_DIR="$REPO_ROOT/.omc/skill-healer"
MANIFEST="$RUN_DIR/run-manifest.json"

# Tier ordering for downgrade detection: lower index = coarser/lower tier.
# changelog (richest, 2) > release (1) > commit (coarsest, 0).
tier_rank() {
    case "$1" in
        commit)    printf '0' ;;
        release)   printf '1' ;;
        changelog) printf '2' ;;
        *)         printf '-1' ;;
    esac
}

# --- optional --dep <name> restriction ---
ONLY_DEP=""
while [ $# -gt 0 ]; do
    case "$1" in
        --dep)
            ONLY_DEP="${2:-}"
            shift 2 || { echo "--dep requires a value" >&2; exit 2; }
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

# --- contract banner (must be first line of stdout) ---
printf '%s\n' '{"_contract": 1, "_collector": "collect_upstream"}'

# ── run-manifest helpers (transactional: tmp + atomic mv) ────────────────────
manifest_write() {
    local content="$1" tmp="${MANIFEST}.tmp"
    mkdir -p "$RUN_DIR"
    printf '%s' "$content" > "$tmp"
    mv -f "$tmp" "$MANIFEST"
}

# True (exit 0) if dep is already recorded in the manifest's deps_done[].
manifest_dep_done() {
    local dep="$1"
    [ -f "$MANIFEST" ] || return 1
    jq -e --arg d "$dep" '.deps_done | index($d) != null' "$MANIFEST" >/dev/null 2>&1
}

# Append a dep name to deps_done[] (idempotent), persist transactionally.
manifest_mark_done() {
    local dep="$1" updated
    updated="$(jq -c --arg d "$dep" \
        '.deps_done = ((.deps_done // []) + [$d] | unique)' "$MANIFEST")"
    manifest_write "$updated"
}

manifest_set_status() {
    local status="$1" updated
    updated="$(jq -c --arg s "$status" '.status = $s' "$MANIFEST")"
    manifest_write "$updated"
}

# ── emit a quiet upstream_delta record (no finding) ──────────────────────────
emit_quiet() {
    local name="$1" tier="$2" reason="$3"
    jq -cn \
        --arg name "$name" \
        --arg tier "$tier" \
        --arg reason "$reason" \
        '{
            kind: "upstream_delta",
            name: $name,
            source_tier: (if $tier == "" then null else $tier end),
            quiet: true,
            quiet_reason: $reason,
            prose_delta: null,
            evidence_refs: [],
            commit_range: null
        }'
}

# ── emit a non-quiet upstream_delta record (a finding) ───────────────────────
# evidence_refs_json and commit_range may be empty → encoded as [] / null.
emit_delta() {
    local name="$1" tier="$2" prose="$3" evidence_json="$4" commit_range="$5"
    local cr_json
    if [ -z "$commit_range" ]; then
        cr_json='null'
    else
        cr_json="$(printf '%s' "$commit_range" | jq -Rs .)"
    fi
    jq -cn \
        --arg name "$name" \
        --arg tier "$tier" \
        --arg prose "$prose" \
        --argjson evidence "$evidence_json" \
        --argjson commit_range "$cr_json" \
        '{
            kind: "upstream_delta",
            name: $name,
            source_tier: $tier,
            quiet: false,
            quiet_reason: null,
            prose_delta: $prose,
            evidence_refs: $evidence,
            commit_range: $commit_range
        }'
}

# ── verbatim evidence extraction ─────────────────────────────────────────────
# Pull VERBATIM evidence refs out of prose text:
#   - issue refs like  mempalace#1457 / chromadb#42 / omc#99 / gstack#7 / superpowers#3
#   - GitHub issue/PR URLs for the mempalace repo → normalized mempalace#NNNN
# Lines/SHAs themselves are added separately by the caller; this only mines refs.
# Emitted EXACTLY as found — never synthesized (MF5).
extract_issue_refs() {
    local text="$1"
    # Uses POSIX ERE only (grep -oE) — portable to BSD grep (macOS /usr/bin/grep
    # has no -P / lookbehind). Each printed line is a VERBATIM evidence ref.
    #
    # Qualified refs (dep#NNN) — emitted exactly as they appear.
    printf '%s' "$text" \
        | grep -oE '(mempalace|chromadb|gstack|superpowers|omc)#[0-9]+' || true
    # Bare #NNNN refs — emitted VERBATIM exactly as they appear (MF5: we do NOT
    # synthesize a dep prefix even though the dep is known; the SKILL.md layer
    # qualifies in context). A '#' that is part of a qualified ref (e.g. the
    # '#1457' inside 'mempalace#1457') is preceded by a letter; strip those so the
    # bare pass only keeps standalone refs. `grep -v` filters, never invents.
    printf '%s' "$text" \
        | grep -oE '[A-Za-z]?#[0-9]+' \
        | grep -E '^#[0-9]+$' || true
    # GitHub issue/PR URLs for the mempalace repo → normalized mempalace#NNNN
    # (the URL path IS the verbatim reference; this is normalization, not invention).
    { printf '%s' "$text" | grep -oE 'MemPalace/mempalace/issues/[0-9]+' || true; \
      printf '%s' "$text" | grep -oE 'MemPalace/mempalace/pull/[0-9]+' || true; } \
        | sed 's|MemPalace/mempalace/issues/|mempalace#|; s|MemPalace/mempalace/pull/|mempalace#|'
}

# Build a JSON array from newline-delimited verbatim strings (dedup, order-stable,
# drops blanks). Each element is emitted exactly as received.
lines_to_json_array() {
    local raw="$1"
    if [ -z "$raw" ]; then
        printf '[]'
        return 0
    fi
    printf '%s\n' "$raw" | jq -Rn '[inputs | select(length > 0)] | unique_by(.) // []' 2>/dev/null \
        || printf '[]'
}

# ── CASCADE tier collectors ──────────────────────────────────────────────────
# Each prints the tier's NEW content text to stdout, empty if the tier yields
# nothing. The caller decides identity + diff semantics.

# changelog tier:
#   - plugin deps: read CHANGELOG.md from the dep's local marketplace clone
#     (install_path). Fully OFFLINE.
#   - binary deps (no local clone, e.g. gstack): GUARDED network fetch of the
#     upstream repo's CHANGELOG.md (see tier_changelog_remote_text). Used only for
#     clone-less deps whose source ships a changelog but no GitHub releases.
#   - python/other: install_path points at a binary/config file, not a clone root,
#     and we do NOT network-fetch for these → empty (falls through to release).
# In every case the tier identity is the sha256 prose hash of the returned text.
tier_changelog_text() {
    local install_path="$1" dep_type="$2" name="${3:-}" source_url="${4:-}"
    local clone_dir cl
    local uref
    case "$dep_type" in
        plugin)
            clone_dir="$install_path"
            [ -n "$clone_dir" ] && [ -d "$clone_dir" ] || { printf ''; return 0; }
            # Read the UPSTREAM CHANGELOG.md (remote-tracking ref) so the changelog
            # tier detects upstream movement, not just a local pull. Fall back to
            # the working-tree file when the clone has no remote-tracking ref
            # (hermetic fixture) or the upstream ref lacks the file. Requires the
            # caller to have run git_upstream_fetch first.
            uref="$(git_upstream_ref "$clone_dir")"
            if [ -n "$uref" ] && git -C "$clone_dir" cat-file -e "$uref:CHANGELOG.md" 2>/dev/null; then
                git -C "$clone_dir" show "$uref:CHANGELOG.md" 2>/dev/null || printf ''
            elif [ -f "$clone_dir/CHANGELOG.md" ]; then
                cat "$clone_dir/CHANGELOG.md"
            else
                printf ''
            fi
            ;;
        binary)
            tier_changelog_remote_text "$name" "$source_url"
            ;;
        *)
            printf ''
            return 0
            ;;
    esac
}

# Remote CHANGELOG.md fetch for clone-less (binary) deps. GUARDED exactly like the
# release tier — never hard-fails: logs "tier=changelog skipped: <reason>" to stderr
# and prints empty on any miss so the cascade falls through cleanly (and the AC5
# "quiet" invariant holds offline). The fetched text's prose hash IS the changelog
# tier identity, identical to the local-clone path. NOTE: the upstream file may be
# large (gstack's is ~838 KB) — it baselines quietly; only a future *change* renders
# it as prose_delta, matching existing whole-file changelog-tier behavior.
tier_changelog_remote_text() {
    local name="$1" source_url="$2" body
    if [ -z "$source_url" ]; then
        echo "tier=changelog skipped: $name has no source_url (remote)" >&2
        printf ''; return 0
    fi
    if ! command -v gh >/dev/null 2>&1; then
        echo "tier=changelog skipped: $name gh not installed (remote)" >&2
        printf ''; return 0
    fi
    if ! gh auth status >/dev/null 2>&1; then
        echo "tier=changelog skipped: $name gh not authenticated (remote)" >&2
        printf ''; return 0
    fi
    if ! body="$(gh api "repos/${source_url}/contents/CHANGELOG.md" \
                    -H 'Accept: application/vnd.github.raw' 2>/dev/null)"; then
        echo "tier=changelog skipped: $name no remote CHANGELOG.md (network/404)" >&2
        printf ''; return 0
    fi
    printf '%s' "$body"
}

# release tier: gh release list/view. GUARDED — never hard-fails.
# Logs "tier=release skipped: <reason>" to stderr and prints empty on any failure.
tier_release_text() {
    local name="$1" source_url="$2"
    if [ -z "$source_url" ]; then
        echo "tier=release skipped: $name has no source_url" >&2
        printf ''
        return 0
    fi
    if ! command -v gh >/dev/null 2>&1; then
        echo "tier=release skipped: $name gh not installed" >&2
        printf ''
        return 0
    fi
    if ! gh auth status >/dev/null 2>&1; then
        echo "tier=release skipped: $name gh not authenticated" >&2
        printf ''
        return 0
    fi
    local list latest_tag notes
    if ! list="$(gh release list -R "$source_url" -L 5 2>/dev/null)"; then
        echo "tier=release skipped: $name gh release list failed (network/rate-limit)" >&2
        printf ''
        return 0
    fi
    if [ -z "$list" ]; then
        echo "tier=release skipped: $name no releases published" >&2
        printf ''
        return 0
    fi
    # `gh release list` columns are TAB-separated: TITLE \t TYPE \t TAGNAME \t
    # PUBLISHED. The tag to pass to `gh release view` is the TAGNAME (column 3).
    latest_tag="$(printf '%s\n' "$list" | head -1 | awk -F'\t' '{print $3}')"
    if [ -z "$latest_tag" ]; then
        echo "tier=release skipped: $name could not parse latest release tag" >&2
        printf ''
        return 0
    fi
    if ! notes="$(gh release view "$latest_tag" -R "$source_url" 2>/dev/null)"; then
        echo "tier=release skipped: $name gh release view failed (network/rate-limit)" >&2
        printf ''
        return 0
    fi
    printf '%s' "$notes"
}

# commit tier: git log <last>..<upstream-tip>. Only for commit_range_capable deps.
# Prints the oneline log text. The IDENTITY for this tier is the UPSTREAM tip SHA
# (handled by the caller), NOT a prose hash. The log target is the remote-tracking
# ref so the evidence subjects are the UPSTREAM commits ahead of the install; it
# falls back to local HEAD when the clone has no remote-tracking ref (hermetic
# fixture / detached). Requires the caller to have run git_upstream_fetch first so
# the upstream objects are present.
tier_commit_text() {
    local dep="$1" clone_dir="$2"
    if [ -z "$clone_dir" ] || ! git -C "$clone_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        printf ''
        return 0
    fi
    local last target tip
    target="$(git_upstream_ref "$clone_dir")"
    [ -n "$target" ] || target="HEAD"
    tip="$(git -C "$clone_dir" rev-parse --short "$target" 2>/dev/null || true)"
    [ -n "$tip" ] || { printf ''; return 0; }
    last="$(lib_state__read_tier "$dep" commit)"
    if [ -z "$last" ]; then
        # cold for the commit tier: no range to diff. Content is the upstream tip
        # commit subject so the tier "yields content" and can be baselined.
        git -C "$clone_dir" log -1 --oneline "$target" 2>/dev/null || true
    else
        git -C "$clone_dir" log "${last}..${target}" --oneline 2>/dev/null || true
    fi
}

git_head_sha() {
    local clone_dir="$1"
    git -C "$clone_dir" rev-parse --short HEAD 2>/dev/null || true
}

# ── upstream-tracking helpers — detect UPSTREAM movement, not local ──────────
# The changelog (plugin) and commit tiers compare against the dep's UPSTREAM tip
# (its remote-tracking ref), not the local checkout, so a finding fires when the
# upstream repo moves ahead of the installed clone even if the user has not
# pulled. All three are GUARDED: a clone with no remote (the hermetic test
# fixture) or an offline run resolves to empty, and every caller falls back to
# the local HEAD / working-tree file so the cascade still completes (AC5
# offline-quiet holds).

# Print the remote-tracking ref for the clone's current branch (e.g.
# "origin/develop"), or empty when the clone has no upstream/remote.
git_upstream_ref() {
    local clone="$1" ref br
    [ -n "$clone" ] || { printf ''; return 0; }
    git -C "$clone" rev-parse --is-inside-work-tree >/dev/null 2>&1 || { printf ''; return 0; }
    # Prefer the branch's configured upstream (@{u}); fall back to origin/<branch>.
    ref="$(git -C "$clone" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
    if [ -z "$ref" ]; then
        br="$(git -C "$clone" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
        if [ -n "$br" ] && git -C "$clone" rev-parse --verify -q "origin/$br" >/dev/null 2>&1; then
            ref="origin/$br"
        fi
    fi
    printf '%s' "$ref"
}

# Guarded fetch so the remote tip + objects are locally available. Never
# hard-fails (offline/SSH-prompt/rate-limit → log a skip, fall through to the
# cached ref). Only updates refs/remotes/* — never the working tree, HEAD, or
# local branches, so it is non-destructive to the user's plugin clones.
# BatchMode + ConnectTimeout keep an unreachable remote from hanging or prompting.
git_upstream_fetch() {
    local clone="$1" name="${2:-}" ref remote
    ref="$(git_upstream_ref "$clone")"
    [ -n "$ref" ] || { echo "upstream fetch skipped: ${name:-$clone} no remote-tracking ref" >&2; return 0; }
    remote="${ref%%/*}"
    GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=5' \
        git -C "$clone" fetch --quiet "$remote" 2>/dev/null \
        || echo "upstream fetch skipped: ${name:-$clone} fetch failed (offline/rate-limit) — using cached ref" >&2
}

# Upstream tip short SHA (post-fetch), or empty when no upstream ref resolvable.
git_upstream_sha() {
    local clone="$1" ref
    ref="$(git_upstream_ref "$clone")"
    [ -n "$ref" ] || { printf ''; return 0; }
    git -C "$clone" rev-parse --short "$ref" 2>/dev/null || true
}

# ── install-lag check (clone-less binary/python deps) ────────────────────────
# The cascade's changelog tier compares upstream-now vs upstream-last-seen (a prose
# hash); it NEVER compares the INSTALLED version against upstream-latest. Clone-backed
# deps catch install-lag through the commit tier (upstream tip vs local HEAD), but
# clone-less deps (gstack, mempalace-cli) have no such comparison — so a clone-less
# dep can be many releases behind the user's installed copy yet report quiet (S015
# false-negative class). This check runs PER DEP, INDEPENDENT of the cascade diff,
# for deps that are NOT commit_range_capable and carry a non-null installed_version.

# Sanitize a dep name into an env-var suffix: uppercased, non-alnum → '_'.
#   mempalace-cli → MEMPALACE_CLI
sanitize_dep_env() {
    printf '%s' "$1" | tr '[:lower:]' '[:upper:]' | tr -c 'A-Z0-9' '_' \
        | sed 's/_*$//'
}

# Resolve the LATEST upstream version for a dep. NETWORK-GUARDED — on any failure
# (no curl/gh, offline, 404, rate-limit) logs to stderr and prints empty so the
# caller SKIPS the lag check (no hard-fail, no false finding).
#
# Resolution order:
#   1. HERMETIC TEST HOOK: env override SKILL_HEALER_FAKE_LATEST_<DEP_SANITIZED>
#      (e.g. SKILL_HEALER_FAKE_LATEST_MEMPALACE_CLI). If set, use it; skip network.
#   2. PyPI — ONLY for python deps (dep_type == "python"). Package name = explicit
#      map (mempalace-cli → `mempalace`) or lowercase last path segment of source_url.
#      Query pypi.org/pypi/<pkg>/json → .info.version. Gating on dep_type avoids a
#      WRONG-package match: garrytan/gstack's last segment "gstack" collides with an
#      UNRELATED PyPI package `gstack` (1.1.1) — only python deps should hit PyPI.
#   3. Generic fallback (any dep): gh release view -R <source_url> --json tagName
#      (strip a leading 'v').
#
# v1 LIMIT: gstack is dep_type=binary (skips PyPI) and garrytan/gstack ships a
# CHANGELOG.md but NO GitHub releases/tags — so step 3 returns empty. gstack's
# install-lag therefore stays UNRESOLVED (logged, skipped) until upstream publishes
# a resolvable version artifact (tagged release or PyPI dist). Documented limit.
resolve_latest_version() {
    local dep="$1" source_url="$2" dep_type="${3:-}" env_name fake pkg latest tag

    # 1. hermetic test hook
    env_name="SKILL_HEALER_FAKE_LATEST_$(sanitize_dep_env "$dep")"
    fake="$(eval "printf '%s' \"\${${env_name}:-}\"")"
    if [ -n "$fake" ]; then
        printf '%s' "$fake"
        return 0
    fi

    # Hermetic override: when set, skip ALL network resolution (the fake-latest
    # hook above still wins). Lets the cascade-focused AC5 tests neutralize the
    # live, network-derived install-lag signal so they test the cascade no-change
    # invariant deterministically, independent of transient upstream-PyPI drift.
    # The live /ark-skill-healer run leaves this unset, so install-lag stays active.
    if [ -n "${SKILL_HEALER_DISABLE_INSTALL_LAG:-}" ]; then
        echo "install-lag: $dep skipped (SKILL_HEALER_DISABLE_INSTALL_LAG set)" >&2
        printf ''; return 0
    fi

    [ -n "$source_url" ] || {
        echo "install-lag: $dep latest-version unresolved: no source_url" >&2
        printf ''; return 0
    }

    # 2. PyPI — ONLY for python deps. Package = explicit map or lowercase last
    # segment. Gating on dep_type prevents the garrytan/gstack → PyPI `gstack`
    # (unrelated, 1.1.1) wrong-package collision.
    if [ "$dep_type" = "python" ]; then
        if [ "$dep" = "mempalace-cli" ]; then
            pkg="mempalace"
        else
            pkg="$(printf '%s' "${source_url##*/}" | tr '[:upper:]' '[:lower:]')"
        fi
        if command -v curl >/dev/null 2>&1; then
            if latest="$(curl -fsSL --max-time 10 "https://pypi.org/pypi/${pkg}/json" 2>/dev/null \
                            | jq -r '.info.version // empty' 2>/dev/null)" \
               && [ -n "$latest" ]; then
                printf '%s' "$latest"
                return 0
            fi
        fi
    fi

    # 3. generic fallback: gh release view (strip a single leading 'v').
    if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
        if tag="$(gh release view -R "$source_url" --json tagName -q .tagName 2>/dev/null)" \
           && [ -n "$tag" ]; then
            printf '%s' "${tag#v}"
            return 0
        fi
    fi

    echo "install-lag: $dep latest-version unresolved: PyPI miss + gh release unavailable (offline/404/rate-limit/no-tool)" >&2
    printf ''
    return 0
}

# True (exit 0) iff $installed is strictly BEHIND $latest by version-aware order:
#   installed != latest AND sort -V puts installed first.
version_is_behind() {
    local installed="$1" latest="$2" lowest
    [ "$installed" != "$latest" ] || return 1
    lowest="$(printf '%s\n%s\n' "$installed" "$latest" | sort -V | head -1)"
    [ "$lowest" = "$installed" ]
}

# Emit an install_lag finding if the dep's installed_version is behind upstream
# latest. ADDITIVE: when installed == latest (or ahead), or latest is unresolved,
# nothing is emitted — the normal cascade result stands and a no-change run stays
# quiet (AC5 invariant preserved). Skips commit_range_capable deps (they catch lag
# via the commit tier) and deps with a null/empty installed_version.
check_install_lag() {
    local name="$1" source_url="$2" commit_range_capable="$3" installed_version="$4" dep_type="${5:-}"
    [ "$commit_range_capable" = "true" ] && return 0
    [ -n "$installed_version" ] && [ "$installed_version" != "null" ] || return 0

    local latest
    latest="$(resolve_latest_version "$name" "$source_url" "$dep_type")"
    [ -n "$latest" ] || return 0   # unresolved → skip (already logged to stderr)

    if version_is_behind "$installed_version" "$latest"; then
        local prose evidence_json
        prose="installed ${installed_version}, upstream latest ${latest}"
        # Self-evident verbatim comparison ref (not a synthesized external citation).
        evidence_json="$(printf '%s\n' "installed ${installed_version} < latest ${latest}" \
            | jq -Rn '[inputs | select(length > 0)]')"
        emit_delta "$name" "install_lag" "$prose" "$evidence_json" ""
    fi
}

# ── per-dep cascade driver ───────────────────────────────────────────────────
process_dep() {
    local record="$1"
    local name dep_type source_url install_path commit_range_capable tiers_json installed_version
    name="$(printf '%s' "$record" | jq -r '.name')"
    dep_type="$(printf '%s' "$record" | jq -r '.dep_type')"
    source_url="$(printf '%s' "$record" | jq -r '.source_url // ""')"
    install_path="$(printf '%s' "$record" | jq -r '.install_path // ""')"
    commit_range_capable="$(printf '%s' "$record" | jq -r '.commit_range_capable')"
    tiers_json="$(printf '%s' "$record" | jq -c '.tiers')"
    installed_version="$(printf '%s' "$record" | jq -r '.installed_version // ""')"

    # For git-clone-backed deps, refresh remote-tracking refs ONCE up front so the
    # changelog and commit tiers both compare against the UPSTREAM tip. Self-guards
    # (no-op for non-clone install_paths like a CLI binary or config file) and
    # never hard-fails offline.
    git_upstream_fetch "$install_path" "$name"

    # Install-lag check: runs INDEPENDENT of the cascade diff (S015 false-negative
    # class). Emits at most one extra non-quiet install_lag record; contributes
    # nothing when not behind / unresolved, so the AC5 quiet-second-run invariant
    # holds (installed == upstream-latest is the normal live-machine case).
    check_install_lag "$name" "$source_url" "$commit_range_capable" "$installed_version" "$dep_type"

    # Walk the dep's tiers in order; stop at the first that yields content.
    local active_tier="" active_text="" active_identity=""
    local tier
    while IFS= read -r tier; do
        [ -n "$tier" ] || continue
        local text="" identity=""
        case "$tier" in
            changelog)
                text="$(tier_changelog_text "$install_path" "$dep_type" "$name" "$source_url")"
                [ -n "$text" ] && identity="$(lib_state__hash "$text")"
                ;;
            release)
                text="$(tier_release_text "$name" "$source_url")"
                [ -n "$text" ] && identity="$(lib_state__hash "$text")"
                ;;
            commit)
                # Only commit_range_capable deps run the commit tier.
                if [ "$commit_range_capable" = "true" ]; then
                    # The commit tier's IDENTITY is the UPSTREAM tip SHA — so the
                    # tier "moves" when the upstream repo advances, not merely when
                    # the user pulls. Falls back to local HEAD for a clone with no
                    # remote-tracking ref (hermetic fixture). The tier is "active"
                    # whenever that SHA exists, even when the log range is empty
                    # (upstream unmoved); the (possibly empty) log is the prose_delta.
                    identity="$(git_upstream_sha "$install_path")"
                    [ -n "$identity" ] || identity="$(git_head_sha "$install_path")"
                    text="$(tier_commit_text "$name" "$install_path")"
                fi
                ;;
        esac
        # A tier is "active" when its identity is determinable. For changelog/
        # release that requires non-empty text (the text IS the identity source);
        # for commit the HEAD SHA suffices even if the diff text is empty.
        if [ -n "$identity" ] && { [ "$tier" = "commit" ] || [ -n "$text" ]; }; then
            active_tier="$tier"
            active_text="$text"
            active_identity="$identity"
            break
        fi
    done < <(printf '%s' "$tiers_json" | jq -r '.[]')

    # No tier produced content at all → quiet, no active tier.
    if [ -z "$active_tier" ]; then
        emit_quiet "$name" "" "no_change"
        return 0
    fi

    # Per-dep cold start: baseline the active tier, emit quiet:baselined.
    if lib_state__is_cold "$name"; then
        lib_state__write_tier "$name" "$active_tier" "$active_identity"
        emit_quiet "$name" "$active_tier" "baselined"
        return 0
    fi

    local stored_active
    stored_active="$(lib_state__read_tier "$name" "$active_tier")"

    # Same-tier identity unchanged → quiet:no_change.
    if [ "$stored_active" = "$active_identity" ]; then
        emit_quiet "$name" "$active_tier" "no_change"
        return 0
    fi

    # Detect a tier downgrade: did last run store a HIGHER tier than the one
    # active this run? If so, and the active (lower) tier's own identity has NOT
    # moved, this is evidence coarsening — quiet, never a finding (MF2 fix).
    if [ -z "$stored_active" ]; then
        local active_rank highest_stored_rank highest_stored_tier t r stored
        active_rank="$(tier_rank "$active_tier")"
        highest_stored_rank=-1
        highest_stored_tier=""
        for t in changelog release commit; do
            stored="$(lib_state__read_tier "$name" "$t")"
            [ -n "$stored" ] || continue
            r="$(tier_rank "$t")"
            if [ "$r" -gt "$highest_stored_rank" ]; then
                highest_stored_rank="$r"
                highest_stored_tier="$t"
            fi
        done
        # A higher tier was seen before, but this run only reached a lower tier,
        # and the lower (active) tier was never recorded (its own identity has not
        # moved from a stored value). → evidence_coarsened.
        if [ -n "$highest_stored_tier" ] && [ "$highest_stored_rank" -gt "$active_rank" ]; then
            emit_quiet "$name" "$active_tier" "evidence_coarsened"
            return 0
        fi
    fi

    # Same-tier identity moved → a real finding.
    local commit_range="" evidence_raw="" evidence_json
    if [ "$active_tier" = "commit" ]; then
        local last head
        last="$(lib_state__read_tier "$name" commit)"
        # Range head = UPSTREAM tip (matches the commit-tier identity); fall back
        # to local HEAD for a no-remote clone.
        head="$(git_upstream_sha "$install_path")"
        [ -n "$head" ] || head="$(git_head_sha "$install_path")"
        if [ -n "$last" ] && [ -n "$head" ]; then
            commit_range="${last}..${head}"
        fi
        # Verbatim evidence for the commit tier = each "<sha> <subject>" log line.
        evidence_raw="$active_text"
    else
        # changelog/release: verbatim evidence = issue refs mined from the text.
        evidence_raw="$(extract_issue_refs "$active_text")"
    fi

    evidence_json="$(lines_to_json_array "$evidence_raw")"
    emit_delta "$name" "$active_tier" "$active_text" "$evidence_json" "$commit_range"

    # Advance the snapshot for THAT tier only.
    lib_state__write_tier "$name" "$active_tier" "$active_identity"
}

# ── gather inventory records (skip the banner line) ──────────────────────────
INVENTORY_OUT="$("$INVENTORY_SCRIPT")"
# All inventory records (banner is the only line with ._contract).
mapfile -t DEP_RECORDS < <(printf '%s\n' "$INVENTORY_OUT" \
    | jq -c 'select(.kind == "inventory")')

# Apply --dep restriction if requested.
if [ -n "$ONLY_DEP" ]; then
    FILTERED=()
    for rec in "${DEP_RECORDS[@]}"; do
        if [ "$(printf '%s' "$rec" | jq -r '.name')" = "$ONLY_DEP" ]; then
            FILTERED+=("$rec")
        fi
    done
    DEP_RECORDS=("${FILTERED[@]}")
fi

DEPS_TOTAL="${#DEP_RECORDS[@]}"

# ── run-manifest: RESUME if in_progress, else initialize ─────────────────────
RESUMING=false
if [ -f "$MANIFEST" ] \
   && [ "$(jq -r '.status // ""' "$MANIFEST" 2>/dev/null || true)" = "in_progress" ]; then
    RESUMING=true
else
    manifest_write "$(jq -cn \
        --arg run_id "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --argjson deps_total "$DEPS_TOTAL" \
        '{run_id: $run_id, deps_total: $deps_total, deps_done: [], status: "in_progress"}')"
fi

# ── drive each dep through the cascade ───────────────────────────────────────
for rec in "${DEP_RECORDS[@]}"; do
    dep_name="$(printf '%s' "$rec" | jq -r '.name')"

    # RESUME: skip deps already completed in a prior interrupted run.
    if [ "$RESUMING" = "true" ] && manifest_dep_done "$dep_name"; then
        continue
    fi

    process_dep "$rec"
    manifest_mark_done "$dep_name"
done

# ── all deps processed → mark the run complete ───────────────────────────────
manifest_set_status "complete"
