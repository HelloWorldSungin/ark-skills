---
title: "Session 15: /ark-skill-healer first real run — gstack upgrade, mempalace fork-vs-PyPI correction, MarkItDown ingest"
type: session-log
tags:
  - session-log
  - S015
  - ark-skill-healer
  - mempalace
  - gstack
  - upstream-watch
  - data-ingest
summary: "First real /ark-skill-healer advisory run. Upgraded gstack 1.42.1.0→1.56.0.0. Caught a fork-vs-PyPI error: mempalace #1457 closed via #1461 but NOT on PyPI (latest 3.3.5) — reverted a wrong floor-bump + workaround-retire. Wired MarkItDown office-doc front-end into ingest skills."
session: "S015"
status: complete
date: 2026-06-05
prev: "[[S014-MemPalace-v3-3-4-Upgrade-Mutex-Retirement]]"
epic: ""
source-tasks: []
created: 2026-06-05
last-updated: 2026-06-05
---

# Session 15: /ark-skill-healer first real run — gstack upgrade, mempalace fork-vs-PyPI correction, MarkItDown ingest

## Objective
Run `/ark-skill-healer` (the upstream-dependency advisory skill) for the first time against the live dep set, then act on the findings the user selected.

## Context
Follows S014 (mempalace v3.3.4 upgrade + mutex retirement). The `ark-skill-healer` skill lives untracked at `.claude/skills/ark-skill-healer/`. This was its first real advisory pass over all 7 inventoried deps.

## Work Done

### 1. /ark-skill-healer advisory pass
- 7 deps inventoried; 2 non-quiet: **mempalace-plugin** (changelog tier showed 3.3.6) and **obsidian-skills** (commit tier, install `fa1e131` 4 commits behind upstream `553ef99`). 5 quiet (gstack, superpowers, mempalace-cli, oh-my-claudecode, karpathy-skills).
- AC11 held: all run-writes confined to gitignored `.omc/skill-healer/`.

### 2. gstack upgrade 1.42.1.0 → 1.56.0.0
- Ran `/gstack-upgrade` (global-git install at `~/.claude/skills/gstack`, HEAD now `cab774c`). 22 releases; no migrations; setup exit 0.
- **Methodology gap found:** gstack reported `quiet: no_change` while being 22 releases behind. The changelog tier compares upstream-now vs upstream-last-seen (prose hash) — it never compares the *installed version* against upstream. Clone-backed deps catch install-lag via the commit tier; clone-less **binary** deps (gstack) have no such comparison. Staged a fix note: `.omc/skill-healer/staged-patches/SKILL-binary-install-lag.note.md`.

### 3. mempalace #1457 — fork-vs-PyPI correction (the key finding)
- Advisory initially claimed mempalace 3.3.6 "fixes #1457" (changelog-verbatim) and `gh` confirmed #1457 **CLOSED 2026-05-14** via merged PRs #1461/#1452. Applied a CLAUDE.md floor-bump (v3.3.5+→v3.3.6+) and removed the `mempalace#1457` workaround entry.
- **User asked to actually upgrade the CLI — which exposed the error:** `pipx` reports mempalace already at latest **3.3.5**. Direct PyPI check (`pypi.org/pypi/mempalace/json`): latest is **3.3.5** (uploaded 2026-05-10); **3.3.6 is unpublished**. The "3.3.6" came from the milla-jovovich *plugin-fork* CHANGELOG, not a release.
- PyPI 3.3.5 (2026-05-10) predates PR #1461 (merged 2026-05-14). Confirmed installed `chroma.py` has only ratio-based quarantine and treats a 0-byte `link_lists.bin` as benign — the #1461 fix is **not** in any installed/installable artifact (CLI 3.3.5, plugin clone 3.3.2).
- **Reverted:** CLAUDE.md floor back to **v3.3.5+**; #1457 caveat reworded to "closed-as-issue but fix unshipped, manual `mv` workaround remains until 3.3.6 ships to PyPI" (`CLAUDE.md:119`, `:127`). Restored the `mempalace#1457` workaround entry with corrected `retire_when` ("shipped to PyPI AND installed", not just "closed"). Corrected `skills/ark-health/SKILL.md:259` narrative. Stamped the advisory artifacts SUPERSEDED.

### 4. MarkItDown office-doc ingest front-end (item 5)
- mempalace `--mode extract` (3.3.6, office-doc mining) is unusable here (3.3.6 unpublished; mines into a *palace*, not vault pages). Chose the **MarkItDown** front-end instead: convert binary office formats → markdown, then distill into vault pages (fills the real gap — Claude can't read `.docx/.pptx/.xlsx/.rtf/.epub` natively).
- Installed `markitdown 0.1.6` (standalone pipx env — does not touch mempalace's chromadb 1.5.7 pin); smoke-tested (HTML→markdown clean).
- Wired into `skills/data-ingest/SKILL.md` and `skills/wiki-ingest/SKILL.md` source-format lists with a `markitdown <file>` convert-first step + on-demand install hint.

## Decisions Made
- **mempalace floor stays v3.3.5+** — 3.3.6 is not installable from PyPI; bumping to it would document an unsatisfiable requirement. `ark-onboard` pin left at `>=3.3.5`.
- **#1457 workaround is NOT retire-able** — a CLOSED GitHub issue ≠ a shipped CLI release. Retirement waits on 3.3.6 publishing to PyPI.
- **Office-doc ingest via MarkItDown, not `mempalace mine --mode extract`** — different target (vault pages vs palace) and MarkItDown is version-independent.

## Issues & Discoveries
- **Fork-vs-PyPI gotcha:** the ark-skill-healer mempalace-plugin changelog tier reads the milla-jovovich fork's CHANGELOG, which runs ahead of the PyPI package. Treating its version headers as releases caused a wrong floor-bump + workaround-retire. The collector's release-tier `no_change` for mempalace-cli was correct all along. Lesson saved to memory: check `pypi.org/pypi/mempalace/json` before floor-bumping a mempalace fix.
- **Binary-dep install-lag blind spot** in ark-skill-healer (see Work §2).

## Open Questions
- When does mempalace 3.3.6 publish to PyPI? (gates #1457 workaround retirement + `--mode extract` availability)
- Implement the binary-dep install-lag check in `collect_upstream.sh`? (staged note exists)
- Pull obsidian-skills (4 commits behind, defuddle-URL move `facfef9`)? Low impact — no ark-skills file pins the old URL.

## Next Steps
1. Version bump + `/ship` this session's edits (CLAUDE.md, ark-health, data-ingest, wiki-ingest).
2. Watch mempalace 3.3.6 → PyPI; on release, retire the #1457 workaround + bump floor.
3. Consider implementing the ark-skill-healer binary-dep install-lag check.
