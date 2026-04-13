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


def test_returns_matches_from_table_form_index():
    """Codex P1 (latest): Ark vaults generate index.md as markdown table rows
    like '| [[Page.md|Title]] | type | summary |'. The parser must handle both
    bullet and table rows — otherwise the wiki lane silently returns empty
    matches on every real vault, while availability reports the lane healthy."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, """---
title: "Index"
---

# Index

<!-- AUTO-GENERATED -->

| Page | Type | Summary |
|------|------|---------|
| [[Auth-Migration.md|Auth migration]] | decision | migration of auth system to new provider |
| [[Cache-Layer.md|Cache Layer]] | doc | caching strategy for api |
| [[Rate-Limiting.md|Rate Limiting]] | doc | rate limiting implementation notes |
""")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "rate limiting api", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        assert out["tier"] == "T4"
        titles = [m["title"] for m in out["matches"]]
        assert "Rate Limiting" in titles or "Rate-Limiting.md" in titles, (
            f"expected Rate Limiting page in matches, got: {titles}"
        )


def test_ignores_table_header_and_separator_rows():
    """The `| Page | Type | Summary |` header and `|---|---|---|` separator
    must not become candidate matches."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        _make_vault(vault, """# Index

| Page | Type | Summary |
|------|------|---------|
| [[auth.md|Auth]] | doc | token auth notes |
""")
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(vault), "--query", "page type summary", "--top", "3", "--json"],
            capture_output=True, text=True, check=True,
        )
        out = json.loads(r.stdout)
        for m in out["matches"]:
            assert m["title"] != "Page", "table header must not match"
            assert "---" not in m.get("title", ""), "separator row must not match"


def test_no_index_file():
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(
            ["python3", str(SCAN_PATH), "--vault", str(tmp), "--query", "foo", "--top", "3", "--json"],
            capture_output=True, text=True,
        )
        assert r.returncode != 0
        assert "index.md" in r.stderr.lower()
