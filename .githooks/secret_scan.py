#!/usr/bin/env python
"""
SlotSight credential guard — layer 2 of the defense described in SECURITY.md.

Scans staged (pre-commit) or outgoing (pre-push) content for credential shapes
and PII before it can reach a remote.

This is *fast local feedback*, not the backstop. It is trivially defeated by
`git commit --no-verify`. The real backstop is the CI secret scan over full
history (.github/workflows/secret-scan.yml), which runs server-side where
--no-verify cannot reach it.

Usage:
    python .githooks/secret_scan.py --staged
    python .githooks/secret_scan.py --range <sha1>..<sha2>

Exit codes:
    0  clean
    1  findings (blocks the operation)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass

# ───────────────────────────────────────────────────────────────────────────
# Paths that must never be committed at all, regardless of content.
# ───────────────────────────────────────────────────────────────────────────
FORBIDDEN_PATHS = [
    (re.compile(r"(^|/)\.env$"), ".env file"),
    (re.compile(r"(^|/)\.env\.(?!example$)[A-Za-z0-9_.-]+$"), ".env.* variant"),
    (re.compile(r"(^|/)secrets?/"), "secrets/ directory"),
    (re.compile(r"\.(pem|key|pfx|p12|jks|keystore)$"), "private key / keystore"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$"), "SSH private key"),
    (re.compile(r"(^|/)(credentials|service-account)\.json$"), "cloud credential file"),
    (re.compile(r"\.publishsettings$"), "Azure publish settings"),
    (re.compile(r"(^|/)\.azure/"), "azd/az local state"),
]

# ───────────────────────────────────────────────────────────────────────────
# Content patterns. Each is (name, regex, why).
#
# Deliberately biased toward *credential shapes* rather than keyword matches,
# because keyword matching drowns in false positives on a repo whose whole
# subject matter is "how to configure secrets safely".
# ───────────────────────────────────────────────────────────────────────────
CONTENT_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "private-key-block",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
        "PEM private key block",
    ),
    (
        "aws-access-key",
        re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        "AWS access key ID",
    ),
    (
        "github-token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"),
        "GitHub token",
    ),
    (
        "slack-token",
        re.compile(r"\bxox[abpsr]-[A-Za-z0-9-]{10,}\b"),
        "Slack token",
    ),
    (
        "openai-key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        "OpenAI-style API key",
    ),
    (
        "azure-storage-conn",
        re.compile(r"DefaultEndpointsProtocol=https?;.*AccountKey=[A-Za-z0-9+/=]{40,}"),
        "Azure Storage connection string",
    ),
    (
        "azure-sas",
        re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{40,}"),
        "Azure SAS signature",
    ),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "JWT (may contain claims/identity)",
    ),
    (
        "db-url-with-password",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)"
            r"(?:\+\w+)?://[^\s:/@]+:(?!change-me|placeholder|password|<)[^\s:/@]{6,}@"
        ),
        "database URL with embedded password",
    ),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|passwd|password|token|client[_-]?secret|"
            r"access[_-]?key)\b\s*[:=]\s*[\"']?(?!$)"
            r"(?!change-me|changeme|placeholder|example|dummy|redacted|xxx|todo|none|null|"
            r"your-|<|\$\{|\{\{|\*{3})"
            r"[A-Za-z0-9+/_=-]{16,}[\"']?"
        ),
        "hardcoded secret assignment",
    ),
    # ── PII ────────────────────────────────────────────────────────────────
    (
        "ssn",
        re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
        "US Social Security Number",
    ),
    (
        "credit-card",
        re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6011\d{12})\b"),
        "credit card number",
    ),
]

# Files whose *content* we skip. These legitimately describe credential shapes.
CONTENT_SCAN_SKIP = re.compile(
    r"(?:"
    r"(^|/)\.githooks/secret_scan\.py$"          # this file: full of patterns
    r"|(^|/)\.github/hooks/scripts/guard_secrets\.py$"
    r"|(^|/)SECURITY\.md$"
    r"|(^|/)\.gitignore$"
    r"|(^|/)\.gitleaks\.toml$"
    r"|(^|/)(uv|pnpm|package|poetry)-?lock(\.yaml|\.json)?$"
    r"|\.(png|jpe?g|gif|ico|webp|woff2?|ttf|eot|pdf|zip|gz|whl|so|dll)$"
    r")"
)

# Line-level opt-out for a reviewed false positive.
ALLOW_MARKER = re.compile(r"#\s*noqa:\s*secret|//\s*noqa:\s*secret|<!--\s*noqa:\s*secret\s*-->")

# ───────────────────────────────────────────────────────────────────────────
# Console safety.
#
# Windows consoles default to cp1252, which cannot encode box-drawing glyphs.
# A guard that crashes while reporting a finding is worse than no guard: git
# sees a non-zero exit and blocks, but the developer never learns why. So we
# force UTF-8 where we can and degrade to ASCII where we can't.
# ───────────────────────────────────────────────────────────────────────────
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass


def _unicode_ok() -> bool:
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "─✗⛔".encode(enc)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


UNI = _unicode_ok()

BAR = ("─" if UNI else "-") * 62
CROSS = "✗" if UNI else "x"
STOP = "⛔" if UNI else "!!"

# Colors only when attached to a real terminal.
if sys.stdout.isatty():
    RED, YEL, DIM, RST = "\033[31m", "\033[33m", "\033[2m", "\033[0m"
else:
    RED = YEL = DIM = RST = ""


@dataclass
class Finding:
    path: str
    line_no: int
    rule: str
    why: str
    excerpt: str


def _run(args: list[str]) -> str:
    return subprocess.run(
        args, capture_output=True, text=True, errors="replace", check=False
    ).stdout


def staged_files() -> list[str]:
    out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [p for p in out.splitlines() if p.strip()]


def range_files(rev_range: str) -> list[str]:
    out = _run(["git", "diff", "--name-only", "--diff-filter=ACMR", rev_range])
    return [p for p in out.splitlines() if p.strip()]


def blob(path: str, staged: bool, rev: str | None) -> str:
    ref = ":" + path if staged else f"{rev}:{path}"
    return _run(["git", "show", ref])


def redact(text: str) -> str:
    """Show enough to locate the finding, never enough to leak it."""
    t = text.strip()
    if len(t) > 90:
        t = t[:90] + "…"
    return re.sub(r"[A-Za-z0-9+/_=-]{12,}", lambda m: m.group()[:4] + "…REDACTED", t)


def scan(paths: list[str], staged: bool, rev: str | None) -> list[Finding]:
    findings: list[Finding] = []

    for path in paths:
        norm = path.replace("\\", "/")

        for pattern, label in FORBIDDEN_PATHS:
            if pattern.search(norm):
                findings.append(
                    Finding(norm, 0, "forbidden-path", f"{label} must never be committed", "")
                )
                break

        if CONTENT_SCAN_SKIP.search(norm):
            continue

        content = blob(path, staged, rev)
        if not content or "\x00" in content[:1024]:
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            if len(line) > 4000 or ALLOW_MARKER.search(line):
                continue
            for rule, pattern, why in CONTENT_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(norm, i, rule, why, redact(line)))
                    break

    return findings


def report(findings: list[Finding], mode: str) -> None:
    print(f"\n{RED}{BAR}{RST}")
    print(f"{RED}  {STOP}  BLOCKED: credential or PII detected{RST}")
    print(f"{RED}{BAR}{RST}\n")

    for f in findings:
        loc = f"{f.path}:{f.line_no}" if f.line_no else f.path
        print(f"  {RED}{CROSS}{RST} {loc}")
        print(f"      {YEL}{f.rule}{RST} - {f.why}")
        if f.excerpt:
            print(f"      {DIM}{f.excerpt}{RST}")
        print()

    print(f"  {len(findings)} finding(s). {mode} aborted.\n")
    print(f"  {YEL}If a credential already reached a remote:{RST}")
    print("      1. ROTATE IT FIRST - assume it is burned.")
    print("      2. Then clean history.\n")
    print(f"  {DIM}False positive? Add `# noqa: secret` to the line, or extend")
    print(f"  CONTENT_SCAN_SKIP in .githooks/secret_scan.py - with a reason.{RST}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Block secrets and PII from being committed.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true", help="scan the git index (pre-commit)")
    g.add_argument("--range", dest="rev_range", help="scan a commit range (pre-push)")
    args = ap.parse_args()

    if args.staged:
        paths, rev, mode = staged_files(), None, "Commit"
    else:
        paths, rev, mode = (
            range_files(args.rev_range),
            args.rev_range.split("..")[-1],
            "Push",
        )

    if not paths:
        return 0

    findings = scan(paths, staged=args.staged, rev=rev)
    if not findings:
        return 0

    report(findings, mode)
    return 1


if __name__ == "__main__":
    sys.exit(main())
