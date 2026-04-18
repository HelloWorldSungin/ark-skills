"""Ark Workflow context-budget probe. See spec 2026-04-17-ark-workflow-context-probe-design.md."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


def probe(
    state_path,
    *,
    nudge_pct: int = 20,
    strong_pct: int = 35,
    max_age_seconds=None,
    expected_cwd=None,
    expected_session_id=None,
):
    """Read Claude Code statusline cache and return a budget recommendation."""
    p = Path(state_path)

    # Filesystem-level checks first.
    if not p.exists():
        return _unknown("file_missing")
    if p.is_dir():
        return _unknown("not_a_file")

    try:
        raw = p.read_text()
    except (PermissionError, OSError):
        return _unknown("permission_error")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _unknown("parse_error")

    # Session-id check supersedes everything else when provided.
    cache_session_id = data.get("session_id") or data.get("sessionId")
    if expected_session_id is not None:
        if cache_session_id != expected_session_id:
            return _unknown("session_mismatch")
    else:
        # Mtime-based staleness fallback only when session-id wasn't checked.
        if max_age_seconds is not None:
            try:
                mtime = p.stat().st_mtime
            except OSError:
                return _unknown("permission_error")
            if (time.time() - mtime) > max_age_seconds:
                return _unknown("stale_file")

    # Cwd check (independent of session-id).
    if expected_cwd is not None:
        cache_cwd = data.get("cwd") or data.get("workspace", {}).get("current_dir")
        if cache_cwd != expected_cwd:
            return _unknown("session_mismatch")

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


class chain_file:
    """Namespace for atomic chain-file mutations."""

    @staticmethod
    def atomic_update(chain_path, mutator_fn):
        """Read chain_path, apply mutator_fn(text) -> text, write atomically.

        Uses fcntl.flock(LOCK_EX) on a sibling .lock file to serialize concurrent
        read-modify-write sequences (prevents lost updates), plus temp-file +
        os.replace for torn-write protection.

        Falls back to temp-file + rename without locking on platforms lacking fcntl.
        """
        chain_path = Path(chain_path)
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = chain_path.with_suffix(chain_path.suffix + ".lock")

        if _HAS_FCNTL:
            with open(lock_path, "w") as lock_fd:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                try:
                    _do_update(chain_path, mutator_fn)
                finally:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        else:
            _do_update(chain_path, mutator_fn)


def _do_update(chain_path: Path, mutator_fn):
    try:
        original = chain_path.read_text()
    except FileNotFoundError:
        original = ""
    new_content = mutator_fn(original)
    fd, tmp_name = tempfile.mkstemp(
        prefix=chain_path.name + ".",
        suffix=".tmp",
        dir=str(chain_path.parent),
    )
    try:
        with os.fdopen(fd, "w") as tmp_f:
            tmp_f.write(new_content)
        os.replace(tmp_name, chain_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


import argparse
import re
import sys


_CHECKLIST_LINE_RE = re.compile(r"^(- \[)([ x])(\] .*)$", re.MULTILINE)


def _cmd_check_off(args) -> int:
    if args.step_index is None or args.step_index < 1:
        return 0  # silent no-op

    target_index = args.step_index

    def mutator(text: str) -> str:
        lines = text.split("\n")
        count = 0
        for i, line in enumerate(lines):
            m = _CHECKLIST_LINE_RE.match(line)
            if m:
                count += 1
                if count == target_index:
                    if m.group(2) == "x":
                        return text  # already checked, no-op
                    lines[i] = m.group(1) + "x" + m.group(3)
                    return "\n".join(lines)
        # Index too large — silent no-op.
        return text

    chain_file.atomic_update(Path(args.chain_path), mutator)
    return 0


def _cmd_raw(args) -> int:
    result = probe(
        Path(args.state_path),
        max_age_seconds=args.max_age_seconds,
        expected_cwd=args.expected_cwd,
        expected_session_id=args.expected_session_id,
    )
    sys.stdout.write(json.dumps(result) + "\n")
    return 0


def _build_parser():
    p = argparse.ArgumentParser(description="Ark Workflow context-budget probe")
    p.add_argument("--format", required=True,
                   choices=["raw", "step-boundary", "path-b-acceptance",
                            "record-proceed", "record-reset", "check-off"])
    p.add_argument("--state-path", default=".omc/state/hud-stdin-cache.json")
    p.add_argument("--chain-path", default=".ark-workflow/current-chain.md")
    p.add_argument("--expected-cwd", default=None)
    p.add_argument("--expected-session-id", default=None)
    p.add_argument("--max-age-seconds", type=int, default=None)
    p.add_argument("--step-index", type=int, default=None,
                   help="1-based step index for --format check-off")
    p.add_argument("--nudge-pct", type=int, default=20)
    p.add_argument("--strong-pct", type=int, default=35)
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.format == "raw":
        return _cmd_raw(args)
    if args.format == "check-off":
        return _cmd_check_off(args)
    sys.stderr.write(f"format {args.format!r} not implemented\n")
    return 0  # spec: all modes exit 0 even on missing implementation


if __name__ == "__main__":
    sys.exit(main())
