---
title: "Python 3.14 @dataclass + future annotations + spec_from_file_location Pitfall"
type: compiled-insight
tags:
  - compiled-insight
  - python
  - gotcha
  - dataclass
summary: "On Python 3.14, combining @dataclass with `from __future__ import annotations` breaks when the module is loaded via importlib.util.spec_from_file_location without being registered in sys.modules. Dataclass internals read sys.modules[cls.__module__].__dict__ and get None."
source-sessions:
  - "[[S006-Ark-Context-Warmup-Ship]]"
source-tasks:
  - "[[Arkskill-002-ark-context-warmup]]"
created: 2026-04-13
last-updated: 2026-04-13
---

# Python 3.14 @dataclass + future annotations + spec_from_file_location

## The Bug

Combining these three things breaks on Python 3.14:

1. `from __future__ import annotations` at the top of the module
2. `@dataclass` on a class in that module
3. Module loaded via `importlib.util.spec_from_file_location(...)` without being registered in `sys.modules`

Error surface:

```
AttributeError: 'NoneType' object has no attribute '__dict__'. Did you mean: '__dir__'?
  at dataclasses.py:762 in _is_type
    ns = sys.modules.get(cls.__module__).__dict__
```

## Root Cause

Dataclass's `_is_type` helper (Python 3.14 `dataclasses.py` line ~762) resolves string annotations at class-build time by reading `sys.modules[cls.__module__].__dict__`. When the module is loaded via `spec_from_file_location` under a name like `"executor"` that isn't registered in `sys.modules`, the lookup returns `None` and the attribute access on it fails.

Pre-3.14 Python didn't hit this code path for simple dataclasses. Python 3.14 tightened annotation resolution.

## Workaround

Pick one, depending on constraints:

1. **Drop `from __future__ import annotations` from that specific file.** Use `typing.Optional[X]` instead of `X | None` for union types. Keep future annotations in sibling files that don't have `@dataclass`.

2. **Register the module in sys.modules before exec.** In the test loader:

   ```python
   import sys, importlib.util
   spec = importlib.util.spec_from_file_location("executor", path)
   mod = importlib.util.module_from_spec(spec)
   sys.modules["executor"] = mod  # ← add this
   spec.loader.exec_module(mod)
   ```

   This lets `dataclass` find the module's `__dict__` at class-build time.

## Context From S006

Found while adding `from __future__ import annotations` to 5 `/ark-context-warmup` script files for Python 3.9 compat (codex P2 #5, per PEP 563). The future import worked on 4 files. On `executor.py`, the `@dataclass ShellResult` broke because the test harness uses `spec_from_file_location` to load the module (not `importlib.import_module`) and doesn't register it in `sys.modules`.

Chose workaround 1 because it's contained: `executor.py` uses `typing.Optional[X]` (3 uses), the other 4 files use future annotations. A module docstring documents the exception so future readers don't reintroduce the conflict.

## Detection

If a test harness dynamically loads modules via `spec_from_file_location` (common in skill-plugin codebases where scripts live outside the package import path):

- Running the test suite raises `AttributeError: 'NoneType' object has no attribute '__dict__'` after adding `from __future__ import annotations` to a file containing `@dataclass`.
- The traceback points at `dataclasses.py` `_is_type` or `_process_class`.

## See Also

- PEP 563 (postponed annotation evaluation)
- [[Codex-Review-Non-Convergence]] — codex pass 5 incorrectly flagged the post-fix `dict | None` annotations as a Python 3.9 blocker; verified false because `from __future__ import annotations` stringifies them per PEP 563
- [[Plugin-Architecture-and-Context-Discovery]] — skill plugins commonly use `spec_from_file_location` because scripts are loaded by path, not package import
