"""Ensure the vault index generator excludes the graphify quarantine dir.

Adds an entry (default "generated") to a Python set literal (default
`EXCLUDE_DIRS`) in a `generate-index.py`, so graphify's `vault/generated/`
quarantine is not indexed. Called by `/graph-map setup` against the resolved
vault path (symlink-aware), so it works for in-repo AND symlinked external vaults
without going through ark-update's project-root path validation.

Corruption-proof: parses the file with `ast` and reconstructs the set literal
from its string members, so quote style / trailing commas / a `regenerated`
member can't trip it. Single-line string-set literals are auto-edited; anything
else (multiline, non-string members, `set([...])` call, unparseable) is DEFERRED
with status "manual" — never edited blindly.

Usage: python3 ensure_index_exclusion.py --file <generate-index.py> [--set EXCLUDE_DIRS] [--entry generated]
Status (stdout): added | present | absent | manual.  Exit: 0 for added/present/absent, 1 for manual.
"""
import argparse
import ast
import sys
from pathlib import Path


def _find_set_assign(tree, set_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == set_name for t in node.targets
        ):
            return node
    return None


def ensure_entry(file: Path, set_name: str = "EXCLUDE_DIRS", entry: str = "generated") -> str:
    file = Path(file)
    if not file.exists():
        return "absent"
    text = file.read_text()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "manual"
    node = _find_set_assign(tree, set_name)
    if node is None or not isinstance(node.value, ast.Set):
        return "manual"
    s = node.value
    members = []
    for el in s.elts:
        if isinstance(el, ast.Constant) and isinstance(el.value, str):
            members.append(el.value)
        else:
            return "manual"  # non-string element — don't touch
    if entry in members:
        return "present"
    # Only auto-edit a single-line literal; reconstruct it from members to avoid
    # any splice/comma corruption.
    if s.lineno != s.end_lineno:
        return "manual"
    new_literal = "{" + ", ".join(f'"{m}"' for m in members + [entry]) + "}"
    lines = text.splitlines(keepends=True)
    i = s.lineno - 1
    line = lines[i]
    lines[i] = line[: s.col_offset] + new_literal + line[s.end_col_offset :]
    file.write_text("".join(lines))
    return "added"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--set", dest="set_name", default="EXCLUDE_DIRS")
    ap.add_argument("--entry", default="generated")
    args = ap.parse_args(argv)
    status = ensure_entry(Path(args.file), args.set_name, args.entry)
    print(status)
    if status == "manual":
        print(
            f"MANUAL: add \"{args.entry}\" to {args.set_name} in {args.file} "
            f"(set is multiline/non-literal — not edited to avoid corruption).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
