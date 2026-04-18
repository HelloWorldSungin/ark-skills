#!/usr/bin/env bats

setup() {
    TMPDIR=$(mktemp -d)
    export TMPDIR
    SCRIPT="skills/ark-workflow/scripts/context_probe.py"
    FIXTURES="skills/ark-workflow/scripts/fixtures/context-probe"
    CHAIN_FIXTURES="skills/ark-workflow/scripts/fixtures/chain-files"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "raw mode: ok fixture prints level=ok" {
    run python3 "$SCRIPT" --format raw --state-path "$FIXTURES/ok-fresh.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *'"level": "ok"'* ]]
}

@test "step-boundary mode: ok fixture is silent" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/ok-fresh.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "step-boundary mode: nudge fixture renders mid-chain menu" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Context at 28%"* ]]
    [[ "$output" == *"Resuming bugfix chain (medium)"* ]]
    [[ "$output" == *"[a/b/c/proceed]"* ]]
}

@test "step-boundary mode: zero-completed renders entry menu" {
    cp "$CHAIN_FIXTURES/entry-0of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"before chain has started"* ]]
    [[ "$output" == *"(a) /compact — unavailable"* ]]
    [[ "$output" == *"[b/c/proceed]"* ]]
}

@test "step-boundary mode: nudge with proceed_past_level=nudge is silent" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "step-boundary mode: strong fires even when proceed_past_level=nudge" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/strong-low.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"attention-rot zone"* ]]
}

@test "path-b-acceptance: nudge prints one-line warning" {
    run python3 "$SCRIPT" --format path-b-acceptance \
        --state-path "$FIXTURES/nudge-mid.json"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Context at 28%"* ]]
    [[ "$output" == *"Path B"* ]]
}

@test "path-b-acceptance: ok is silent" {
    run python3 "$SCRIPT" --format path-b-acceptance \
        --state-path "$FIXTURES/ok-fresh.json"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "record-proceed at nudge writes proceed_past_level: nudge" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"
}

@test "record-proceed at strong leaves proceed_past_level: null" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/strong-low.json" \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"
}

@test "record-reset clears proceed_past_level back to null" {
    sed 's/proceed_past_level: null/proceed_past_level: nudge/' \
        "$CHAIN_FIXTURES/midchain-2of4.md" > "$TMPDIR/current-chain.md"
    python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"
    ! grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"
}

@test "end-to-end reset lifecycle: nudge -> proceed -> reset -> menu fires again" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"

    # 1. Record-proceed at nudge => proceed_past_level: nudge
    python3 "$SCRIPT" --format record-proceed \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: nudge" "$TMPDIR/current-chain.md"

    # 2. Step-boundary at nudge => suppressed (empty output)
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [ -z "$output" ]

    # 3. Record-reset
    python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    grep -q "proceed_past_level: null" "$TMPDIR/current-chain.md"

    # 4. Step-boundary at nudge => menu fires again
    run python3 "$SCRIPT" --format step-boundary \
        --state-path "$FIXTURES/nudge-mid.json" \
        --chain-path "$TMPDIR/current-chain.md"
    [[ "$output" == *"Context at 28%"* ]]
}

@test "atomic write stress: concurrent check-off + record-proceed never corrupts" {
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"

    # Background loop: rapid check-off / reset cycles for ~2 seconds
    (
        end=$(($(date +%s) + 2))
        while [ "$(date +%s)" -lt "$end" ]; do
            python3 "$SCRIPT" --format check-off --step-index 3 \
                --chain-path "$TMPDIR/current-chain.md"
        done
    ) &
    bg_pid=$!

    # Foreground loop: rapid frontmatter mutations
    end=$(($(date +%s) + 2))
    while [ "$(date +%s)" -lt "$end" ]; do
        python3 "$SCRIPT" --format record-proceed \
            --state-path "$FIXTURES/nudge-mid.json" \
            --chain-path "$TMPDIR/current-chain.md"
        python3 "$SCRIPT" --format record-reset \
            --chain-path "$TMPDIR/current-chain.md"
    done

    wait $bg_pid

    # Final state must still be valid: opens with frontmatter delimiter, has "## Steps".
    head -1 "$TMPDIR/current-chain.md" | grep -q "^---$"
    grep -q "^## Steps$" "$TMPDIR/current-chain.md"
    # proceed_past_level must be in a valid terminal state (null OR nudge — never garbage).
    # Tight regex catches torn writes like "proceed_past_level: nuxxxx".
    [ "$(grep -Ec '^proceed_past_level: (null|nudge)$' "$TMPDIR/current-chain.md")" -eq 1 ]
    # Step 3 was the check-off target — must end checked.
    grep -q "^- \[x\] /ark-code-review$" "$TMPDIR/current-chain.md"
}

@test "all six modes exit 0 on missing state file" {
    for fmt in raw step-boundary path-b-acceptance record-proceed; do
        run python3 "$SCRIPT" --format "$fmt" \
            --state-path "$TMPDIR/nope.json" \
            --chain-path "$TMPDIR/current-chain.md"
        [ "$status" -eq 0 ]
    done
    cp "$CHAIN_FIXTURES/midchain-2of4.md" "$TMPDIR/current-chain.md"
    run python3 "$SCRIPT" --format record-reset \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
    run python3 "$SCRIPT" --format check-off --step-index 1 \
        --chain-path "$TMPDIR/current-chain.md"
    [ "$status" -eq 0 ]
}
