---
name: Security & privacy rules
description: Credential handling, PII prohibition, and synthetic-data disclosure
applyTo: "**"
---

# Security and privacy — non-negotiable

Full policy: [`../../SECURITY.md`](../../SECURITY.md).

## Never write a credential anywhere git can see

No key, token, connection string, password, or SAS signature in code, config,
tests, fixtures, docs, or commit messages. Not "temporarily". Not "just to get
it working".

A push to a public remote is **publication**. Force-pushing it away does not
un-publish it. If a credential ever reaches the remote: **rotate it first**,
assume it is burned, and only then clean history.

`.env` is gitignored. `.env.example` contains placeholders only and is the sole
tracked `.env*` file.

## Azure OpenAI has no API key — do not add one

Auth is Microsoft Entra ID via `DefaultAzureCredential`. Local development
resolves your `az login` identity; Azure resolves the Container App's
user-assigned managed identity. There is nothing to store, nothing to rotate,
and nothing to leak.

If you find yourself adding `azure_openai_api_key` to `config.py`, stop. That is
the wrong fix for whatever you are debugging. See `agent/azure_openai.py`.

## Verify credentials without reading them

Never echo a secret "just to check". Confirm **presence and behaviour**:

```bash
grep -c '^AZURE_OPENAI_ENDPOINT=' .env     # count, don't print
az account show --query user.name -o tsv   # identity, not token
curl -fsS localhost:8000/api/health         # reachable + authorized?
```

`/api/health` deliberately reports whether Azure OpenAI is configured **without
revealing the endpoint or any token**. There is a test asserting exactly that
(`test_never_leaks_the_endpoint_or_a_token`). Keep it passing.

## There is no PII in this system, by design

No player names, loyalty accounts, card numbers, addresses, contact details, or
session-level tracking. SlotSight models **machines and money, never people**.

This is a deliberate architectural stance, not an oversight: the valuable
slot-floor analytics problem is about asset performance and does not require
player data. **Adding a player table is a defect, not a feature.**

If someone asks for player-level analysis, say plainly that this system has no
player data and that adding it brings regulated-data obligations these controls
do not cover.

## Synthetic data must always declare itself

Every market-intelligence payload carries `is_synthetic: true` and a disclaimer,
and every UI view showing that data carries a visible marker.

A recommendation built on invented benchmarks must never reach a screen looking
like one built on real market intelligence. This is a correctness requirement.
See [`../../NOTICE.md`](../../NOTICE.md).

## Infrastructure

No secrets in Bicep. No secrets in `azure.yaml`. Access is granted by **RBAC
role assignment to a managed identity**, never by a key in a config file.

The only generated secret in the whole deployment is the PostgreSQL admin
password, which is created at provision time and stored in Key Vault — never
written to a file, never printed to a log.

## The agent guardrail

`.github/hooks/guardrails.json` registers a `PreToolUse` hook that intercepts
**Copilot's own tool calls** and denies reads of `.env`, `secrets/**`, `*.pem`,
and destructive commands (`rm -rf`, `git push --force`, `DROP DATABASE`).

If you are denied by that hook, it is working as designed. Do not route around
it, do not disable it, and do not ask the user to disable it — find the approach
that does not need the blocked action.
