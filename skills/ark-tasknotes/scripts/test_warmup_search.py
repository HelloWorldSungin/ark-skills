"""Tests for ark-tasknotes warmup_search.py."""
import json
import subprocess
import tempfile
import textwrap
from pathlib import Path

SCAN_PATH = Path(__file__).parent / "warmup_search.py"


def _write_task(tasks_dir: Path, name: str, frontmatter: dict, body: str = ""):
    (tasks_dir / f"{name}.md").write_text(
        "---\n"
        + "\n".join(f"{k}: {v}" for k, v in frontmatter.items())
        + "\n---\n" + body + "\n"
    )


def test_finds_matching_component():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "Auth migration", "status": "in-progress", "component": "auth"})
        _write_task(tp / "Tasks", "TEST-002", {"title": "Cache layer", "status": "open", "component": "cache"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "auth provider change", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        # component-match: "auth" is extracted from task_normalized, so TEST-001 hits
        assert any(m["id"] == "TEST-001" for m in out["matches"])


def test_skips_done_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "Auth migration", "status": "done", "component": "auth"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "auth provider change", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert all(m["status"] != "done" for m in out["matches"])


def test_status_summary_included():
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks").mkdir()
        _write_task(tp / "Tasks", "TEST-001", {"title": "A", "status": "in-progress", "component": "x"})
        _write_task(tp / "Tasks", "TEST-002", {"title": "B", "status": "open", "component": "y"})
        _write_task(tp / "Tasks", "TEST-003", {"title": "C", "status": "done", "component": "z"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "unrelated", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["status_summary"]["in-progress"] == 1
        assert out["status_summary"]["open"] == 1
        assert out["status_summary"]["done"] == 1


def test_finds_nested_tasks():
    """Deferred finding (codex round 3): glob depth. Tasks/ may contain subdirs like Tasks/Bug/, Tasks/Story/.
    The scan must find tasks in nested directories (use rglob, not glob)."""
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        (tp / "Tasks" / "Bug").mkdir(parents=True)
        (tp / "Tasks" / "Story").mkdir(parents=True)
        _write_task(tp / "Tasks" / "Bug", "TEST-010", {"title": "Nested bug", "status": "open", "component": "auth"})
        _write_task(tp / "Tasks" / "Story", "TEST-011", {"title": "Nested story", "status": "open", "component": "cache"})
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--tasknotes", str(tp), "--prefix", "TEST-",
             "--task-normalized", "auth work", "--scenario", "greenfield", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        # Both nested tasks must appear in status_summary
        assert out["status_summary"]["open"] == 2
        # TEST-010 should match on component="auth"
        ids = [m["id"] for m in out["matches"]]
        assert "TEST-010" in ids
