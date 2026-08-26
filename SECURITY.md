# Security Policy

## 🎯 Scope

SlotSight is a **public teaching repository**. It contains no production
systems, no real operator data, and — by design — **no secrets**. See
[`NOTICE.md`](NOTICE.md).

That does not make security posture optional. This repo is meant to be *copied*,
so it demonstrates the layered credential controls a real project should carry.

---

## 🔐 The rule

> **No credential, key, token, connection string, or piece of PII is ever
> committed to this repository. Not in code, not in config, not in a test
> fixture, not in a commit message, not "temporarily".**

A push to a public remote is **publication**. Force-pushing it away does not
un-publish it — the content is already cloned, cached, and indexed. If a
credential ever reaches this remote, the correct order is:

1. **Rotate the credential first.** Assume it is burned.
2. *Then* clean history.
3. Then figure out how the guard was bypassed.

---

## 🛡️ Defense in depth

A single control is a single point of failure. This repo layers four, because
each one defeats a different failure mode.

| Layer | File | Stops | Defeated by |
|---|---|---|---|
| **1. Ignore** | [`.gitignore`](.gitignore) | Accidentally staging `.env`, `*.pem`, `secrets/` | `git add -f` |
| **2. Local hooks** | [`.githooks/`](.githooks/) | Committing/pushing credential-shaped content | `--no-verify` |
| **3. Agent guardrail** | [`.github/hooks/`](.github/hooks/) | **Copilot itself** reading `.env` or running destructive commands | Not applicable to humans |
| **4. CI secret scan** | [`.github/workflows/secret-scan.yml`](.github/workflows/secret-scan.yml) | Anything the above missed, **across full history** | Nothing. This is the backstop. |

Layers 1–3 are *fast local feedback*. Layer 4 is the one that actually holds,
because it runs server-side over `--all` history where `--no-verify` cannot
reach it.

### Enabling the local hooks

Local git hooks are **not** installed by cloning — git requires opt-in:

```bash
git config core.hooksPath .githooks
```

`make setup` does this for you. Verify with:

```bash
git config --get core.hooksPath   # → .githooks
```

### The agent guardrail (layer 3)

This is the layer most repos don't have. `.github/hooks/guardrails.json`
registers a `PreToolUse` hook that intercepts **GitHub Copilot's own tool
calls** and denies:

- reads of `.env`, `secrets/**`, `*.pem`, `*.key`, `*.pfx`
- `rm -rf`, `git push --force`, `DROP DATABASE`, `TRUNCATE`

Ask Copilot to read `.env` in this repo and watch it get denied. That is
working as designed, and it is the single best demonstration in the repo of why
agent hooks matter.

---

## 🔑 How credentials actually reach this app

**Local development** — via `.env`, which is gitignored. Copy the template:

```bash
cp .env.example .env
```

Then fill it in locally. `.env.example` contains **placeholders only** and is
the only `.env*` file tracked by git.

**Azure OpenAI** uses **Microsoft Entra ID**, not API keys:

```python
from azure.identity.aio import DefaultAzureCredential
```

You authenticate with `az login`. There is **no API key to leak** because the
app never accepts one. Locally this resolves to your `az` identity; in Azure it
resolves to the Container App's user-assigned managed identity.

**Azure deployment** — zero secrets in Bicep. The managed identity is granted
`Cognitive Services OpenAI User` and `AcrPull` via RBAC role assignments. The
only generated secret is the PostgreSQL admin password, which is created at
provision time and stored in Key Vault — never emitted to a file, never printed.

### Verifying a credential is present without reading it

Never echo a secret "just to check". Verify **presence and behavior**:

```bash
# Presence — count, don't print
grep -c '^AZURE_OPENAI_ENDPOINT=' .env

# Behavior — does the identity actually work?
az account show --query user.name -o tsv
curl -fsS localhost:8000/api/health | jq '.dependencies[] | select(.name=="azure_openai")'
```

`/api/health` reports whether Azure OpenAI is **configured**, without ever
revealing the endpoint or a token — and it says `"configured"`, deliberately
**not** `"ok"`, because two environment variables being set does not prove the
credential resolves. Proving that would mean minting a token on every health
check. `POST /api/chat` is the only real test. There is a test asserting the
endpoint never leaks the endpoint or a token
(`test_never_leaks_the_endpoint_or_a_token`).

---

## 🚫 No PII, by design

SlotSight models **machines and money — never people**.

The schema has no player table, no loyalty ID, no card number, no name, no
address. This is deliberate: the valuable slot-floor analytics problem is about
asset performance, and solving it does not require player data. Adding PII to
this repo would be a bug, not a feature.

If you extend SlotSight with player-level data, that is your regulated-data
problem to solve — and this repo's controls are **not** sufficient for it.

---

## 📣 Reporting a vulnerability

Found a real problem — a leaked credential in history, a dependency CVE, an
injection path?

**Open a [GitHub Security Advisory](https://github.com/fgarofalo56/demo-SlotSight/security/advisories/new)** rather than
a public issue, so it can be triaged before disclosure.

For anything non-sensitive, a normal issue is fine.

**Expected response:** this is a demo repo maintained on a best-effort basis.
Please do not rely on it for a production security posture — copy the *patterns*,
not the *guarantees*.

---

## ✅ Pre-push checklist

Before pushing anything to a public remote:

```bash
make gates            # lint + types + tests
gitleaks detect --no-git --redact          # working tree
gitleaks detect --log-opts=--all --redact  # full history
git config --get core.hooksPath            # → .githooks
```

If `gitleaks` is not installed: `winget install gitleaks` or
`brew install gitleaks`.
