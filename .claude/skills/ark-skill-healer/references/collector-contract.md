# Collector Contract v1

The deterministic collector scripts emit **JSON Lines** (one JSON object per line)
on stdout. The SKILL.md LLM layer consumes these records. This contract is the
boundary between the two layers.

**Contract version: `1`.** Every collector prints a leading
`{"_contract": 1, "_collector": "<name>"}` banner line as its first line of
output. The SKILL.md workflow asserts `_contract == 1` before consuming.

---

## Cardinal rule — evidence integrity (MF5)

`evidence_refs[]` strings are emitted **verbatim** by collectors (a changelog
line, a release-note line, a commit subject + short SHA, or an issue ref like
`mempalace#1457`). The SKILL.md render step may **select and reorder** evidence
refs; it must **never synthesize, paraphrase, or invent** a SHA / line / issue
number. A finding with no collector-emitted evidence ref is rendered with
`evidence: none` — never with a fabricated citation.

---

## Record shapes

### 1. inventory record — `collect_inventory.sh`

```json
{
  "kind": "inventory",
  "name": "mempalace-cli",
  "dep_type": "plugin | python | binary",
  "source_url": "MemPalace/mempalace",
  "subtree_path": null,
  "installed_version": "3.3.5",
  "git_commit_sha": null,
  "install_path": "/Users/.../bin/mempalace",
  "commit_range_capable": false,
  "tiers": ["changelog", "release"],
  "annotations": ["chromadb is a transitive pin of this dep (>=? per CLAUDE.md)"]
}
```

- `commit_range_capable`: true only when a local git clone exists to `git log` against.
- `tiers`: the ordered cascade this dep supports (subset of `changelog`, `release`, `commit`).
- `subtree_path`: non-null only for deps whose source is a subtree of a larger clone
  (none in v1 — superpowers is changelog/release-only, see source-map.md).
- `annotations`: free-text notes (e.g. chromadb transitive-pin annotation on `mempalace-cli`).

### 2. upstream-delta record — `collect_upstream.sh`

```json
{
  "kind": "upstream_delta",
  "name": "mempalace-cli",
  "source_tier": "changelog | release | commit",
  "quiet": false,
  "quiet_reason": null,
  "prose_delta": "…the new/changed text since last-seen…",
  "evidence_refs": ["mempalace#1457", "3.3.5 — quarantine_stale_hnsw wired into chromadb open path"],
  "commit_range": null
}
```

- `quiet: true` + `quiet_reason: "no_change" | "evidence_coarsened" | "baselined"`
  means NO finding should be produced for this dep this run.
- `evidence_coarsened` is emitted on a **tier downgrade with no movement in the
  lower tier's own hash** (e.g. changelog last run → commit this run, same SHA range).
- `baselined` is emitted on per-dep cold-start (first time this dep is seen).
- `commit_range`: `"<short_sha>..<short_sha>"` when `source_tier == commit`, else null.

### 3. snapshot record — `lib_state.sh` (persisted, not stdout)

Stored at `.omc/skill-healer/state/last-seen/<dep>.json`, keyed **per tier**:

```json
{
  "dep": "mempalace-cli",
  "tiers": {
    "changelog": { "content_hash": "sha256:…", "captured_at": "<iso>" },
    "release":   { "content_hash": "sha256:…", "captured_at": "<iso>" },
    "commit":    { "head_sha": "818b7f4", "captured_at": "<iso>" }
  }
}
```

- The `commit` tier identity is the **upstream-tip short SHA** (local HEAD when the
  clone has no remote-tracking ref), tier-invariant, not a prose hash. The snapshot
  key stays `head_sha` for back-compat.
- A tier is "changed" only when **that same tier's** identity moves.
- Writes are transactional: write `…/<dep>.json.tmp` then atomic `mv` into place.
- Cold-start is **per-dep**: absence of `<dep>.json` ⇒ baseline this dep only.

### 4. workaround-seed / proposal record — `seed_workarounds.sh`

```json
{
  "kind": "workaround_proposal",
  "dep": "mempalace-cli",
  "issue_ref": "mempalace#1502",
  "found_in": "CHANGELOG.md:42",
  "in_registry": false,
  "proposed_entry": { "description": "…", "upstream_issue_ref": "mempalace#1502", "carrier_file": "…", "retire_when": "…" }
}
```

- `in_registry: false` ⇒ this is a **proposal** for a human to add. The collector
  NEVER writes `references/workarounds.yaml`. Proposals go to stdout and
  `.omc/skill-healer/proposals.yaml`.

---

## Run manifest — `.omc/skill-healer/run-manifest.json`

Advanced after each dep is processed, for resumability:

```json
{ "run_id": "<iso>", "deps_total": 8, "deps_done": ["gstack", "superpowers"], "status": "in_progress | complete" }
```

A re-run that finds `status: in_progress` resumes the remaining deps rather than
treating the partial state as "quiet".
