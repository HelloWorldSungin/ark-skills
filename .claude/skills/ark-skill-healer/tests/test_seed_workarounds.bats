#!/usr/bin/env bats
# test_seed_workarounds.bats — seeder is READ-ONLY against the registry and only
# proposes untracked refs (contract §4).

load helper

setup()    { healer_setup_tmp; }
teardown() { healer_teardown_tmp; }

@test "running the seeder does NOT modify references/workarounds.yaml" {
    reg="$REFERENCES_DIR/workarounds.yaml"
    [ -f "$reg" ]
    before="$(shasum "$reg" | awk '{print $1}')"
    run bash "$SEED_SH"
    [ "$status" -eq 0 ]
    after="$(shasum "$reg" | awk '{print $1}')"
    [ "$before" = "$after" ]
}

@test "banner declares _contract:1 / collector seed_workarounds" {
    run bash "$SEED_SH"
    [ "$status" -eq 0 ]
    banner="$(printf '%s\n' "$output" | head -1)"
    [ "$(printf '%s' "$banner" | jq -r '._contract')" = "1" ]
    [ "$(printf '%s' "$banner" | jq -r '._collector')" = "seed_workarounds" ]
}

@test "a ref already in the registry is NOT proposed; an untracked ref IS" {
    run bash "$SEED_SH"
    [ "$status" -eq 0 ]
    refs="$(printf '%s\n' "$output" \
        | jq -r 'select(.kind=="workaround_proposal") | .issue_ref' | sort -u)"

    # mempalace#1322 is registered (workarounds.yaml) → must NOT appear.
    ! printf '%s\n' "$refs" | grep -qx 'mempalace#1322'
    ! printf '%s\n' "$refs" | grep -qx 'mempalace#1457'
    ! printf '%s\n' "$refs" | grep -qx 'chromadb#1092'

    # mempalace#1132 appears in CLAUDE.md, is NOT registered → must be proposed.
    printf '%s\n' "$refs" | grep -qx 'mempalace#1132'
}

@test "every proposal carries in_registry:false and a proposed_entry" {
    run bash "$SEED_SH"
    [ "$status" -eq 0 ]
    # All proposal records have in_registry=false.
    bad="$(printf '%s\n' "$output" \
        | jq -c 'select(.kind=="workaround_proposal" and .in_registry != false)' \
        | grep -c . || true)"
    [ "$bad" -eq 0 ]
    # At least one proposal exists, each with a non-empty proposed_entry.retire_when.
    n="$(printf '%s\n' "$output" \
        | jq -c 'select(.kind=="workaround_proposal" and (.proposed_entry.retire_when | length > 0))' \
        | grep -c . || true)"
    [ "$n" -gt 0 ]
}

@test "proposals are written to gitignored .omc, never to workarounds.yaml" {
    run bash "$SEED_SH"
    [ "$status" -eq 0 ]
    [ -f "$REPO_ROOT/.omc/skill-healer/proposals.yaml" ]
    git -C "$REPO_ROOT" check-ignore "$REPO_ROOT/.omc/skill-healer/proposals.yaml" >/dev/null
}
