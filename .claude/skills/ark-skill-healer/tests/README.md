# ark-skill-healer — test harness (Phase 5)

Hermetic test suite for the Phase-2 collector scripts under `../scripts/`.

## Framework

**bats** (`bats-core`). Chosen because bats is the house tool and is installed
(`command -v bats`), and the scripts under test are POSIX/bash — bats exercises
them as real subprocesses against their true stdout/JSONL contract. (The sibling
`skills/ark-update/tests/` uses pytest because it tests a Python `migrate.py`;
here the units are shell scripts, so bats is the natural fit.)

## Running

```bash
bash .claude/skills/ark-skill-healer/tests/run.sh
# or directly:
bats .claude/skills/ark-skill-healer/tests/*.bats
```

Install bats if missing: `brew install bats-core`.

## Hermeticity (CRITICAL)

Every test sets a temp `SKILL_HEALER_STATE_DIR` via `mktemp -d` (in
`helper.bash::healer_setup_tmp`) and removes it in `teardown`. The suite **never**
reads or writes the real `.omc/skill-healer/state/last-seen`. Verified: the real
state dir's file mtimes are unchanged across a full suite run.

The only repo-relative write the collectors make that a test triggers is the
gitignored `.omc/skill-healer/run-manifest.json` (and `proposals.yaml`) — both are
`.gitignore`d, so the AC11 advisory-only test confirms zero **tracked**-file
modifications.

## Files

| File | Covers |
|------|--------|
| `test_collect_inventory.bats` | banner `_contract:1`; EXACTLY 7 allowlisted deps (AC2); gstack `dep_type=binary` (AC3/NIT-2); mempalace SPLIT into `-plugin`+`-cli`; superpowers `commit_range_capable:false` (NIT-1); NO chromadb/ark-skills/frontend-design/taches records |
| `test_lib_state.bats` | per-dep cold-start; per-tier merge preserves siblings; no `.tmp` leftover (atomic write); commit→`head_sha`, changelog→`content_hash` `sha256:` |
| `test_collect_upstream.bats` | AC5 quiet-second-run linchpin; **MF2 tier-downgrade** → `quiet:true`/`evidence_coarsened` (fixture); forced changelog change → `quiet:false`+`source_tier`+non-empty `evidence_refs` (AC4/AC7); forced commit change → `commit_range` |
| `test_seed_workarounds.bats` | registry shasum unchanged (read-only); registered refs NOT proposed, untracked ref IS; proposals to gitignored `.omc` only |
| `test_e2e_quiet_second_run.bats` | full cascade twice end-to-end: second run fully quiet (AC5) + no new tracked-file mods (AC11) |
| `helper.bash` | path resolution, temp-state setup/teardown, `json_lines`/`count_deltas` helpers |
| `fixtures/make_fixture_clone.sh` | builds the hermetic fixture for the tier-downgrade test |

## Fixtures

### `fixtures/make_fixture_clone.sh`

The MF2 tier-downgrade test needs a dep that can **only** reach the commit tier,
with a stored snapshot showing a richer (changelog) tier was seen before. Live
clones can't reliably reproduce a true downgrade, so this builder synthesizes a
deterministic fixture at test time:

- A throwaway git work tree with a single commit (commit tier reachable; a real
  HEAD SHA). A live git repo can't be committed inside this repo (nested `.git`),
  hence a builder rather than a checked-in directory.
- A **fixture inventory script** emitting one `inventory` record for dep `fixdep`
  with `tiers:[changelog,release,commit]`, no `CHANGELOG.md` in the clone
  (changelog tier yields empty), and empty `source_url` (release tier skipped).

The fixture inventory is injected via the `SKILL_HEALER_INVENTORY_SCRIPT` env
override on `collect_upstream.sh`. The test pre-seeds the temp state with a stored
`changelog` identity (higher tier) and NO `commit` identity, then runs the
cascade: it can only reach `commit`, a higher tier was recorded, and the commit
tier's own identity was never stored → `quiet:true`, `quiet_reason:"evidence_coarsened"`.

## Script change made for testability

`collect_upstream.sh` gained one surgical test-seam: the inventory source is now
`${SKILL_HEALER_INVENTORY_SCRIPT:-$SCRIPT_DIR/collect_inventory.sh}` (was a hard
path). This is an env-gated override with no behavior change in production (the
default is identical). It exists solely so the tier-downgrade test can feed a
hermetic fixture inventory. No collector logic was modified.
