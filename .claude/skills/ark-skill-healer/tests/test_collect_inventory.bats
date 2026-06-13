#!/usr/bin/env bats
# test_collect_inventory.bats — collect_inventory.sh contract + positive allowlist.

load helper

setup()    { healer_setup_tmp; }
teardown() { healer_teardown_tmp; }

@test "banner line declares _contract:1 and the collector name" {
    run bash "$INVENTORY_SH"
    [ "$status" -eq 0 ]
    banner="$(printf '%s\n' "$output" | head -1)"
    [ "$(printf '%s' "$banner" | jq -r '._contract')" = "1" ]
    [ "$(printf '%s' "$banner" | jq -r '._collector')" = "collect_inventory" ]
}

@test "EXACTLY the 7 allowlisted dep names — no more, no less (AC2)" {
    run bash "$INVENTORY_SH"
    [ "$status" -eq 0 ]
    names="$(json_lines "$output" | jq -r 'select(.kind=="inventory") | .name' | sort)"
    expected="$(printf '%s\n' \
        gstack superpowers mempalace-plugin mempalace-cli \
        oh-my-claudecode karpathy-skills obsidian-skills | sort)"
    [ "$names" = "$expected" ]
    # And exactly 7 inventory records.
    n="$(json_lines "$output" | jq -c 'select(.kind=="inventory")' | grep -c .)"
    [ "$n" -eq 7 ]
}

@test "gstack present with dep_type=binary (AC3/NIT-2 — proves the detector branch)" {
    run bash "$INVENTORY_SH"
    rec="$(json_lines "$output" | jq -c 'select(.kind=="inventory" and .name=="gstack")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.dep_type')" = "binary" ]
}

@test "mempalace is SPLIT into -plugin AND -cli (no bare 'mempalace')" {
    run bash "$INVENTORY_SH"
    names="$(json_lines "$output" | jq -r 'select(.kind=="inventory") | .name')"
    printf '%s\n' "$names" | grep -qx 'mempalace-plugin'
    printf '%s\n' "$names" | grep -qx 'mempalace-cli'
    # No bare "mempalace" record.
    ! printf '%s\n' "$names" | grep -qx 'mempalace'
}

@test "superpowers has commit_range_capable:false (NIT-1)" {
    run bash "$INVENTORY_SH"
    rec="$(json_lines "$output" | jq -c 'select(.kind=="inventory" and .name=="superpowers")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.commit_range_capable')" = "false" ]
}

@test "superpowers source_url is the upstream dev repo obra/superpowers (not the marketplace aggregator)" {
    run bash "$INVENTORY_SH"
    rec="$(json_lines "$output" | jq -c 'select(.kind=="inventory" and .name=="superpowers")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_url')" = "obra/superpowers" ]
}

@test "gstack source_url is garrytan/gstack (drives the binary-dep remote changelog tier)" {
    run bash "$INVENTORY_SH"
    rec="$(json_lines "$output" | jq -c 'select(.kind=="inventory" and .name=="gstack")')"
    [ -n "$rec" ]
    [ "$(printf '%s' "$rec" | jq -r '.source_url')" = "garrytan/gstack" ]
}

@test "NO chromadb standalone record (it is an annotation on mempalace-cli)" {
    run bash "$INVENTORY_SH"
    names="$(json_lines "$output" | jq -r 'select(.kind=="inventory") | .name')"
    ! printf '%s\n' "$names" | grep -qx 'chromadb'
    # chromadb survives only as an annotation string on mempalace-cli.
    ann="$(json_lines "$output" | jq -r 'select(.name=="mempalace-cli") | .annotations[]')"
    printf '%s' "$ann" | grep -qi 'chromadb'
}

@test "NO ark-skills self-record and NO unrelated installed plugins" {
    run bash "$INVENTORY_SH"
    names="$(json_lines "$output" | jq -r 'select(.kind=="inventory") | .name')"
    ! printf '%s\n' "$names" | grep -qx 'ark-skills'
    ! printf '%s\n' "$names" | grep -qx 'frontend-design'
    ! printf '%s\n' "$names" | grep -qx 'taches-cc-resources'
}
