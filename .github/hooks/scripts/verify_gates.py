#!/usr/bin/env python
"""Stop hook — flag source changes that were never gated.

The failure this exists to prevent: an agent edits `analytics/`, summarises the
work confidently, and stops — without ever running the tests. The summary reads
like success. The build is red. Nobody finds out until the next person pulls.

So at the end of a session we check whether source files changed and whether
the gates plausibly ran. If source moved and nothing was verified, we say so.

**This warns, it does not block.** `continue: false` would end the session,
which is the wrong response to "you might want to run the tests" — plenty of
sessions legitimately end mid-task. The goal is to make an unverified change
visible, not to prevent it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

WATCHED = ("apps/api/src/", "apps/web/src/", "mcp/", "infra/")

# Artifacts a test run leaves behind. If none is newer than the newest source
# edit, the gates almost certainly did not run after that edit.
TEST_ARTIFACTS = (
    "apps/api/.pytest_cache/CACHEDIR.TAG",
    "apps/api/.pytest_cache",
    "apps/api/.ruff_cache",
    "apps/api/.mypy_cache",
)

# Touching these means the golden tests specifically need to run.
GOLDEN_SENSITIVE = (
    "apps/api/src/slotsight/analytics/",
    "apps/api/src/slotsight/seed/",
)


def run(args: list[str]) -> str:
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=5, cwd=REPO, check=False
        )
        return r.stdout
    except (subprocess.SubprocessError, OSError):
        return ""


def changed_files() -> list[str]:
    out = run(["git", "status", "--porcelain"])
    files: list[str] = []
    for line in out.splitlines():
        if len(line) > 3:
            path = line[3:].strip().strip('"')
            files.append(path.replace("\\", "/"))
    return files


def newest_mtime(paths: list[str]) -> float:
    newest = 0.0
    for rel in paths:
        p = REPO / rel
        try:
            if p.is_file():
                newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue
    return newest


def newest_artifact_mtime() -> float:
    newest = 0.0
    for rel in TEST_ARTIFACTS:
        p = REPO / rel
        try:
            if p.exists():
                newest = max(newest, p.stat().st_mtime)
        except OSError:
            continue
    return newest


def main() -> int:
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    changed = changed_files()
    source_changed = [f for f in changed if f.startswith(WATCHED)]
    if not source_changed:
        return 0

    source_time = newest_mtime(source_changed)
    artifact_time = newest_artifact_mtime()

    # A small grace window: a test run that finished just before the last edge
    # of an edit is still a run.
    if artifact_time >= source_time - 60:
        return 0

    golden_needed = [f for f in source_changed if f.startswith(GOLDEN_SENSITIVE)]

    lines = [
        "⚠️  Source changed but the gates do not appear to have run this session.",
        "",
        f"Changed ({len(source_changed)}): "
        + ", ".join(source_changed[:6])
        + (" …" if len(source_changed) > 6 else ""),
        "",
        "Run before calling this done:",
        "    cd apps/api && uv run ruff check . && uv run mypy src && uv run pytest",
    ]

    if golden_needed:
        lines += [
            "    cd apps/api && uv run pytest -m golden -v",
            "",
            "The golden tests are required here — you changed the analytics or the "
            "generator, which is exactly what they exist to protect.",
        ]

    lines += ["", 'Reminder: "it should work now" is not a result.']

    age = time.time() - artifact_time if artifact_time else None
    if age and age > 3600:
        lines.append(f"(Last test artifact is {age / 3600:.1f}h old.)")

    print(json.dumps({"systemMessage": "\n".join(lines)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
