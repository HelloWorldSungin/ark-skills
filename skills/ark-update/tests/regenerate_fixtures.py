"""Regenerate stale fixture expected-post/ (and some pre-state) files.

Background
----------
Commit 547cc34 bumped target-profile.yaml routing-rules to version 1.17.0 and
added the "Session habits" subsection to templates/routing-template.md. The
test fixtures under tests/fixtures/*/ were not regenerated, so every
convergence test that expects "idempotent / clean" run now sees legitimate
drift and fails.

Semantic groups
---------------
Group A (pre-state preserved, regenerate expected-post only):
    pre-v1.11, pre-v1.12, pre-v1.13, fresh, drift-inside-markers
      Pre-state represents an older, fresh, or drifted project.  After engine
      runs, expected-post must reflect current target.

Group B (also rewrite pre-state; fixture represents "at current target"):
    healthy-current     — pre == post, both must match current target byte-exact.
    drift-outside-markers — inside-markers must match current target byte-exact;
                             outside-markers content preserved as-is.

Usage
-----
    python3 regenerate_fixtures.py --dry-run     # print planned writes, no file changes
    python3 regenerate_fixtures.py --apply       # write the changes
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent

GROUP_A = ["pre-v1.11", "pre-v1.12", "pre-v1.13", "fresh", "drift-inside-markers"]
GROUP_B = ["healthy-current", "drift-outside-markers"]


def _copy_pre(fixture_name: str, dest: Path) -> None:
    src = _FIXTURES_DIR / fixture_name
    for item in src.iterdir():
        if item.name == "expected-post":
            continue
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d)
        else:
            shutil.copy2(item, d)


def _run_engine(project_root: Path) -> None:
    cmd = [
        sys.executable,
        str(_SCRIPTS_DIR / "migrate.py"),
        "--project-root", str(project_root),
        "--skills-root", str(_SKILLS_ROOT),
        "--force",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Engine failed for {project_root}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def _snapshot(root: Path, skip_prefixes: tuple[str, ...] = (".ark",)) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if rel.parts and rel.parts[0] in skip_prefixes:
            continue
        snap[str(rel)] = f.read_bytes()
    return snap


def _write_snapshot(snap: dict[str, bytes], dest: Path, dry_run: bool) -> list[str]:
    changes: list[str] = []
    for rel, content in snap.items():
        target = dest / rel
        if target.exists() and target.read_bytes() == content:
            continue
        changes.append(f"  write {target.relative_to(_FIXTURES_DIR)} ({len(content)} bytes)")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    existing = {
        str(p.relative_to(dest))
        for p in dest.rglob("*")
        if p.is_file()
    }
    stale = existing - set(snap.keys())
    for rel in sorted(stale):
        changes.append(f"  DELETE {(dest / rel).relative_to(_FIXTURES_DIR)}")
        if not dry_run:
            (dest / rel).unlink()
    return changes


def regenerate_group_a(fixture_name: str, dry_run: bool) -> list[str]:
    """Run engine on pre-state; overwrite expected-post/ with result."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _copy_pre(fixture_name, tmp_path)
        _run_engine(tmp_path)
        new_post = _snapshot(tmp_path)
    dest = _FIXTURES_DIR / fixture_name / "expected-post"
    dest.mkdir(exist_ok=True)
    changes = _write_snapshot(new_post, dest, dry_run)
    return changes


def regenerate_group_b(fixture_name: str, dry_run: bool) -> list[str]:
    """Run engine on pre-state; use result as BOTH pre and expected-post."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _copy_pre(fixture_name, tmp_path)
        _run_engine(tmp_path)
        new_state = _snapshot(tmp_path)

    fixture_root = _FIXTURES_DIR / fixture_name
    post_root = fixture_root / "expected-post"
    post_root.mkdir(exist_ok=True)

    changes: list[str] = []
    changes.append(f"# pre-state:")
    pre_snap = {
        str(p.relative_to(fixture_root)): p.read_bytes()
        for p in fixture_root.rglob("*")
        if p.is_file() and "expected-post" not in p.parts
    }

    pre_changes: list[str] = []
    for rel, content in new_state.items():
        target = fixture_root / rel
        if str(rel) in pre_snap and pre_snap[str(rel)] == content:
            continue
        pre_changes.append(f"  write {target.relative_to(_FIXTURES_DIR)} ({len(content)} bytes)")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    stale_pre = set(pre_snap.keys()) - set(new_state.keys())
    for rel in sorted(stale_pre):
        pre_changes.append(f"  DELETE {(fixture_root / rel).relative_to(_FIXTURES_DIR)}")
        if not dry_run:
            (fixture_root / rel).unlink()

    if pre_changes:
        changes.extend(pre_changes)
    else:
        changes.append("  (no pre-state changes)")

    changes.append(f"# expected-post:")
    post_changes = _write_snapshot(new_state, post_root, dry_run)
    if post_changes:
        changes.extend(post_changes)
    else:
        changes.append("  (no expected-post changes)")

    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dry_run = args.dry_run

    print(f"{'DRY-RUN' if dry_run else 'APPLYING'} fixture regeneration\n")

    for name in GROUP_A:
        print(f"== Group A: {name} ==")
        for line in regenerate_group_a(name, dry_run):
            print(line)
        print()

    for name in GROUP_B:
        print(f"== Group B: {name} ==")
        for line in regenerate_group_b(name, dry_run):
            print(line)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
