---
name: vault
description: Write-side knowledge operations for the OKF vault bundle at vault/. Triggers on "update the vault", "save this knowledge", "ingest this doc", "distill", "end of session knowledge", "regenerate index". Writes durable insights, research, decisions, and reference pages only — NOT session logs and NOT task tracking. Reading the vault is a separate concern (use NotebookLM or okf_cli.py).
---

# vault — OKF Knowledge Ops (write side)

Write-side knowledge operations for the **OKF bundle** at `vault/`. This skill
persists **durable knowledge only**: research findings, decisions and their
rationale, and reference pages worth keeping.

**Out of scope — do not do these here:**
- **Session logs** — retired. The work record lives in GitHub issues + the bundle's
  `log.md`, not in narrative session pages.
- **Task tracking** — GitHub Issues. TaskNotes is frozen.
- **Reading / querying** — this is write-side only. To read the vault, use
  NotebookLM (synthesized recall) or `python3 vault/_meta/okf/okf_cli.py
  {list,search,read}`.

## Schema-first rule (mandatory)

Before writing ANY page:

1. Read `vault/_meta/vault-schema.md` — the authoritative frontmatter + directory spec.
2. Check `vault/_Templates/` for a matching template (Research, Compiled-Insight,
   Service, etc.) and start from it.

Every page you write emits **OKF frontmatter** and **relative markdown links**:

- Frontmatter keys: `type`, `description` (≤200 chars), `timestamp` (ISO 8601),
  `tags` (from `vault/_meta/taxonomy.md`), plus type-specific keys per the schema
  (`source-sessions`, `source-tasks` for insights/research). Use `type:` — never
  `category:`. Never use `provenance:` markers.
- Links: **relative markdown** — `[label](../Research/page.md)`. **Never wikilinks**
  (`[[page]]`). The OKF lint gate rejects wikilinks.

## Operations

### 1 — End-of-session distillation

Extract the *durable* insights from the session — not a narrative of what happened
(that is the GitHub issue + `log.md`), but knowledge that outlives the session:
decisions and why, research conclusions, reusable reference facts.

1. Identify each durable insight. Discard play-by-play, task status, and anything
   already captured as an issue comment.
2. For each, pick the right folder (e.g. `Compiled-Insights/`, `Research/`) and the
   matching template. One coherent insight per page; link related pages relatively.
3. Write OKF-conformant pages. Populate `source-tasks` with the GitHub issue numbers
   the insight came from.
4. Finish with the index + lint step (below).

### 2 — Document ingestion

Distill an external document, transcript, or export into vault pages. (Absorbs the
retired document-ingestion rules, rewritten for OKF.)

1. Read the source. Determine whether it is one page or several distinct topics —
   split by topic, one topic per page.
2. For each page: choose folder + template, write a ≤200-char `description`, tag from
   the taxonomy, and **distill** — summarize and structure the knowledge; do not
   paste the raw document. Preserve source attribution in `source-*` frontmatter.
3. Cross-link related pages with relative markdown links.
4. Finish with the index + lint step (below).

**`/research` output is a first-class ingest source.** mattpocock's `/research` skill
writes cited-Markdown findings to `vault/Research/` (declared in `CLAUDE.md` → Project
Configuration → Research notes). Ingesting them is the same distillation as above:
give each an OKF `type:`, a ≤200-char `description:`, and populate `source-tasks:` with
the originating GitHub issue number(s). Distill — do not paste the raw research file.

### 3 — log.md append (work-record mirror)

The bundle's `log.md` is a synced mirror of GitHub progress comments (dual-write; the
GitHub comment is authoritative). When invoked to record work progress, append a
short line — issue number, one-line summary, and the GitHub comment permalink
(`gh issue view <n> --json url --jq .url`). This keeps the vault's work log
continuous for NotebookLM sync. See `docs/agents/issue-tracker.md` for the dual-write
rule. `log.md` is append-only work record — it is NOT a knowledge page and does not
get OKF frontmatter.

### 4 — Always finish: regenerate index + lint (mandatory gate)

After ANY write in operations 1–3, run both, in order:

```bash
python3 vault/_meta/generate-index.py
python3 vault/_meta/okf/okf_lint.py --quiet ; echo "exit=$?"
```

`okf_lint.py --quiet` **must exit 0**. If it reports errors, fix them (usually a
wikilink that should be a relative link, a missing `description`, or a malformed
timestamp) and re-run until it exits 0. Do not report the vault update as complete
until lint is clean.

## Read-side note

Querying the vault is NOT this skill. For factual/synthesized recall use NotebookLM;
for navigation/full-text use `python3 vault/_meta/okf/okf_cli.py {list,search,read}`.
