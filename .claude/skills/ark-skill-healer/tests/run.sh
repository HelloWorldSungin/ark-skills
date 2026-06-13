#!/usr/bin/env bash
# run.sh — execute the ark-skill-healer hermetic test suite (bats).
#
# Every test uses a temp SKILL_HEALER_STATE_DIR (mktemp -d) and NEVER touches the
# real .omc/skill-healer/state. Run from anywhere:
#     bash .claude/skills/ark-skill-healer/tests/run.sh
set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v bats >/dev/null 2>&1; then
    echo "bats not found. Install with: brew install bats-core" >&2
    exit 127
fi

exec bats "$TESTS_DIR"/*.bats
