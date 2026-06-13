# Cascade — upstream fetch & diff (load-on-demand)

How `collect_upstream.sh` turns a dependency's last-seen snapshot into either a
finding or a quiet record. This is the AC5 linchpin: a no-change run must produce
**zero** non-quiet records.

## The cascade (primary signal = prose, R4)

Per dep, the collector walks ONLY the tiers in that dep's inventory `tiers[]`
field, **in order**, stopping at the **first tier that yields content**:

```
changelog  ──▶  release  ──▶  commit
 (richest)                    (coarsest)
```

All tiers track the dep's **upstream tip**, not the local checkout: the collector
runs a guarded `git fetch` per clone-backed dep up front, then the changelog and
commit tiers read the **remote-tracking ref** (e.g. `origin/develop`). So a finding
fires when the upstream repo moves ahead of the installed clone — even if the user
never pulled. Each tier falls back to the local working tree only when there is no
remote-tracking ref (the hermetic test fixture / a detached clone).

| tier | source | identity | offline? |
|------|--------|----------|----------|
| `changelog` | plugin deps: `CHANGELOG.md` at the **upstream ref** (`git show <origin/branch>:CHANGELOG.md`), local working-tree file as fallback. binary deps: **guarded remote** `gh api repos/<source_url>/contents/CHANGELOG.md` | `sha256` prose hash of the file text | **no** (guarded fetch; cached ref / local file on miss) |
| `release` | `gh release list -R <source_url> -L 5` → `gh release view <tag>` | `sha256` prose hash of the release-notes text | **no** (network, guarded) |
| `commit` | `git -C <clone> log <last>..<upstream-tip> --oneline` | **upstream-tip short SHA** (local HEAD fallback; not a prose hash) | **no** (guarded fetch; cached ref on miss) |

- Plugin deps read the changelog from the upstream ref after a guarded fetch,
  falling back to the local clone's working-tree file when no remote-tracking ref
  exists. **Binary/CLI deps (no clone)** run the changelog tier as a *guarded remote
  fetch* of the upstream repo's `CHANGELOG.md` — used when the dep ships a changelog
  but no GitHub releases (e.g. `gstack` → `garrytan/gstack`). All network paths are
  guarded exactly like the release tier (never hard-fail). python deps still have no
  changelog source.
- The `commit` tier runs **only** for deps with `commit_range_capable=true`.
- The up-front `git fetch` only updates `refs/remotes/*` (and downloads objects) —
  it never touches the working tree, HEAD, or local branches, so it is
  non-destructive to the user's plugin clones. `BatchMode`/`ConnectTimeout` keep an
  unreachable remote from hanging or prompting.
- A tier is "active" when its identity is **determinable**: changelog/release
  require non-empty text (the text IS the identity source); `commit` is active
  whenever an upstream-tip (or fallback HEAD) SHA exists — even when
  `git log <last>..<upstream-tip>` is **empty** (upstream unmoved), the SHA still
  anchors the tier.

## Per-tier hashing semantics

- **changelog / release** → `lib_state__hash <text>` = `sha256:<hex>` of the
  tier's full text. The hash IS the stored identity; the prose IS the
  `prose_delta`.
- **commit** → the stored identity is the **upstream-tip short SHA** (local HEAD
  when no remote-tracking ref), tier-invariant. Never hash commit prose — two
  different log windows over the same tip are the same identity.

## Decision tree (per dep, after the active tier is chosen)

```
no tier yielded content
  └─▶ quiet:no_change, source_tier:null            (nothing to compare)

per-dep cold start (no <dep>.json)
  └─▶ write baseline snapshot for the active tier
      quiet:baselined                              (no finding, first sighting)

active tier's stored identity == new identity
  └─▶ quiet:no_change                              (same tier, no movement)

active tier's stored identity is EMPTY,
AND a HIGHER tier was recorded last run (downgrade),
AND the active (lower) tier's own identity has not moved
  └─▶ quiet:evidence_coarsened                     (MF2 fix — NEVER a finding)
      (no snapshot write)

active tier's stored identity != new identity (same-tier movement)
  └─▶ NON-QUIET upstream_delta + write that tier's snapshot
```

### Why the tier-downgrade rule exists (MF2)

A single tier-blind hash would manufacture a false positive when last run reached
a rich tier (changelog) but this run only reached a coarse tier (commit) — the
hash "changed" merely because the evidence source changed. The fix: compare a
tier's identity ONLY against the **same tier's** stored identity. A pure downgrade
with no movement in the lower tier is `evidence_coarsened` — quiet, no finding,
**no snapshot write** (so the higher-tier baseline is preserved for next run).

Tier rank for downgrade detection: `changelog (2) > release (1) > commit (0)`.

## Evidence extraction (MF5 — verbatim only)

`evidence_refs[]` are pulled **verbatim** from the active tier's text. The
collector NEVER synthesizes a SHA, line, or issue number.

- **changelog / release**: issue refs mined from the text —
  - qualified `dep#NNN` (`mempalace#1457`, `chromadb#42`, `omc#99`, …) — as-is.
  - bare `#NNN` — emitted exactly as it appears; the dep prefix is **not**
    synthesized even though the dep is known (the SKILL.md layer qualifies in
    context).
  - GitHub `MemPalace/mempalace/(issues|pull)/NNNN` URLs → normalized to
    `mempalace#NNNN` (the URL path IS the verbatim reference).
  - POSIX ERE only (`grep -oE`) — portable to BSD `grep` (macOS `/usr/bin/grep`
    has no `-P` / lookbehind). The bare-ref pass uses an optional leading-letter
    capture (`[A-Za-z]?#[0-9]+`) filtered to `^#[0-9]+$` so the `#NNN` inside a
    qualified ref is not double-counted.
- **commit**: each verbatim `<short_sha> <subject>` line from
  `git log <last>..<upstream-tip> --oneline`. `commit_range` is set to
  `<last_short_sha>..<upstream_tip_short_sha>` when both are known, else null.

## gh auth / rate-limit / offline handling (network tiers)

The release tier (and the binary-dep remote changelog tier) are the network tiers
and are **guarded** — they never hard-fail the run. The binary remote-changelog
fetch applies the same guard chain (no source_url / no gh / unauthenticated /
network-or-404 → log `tier=changelog skipped: <name> <reason>` to **stderr** and
fall through returning empty text). For the release tier, on any of the following
it logs `tier=release skipped: <name> <reason>` to **stderr** and falls through to
the next tier (returning empty text):

- the dep has no `source_url` (e.g. `gstack`),
- `gh` is not installed,
- `gh auth status` fails (unauthenticated),
- `gh release list` fails (network / rate-limit),
- the repo has no published releases,
- the latest tag can't be parsed, or `gh release view` fails.

`gh release list` columns are TAB-separated `TITLE \t TYPE \t TAGNAME \t
PUBLISHED`; the tag passed to `gh release view` is column 3 (TAGNAME), not the
title.

The commit tier and the *plugin* changelog tier now run a guarded `git fetch` to
read the upstream ref; when the fetch fails (offline / SSH unreachable /
rate-limit) they fall back to the **cached** remote-tracking ref (last successful
fetch), and only to the local working tree when no remote-tracking ref exists at
all. The fetch is guarded — it logs `upstream fetch skipped: <name> <reason>` to
**stderr** and never hard-fails. A dep whose only viable tier is network —
`mempalace-cli` → release, or a binary dep like `gstack` → remote changelog —
simply yields `quiet:no_change`, `source_tier:null` when offline (the guard prints
empty and the cascade falls through) — never an error.

## Run manifest & resumability

`.omc/skill-healer/run-manifest.json`:

```json
{ "run_id": "<iso>", "deps_total": 7, "deps_done": ["…"], "status": "in_progress | complete" }
```

- On start: if the file exists with `status:in_progress`, **RESUME** — skip any
  dep already in `deps_done[]`. Otherwise initialize a fresh manifest.
- After each dep is processed, append its name to `deps_done[]` (transactional:
  write `…tmp` then atomic `mv`).
- When all deps are processed, set `status:complete`.

This makes a partial run resumable rather than mistaking the partial state for
"quiet". All writes (snapshots + manifest) land under the gitignored
`.omc/skill-healer/` — no run can dirty a tracked file (AC11).
