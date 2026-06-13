#!/usr/bin/env bash
# make_fixture_clone.sh — build a hermetic, deterministic git clone + a fixture
# inventory script for the tier-downgrade (MF2) test in test_collect_upstream.bats.
#
# Why a builder instead of a checked-in fixture: a real git work tree cannot be
# committed inside this repo (nested .git). So we synthesize one in a temp dir at
# test time. The clone has a single commit (commit tier reachable, head SHA
# deterministic within the run) and NO CHANGELOG.md (changelog tier yields empty),
# and the fixture inventory gives it no source_url (release tier skipped). The dep
# therefore can only reach the COMMIT tier — exactly what the downgrade test needs.
#
# Usage:  make_fixture_clone.sh <dest_dir>
#   Creates:
#     <dest_dir>/clone/            — git work tree, one commit
#     <dest_dir>/inventory.sh      — emits banner + one inventory record for 'fixdep'
#   Prints the clone's short HEAD sha to stdout.
set -euo pipefail

dest="$1"
clone="$dest/clone"
inv="$dest/inventory.sh"

mkdir -p "$clone"
git -C "$clone" init -q
git -C "$clone" config user.email "fixture@test.local"
git -C "$clone" config user.name  "fixture"
printf 'hermetic fixture\n' > "$clone/file.txt"
git -C "$clone" add .
git -C "$clone" commit -qm "fixture seed commit"
head_sha="$(git -C "$clone" rev-parse --short HEAD)"

cat > "$inv" <<EOF
#!/usr/bin/env bash
# Fixture inventory — emits the collect_inventory contract for a single dep that
# can ONLY reach the commit tier (no CHANGELOG.md, no source_url for release).
printf '%s\n' '{"_contract": 1, "_collector": "collect_inventory"}'
printf '%s\n' '{"kind":"inventory","name":"fixdep","dep_type":"plugin","source_url":"","subtree_path":null,"installed_version":null,"git_commit_sha":"$head_sha","install_path":"$clone","commit_range_capable":true,"tiers":["changelog","release","commit"],"annotations":[]}'
EOF
chmod +x "$inv"

printf '%s' "$head_sha"
