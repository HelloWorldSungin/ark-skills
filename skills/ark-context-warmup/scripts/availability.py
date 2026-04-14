"""Availability probe for /ark-context-warmup backends."""
from __future__ import annotations

import json
from pathlib import Path


def _load_notebooklm_config(project_repo: Path, vault_path: Path) -> dict | None:
    # Lookup order: vault_path/.notebooklm/config.json first, then project_repo/.notebooklm/config.json.
    # A malformed/unreadable config at the first location must NOT short-circuit
    # the lookup — continue to the next location (codex P3 finding). Only
    # return None if every location is missing or unparseable.
    for base in (vault_path, project_repo):
        cfg = base / ".notebooklm" / "config.json"
        if not cfg.exists():
            continue
        try:
            return json.loads(cfg.read_text())
        except (json.JSONDecodeError, OSError):
            continue
    return None


def probe(
    *,
    project_repo: Path,
    vault_path: Path,
    tasknotes_path: Path,
    task_prefix: str,
    notebooklm_cli_path: str | None,
    # OMC_CACHE_DIR canonical constant lives in
    # skills/ark-workflow/references/omc-integration.md § Section 0.
    omc_cli_path: str | None = None,
    omc_cache_dir: Path | None = None,
) -> dict:
    """Returns a dict with keys:
    - notebooklm: bool
    - wiki: bool
    - tasknotes: bool
    - has_omc: bool
    - notebooklm_skip_reason, wiki_skip_reason, tasknotes_skip_reason,
      has_omc_skip_reason: str (present if False)
    """
    result: dict = {}

    # NotebookLM
    if notebooklm_cli_path is None:
        result["notebooklm"] = False
        result["notebooklm_skip_reason"] = "notebooklm CLI not on PATH"
    else:
        cfg = _load_notebooklm_config(project_repo, vault_path)
        if cfg is None:
            result["notebooklm"] = False
            result["notebooklm_skip_reason"] = "no parseable .notebooklm/config.json in project repo or vault"
        else:
            notebooks = cfg.get("notebooks", {})
            if not notebooks:
                result["notebooklm"] = False
                result["notebooklm_skip_reason"] = "config has no notebooks"
            elif len(notebooks) == 1:
                result["notebooklm"] = True
            else:
                default_key = cfg.get("default_for_warmup")
                if default_key and default_key in notebooks:
                    result["notebooklm"] = True
                else:
                    result["notebooklm"] = False
                    result["notebooklm_skip_reason"] = (
                        "Multi-notebook NotebookLM config without default_for_warmup — lane skipped. "
                        "Add default_for_warmup to .notebooklm/config.json pointing at the notebook key to use."
                    )

    # Wiki — the T4 scan only reads index.md. Do not require _meta/vault-schema.md;
    # minimal / pre-restructured vaults still have a working wiki lane without it.
    index = vault_path / "index.md"
    if not index.exists():
        result["wiki"] = False
        result["wiki_skip_reason"] = f"index.md missing at {index}"
    else:
        result["wiki"] = True

    # TaskNotes — warmup_search.py only reads {tasknotes_path}/Tasks/*.md. The
    # counter file is only used when CREATING new tasks, not when searching,
    # so availability must key off the Tasks/ directory existence. Imported or
    # read-only vaults have a populated Tasks/ but no counter, and the lane
    # should remain available there (codex P2 finding).
    tasks_dir = tasknotes_path / "Tasks"
    if not tasks_dir.is_dir():
        result["tasknotes"] = False
        result["tasknotes_skip_reason"] = f"Tasks directory missing at {tasks_dir}"
    else:
        result["tasknotes"] = True

    # OMC — optional autonomous-execution framework. Mirrors notebooklm idiom:
    # upstream callers resolve `omc_cli_path` via `shutil.which("omc")` so the
    # probe stays pure. Detection is OR of: CLI on PATH, or cache dir present.
    # OMC_CACHE_DIR canonical: see skills/ark-workflow/references/omc-integration.md § Section 0.
    has_cli = omc_cli_path is not None
    has_cache = omc_cache_dir is not None and omc_cache_dir.exists()
    if has_cli or has_cache:
        result["has_omc"] = True
    else:
        result["has_omc"] = False
        resolved = omc_cache_dir if omc_cache_dir is not None else Path.home() / ".claude" / "plugins" / "cache" / "omc"
        result["has_omc_skip_reason"] = (
            f"OMC CLI not on PATH and OMC_CACHE_DIR ({resolved}) not present"
        )

    return result
