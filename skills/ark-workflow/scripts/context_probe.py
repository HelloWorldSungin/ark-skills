"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

import json
from pathlib import Path


def probe(state_path):
    """Read Claude Code statusline cache and return a budget recommendation."""
    data = json.loads(Path(state_path).read_text())
    pct = data["context_window"]["used_percentage"]
    return {"level": "ok", "pct": pct, "tokens": None, "warnings": [], "reason": None}
