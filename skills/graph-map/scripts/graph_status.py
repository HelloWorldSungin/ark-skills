"""Graph freshness helper for /graph-map.

Writes/reads {vault}/generated/graphify/_graphify-meta.json and reports whether
the committed graphify-out/graph.json has drifted from the relocated vault copy.

Exit codes (check): 0 fresh, 1 stale, 2 meta/graph missing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def write_meta(graph: Path, out: Path, version: str, timestamp: str) -> None:
    graph = Path(graph)
    if not graph.exists():
        raise FileNotFoundError(f"graph not found: {graph}")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "graph_sha256": sha256_file(graph),
        "graphify_version": version,
        "generated_at": timestamp,
    }, indent=2) + "\n")


def check(graph: Path, meta: Path) -> int:
    graph, meta = Path(graph), Path(meta)
    if not graph.exists() or not meta.exists():
        return 2
    try:
        recorded = json.loads(meta.read_text()).get("graph_sha256")
    except (json.JSONDecodeError, OSError):
        return 2
    return 0 if recorded == sha256_file(graph) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="graphify graph freshness helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write-meta")
    w.add_argument("--graph", required=True)
    w.add_argument("--out", required=True)
    w.add_argument("--version", required=True)
    w.add_argument("--timestamp", required=True)
    c = sub.add_parser("check")
    c.add_argument("--graph", required=True)
    c.add_argument("--meta", required=True)
    args = p.parse_args(argv)
    if args.cmd == "write-meta":
        try:
            write_meta(Path(args.graph), Path(args.out), args.version, args.timestamp)
        except FileNotFoundError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 2
        print(f"wrote {args.out}")
        return 0
    rc = check(Path(args.graph), Path(args.meta))
    print({0: "fresh", 1: "stale", 2: "missing"}[rc])
    return rc


if __name__ == "__main__":
    sys.exit(main())
