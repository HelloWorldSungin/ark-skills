# ark-update templates/

Template files used by `/ark-update`'s target-profile ops. Each file here corresponds
to at least one `managed_regions[]` or `ensured_files[]` entry in `target-profile.yaml`.

## Marker version= semantics

Every managed region written by the engine carries an HTML comment marker pair:

```
<!-- ark:begin id=<stable-id> version=<semver> -->
...managed content...
<!-- ark:end id=<stable-id> -->
```

The `version=` value on the `ark:begin` marker is **emitted on write** from the
`version` field in `target-profile.yaml:managed_regions[].version`. It is **parsed on
read** by `detect_drift` to compare against the target profile's current version.

### What version= signals

- `version=` in the file == `version` in target profile: region content is current.
  Idempotency check passes; the op is a no-op on this run.
- `version=` in the file < `version` in target profile: **drift signal**, even if the
  region text content is byte-identical to the template. The engine overwrites the region
  (writing a backup of the prior content) and updates the marker to the current version.
  This restores "marker-version honesty" — a stale version= would silently mask future
  drift. (Codex P2-3 fix.)

### When to bump version in target-profile.yaml

Bump `managed_regions[].version` (and update this file's corresponding template) when:
- The template content changes structurally (new lines, reordered sections, changed URLs).
- A new constant or table row is added.
- The template's semantics change in a way that downstream projects should re-apply.

Do NOT bump version for cosmetic whitespace changes that don't affect rendered output.

The engine uses `version` as a drift signal, so unnecessary bumps cause spurious
overwrites on downstream projects. Be deliberate.

## CI enforcement

`scripts/check_target_profile_valid.py` enforces:
1. Every `template:` reference in `target-profile.yaml` resolves to a real file in this directory.
2. Every file in this directory (except `README.md`) has a corresponding `template:` reference
   in `target-profile.yaml`.
3. `templates/routing-template.md` is byte-equal to
   `skills/ark-workflow/references/routing-template.md` (drift guard — the routing template
   is a canonical copy and must not diverge).

Run the validator before committing template changes:

```
python3 skills/ark-update/scripts/check_target_profile_valid.py
```

## Files in this directory

| File | Type | Managed by |
|------|------|------------|
| `omc-routing-block.md` | Managed CLAUDE.md region | `managed_regions[id=omc-routing]` |
| `routing-template.md` | Routing rules block (byte-copy) | `managed_regions[id=routing-rules]` |
| `setup-vault-symlink.sh` | Ensured file | `ensured_files[id=setup-vault-symlink]` |
| `README.md` | Documentation | (exempt from template-reference enforcement) |

## Adding a new template

1. Add the file to `templates/`.
2. Add a corresponding entry in `target-profile.yaml` (`managed_regions[]` or `ensured_files[]`).
3. Set `since:` to the plugin version that introduces this convention (must appear in `CHANGELOG.md`).
4. Set `version:` to the same value as `since:` for new entries.
5. Run `python3 skills/ark-update/scripts/check_target_profile_valid.py` to verify.
