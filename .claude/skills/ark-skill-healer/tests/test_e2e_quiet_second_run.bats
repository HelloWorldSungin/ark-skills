#!/usr/bin/env bats
# test_e2e_quiet_second_run.bats — AC11 + AC5 together. Mirrors the spirit of
# skills/ark-update/tests/test_e2e_shell.py: drive the full collector end-to-end
# via subprocess (no --dep filter), then assert the advisory-only invariant.
#
#   (a) The second full run is FULLY quiet (zero non-quiet records).
#   (b) The run produces NO new tracked-file modifications — its entire write
#       surface is the gitignored .omc/skill-healer/.

load helper

setup()    { healer_setup_tmp; }
teardown() { healer_teardown_tmp; }

@test "full cascade: second run is fully quiet (AC5 end-to-end)" {
    # Exercises the CASCADE quiet invariant end-to-end. Disable the independent,
    # network-derived install-lag signal so this assertion does not depend on
    # transient live upstream-PyPI drift (install-lag has its own dedicated tests).
    export SKILL_HEALER_DISABLE_INSTALL_LAG=1
    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]

    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]
    # (a) zero non-quiet records on the second run.
    nonquiet="$(count_deltas "$output" '.quiet == false')"
    [ "$nonquiet" -eq 0 ]
    # Banner still present and valid on the second run.
    banner="$(printf '%s\n' "$output" | head -1)"
    [ "$(printf '%s' "$banner" | jq -r '._contract')" = "1" ]
}

@test "advisory-only: full run adds NO new tracked-file modifications (AC11)" {
    # Snapshot the repo's tracked-file porcelain BEFORE the run (excluding the
    # untracked '??' lines, which include in-progress dev like these test files).
    before="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no)"

    run bash "$UPSTREAM_SH"
    [ "$status" -eq 0 ]

    after="$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no)"

    # No NEW tracked-file modification attributable to the run.
    [ "$before" = "$after" ]

    # The only write surface (.omc/skill-healer/run-manifest.json) is gitignored.
    [ -f "$REPO_ROOT/.omc/skill-healer/run-manifest.json" ]
    git -C "$REPO_ROOT" check-ignore "$REPO_ROOT/.omc/skill-healer/run-manifest.json" >/dev/null
}
