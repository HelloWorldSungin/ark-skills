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


def _parse_chain_file(text: str):
    """Return dict: scenario, weight, completed, next_skill, remaining, all_steps, proceed_past_level."""
    fm = {}
    body = text
    if text.startswith("---"):
        lines = text.split("\n")
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for fl in lines[1:i]:
                    if ":" in fl:
                        k, _, v = fl.partition(":")
                        fm[k.strip()] = v.strip()
                body = "\n".join(lines[i + 1:])
                break

    completed = []
    remaining = []
    all_steps = []
    for line in body.split("\n"):
        m = _CHECKLIST_LINE_RE.match(line)
        if not m:
            continue
        label = m.group(3)[2:].strip()  # everything after "] "
        all_steps.append(label)
        if m.group(2) == "x":
            completed.append(label)
        else:
            remaining.append(label)
    next_skill = remaining[0] if remaining else None
    rest = remaining[1:] if remaining else []
    return {
        "scenario": fm.get("scenario", "unknown"),
        "weight": fm.get("weight", "unknown"),
        "completed": completed,
        "next_skill": next_skill,
        "remaining": rest,
        "all_steps": all_steps,
        "proceed_past_level": fm.get("proceed_past_level", "null"),
    }


def render_step_boundary_menu(*, level: str, pct: int, tokens, chain_text: str) -> str:
    """Render the three-option mitigation menu for mid-chain step boundaries.

    Task 10 only handles the mid-chain case (>=1 [x] step). Task 11 adds the
    zero-completed entry branch.
    """
    info = _parse_chain_file(chain_text)
    if not info["completed"] and info["all_steps"]:
        return _render_entry_menu(level=level, pct=pct, tokens=tokens, info=info)
    return _render_midchain_menu(level=level, pct=pct, tokens=tokens, info=info)


def _format_pct_tokens(pct: int, tokens) -> str:
    if isinstance(tokens, int):
        return f"Context at {pct}% (~{tokens // 1000}k)"
    return f"Context at {pct}%"


def _render_midchain_menu(*, level, pct, tokens, info) -> str:
    completed = ", ".join(info["completed"]) or "(none)"
    remaining = ", ".join(info["remaining"]) or "(none)"
    next_skill = info["next_skill"] or "(unknown)"
    next_step_num = len(info["completed"]) + 1
    scenario = info["scenario"]
    weight = info["weight"]
    pct_tokens = _format_pct_tokens(pct, tokens)

    if level == "strong":
        header = (
            f"⚠ {pct_tokens} — entering the attention-rot zone (~300k+ tokens) "
            f"where reasoning quality degrades. One of (a)/(b)/(c) is strongly "
            f"recommended before continuing."
        )
    else:
        header = f"⚠ {pct_tokens}. Options before continuing to Next:"

    forward_brief = (
        f'  "Resuming {scenario} chain ({weight}). Completed: {completed}.\n'
        f'   Next: step {next_step_num} — {next_skill}. Remaining: {remaining}.\n'
        f'   Key findings so far: <fill in>."'
    )

    return (
        f"{header}\n\n"
        f"Forward brief (auto-assembled from current-chain.md):\n"
        f"{forward_brief}\n\n"
        f"  (a) /compact focus on the forward brief above.\n"
        f"  (b) /clear, then paste the forward brief above as your opening message.\n"
        f"  (c) Delegate Next step to a subagent (keeps this session lean — only the\n"
        f"      subagent's conclusion returns, not its tool output).\n\n"
        f"Which option? [a/b/c/proceed]"
    )


def _render_entry_menu(*, level, pct, tokens, info) -> str:
    plan = ", ".join(info["all_steps"]) or "(no steps)"
    scenario = info["scenario"]
    weight = info["weight"]
    pct_tokens = _format_pct_tokens(pct, tokens)

    if level == "strong":
        header = (
            f"⚠ {pct_tokens} — entering the attention-rot zone (~300k+ tokens) "
            f"before chain has started. One of (b)/(c) is strongly recommended."
        )
    else:
        header = f"⚠ {pct_tokens} before chain has started."

    forward_brief = (
        f'  "Starting {scenario} chain ({weight}). Plan: {plan}.\n'
        f'   Key context to preserve: <fill in>."'
    )

    return (
        f"{header}\n\n"
        f"Forward brief (auto-assembled):\n"
        f"{forward_brief}\n\n"
        f"  (a) /compact — unavailable (no progress to summarize yet).\n"
        f"  (b) /clear, then paste the forward brief above as your opening message.\n"
        f"  (c) Delegate Step 1 to a subagent (keeps this session lean — only the\n"
        f"      subagent's conclusion returns, not its tool output).\n\n"
        f"Which option? [b/c/proceed]"
    )


def _set_proceed_past_level(text: str, value: str) -> str:
    """Set proceed_past_level in YAML frontmatter to 'nudge' or 'null'.

    Only matches lines that start at column 0 with `proceed_past_level:` — this
    avoids clobbering an indented content line inside a block scalar (e.g.,
    `task_summary: |-` followed by indented text containing the literal string
    `proceed_past_level:`). Top-level YAML keys never have leading whitespace.

    If the field is missing from the frontmatter, insert it before the closing '---'.
    Operates only on the frontmatter region (text between the first two '---' lines).
    """
    if not text.startswith("---"):
        return text  # no frontmatter; refuse to mutate

    lines = text.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return text  # malformed; refuse

    fm_lines = lines[1:end_idx]
    new_field = f"proceed_past_level: {value}"
    found = False
    for i, line in enumerate(fm_lines):
        # Anchor at column 0 — top-level YAML keys have no leading whitespace.
        # `line.startswith(...)` (NOT `line.strip().startswith(...)`) so that an
        # indented occurrence inside a block scalar like `task_summary: |-` is
        # never matched.
        if line.startswith("proceed_past_level:"):
            fm_lines[i] = new_field
            found = True
            break
    if not found:
        fm_lines.append(new_field)

    return "\n".join([lines[0]] + fm_lines + lines[end_idx:])


def _cmd_record_proceed(args) -> int:
    result = probe(Path(args.state_path),
                   nudge_pct=args.nudge_pct,
                   strong_pct=args.strong_pct)
    # Probe failure (missing/stale/malformed cache) -> silent no-op so existing
    # suppression state is preserved. Spec: probe failures degrade silently.
    if result["level"] == "unknown":
        return 0
    # Strong or ok -> persist null. Only nudge persists "nudge".
    value = "nudge" if result["level"] == "nudge" else "null"
    chain_file.atomic_update(
        Path(args.chain_path),
        lambda text: _set_proceed_past_level(text, value),
    )
    return 0


def _cmd_record_reset(args) -> int:
    chain_file.atomic_update(
        Path(args.chain_path),
        lambda text: _set_proceed_past_level(text, "null"),
    )
    return 0


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


def _cmd_step_boundary(args) -> int:
    result = probe(
        Path(args.state_path),
        nudge_pct=args.nudge_pct,
        strong_pct=args.strong_pct,
        max_age_seconds=args.max_age_seconds,
        expected_cwd=args.expected_cwd,
        expected_session_id=args.expected_session_id,
    )
    if result["level"] in ("ok", "unknown"):
        return 0  # silent

    # Read chain file (degraded if missing).
    try:
        chain_text = Path(args.chain_path).read_text()
    except FileNotFoundError:
        chain_text = "---\nscenario: unknown\nweight: unknown\n---\n## Steps\n"
        sys.stderr.write(f"chain file missing: {args.chain_path}\n")
    except Exception as exc:
        chain_text = "---\nscenario: unknown\nweight: unknown\n---\n## Steps\n"
        sys.stderr.write(f"chain file unreadable: {exc}\n")

    # Suppression: if proceed_past_level == 'nudge' and current level is 'nudge', skip.
    info = _parse_chain_file(chain_text)
    if result["level"] == "nudge" and info.get("proceed_past_level") == "nudge":
        return 0

    menu = render_step_boundary_menu(
        level=result["level"],
        pct=result["pct"],
        tokens=result["tokens"],
        chain_text=chain_text,
    )
    sys.stdout.write(menu + "\n")
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
    if args.format == "step-boundary":
        return _cmd_step_boundary(args)
    if args.format == "check-off":
        return _cmd_check_off(args)
    if args.format == "record-proceed":
        return _cmd_record_proceed(args)
    if args.format == "record-reset":
        return _cmd_record_reset(args)
    sys.stderr.write(f"format {args.format!r} not implemented\n")
    return 0  # spec: all modes exit 0 even on missing implementation


if __name__ == "__main__":
    sys.exit(main())
