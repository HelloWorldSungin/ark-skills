"""Tests for relink.py — relative-link fixer after relocation."""
import importlib.util
from pathlib import Path

MOD_PATH = Path(__file__).parent / "relink.py"
spec = importlib.util.spec_from_file_location("relink", MOD_PATH)
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)


class TestRewriteLink:
    def test_rewrites_relative_target_across_depth(self):
        # old page at OLD/page.md linked to ../src/a.py ; page now at NEW/sub/page.md
        new = rl.rewrite_link("../src/a.py", old_page_dir=Path("/repo/graphify-out/obs"),
                              new_page_dir=Path("/repo/vault/generated/graphify/sub"))
        # target resolves to /repo/graphify-out/src/a.py; relpath from new page dir:
        assert new == "../../../../graphify-out/src/a.py"

    def test_leaves_absolute_url_untouched(self):
        assert rl.rewrite_link("https://x.com/a", old_page_dir=Path("/a"),
                               new_page_dir=Path("/b")) is None

    def test_leaves_anchor_untouched(self):
        assert rl.rewrite_link("#section", old_page_dir=Path("/a"),
                               new_page_dir=Path("/b")) is None


class TestProcessFile:
    def test_rewrites_markdown_link_in_file(self, tmp_path):
        old_dir = tmp_path / "graphify-out" / "obs"
        new_dir = tmp_path / "vault" / "generated" / "graphify"
        new_dir.mkdir(parents=True)
        (tmp_path / "graphify-out" / "src").mkdir(parents=True)
        (tmp_path / "graphify-out" / "src" / "a.py").write_text("x")
        page = new_dir / "page.md"
        page.write_text("See [A](../src/a.py) and [ext](https://x).")
        changed = rl.process_file(page, old_dir, new_dir)
        assert changed == 1
        assert "https://x" in page.read_text()
        assert "../src/a.py" not in page.read_text()

    def test_leaves_image_link_untouched(self, tmp_path):
        old_dir = tmp_path / "graphify-out" / "obs"
        new_dir = tmp_path / "vault" / "generated" / "graphify"
        new_dir.mkdir(parents=True)
        page = new_dir / "page.md"
        page.write_text("![diagram](assets/x.png) and [A](../src/a.py)")
        (tmp_path / "graphify-out" / "src").mkdir(parents=True)
        (tmp_path / "graphify-out" / "src" / "a.py").write_text("x")
        rl.process_file(page, old_dir, new_dir)
        assert "![diagram](assets/x.png)" in page.read_text()
