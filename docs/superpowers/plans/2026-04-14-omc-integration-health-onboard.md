# OMC Integration into /ark-health and /ark-onboard — Implementation Plan (v2, post-codex)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire OMC (oh-my-claudecode) awareness into `/ark-health` (as Check 21, optional capability extension, never fails) and `/ark-onboard` (Healthy Step 3 surfaces OMC as a separate "optional capability extension" group + Greenfield Step 18 final reminder + scorecard collapse rules + shared diagnostic checklist sync), so v1.13.0+'s `HAS_OMC` probe in `/ark-workflow` has a matching recommendation path.

**Architecture:** All edits are additive to skill text. Detection mirrors the canonical `HAS_OMC` probe in `skills/ark-workflow/SKILL.md:54-61` **structurally** (detect → set `HAS_OMC` → apply `ARK_SKIP_OMC` override after detection); structural parity is enforced by an explicit canonical-comparison verification step. `INSTALL_HINT_URL` is sourced verbatim from `skills/ark-workflow/references/omc-integration.md` § Section 0 (`https://github.com/anthropics/oh-my-claudecode`). Check 21 is **upgrade-style** (returns `pass`/`upgrade`/`skip`, **never `fail`**), mirroring Checks 14/17/18.

**Tier framing (revised per codex review):** Check 21 carries `Tier: Standard` for surfacing-priority purposes (it appears alongside Standard-tier checks in the scorecard) but **does not gate the Standard tier**, since the check never returns `fail`. To avoid the existing UX gap where "Upgrade to Full tier now?" follows the upgrade-opportunities list, OMC is surfaced in a **separate sub-block** in Healthy Step 3: `"Optional capability extensions:"` (OMC) — distinct from `"Available Full-tier upgrades:"` (MemPalace / history hook / NotebookLM). This prevents implying OMC promotes to Full tier.

**Tech Stack:** Markdown skill files (`skills/ark-health/SKILL.md`, `skills/ark-onboard/SKILL.md`); bash detection snippet (mirrors canonical structure); structural verification via `Grep`/`diff`/`bash -n`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `skills/ark-health/SKILL.md` | Modify | Add Check 21 (OMC plugin); update intro counts (20→21) at 8 sites; update Step 1 results dict; update tier-assignment block; update scorecard Output Format (Integrations); update authoritative-skill claim |
| `skills/ark-onboard/SKILL.md` | Modify | Update Shared Diagnostic Checklist sync note + integrations table heading + results dict + skip-rule + add Check 21 row; update 7 other "20 checks" / "Full tier 1-20" sites; add OMC to Healthy Step 3 (NEW sub-block "Optional capability extensions"); add OMC line to scorecard ASCII example; add `OMC plugin` to scorecard collapse rules; add non-blocking OMC mention to Greenfield Step 18 reminders; update Full-tier description |

No new files. No script changes — the canonical `HAS_OMC` probe in `skills/ark-workflow/SKILL.md:54-61` is the single source of truth; both target files describe how to invoke an equivalent inline probe whose structural shape is verified to match.

**Anti-drift boundary:** `INSTALL_HINT_URL` and the bash probe are duplicated as inline literals in both target skill files. They MUST match the canonical values in `references/omc-integration.md` § Section 0 (URL) and `skills/ark-workflow/SKILL.md:54-61` (probe). The verification step in Task 4 Step 6 runs an explicit `diff` of the canonicalized probe blocks AND a literal URL grep across all three files.

---

## Task 1: Add Check 21 (OMC plugin) to `/ark-health` Diagnostic Checklist

**Files:**
- Modify: `skills/ark-health/SKILL.md` — insert after Check 20's closing block (before `## Workflow` at line 529)

- [ ] **Step 1: Verify baseline (Check 21 absent)**

```bash
cd /Users/sunginkim/.superset/worktrees/ark-skills/ark-update
grep -c '^\*\*Check 21' skills/ark-health/SKILL.md
```

Expected: `0`.

- [ ] **Step 2: Insert Check 21 block**

Locate the closing `---` line that follows Check 20's `- **Fail:** Never.` line (around line 526) and the `## Workflow` heading (line 529). Insert this block in between, preceded by its own `---` separator line:

````markdown
**Check 21 — OMC plugin** | Tier: Standard (upgrade-style, never blocks tier classification)

Detect oh-my-claudecode (OMC) — the autonomous-execution framework that powers `/ark-workflow` Path B. Detection mirrors the canonical `HAS_OMC` probe in `skills/ark-workflow/SKILL.md:54-61` structurally: detect first, then apply the `ARK_SKIP_OMC=true` override (downstream emergency rollback per `skills/ark-workflow/references/omc-integration.md` § Section 3). Check 21 is exempt from the CLAUDE.md-missing skip rule because OMC presence is a CLI/cache-dir property, not a project-config property.

```bash
# Canonical: skills/ark-workflow/SKILL.md:54-61
# OMC_CACHE_DIR canonical: ~/.claude/plugins/cache/omc
# (see skills/ark-workflow/references/omc-integration.md § Section 0)
if command -v omc >/dev/null 2>&1 || [ -d "$HOME/.claude/plugins/cache/omc" ]; then
  HAS_OMC=true
else
  HAS_OMC=false
fi
# ARK_SKIP_OMC=true forces HAS_OMC=false regardless of detection
[ "$ARK_SKIP_OMC" = "true" ] && HAS_OMC=false

if [ "$HAS_OMC" = "true" ]; then
  echo "PASS: OMC detected"
elif [ "$ARK_SKIP_OMC" = "true" ]; then
  echo "SKIP: ARK_SKIP_OMC=true (user-suppressed)"
else
  echo "UPGRADE: OMC not installed"
fi
```

- **Pass:** `omc` CLI on PATH OR `~/.claude/plugins/cache/omc` directory exists, AND `ARK_SKIP_OMC` is not `true`
- **Upgrade action:** Install OMC at https://github.com/anthropics/oh-my-claudecode — unlocks `/ark-workflow` Path B (autonomous execution via `/autopilot`, `/ralph`, `/ultrawork`, `/team`)
- **Skip:** When `ARK_SKIP_OMC=true` (env-suppressed); render as `--` with note `OMC suppressed (ARK_SKIP_OMC=true)`
- **Fail:** Never. OMC is upgrade-style (mirrors Checks 14/17/18 — MemPalace, NotebookLM CLI, NotebookLM config).
- **Tier:** Standard — surfaces alongside Standard-tier checks in the scorecard. Absence does NOT block any tier classification (Standard, Quick, or Full).
- **CLAUDE.md exemption:** Check 21 runs even when CLAUDE.md is missing. It does not depend on any CLAUDE.md field.
````

(Preserve the literal triple-backtick fences around the bash block when editing.)

- [ ] **Step 3: Verify insertion + structural parity with canonical probe**

```bash
# Block exists
grep -c '^\*\*Check 21 — OMC plugin\*\*' skills/ark-health/SKILL.md

# Canonical structural parity: extract the detect-then-override portion of both probes
# and diff them after stripping comments and blank lines.
extract_probe() {
  awk '
    /^if command -v omc/{flag=1}
    flag {print}
    /^\[ "\$ARK_SKIP_OMC" = "true" \] && HAS_OMC=false$/{flag=0; exit}
  ' "$1" | grep -vE '^\s*#|^\s*$'
}
diff <(extract_probe skills/ark-workflow/SKILL.md) <(extract_probe skills/ark-health/SKILL.md)
echo "diff exit: $?"

# Bash syntax of inserted block
sed -n '/^\*\*Check 21 — OMC plugin\*\*/,/^---/p' skills/ark-health/SKILL.md | sed -n '/^```bash$/,/^```$/p' | sed '1d;$d' | bash -n
echo "bash -n exit: $?"
```

Expected: grep `1`; diff exit `0` (probes structurally identical); `bash -n` exit `0`.

- [ ] **Step 4: Single per-file commit deferred — see Task 2 Step 7**

Task 1 alone leaves `/ark-health` internally inconsistent (Check 21 exists but intro still says "20 checks"). Commit happens at end of Task 2.

---

## Task 2: Apply all "20 → 21" cascading consistency edits to `/ark-health`

**Files:**
- Modify: `skills/ark-health/SKILL.md` lines 8, 16, 18, 99, 533, 560, 575-586, 619-633 (Output Format), 654

These are all the sites that `grep -n "all 20\|20 diagnostic\|20 check\|20 checks\|7–20\|1–20"` returns for `/ark-health`. Codex flagged 99 and 654 as missed in v1.

- [ ] **Step 1: Update intro count and abort-prevention text (lines 8, 16, 18, 99)**

Edit line 8:
- Before: `Run all 20 diagnostic checks across the Ark ecosystem and produce a scored report with actionable fix instructions.`
- After: `Run all 21 diagnostic checks across the Ark ecosystem and produce a scored report with actionable fix instructions.`

Edit line 16. **Do NOT change "Checks 7–20" to "Checks 7–21"** — Check 21 is exempt from the CLAUDE.md-missing skip. Append a parenthetical instead:
- Before: `- Checks 7–20 report "cannot check — CLAUDE.md missing" instead of failing silently`
- After: `- Checks 7–20 report "cannot check — CLAUDE.md missing" instead of failing silently (Check 21 is exempt — runs unconditionally)`

Edit line 18:
- Before: `Never abort early. Run all 20 checks regardless of earlier failures.`
- After: `Never abort early. Run all 21 checks regardless of earlier failures.`

Edit line 99 (codex-flagged miss):
- Before: `Read CLAUDE.md before running these checks. If CLAUDE.md does not exist, checks 4–6 all fail and checks 7–20 report "cannot check — CLAUDE.md missing".`
- After: `Read CLAUDE.md before running these checks. If CLAUDE.md does not exist, checks 4–6 all fail and checks 7–20 report "cannot check — CLAUDE.md missing". Check 21 (OMC plugin) is exempt — it does not depend on CLAUDE.md.`

- [ ] **Step 2: Update Workflow Step 1 (lines 533, 535-558, 560)**

Edit line 533:
- Before: `Run checks in sequence. Do not abort on failure — complete all 20. Track results as you go:`
- After: `Run checks in sequence. Do not abort on failure — complete all 21. Track results as you go:`

Update the `results = {...}` dict to add line for Check 21. Insert after the existing `20: pass|warn,` line:
- Add: `  21: pass|upgrade|skip,`

Edit line 560:
- Before: `For checks 7–20: if CLAUDE.md was missing (check 4 = fail), record \`skip\` with message "cannot check — CLAUDE.md missing".`
- After: `For checks 7–20: if CLAUDE.md was missing (check 4 = fail), record \`skip\` with message "cannot check — CLAUDE.md missing". Check 21 (OMC plugin) is exempt — runs regardless of CLAUDE.md.`

- [ ] **Step 3: Update tier assignment block (lines 575-586)**

Replace the entire block (Tier assignment + Minimal/Quick/Standard/Full bullets + warn-checks note):

Before:
```
**Tier assignment:**

Determine the user's implicit tier from the highest tier where no Critical or Standard check returns `fail`. Warn and skip outcomes do NOT block tier classification.

- **Minimal tier:** No fail in checks 1–9, checks 10–11 skip (no vault)
- **Quick tier:** No fail in checks 1–11 (vault present, no integrations)
- **Standard tier:** No fail in checks 1–13 (TaskNotes MCP configured)
- **Full tier:** No fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Warn-returning checks (10 index staleness, 20 vault externalized) are advisory — they surface in the scorecard but don't demote the tier.
```

After:
```
**Tier assignment:**

Determine the user's implicit tier from the highest tier where no Critical or Standard check returns `fail`. Warn, skip, and upgrade outcomes do NOT block tier classification.

- **Minimal tier:** No fail in checks 1–9, checks 10–11 skip (no vault)
- **Quick tier:** No fail in checks 1–11 (vault present, no integrations)
- **Standard tier:** No fail in checks 1–13 (TaskNotes MCP configured)
- **Full tier:** No fail in checks 1–20 (MemPalace + history hook + NotebookLM + vault externalized OR embedded opt-out)

Check 21 (OMC plugin) is **tier-agnostic**: it never returns `fail`, so it never demotes any tier. It is surfaced in the scorecard alongside Standard-tier checks for visibility, but installing or omitting OMC has no effect on the user's tier.

Warn-returning checks (10 index staleness, 20 vault externalized) are advisory — they surface in the scorecard but don't demote the tier. Upgrade-returning checks (14 MemPalace, 17 NotebookLM CLI, 18 NotebookLM config, 21 OMC plugin) are also non-blocking.
```

- [ ] **Step 4: Add OMC to Output Format Integrations block (lines 619-633)**

Insert after the existing NotebookLM upgrade entry (lines 630-632), before the closing fence on line 633:

```
  --  OMC plugin -- not installed
      Unlock: /ark-workflow Path B (autonomous execution via /autopilot, /ralph, /ultrawork, /team)
      Install: see https://github.com/anthropics/oh-my-claudecode
```

When passed: render as `OK  OMC plugin -- detected`. When suppressed: render as `--  OMC plugin -- suppressed (ARK_SKIP_OMC=true)`. Document both forms in the comment area immediately after the integrations block (no separate code change — these are mode strings the runtime selects).

- [ ] **Step 5: Update authoritative-skill claim (line 654)**

Edit line 654 (codex-flagged miss):
- Before: `- **This skill is authoritative** for all 20 check definitions. If \`/ark-onboard\`'s copy of a check drifts from this file, this file is the source of truth.`
- After: `- **This skill is authoritative** for all 21 check definitions. If \`/ark-onboard\`'s copy of a check drifts from this file, this file is the source of truth.`

- [ ] **Step 6: Run structural verification across all `/ark-health` edits**

```bash
# All "20" → "21" sites updated (no stale references except the deliberate "Checks 7–20" exemption text)
remaining_20=$(grep -nE 'all 20 diagnostic|all 20 checks|complete all 20|Run all 20|all 20 check definitions' skills/ark-health/SKILL.md)
[ -z "$remaining_20" ] && echo "OK: no stale '20' counts" || { echo "FAIL: stale references"; echo "$remaining_20"; }

# Check 21 in results dict, intro, tier block, output format
grep -c '21: pass|upgrade|skip' skills/ark-health/SKILL.md
grep -c 'all 21 diagnostic checks' skills/ark-health/SKILL.md
grep -c 'all 21 check definitions' skills/ark-health/SKILL.md
grep -c 'tier-agnostic' skills/ark-health/SKILL.md
grep -c 'OMC plugin -- not installed' skills/ark-health/SKILL.md

# Canonical URL byte-match
grep -c 'https://github.com/anthropics/oh-my-claudecode' skills/ark-health/SKILL.md
```

Expected: `OK: no stale '20' counts`; all individual greps `≥1`.

- [ ] **Step 7: Atomic per-file commit**

```bash
git add skills/ark-health/SKILL.md
git commit -m "feat(ark-health): add Check 21 OMC plugin (upgrade-style, tier-agnostic)

- New Check 21 mirrors canonical HAS_OMC probe (skills/ark-workflow/SKILL.md:54-61)
  structurally: detect → set HAS_OMC → apply ARK_SKIP_OMC override
- Honors ARK_SKIP_OMC=true escape hatch
- Returns pass/upgrade/skip — never fail. Mirrors Checks 14/17/18 pattern.
- Tier-agnostic: surfaces in Standard-tier scorecard slot but never demotes any tier
- All 8 'all 20 / 1–20 / 7–20' references updated for consistency
- CLAUDE.md exemption documented (Check 21 has no project-config dependency)"
```

---

## Task 3: Sync `/ark-onboard` Shared Diagnostic Checklist with Check 21

**Files:**
- Modify: `skills/ark-onboard/SKILL.md` lines 193, 221, 224 (table block), 237-251

The shared diagnostic checklist in `/ark-onboard` is a copy of `/ark-health`'s definitions. Adding Check 21 to `/ark-health` requires syncing here, otherwise the two skills disagree.

- [ ] **Step 1: Update sync note (line 193)**

Edit:
- Before: `> **Sync note:** \`/ark-health\` is the authoritative source for all 20 check definitions. If this copy drifts from \`/ark-health\`, that skill is correct. This copy exists so \`/ark-onboard\` can run diagnostics without invoking a separate skill.`
- After: `> **Sync note:** \`/ark-health\` is the authoritative source for all 21 check definitions. If this copy drifts from \`/ark-health\`, that skill is correct. This copy exists so \`/ark-onboard\` can run diagnostics without invoking a separate skill.`

- [ ] **Step 2: Rename Integrations table heading (line 221)**

Edit:
- Before: `### Integrations (Checks 12-20)`
- After: `### Integrations (Checks 12-21)`

- [ ] **Step 3: Add Check 21 row to Integrations table**

After the existing line 233 (the Check 20 row), insert before the next blank/heading:

```
| 21 | OMC plugin | Standard (tier-agnostic) | `omc` CLI on PATH OR `~/.claude/plugins/cache/omc/` exists; `ARK_SKIP_OMC=true` forces skip |
```

- [ ] **Step 4: Update "Run all 20" + results dict + skip rules (lines 237, 240-243, 246-251)**

Edit line 237:
- Before: `Run all 20 checks in sequence. Never abort on failure. Track results:`
- After: `Run all 21 checks in sequence. Never abort on failure. Track results:`

Update results dict (lines 240-243). Replace:
```
results = {
  1..19: pass|fail|warn|skip|upgrade,
  20: pass|warn,
}
```
With:
```
results = {
  1..19: pass|fail|warn|skip|upgrade,
  20: pass|warn,
  21: pass|upgrade|skip,
}
```

Edit line 246:
- Before: `- Checks 7-20 with CLAUDE.md missing (check 4 = fail): record \`skip\` — "cannot check — CLAUDE.md missing"`
- After: `- Checks 7-20 with CLAUDE.md missing (check 4 = fail): record \`skip\` — "cannot check — CLAUDE.md missing"; Check 21 is exempt (no CLAUDE.md dependency)`

Add a new bullet after line 251 (immediately before the next heading or blank line):
- New: `- Check 21 (OMC): \`pass\` if \`omc\` CLI on PATH or \`~/.claude/plugins/cache/omc/\` exists; \`upgrade\` if neither; \`skip\` if \`ARK_SKIP_OMC=true\`. Never \`fail\`. Tier-agnostic (does not block any tier).`

- [ ] **Step 5: Verify**

```bash
grep -c 'all 21 check definitions' skills/ark-onboard/SKILL.md
grep -c 'Integrations (Checks 12-21)' skills/ark-onboard/SKILL.md
grep -c '| 21 | OMC plugin' skills/ark-onboard/SKILL.md
grep -c 'Run all 21 checks' skills/ark-onboard/SKILL.md
grep -c '21: pass|upgrade|skip' skills/ark-onboard/SKILL.md
grep -c 'Check 21 is exempt (no CLAUDE.md dependency)' skills/ark-onboard/SKILL.md
```

All expected `≥1`.

- [ ] **Step 6: Commit deferred — see Task 4 Step 8 (single per-file commit)**

---

## Task 4: Apply remaining `/ark-onboard` updates (Healthy Step 3, Greenfield Step 18, scorecard, all stale "20" sites)

**Files:**
- Modify: `skills/ark-onboard/SKILL.md` lines 1689, 1693-1701, 2379, 2490, 2511, 2519-2547, 2570 area, 2581, 2596

Codex flagged the following additional stale "20 checks" call sites that v1 missed: 1689, 1946, 2379, 2490, 2511, 2546. Plus the 5 user-requested surfaces.

- [ ] **Step 1: Add OMC to Greenfield Step 18 final reminders + 20→21 update at line 1689**

Edit line 1689:
- Before: `Run the full 20-check diagnostic (see Shared Diagnostic Checklist above). Show the scorecard (see Scorecard Output Format below).`
- After: `Run the full 21-check diagnostic (see Shared Diagnostic Checklist above). Show the scorecard (see Scorecard Output Format below).`

Edit reminder block (lines 1693-1701):

Before:
```
Setup complete! Follow-up reminders:

1. Open the vault in Obsidian — plugins are pre-configured (if downloaded/copied)
   OR: Install TaskNotes + Obsidian Git via Community Plugins (if manual fallback was needed)
2. Fill in NotebookLM notebook ID in .notebooklm/config.json (if Full tier)
3. Run /ark-health anytime to check ecosystem health
4. Run /ark-onboard again to upgrade tiers
```

After:
```
Setup complete! Follow-up reminders:

1. Open the vault in Obsidian — plugins are pre-configured (if downloaded/copied)
   OR: Install TaskNotes + Obsidian Git via Community Plugins (if manual fallback was needed)
2. Fill in NotebookLM notebook ID in .notebooklm/config.json (if Full tier)
3. Optional: install OMC for /ark-workflow Path B (autonomous execution) — see https://github.com/anthropics/oh-my-claudecode
4. Run /ark-health anytime to check ecosystem health
5. Run /ark-onboard again to upgrade tiers
```

In the conditional adjustment notes immediately below (lines 1703-1707), append one bullet:
- New: `- Omit OMC reminder if /ark-health Check 21 already reports OMC detected (HAS_OMC=true)`

- [ ] **Step 2: Update Migration follow-up reminder reference (line 1946 area)**

Re-read the file at line 1946 (context: "Show follow-up reminders (same as Greenfield Step 18, adjusted for migration context).") — no edit required if this line just references the Step 18 block; the change in Step 1 above will be inherited automatically. Verify:

```bash
sed -n '1940,1960p' skills/ark-onboard/SKILL.md
```

If this section has its own copy of the reminder text (rather than just a reference), apply the same OMC-line addition. Otherwise no edit.

- [ ] **Step 3: Update Repair-path "Run all 20" sites (lines 2379, 2490, 2511, 2546)**

Edit each:
- Line 2379: `Run all 20 checks. Record which checks fail.` → `Run all 21 checks. Record which checks fail.`
- Line 2490: `Run all 20 checks again. Show before/after scorecard:` → `Run all 21 checks again. Show before/after scorecard:`
- Line 2511: `Run all 20 checks. All Critical and Standard checks should pass.` → `Run all 21 checks. All Critical and Standard checks should pass.`
- Line 2546: `All 20 checks pass. Full tier active.` → `All 21 checks pass. Full tier active. (Check 21 OMC may be in upgrade state — non-blocking.)`

- [ ] **Step 4: Add OMC to Healthy Step 3 in a SEPARATE sub-block (lines 2519-2547)**

Codex flagged that listing OMC under "Available upgrades:" followed by "Upgrade to Full tier now?" misleads users into thinking OMC promotes to Full. Solution: add a NEW sub-block titled "Optional capability extensions:" for OMC, distinct from the Full-tier upgrade list.

Replace the entire block at lines 2525-2540:

Before:
```
Current tier: Standard. Available upgrades:

  MemPalace — deep vault search + experiential synthesis
    Install: pipx install "mempalace>=3.0.0,<4.0.0"
    Then run: bash skills/shared/mine-vault.sh

  History hook — auto-index Claude sessions on exit
    Install: bash skills/claude-history-ingest/hooks/install-hook.sh

  NotebookLM — fastest pre-synthesized vault queries
    Install: pipx install notebooklm-cli
    Then configure: /notebooklm-vault setup

Upgrade to Full tier now? [y/n]
```

After:
```
Current tier: Standard. Available Full-tier upgrades:

  MemPalace — deep vault search + experiential synthesis
    Install: pipx install "mempalace>=3.0.0,<4.0.0"
    Then run: bash skills/shared/mine-vault.sh

  History hook — auto-index Claude sessions on exit
    Install: bash skills/claude-history-ingest/hooks/install-hook.sh

  NotebookLM — fastest pre-synthesized vault queries
    Install: pipx install notebooklm-cli
    Then configure: /notebooklm-vault setup

Upgrade to Full tier now? [y/n]

Optional capability extensions (do NOT promote tier):

  OMC plugin — autonomous execution for /ark-workflow Path B
    Install: see https://github.com/anthropics/oh-my-claudecode
    (Install separately if interested; does not affect tier classification.)
```

- [ ] **Step 5: Add OMC line to scorecard ASCII example + update upgrade count (line 2570 area)**

Edit the scorecard table at lines 2557-2575. Insert one row after `| NotebookLM         --  not installed |`:

Before (excerpt):
```
| NotebookLM         --  not installed |
+--------------------------------------+
```

After:
```
| NotebookLM         --  not installed |
| OMC plugin         --  not installed |
+--------------------------------------+
```

Update the summary line on the same scorecard (line 2573):
- Before: `| 0 fixes, 0 warnings, 2 upgrades     |`
- After: `| 0 fixes, 0 warnings, 3 upgrades     |`

- [ ] **Step 6: Update scorecard collapse rules (line 2581)**

Edit:
- Before: `- Always show all logical groups, never omit a group. Related checks are collapsed: checks 4+5+6 → "CLAUDE.md", checks 7+8 → "Vault structure", checks 14+15 → "MemPalace", checks 17+18+19 → "NotebookLM"`
- After: `- Always show all logical groups, never omit a group. Related checks are collapsed: checks 4+5+6 → "CLAUDE.md", checks 7+8 → "Vault structure", checks 14+15 → "MemPalace", checks 17+18+19 → "NotebookLM", check 21 → "OMC plugin"`

- [ ] **Step 7: Update Full-tier description (line 2596) + warn-checks note (line 2599)**

Edit line 2596:
- Before: `| Full | No Critical or Standard fail in checks 1-20 (warn is OK) |`
- After: `| Full | No Critical or Standard fail in checks 1-20 (warn is OK); Check 21 is tier-agnostic and does not affect Full tier in either direction |`

Edit line 2599:
- Before: `**Warn checks do not block tier classification.** Checks 10 (index staleness) and 20 (vault externalized) return \`warn\`, which counts as "no fail" for tier purposes. They still surface in the scorecard as warnings.`
- After: `**Warn and upgrade checks do not block tier classification.** Checks 10 (index staleness) and 20 (vault externalized) return \`warn\`; Checks 14/17/18/21 (MemPalace, NotebookLM CLI, NotebookLM config, OMC) return \`upgrade\` when not installed. All count as "no fail" for tier purposes and still surface in the scorecard.`

- [ ] **Step 8: Cross-file canonical-constants drift verification**

This is the test that v1 lacked — explicit byte-comparison of canonical literals across all three files:

```bash
EXPECTED_URL="https://github.com/anthropics/oh-my-claudecode"

# URL drift: same literal in all three files
url_health=$(grep -c "$EXPECTED_URL" skills/ark-health/SKILL.md)
url_onboard=$(grep -c "$EXPECTED_URL" skills/ark-onboard/SKILL.md)
url_canonical=$(grep -c "$EXPECTED_URL" skills/ark-workflow/references/omc-integration.md)
echo "URL counts — health:$url_health onboard:$url_onboard canonical:$url_canonical (all must be ≥1)"

# Probe drift: structural diff (Task 2 Step 6 already ran for ark-health vs ark-workflow;
# rerun here to confirm no edit since Task 2 reverted it)
extract_probe() {
  awk '
    /^if command -v omc/{flag=1}
    flag {print}
    /^\[ "\$ARK_SKIP_OMC" = "true" \] && HAS_OMC=false$/{flag=0; exit}
  ' "$1" | grep -vE '^\s*#|^\s*$'
}
diff <(extract_probe skills/ark-workflow/SKILL.md) <(extract_probe skills/ark-health/SKILL.md)
echo "probe diff exit (must be 0): $?"

# Stale "20" sweep across both target files (excluding the deliberate "Checks 7–20" exemption text)
stale=$(grep -nE 'all 20 diagnostic|all 20 checks|complete all 20|Run all 20|all 20 check definitions|1-20 \(warn is OK\)|Integrations \(Checks 12-20\)|20 checks pass\.' skills/ark-health/SKILL.md skills/ark-onboard/SKILL.md)
[ -z "$stale" ] && echo "OK: no stale '20' counts" || { echo "FAIL: stale references"; echo "$stale"; }

# Markdown structure sanity: line counts grew (not shrunk), no accidental Check 22
wc -l skills/ark-health/SKILL.md skills/ark-onboard/SKILL.md
grep -c '^\*\*Check 2[0-9]' skills/ark-health/SKILL.md
echo "(expected: 2 — Check 20 + Check 21)"

# Healthy Step 3 has BOTH the Full-tier prompt AND the new sub-block
grep -c 'Available Full-tier upgrades' skills/ark-onboard/SKILL.md
grep -c 'Optional capability extensions' skills/ark-onboard/SKILL.md
grep -c 'do NOT promote tier' skills/ark-onboard/SKILL.md
```

Expected: URL counts all `≥1`; probe diff exit `0`; `OK: no stale '20' counts`; Check 22 grep `2`; the three Healthy Step 3 greps all `≥1`.

- [ ] **Step 9: Atomic per-file commit**

```bash
git add skills/ark-onboard/SKILL.md
git commit -m "feat(ark-onboard): add OMC awareness — Check 21 sync, Healthy Step 3, scorecard, Greenfield Step 18

- Shared Diagnostic Checklist gains Check 21 row + 20→21 sync note + results-dict + skip-rule
- Integrations heading: 'Checks 12-20' → 'Checks 12-21'
- Healthy Step 3: NEW 'Optional capability extensions' sub-block for OMC
  (separate from 'Available Full-tier upgrades' to prevent implying OMC promotes Full)
- Greenfield Step 18 reminders mention OMC once, non-blocking
- Scorecard ASCII example gains OMC row + bumps upgrade count 2→3
- Scorecard collapse rules add 'check 21 → OMC plugin' group
- Full-tier description acknowledges Check 21 as tier-agnostic
- Repair-path 'Run all 20' sites updated (lines 2379, 2490, 2511, 2546)
- Final-diagnostic step 1689 'Run the full 20-check' updated
- Stale '20 checks' references swept across the file"
```

---

## Self-Review Checklist (run after all 4 tasks)

- [ ] **Spec coverage:** Every user-stated scope item AND every codex-flagged miss is covered:
  - `/ark-health` Check 21 → Task 1
  - `/ark-onboard` Healthy Step 3 (with codex's separate-sub-block reframing) → Task 4 Step 4
  - `/ark-onboard` Greenfield Step 18 final reminders → Task 4 Step 1
  - `/ark-health` tier assignment rules update → Task 2 Step 3
  - `/ark-onboard` scorecard collapse rules "OMC" group → Task 4 Step 6
  - Detection mirrors HAS_OMC probe **structurally** (codex-driven correction) → Task 1 Step 2 + Task 1 Step 3 (diff-based parity check)
  - ARK_SKIP_OMC=true escape hatch → Task 1 Step 2 (matches canonical placement: after detect, not before)
  - INSTALL_HINT_URL byte-match → Task 4 Step 8 cross-file drift check
  - **Codex miss #1:** `/ark-health` line 99 stale "checks 7–20" → Task 2 Step 1
  - **Codex miss #2:** `/ark-health` line 654 stale "all 20 check definitions" → Task 2 Step 5
  - **Codex miss #3:** `/ark-onboard` lines 193 (sync note), 221 (table heading), 237 (Run all 20), 246 (skip rule), 1689 (full 20-check), 2379/2490/2511/2546 (Repair-path) — all → Task 3 + Task 4 Steps 1 and 3

- [ ] **Internal consistency (codex finding #4):** No verification step greps for a string that other steps explicitly DIDN'T introduce. Specifically: Task 2 Step 1 leaves "Checks 7–20" intact (with parenthetical exemption) and Task 2 Step 6 does NOT grep for "7–21".

- [ ] **Commit atomicity (codex finding #5):** Two commits total — one per file. Each leaves its file internally consistent.

- [ ] **Probe parity (codex finding #1):** Bash probe is structurally identical to canonical — same `if command -v omc / set HAS_OMC / apply ARK_SKIP_OMC override after` shape. Verified by `diff` in Task 1 Step 3 and Task 4 Step 8.

- [ ] **Tier framing (codex finding #2):** Resolved by:
  - Keeping `Tier: Standard` label (per user's explicit instruction)
  - Marking Check 21 explicitly as `tier-agnostic` everywhere it appears in tier-classification context
  - Splitting Healthy Step 3 into TWO sub-blocks so OMC is no longer implied to promote Full tier

- [ ] **Placeholder scan:** No "TBD", "TODO", "implement later", "fill in details", or hand-wavy text. All bash snippets are runnable; all sed/grep/diff verification commands have expected outputs.

- [ ] **String/casing consistency:** "Check 21", "OMC plugin", `https://github.com/anthropics/oh-my-claudecode`, `ARK_SKIP_OMC=true`, `HAS_OMC` — spellings match canonical sources everywhere.

- [ ] **Coordination note:** Session 2 shares branch `ark-update`. Do NOT version-bump or `/ship` solo — defer to user-coordinated batch with Session 2's work. Mentioned in chain file `.ark-workflow/current-chain.md` Notes section.
