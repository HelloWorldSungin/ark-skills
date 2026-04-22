#!/usr/bin/env bats
bats_require_minimum_version 1.5.0
# Integration tests for the continuous-checkpoint bash snippet added to Step 6.5
# in SKILL.md. See docs/superpowers/specs/2026-04-22-gstack-v1.5.1.0-integration.md
# § "Commit 2: wire continuous-checkpoint mode into Step 6.5 check-off".
#
# These tests duplicate the bash literally; when the SKILL.md snippet changes,
# update both. Shellcheck coverage lives at the SKILL.md source of truth.

setup() {
    TMPDIR=$(mktemp -d)
    export TMPDIR
    pushd "$TMPDIR" >/dev/null
    git init -q .
    git config user.email "test@ark-skills.test"
    git config user.name "ark-skills test"
    git commit --allow-empty -q -m "initial"

    mkdir -p .ark-workflow
    cat > .ark-workflow/current-chain.md <<'EOF'
---
scenario: migration
weight: medium
chain_id: FIXTUREWIP
proceed_past_level: null
---
# Current Chain: migration-medium
## Steps
- [x] 0. /ark-context-warmup — load context
- [x] 1. /investigate — audit refs
- [ ] 2. /test-driven-development — write tests
- [ ] 3. Implement — 4 atomic commits
## Notes
EOF

    STUB_BIN="$TMPDIR/fake-gstack-bin"
    mkdir -p "$STUB_BIN"
    export GSTACK_CONFIG="$STUB_BIN/gstack-config"
}

teardown() {
    popd >/dev/null
    rm -rf "$TMPDIR"
}

# Stub factory: writes a fake gstack-config that returns $1 for any `get <key>`.
# Pass "MISSING" to leave the stub absent (simulates gstack not installed).
# Pass "NONEXEC" to create a non-executable file (simulates broken install).
_make_stub() {
    case "$1" in
    MISSING) rm -f "$STUB_BIN/gstack-config" ;;
    NONEXEC)
        printf '#!/bin/sh\necho continuous\n' > "$STUB_BIN/gstack-config"
        chmod 644 "$STUB_BIN/gstack-config"
        ;;
    *)
        printf '#!/bin/sh\necho "%s"\n' "$1" > "$STUB_BIN/gstack-config"
        chmod 755 "$STUB_BIN/gstack-config"
        ;;
    esac
}

# Runs the continuous-checkpoint snippet literally. N is the just-completed
# step number (1-based count of checked lines). Must match the snippet in
# skills/ark-workflow/SKILL.md Step 6.5.
_run_snippet() {
    local N="$1"
    if [ -x "$GSTACK_CONFIG" ]; then
        CHECKPOINT_MODE=$("$GSTACK_CONFIG" get checkpoint_mode 2>/dev/null)
        if [ "$CHECKPOINT_MODE" = "continuous" ] && git rev-parse --git-dir >/dev/null 2>&1; then
            STEP_LABEL=$(awk -v n="$N" '/^- \[x\]/ { c++; if (c == n) { sub(/^- \[x\] [0-9]+\. /, ""); print; exit } }' .ark-workflow/current-chain.md)
            REMAINING_LABEL=$(awk '/^- \[ \]/ { sub(/^- \[ \] [0-9]+\. /, ""); print; exit }' .ark-workflow/current-chain.md)
            [ -z "$REMAINING_LABEL" ] && REMAINING_LABEL="chain complete"
            git commit --allow-empty -m "$(printf 'WIP: chain step %s done\n\n[gstack-context]\nDecisions: %s\nRemaining: %s\nSkill: /ark-workflow\n[/gstack-context]\n' "$N" "$STEP_LABEL" "$REMAINING_LABEL")" >/dev/null 2>&1 \
                || echo "warning: continuous-checkpoint commit skipped (commit failed; check-off still applied)" >&2
        fi
    fi
}

@test "continuous mode: drops WIP commit with schema-pinned body" {
    _make_stub "continuous"
    _run_snippet 2
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 2 ]
    subject=$(git log -1 --format=%s)
    body=$(git log -1 --format=%b)
    [[ "$subject" == "WIP: chain step 2 done" ]]
    [[ "$body" == *"[gstack-context]"* ]]
    [[ "$body" == *"Decisions: /investigate — audit refs"* ]]
    [[ "$body" == *"Remaining: /test-driven-development — write tests"* ]]
    [[ "$body" == *"Skill: /ark-workflow"* ]]
    [[ "$body" == *"[/gstack-context]"* ]]
}

@test "explicit mode: no WIP commit dropped" {
    _make_stub "explicit"
    _run_snippet 2
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}

@test "empty mode: no WIP commit dropped" {
    _make_stub ""
    _run_snippet 2
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}

@test "unexpected mode value: no WIP commit dropped" {
    _make_stub "garbage-mode"
    _run_snippet 2
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}

@test "gstack-config binary missing: silent no-op" {
    _make_stub MISSING
    run _run_snippet 2
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}

@test "gstack-config not executable: silent no-op" {
    _make_stub NONEXEC
    run _run_snippet 2
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}

@test "not in a git repo: silent no-op" {
    _make_stub "continuous"
    mkdir -p "$TMPDIR/no-git" && pushd "$TMPDIR/no-git" >/dev/null
    mkdir -p .ark-workflow
    cp "$TMPDIR/.ark-workflow/current-chain.md" .ark-workflow/
    run _run_snippet 2
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    popd >/dev/null
}

@test "last step checked: Remaining field renders 'chain complete'" {
    _make_stub "continuous"
    cat > .ark-workflow/current-chain.md <<'EOF'
---
scenario: migration
weight: medium
chain_id: FIXTUREFINAL
proceed_past_level: null
---
## Steps
- [x] 0. /ark-context-warmup — load context
- [x] 1. /investigate — audit refs
- [x] 2. /test-driven-development — write tests
- [x] 3. Implement — 4 atomic commits
## Notes
EOF
    _run_snippet 4
    body=$(git log -1 --format=%b)
    [[ "$body" == *"Remaining: chain complete"* ]]
}

@test "git commit failure: warn to stderr, do not abort" {
    _make_stub "continuous"
    # Install a pre-commit hook that always fails. Forces `git commit` to exit
    # non-zero, which should trigger the snippet's warn-and-continue branch.
    mkdir -p .git/hooks
    cat > .git/hooks/pre-commit <<'HOOK'
#!/bin/sh
exit 1
HOOK
    chmod 755 .git/hooks/pre-commit

    run -0 _run_snippet 2
    [[ "$stderr" == *"warning: continuous-checkpoint commit skipped"* ]] || \
        [[ "$output" == *"warning: continuous-checkpoint commit skipped"* ]]
    # Check-off is still applied at the Python-helper layer; the bash layer
    # must not have produced a WIP commit, so log stays at the initial commit.
    [ "$(git log --oneline | wc -l | tr -d ' ')" -eq 1 ]
}
