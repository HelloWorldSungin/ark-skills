"""Contract executor: runs warmup_contract commands end-to-end.

Resolves inputs (env, config JSON-path, template) → runs preconditions (D6 convention) →
substitutes shell template → runs shell with timeout → parses JSON → extracts fields via
simple dotted JSONPath → validates required_fields.

Note: this module deliberately does NOT use `from __future__ import annotations`.
Combining that with @dataclass breaks under Python 3.14 when the module is loaded
via spec_from_file_location without being registered in sys.modules (as the test
harness does). The file uses Optional[X] from typing instead for py3.9 compat.
"""
import json
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class InputResolutionError(RuntimeError):
    pass


class JSONPathError(RuntimeError):
    pass


@dataclass
class ShellResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


def extract_json_path(data: Any, path: str) -> Any:
    """Simple dotted JSONPath. Supports:
      - "$"          → the whole document
      - "$.a.b.c"    → nested key access
    Arrays are NOT supported (raises JSONPathError if requested with [N] syntax).
    Missing keys return None.
    """
    if path == "$":
        return data
    if not path.startswith("$."):
        raise JSONPathError(f"JSONPath must start with '$' or '$.': {path}")
    if "[" in path or "]" in path:
        raise JSONPathError(f"array indexing not supported in simple JSONPath: {path}")
    current = data
    for key in path[2:].split("."):
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]
    return current


def substitute_shell_template(template: str, vars_: dict) -> str:
    """Substitute {{var}} placeholders. Raises KeyError if any placeholder is unresolved.

    Every substituted value is passed through shlex.quote so the resulting
    string is safe to run via `bash -c`, regardless of what shell-significant
    characters the value contains. Backend shell templates MUST NOT wrap
    {{placeholders}} in their own quotes — e.g. write `ask {{prompt}}`, never
    `ask "{{prompt}}"`. TestBackendContractShellTemplates enforces this.
    """
    def _replace(m):
        name = m.group(1).strip()
        if name not in vars_:
            raise KeyError(f"unresolved shell template variable: {name}")
        return shlex.quote(str(vars_[name]))
    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", _replace, template)


def _normalize_json_path(path: str) -> str:
    """Return a JSONPath starting with '$.'; if it already starts with '$', return as-is."""
    return path if path.startswith("$") else "$." + path


# Template bodies (from: template in a warmup_contract) may contain single-brace
# placeholders like {WARMUP_TASK_TEXT} or {WARMUP_PROJECT_NAME}. The executor
# expands these from the environment at resolve time. Unknown placeholders pass
# through literally so a misnamed placeholder surfaces as garbage in the backend
# response rather than crashing resolve_input.
_TEMPLATE_VAR_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def _interpolate_template(body: str, env: dict) -> str:
    def _replace(m: "re.Match[str]") -> str:
        name = m.group(1)
        return env.get(name, m.group(0))
    return _TEMPLATE_VAR_RE.sub(_replace, body)


def _lookup_single_or_default(config: dict, json_path_template: str) -> Any:
    """Implements the D5 lookup: if notebooks has one key, use it; if multiple,
    require default_for_warmup to pick. Raises otherwise.
    """
    notebooks = config.get("notebooks", {})
    if not notebooks:
        raise InputResolutionError("config has no notebooks")
    if len(notebooks) == 1:
        key = next(iter(notebooks))
    else:
        key = config.get("default_for_warmup")
        if not key or key not in notebooks:
            raise InputResolutionError(
                "Multi-notebook NotebookLM config without default_for_warmup — "
                "lane skipped. Add default_for_warmup to .notebooklm/config.json "
                "pointing at the notebook key to use."
            )
    resolved_path = json_path_template.replace("{key}", key)
    value = extract_json_path(config, _normalize_json_path(resolved_path))
    if value is None:
        raise InputResolutionError(f"config path {resolved_path} resolved to None")
    return value


def resolve_input(input_spec: dict, *, config: Optional[dict], templates: dict) -> Any:
    """Resolve a single input per D6. `input_spec` is one entry from warmup_contract.commands[*].inputs."""
    source = input_spec.get("from")
    required = bool(input_spec.get("required", False))
    if source == "env":
        name = input_spec["env_var"]
        val = os.environ.get(name)
        if val is None and required:
            raise InputResolutionError(f"required env var not set: {name}")
        return val
    if source == "config":
        if config is None and required:
            raise InputResolutionError("config required but not provided")
        if config is None:
            return None
        if "json_path" in input_spec:
            return extract_json_path(config, _normalize_json_path(input_spec["json_path"]))
        if input_spec.get("lookup") == "single_or_default_for_warmup":
            return _lookup_single_or_default(config, input_spec["json_path_template"])
        raise InputResolutionError(f"config input needs json_path or lookup: {input_spec}")
    if source == "template":
        tid = input_spec["template_id"]
        if tid not in templates:
            raise InputResolutionError(f"unknown template id: {tid}")
        return _interpolate_template(templates[tid], os.environ)
    raise InputResolutionError(f"unknown input source: {source}")


def run_precondition(*, script_path: Path, env: dict, timeout_s: int = 5) -> tuple[bool, str]:
    """Run a precondition script per D6. Returns (exit_0_bool, stderr_text)."""
    if not Path(script_path).exists():
        return False, f"precondition script not found: {script_path}"
    merged_env = {**os.environ, **env}
    try:
        r = subprocess.run(
            ["bash", str(script_path)],
            env=merged_env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return (r.returncode == 0), r.stderr
    except subprocess.TimeoutExpired:
        return False, f"precondition timeout after {timeout_s}s"


def run_shell(shell_cmd: str, *, timeout_s: int = 90, env: Optional[dict] = None) -> ShellResult:
    """Run a resolved shell command and return its result."""
    merged_env = {**os.environ, **(env or {})}
    try:
        r = subprocess.run(
            ["bash", "-c", shell_cmd],
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return ShellResult(exit_code=r.returncode, stdout=r.stdout, stderr=r.stderr, timed_out=False)
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return ShellResult(exit_code=-1, stdout=stdout, stderr=stderr, timed_out=True)


def execute_command(
    command_spec: dict,
    *,
    config: Optional[dict],
    templates: dict,
    env_overrides: dict,
    timeout_s: int = 90,
) -> Optional[dict]:
    """Execute a single warmup_contract command. Returns extracted dict on success,
    or None if the command was skipped (precondition failed) or failed validation.
    """
    # 1. Resolve inputs
    resolved: dict = {}
    for name, spec in (command_spec.get("inputs") or {}).items():
        try:
            resolved[name] = resolve_input(spec, config=config, templates=templates)
        except InputResolutionError:
            return None  # Treat missing-required-input as a skip

    # 2. Run preconditions (all must pass)
    for pre in (command_spec.get("preconditions") or []):
        script_path = Path(pre["script"])
        ok, _stderr = run_precondition(script_path=script_path, env=env_overrides, timeout_s=5)
        if not ok:
            return None

    # 3. Substitute shell template
    try:
        shell_cmd = substitute_shell_template(command_spec["shell"], resolved)
    except KeyError:
        return None

    # 4. Run shell
    result = run_shell(shell_cmd, timeout_s=timeout_s, env=env_overrides)
    if result.timed_out or result.exit_code != 0:
        return None

    # 5. Parse JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    # 6. Extract fields
    extract_spec = command_spec.get("output", {}).get("extract", {})
    extracted: dict = {}
    for field, path in extract_spec.items():
        try:
            extracted[field] = extract_json_path(data, path)
        except JSONPathError:
            return None

    # 7. Validate required_fields — only reject missing or explicit-null.
    # Empty containers ([], {}, "") and False are legitimate results from a
    # healthy backend ("no sessions found") and must not be demoted to
    # Degraded coverage (mirrors the Task 13 semantic fix in evidence.py).
    required = command_spec.get("output", {}).get("required_fields", [])
    for field in required:
        if field not in extracted or extracted[field] is None:
            return None

    return extracted
