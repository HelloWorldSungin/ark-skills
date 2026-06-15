"""Tests for graph_status.py — graph freshness/drift helper."""
import importlib.util
import json
import subprocess
from pathlib import Path

MOD_PATH = Path(__file__).parent / "graph_status.py"
spec = importlib.util.spec_from_file_location("graph_status", MOD_PATH)
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


class TestHash:
    def test_sha256_of_file_is_stable(self, tmp_path):
        f = tmp_path / "graph.json"
        f.write_text('{"nodes": [1, 2, 3]}')
        h1 = gs.sha256_file(f)
        h2 = gs.sha256_file(f)
        assert h1 == h2 and len(h1) == 64


class TestWriteMeta:
    def test_write_meta_records_hash_and_version(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"nodes": []}')
        out = tmp_path / "_graphify-meta.json"
        gs.write_meta(graph, out, version="0.8.39", timestamp="2026-06-15T00:00:00Z")
        data = json.loads(out.read_text())
        assert data["graph_sha256"] == gs.sha256_file(graph)
        assert data["graphify_version"] == "0.8.39"
        assert data["generated_at"] == "2026-06-15T00:00:00Z"

    def test_write_meta_missing_graph_raises(self, tmp_path):
        import pytest
        with pytest.raises(FileNotFoundError):
            gs.write_meta(tmp_path / "nope.json", tmp_path / "_graphify-meta.json",
                          version="0.8.39", timestamp="t")


class TestCheck:
    def _setup(self, tmp_path, same):
        graph = tmp_path / "graph.json"
        graph.write_text('{"nodes": []}')
        meta = tmp_path / "_graphify-meta.json"
        gs.write_meta(graph, meta, version="0.8.39", timestamp="t")
        if not same:
            graph.write_text('{"nodes": [99]}')
        return graph, meta

    def test_fresh_returns_zero(self, tmp_path):
        graph, meta = self._setup(tmp_path, same=True)
        assert gs.check(graph, meta) == 0

    def test_stale_returns_one(self, tmp_path):
        graph, meta = self._setup(tmp_path, same=False)
        assert gs.check(graph, meta) == 1

    def test_missing_meta_returns_two(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text("{}")
        assert gs.check(graph, tmp_path / "nope.json") == 2


class TestCli:
    def test_cli_check_stale_exit_1(self, tmp_path):
        graph = tmp_path / "graph.json"
        graph.write_text('{"nodes": []}')
        meta = tmp_path / "_graphify-meta.json"
        subprocess.run(["python3", str(MOD_PATH), "write-meta", "--graph", str(graph),
                        "--out", str(meta), "--version", "0.8.39", "--timestamp", "t"], check=True)
        graph.write_text('{"nodes": [1]}')
        r = subprocess.run(["python3", str(MOD_PATH), "check", "--graph", str(graph),
                            "--meta", str(meta)], capture_output=True, text=True)
        assert r.returncode == 1
        assert "stale" in r.stdout.lower()
