"""Tests for secret_scan.py — pre-commit safety scan over graphify output."""
import importlib.util
import subprocess
from pathlib import Path

MOD_PATH = Path(__file__).parent / "secret_scan.py"
spec = importlib.util.spec_from_file_location("secret_scan", MOD_PATH)
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)


class TestScanText:
    def test_detects_private_key(self):
        hits = ss.scan_text("-----BEGIN RSA PRIVATE KEY-----\nabc")
        assert any(h[0] == "private_key" for h in hits)

    def test_detects_aws_key(self):
        hits = ss.scan_text("aws_key = AKIAIOSFODNN7EXAMPLE")
        assert any(h[0] == "aws_access_key" for h in hits)

    def test_detects_assigned_secret(self):
        hits = ss.scan_text('api_token = "s3cr3tValueLongEnoughToMatch123"')
        assert any(h[0] == "assigned_secret" for h in hits)

    def test_clean_text_no_hits(self):
        assert ss.scan_text("just some graph nodes and edges") == []


class TestScanDir:
    def test_flags_oversized_file(self, tmp_path):
        big = tmp_path / "graph.html"
        big.write_bytes(b"x" * (2 * 1024 * 1024))
        findings = ss.scan_dir(tmp_path, max_bytes=1024 * 1024)
        assert any(f["kind"] == "oversized" for f in findings)

    def test_flags_secret_file(self, tmp_path):
        (tmp_path / "report.md").write_text("token = AKIAIOSFODNN7EXAMPLE")
        findings = ss.scan_dir(tmp_path, max_bytes=10 * 1024 * 1024)
        assert any(f["kind"] == "secret" for f in findings)


class TestCli:
    def test_cli_exit_1_on_finding(self, tmp_path):
        (tmp_path / "leak.txt").write_text("-----BEGIN PRIVATE KEY-----")
        r = subprocess.run(["python3", str(MOD_PATH), str(tmp_path)],
                           capture_output=True, text=True)
        assert r.returncode == 1

    def test_cli_exit_0_when_clean(self, tmp_path):
        (tmp_path / "ok.md").write_text("nodes and edges only")
        r = subprocess.run(["python3", str(MOD_PATH), str(tmp_path)],
                           capture_output=True, text=True)
        assert r.returncode == 0
