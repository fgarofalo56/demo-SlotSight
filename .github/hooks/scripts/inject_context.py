#!/usr/bin/env python
"""SessionStart hook — tells the agent where the project actually stands.

An agent that starts every session by running `git status`, `docker ps`, and
`ls specs/` burns three tool calls and a chunk of context rediscovering things
that could simply have been handed to it. This hook front-loads that.

It emits a `systemMessage`, which VS Code injects into the session context.
Everything here is cheap, read-only, and degrades to silence on failure — a
session-start hook that hangs or crashes is worse than no hook at all.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TIMEOUT = 4


def run(args: list[str]) -> str:
    try:
        out = subprocess.run(
            args, capture_output=True, text=True, timeout=TIMEOUT, cwd=REPO, check=False
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def git_context() -> list[str]:
    lines: list[str] = []
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch:
        lines.append(f"Branch: {branch}")

    status = run(["git", "status", "--porcelain"])
    if status:
        changed = len(status.splitlines())
        lines.append(f"Working tree: {changed} uncommitted file(s)")
    elif branch:
        lines.append("Working tree: clean")

    hooks_path = run(["git", "config", "--get", "core.hooksPath"])
    if hooks_path != ".githooks":
        lines.append(
            "⚠️  Local git hooks are NOT enabled. The pre-commit secret scan will "
            "not run. Fix: `git config core.hooksPath .githooks` (or `make setup`)."
        )
    return lines


def spec_context() -> list[str]:
    specs_dir = REPO / "specs"
    if not specs_dir.is_dir():
        return []

    lines: list[str] = []
    for spec in sorted(p for p in specs_dir.iterdir() if p.is_dir()):
        spec_md = spec / "spec.md"
        if not spec_md.is_file():
            continue

        status = "Unknown"
        try:
            text = spec_md.read_text(encoding="utf-8", errors="replace")
            if m := re.search(r"^\*\*Status:\*\*\s*(.+)$", text, re.M):
                status = m.group(1).strip()
        except OSError:
            pass

        tasks_md = spec / "tasks.md"
        progress = ""
        if tasks_md.is_file():
            try:
                t = tasks_md.read_text(encoding="utf-8", errors="replace")
                done = len(re.findall(r"^\s*-\s*\[x\]", t, re.M | re.I))
                total = done + len(re.findall(r"^\s*-\s*\[ \]", t, re.M))
                if total:
                    progress = f" — {done}/{total} tasks"
            except OSError:
                pass

        lines.append(f"  {spec.name}: {status}{progress}")
    return lines


def stack_context() -> list[str]:
    """Is the local stack up? Cheap check, no docker CLI dependency."""
    import socket

    lines: list[str] = []
    for label, port in (("api", 8000), ("web", 5173), ("db", 5432)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            state = "up" if s.connect_ex(("127.0.0.1", port)) == 0 else "down"
        lines.append(f"{label}:{state}")
    return [f"Local stack: {'  '.join(lines)}"]


def main() -> int:
    try:
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass  # no payload is fine; we only emit

    parts: list[str] = ["🎰 SlotSight — Neon Palms Casino Resort (all data synthetic)"]

    if git := git_context():
        parts.append("\n".join(git))

    if specs := spec_context():
        parts.append("Specs:\n" + "\n".join(specs))

    parts.extend(stack_context())

    parts.append(
        "Reminders: analytics stay deterministic and LLM-free · rank on peer_index "
        "not floor_index · money is integer cents · no secrets, no PII · "
        "run `pytest -m golden` after touching analytics."
    )

    print(json.dumps({"systemMessage": "\n\n".join(parts)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
