"""Safe path resolution for ark-update ops.

Contract: ``safe_resolve(project_root, candidate)`` returns a fully-resolved
absolute ``Path`` that is guaranteed to lie inside ``project_root``.

Three rejection classes (all raise ``PathTraversalError``):

1. **Absolute paths** — ``candidate`` must be a relative path string or a
   ``Path`` with no root component. Absolute inputs are refused unconditionally
   because the caller controls the root; accepting absolute paths would bypass
   the root-scoping guarantee entirely.

2. **`..`-escape** — after ``(project_root / candidate).resolve()`` the
   resulting absolute path must start with ``project_root.resolve()``. A
   ``..`` component that crosses the project root boundary (e.g.
   ``"../../etc/passwd"``) is refused.

3. **Symlink-escape** — if any component along the resolved path is a
   symlink whose resolved target lies outside ``project_root``, the path is
   refused. ``Path.resolve()`` already follows symlinks, so the ``..``-escape
   check handles this transitively: if the symlink target is outside the root,
   the resolved path won't start with the resolved root and is refused.
"""
from __future__ import annotations

from pathlib import Path


class PathTraversalError(Exception):
    """Raised when ``safe_resolve`` detects an attempted path traversal."""


def safe_resolve(project_root: Path, candidate: "str | Path") -> Path:
    """Resolve *candidate* relative to *project_root* and verify it stays inside.

    Parameters
    ----------
    project_root:
        The directory that defines the trusted boundary. Need not be resolved
        yet — this function resolves it internally.
    candidate:
        A **relative** path (string or ``Path``) to resolve under
        ``project_root``. Absolute paths are refused immediately (rejection
        class 1).

    Returns
    -------
    Path
        A fully-resolved absolute ``Path`` guaranteed to be equal to or nested
        under ``project_root.resolve()``.

    Raises
    ------
    PathTraversalError
        On any of the three rejection classes: absolute path, ``..``-escape,
        or symlink-escape (symlinks are followed by ``Path.resolve()``; if the
        resolved target escapes the root it is caught by the ``..``-escape
        check).
    """
    candidate = Path(candidate)

    # Rejection class 1: absolute paths
    if candidate.is_absolute():
        raise PathTraversalError(
            f"Candidate path must be relative, got absolute path: {candidate!r}"
        )

    resolved_root = project_root.resolve()
    resolved_candidate = (project_root / candidate).resolve()

    # Rejection classes 2 & 3: ..-escape and symlink-escape.
    # Path.resolve() follows symlinks, so both cases reduce to the same check:
    # the resolved candidate must start with the resolved root.
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        raise PathTraversalError(
            f"Path {candidate!r} resolves to {resolved_candidate!r}, "
            f"which is outside project root {resolved_root!r}. "
            f"Possible traversal via '..', absolute symlink, or symlink pointing outside root."
        )

    return resolved_candidate
