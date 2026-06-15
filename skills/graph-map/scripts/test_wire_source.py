"""Tests for wire_source.py — wire concept notes to their origin source file."""
import importlib.util
from pathlib import Path

MOD_PATH = Path(__file__).parent / "wire_source.py"
spec = importlib.util.spec_from_file_location("wire_source", MOD_PATH)
ws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ws)

NOTE = """---
source_file: "skills/foo/bar.py"
type: "rationale"
location: "L1"
tags:
  - graphify/rationale
---

# Bar concept

## Connections
- [[bar.py]] - `rationale_for`
"""


def _make(tmp_path):
    (tmp_path / "skills" / "foo").mkdir(parents=True)
    (tmp_path / "skills" / "foo" / "bar.py").write_text("x = 1\n")
    notes = tmp_path / "vault" / "generated" / "graphify"
    notes.mkdir(parents=True)
    note = notes / "Bar concept.md"
    note.write_text(NOTE)
    return notes, note


class TestWireNote:
    def test_injects_source_link_that_resolves(self, tmp_path):
        notes, note = _make(tmp_path)
        assert ws.wire_note(note, tmp_path) is True
        text = note.read_text()
        assert "## Source" in text
        # the injected relative link must resolve to the real source on disk
        import re
        m = re.search(r"## Source\n\n\[.*?\]\((.*?)\)", text)
        assert m, "no source link found"
        target = (note.parent / m.group(1)).resolve()
        assert target == (tmp_path / "skills" / "foo" / "bar.py").resolve()
        assert target.exists()

    def test_idempotent(self, tmp_path):
        notes, note = _make(tmp_path)
        ws.wire_note(note, tmp_path)
        assert ws.wire_note(note, tmp_path) is False  # already wired
        assert note.read_text().count("## Source") == 1

    def test_skips_note_without_source_file(self, tmp_path):
        notes, _ = _make(tmp_path)
        bare = notes / "bare.md"
        bare.write_text("---\ntype: x\n---\n\n# Bare\n")
        assert ws.wire_note(bare, tmp_path) is False
        assert "## Source" not in bare.read_text()

    def test_preserves_title_and_connections(self, tmp_path):
        notes, note = _make(tmp_path)
        ws.wire_note(note, tmp_path)
        text = note.read_text()
        assert "# Bar concept" in text
        assert "[[bar.py]]" in text


    def test_single_quoted_source_file_no_literal_quotes(self, tmp_path):
        """A single-quoted source_file value must be parsed without literal quotes."""
        (tmp_path / "skills" / "foo").mkdir(parents=True)
        (tmp_path / "skills" / "foo" / "bar.py").write_text("x = 1\n")
        notes = tmp_path / "vault" / "generated" / "graphify"
        notes.mkdir(parents=True)
        note = notes / "Single Quote.md"
        note.write_text(
            "---\nsource_file: 'skills/foo/bar.py'\ntype: rationale\n---\n\n# Single Quote\n"
        )
        assert ws.wire_note(note, tmp_path) is True
        text = note.read_text()
        assert "## Source" in text
        # Must not retain literal quotes in the link target
        import re as _re
        m = _re.search(r"## Source\n\n\[.*?\]\((.*?)\)", text)
        assert m, "no source link found"
        rel_path = m.group(1)
        assert "'" not in rel_path, f"Literal single-quote in link path: {rel_path!r}"
        target = (note.parent / rel_path).resolve()
        assert target == (tmp_path / "skills" / "foo" / "bar.py").resolve()
        assert target.exists()


class TestMain:
    def test_main_wires_all(self, tmp_path, capsys):
        notes, _ = _make(tmp_path)
        rc = ws.main(["--notes-dir", str(notes), "--repo-root", str(tmp_path)])
        assert rc == 0
        assert "wired 1" in capsys.readouterr().out
