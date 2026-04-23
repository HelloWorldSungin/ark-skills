# /ark-code-review — External Second Opinion (framing, cost, vendor capacity)

Philosophical framing and operational caveats for the vendor-CLI second-opinion fan-out landed in v1.14.0.

Operational rules (trigger conditions, `--no-multi-vendor` opt-out, trust-boundary notice, fan-out command shape, degradation table) stay inline in `SKILL.md` § External Second Opinion — they are security-critical and must be visible without loading this file. This file holds the explanatory prose.

---

## Framing: what the vendors add (and don't)

| Source | What it brings |
|---|---|
| Native CC agents (`code-reviewer`, `code-architect`, …) | Conventions awareness (CLAUDE.md, ark skills), same-context continuity, access to vault/TaskNotes |
| Codex CLI via `omc ask codex` | OpenAI model family's training-biased code-quality lens — second opinion on bugs, logic, security smells |
| Gemini CLI via `omc ask gemini` | Google model family's training-biased perspective — second opinion on UI/UX cues and documentation hygiene |

**The value is vendor diversity, not capability expansion.** The native CC review already covers correctness / architecture / tests at parent capacity. The vendor streams are a cheap sanity check: when Codex and the native reviewer both flag the same issue, confidence rises; when only a vendor flags it, you have a specific vendor-diversity signal to weigh.

---

## Why `omc ask`, not `omc team`

Fan-out uses the `omc ask <vendor> "<prompt>"` primitive from the OMC framework. Unlike `omc team` (which spawns tmux panes and requires multi-stage leader orchestration via `omc team api`), `omc ask` is a single-shot invocation that:

- Handles shell/JSON quoting of the prompt argument internally — no injection surface for the review skill to manage.
- Handles vendor CLI authentication, timeout, and retry concerns.
- Returns the path to a captured markdown artifact on stdout.
- Writes the artifact to `.omc/artifacts/ask/<vendor>-<slug>-<ts>.md` for later re-read.

This surface therefore does **not** require tmux and has no `omc team api list-tasks` JSON-schema dependency.

---

## Synthesis detail

After all sources (native + vendor) complete, Claude reads each vendor artifact directly:

```bash
cat .omc/artifacts/ask/codex-<slug>-<ts>.md
cat .omc/artifacts/ask/gemini-<slug>-<ts>.md
```

No JSON parsing, no tmux pane capture — the artifacts are plain markdown. Findings merge into the unified report; the "Reviewers" header line in the final report adds vendor labels:

```
Reviewers: code-reviewer, code-architect, test-coverage-checker, silent-failure-hunter, test-analyzer, codex-cli, gemini-cli
```

Findings deduplicate across all sources (prefer the more specific finding, or the one backed by ark-conventions context). Each entry tags which source surfaced it (e.g., `Found by: codex-cli`).

---

## Cost notice

Each `omc ask` invocation is a separate call to the vendor's API. For Heavy diffs with dual-vendor fan-out, the cost delta over native-only review is two additional vendor API calls per `--thorough`. If a per-review cost ceiling applies, use `--no-multi-vendor` to opt out for that invocation, or uninstall the vendor CLI whose review isn't wanted.

---

## Vendor capacity caveat (Gemini)

During live testing, Gemini preview models (`gemini-3.1-pro-preview` class) have returned `MODEL_CAPACITY_EXHAUSTED` (HTTP 429) under burst load. When this happens, `omc ask gemini` exits non-zero; treat it as a per-vendor runtime failure per the degradation table in `SKILL.md` and continue synthesis on the remaining streams. The failure is on the vendor side, not the `/ark-code-review` skill. Retry the Gemini stream manually later if full coverage matters for that review.
