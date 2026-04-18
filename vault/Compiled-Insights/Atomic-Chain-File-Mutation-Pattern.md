---
title: "Atomic Chain-File Mutation Pattern"
type: compiled-insight
tags:
  - compiled-insight
  - pattern
  - python
  - stdlib
  - atomic-writes
  - concurrency
  - ark-workflow
summary: "fcntl.flock(LOCK_EX) + tempfile.mkstemp + os.replace — the stdlib-only pattern used in context_probe.py to serialize concurrent read-modify-write sequences against a shared markdown file with frontmatter + checklist content. Both torn-write protection and lost-update prevention in one shape."
source-sessions:
  - "[[S011-Ark-Workflow-Context-Budget-Probe]]"
source-tasks:
  - "[[Arkskill-007-context-budget-probe]]"
created: 2026-04-17
last-updated: 2026-04-17
---

# Atomic Chain-File Mutation Pattern

## Summary

A stdlib-only shape for atomic read-modify-write against a file that two
or more callers may edit concurrently. Used by `/ark-workflow`'s
`.ark-workflow/current-chain.md` where three CLI modes
(`record-proceed`, `record-reset`, `check-off`) can mutate frontmatter
and body content in parallel with no coordination at the call site.
Combines file locking (for lost-update prevention) and temp-file
rename (for torn-write prevention) in one helper.

## The helper

```python
import fcntl
import os
import tempfile
from pathlib import Path


class chain_file:
    """Namespace for atomic chain-file mutations."""

    @staticmethod
    def atomic_update(chain_path, mutator_fn):
        chain_path = Path(chain_path)
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = chain_path.with_suffix(chain_path.suffix + ".lock")

        with open(lock_path, "w") as lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            try:
                _do_update(chain_path, mutator_fn)
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


def _do_update(chain_path: Path, mutator_fn):
    try:
        original = chain_path.read_text()
    except FileNotFoundError:
        original = ""
    new_content = mutator_fn(original)
    fd, tmp_name = tempfile.mkstemp(
        prefix=chain_path.name + ".",
        suffix=".tmp",
        dir=str(chain_path.parent),
    )
    try:
        with os.fdopen(fd, "w") as tmp_f:
            tmp_f.write(new_content)
        os.replace(tmp_name, chain_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
```

Call sites pass a mutator function of shape `(str) -> str`:

```python
chain_file.atomic_update(
    Path(".ark-workflow/current-chain.md"),
    lambda text: _set_proceed_past_level(text, "nudge"),
)
```

## Why both locking and temp-rename

Two distinct problems need two distinct mitigations:

| Problem | Mitigation | What goes wrong without it |
|---------|-----------|---------------------------|
| **Torn writes** — one process writes partial bytes, another reads mid-write | `tempfile.mkstemp` + `os.replace` | Reader sees half-written content; JSON/YAML parsers crash |
| **Lost updates** — two processes both `read()` old state, both `write()` back, second overwrites first | `fcntl.flock(LOCK_EX)` on a sibling lock file | Frontmatter edit overwrites checklist edit or vice versa |

Temp-rename alone fixes torn writes but not lost updates (both processes
can read the same old state, both rename their temp file, the last
rename wins and the other's mutation is lost). Locking alone fixes lost
updates but readers during the brief write window can still see torn
content if the writer doesn't use atomic rename.

## Why `mkstemp` in the same directory

`os.replace` is atomic only within the same filesystem. Placing the temp
file next to the target guarantees they're on the same filesystem — a
temp file in `/tmp/` would defeat atomicity on systems where `/tmp/`
is tmpfs while the working directory is on a different volume.

The `prefix=chain_path.name + "."` + `suffix=".tmp"` pattern produces
visible temp files like `current-chain.md.abc123.tmp` that are easy
to clean up if a crash leaves one behind. `mkstemp` creates the file
with mode 0600 and unique name, avoiding symlink races that `mktemp`
(deprecated) exposed.

## Lock file lifecycle

The sibling `.lock` file is never cleaned up. This is intentional:

- An abandoned lock file is harmless — it's 0 bytes.
- Cleaning it up requires another lock, which reintroduces race windows.
- The OS reclaims the flock when the file descriptor closes, even on
  crash — there's no stale-lock problem.

## Known limitation (P2 follow-up)

`open(lock_path, "w")` follows symlinks and truncates. In a hostile
workspace, a precreated `.ark-workflow/current-chain.md.lock` symlink
could clobber an arbitrary user-writable file. The fix:

```python
fd = os.open(
    lock_path,
    os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
    0o600,
)
stat_info = os.fstat(fd)
if not stat.S_ISREG(stat_info.st_mode):
    os.close(fd)
    raise OSError("lock path is not a regular file")
# then flock(fd) as before
```

Filed as P2-1 in the v1.17.0 follow-up notes. Low practical risk (an
attacker with write access to the project can already do worse) but
cheap to harden.

## When to use this pattern

- Multiple processes / shell invocations may edit the same file
  concurrently
- The file is a single source of truth (not append-only — append-only
  logs can use `O_APPEND` instead)
- The mutation is a read-modify-write, not a blind overwrite
- Stdlib-only is a requirement (no `portalocker`, no `filelock`)

When **not** to use:

- Append-only logs (just use `O_APPEND` writes — the kernel serializes)
- Read-only access (no mutation, no coordination needed)
- Files edited by a single long-running process (in-process mutex is
  simpler and faster than flock)
- Cross-machine coordination (flock is per-host; for networked shares,
  reach for a proper lock service)

## Verification

`skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats`
includes a 2-second concurrent-write stress test: background loop rapidly
calls `check-off` while foreground loop alternates `record-proceed` and
`record-reset`. Assertion after teardown:

```bash
[ "$(grep -Ec '^proceed_past_level: (null|nudge)$' chain-file)" -eq 1 ]
```

A torn write or lost update would leave the file with zero or two or
garbage-valued `proceed_past_level:` lines. 14/14 bats runs pass.

## References

- `skills/ark-workflow/scripts/context_probe.py` — canonical implementation
- `skills/ark-workflow/scripts/integration/test_probe_skill_invocation.bats` — stress test
- [[S011-Ark-Workflow-Context-Budget-Probe]] — ship session
- [[Arkskill-007-context-budget-probe]] — epic
- Python docs: `tempfile.mkstemp`, `os.replace`, `fcntl.flock`
