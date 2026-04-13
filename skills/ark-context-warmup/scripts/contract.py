"""Parse and validate warmup_contract blocks from backend SKILL.md files."""
from __future__ import annotations

import re
from pathlib import Path

try:
    import yaml
except ImportError as e:
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml") from e


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)


def _extract_yaml_blocks(text: str):
    return [m.group(1) for m in _YAML_BLOCK_RE.finditer(text)]


def _validate_contract(d: dict) -> bool:
    if not isinstance(d, dict):
        return False
    wc = d.get("warmup_contract")
    if not isinstance(wc, dict):
        return False
    if wc.get("version") != 1:
        return False
    cmds = wc.get("commands")
    if not isinstance(cmds, list) or not cmds:
        return False
    for cmd in cmds:
        if not isinstance(cmd, dict):
            return False
        if not cmd.get("id") or not isinstance(cmd.get("id"), str):
            return False
        if not cmd.get("shell") or not isinstance(cmd.get("shell"), str):
            return False
        out = cmd.get("output", {})
        if not isinstance(out, dict):
            return False
        if "required_fields" not in out or not isinstance(out["required_fields"], list):
            return False
    return True


def _resolve_precondition_paths(contract_dict: dict, skill_dir: Path) -> None:
    """Rewrite relative preconditions[*].script entries to absolute paths
    anchored at skill_dir. Mutates in place. Absolute paths are left untouched
    so callers can opt into external scripts (e.g. `$ARK_SKILLS_ROOT/...`
    after shell expansion) without surprise rewriting.
    """
    for cmd in contract_dict.get("commands", []) or []:
        for pre in cmd.get("preconditions", []) or []:
            script = pre.get("script")
            if not isinstance(script, str) or not script:
                continue
            p = Path(script)
            if p.is_absolute():
                continue
            pre["script"] = str((skill_dir / p).resolve())


def load_contract(skill_md: Path) -> dict | None:
    """Load and validate the warmup_contract block from a SKILL.md file.
    Returns the warmup_contract dict (unwrapped), or None if missing/invalid.

    Relative precondition script paths are resolved against the SKILL.md's
    parent directory so /ark-context-warmup can execute them regardless of cwd
    (fix for the codex P1 finding: contracts declare e.g.
    'scripts/session_shape_check.sh', and that must resolve to the path under
    the backend skill, not the project root).
    """
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    for block in _extract_yaml_blocks(text):
        if "warmup_contract" not in block:
            continue
        try:
            d = yaml.safe_load(block)
        except yaml.YAMLError:
            return None
        if _validate_contract(d):
            wc = d["warmup_contract"]
            _resolve_precondition_paths(wc, skill_md.parent)
            return wc
        return None
    return None
