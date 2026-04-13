#!/usr/bin/env bats

setup() {
    TMPDIR=$(mktemp -d)
    export TMPDIR
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "all backends unavailable → all three probes return false" {
    run python3 -c "
import sys
sys.path.insert(0, 'skills/ark-context-warmup/scripts')
import availability
from pathlib import Path
r = availability.probe(
    project_repo=Path('$TMPDIR'),
    vault_path=Path('$TMPDIR/nope'),
    tasknotes_path=Path('$TMPDIR/nope'),
    task_prefix='X-',
    notebooklm_cli_path=None,
)
print(r['notebooklm'], r['wiki'], r['tasknotes'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"False False False"* ]]
}

@test "multi-notebook config without default_for_warmup → notebooklm skipped with clear reason" {
    mkdir -p "$TMPDIR/.notebooklm"
    echo '{"notebooks": {"main": {"id": "a"}, "infra": {"id": "b"}}}' > "$TMPDIR/.notebooklm/config.json"
    run python3 -c "
import sys
sys.path.insert(0, 'skills/ark-context-warmup/scripts')
import availability
from pathlib import Path
r = availability.probe(
    project_repo=Path('$TMPDIR'),
    vault_path=Path('$TMPDIR/nope'),
    tasknotes_path=Path('$TMPDIR/nope'),
    task_prefix='X-',
    notebooklm_cli_path='/usr/bin/echo',
)
print(r['notebooklm'])
print(r['notebooklm_skip_reason'])
"
    [ "$status" -eq 0 ]
    [[ "$output" == *"False"* ]]
    [[ "$output" == *"default_for_warmup"* ]]
}
