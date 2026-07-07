"""Op: okf_conversion — convert a project's vault into an OKF v0.1 bundle (#34).

Wraps the OKF playbook's 7-step recipe
(docs/playbooks/okf-knowledge-base.md) as an idempotent, dry-run-first
destructive migration:

  1. Seed the bundle tooling into ``vault/_meta/okf/`` (+ ``generate-index.py``)
     from the plugin's own bundle. Plugin-owned files: overwrite-on-drift **with**
     ``.bak`` + ``.meta.json`` provenance backups.
  2. ``normalize_frontmatter.py --apply``  (ensure type/tags/timestamp)
  3. ``convert_links.py --apply``          (wikilinks -> relative markdown)
  4. ``generate-index.py``                 (root index.md declares okf_version)
  5. ensure ``log.md`` exists              (the in-bundle work-record mirror)
  6. freeze ``Session-Logs/`` + ``TaskNotes/`` with banners
  7. verify ``okf_lint.py --quiet`` exits 0

Idempotency: a vault whose root ``index.md`` already declares ``okf_version``
and lints clean is already an OKF bundle -> ``skipped_idempotent`` with zero
writes. A project with no vault -> ``skipped_precondition``.
"""
from __future__ import annotations

import sys
from pathlib import Path

_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from ops import DestructiveOp, register_destructive_op  # noqa: E402
from ops._migration_helpers import freeze_legacy_trackers, run_tool  # noqa: E402
from state import write_backup_with_sidecar  # noqa: E402

# Bundle tooling copied into the project vault. Relative to a bundle root.
_OKF_TOOLS = (
    "_meta/okf/okf_lint.py",
    "_meta/okf/okf_cli.py",
    "_meta/okf/convert_links.py",
    "_meta/okf/normalize_frontmatter.py",
    "_meta/generate-index.py",
)


def _has_okf_version(index_md: Path) -> bool:
    if not index_md.exists():
        return False
    text = index_md.read_text(encoding="utf-8")
    # okf_version lives in the root index.md frontmatter block.
    head = text.split("\n---", 1)[0] if text.startswith("---") else text
    return "okf_version" in head


@register_destructive_op("okf_conversion")
class OKFConversionOp(DestructiveOp):
    """Convert a project's vault to an OKF v0.1 knowledge bundle."""

    OP_TYPE = "okf_conversion"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _vault(self, project_root: Path, args: dict) -> Path:
        return self.safe_path(project_root, args.get("vault", "vault"))

    def _lint_clean(self, vault: Path) -> bool:
        lint = vault / "_meta" / "okf" / "okf_lint.py"
        if not lint.exists():
            return False
        return run_tool(lint, ["--quiet"]).returncode == 0

    def _is_converted(self, vault: Path) -> bool:
        """A converted vault declares okf_version and lints clean."""
        return _has_okf_version(vault / "index.md") and self._lint_clean(vault)

    def _seed_tooling(self, vault: Path, skills_root: Path, backups_dir: Path) -> list[str]:
        """Copy bundle tooling into the vault. Overwrite-on-drift with backups."""
        backups: list[str] = []
        for rel in _OKF_TOOLS:
            src = skills_root / "vault" / rel
            if not src.exists():
                raise FileNotFoundError(
                    f"OKF tooling {rel!r} not found in plugin bundle at {src}."
                )
            dest = vault / rel
            src_bytes = src.read_bytes()
            if dest.exists():
                if dest.read_bytes() == src_bytes:
                    continue  # identical — no write, no backup
                info = write_backup_with_sidecar(backups_dir, dest)
                backups.append(str(info["bak_path"]))
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src_bytes)
        return backups

    # ------------------------------------------------------------------
    # dry_run
    # ------------------------------------------------------------------

    def dry_run(self, project_root: Path, args: dict) -> dict:
        op_id = args.get("id", "okf-conversion")
        vault = self._vault(project_root, args)

        def report(**kw) -> dict:
            base = {
                "op_id": op_id,
                "op_type": self.OP_TYPE,
                "would_apply": False,
                "would_skip_idempotent": False,
                "would_overwrite_drift": False,
                "would_fail_precondition": False,
                "drift_summary": None,
            }
            base.update(kw)
            return base

        if not vault.is_dir():
            return report(would_fail_precondition=True,
                          drift_summary="no vault directory to convert")
        if self._is_converted(vault):
            return report(would_skip_idempotent=True)
        return report(would_apply=True)

    # ------------------------------------------------------------------
    # apply
    # ------------------------------------------------------------------

    def apply(self, project_root: Path, args: dict) -> dict:
        op_id = args.get("id", "okf-conversion")
        skills_root = Path(args["skills_root"])
        vault = self._vault(project_root, args)
        backups_dir = project_root / ".ark" / "backups"

        def result(status: str, **kw) -> dict:
            base = {
                "op_id": op_id,
                "op_type": self.OP_TYPE,
                "status": status,
                "backups": [],
                "error": None,
            }
            base.update(kw)
            return base

        if not vault.is_dir():
            return result("skipped_precondition",
                          error="no vault directory to convert")
        if self._is_converted(vault):
            return result("skipped_idempotent")

        # 1. Seed tooling (plugin-owned, overwrite-on-drift with backups).
        backups = self._seed_tooling(vault, skills_root, backups_dir)

        okf_dir = vault / "_meta" / "okf"
        # 2. normalize frontmatter.
        norm = run_tool(okf_dir / "normalize_frontmatter.py", ["--apply"])
        if norm.returncode != 0:
            return result("failed", backups=backups,
                          error=f"normalize_frontmatter failed: {norm.stderr or norm.stdout}")
        # 3. convert links.
        conv = run_tool(okf_dir / "convert_links.py", ["--apply"])
        if conv.returncode != 0:
            return result("failed", backups=backups,
                          error=f"convert_links failed: {conv.stderr or conv.stdout}")
        # 4. regenerate indexes (root index.md declares okf_version).
        gen = run_tool(vault / "_meta" / "generate-index.py", [])
        if gen.returncode != 0:
            return result("failed", backups=backups,
                          error=f"generate-index failed: {gen.stderr or gen.stdout}")
        # 5. ensure log.md mirror exists.
        log_md = vault / "log.md"
        if not log_md.exists():
            log_md.write_text(
                "# Work log\n\nIn-bundle mirror of the work record "
                "(see docs/agents/issue-tracker.md dual-write rule).\n",
                encoding="utf-8",
            )
        # 6. freeze legacy trackers.
        freeze_legacy_trackers(vault)
        # 7. verify.
        if not self._lint_clean(vault):
            lint = run_tool(okf_dir / "okf_lint.py", [])
            return result("failed", backups=backups,
                          error=f"okf_lint reported errors:\n{lint.stdout}")

        return result("applied", backups=backups)
