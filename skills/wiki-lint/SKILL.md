---
name: wiki-lint
description: Audit vault health — broken links, missing frontmatter, stale index, tag violations
---

# Wiki Lint

Audit the project's Obsidian vault for structural issues and produce a health report.

## Project Discovery

1. Read the project's CLAUDE.md to find the vault path
2. Read `{vault_path}/_meta/taxonomy.md` for canonical tag list
3. Read `{vault_path}/index.md` for page inventory

## Lint Checks

Run all checks in sequence. Report findings as a structured list.

### Check 1: Broken Wikilinks

```bash
cd {vault_path}
grep -roh '\[\[[^]]*\]\]' --include="*.md" . | sed 's/\[\[//;s/\]\]//;s/|.*//' | sort -u | while read link; do
  base=$(echo "$link" | sed 's/#.*//')
  [ -z "$base" ] && continue
  found=$(find . -name "${base}.md" 2>/dev/null | head -1)
  [ -z "$found" ] && echo "BROKEN: [[${link}]]"
done
```

### Check 2: Orphaned Pages

Find pages with zero incoming wikilinks (excluding index.md, 00-Home.md, templates):

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  basename=$(basename "$f" .md)
  incoming=$(grep -rl "\[\[$basename" --include="*.md" . 2>/dev/null | grep -v "$f" | wc -l | tr -d ' ')
  [ "$incoming" -eq 0 ] && echo "ORPHAN: $f"
done
```

### Check 3: Missing Frontmatter

Check all pages have required fields: `title`, `type` (or `task-type`), `tags`

```bash
cd {vault_path}
find . -name "*.md" ! -path './.obsidian/*' ! -path './.git/*' ! -path './_Templates/*' ! -path './_meta/*' | while read f; do
  head -1 "$f" | grep -q "^---" || echo "NO FRONTMATTER: $f"
done
```

### Check 4: Missing Summary

Check for `summary:` field on all pages. Report count of pages without it.

### Check 5: Tag Violations

Compare all tags in use against `_meta/taxonomy.md`. Flag:
- Tags not in taxonomy
- Alias tags that should be normalized

### Check 6: Index Freshness

Compare page count in `index.md` vs actual `.md` files on disk. If they differ, the index is stale.

### Check 7: Summary Length

Find pages where `summary:` exceeds 200 characters.

## Report Format

```
Wiki Lint Report: {project_name}
================================
Broken wikilinks: N
Orphaned pages: N
Missing frontmatter: N
Missing summary: N
Tag violations: N
Index stale: yes/no
Summary too long: N

Details:
[list each issue with file path]
```

## Skill-Graph Lint Mode (plugin repo only)

When run in the ark-skills plugin repo (presence of `skills/*/SKILL.md`), six
additional checks audit the skill graph itself. These are skipped silently in
downstream vault repos.

Run via the Python helper:

```bash
python3 skills/wiki-lint/scripts/skill_graph_audit.py
```

The script exits 1 if any HARD error is found, else 0. Findings are tagged
`ERROR` (HARD) or `WARN` (soft) per the rules below.

### Check 8: Catalog Drift

- **HARD** error if `find skills -maxdepth 2 -name SKILL.md` (excluding
  `shared/`) and the parsed catalog rows in `skills/AGENTS.md` (Subdirectories
  section), `README.md` (Available Skills table), and `CLAUDE.md` (Available
  Skills bullets) disagree on the set of skills present.
- **WARN** when descriptions for the same skill diverge across catalogs
  (Jaccard word similarity < 0.30).

### Check 9: Section-Anchor Refs

Find every `references/<file>.md § Section X.Y` citation across `skills/`.
Resolve each by walking ancestors of the citing file (chain prose often elides
the parent skill in the path). Heading scheme is dual:

- `## Section N — Title` for top-level
- `### N.M Title` for sub-numbering (no "Section" prefix)

**WARN** if either the cited file or the cited section is unresolvable.

### Check 10: Description Shape (heuristic)

For each `SKILL.md` frontmatter `description`:

- **WARN** if shorter than 50 chars or longer than ~500 chars.
- **WARN** if no recognized trigger verb appears (use/run/audit/search/...).
  This is a heuristic, not a phrase-match — three canonical atom skills
  (`/wiki-status`, `/tag-taxonomy`, `/cross-linker`) do not contain literal
  "Use when"/"Do NOT use" phrases and are correct.
- **WARN** when two descriptions overlap on word-set Jaccard > 0.55 — suggests
  the router may pick wrong; consider adding a negative-routing clause.

Never errors. The lint does not enforce a literal description template.

### Check 11: Active-Body Length

**WARN** at 500 lines per the published skill-design guidance. Do **not**
auto-trigger refactor — `/ark-workflow/SKILL.md`, `/ark-onboard/SKILL.md`, and
`/ark-health/SKILL.md` all exceed 500 today and have load-bearing sections
(Project Discovery, Scenario Detection, Triage, Chain Lookup, Condition
Resolution Dispatch, Condition Definitions) that cannot move into `references/`
without behavior loss. The warn is informational.

### Check 12: Chain Reachability

Parse each `skills/ark-workflow/chains/*.md`, extract the leading-token
slash-command from every backtick span (so `/ark-code-review --quick` resolves
to `/ark-code-review`). Cross-check against:

- The internal skill set (`find skills -maxdepth 2 -name SKILL.md`)
- `skills/ark-workflow/references/external-skills.yaml` (canonical external
  registry maintained per Arkskill-012-S2)

**WARN** on any unclassified slash-command — likely typo, renamed skill, or a
new external dependency that needs a registry entry.

### Check 13: Compound-to-Compound Calls

Soft signal that an orchestrating skill (a "compound") invokes another
compound. Compound detection is heuristic: any internal `SKILL.md` with a
`chains/` subdir, or whose body invokes ≥ 2 distinct internal slash-commands.

**WARN** soft. Live examples in this repo are correct (`/ark-code-review` and
`/codebase-maintenance` from chains, `/wiki-handoff` from `/ark-workflow` Step
6.5, `/ark-onboard` ↔ `/ark-update` ↔ `/ark-health` cross-references). The
guardrail (per `skills/AGENTS.md` § Composition Guardrails) is **not** "no
compound calls another compound" — it's "only via explicit chain steps with
conditions resolved before presentation, with bounded mode/argument and a
documented handback point."

## Skipped Checks (not applicable to Ark vaults)

- Provenance drift — Ark vaults don't use `provenance:` markers
- Stale content by timestamp — no source-tracking manifest
- Contradiction detection — too expensive for routine lint
- Version-state lint (VERSION/plugin.json/marketplace.json/CHANGELOG
  consistency) — belongs in `/ark-update` or a separate release lint, not
  here.
