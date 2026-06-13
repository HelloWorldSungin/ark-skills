#!/usr/bin/env bats
# test_lib_state.bats — lib_state.sh per-tier snapshot semantics (contract §3).

load helper

setup() {
    healer_setup_tmp
    # Source the lib under test. STATE_DIR is read at source time from the env,
    # so it must be exported (healer_setup_tmp does) before sourcing.
    . "$LIB_STATE_SH"
}
teardown() { healer_teardown_tmp; }

@test "per-dep cold-start: is_cold true before write, false after; sibling stays cold" {
    run lib_state__is_cold newdep
    [ "$status" -eq 0 ]            # exit 0 == cold

    lib_state__write_tier newdep changelog "sha256:abc"

    run lib_state__is_cold newdep
    [ "$status" -ne 0 ]            # no longer cold

    # A different, untouched dep is still cold.
    run lib_state__is_cold otherdep
    [ "$status" -eq 0 ]
}

@test "writing a second tier PRESERVES the first (per-tier merge)" {
    lib_state__write_tier d changelog "sha256:CL"
    lib_state__write_tier d commit "abc1234"

    [ "$(lib_state__read_tier d changelog)" = "sha256:CL" ]
    [ "$(lib_state__read_tier d commit)" = "abc1234" ]

    # Both tiers coexist in one file.
    file="$SKILL_HEALER_STATE_DIR/d.json"
    [ "$(jq -r '.tiers | keys | length' "$file")" -eq 2 ]
}

@test "atomic write leaves no .tmp file behind" {
    lib_state__write_tier d release "sha256:R"
    # No leftover *.tmp anywhere in the state dir.
    run bash -c "ls \"$SKILL_HEALER_STATE_DIR\"/*.tmp 2>/dev/null"
    [ "$status" -ne 0 ]
}

@test "commit tier stores head_sha; changelog stores content_hash (sha256:)" {
    lib_state__write_tier d commit "818b7f4"
    lib_state__write_tier d changelog "sha256:deadbeef"
    file="$SKILL_HEALER_STATE_DIR/d.json"

    # commit identity field is head_sha, a bare SHA (no sha256: prefix).
    [ "$(jq -r '.tiers.commit.head_sha' "$file")" = "818b7f4" ]
    [ "$(jq -r '.tiers.commit.content_hash // "null"' "$file")" = "null" ]

    # changelog identity field is content_hash, sha256:-prefixed.
    [ "$(jq -r '.tiers.changelog.content_hash' "$file")" = "sha256:deadbeef" ]
    [ "$(jq -r '.tiers.changelog.head_sha // "null"' "$file")" = "null" ]
}

@test "lib_state__hash emits a sha256:<hex> identity" {
    h="$(lib_state__hash "some content")"
    printf '%s' "$h" | grep -qE '^sha256:[0-9a-f]{64}$'
    # Deterministic.
    [ "$h" = "$(lib_state__hash "some content")" ]
}
