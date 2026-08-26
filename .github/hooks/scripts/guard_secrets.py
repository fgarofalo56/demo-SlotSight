#!/usr/bin/env python
"""PreToolUse guard — intercepts GitHub Copilot's own tool calls.

This is the layer most repositories do not have, and the one worth
understanding: `.gitignore` stops you staging a secret and CI stops you pushing
one, but **neither stops an agent from reading `.env` and pasting its contents
into a chat transcript**, a summary, or a file it writes next.

This hook runs before every tool call, inspects what the agent is about to do,
and denies:

  * reads or writes touching `.env`, `secrets/**`, `*.pem`, `*.key`, `*.pfx`
  * destructive shell commands (`rm -rf`, `git push --force`, `DROP DATABASE`)
  * `git commit --no-verify`, which would bypass the local secret scan

Protocol: VS Code passes the event as JSON on stdin. Emitting
`hookSpecificOutput.permissionDecision: "deny"` blocks that single tool call
while leaving the session running, so the agent can read the reason and choose
a different approach.

Documented in SECURITY.md as layer 3 of four. Try it: ask Copilot to read
`.env` in this repository and watch it get refused.
"""

from __future__ import annotations

import json
import re
import sys

# ── Paths the agent must never touch ───────────────────────────────────────
#
# These match against the tool input *serialized as JSON*, so a path can be
# preceded by a quote, a separator, whitespace, or nothing at all. Every
# pattern therefore anchors on a permissive boundary class rather than assuming
# a leading `/`. Getting that wrong is how `secrets/prod.json` sails straight
# through a guard that looks correct.
_B = r"""(^|[/\\"'\s:,=(\[])"""

FORBIDDEN_PATHS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(_B + r"\.env($|[/\\\"'\s.])(?!example)"), "the .env file"),
    (re.compile(_B + r"secrets?[/\\]", re.I), "the secrets directory"),
    (re.compile(r"\.(pem|key|pfx|p12|jks|keystore)([\"'\s,\]}]|$)", re.I), "a private key"),
    (re.compile(_B + r"id_(rsa|dsa|ecdsa|ed25519)([\"'\s,\]}]|$)"), "an SSH private key"),
    (re.compile(r"(credentials|service-account)\.json", re.I), "a cloud credential file"),
    (re.compile(r"\.publishsettings", re.I), "Azure publish settings"),
    (re.compile(_B + r"\.aws[/\\]", re.I), "AWS credentials"),
    (re.compile(_B + r"\.ssh[/\\]", re.I), "the SSH directory"),
]

# ── Commands that are destructive or bypass a control ──────────────────────
DANGEROUS_COMMANDS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)+", re.I),
        "a recursive/forced delete",
    ),
    (
        re.compile(r"\bgit\s+push\b[^\n|;]*\s(--force|-f)\b", re.I),
        "a force push (this rewrites published history)",
    ),
    (
        re.compile(r"\bgit\s+(commit|push)\b[^\n|;]*--no-verify\b", re.I),
        "a commit/push that skips the local secret scan",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
        "a hard reset (this discards uncommitted work)",
    ),
    (
        re.compile(r"\b(DROP|TRUNCATE)\s+(DATABASE|TABLE|SCHEMA)\b", re.I),
        "a destructive SQL statement",
    ),
    (
        re.compile(r"\bazd\s+down\b", re.I),
        "an Azure teardown",
    ),
    (
        re.compile(r"\bdocker\s+(system\s+)?prune\b[^\n|;]*(-a|--all)", re.I),
        "a full Docker prune",
    ),
    (
        re.compile(r"\bgit\s+clean\b[^\n|;]*-[a-zA-Z]*[fx]", re.I),
        "a forced clean (this deletes untracked files)",
    ),
]

# Reading these is fine — they *describe* the patterns rather than containing
# secrets, and blocking them would make the repo impossible to work on.
ALLOWLIST = re.compile(
    r"(\.env\.example"
    r"|\.gitignore"
    r"|SECURITY\.md"
    r"|guard_secrets\.py"
    r"|secret_scan\.py"
    r"|security\.instructions\.md"
    r"|\.gitleaks\.toml)"
)


def deny(reason: str, suggestion: str) -> None:
    """Block this single tool call, leaving the session alive."""
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"{reason}\n\n{suggestion}",
                }
            }
        )
    )
    sys.exit(0)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # A guard that crashes must not become a guard that blocks everything.
        return 0

    tool_name = str(event.get("tool_name") or event.get("toolName") or "")
    tool_input = event.get("tool_input") or event.get("toolInput") or {}

    # Flatten the input so we do not have to know each tool's argument shape -
    # a new tool with a differently-named path field is still covered.
    blob = json.dumps(tool_input, default=str)

    # Strip allowlisted filenames before matching, so `.env.example` does not
    # trip the `.env` rule.
    scannable = ALLOWLIST.sub("<allowed>", blob)

    for pattern, label in FORBIDDEN_PATHS:
        if pattern.search(scannable):
            deny(
                f"🔒 Blocked: this tool call touches {label}.",
                "SlotSight forbids agents reading or writing credential-bearing "
                "paths — see SECURITY.md, layer 3.\n"
                "If you need configuration values, read `.env.example`, which "
                "holds placeholders only. To verify a credential is present, "
                "check presence and behaviour (`grep -c '^KEY=' .env`, "
                "`GET /api/health`) rather than reading the value.",
            )

    if tool_name in ("runCommands", "run_in_terminal", "bash", "shell") or "command" in blob:
        for pattern, label in DANGEROUS_COMMANDS:
            if pattern.search(blob):
                deny(
                    f"🛑 Blocked: this command performs {label}.",
                    "Destructive and control-bypassing commands require a human. "
                    "Explain what you want to do and why, and let the operator "
                    "run it.",
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
