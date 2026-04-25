#!/usr/bin/env python3
"""Skill-graph audit for wiki-lint (Arkskill-012-S3).

Runs six checks on the ark-skills plugin repo:
  1. Catalog drift          - HARD on count mismatch; WARN on description drift
  2. Section-anchor refs    - WARN on broken `references/<file>.md § Section X.Y`
  3. Description shape      - WARN heuristic (length / verbs / overlap)
  4. Active-body length     - WARN at 500 lines (Anthropic guidance)
  5. Chain reachability     - WARN on unclassified slash-commands
  6. Compound-to-compound   - WARN soft (do not block; live examples are correct)

Filesystem ground truth:  find skills -maxdepth 2 -name SKILL.md (excludes shared/)
External registry:        skills/ark-workflow/references/external-skills.yaml

Exits 1 if any HARD error is found, else 0. Run from the plugin repo root.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO / "skills"
CHAINS_DIR = SKILLS_DIR / "ark-workflow" / "chains"
REGISTRY = SKILLS_DIR / "ark-workflow" / "references" / "external-skills.yaml"

# Description-shape heuristic vocabulary.
TRIGGER_VERBS = {
    "use", "run", "audit", "search", "mine", "process", "initialize", "distill",
    "validate", "discover", "configure", "bump", "convert", "generate", "sync",
    "query", "lint", "ingest", "file", "write", "read", "parse", "build",
    "analyze", "scan", "monitor", "fetch", "load", "save", "update", "normalize",
    "classify", "dispatch", "orchestrate", "coordinate", "render", "route",
    "trigger", "execute", "cleanup", "verify", "check", "test", "commit",
    "deploy", "ship", "install", "setup", "archive", "refactor", "extract",
    "evaluate", "review", "diagnose", "report", "show", "create", "manage",
    "track", "compose", "compile", "transform", "merge", "filter", "select",
    "store", "retrieve",
}

# Catalog drift: WARN threshold for description Jaccard similarity (word sets).
DESC_JACCARD_WARN_BELOW = 0.30
# Description shape: WARN threshold for cross-skill description overlap.
SHAPE_JACCARD_WARN_ABOVE = 0.55
# Active body length budget.
ACTIVE_BODY_WARN_LINES = 500


# ─── findings ──────────────────────────────────────────────────────────────

@dataclass
class Finding:
    severity: str  # "ERROR" or "WARN"
    rule: str
    message: str
    location: str = ""


def fmt(f: Finding) -> str:
    loc = f" [{f.location}]" if f.location else ""
    return f"{f.severity:5} {f.rule:24} {f.message}{loc}"


# ─── helpers ───────────────────────────────────────────────────────────────

def internal_skills() -> dict[str, Path]:
    """Map /<name> -> Path(SKILL.md). Filesystem ground truth, excludes shared/."""
    out = {}
    for skill_md in SKILLS_DIR.glob("*/SKILL.md"):
        name = skill_md.parent.name
        if name == "shared":
            continue
        out[f"/{name}"] = skill_md
    return out


def parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML-ish frontmatter via field-targeted regex.

    SKILL.md `description` values frequently contain unquoted colons
    ("Do NOT use for: ...") which break PyYAML's mapping parse. Frontmatter
    is a flat name/description/tags shape, so we parse field-by-field.
    """
    text = skill_md.read_text()
    m = re.match(r"^---\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    fm = m.group(1)
    out: dict = {}
    name = re.search(r"^name:\s*(.+?)\s*$", fm, re.MULTILINE)
    if name:
        out["name"] = name.group(1).strip().strip('"').strip("'")
    # description may be a single long line; capture until next top-level key.
    desc = re.search(
        r"^description:\s*(.+?)(?=\n[a-zA-Z][\w-]*:\s|\Z)",
        fm, re.MULTILINE | re.DOTALL,
    )
    if desc:
        out["description"] = desc.group(1).strip().strip('"').strip("'")
    return out


def words(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9-]+", s or "")}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ─── parsers for catalog rows ──────────────────────────────────────────────

def parse_skills_agents() -> dict[str, str]:
    """skills/AGENTS.md: skill rows under '## Subdirectories' only.

    The 'Subdirectory Conventions' subsection (under '## For AI Agents')
    has identical row shape — must scope to the Subdirectories block.
    """
    out = {}
    text = (SKILLS_DIR / "AGENTS.md").read_text()
    in_section = False
    for line in text.splitlines():
        if re.match(r"^##\s+Subdirectories\b", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if not in_section:
            continue
        m = re.match(r"\|\s*`([a-z][a-z0-9-]+)/`\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            name, desc = m.group(1), m.group(2).strip()
            if name == "shared":
                continue
            out[f"/{name}"] = desc
    return out


def parse_available_skills_section(path: Path) -> dict[str, str]:
    """README.md (table) / CLAUDE.md (bullets): both formats supported."""
    out = {}
    in_section = False
    text = path.read_text()
    for line in text.splitlines():
        if re.match(r"^##\s+Available Skills\b", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if not in_section:
            continue
        # Bullet form (CLAUDE.md): - `/<name>` — <description>
        m = re.match(r"^-\s+`(/[a-z][a-z0-9-]+)`\s*[—–-]\s*(.+?)\s*$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
            continue
        # Table form (README.md): | `/<name>` | <category> | <description> | <source> |
        m = re.match(
            r"^\|\s*`(/[a-z][a-z0-9-]+)`\s*\|\s*[^|]*\|\s*([^|]+?)\s*\|",
            line,
        )
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


# ─── checks ────────────────────────────────────────────────────────────────

def check_catalog_drift(internal: dict[str, Path]) -> list[Finding]:
    f: list[Finding] = []
    fs_set = set(internal.keys())

    catalogs = {
        "skills/AGENTS.md": parse_skills_agents(),
        "README.md": parse_available_skills_section(REPO / "README.md"),
        "CLAUDE.md": parse_available_skills_section(REPO / "CLAUDE.md"),
    }

    # Count mismatch is HARD.
    for path, parsed in catalogs.items():
        if set(parsed.keys()) != fs_set:
            missing = fs_set - parsed.keys()
            extra = parsed.keys() - fs_set
            parts = []
            if missing:
                parts.append(f"missing: {sorted(missing)}")
            if extra:
                parts.append(f"extra: {sorted(extra)}")
            f.append(Finding(
                "ERROR", "catalog-drift",
                f"{path} has {len(parsed)} skills, filesystem has {len(fs_set)}; {'; '.join(parts)}",
                path,
            ))

    # Description drift across catalogs (WARN). Pairwise Jaccard.
    common = set.intersection(*(set(p.keys()) for p in catalogs.values())) if catalogs else set()
    for slash in sorted(common):
        descs = {path: catalogs[path][slash] for path in catalogs}
        word_sets = {p: words(d) for p, d in descs.items()}
        names = list(descs.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                sim = jaccard(word_sets[names[i]], word_sets[names[j]])
                if sim < DESC_JACCARD_WARN_BELOW:
                    f.append(Finding(
                        "WARN", "description-drift",
                        f"{slash}: descriptions diverge between {names[i]} and {names[j]} (jaccard={sim:.2f})",
                        slash,
                    ))
                    break  # one warn per skill is enough
            else:
                continue
            break
    return f


def resolve_reference(src: Path, rel: str) -> Path | None:
    """Resolve a `references/<file>.md` citation, walking ancestors to find it.

    Chain prose often writes 'references/omc-integration.md' meaning the
    sibling references/ directory of the parent skill, not the citing file's
    own subdir. Walk up the tree, then fall back to a unique repo-wide match
    by basename.
    """
    # Direct (citing-file relative).
    p = (src.parent / rel).resolve()
    if p.exists():
        return p
    # Walk up: try each ancestor as the base.
    for ancestor in src.parents:
        candidate = (ancestor / rel)
        if candidate.exists():
            return candidate
        if ancestor == REPO:
            break
    # Repo-wide basename match (last resort; only accept unique).
    basename = Path(rel).name
    matches = [m for m in REPO.rglob(basename) if "/tests/fixtures/" not in str(m)]
    if len(matches) == 1:
        return matches[0]
    return None


def check_anchor_refs(internal: dict[str, Path]) -> list[Finding]:
    """Verify ``references/<file>.md § Section X.Y`` cites resolve to a heading.

    Anchor scheme in the repo:
      ``## Section N — Title``        (top-level)
      ``### N.M Title``               (sub-numbering, no "Section" prefix)
    """
    f: list[Finding] = []
    cite_re = re.compile(
        r"`?(?P<rel>[\w/.-]*references/[\w./-]+\.md)`?\s*§\s*Section\s+(?P<num>\d+(?:\.\d+)*)",
        re.IGNORECASE,
    )

    files = list(SKILLS_DIR.rglob("*.md")) + list(SKILLS_DIR.rglob("*.py"))
    files = [p for p in files if "/tests/fixtures/" not in str(p) and "/templates/" not in str(p)]

    for src in files:
        text = src.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for m in cite_re.finditer(line):
                rel = m.group("rel")
                num = m.group("num")
                target = resolve_reference(src, rel)
                if target is None:
                    f.append(Finding(
                        "WARN", "anchor-ref-broken",
                        f"target file not found: {rel}",
                        f"{src.relative_to(REPO)}:{line_no}",
                    ))
                    continue
                target_text = target.read_text(errors="ignore")
                if "." in num:
                    pat = re.compile(rf"^###\s+{re.escape(num)}\b", re.MULTILINE)
                else:
                    pat = re.compile(rf"^##\s+Section\s+{re.escape(num)}\b", re.MULTILINE)
                if not pat.search(target_text):
                    f.append(Finding(
                        "WARN", "anchor-ref-broken",
                        f"§ Section {num} not found in {target.relative_to(REPO)}",
                        f"{src.relative_to(REPO)}:{line_no}",
                    ))
    return f


def check_description_shape(internal: dict[str, Path]) -> list[Finding]:
    f: list[Finding] = []
    descs: dict[str, tuple[str, set[str]]] = {}
    for slash, path in internal.items():
        fm = parse_frontmatter(path)
        desc = (fm.get("description") or "").strip()
        if not desc:
            f.append(Finding("WARN", "description-shape",
                             "missing description in frontmatter", slash))
            continue
        descs[slash] = (desc, words(desc))
        # Length sanity.
        if len(desc) < 50:
            f.append(Finding("WARN", "description-shape",
                             f"description too short ({len(desc)} chars): {desc!r}", slash))
        # Trigger-verb presence (heuristic, not phrase-match).
        if not (words(desc) & TRIGGER_VERBS):
            f.append(Finding("WARN", "description-shape",
                             "no recognized trigger verb (use/run/audit/...)", slash))
    # Pairwise overlap.
    keys = sorted(descs.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            sim = jaccard(descs[keys[i]][1], descs[keys[j]][1])
            if sim > SHAPE_JACCARD_WARN_ABOVE:
                f.append(Finding(
                    "WARN", "description-shape",
                    f"high overlap with {keys[j]} (jaccard={sim:.2f}); add negative-routing clause",
                    keys[i],
                ))
    return f


def check_active_body_length(internal: dict[str, Path]) -> list[Finding]:
    f: list[Finding] = []
    for slash, path in sorted(internal.items()):
        n = sum(1 for _ in path.read_text().splitlines())
        if n > ACTIVE_BODY_WARN_LINES:
            f.append(Finding(
                "WARN", "active-body-length",
                f"{n} lines (> {ACTIVE_BODY_WARN_LINES}); consider moving non-load-bearing prose to references/",
                slash,
            ))
    return f


def chain_command_tokens() -> dict[Path, set[str]]:
    """Map chain Path -> set of leading-token slash-commands extracted from backtick spans."""
    out = {}
    for chain in sorted(CHAINS_DIR.glob("*.md")):
        text = chain.read_text()
        cmds = set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9_-]+)", text))
        out[chain] = cmds
    return out


def check_chain_reachability(internal: dict[str, Path]) -> list[Finding]:
    f: list[Finding] = []
    if not REGISTRY.exists():
        f.append(Finding("ERROR", "chain-reachability",
                         f"missing external registry: {REGISTRY.relative_to(REPO)}",
                         "external-skills.yaml"))
        return f
    try:
        data = yaml.safe_load(REGISTRY.read_text()) or {}
    except yaml.YAMLError as e:
        f.append(Finding("ERROR", "chain-reachability",
                         f"YAML parse error: {e}",
                         str(REGISTRY.relative_to(REPO))))
        return f
    registered = {entry["slash"] for entry in (data.get("skills") or [])}
    classified = set(internal.keys()) | registered

    for chain, cmds in chain_command_tokens().items():
        for cmd in sorted(cmds - classified):
            f.append(Finding(
                "WARN", "chain-reachability",
                f"unclassified slash-command (not internal, not in external-skills.yaml): {cmd}",
                str(chain.relative_to(REPO)),
            ))
    return f


def detect_compounds(internal: dict[str, Path]) -> set[str]:
    """A compound: an internal SKILL.md whose body invokes >= 2 distinct internal slash-commands,
    OR has a chains/ subdir."""
    compounds: set[str] = set()
    for slash, path in internal.items():
        if (path.parent / "chains").is_dir():
            compounds.add(slash)
            continue
        body = path.read_text()
        invoked = set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9_-]+)", body))
        invoked &= set(internal.keys())
        invoked.discard(slash)  # ignore self-references
        if len(invoked) >= 2:
            compounds.add(slash)
    return compounds


def check_compound_to_compound(internal: dict[str, Path]) -> list[Finding]:
    f: list[Finding] = []
    compounds = detect_compounds(internal)
    # 1) Chain steps that call other compounds.
    for chain, cmds in chain_command_tokens().items():
        for cmd in sorted(cmds & compounds):
            f.append(Finding(
                "WARN", "compound-to-compound",
                f"chain calls compound {cmd}; verify bounded mode + handback contract",
                str(chain.relative_to(REPO)),
            ))
    # 2) Non-chain compound bodies that call other compounds.
    for slash in sorted(compounds):
        path = internal[slash]
        body = path.read_text()
        invoked = set(re.findall(r"`(/[a-zA-Z][a-zA-Z0-9_-]+)", body)) & compounds
        invoked.discard(slash)
        if (path.parent / "chains").is_dir():
            continue  # already covered via chain inspection
        for callee in sorted(invoked):
            f.append(Finding(
                "WARN", "compound-to-compound",
                f"{slash} body invokes compound {callee}",
                str(path.relative_to(REPO)),
            ))
    return f


# ─── runner ────────────────────────────────────────────────────────────────

def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"ERROR: skills/ not found under {REPO}", file=sys.stderr)
        return 2
    internal = internal_skills()

    findings: list[Finding] = []
    findings += check_catalog_drift(internal)
    findings += check_anchor_refs(internal)
    findings += check_description_shape(internal)
    findings += check_active_body_length(internal)
    findings += check_chain_reachability(internal)
    findings += check_compound_to_compound(internal)

    errors = [x for x in findings if x.severity == "ERROR"]
    warns = [x for x in findings if x.severity == "WARN"]

    print(f"Skill-Graph Audit: {len(internal)} internal skills")
    print(f"  ERRORs: {len(errors)}")
    print(f"  WARNs:  {len(warns)}")
    print()
    if errors:
        print("── ERRORS ──")
        for x in errors:
            print(fmt(x))
        print()
    if warns:
        print("── WARNINGS ──")
        for x in warns:
            print(fmt(x))
        print()
    if not errors and not warns:
        print("Clean.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
