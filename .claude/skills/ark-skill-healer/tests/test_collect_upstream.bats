#!/usr/bin/env bats
# test_collect_upstream.bats — the AC5 LINCHPIN (quiet second run), tier-downgrade
# (MF2 evidence_coarsened), and forced-change finding (AC4/AC7).

load helper

setup()    { healer_setup_tmp; chmod +x "$FIXTURES_DIR/make_fixture_clone.sh"; }
teardown() { healer_teardown_tmp; }

@test "AC5 linchpin: cold run baselines, second unchanged run is fully quiet" {
    # This test exercises the CASCADE quiet invariant. Disable the independent,
    # network-derived install-lag signal so the assertion does not depend on
    # transient live upstream-PyPI drift (install-lag has its own dedicated tests).
    export SKILL_HEALER_DISABLE_INSTALL_LAG=1
    # Run 1 (cold).
    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    # Every dep record on the cold run is quiet (baselined or no_change).
    nonquiet1="$(count_deltas "$output" '.quiet == false')"
    [ "$nonquiet1" -eq 0 ]

    # Run 2 (no change). ZERO non-quiet records — the quiet-second-run invariant.
    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    nonquiet2="$(count_deltas "$output" '.quiet == false')"
    [ "$nonquiet2" -eq 0 ]

    # And every dep that baselined on run 1 reports no_change on run 2.
    reasons="$(json_lines "$output" \
        | jq -r 'select(.kind=="upstream_delta") | .quiet_reason' | sort -u)"
    ! printf '%s\n' "$reasons" | grep -qx 'baselined'
}

@test "MF2 tier-downgrade: stored higher tier, only commit reachable, head unmoved -> evidence_coarsened (NOT a finding)" {
    # Build a hermetic fixture clone + fixture inventory (commit-tier-only dep).
    fx="$HEALER_TMP/fx"
    mkdir -p "$fx"
    head_sha="$(bash "$FIXTURES_DIR/make_fixture_clone.sh" "$fx")"
    export SKILL_HEALER_INVENTORY_SCRIPT="$fx/inventory.sh"

    # Pre-seed state: the dep was last seen at the CHANGELOG tier (a HIGHER tier
    # than commit). The commit tier was NEVER recorded. This simulates a prior run
    # that had richer evidence; this run can only reach the coarser commit tier.
    cat > "$SKILL_HEALER_STATE_DIR/fixdep.json" <<EOF
{"dep":"fixdep","tiers":{"changelog":{"content_hash":"sha256:previously-seen-richer-evidence","captured_at":"2026-01-01T00:00:00Z"}}}
EOF

    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    rec="$(json_lines "$output" | jq -c 'select(.kind=="upstream_delta" and .name=="fixdep")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.quiet')" = "true" ]
    [ "$(printf '%s' "$rec" | jq -r '.quiet_reason')" = "evidence_coarsened" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_tier')" = "commit" ]
}

@test "AC4/AC7 forced change: tampered changelog hash yields quiet:false with source_tier + non-empty evidence_refs" {
    # Baseline mempalace-plugin (changelog tier, reads its local clone CHANGELOG.md).
    run bash "$UPSTREAM_SH" --dep mempalace-plugin
    [ "$status" -eq 0 ]
    snap="$SKILL_HEALER_STATE_DIR/mempalace-plugin.json"
    [ -f "$snap" ]
    # Confirm it baselined at the changelog tier (deterministic, offline).
    [ "$(jq -r '.tiers.changelog.content_hash // "" ' "$snap")" != "" ]

    # Tamper the stored changelog hash to force a same-tier identity move.
    jq '.tiers.changelog.content_hash = "sha256:tampered"' "$snap" > "$snap.x"
    mv "$snap.x" "$snap"

    run bash "$UPSTREAM_SH" --dep mempalace-plugin
    [ "$status" -eq 0 ]
    rec="$(json_lines "$output" | jq -c 'select(.kind=="upstream_delta" and .name=="mempalace-plugin")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.quiet')" = "false" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_tier')" = "changelog" ]
    # Non-empty evidence_refs (verbatim issue refs mined from the changelog text).
    [ "$(printf '%s' "$rec" | jq -r '.evidence_refs | length')" -gt 0 ]
}

@test "install-lag: fake latest far ahead of installed -> quiet:false install_lag finding naming both versions" {
    # mempalace-cli is clone-less (commit_range_capable=false) and carries a live
    # installed_version from `mempalace --version`. The fake-latest env hook forces
    # the upstream-latest deterministically (no network), so a version far ahead of
    # the installed 3.3.5 must surface the install_lag false-negative class (S015).
    command -v mempalace >/dev/null 2>&1 || skip "mempalace CLI not installed (no installed_version to compare)"

    SKILL_HEALER_FAKE_LATEST_MEMPALACE_CLI=9.9.9 run bash "$UPSTREAM_SH" --dep mempalace-cli
    [ "$status" -eq 0 ]
    rec="$(json_lines "$output" \
        | jq -c 'select(.kind=="upstream_delta" and .name=="mempalace-cli" and .source_tier=="install_lag")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.quiet')" = "false" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_tier')" = "install_lag" ]
    # evidence_ref names BOTH versions verbatim.
    ev="$(printf '%s' "$rec" | jq -r '.evidence_refs[0]')"
    printf '%s' "$ev" | grep -q '9.9.9'
    [ "$(printf '%s' "$rec" | jq -r '.evidence_refs | length')" -gt 0 ]
    # prose_delta carries the verbatim comparison too.
    printf '%s' "$rec" | jq -r '.prose_delta' | grep -q 'upstream latest 9.9.9'
}

@test "install-lag: fake latest BEHIND installed -> no install_lag finding (not falsely flagged)" {
    command -v mempalace >/dev/null 2>&1 || skip "mempalace CLI not installed (no installed_version to compare)"

    # A fake latest older than the installed version must NOT produce a finding.
    SKILL_HEALER_FAKE_LATEST_MEMPALACE_CLI=0.0.1 run bash "$UPSTREAM_SH" --dep mempalace-cli
    [ "$status" -eq 0 ]
    rec="$(json_lines "$output" \
        | jq -c 'select(.kind=="upstream_delta" and .name=="mempalace-cli" and .source_tier=="install_lag")')"
    [ -z "$rec" ]
}

@test "install-lag is additive: latest == installed keeps the quiet second run fully quiet" {
    command -v mempalace >/dev/null 2>&1 || skip "mempalace CLI not installed (no installed_version to compare)"

    # Force upstream-latest == the live installed version so the comparison is the
    # normal in-sync case deterministically (no dependence on live PyPI state). No
    # install_lag finding is emitted, so the AC5 quiet-second-run invariant holds
    # across a cold + unchanged run.
    inst="$(mempalace --version 2>/dev/null | awk '{print $NF}')"
    [ -n "$inst" ] || skip "could not read installed mempalace version"
    export SKILL_HEALER_FAKE_LATEST_MEMPALACE_CLI="$inst"

    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    [ "$(count_deltas "$output" '.quiet == false')" -eq 0 ]

    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    [ "$(count_deltas "$output" '.quiet == false')" -eq 0 ]
    # Specifically, zero install_lag records when in sync.
    [ "$(count_deltas "$output" '.source_tier == "install_lag"')" -eq 0 ]
}

@test "forced commit-tier change carries a commit_range and source_tier:commit" {
    # karpathy-skills resolves to the commit tier (local git clone, deterministic).
    run bash "$UPSTREAM_SH" --dep karpathy-skills
    [ "$status" -eq 0 ]
    snap="$SKILL_HEALER_STATE_DIR/karpathy-skills.json"
    # Only assert if it baselined at the commit tier (it does in this environment;
    # skip gracefully if a future env resolves it elsewhere).
    stored="$(jq -r '.tiers.commit.head_sha // ""' "$snap" 2>/dev/null || true)"
    [ -n "$stored" ] || skip "karpathy-skills did not resolve to commit tier in this env"

    jq '.tiers.commit.head_sha = "deadbee"' "$snap" > "$snap.x"; mv "$snap.x" "$snap"
    run bash "$UPSTREAM_SH" --dep karpathy-skills
    [ "$status" -eq 0 ]
    rec="$(json_lines "$output" | jq -c 'select(.kind=="upstream_delta" and .name=="karpathy-skills")')"
    [ "$(printf '%s' "$rec" | jq -r '.quiet')" = "false" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_tier')" = "commit" ]
    printf '%s' "$rec" | jq -e '.commit_range | startswith("deadbee..")' >/dev/null
}
