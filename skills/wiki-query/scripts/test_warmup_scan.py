"""Tests for warmup_scan.py — T4 index.md scan for warm-up."""
import json
import subprocess
import tempfile
from pathlib import Path

SCAN_PATH = Path(__file__).parent / "warmup_scan.py"


def _make_vault(tmpdir: Path, index_content: str):
    """Write index.md to a temp vault dir."""
    (tmpdir / "index.md").write_text(index_content)


def test_returns_top_matches():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, """# Index
- [[Auth-Migration]] — tags: migration, auth — migration of auth system to new provider
- [[Cache-Layer]] — tags: performance — caching strategy for api
- [[Rate-Limiting]] — tags: api, security — rate limiting implementation notes
""")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "rate limiting api", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["tier"] == "T4"
        assert len(out["matches"]) >= 1
        titles = [m["title"] for m in out["matches"]]
        assert "Rate-Limiting" in titles


def test_no_matches():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, "# Index\n(empty)\n")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "nothing", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["matches"] == []


def test_no_index_file():
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(tmp), "--query", "foo", "--top", "3", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "index.md" in r.stderr.lower()
