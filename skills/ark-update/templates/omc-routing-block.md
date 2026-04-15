## Skill routing — OMC integration

This section is managed by `/ark-update`. Do not hand-edit content between the ark markers.

### When OMC is available

When `HAS_OMC=true` (i.e., `command -v omc` succeeds and `ARK_SKIP_OMC` is not set),
`/ark-workflow` Step 6 renders a 3-button choice after triage:

```
[Accept Path B]   [Use Path A]   [Show me both]
```

**Path A (Ark-native):** step-by-step, user-in-the-loop, discrete skills at every decision
point. Always available. Default when OMC is not detected.

**Path B (OMC-powered):** front-loaded judgment + consensus plan + autonomous execution +
Ark closeout. Recommended when any of these signals fires:
- Prompt contains an OMC keyword (`autopilot`, `ralph`, `ulw`, `deep interview`, etc.)
- Triaged weight class is Heavy
- Task touches ≥3 independent modules
- User explicitly requests hands-off execution

**Emergency rollback:** `ARK_SKIP_OMC=true /ark-workflow "<prompt>"` forces Path A
regardless of OMC detection. Intended for incident response.

### Install OMC

OMC not detected? Install it to unlock Path B chains:

  See INSTALL_HINT_URL for installation instructions.
  (Constant defined in `skills/ark-workflow/references/omc-integration.md` § Section 0.)

After installation, re-run `/ark-workflow` — OMC detection is automatic.

### Path B routing table

| Variant | OMC engine | Handback boundary |
|---------|-----------|-------------------|
| Greenfield / Bugfix / Hygiene / Ship / Migration (non-Heavy) | `/autopilot` | After Phase 4; Phase 5 (docs/ship) skipped |
| Greenfield Heavy (multi-module) | `/ultrawork` | After last parallel lane completes |
| Bugfix Heavy / Performance Medium+Heavy | `/ralph` | After loop-to-verified exits with success |
| Migration Heavy | `/team` | After `team-verify`, before `team-fix` |

After `<<HANDBACK>>`, Ark resumes from the variant's Path A closeout step.
See `skills/ark-workflow/references/omc-integration.md` § Section 4 for the full
variant-inherited handback contract and expected-closeout table.
