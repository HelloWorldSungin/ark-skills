#!/usr/bin/env bash
# MCP concurrency probe. Validates spec decision D4.
#
# Runs N parallel obsidian CLI reads against the same vault. If all succeed with
# no ClosedResourceError / connection errors, the vault-local lane *could* be
# parallelized. Current default per D4 is serialized regardless.
#
# This script is informational — used in CI to track whether the assumption
# is still warranted. Exit 0 = all parallel reads succeeded. Exit non-zero =
# at least one failure (serialized remains correct).
#
# Usage: mcp_concurrency_probe.sh <vault_path> <file_to_read> [<parallel_N>]

set -uo pipefail

VAULT="${1:-}"
FILE="${2:-}"
N="${3:-10}"

if [ -z "$VAULT" ] || [ -z "$FILE" ]; then
    echo "usage: $0 <vault_path> <file_to_read> [<parallel_N>]" >&2
    exit 2
fi

if ! command -v obsidian >/dev/null 2>&1; then
    echo "obsidian CLI not on PATH — probe cannot run" >&2
    exit 3
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Launch N parallel reads, collect exit codes
PIDS=()
for i in $(seq 1 "$N"); do
    ( obsidian read file="$FILE" >"$TMP/out.$i" 2>"$TMP/err.$i"; echo $? >"$TMP/exit.$i" ) &
    PIDS+=($!)
done

for pid in "${PIDS[@]}"; do wait "$pid"; done

FAIL_COUNT=0
for i in $(seq 1 "$N"); do
    code=$(cat "$TMP/exit.$i" 2>/dev/null || echo "unknown")
    if [ "$code" != "0" ]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "probe $i: exit=$code, stderr: $(head -c 200 "$TMP/err.$i")" >&2
    fi
done

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "probe: $N/$N parallel reads succeeded — MCP appears concurrency-safe for reads"
    exit 0
else
    echo "probe: $FAIL_COUNT/$N failures — keep serialized per D4" >&2
    exit 1
fi
