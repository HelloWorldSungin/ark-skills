"""Tests for ensure_index_exclusion.py — add an entry to a Python set literal safely."""
import importlib.util
import subprocess
from pathlib import Path

MOD_PATH = Path(__file__).parent / "ensure_index_exclusion.py"
spec = importlib.util.spec_from_file_location("ensure_index_exclusion", MOD_PATH)
eie = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eie)


def _write(tmp_path, body):
    f = tmp_path / "generate-index.py"
    f.write_text(body)
    return f


class TestEnsureEntry:
    def test_adds_to_canonical_single_line(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {"_Templates", "_meta", ".obsidian"}\n')
        assert eie.ensure_entry(f) == "added"
        assert eie.ensure_entry(f) == "present"  # idempotent
        # set is still a valid single-line literal containing generated
        import ast
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "EXCLUDE_DIRS":
                vals = {e.value for e in node.value.elts}
        assert vals == {"_Templates", "_meta", ".obsidian", "generated"}

    def test_single_quoted_members_recognized(self, tmp_path):
        f = _write(tmp_path, "EXCLUDE_DIRS = {'_meta', 'generated'}\n")
        assert eie.ensure_entry(f) == "present"  # ast sees 'generated' despite quote style

    def test_regenerated_not_false_matched(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {"_meta", "regenerated"}\n')
        assert eie.ensure_entry(f) == "added"
        import ast
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "EXCLUDE_DIRS":
                vals = {e.value for e in node.value.elts}
        assert "regenerated" in vals and "generated" in vals

    def test_trailing_comma_no_corruption(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {"_meta",}\n')
        assert eie.ensure_entry(f) == "added"
        # must still parse cleanly (no ",," corruption)
        import ast
        ast.parse(f.read_text())

    def test_multiline_set_deferred_not_corrupted(self, tmp_path):
        body = 'EXCLUDE_DIRS = {\n    "_meta",\n    ".obsidian",\n}\n'
        f = _write(tmp_path, body)
        assert eie.ensure_entry(f) == "manual"
        assert f.read_text() == body  # untouched

    def test_non_string_member_deferred(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {"_meta", SOME_CONST}\n')
        assert eie.ensure_entry(f) == "manual"

    def test_absent_file(self, tmp_path):
        assert eie.ensure_entry(tmp_path / "nope.py") == "absent"

    def test_no_set_assignment(self, tmp_path):
        f = _write(tmp_path, "X = 1\n")
        assert eie.ensure_entry(f) == "manual"


class TestCli:
    def test_cli_added_exit_0(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {"_meta"}\n')
        r = subprocess.run(["python3", str(MOD_PATH), "--file", str(f)],
                           capture_output=True, text=True)
        assert r.returncode == 0 and "added" in r.stdout

    def test_cli_manual_exit_1(self, tmp_path):
        f = _write(tmp_path, 'EXCLUDE_DIRS = {\n    "_meta",\n}\n')
        r = subprocess.run(["python3", str(MOD_PATH), "--file", str(f)],
                           capture_output=True, text=True)
        assert r.returncode == 1 and "manual" in r.stdout.lower()
