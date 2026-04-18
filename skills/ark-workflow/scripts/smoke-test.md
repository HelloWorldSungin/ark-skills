# Manual smoke test: context_probe.py

Use this when you want a hands-on sanity check that the probe surfaces the
mitigation menu, suppresses correctly, and resets cleanly.

## Setup

```bash
TMPSTATE=$(mktemp -d)
TMPCHAIN=$(mktemp -d)
cp skills/ark-workflow/scripts/fixtures/chain-files/midchain-2of4.md \
   "$TMPCHAIN/current-chain.md"
```

## 1. Manually craft a "≥35% strong" cache

```bash
cat > "$TMPSTATE/hud-stdin-cache.json" <<EOF
{
  "session_id": "smoke-session",
  "cwd": "$(pwd)",
  "workspace": {"current_dir": "$(pwd)"},
  "context_window": {
    "used_percentage": 42,
    "current_usage": {
      "input_tokens": 6,
      "output_tokens": 200,
      "cache_creation_input_tokens": 5000,
      "cache_read_input_tokens": 415000
    },
    "context_window_size": 1000000
  }
}
EOF
```

## 2. Step-boundary probe should render the strong-level menu

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected:
- Header includes `Context at 42%` and `attention-rot zone`.
- Forward brief shows `Resuming bugfix chain (medium)` with the right Completed / Next / Remaining lists.
- Three options shown; answer prompt is `[a/b/c/proceed]`.

## 3. Record-proceed at strong should NOT silence anything

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-proceed \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md"

grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: null` (strong never persists suppression).

## 4. Lower the cache to nudge, record proceed, verify suppression

```bash
sed -i.bak 's/"used_percentage": 42/"used_percentage": 24/' \
  "$TMPSTATE/hud-stdin-cache.json"
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-proceed \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md"
grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: nudge`.

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected: empty output (suppressed).

## 5. Bump back to strong, verify menu fires regardless

```bash
sed -i.bak 's/"used_percentage": 24/"used_percentage": 42/' \
  "$TMPSTATE/hud-stdin-cache.json"
python3 skills/ark-workflow/scripts/context_probe.py \
  --format step-boundary \
  --state-path "$TMPSTATE/hud-stdin-cache.json" \
  --chain-path "$TMPCHAIN/current-chain.md" \
  --expected-cwd "$(pwd)"
```

Expected: strong-level menu prints (suppression doesn't apply at strong).

## 6. Reset clears suppression

```bash
python3 skills/ark-workflow/scripts/context_probe.py \
  --format record-reset \
  --chain-path "$TMPCHAIN/current-chain.md"
grep "proceed_past_level" "$TMPCHAIN/current-chain.md"
```

Expected: `proceed_past_level: null`.

## Cleanup

```bash
rm -rf "$TMPSTATE" "$TMPCHAIN"
```

## Notes

- If `bats` is not installed locally, this manual runbook substitutes for the
  integration suite at `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats`.
  Install via `brew install bats-core` to run the automated tests.
- The probe degrades silently when `HAS_OMC=false` (Step 6.5 doesn't invoke it
  in that case). To simulate that path, just don't run the probe.
