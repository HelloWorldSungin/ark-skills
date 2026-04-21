"""Pick the relevant session-bridge page for the current warmup."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "python"
sys.path.insert(0, str(_SHARED))

from omc_page import parse_page  # noqa: E402


CHAIN_MATCH_WINDOW_S = 7 * 24 * 3600
NO_MATCH_WINDOW_S = 48 * 3600


def pick_bridge(wiki_dir: Path, *, current_chain_id: str) -> Optional[Path]:
    if not wiki_dir.is_dir():
        return None
    now = time.time()
    best_match = None
    best_any = None
    for path in wiki_dir.glob("*.md"):
        try:
            page = parse_page(path)
        except ValueError:
            continue
        tags = page.frontmatter.get("tags") or []
        if "session-bridge" not in tags:
            continue
        chain_id = page.frontmatter.get("chain_id")
        mtime = path.stat().st_mtime
        age = now - mtime
        if chain_id == current_chain_id and age <= CHAIN_MATCH_WINDOW_S:
            if best_match is None or mtime > best_match[0]:
                best_match = (mtime, path)
        if best_any is None or mtime > best_any[0]:
            best_any = (mtime, path)
    if best_match:
        return best_match[1]
    if best_any and (now - best_any[0]) <= NO_MATCH_WINDOW_S:
        return best_any[1]
    return None


def _cli() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--wiki-dir", required=True)
    p.add_argument("--chain-id", required=True)
    args = p.parse_args()
    picked = pick_bridge(Path(args.wiki_dir), current_chain_id=args.chain_id)
    if picked:
        print(picked)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
