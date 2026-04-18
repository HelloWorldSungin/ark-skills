"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

import json
from pathlib import Path


def probe(state_path, *, nudge_pct: int = 20, strong_pct: int = 35):
    """Read Claude Code statusline cache and return a budget recommendation."""
    p = Path(state_path)

    # Filesystem-level checks first.
    if not p.exists():
        return _unknown("file_missing")
    if p.is_dir():
        return _unknown("not_a_file")

    try:
        raw = p.read_text()
    except PermissionError:
        return _unknown("permission_error")
    except OSError:
        return _unknown("permission_error")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _unknown("parse_error")

    cw = data.get("context_window", {})
    pct = cw.get("used_percentage")
    if not isinstance(pct, int):
        return _unknown("schema_mismatch")
    pct = max(0, min(100, pct))

    tokens, warnings = _sum_tokens(cw.get("current_usage"))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": tokens, "warnings": warnings, "reason": None}


def _unknown(reason: str):
    return {"level": "unknown", "pct": None, "tokens": None, "warnings": [], "reason": reason}


def _sum_tokens(current_usage):
    """Sum the four token subfields. Return (None, ['tokens_unavailable']) if any is bad."""
    if not isinstance(current_usage, dict):
        return None, ["tokens_unavailable"]
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    total = 0
    for k in keys:
        v = current_usage.get(k)
        if not isinstance(v, int):
            return None, ["tokens_unavailable"]
        total += v
    return total, []
