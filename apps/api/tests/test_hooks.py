"""Tests for the Copilot agent guardrail hooks.

These live in the API test suite because that is what CI already runs, but they
test `.github/hooks/scripts/` — the layer that intercepts **Copilot's own tool
calls** before they execute.

This is the control most repositories lack. `.gitignore` stops you staging a
secret and CI stops you pushing one, but neither stops an agent from reading
`.env` and pasting the contents into a transcript or a file it writes next.

A guard with a hole in it is worse than no guard, because it is trusted. These
tests exist because the first version of this hook *looked* correct and silently
let `secrets/prod.json` through: the pattern required a path separator before
`secrets`, and in the serialized tool input the character before it is a quote.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GUARD = REPO / ".github" / "hooks" / "scripts" / "guard_secrets.py"
CONTEXT = REPO / ".github" / "hooks" / "scripts" / "inject_context.py"
GATES = REPO / ".github" / "hooks" / "scripts" / "verify_gates.py"


def run_hook(script: Path, payload: dict) -> dict:
    """Run a hook the way VS Code does: JSON on stdin, JSON on stdout."""
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO,
        check=False,
    )
    assert result.returncode == 0, f"hook crashed: {result.stderr}"
    out = result.stdout.strip()
    return json.loads(out) if out else {}


def is_denied(payload: dict) -> bool:
    out = run_hook(GUARD, payload)
    return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def read_file(path: str) -> dict:
    return {"tool_name": "edit/readFile", "tool_input": {"filePath": path}}


def shell(command: str) -> dict:
    return {"tool_name": "runCommands", "tool_input": {"command": command}}


class TestGuardBlocksCredentialPaths:
    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            "./.env",
            "E:/repos/demo-SlotSight/.env",
            ".env.production",
            "secrets/prod.json",
            "apps/api/secrets/db.yaml",
            "certs/server.pem",
            "keys/private.key",
            "cert.pfx",
            "/home/user/.ssh/id_rsa",
            "~/.aws/credentials",
            "credentials.json",
            "service-account.json",
            "azure.publishsettings",
        ],
    )
    def test_denied(self, path: str) -> None:
        assert is_denied(read_file(path)), f"{path!r} should have been denied"

    @pytest.mark.parametrize(
        "path",
        [
            ".env.example",
            "SECURITY.md",
            ".gitignore",
            "apps/api/src/slotsight/main.py",
            "apps/web/src/App.tsx",
            "docs/getting-started.md",
            "infra/main.bicep",
        ],
    )
    def test_allowed(self, path: str) -> None:
        """A guard that blocks ordinary work gets disabled, then protects nothing."""
        assert not is_denied(read_file(path)), f"{path!r} should have been allowed"


class TestGuardBlocksDangerousCommands:
    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf apps/api",
            "rm -fr /",
            "rm -r -f build",
            "git push --force origin main",
            "git push -f",
            "git reset --hard HEAD~3",
            "git clean -fdx",
            "psql -c 'DROP DATABASE slotsight'",
            "psql -c 'TRUNCATE TABLE machines'",
            "azd down --purge",
            "docker system prune -a",
        ],
    )
    def test_denied(self, command: str) -> None:
        assert is_denied(shell(command)), f"{command!r} should have been denied"

    def test_no_verify_is_blocked(self) -> None:
        """--no-verify bypasses the local secret scan, which is the point of it."""
        assert is_denied(shell("git commit --no-verify -F msg.txt"))

    @pytest.mark.parametrize(
        "command",
        [
            "uv run pytest -q",
            "git status",
            "git diff --cached",
            "docker compose up -d",
            "pnpm build",
            "az account show",
            "make gates",
        ],
    )
    def test_allowed(self, command: str) -> None:
        assert not is_denied(shell(command)), f"{command!r} should have been allowed"


class TestGuardRobustness:
    def test_malformed_input_does_not_block_everything(self) -> None:
        """A crashing guard must fail open, not brick the session.

        Failing closed here would make a bad JSON payload look like a security
        policy, and the first thing anyone does with a hook that blocks
        everything is delete it.
        """
        result = subprocess.run(
            [sys.executable, str(GUARD)],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO,
            check=False,
        )
        assert result.returncode == 0
        assert "deny" not in result.stdout

    def test_empty_input_is_handled(self) -> None:
        assert not is_denied({})

    def test_denial_explains_what_to_do_instead(self) -> None:
        """A block without an alternative just gets worked around."""
        out = run_hook(GUARD, read_file(".env"))
        reason = out["hookSpecificOutput"]["permissionDecisionReason"]
        assert ".env.example" in reason
        assert "SECURITY.md" in reason


class TestSessionStartHook:
    def test_emits_a_system_message(self) -> None:
        out = run_hook(CONTEXT, {})
        assert "systemMessage" in out
        msg = out["systemMessage"]
        assert "SlotSight" in msg
        assert "peer_index" in msg

    def test_does_not_leak_secrets(self) -> None:
        msg = run_hook(CONTEXT, {}).get("systemMessage", "")
        lowered = msg.lower()
        assert "cognitiveservices.azure.com" not in lowered
        assert "password" not in lowered


class TestStopHook:
    def test_does_not_crash(self) -> None:
        run_hook(GATES, {})

    def test_never_halts_the_session(self) -> None:
        """Warn, don't block. Plenty of sessions legitimately end mid-task."""
        out = run_hook(GATES, {})
        assert out.get("continue") is not False
