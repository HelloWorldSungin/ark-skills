#!/usr/bin/env bats

setup() {
    export TMPDIR_TEST="$(mktemp -d)"
    cp -R "${BATS_TEST_DIRNAME}/../fixtures/mixed/" "${TMPDIR_TEST}/repo"
    cd "${TMPDIR_TEST}/repo"
    mkdir -p vault/Architecture vault/Compiled-Insights vault/Staging \
             vault/Troubleshooting vault/Session-Logs vault/TaskNotes/Tasks/Bug
    cat > vault/Session-Logs/S001-test.md <<'EOF'
---
title: Session 1
session: S001
type: session-log
created: 2026-04-20
---

## Issues & Discoveries

EOF
}

teardown() {
    rm -rf "$TMPDIR_TEST"
}

_run() {
    python3 "${BATS_TEST_DIRNAME}/../cli_promote.py" \
        --repo-root "$(pwd)" --omc-wiki-dir ".omc/wiki" \
        --project-docs-path "$(pwd)/vault" \
        --tasknotes-path "$(pwd)/vault/TaskNotes" \
        --task-prefix "Arktest-" --session-slug "S001-test"
}

@test "e2e: arch-high promotes; OMC source deleted after index regen" {
    run _run
    [ "$status" -eq 0 ]
    [ -f vault/Architecture/arch-high.md ]
    [ ! -f .omc/wiki/arch-high.md ]
    grep -q "JWT" vault/Architecture/arch-high.md
}

@test "e2e: medium-conf stages + creates TaskNote non-interactively" {
    run _run
    [ -f vault/Staging/pattern-medium.md ]
    ls vault/TaskNotes/Tasks/Bug/*.md | xargs grep -l "Review staged wiki"
}

@test "e2e: debugging pattern dual-writes Troubleshooting + session log" {
    run _run
    grep -q "JWT Refresh Race" vault/Session-Logs/S001-test.md
    ls vault/Troubleshooting/*.md >/dev/null
    grep -rq "compiled-insight" vault/Troubleshooting/
}

@test "e2e: failed vault write preserves OMC source" {
    chmod a-w vault/Architecture
    run _run
    [ -f .omc/wiki/arch-high.md ]
    chmod u+w vault/Architecture
}

@test "e2e: no .omc/wiki/ → silent no-op, exit 0" {
    rm -rf .omc
    run _run
    [ "$status" -eq 0 ]
}

@test "e2e: source-warmup untouched (seed_body_hash matches) is skipped" {
    python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, '${BATS_TEST_DIRNAME}/../../../shared/python')
from omc_page import parse_page, body_hash, write_page
path = Path('.omc/wiki/source-warmup-untouched.md')
page = parse_page(path)
page.frontmatter['seed_body_hash'] = body_hash(page.body)
write_page(path, page)
"
    run _run
    # Source preserved because it's untouched (re-derivable from vault)
    [ -f .omc/wiki/source-warmup-untouched.md ]
}
