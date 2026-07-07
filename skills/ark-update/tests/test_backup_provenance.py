"""Tests for backup-provenance helpers in state.py (issue #34).

The okf-conversion and gh-issues-adoption migration ops can overwrite
plugin-owned / convention files that already exist and differ from the target.
When they do, they MUST leave a ``.bak`` copy plus a ``.meta.json`` sidecar
recording a ``pre_hash`` of the pre-overwrite bytes, so an operator can verify
and roll back. These tests pin the shared helper the ops use.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from state import write_backup_with_sidecar, verify_backup  # noqa: E402


def test_backup_creates_bak_and_sidecar(tmp_path):
    backups_dir = tmp_path / ".ark" / "backups"
    backups_dir.mkdir(parents=True)
    target = tmp_path / "CLAUDE.md"
    original = b"# original bytes\nrow: stale\n"
    target.write_bytes(original)

    info = write_backup_with_sidecar(backups_dir, target)

    bak_path = Path(info["bak_path"])
    meta_path = Path(info["meta_path"])
    assert bak_path.exists()
    assert meta_path.exists()
    # The .bak is a byte-exact copy of the pre-overwrite content.
    assert bak_path.read_bytes() == original
    # pre_hash is the sha256 of the pre-overwrite bytes.
    expected_hash = hashlib.sha256(original).hexdigest()
    assert info["pre_hash"] == expected_hash

    meta = json.loads(meta_path.read_text())
    assert meta["pre_hash"] == expected_hash
    assert meta["original_path"].endswith("CLAUDE.md")
    assert "backed_up_at" in meta
    assert meta["bak_path"].endswith(".bak")


def test_verify_backup_true_when_intact(tmp_path):
    backups_dir = tmp_path / ".ark" / "backups"
    backups_dir.mkdir(parents=True)
    target = tmp_path / "file.md"
    target.write_bytes(b"content to back up\n")

    info = write_backup_with_sidecar(backups_dir, target)
    assert verify_backup(Path(info["meta_path"])) is True


def test_verify_backup_false_when_tampered(tmp_path):
    backups_dir = tmp_path / ".ark" / "backups"
    backups_dir.mkdir(parents=True)
    target = tmp_path / "file.md"
    target.write_bytes(b"content to back up\n")

    info = write_backup_with_sidecar(backups_dir, target)
    # Tamper with the .bak copy — pre_hash no longer matches.
    Path(info["bak_path"]).write_bytes(b"tampered\n")
    assert verify_backup(Path(info["meta_path"])) is False


def test_sidecar_meta_alongside_bak(tmp_path):
    """The sidecar path is <bak>.meta.json so it travels with its backup."""
    backups_dir = tmp_path / ".ark" / "backups"
    backups_dir.mkdir(parents=True)
    target = tmp_path / "x.md"
    target.write_bytes(b"abc\n")
    info = write_backup_with_sidecar(backups_dir, target)
    assert Path(info["meta_path"]).name == Path(info["bak_path"]).name + ".meta.json"
