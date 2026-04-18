"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

import json
from pathlib import Path


def probe(state_path, *, nudge_pct: int = 20, strong_pct: int = 35):
    """Read Claude Code statusline cache and return a budget recommendation."""
    data = json.loads(Path(state_path).read_text())
    pct = data["context_window"]["used_percentage"]
    pct = max(0, min(100, pct))

    if pct >= strong_pct:
        level = "strong"
    elif pct >= nudge_pct:
        level = "nudge"
    else:
        level = "ok"

    return {"level": level, "pct": pct, "tokens": None, "warnings": [], "reason": None}
