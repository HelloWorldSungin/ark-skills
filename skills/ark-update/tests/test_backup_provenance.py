"""Tests: each backup has a .meta.json sidecar with provenance fields.

When the engine detects drift and creates a backup, it must also write a
sidecar at ``<backup_path>.meta.json`` containing:
  {
    "op": "<op_type>",
    "region_id": "<region_id>",
    "run_id": "<uuid>",
    "pre_hash": "<sha256 of pre-overwrite bytes>",
    "reason": "<drift_summary>"
  }

This enables audit trails and pre-mortem mitigation 1.1 verification:
the backup bytes must be byte-equal to the pre-overwrite file content,
which we can verify by hashing the backup and comparing to meta.pre_hash.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_SCRIPTS_DIR = _TESTS_DIR.parent / "scripts"
_SKILLS_ROOT = _TESTS_DIR.parent.parent.parent


def _run_engine(project_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPTS_DIR / "migrate.py"),
            "--project-root", str(project_root),
            "--skills-root", str(_SKILLS_ROOT),
            "--force",
        ],
        capture_output=True,
        text=True,
    )


def _copy_fixture_pre(fixture_name: str, dest: Path) -> None:
    src = _FIXTURES_DIR / fixture_name
    for item in src.iterdir():
        if item.name == "expected-post":
            continue
        d = dest / item.name
        if item.is_dir():
            shutil.copytree(item, d)
        else:
            shutil.copy2(item, d)


def test_backup_has_meta_sidecar(tmp_path: Path) -> None:
    """Each .bak file must have a corresponding .bak.meta.json sidecar."""
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0

    backups_dir = tmp_path / ".ark" / "backups"
    assert backups_dir.exists(), "backups/ dir must exist after drift run"

    bak_files = list(backups_dir.glob("*.bak"))
    assert bak_files, "Expected at least one .bak file"

    for bak in bak_files:
        meta_path = Path(str(bak) + ".meta.json")
        assert meta_path.exists(), (
            f"Missing .meta.json sidecar for {bak.name}"
        )


def test_backup_meta_schema(tmp_path: Path) -> None:
    """Each .meta.json sidecar must contain the required provenance fields."""
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0

    backups_dir = tmp_path / ".ark" / "backups"
    bak_files = list(backups_dir.glob("*.bak"))
    assert bak_files

    for bak in bak_files:
        meta_path = Path(str(bak) + ".meta.json")
        assert meta_path.exists(), f"Missing .meta.json for {bak.name}"

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        required = {"op", "region_id", "run_id", "pre_hash", "reason"}
        missing = required - set(meta.keys())
        assert not missing, (
            f"{bak.name}.meta.json missing fields: {sorted(missing)}"
        )

        # Validate types.
        assert isinstance(meta["op"], str) and meta["op"], "op must be non-empty str"
        assert isinstance(meta["region_id"], str) and meta["region_id"], "region_id must be non-empty str"
        assert isinstance(meta["run_id"], str), "run_id must be a str"
        assert isinstance(meta["pre_hash"], str) and len(meta["pre_hash"]) == 64, (
            f"pre_hash must be a 64-char hex string: {meta['pre_hash']!r}"
        )
        assert isinstance(meta["reason"], str) and meta["reason"], "reason must be non-empty str"

        # Validate run_id is UUID-shaped.
        try:
            uuid.UUID(meta["run_id"])
        except ValueError:
            pytest.fail(f"run_id is not a valid UUID: {meta['run_id']!r}")


def test_backup_bytes_match_pre_hash(tmp_path: Path) -> None:
    """Backup bytes must hash to meta.pre_hash (pre-mortem mitigation 1.1).

    This verifies that backup bytes are byte-equal to the pre-overwrite file
    content, not a post-overwrite snapshot.
    """
    _copy_fixture_pre("drift-inside-markers", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0

    backups_dir = tmp_path / ".ark" / "backups"
    bak_files = list(backups_dir.glob("*.bak"))
    assert bak_files

    for bak in bak_files:
        meta_path = Path(str(bak) + ".meta.json")
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        bak_bytes = bak.read_bytes()
        actual_hash = hashlib.sha256(bak_bytes).hexdigest()
        assert actual_hash == meta["pre_hash"], (
            f"{bak.name}: backup hash {actual_hash!r} != meta.pre_hash {meta['pre_hash']!r}. "
            f"Backup bytes do NOT match pre-overwrite content (pre-mortem mitigation 1.1)."
        )


def test_no_backup_on_idempotent_run(tmp_path: Path) -> None:
    """Idempotent run must not create any backup files."""
    _copy_fixture_pre("healthy-current", tmp_path)
    result = _run_engine(tmp_path)
    assert result.returncode == 0

    backups_dir = tmp_path / ".ark" / "backups"
    if backups_dir.exists():
        bak_files = list(backups_dir.glob("*.bak"))
        assert not bak_files, (
            f"Unexpected .bak files on idempotent run: {bak_files}"
        )


def test_stale_version_drift_creates_backup(tmp_path: Path) -> None:
    """P2-3: stale version= in marker must trigger backup even when content is identical.

    The drift-inside-markers fixture contains a routing-rules region with
    version=1.11.0 (stale) but byte-identical content. Engine must backup and
    re-stamp with the target version.
    """
    _copy_fixture_pre("drift-inside-markers", tmp_path)

    # Record pre-overwrite bytes of CLAUDE.md.
    claude_before = (tmp_path / "CLAUDE.md").read_bytes()

    result = _run_engine(tmp_path)
    assert result.returncode == 0
    assert "drift-overwritten" in result.stdout

    backups_dir = tmp_path / ".ark" / "backups"
    bak_files = list(backups_dir.glob("*.bak"))
    assert bak_files, "Expected backup for stale-version drift (P2-3)"

    # At least one backup must have pre_hash matching the pre-overwrite bytes.
    expected_hash = hashlib.sha256(claude_before).hexdigest()
    matching = [
        bak for bak in bak_files
        if (meta_path := Path(str(bak) + ".meta.json")).exists()
        and json.loads(meta_path.read_text())["pre_hash"] == expected_hash
    ]
    assert matching, (
        f"No backup's pre_hash matches the pre-overwrite CLAUDE.md hash {expected_hash!r}. "
        f"Stale-version drift must create a provenance-correct backup (P2-3 + P1-1)."
    )
