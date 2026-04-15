#!/usr/bin/env python3
"""CI validator for ark-update target-profile.yaml.

Mirrors the pattern of skills/ark-context-warmup/scripts/check_chain_integrity.py.

Checks:
  1. target-profile.yaml structure (schema_version, required fields per entry type).
  2. All op: names are in OP_REGISTRY.
  3. All template: references resolve to files under templates/.
  4. All since: values appear in repo's CHANGELOG.md.
  5. Byte-equality: templates/routing-template.md == skills/ark-workflow/references/routing-template.md.
  6. Path-safety: every file:/target: field resolves via paths.safe_resolve without raising
     (absolute paths and .. escapes will fail — codex P1-1).
  7. Schema acceptance for failed_ops[] and depends_on_op in migrations/*.yaml (codex P2-4).
  8. _ark_managed sentinel documentation check for ensure_mcp_server entries.

Exit 0 on success, non-zero on failure with clear error messages on stderr.
~200 LOC.

Note (codex P2-8 prep): a future Step 8 should add a repo-wide check verifying
that no stale references to "21 checks" or "20 checks" remain after /ark-health
check counts change. Step 5 notes this but does not implement it — Step 8 owns it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Registered op type names — mirrors OP_REGISTRY keys populated by Step 3.
OP_REGISTRY = {
    "ensure_claude_md_section",
    "ensure_gitignore_entry",
    "ensure_mcp_server",
    "create_file_from_template",
    "ensure_routing_rules_block",
}

# Required fields per entry type.
_MANAGED_REGION_REQUIRED = {"op", "file", "since", "version"}
_ENSURED_FILE_REQUIRED = {"op", "target", "template", "since", "version"}
_ENSURED_GITIGNORE_REQUIRED = {"entry", "since"}
_ENSURED_MCP_REQUIRED = {"id", "name", "since"}

# ensure_routing_rules_block does not require a template: field (it embeds
# the routing template content via the op's own logic).
_NO_TEMPLATE_OPS = {"ensure_routing_rules_block"}

# Fields whose values are file paths (must pass path-safety check).
_PATH_FIELDS = ("file", "target")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_repo_root(start: Path) -> Path:
    """Walk up from *start* to find the git repo root (contains CHANGELOG.md)."""
    p = start.resolve()
    for ancestor in [p, *p.parents]:
        if (ancestor / "CHANGELOG.md").exists():
            return ancestor
    return start.resolve()


def _safe_resolve_check(project_root: Path, rel_path: str) -> str | None:
    """Return None if rel_path is safe, or an error string if it escapes project_root."""
    if os.path.isabs(rel_path):
        return f"absolute path not allowed: {rel_path!r}"
    resolved = (project_root / rel_path).resolve()
    try:
        resolved.relative_to(project_root.resolve())
        return None
    except ValueError:
        return f"path escapes project root: {rel_path!r} -> {resolved}"


def _check_yaml_structure(data: dict, errors: list[str]) -> None:
    """Check 1: top-level keys and required fields per entry type."""
    if not isinstance(data.get("schema_version"), int):
        errors.append("schema_version is missing or not an integer")

    for i, entry in enumerate(data.get("managed_regions", [])):
        missing = _MANAGED_REGION_REQUIRED - set(entry.keys())
        # template is required unless the op type is in _NO_TEMPLATE_OPS
        op = entry.get("op", "")
        if op not in _NO_TEMPLATE_OPS and "template" not in entry:
            missing.add("template")
        if missing:
            eid = entry.get("id", f"managed_regions[{i}]")
            errors.append(f"managed_regions entry {eid!r} missing required fields: {sorted(missing)}")

    for i, entry in enumerate(data.get("ensured_files", [])):
        missing = _ENSURED_FILE_REQUIRED - set(entry.keys())
        if missing:
            eid = entry.get("id", f"ensured_files[{i}]")
            errors.append(f"ensured_files entry {eid!r} missing required fields: {sorted(missing)}")

    for i, entry in enumerate(data.get("ensured_gitignore", [])):
        missing = _ENSURED_GITIGNORE_REQUIRED - set(entry.keys())
        if missing:
            errors.append(
                f"ensured_gitignore[{i}] missing required fields: {sorted(missing)}"
            )

    for i, entry in enumerate(data.get("ensured_mcp_servers", [])):
        missing = _ENSURED_MCP_REQUIRED - set(entry.keys())
        if missing:
            eid = entry.get("id", f"ensured_mcp_servers[{i}]")
            errors.append(f"ensured_mcp_servers entry {eid!r} missing required fields: {sorted(missing)}")


def _check_op_registry(data: dict, errors: list[str]) -> None:
    """Check 2: all op: values are in OP_REGISTRY."""
    for entry in data.get("managed_regions", []) + data.get("ensured_files", []):
        op = entry.get("op")
        if op and op not in OP_REGISTRY:
            eid = entry.get("id", repr(entry.get("op")))
            errors.append(f"entry {eid!r}: op type {op!r} not in OP_REGISTRY {sorted(OP_REGISTRY)}")


def _check_template_refs(data: dict, templates_dir: Path, errors: list[str]) -> None:
    """Check 3: all template: references resolve to real files under templates/."""
    for entry in data.get("managed_regions", []) + data.get("ensured_files", []):
        tmpl = entry.get("template")
        if not tmpl:
            continue
        path = templates_dir / tmpl
        if not path.exists():
            eid = entry.get("id", repr(tmpl))
            errors.append(f"entry {eid!r}: template {tmpl!r} not found at {path}")


def _check_since_values(data: dict, changelog_text: str, errors: list[str]) -> None:
    """Check 4: all since: values appear in CHANGELOG.md."""
    all_entries = (
        data.get("managed_regions", [])
        + data.get("ensured_files", [])
        + data.get("ensured_gitignore", [])
        + data.get("ensured_mcp_servers", [])
    )
    seen: set[str] = set()
    for entry in all_entries:
        since = entry.get("since")
        if since and since not in seen:
            seen.add(since)
            # Accept "[1.13.0]" or "## [1.13.0]" forms
            if f"[{since}]" not in changelog_text:
                eid = entry.get("id", repr(since))
                errors.append(
                    f"entry {eid!r}: since {since!r} not found in CHANGELOG.md"
                )


def _check_routing_template_byte_equality(
    templates_dir: Path, ark_workflow_ref: Path, errors: list[str]
) -> None:
    """Check 5: templates/routing-template.md byte-equals the ark-workflow reference."""
    local = templates_dir / "routing-template.md"
    if not local.exists():
        errors.append("templates/routing-template.md does not exist")
        return
    if not ark_workflow_ref.exists():
        errors.append(f"ark-workflow reference not found at {ark_workflow_ref}")
        return
    if local.read_bytes() != ark_workflow_ref.read_bytes():
        errors.append(
            f"templates/routing-template.md differs from {ark_workflow_ref} "
            "(byte-equality drift; re-run: cp <ark-workflow-ref> templates/routing-template.md)"
        )


def _check_path_safety(data: dict, errors: list[str]) -> None:
    """Check 6 (codex P1-1): every file:/target: field is path-safe."""
    # Use a synthetic project root to test resolution. Any non-.. relative path is safe.
    synthetic_root = Path("/tmp/test-ark-update-path-safety")
    all_entries = data.get("managed_regions", []) + data.get("ensured_files", [])
    for entry in all_entries:
        for field in _PATH_FIELDS:
            val = entry.get(field)
            if val:
                err = _safe_resolve_check(synthetic_root, val)
                if err:
                    eid = entry.get("id", repr(val))
                    errors.append(f"entry {eid!r} field {field!r}: {err}")


def _check_migrations_schema(migrations_dir: Path, errors: list[str]) -> None:
    """Check 7 (codex P2-4): migrations/*.yaml accept failed_ops[] and depends_on_op.

    v1.0 has no destructive migrations, so this is a schema-acceptance check only:
    we verify the parser (yaml.safe_load) accepts these fields when present in any
    migration YAML files found. If none exist, the check passes trivially.
    """
    try:
        import yaml
    except ImportError:
        errors.append("PyYAML not installed; cannot check migrations schema (pip install pyyaml)")
        return

    if not migrations_dir.exists():
        return  # No migrations dir; check passes trivially.

    for yaml_path in sorted(migrations_dir.glob("*.yaml")):
        try:
            migration = yaml.safe_load(yaml_path.read_text())
        except Exception as exc:
            errors.append(f"migrations/{yaml_path.name}: YAML parse error: {exc}")
            continue
        if not isinstance(migration, dict):
            continue
        # Verify the parser round-trips failed_ops[] and depends_on_op if present.
        ops_list = migration.get("ops", [])
        for op_entry in (ops_list if isinstance(ops_list, list) else []):
            if not isinstance(op_entry, dict):
                continue
            # depends_on_op: optional string field — check it parses as a string if present
            doo = op_entry.get("depends_on_op")
            if doo is not None and not isinstance(doo, str):
                errors.append(
                    f"migrations/{yaml_path.name}: depends_on_op must be a string, "
                    f"got {type(doo).__name__!r}"
                )
        # failed_ops[]: optional list field at the run-log level (not op level)
        # In migration YAML files this would appear as a top-level key if added.
        failed = migration.get("failed_ops")
        if failed is not None and not isinstance(failed, list):
            errors.append(
                f"migrations/{yaml_path.name}: failed_ops must be a list, "
                f"got {type(failed).__name__!r}"
            )


def _check_mcp_sentinel_docs(data: dict, errors: list[str]) -> None:
    """Check 8: ensure_mcp_server entries should document _ark_managed sentinel.

    This is a documentation check — entries without a 'description' field that
    mentions _ark_managed are flagged as warnings (not errors). The sentinel is
    how the engine distinguishes ark-managed MCP servers from user-added ones.
    """
    for entry in data.get("ensured_mcp_servers", []):
        desc = entry.get("description", "")
        if "_ark_managed" not in desc:
            eid = entry.get("id", repr(entry))
            errors.append(
                f"ensured_mcp_servers entry {eid!r}: description should document "
                f"the _ark_managed sentinel so the engine can identify managed entries"
            )


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

def validate(
    profile_path: Path,
    templates_dir: Path,
    changelog_path: Path,
    ark_workflow_ref: Path,
    migrations_dir: Path,
) -> list[str]:
    """Run all checks. Return list of error strings (empty = valid)."""
    errors: list[str] = []

    # Load YAML
    try:
        import yaml
    except ImportError:
        return ["PyYAML not installed (pip install pyyaml)"]

    try:
        data = yaml.safe_load(profile_path.read_text())
    except Exception as exc:
        return [f"Failed to parse {profile_path}: {exc}"]

    if not isinstance(data, dict):
        return [f"{profile_path}: top level must be a YAML mapping, got {type(data).__name__}"]

    # Load CHANGELOG
    changelog_text = changelog_path.read_text() if changelog_path.exists() else ""
    if not changelog_text:
        errors.append(f"CHANGELOG.md not found or empty at {changelog_path}")

    _check_yaml_structure(data, errors)
    _check_op_registry(data, errors)
    _check_template_refs(data, templates_dir, errors)
    _check_since_values(data, changelog_text, errors)
    _check_routing_template_byte_equality(templates_dir, ark_workflow_ref, errors)
    _check_path_safety(data, errors)
    _check_migrations_schema(migrations_dir, errors)
    _check_mcp_sentinel_docs(data, errors)

    return errors


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate ark-update target-profile.yaml and templates/."
    )
    ap.add_argument(
        "--profile",
        type=Path,
        default=None,
        help="Path to target-profile.yaml (default: auto-discover from script location)",
    )
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repo root containing CHANGELOG.md (default: auto-discover)",
    )
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent  # skills/ark-update/

    profile_path = args.profile or (skill_dir / "target-profile.yaml")
    templates_dir = skill_dir / "templates"
    migrations_dir = skill_dir / "migrations"

    repo_root = args.repo_root or _find_repo_root(skill_dir)
    changelog_path = repo_root / "CHANGELOG.md"
    ark_workflow_ref = repo_root / "skills" / "ark-workflow" / "references" / "routing-template.md"

    errors = validate(
        profile_path=profile_path,
        templates_dir=templates_dir,
        changelog_path=changelog_path,
        ark_workflow_ref=ark_workflow_ref,
        migrations_dir=migrations_dir,
    )

    if errors:
        for e in errors:
            sys.stderr.write(f"ERROR: {e}\n")
        return 1

    print(f"OK: target-profile.yaml valid ({profile_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
