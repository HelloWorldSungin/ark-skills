"""HTML-comment marker parsing and region I/O for ark-update.

Marker syntax
-------------
Every ark-managed region is delimited by a pair of HTML comment markers:

    <!-- ark:begin id=<id> version=<semver> -->
    ... region content ...
    <!-- ark:end id=<id> -->

Rules (all are hard invariants — violations raise ``MarkerIntegrityError``):

1. **id format** — must match ``[a-z][a-z0-9-]*`` (lowercase letters, digits,
   hyphens; must start with a letter).
2. **Nesting is illegal** — a ``<!-- ark:begin ... -->`` inside an already-open
   region is an error.  Nested markers corrupt the ownership model.
3. **Mismatched-id refusal** — if the ``id=`` on ``<!-- ark:end ... -->`` does
   not match the most recently opened ``<!-- ark:begin ... -->``, the file is
   considered corrupted and parsing refuses with ``MarkerIntegrityError``.
4. **Unclosed region** — an ``<!-- ark:begin ... -->`` with no matching
   ``<!-- ark:end ... -->`` is an error.

Inside / outside zero-touch rule
---------------------------------
``replace_region`` rewrites ONLY the bytes delimited by the begin/end marker
pair (inclusive of the marker lines themselves).  Bytes outside the markers are
preserved byte-for-byte.  Callers must never assume that content outside markers
can be inspected or modified by any engine operation.

Version= drift-signal semantics (codex P2-3)
--------------------------------------------
The ``version=`` attribute in ``<!-- ark:begin ... -->`` is a **drift signal**,
not a content hash.  ``TargetProfileOp.detect_drift()`` callers MUST treat
``parsed_version != target_profile.version`` as drift, triggering a
rewrite+backup even when the region's text content is otherwise byte-identical
to the target template.  This keeps markers honest about which managed-region
version they were written by, enabling future version-gated logic.

On write: ``replace_region`` and ``insert_region`` emit the ``version=``
attribute from ``target_profile.version`` (the caller supplies it).
On read: ``extract_regions`` parses the ``version=`` attribute from the begin
marker and populates ``ManagedRegion.version``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Public regex constants (load-bearing — callers may import these)
# ---------------------------------------------------------------------------

BEGIN_MARKER_RE = re.compile(
    r"<!-- ark:begin id=([a-z][a-z0-9-]*) version=(\d+\.\d+\.\d+) -->"
)
END_MARKER_RE = re.compile(
    r"<!-- ark:end id=([a-z][a-z0-9-]*) -->"
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MarkerIntegrityError(Exception):
    """Raised when marker parsing detects a structural violation.

    Covers: nested markers, mismatched id, unclosed region.
    """


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class ManagedRegion:
    """A parsed ark-managed region within a file.

    Attributes
    ----------
    id:
        Stable region identifier (matches the ``id=`` attribute).
    version:
        Semver from the ``version=`` attribute of the begin marker.
        Populated on read by ``extract_regions``; used as a drift signal by
        ``TargetProfileOp.detect_drift()`` — see module docstring.
    file:
        The file this region was parsed from.
    begin_line:
        1-based line number of the ``<!-- ark:begin ... -->`` line.
    end_line:
        1-based line number of the ``<!-- ark:end ... -->`` line.
    content:
        The text between the begin and end marker lines (not including the
        marker lines themselves).
    """

    id: str
    version: str
    file: Path
    begin_line: int
    end_line: int
    content: str


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def extract_regions(file_path: Path) -> list[ManagedRegion]:
    """Parse all ark-managed regions from *file_path*.

    Returns
    -------
    list[ManagedRegion]
        Regions in document order.

    Raises
    ------
    MarkerIntegrityError
        On nested markers, mismatched id, or unclosed region.
    FileNotFoundError
        If *file_path* does not exist.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    regions: list[ManagedRegion] = []
    # Stack of (region_id, version, begin_line_1based, content_lines_so_far)
    stack: list[tuple[str, str, int, list[str]]] = []

    for lineno_0based, line in enumerate(lines):
        lineno = lineno_0based + 1  # 1-based
        line_stripped = line.rstrip("\n").rstrip("\r")

        begin_match = BEGIN_MARKER_RE.search(line_stripped)
        end_match = END_MARKER_RE.search(line_stripped)

        if begin_match:
            region_id = begin_match.group(1)
            version = begin_match.group(2)
            if stack:
                raise MarkerIntegrityError(
                    f"{file_path}:{lineno}: nested ark:begin marker "
                    f"id={region_id!r} inside already-open region "
                    f"id={stack[-1][0]!r} (opened at line {stack[-1][2]}). "
                    f"Nested markers are illegal."
                )
            stack.append((region_id, version, lineno, []))

        elif end_match:
            end_id = end_match.group(1)
            if not stack:
                raise MarkerIntegrityError(
                    f"{file_path}:{lineno}: <!-- ark:end id={end_id!r} --> "
                    f"with no matching <!-- ark:begin -->."
                )
            open_id, open_version, open_line, content_lines = stack.pop()
            if end_id != open_id:
                raise MarkerIntegrityError(
                    f"{file_path}:{lineno}: mismatched marker ids — "
                    f"<!-- ark:begin id={open_id!r} --> (line {open_line}) "
                    f"closed by <!-- ark:end id={end_id!r} -->."
                )
            regions.append(
                ManagedRegion(
                    id=open_id,
                    version=open_version,
                    file=file_path,
                    begin_line=open_line,
                    end_line=lineno,
                    content="".join(content_lines),
                )
            )

        else:
            if stack:
                # Accumulate content line (with original line ending).
                stack[-1][3].append(line)

    if stack:
        open_id, _, open_line, _ = stack[0]
        raise MarkerIntegrityError(
            f"{file_path}: unclosed <!-- ark:begin id={open_id!r} --> "
            f"at line {open_line} (no matching <!-- ark:end -->)."
        )

    return regions


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------

def replace_region(
    file_path: Path,
    region_id: str,
    new_content: str,
    new_version: str,
) -> None:
    """Replace the content of the named region and update its ``version=``.

    Outside-markers zero-touch invariant: bytes on every line outside the
    begin/end marker pair are preserved byte-for-byte.  Only the begin marker
    line (to update ``version=``), the content lines, and the end marker line
    are replaced.

    Parameters
    ----------
    file_path:
        The file containing the region.
    region_id:
        The ``id=`` of the region to replace.
    new_content:
        Replacement text for the region body.  Should NOT include marker lines.
        A trailing newline is normalised (added if absent) so the end marker
        always starts on its own line.
    new_version:
        The ``version=`` value to write into the begin marker (drift-signal
        semantics — callers supply ``target_profile.version``).

    Raises
    ------
    KeyError
        If no region with *region_id* exists in the file.
    MarkerIntegrityError
        On structural violations found during re-parse.
    """
    regions = extract_regions(file_path)
    matching = [r for r in regions if r.id == region_id]
    if not matching:
        raise KeyError(
            f"No ark-managed region with id={region_id!r} found in {file_path}."
        )
    region = matching[0]

    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Determine the line ending in use (default to \n).
    line_ending = "\n"
    if lines and lines[0].endswith("\r\n"):
        line_ending = "\r\n"

    new_begin = f"<!-- ark:begin id={region_id} version={new_version} -->{line_ending}"
    new_end = f"<!-- ark:end id={region_id} -->{line_ending}"

    # Ensure new_content ends with a single newline so the end marker is on its own line.
    if new_content and not new_content.endswith("\n"):
        new_content = new_content + line_ending

    # begin_line and end_line are 1-based.
    before = lines[: region.begin_line - 1]
    after = lines[region.end_line :]  # lines after the end marker

    # Keep original line ending on last "after" line if file ended without newline.
    new_lines = before + [new_begin] + [new_content] + [new_end] + after

    # If the original file did NOT end with a newline, strip the trailing newline
    # we may have added from the last "after" line — but only when "after" is empty
    # (end marker was the last line).
    new_text = "".join(new_lines)

    file_path.write_text(new_text, encoding="utf-8")


def insert_region(
    file_path: Path,
    region_id: str,
    version: str,
    content: str,
    insertion_point: str = "eof",
) -> None:
    """Insert a new ark-managed region into *file_path*.

    Parameters
    ----------
    file_path:
        Target file.  Must already exist.
    region_id:
        Stable region id (``[a-z][a-z0-9-]*``).
    version:
        Semver string to embed in the begin marker.
    content:
        Region body text (marker lines are generated automatically).
    insertion_point:
        Where to insert.  v1.0 supports ``'eof'`` only — appends the region
        (with a blank separator line) at the end of the file.

    Raises
    ------
    ValueError
        If *insertion_point* is not ``'eof'`` (unsupported in v1.0).
    FileNotFoundError
        If *file_path* does not exist.
    """
    if insertion_point != "eof":
        raise ValueError(
            f"insert_region only supports insertion_point='eof' in v1.0, "
            f"got {insertion_point!r}."
        )

    existing_text = file_path.read_text(encoding="utf-8")

    # Determine line ending.
    line_ending = "\r\n" if "\r\n" in existing_text else "\n"

    # Ensure we start on a new line.
    separator = "" if (not existing_text or existing_text.endswith("\n")) else line_ending

    if content and not content.endswith("\n"):
        content = content + line_ending

    block = (
        f"{separator}"
        f"<!-- ark:begin id={region_id} version={version} -->{line_ending}"
        f"{content}"
        f"<!-- ark:end id={region_id} -->{line_ending}"
    )

    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(block)
