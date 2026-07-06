---
title: "Upstream Fork CHANGELOG vs PyPI Release Skew"
type: compiled-insight
tags:
  - compiled-insight
  - ark-skill-healer
  - mempalace
  - upstream-watch
  - dependency-management
description: "A CLOSED GitHub issue is not a shipped release. ark-skill-healer's changelog tier reads a plugin-fork CHANGELOG that runs ahead of the PyPI package — verify pypi.org/pypi/<pkg>/json before floor-bumping or retiring a workaround on an upstream fix."
source-sessions:
  - "[[S015-Ark-Skill-Healer-Run-Mempalace-Fork-vs-PyPI]]"
source-tasks: []
created: 2026-06-05
last-updated: 2026-06-05
timestamp: 2026-06-05T00:00:00Z
---

# Upstream Fork CHANGELOG vs PyPI Release Skew

## The trap
A dependency fix can be in **four distinct states**, and they are easy to conflate:

1. **PR merged** upstream (code exists on a branch)
2. **Issue closed** on GitHub (`gh issue view` → CLOSED/COMPLETED)
3. **Documented in a CHANGELOG** (a version header exists)
4. **Published to the package index** (installable via `pip`/`pipx`)

Only state **4** means the fix is in a user's installed software. States 1–3 routinely run ahead of 4.

## The concrete incident (S015, mempalace #1457)
`/ark-skill-healer` flagged mempalace **3.3.6** as "fixes #1457" (zero-byte `link_lists.bin` SIGSEGV gap), and `gh` confirmed #1457 **CLOSED 2026-05-14** via merged PRs #1461/#1452. On that basis a CLAUDE.md floor-bump (v3.3.5+ → v3.3.6+) and a workaround **retirement** were applied.

They were **wrong**. Attempting the actual CLI upgrade exposed it:
- `pipx` reported mempalace already at latest **3.3.5**.
- `https://pypi.org/pypi/mempalace/json` → `info.version` = **3.3.5** (uploaded 2026-05-10). **3.3.6 is unpublished.**
- PyPI 3.3.5 (2026-05-10) **predates** PR #1461 (merged 2026-05-14), so the installed CLI does not contain the fix. Installed `chroma.py` still treats a 0-byte `link_lists.bin` as benign.

The "3.3.6" came from the **milla-jovovich plugin-fork CHANGELOG**, which is what ark-skill-healer's `mempalace-plugin` changelog tier reads — not the canonical PyPI package (`mempalace-cli`). The collector's **release-tier `no_change` for `mempalace-cli` was correct all along**; the changelog-tier 3.3.6 was fork-only.

## Why ark-skill-healer is structurally exposed to this
- `mempalace-plugin` (source `milla-jovovich/mempalace`) and `mempalace-cli` (source `MemPalace/mempalace`, PyPI) are **two inventory records for what looks like one project**, with **divergent version numbering**.
- The changelog tier reads the fork clone's `CHANGELOG.md` at the upstream tip → it can show versions the PyPI package hasn't cut.
- Issue/PR numbers in the fork's changelog reference the canonical repo, so `gh` verification of "closed" passes — reinforcing the false "shipped" conclusion.

## The rule
**Before bumping a version floor or retiring a workaround on an upstream fix, confirm the fix is in a *published release*, not just merged/closed/changelogged.** For PyPI deps:

```bash
python3 -c "import json,urllib.request; print(json.load(urllib.request.urlopen('https://pypi.org/pypi/mempalace/json'))['info']['version'])"
```

Gate the retirement on **"shipped to the package index AND installed"**, not "issue closed." A workaround's `retire_when` should name the published version, e.g. *"mempalace 3.3.6 published to PyPI AND installed CLI upgraded to it."*

## Related
- [MemPalace-HNSW-Bloat-Repair](MemPalace-HNSW-Bloat-Repair.md) — the #1457 workaround this gotcha kept alive (manual segment `mv` until 3.3.6 ships).
- [Plugin-Versioning-and-Cache-Pitfalls](Plugin-Versioning-and-Cache-Pitfalls.md) — sibling versioning trap (plugin cache staleness).
- [Ecosystem-Architecture-Map](Ecosystem-Architecture-Map.md) — where mempalace sits in the dependency graph.
