"""ark-update engine entry point.

Usage::

    python3 migrate.py --project-root <path> [--dry-run] [--force] \\
                       [--skills-root <path>]

Exit codes
----------
0  Clean run — either work was applied successfully, or nothing to do.
1  Unexpected error (exception, I/O failure, lock held by another process).
2  Dirty working tree — project has uncommitted changes; pass --force to override.
3  Path traversal refusal — a target-profile file path escapes the project root.
4  Malformed state refusal — .ark/migrations-applied.jsonl is unparseable;
   run /ark-onboard repair to fix.

ARK_SKILLS_ROOT resolution (three-case pattern from ark-context-warmup)
-----------------------------------------------------------------------
1. ``--skills-root <path>`` CLI flag (highest priority).
2. ``ARK_SKILLS_ROOT`` environment variable.
3. If neither is set, fail loud with a user-facing message.

Path safety (codex P1-1 — defense in depth)
--------------------------------------------
At load time, every file path declared in the target profile is passed through
``paths.safe_resolve(project_root, ...)`` BEFORE any phase runs.  On
``PathTraversalError``, the engine refuses with exit code 3 and a message
pointing to ``/ark-onboard repair``.

Clean-run short-circuit (codex P1-2)
-------------------------------------
If Phase 1 had zero pending migrations AND Phase 2 ops all returned
``skipped_idempotent``, no log entry is appended and no pointer is rewritten.
The engine prints a "clean — nothing to do" summary and exits 0.

depends_on_op skip-cascade (spec amendment)
--------------------------------------------
If a destructive op fails (appears in ``failed_ops[]``), subsequent ops in
the same migration whose ``depends_on_op`` field references the failed op id
are marked ``skipped_due_to_dependency`` and excluded from ``ops_ran``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path shim — allows bare "import paths" / "import state" etc.
# ---------------------------------------------------------------------------
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

try:
    import yaml  # type: ignore[import]
except ImportError:
    yaml = None  # type: ignore[assignment]

from markers import MarkerIntegrityError  # noqa: E402
from paths import PathTraversalError, safe_resolve  # noqa: E402
from state import (  # noqa: E402
    acquire_lock,
    bootstrap,
    computed_installed_version,
    maybe_append_log_and_pointer,
    read_log,
    release_lock,
    utc_now_iso,
)
from plan import build_plan, render_plan_report  # noqa: E402
from ops import OP_REGISTRY  # noqa: E402

# Import concrete op modules so their @register_op decorators fire and
# populate OP_REGISTRY before any phase runs.  Order matches declaration
# order in target-profile.yaml.
import ops.ensure_claude_md_section  # noqa: F401, E402
import ops.ensure_routing_rules_block  # noqa: F401, E402
import ops.ensure_gitignore_entry  # noqa: F401, E402
import ops.create_file_from_template  # noqa: F401, E402
import ops.ensure_mcp_server  # noqa: F401, E402


# ---------------------------------------------------------------------------
# Target-profile file-path keys that require safe_resolve (codex P1-1)
# ---------------------------------------------------------------------------
_PROFILE_PATH_KEYS = (
    # managed_regions entries
    "file",
    # ensured_files entries
    "target",
    # ensured_gitignore entries — gitignore entry is a pattern, not a file path;
    # the "file" key holds the .gitignore path itself when present.
    # ensured_mcp_servers entries
    # (no file key — server args may have paths but those are user-controlled)
)


# ---------------------------------------------------------------------------
# Skills-root resolution
# ---------------------------------------------------------------------------

def _resolve_skills_root(cli_flag: str | None) -> Path:
    """Resolve ARK_SKILLS_ROOT via (1) CLI flag, (2) env var.

    Raises SystemExit(1) if neither is set.
    """
    if cli_flag:
        p = Path(cli_flag).resolve()
        if not p.is_dir():
            _die(1, f"--skills-root {cli_flag!r} does not exist or is not a directory.")
        return p

    env = os.environ.get("ARK_SKILLS_ROOT")
    if env:
        p = Path(env).resolve()
        if not p.is_dir():
            _die(1, f"ARK_SKILLS_ROOT={env!r} does not exist or is not a directory.")
        return p

    _die(
        1,
        "Could not resolve ARK_SKILLS_ROOT. Pass --skills-root <path> or "
        "set the ARK_SKILLS_ROOT environment variable to the ark-skills plugin root.",
    )


# ---------------------------------------------------------------------------
# YAML / target-profile loading
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML file; return empty dict if file does not exist."""
    if not path.exists():
        return {}
    if yaml is None:
        # Fallback: attempt json (unlikely to be YAML-only) or empty.
        try:
            import json as _json
            return _json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            _die(1, f"PyYAML is not installed and {path} cannot be parsed as JSON. "
                 f"Install PyYAML: pip install pyyaml")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _load_target_profile(skills_root: Path) -> dict:
    """Load skills/ark-update/target-profile.yaml from skills_root."""
    profile_path = skills_root / "skills" / "ark-update" / "target-profile.yaml"
    return _load_yaml(profile_path)


def _load_pending_migrations(
    skills_root: Path,
    installed_version: str,
) -> list[dict]:
    """Load and filter destructive migration files.

    Scans ``skills/ark-update/migrations/*.yaml``, parses each, filters to
    semver > installed_version, sorts ascending.  Each YAML file may contain
    a top-level list of op dicts, or a dict with ``ops:`` key.

    Each op dict may have an optional ``depends_on_op: <op-id>`` field (spec
    amendment) — the parser preserves it in the returned dict for the engine's
    skip-cascade logic.
    """
    migrations_dir = skills_root / "skills" / "ark-update" / "migrations"
    if not migrations_dir.is_dir():
        return []

    try:
        from packaging.version import Version  # type: ignore[import]
    except ImportError:
        _die(1, "packaging library is required. Install: pip install packaging")

    installed_ver = Version(installed_version)
    pending: list[tuple] = []  # (Version, list[dict])

    for yaml_file in sorted(migrations_dir.glob("*.yaml")):
        raw = _load_yaml(yaml_file)
        if not raw:
            continue

        # Extract semver from filename: "v1.14.2.yaml" → "1.14.2"
        stem = yaml_file.stem  # e.g. "v1.14.2"
        semver_str = stem.lstrip("v")
        try:
            file_ver = Version(semver_str)
        except Exception:
            # Non-semver filename — skip.
            continue

        if file_ver <= installed_ver:
            continue

        # Normalize: accept top-level list or {"ops": [...]}
        if isinstance(raw, list):
            ops = raw
        elif isinstance(raw, dict):
            ops = raw.get("ops", [])
        else:
            ops = []

        # Ensure depends_on_op is preserved (spec amendment).
        normalized: list[dict] = []
        for op in ops:
            if not isinstance(op, dict):
                continue
            entry = dict(op)
            # depends_on_op is optional; keep as-is if present.
            normalized.append(entry)

        if normalized:
            pending.append((file_ver, normalized))

    # Sort by semver ascending.
    pending.sort(key=lambda t: t[0])

    # Flatten: all ops from all pending migration files, preserving order.
    result: list[dict] = []
    for _ver, ops in pending:
        result.extend(ops)
    return result


# ---------------------------------------------------------------------------
# Path safety gate (codex P1-1)
# ---------------------------------------------------------------------------

def _validate_target_profile_paths(project_root: Path, target_profile: dict) -> None:
    """Iterate all file-path fields in target_profile and call safe_resolve.

    On PathTraversalError, prints a user-facing message and exits with code 3.
    """
    sections = {
        "managed_regions": ["file"],
        "ensured_files": ["target"],
        "ensured_gitignore": ["file"],
        "ensured_mcp_servers": ["file"],
    }
    for section, keys in sections.items():
        for entry in target_profile.get(section, []):
            if not isinstance(entry, dict):
                continue
            for key in keys:
                value = entry.get(key)
                if value is None:
                    continue
                try:
                    safe_resolve(project_root, value)
                except PathTraversalError as exc:
                    _die(
                        3,
                        f"Path traversal detected in target-profile.yaml "
                        f"(section={section!r}, key={key!r}, value={value!r}):\n"
                        f"  {exc}\n"
                        f"This may indicate a tampered target-profile.yaml. "
                        f"Run /ark-onboard repair or inspect the file manually.",
                    )


# ---------------------------------------------------------------------------
# Git dirty-tree check
# ---------------------------------------------------------------------------

def _check_git_clean(project_root: Path, force: bool) -> None:
    """Refuse to run on a dirty working tree unless --force is passed."""
    if force:
        return
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # git not available or timed out — skip check.
        return

    if result.returncode != 0:
        # Not a git repo — skip check.
        return

    if result.stdout.strip():
        _die(
            2,
            f"Working tree at {project_root} has uncommitted changes.\n"
            f"Commit or stash your changes before running /ark-update, "
            f"or pass --force to override (not recommended).\n\n"
            f"Dirty files:\n{result.stdout.rstrip()}",
        )


# ---------------------------------------------------------------------------
# .ark/ gitignored check (pre-mortem Scenario 3 mitigation)
# ---------------------------------------------------------------------------

def _check_ark_not_gitignored(project_root: Path) -> None:
    """Refuse to run when ``.ark/`` is listed in .gitignore.

    If ``.ark/`` is gitignored, migration log and pointer are excluded from
    source control — subsequent clones and worktrees start from ``0.0.0``
    and will re-apply all migrations, potentially corrupting state.

    The check reads ``.gitignore`` at *project_root* level only (not nested
    .gitignore files or global gitignore).  If ``.gitignore`` doesn't exist
    the check passes silently.
    """
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        # Match ".ark/" and ".ark" patterns
        if stripped in (".ark/", ".ark"):
            _die(
                1,
                f".ark/ is listed in {gitignore} (pattern: {stripped!r}).\n"
                f"The .ark/ directory must be committed to source control so\n"
                f"migration state is shared across clones and worktrees.\n"
                f"Remove the pattern from .gitignore, commit the change, then\n"
                f"re-run /ark-update.",
            )


# ---------------------------------------------------------------------------
# Phase 1: destructive migrations
# ---------------------------------------------------------------------------

def _run_phase_1(
    pending_migrations: list[dict],
    project_root: Path,
    log_path: Path,
    pointer_path: Path,
    skills_root: Path,
) -> tuple[list[dict], list[dict]]:
    """Apply pending destructive migrations in semver order.

    Returns (ops_ran_list, failed_ops_list).

    In v1.0, pending_migrations is always empty.  The machinery is wired for
    future destructive migrations.

    skip-cascade: if an op fails, subsequent ops with ``depends_on_op`` pointing
    to the failed op id are skipped and recorded as ``skipped_due_to_dependency``.
    """
    ops_ran: list[dict] = []
    failed_ops: list[dict] = []
    failed_ids: set[str] = set()

    for migration_op in pending_migrations:
        op_id = migration_op.get("op_id", "unknown")
        op_type = migration_op.get("op_type", "unknown")
        depends_on = migration_op.get("depends_on_op")

        # Skip-cascade check.
        if depends_on and depends_on in failed_ids:
            ops_ran.append({
                "op_id": op_id,
                "op_type": op_type,
                "status": "skipped_due_to_dependency",
                "depends_on_op": depends_on,
            })
            continue

        # No destructive op classes in v1.0 — log as unregistered failure.
        failed_ids.add(op_id)
        failed_ops.append({
            "op_id": op_id,
            "op_type": op_type,
            "error": f"destructive op type {op_type!r} has no registered class in v1.0",
        })

    return ops_ran, failed_ops


# ---------------------------------------------------------------------------
# Phase 2: target-profile convergence
# ---------------------------------------------------------------------------

def _run_phase_2(
    target_profile: dict,
    project_root: Path,
    skills_root: Path,
) -> tuple[list[dict], list[dict]]:
    """Converge project to target profile, invoking each op's apply().

    Returns (apply_results_list, failed_ops_list).

    In v1.0 Step 2, OP_REGISTRY is empty so every entry returns a stub result.
    Step 3 fills the registry and this function automatically dispatches to
    concrete op classes.
    """
    apply_results: list[dict] = []
    failed_ops: list[dict] = []

    for entry in _iter_target_profile_entries(target_profile):
        op_type = entry.get("op", "unknown")
        op_id = entry.get("id", entry.get("target", op_type))
        args = dict(entry)
        args["skills_root"] = str(skills_root)

        cls = OP_REGISTRY.get(op_type)
        if cls is None:
            # Not yet registered — skip cleanly (Step 3 will fill this).
            apply_results.append({
                "op_id": op_id,
                "op_type": op_type,
                "status": "skipped_idempotent",
                "_note": f"op type {op_type!r} not yet registered",
            })
            continue

        instance = cls()
        try:
            result = instance.apply(project_root, args)
            apply_results.append(dict(result))
            if result.get("status") == "failed":
                failed_ops.append({
                    "op_id": op_id,
                    "op_type": op_type,
                    "error": result.get("error", "unknown error"),
                })
        except MarkerIntegrityError as exc:
            # Hard refusal: corrupted marker structure.  The engine cannot
            # safely overwrite or insert regions when markers are malformed.
            # Exit 1 and point user to /ark-onboard repair.
            _die(
                1,
                f"Marker integrity error in {op_id!r} ({op_type}):\n"
                f"  {exc}\n"
                f"The file has corrupted ark markers. Run /ark-onboard repair "
                f"to restore a valid state, then retry /ark-update.",
            )
        except Exception as exc:  # noqa: BLE001
            apply_results.append({
                "op_id": op_id,
                "op_type": op_type,
                "status": "failed",
                "error": str(exc),
            })
            failed_ops.append({
                "op_id": op_id,
                "op_type": op_type,
                "error": str(exc),
            })

    return apply_results, failed_ops


def _iter_target_profile_entries(target_profile: dict):
    """Yield all op-entry dicts from target_profile in declaration order.

    Injects ``op`` key for sections whose entries don't carry an explicit ``op``
    field (e.g. ``ensured_gitignore`` uses ``entry`` + implicit op type).
    """
    _IMPLICIT_OPS = {
        "ensured_gitignore": "ensure_gitignore_entry",
        "ensured_mcp_servers": "ensure_mcp_server",
    }
    for section_key in ("managed_regions", "ensured_files", "ensured_gitignore", "ensured_mcp_servers"):
        implicit_op = _IMPLICIT_OPS.get(section_key)
        for entry in target_profile.get(section_key, []):
            if implicit_op and not entry.get("op"):
                entry = dict(entry)
                entry["op"] = implicit_op
            yield entry


# ---------------------------------------------------------------------------
# Summary rendering
# ---------------------------------------------------------------------------

def _render_summary(
    p1_results: list[dict],
    p1_failed: list[dict],
    p2_results: list[dict],
    p2_failed: list[dict],
    was_clean: bool,
) -> str:
    lines = ["ark-update run summary", "======================"]

    if was_clean:
        lines.append("clean — nothing to do (all ops idempotent, no pending migrations)")
        return "\n".join(lines)

    p1_ran = len([r for r in p1_results if r.get("status") not in ("skipped_due_to_dependency",)])
    p2_ran = len([r for r in p2_results if r.get("status") == "applied"])
    p2_drift = len([r for r in p2_results if r.get("status") == "drifted_overwritten"])
    p2_skip = len([r for r in p2_results if r.get("status") == "skipped_idempotent"])

    lines.append(f"Phase 1 (destructive migrations): {p1_ran} applied, {len(p1_failed)} failed")
    lines.append(f"Phase 2 (convergence): {p2_ran} applied, {p2_drift} drift-overwritten, {p2_skip} skipped, {len(p2_failed)} failed")

    if p2_drift:
        lines.append("")
        lines.append("Drift events:")
        for r in p2_results:
            if r.get("status") == "drifted_overwritten":
                backup = r.get("backup_path", "?")
                lines.append(f"  drift: {r.get('op_id')} (backup: {backup})")

    total_failed = len(p1_failed) + len(p2_failed)
    if total_failed:
        lines.append("")
        lines.append("Failures:")
        for f in p1_failed + p2_failed:
            lines.append(f"  FAIL: {f.get('op_id')} ({f.get('op_type')}): {f.get('error')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _die(code: int, message: str) -> None:
    print(f"ark-update: {message}", file=sys.stderr)
    sys.exit(code)


def _plugin_version(skills_root: Path) -> str:
    """Read VERSION from skills_root; return '0.0.0' if missing."""
    version_file = skills_root / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="migrate.py",
        description="ark-update engine: replay destructive migrations then converge to target profile.",
    )
    parser.add_argument(
        "--project-root",
        required=True,
        help="Absolute path to the project root (the directory containing CLAUDE.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without writing anything.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the dirty-working-tree check.",
    )
    parser.add_argument(
        "--skills-root",
        default=None,
        help="Path to the ark-skills plugin root. Falls back to ARK_SKILLS_ROOT env var.",
    )

    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        project_root.mkdir(parents=True, exist_ok=True)

    # 1. Resolve skills_root.
    skills_root = _resolve_skills_root(args.skills_root)

    # 2. Git dirty-tree check.
    _check_git_clean(project_root, args.force)

    # 2b. Refuse if .ark/ is gitignored (pre-mortem Scenario 3 mitigation).
    _check_ark_not_gitignored(project_root)

    # 3. Acquire advisory lock.
    ark_dir = project_root / ".ark"
    lock_path = ark_dir / "lock"
    # Bootstrap first so ark_dir exists for the lock.
    ark_dir.mkdir(parents=True, exist_ok=True)

    try:
        acquire_lock(lock_path)
    except RuntimeError as exc:
        _die(1, str(exc))

    try:
        _run(project_root, skills_root, args.dry_run, args.force, ark_dir)
    finally:
        release_lock(lock_path)


def _run(
    project_root: Path,
    skills_root: Path,
    dry_run: bool,
    force: bool,
    ark_dir: Path,
) -> None:
    log_path = ark_dir / "migrations-applied.jsonl"
    pointer_path = ark_dir / "plugin-version"

    # 4. Bootstrap .ark/ and read state.
    try:
        installed_version = bootstrap(ark_dir)
        log_entries = read_log(log_path)
        installed_version = computed_installed_version(log_entries) if log_entries else installed_version
    except ValueError as exc:
        _die(
            4,
            f"Malformed .ark/migrations-applied.jsonl: {exc}\n"
            f"Run /ark-onboard repair to restore a valid .ark/ directory.",
        )

    # 5. Load target profile and pending migrations.
    target_profile = _load_target_profile(skills_root)
    try:
        pending_migrations = _load_pending_migrations(skills_root, installed_version)
    except Exception as exc:  # noqa: BLE001
        _die(1, f"Failed to load pending migrations: {exc}")

    # 6. Path safety gate (codex P1-1): validate all file paths in target profile.
    _validate_target_profile_paths(project_root, target_profile)

    # 7. Dry-run path: build plan, print JSON, exit 0.
    if dry_run:
        plan = build_plan(target_profile, pending_migrations, project_root)
        print(render_plan_report(plan))
        print()
        print(json.dumps(plan, sort_keys=True, indent=2))
        sys.exit(0)

    # 8. Phase 1: destructive migrations.
    p1_results, p1_failed = _run_phase_1(
        pending_migrations, project_root, log_path, pointer_path, skills_root
    )

    # Append Phase 1 log if there was any work.
    plugin_ver = _plugin_version(skills_root)
    if pending_migrations:
        p1_ops_ran = len([r for r in p1_results if r.get("status") not in ("skipped_due_to_dependency",)])
        p1_entry = {
            "version": plugin_ver,
            "applied_at": utc_now_iso(),
            "ops_ran": p1_ops_ran,
            "ops_skipped": len([r for r in p1_results if r.get("status") == "skipped_due_to_dependency"]),
            "failed_ops": p1_failed,
            "result": "partial" if p1_failed else "clean",
            "phase": "destructive",
        }
        maybe_append_log_and_pointer(log_path, pointer_path, p1_entry, plugin_ver)

    # 9. Phase 2: target-profile convergence.
    p2_results, p2_failed = _run_phase_2(target_profile, project_root, skills_root)

    # 10. Clean-run short-circuit (codex P1-2).
    p2_ops_ran = len([r for r in p2_results if r.get("status") == "applied"])
    p2_drift_ran = len([r for r in p2_results if r.get("status") == "drifted_overwritten"])
    p2_total_work = p2_ops_ran + p2_drift_ran + len(p2_failed)
    no_pending = len(pending_migrations) == 0
    all_idempotent = p2_total_work == 0

    was_clean = no_pending and all_idempotent

    if not was_clean:
        p2_skipped = len([r for r in p2_results if r.get("status") == "skipped_idempotent"])
        p2_entry = {
            "version": plugin_ver,
            "applied_at": utc_now_iso(),
            "ops_ran": p2_ops_ran + p2_drift_ran,
            "ops_skipped": p2_skipped,
            "failed_ops": p2_failed,
            "result": "partial" if p2_failed else "clean",
            "phase": "convergence",
        }
        maybe_append_log_and_pointer(log_path, pointer_path, p2_entry, plugin_ver)

    # 11. Print summary.
    summary = _render_summary(p1_results, p1_failed, p2_results, p2_failed, was_clean)
    print(summary)


if __name__ == "__main__":
    main()
