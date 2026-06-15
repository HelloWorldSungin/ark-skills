# Source Map — dependency inventory (ground truth)

Every row written from a live `ls` / `git -C` probe on 2026-06-05 — never from
memory. Re-probe before trusting.

`collect_inventory.sh` reads installed values (versions, SHAs, paths) live and
gates emission on the positive allowlist documented in that script's header. This
table is the authoritative dep set: exactly these 8 rows. `ark-skills` (self) is
excluded — it IS the project being healed. `chromadb` is excluded — it is a
transitive-pin annotation on `mempalace-cli`, not an independent cascade target.

| name | dep_type | source_url | clone path | commit_range_capable | tiers |
|------|----------|-----------|-----------|----------------------|-------|
| gstack | binary | garrytan/gstack | `~/.gstack/config.yaml` (detector) | false | changelog (remote), release |
| superpowers | plugin | obra/superpowers | `~/.claude/plugins/marketplaces/claude-plugins-official` | false | changelog, release |
| mempalace-plugin | plugin | milla-jovovich/mempalace | `~/.claude/plugins/marketplaces/mempalace` | true | changelog, release, commit |
| mempalace-cli | python | MemPalace/mempalace | _(PyPI — `~/.local/bin/mempalace`)_ | false | changelog, release |
| oh-my-claudecode | plugin | Yeachan-Heo/oh-my-claudecode | `~/.claude/plugins/marketplaces/omc` | true | changelog, release, commit |
| karpathy-skills | plugin | forrestchang/andrej-karpathy-skills | `~/.claude/plugins/marketplaces/karpathy-skills` | true | changelog, release, commit |
| obsidian-skills | plugin | kepano/obsidian-skills | `~/.claude/plugins/marketplaces/obsidian-skills` | true | changelog, release, commit |
| graphify | python | safishamsi/graphify | _(PyPI — `command -v graphify`)_ | false | changelog, release |

## Probe notes (2026-06-05)

- **gstack** — branch (c) of the allowlist (NIT-2): ABSENT from
  `known_marketplaces.json`, so it needs an explicit detector. Detected via
  `~/.gstack/config.yaml` + `~/.gstack/.last-setup-version` (version read from
  the file; live value at probe time was `1.42.1.0`). No marketplace clone, so the
  changelog tier has no LOCAL source. **Re-probe 2026-06-05:** the public upstream
  repo is `garrytan/gstack` (confirmed via `gh search repos gstack`); it publishes
  **NO GitHub releases and NO tags** (`gh release list` / `gh api …/tags` both
  empty), so the release tier stays dead — but it DOES ship a root `CHANGELOG.md`
  (`gh api repos/garrytan/gstack/contents/CHANGELOG.md` → 838 KB). `source_url` is
  therefore set to `garrytan/gstack` and the changelog tier runs as a **guarded
  REMOTE fetch** (binary-dep path in `collect_upstream.sh`), keeping
  `commit_range_capable=false`, tiers `[changelog (remote), release]`.
- **superpowers** — NIT-1: the `claude-plugins-official` clone is NOT a git repo
  (`git -C … rev-parse --is-inside-work-tree` → exit 128) and has NO `superpowers`
  subtree (only `LICENSE` / `README` / `external_plugins` / `plugins`). Therefore
  `commit_range_capable=false`, `subtree_path=null`, and NO commit (subtree
  git-log) tier — changelog/release-only. **Re-probe 2026-06-05:** `source_url`
  corrected from the `claude-plugins-official` marketplace aggregator (which
  publishes NO releases, the cause of the prior `no_change` degrade) to the upstream
  dev repo `obra/superpowers` — read live from the installed plugin's own
  `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/.claude-plugin/plugin.json`
  `repository` field. `obra/superpowers` publishes releases (`v5.1.0` latest,
  2026-05-04; `v5.0.7`, `v5.0.6`, …), so the release tier now resolves. (No root
  `CHANGELOG.md` there — 404 — but `RELEASE-NOTES.md` exists; the local-clone
  changelog tier stays empty and falls through to release.)
- **mempalace-plugin** — git clone, HEAD `818b7f4` at probe time.
  ⚠️ **FORK-AHEAD-OF-PYPI GUARDRAIL (S015 lesson).** `milla-jovovich/mempalace` is
  a *plugin fork* whose `CHANGELOG.md` runs **ahead of the PyPI package**: it
  carried a `3.3.6` header while PyPI's latest published `mempalace` was still
  `3.3.5`. Its changelog/version headers are **NOT authoritative releases.** Any
  finding sourced from this dep's changelog tier that claims a version or a fix is
  shipped MUST be treated as fork-only and cross-checked against **mempalace-cli**
  (PyPI release tier) before driving any pin-bump or workaround-retire. In S015,
  treating a fork `3.3.6` header as a release caused a wrong floor-bump + a wrong
  `#1457` workaround-retire that had to be reverted. Pin/version/workaround
  authority lives ONLY on `mempalace-cli`.
- **mempalace-cli** — PyPI install (`mempalace --version` → `MemPalace 3.3.5`,
  pin `>=3.3.5`). The #1457 / #976 / #1322 workaround logic anchors on THIS
  record — it is the **single source of version/pin/workaround authority** for
  mempalace (see the mempalace-plugin guardrail above). `chromadb 1.5.7` is carried
  as an annotation here (M2/NIT-2), not a standalone record.
- **oh-my-claudecode** — marketplace key `omc`; git clone, HEAD `3e945671` at
  probe time. `source_url` is the ground-truth `Yeachan-Heo/oh-my-claudecode`
  (the marketplace entry's `source.source` is `git`, with no `repo` field).
- **karpathy-skills** — git clone, HEAD `2c60614` at probe time.
- **obsidian-skills** — git clone, HEAD `fa1e131` at probe time.
