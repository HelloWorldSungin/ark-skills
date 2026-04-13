"""Parse and validate warmup_contract blocks from backend SKILL.md files."""
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


def load_contract(skill_md: Path) -> dict | None:
    """Load and validate the warmup_contract block from a SKILL.md file.
    Returns the warmup_contract dict (unwrapped), or None if missing/invalid.
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
            return d["warmup_contract"]
        return None
    return None
