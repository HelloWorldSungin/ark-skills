"""Test the chain integrity CI check."""
import subprocess
from pathlib import Path

CHECK = Path(__file__).parent / "check_chain_integrity.py"


def test_passes_on_current_repo(tmp_path):
    # Use the actual chain dir — post-Task-20, all 7 chains have step 0 = warmup.
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", "skills/ark-workflow/chains"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"


def test_fails_when_step_0_missing(tmp_path):
    d = tmp_path / "chains"
    d.mkdir()
    (d / "broken.md").write_text("## Light\n1. first step\n2. second\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "step 0" in r.stderr.lower() or "first step" in r.stderr.lower()


def test_fails_on_handoff_marker_drift(tmp_path):
    d = tmp_path / "chains"
    d.mkdir()
    (d / "drift.md").write_text("## Heavy\nhandoff_marker: after-step-5\n0. `/ark-context-warmup`\n1. first\n2. second\n3. third\n")
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "handoff_marker" in r.stderr.lower()


def test_detects_preamble_level_numbered_list(tmp_path):
    """Deferred finding: plan's check only scanned ## sections, would skip ship.md (no ## subsection)."""
    d = tmp_path / "chains"
    d.mkdir()
    # Preamble-only chain (like ship.md), but step 0 is missing
    (d / "preamble-only.md").write_text(
        "# Ship\n\n*standalone ship*\n\n1. `/review`\n2. `/ship`\n3. `/canary`\n"
    )
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "step 0" in r.stderr.lower() or "first step" in r.stderr.lower()


def test_detects_step_0_without_warmup(tmp_path):
    """Deferred finding: step 0 must actually contain /ark-context-warmup, not just the digit 0."""
    d = tmp_path / "chains"
    d.mkdir()
    (d / "wrong-step-0.md").write_text(
        "## Light\n0. Do something else entirely\n1. next\n"
    )
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "ark-context-warmup" in r.stderr.lower()


def test_passes_on_preamble_with_step_0(tmp_path):
    """ship.md-like file with step 0 at preamble level should pass."""
    d = tmp_path / "chains"
    d.mkdir()
    (d / "ship-like.md").write_text(
        "# Shipping\n\n*standalone ship*\n\n0. `/ark-context-warmup` — load context\n"
        "1. `/review`\n2. `/ship`\n3. `/canary`\n"
    )
    r = subprocess.run(
        ["python3", str(CHECK), "--chains", str(d)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"
