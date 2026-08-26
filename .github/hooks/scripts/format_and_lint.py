#!/usr/bin/env python
"""PostToolUse hook — format files the agent just edited.

Formatting is not a judgement call, so it should not consume the agent's
attention or a review comment. This runs the formatter on the specific files
that changed and says nothing unless something needed fixing.

Deliberately narrow:

  * only files the tool actually touched, never the whole tree
  * only formatters, never linters that could fail the operation
  * never blocks — a formatting hook that stops work is a broken hook

`ruff format` handles Python. TypeScript is left to the editor's own formatter,
because invoking `pnpm` per edit adds seconds to every single tool call for a
change the editor already makes on save.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
API_DIR = REPO / "apps" / "api"
PY_TIMEOUT = 25

PATH_RE = re.compile(r"[\"']?((?:[A-Za-z]:)?[\w./\\-]+\.py)[\"']?")


def extract_paths(payload: str) -> list[Path]:
    """Pull plausible .py paths out of whatever shape the tool input took."""
    found: list[Path] = []
    for raw in PATH_RE.findall(payload):
        p = Path(raw)
        candidate = p if p.is_absolute() else (REPO / raw)
        try:
            if candidate.is_file() and candidate.suffix == ".py":
                found.append(candidate.resolve())
        except OSError:
            continue
    return sorted(set(found))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = str(event.get("tool_name") or event.get("toolName") or "")
    if "edit" not in tool_name.lower() and "write" not in tool_name.lower():
        return 0

    blob = json.dumps(event.get("tool_input") or event.get("toolInput") or {}, default=str)
    paths = extract_paths(blob)
    if not paths:
        return 0

    ruff = API_DIR / ".venv" / "Scripts" / "ruff.exe"
    if not ruff.is_file():
        ruff = API_DIR / ".venv" / "bin" / "ruff"
    if not ruff.is_file():
        return 0  # no venv yet - nothing to do, and not worth complaining about

    try:
        result = subprocess.run(
            [str(ruff), "format", *[str(p) for p in paths]],
            capture_output=True,
            text=True,
            timeout=PY_TIMEOUT,
            cwd=API_DIR,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return 0

    # ruff format prints "N files reformatted" only when it changed something.
    if "reformatted" in (result.stdout or ""):
        names = ", ".join(p.name for p in paths)
        print(json.dumps({"systemMessage": f"🎨 ruff format applied to: {names}"}))

    return 0


if __name__ == "__main__":
    sys.exit(main())
