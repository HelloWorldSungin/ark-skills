"""Tests for ops/okf_conversion.py — the okf-conversion migration op (issue #34).

Exercises the OKF-playbook 7-step recipe end-to-end against a minimal real
vault, using the plugin's own OKF tooling (copied from the real skills_root).

Scenarios (issue "what done looks like"):
  * fresh non-OKF vault           -> converts, status "applied"
  * already-converted vault       -> status "skipped_idempotent", zero writes
  * second run is byte-identical  -> idempotency
  * no vault directory            -> status "skipped_precondition"
  * dry_run writes nothing
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from ops import DESTRUCTIVE_OP_REGISTRY  # noqa: E402
from ops.okf_conversion import OKFConversionOp  # noqa: E402

# Real ark-skills repo root — has vault/_meta/okf tooling + generate-index.py.
_SKILLS_ROOT = Path(__file__).resolve().parents[3]


def _op() -> OKFConversionOp:
    return OKFConversionOp()


def _args(**overrides) -> dict:
    base = {
        "id": "okf-conversion",
        "op": "okf_conversion",
        "since": "2.0.0",
        "vault": "vault",
        "skills_root": str(_SKILLS_ROOT),
    }
    base.update(overrides)
    return base


def _make_non_okf_vault(project_root: Path) -> Path:
    """Build a minimal non-OKF vault: frontmatter pages + wikilinks + a session log."""
    vault = project_root / "vault"
    (vault / "Research").mkdir(parents=True)
    (vault / "Session-Logs").mkdir(parents=True)

    (vault / "00-Home.md").write_text(
        "---\ntype: moc\ndescription: Home navigation\n---\n\n"
        "# Home\n\nSee [[Alpha-Study]] for details.\n",
        encoding="utf-8",
    )
    (vault / "Research" / "Alpha-Study.md").write_text(
        "---\ntype: research\ndescription: A study of alpha\n---\n\n"
        "# Alpha Study\n\nBack to [[00-Home]].\n",
        encoding="utf-8",
    )
    (vault / "Session-Logs" / "S001-Kickoff.md").write_text(
        "---\ntype: session\ndescription: Kickoff session\n---\n\n"
        "# S001 Kickoff\n\nWork happened.\n",
        encoding="utf-8",
    )
    return vault


def _snapshot(root: Path, exclude=(".ark",)) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and not any(part in exclude for part in f.relative_to(root).parts):
            snap[str(f.relative_to(root))] = f.read_bytes()
    return snap


def test_apply_converts_fresh_vault(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".ark" / "backups").mkdir(parents=True)
    vault = _make_non_okf_vault(project_root)

    result = _op().apply(project_root, _args())

    assert result["status"] == "applied", result
    # OKF tooling seeded into the project's vault.
    assert (vault / "_meta" / "okf" / "okf_lint.py").exists()
    # Root index.md declares okf_version.
    index_text = (vault / "index.md").read_text(encoding="utf-8")
    assert "okf_version" in index_text
    # log.md mirror exists.
    assert (vault / "log.md").exists()
    # Session-Logs frozen with a banner.
    frozen = list((vault / "Session-Logs").glob("*.md"))
    assert any("FROZEN" in p.read_text(encoding="utf-8") for p in frozen)
    # backups key present (list).
    assert isinstance(result.get("backups", []), list)


def test_apply_idempotent_second_run(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".ark" / "backups").mkdir(parents=True)
    _make_non_okf_vault(project_root)

    first = _op().apply(project_root, _args())
    assert first["status"] == "applied"
    snap_after_first = _snapshot(project_root)

    second = _op().apply(project_root, _args())
    assert second["status"] == "skipped_idempotent", second
    snap_after_second = _snapshot(project_root)

    assert snap_after_first == snap_after_second, (
        "Second okf-conversion run mutated the tree — not idempotent"
    )


def test_apply_skips_when_no_vault(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".ark" / "backups").mkdir(parents=True)

    result = _op().apply(project_root, _args())
    assert result["status"] == "skipped_precondition", result


def test_dry_run_writes_nothing(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    _make_non_okf_vault(project_root)
    snap_before = _snapshot(project_root)

    report = _op().dry_run(project_root, _args())
    assert report["would_apply"] is True
    assert report["would_skip_idempotent"] is False

    snap_after = _snapshot(project_root)
    assert snap_before == snap_after, "dry_run mutated the tree"


def test_dry_run_skip_when_no_vault(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    report = _op().dry_run(project_root, _args())
    assert report["would_apply"] is False
    assert report["would_fail_precondition"] is True


def test_op_registered():
    assert "okf_conversion" in DESTRUCTIVE_OP_REGISTRY
    assert DESTRUCTIVE_OP_REGISTRY["okf_conversion"] is OKFConversionOp
