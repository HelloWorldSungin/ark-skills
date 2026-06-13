# ark-skill-healer — architecture (load-on-demand)

## What it is
The **upstream-facing mirror of `/ark-update`**. `/ark-update` converges
*downstream* projects to ark-skills' profile; `ark-skill-healer` watches the
*upstream* deps ark-skills integrates with and advises what ark-skills should
change. Distinct from `/ark-health` (read-only session-capability diagnostic).

Advisory-only, enforced **structurally**: the entire run-write surface is the
gitignored `.omc/skill-healer/`, so no run can dirty a tracked file (AC11).

## Lineage (accurate)
- `tests/` harness pattern borrowed from **ark-update** (`skills/ark-update/tests/test_e2e_shell.py`).
- `references/` load-on-demand pattern borrowed from **ark-health**.
Not a blanket "mirror ark-update."

## The 6 components
1. **Dependency Inventory** (`collect_inventory.sh`) — positive-allowlist of
   ark-skills-referenced deps with installed version/sha + per-dep source map.
2. **Upstream Fetch & Diff** (`collect_upstream.sh`) — per-tier cascade diff vs
   the last-seen snapshot.
3. **Impact Analysis** (SKILL.md judgment) — must-change findings + staged patches.
4. **Opportunity Discovery** (SKILL.md judgment) — could-improve findings.
5. **Output / Report** (SKILL.md render) — one ranked list, nothing dropped.
6. **Workaround Retirement** (`seed_workarounds.sh` + SKILL.md judgment) —
   registry cross-check, proposals only.

## The cascade (primary signal = prose, R4)
All clone-backed tiers track the **upstream tip**, not the local checkout: a
guarded `git fetch` runs per clone-backed dep up front, then the changelog and
commit tiers read the **remote-tracking ref** so a finding fires when upstream
moves ahead of the install (not only when the user pulls). Each falls back to the
local working tree when no remote-tracking ref exists. Per dep, in order, stopping
at the first tier that yields content:
1. **changelog** — `CHANGELOG.md` at the upstream ref
   (`git show <origin/branch>:CHANGELOG.md`; local clone file as fallback), or the
   dep's remote changelog/release source for clone-less CLI/binary deps.
2. **release** — `gh release ...` (network; guarded — on auth/rate-limit failure,
   log the skip and fall through).
3. **commit** — `git -C <clone> log <last_sha>..<upstream-tip> [-- <subtree_path>]`,
   guarded fetch (local HEAD fallback), anchored on the upstream-tip SHA. Only for
   `commit_range_capable` deps.

`source-map.md` declares each dep's available tiers (probe-confirmed).

## Per-tier snapshot lifecycle (AC5 linchpin)
- Snapshot is keyed **per tier** (see collector-contract §3).
- "changed" ⇔ the **same tier's** identity moved (prose hash for changelog/release;
  upstream-tip SHA for commit).
- **Tier downgrade with no lower-tier movement ⇒ `quiet, evidence_coarsened`**, not
  a finding. (Prevents the false positive a single tier-blind hash would manufacture.)
- **Per-dep cold-start**: absence of the dep's snapshot ⇒ baseline that dep, emit
  `quiet: baselined`, produce no finding.
- Writes are transactional (temp + atomic mv); a `run-manifest.json` makes a
  partial run resumable rather than mistaken for "quiet".

## Ranking (AC6 — nothing dropped)
- Every finding gets `impact (1–5)` × `confidence (0–1)`; the report is sorted
  descending by the product.
- **No top-N truncation.** Commit-tier findings get **down-weighted confidence**
  (coarse evidence) so they sink — they are never dropped.
- Each rendered finding cites a **verbatim** evidence ref (select/reorder only).

## Source-map authority
Every row in `source-map.md` is written from a **live `ls` / `git -C` probe** at
implementation time, never from memory. The consensus caught two memory-written
mappings (superpowers subtree, gstack allowlist) — hence this rule.
