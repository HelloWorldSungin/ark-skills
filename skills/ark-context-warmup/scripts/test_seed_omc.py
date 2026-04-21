"""Tests for seed_omc: per-source content hashing + stale cleanup."""
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import content_hash_slug, parse_page, write_page, OMCPage
from seed_omc import seed, SeedSource


def _mk(title="Auth", path="vault/Architecture/Auth.md",
        body="# Auth\n\n" + "body " * 60, vault_type="architecture",
        tags=None, confidence="high"):
    return SeedSource(title=title, vault_source_path=path, body=body,
                      vault_type=vault_type, tags=tags or ["auth"],
                      confidence=confidence)


def test_seed_writes_new_page(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[_mk()])
    assert r.written == 1
    slug = content_hash_slug("vault/Architecture/Auth.md", _mk().body)
    assert (wiki / f"source-{slug}.md").exists()


def test_seed_skips_short_sources(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[_mk(body="short")])
    assert r.written == 0
    assert list(wiki.glob("source-*.md")) == []


def test_seed_idempotent_same_content(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    s = [_mk()]
    seed(wiki, chain_id="CH-A", sources=s)
    before = {p.name for p in wiki.glob("source-*.md")}
    r = seed(wiki, chain_id="CH-A", sources=s)
    assert r.written == 0
    after = {p.name for p in wiki.glob("source-*.md")}
    assert before == after


def test_seed_content_change_creates_new_hash_and_cleans_stale(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A",
         sources=[_mk(body="# v1\n\n" + "a" * 250)])
    r = seed(wiki, chain_id="CH-A",
             sources=[_mk(body="# v2\n\n" + "b" * 250)])  # same path, new content
    assert r.written == 1
    assert r.deleted_stale == 1


def test_seed_topic_shift_deletes_stale_sources(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Auth", path="vault/Architecture/Auth.md", body="# A\n\n" + "a" * 250),
        _mk(title="Users", path="vault/Architecture/Users.md", body="# B\n\n" + "b" * 250),
    ])
    assert len(list(wiki.glob("source-*.md"))) == 2
    r = seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Billing", path="vault/Architecture/Billing.md", body="# C\n\n" + "c" * 250),
    ])
    assert r.written == 1 and r.deleted_stale == 2
    assert len(list(wiki.glob("source-*.md"))) == 1


def test_seed_preserves_other_chains(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[_mk()])
    r = seed(wiki, chain_id="CH-B",
             sources=[_mk(title="Deploys", path="vault/Ops/Deploys.md",
                          body="# D\n\n" + "d" * 250)])
    assert r.deleted_stale == 0
    assert len(list(wiki.glob("source-*.md"))) == 2


def test_seed_frontmatter_has_full_provenance(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    seed(wiki, chain_id="CH-A", sources=[_mk(vault_type="research")])
    page = parse_page(next(wiki.glob("source-*.md")))
    fm = page.frontmatter
    assert fm["ark-original-type"] == "research"
    assert fm["ark-source-path"] == "vault/Architecture/Auth.md"
    assert "seed_body_hash" in fm
    assert fm["seed_chain_id"] == "CH-A"
    assert "source-warmup" in fm["tags"]
    assert fm["category"] == "architecture"  # research → architecture per mapping


def test_seed_excluded_vault_types(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    for bad in ("session-log", "epic", "story", "bug", "task"):
        r = seed(wiki, chain_id="CH-A",
                 sources=[_mk(vault_type=bad, body="x" * 250,
                              path=f"vault/{bad}.md")])
        assert r.written == 0


def test_seed_same_title_different_path_produces_distinct_slugs(tmp_path):
    wiki = tmp_path / ".omc" / "wiki"
    wiki.mkdir(parents=True)
    r = seed(wiki, chain_id="CH-A", sources=[
        _mk(title="Auth", path="vault/A/Auth.md", body="# A\n\n" + "x" * 250),
        _mk(title="Auth", path="vault/B/Auth.md", body="# A\n\n" + "x" * 250),
    ])
    assert r.written == 2
    assert len(list(wiki.glob("source-*.md"))) == 2
