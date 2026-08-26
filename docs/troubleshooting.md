# 🔧 Troubleshooting

Real failures, in the order you are likely to hit them. Every entry here is
something that actually went wrong while building this.

---

## Chat returns 503 — "azure_openai_not_configured"

**Expected.** `/api/chat` is the only endpoint that needs Azure OpenAI.
Everything else is deterministic SQL.

```bash
cp .env.example .env
# set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT
az login
```

Your account needs **Cognitive Services OpenAI User** on the resource.

> There is no API key setting and you should not add one. Auth is Entra ID via
> `DefaultAzureCredential`, which is why there is nothing to leak. See
> [`SECURITY.md`](../SECURITY.md).

Confirm what the API thinks:

```bash
curl -fsS localhost:8000/api/health | python -m json.tool
```

Note it reports `"status": "configured"`, **not** `"ok"` — configuration alone
does not prove the credential resolves. `POST /api/chat` is the only real check.

---

## Chat returns 502 inside Docker

### `ClientAuthenticationError` — the one that will catch you

**Entra auth does not cross from a Windows or macOS host into a Linux
container.** Two independent reasons:

1. The slim Python image has no `az` CLI, so `DefaultAzureCredential` never even
   attempts `AzureCliCredential`.
2. The Windows token cache is DPAPI-encrypted and the macOS one is Keychain-bound.
   Neither is readable from Linux, so `SharedTokenCacheCredential` finds nothing.

Mounting `~/.azure` read-only does not fix this. The files are visible; they are
just not decryptable.

**This is a local-Docker limitation only.** In Azure, the Container App's managed
identity works correctly — no cache, no CLI, no mount.

**Fix for a local chat demo:**

```bash
make dev        # postgres in Docker, seeded
make api        # terminal 1 — runs on the host, uses your az login
make web        # terminal 2
```

Analytics, dashboard, machines, and recommendations all work fine under
`make up`. Only chat needs `make dev`.

### `BadRequestError` — unsupported parameter

Different Azure OpenAI model families accept different parameters:

| Family | Wants | Rejects |
|---|---|---|
| `gpt-4.1`, `gpt-4o` | `max_tokens` | — |
| `gpt-5.x`, `o-series` | `max_completion_tokens` | non-default `temperature` |

SlotSight negotiates this automatically — it sends the modern shape and drops
whatever the API names in a 400. See
[`agent/orchestrator.py`](../apps/api/src/slotsight/agent/orchestrator.py).

If you see this error anyway, the deployment rejected something the fallback
table does not know about. Add it to `_PARAM_FALLBACKS`.

### `ModuleNotFoundError: No module named 'aiohttp'`

`azure-identity`'s **async** credentials need an async transport, and it is not a
declared dependency of `azure-identity`. Already pinned in
[`pyproject.toml`](../apps/api/pyproject.toml) — if you see this, reinstall:

```bash
cd apps/api && uv pip install -e ".[dev]"
```

Worth knowing because it fails **only on the chat path**, at credential
construction, long after everything else looks healthy.

---

## Port already in use

Vite's default 5173 and Postgres's 5432 are commonly taken. All three host ports
are configurable:

```bash
WEB_PORT=5273 API_PORT=8100 DB_PORT=55432 make up
```

Find the culprit:

```bash
# Windows
netstat -ano | grep ":5173 .*LISTENING"
taskkill //F //PID <pid>

# macOS / Linux
lsof -i :5173
```

> If the app loads but shows *someone else's* application, that is this problem —
> another service is bound to the port and Docker's mapping is shadowed.

---

## `/api/health` says the database is degraded

```
"Connected, but no machines found. Run: make seed"
```

Exactly what it says:

```bash
make seed         # generates if empty
make reseed       # drops and regenerates
```

Seeding writes 151,200 rows and takes 10–15 seconds.

---

## `pnpm install` fails — `ERR_PNPM_IGNORED_BUILDS`

pnpm 11 refuses to run dependency install scripts unless explicitly allowed.
esbuild needs its postinstall to fetch a platform binary.

Already handled in
[`apps/web/pnpm-workspace.yaml`](../apps/web/pnpm-workspace.yaml). If you are
copying this pattern elsewhere, note the key **moved**: it was
`pnpm.onlyBuiltDependencies` in `package.json` under pnpm 10, and is
`allowBuilds` in `pnpm-workspace.yaml` under pnpm 11.

---

## Docker build fails on the web image

If `COPY . .` overwrites the container's `node_modules` with the host's, pnpm's
dependency-status check fails the build with a confusing message about re-running
install.

Fixed by [`apps/web/.dockerignore`](../apps/web/.dockerignore). If you add a new
app, give it a `.dockerignore` **first** — this failure does not point at the
cause.

---

## The API container starts but `slotsight.seed` is missing

```
ModuleNotFoundError: No module named 'slotsight.seed'
```

The Dockerfile installs a stub package first for dependency-layer caching, then
the real sources. Without `--reinstall-package slotsight`, uv sees
`slotsight==0.1.0` already installed and **skips the second install entirely** —
shipping an empty package.

Already fixed, with a build-time assertion so it can never regress silently. See
[`apps/api/Dockerfile`](../apps/api/Dockerfile).

---

## `TypeError: unsupported operand type(s) for /: 'decimal.Decimal' and 'float'`

Postgres `SUM()` over `BIGINT` returns `NUMERIC`, which asyncpg gives you as
`decimal.Decimal`. Dividing it by a float raises.

**This fails only against Postgres.** The SQLite test suite returns plain `int`
and stays green, so unit tests will not catch it.

Coerce at the SQL boundary:

```python
coin_in = int(row.coin_in)
par_hold = float(row.par_hold_pct)
```

---

## A golden test failed

```bash
cd apps/api && uv run pytest -m golden -v
```

**Do not adjust the assertion to match your output.** Those tests assert the
pipeline reaches the right *conclusion* about a floor whose truth we control, and
they are designed to be hard to silence.

Work out which behaviour changed:

- Did you move a threshold in `outliers.py` or `recommend.py`?
- Did you change the generator (`seed/catalog.py`, `seed/generate.py`)?
- Did you widen the distribution? Raising `unit_quality` sigma or the title
  popularity spread pushes a fifth of the floor below the underperformance
  threshold on noise alone, which buries the planted signals.

If the change was intended, update the constants in `seed/scenarios.py` and say
why in the commit.

---

## The `/spec-*` commands don't appear in chat

The single most common setup question. Work down this list.

### 1. Are you in VS Code Chat? Prompt files do not work anywhere else

**This is the most likely answer, and it is a platform limitation, not a
misconfiguration.**

| Surface | `/spec-*` prompt files | `spec-*` **skills** | `.github/agents/` |
|---|---|---|---|
| **VS Code Chat view** | ✅ yes | ✅ yes | ✅ yes |
| **VS Code inline chat** (`Ctrl+I`) | ❌ no | ❌ no | ❌ no |
| **GitHub Copilot CLI** | ❌ **no** | ✅ **yes** | ✅ yes (`/agent`) |
| **Copilot coding agent** (github.com) | ❌ no | ✅ yes | ⚠️ varies |

VS Code's documentation is explicit: *"Agents running on the Agent Host don't
use prompt files."* The Copilot CLI is an Agent Host. No amount of configuration
will surface `/spec-new` there.

> [!TIP]
> **This repository ships the spec workflow twice**, precisely because of that
> row. The same instructions exist as prompt files (`.github/prompts/`) for the
> nice VS Code slash-command UX, **and** as agent skills
> (`.github/skills/spec-*/`) which are portable to the CLI and the coding agent.
>
> In the CLI you don't type a slash command — you just ask, and the runtime
> loads the skill from its description:
>
> ```
> copilot
> > plan spec 003-competitive-intel-feed
> > implement the next task in spec 003
> > verify spec 001
> ```

Use the **Chat view** for slash commands — the sidebar panel, not inline chat.

### 2. Is the folder opened at the repository root?

VS Code discovers `.github/prompts` relative to the **workspace folder**. If you
opened a parent directory, they will not be found.

```bash
code E:/Repos/GitHub/MyDemoRepos/demo-SlotSight     # ✅
code E:/Repos/GitHub/MyDemoRepos                    # ❌ one level too high
```

Check: the Explorer's top-level entry should read `DEMO-SLOTSIGHT`, and
`.github/prompts/` should be directly beneath it.

### 3. Reload the window

Customization files are read at startup. If they arrived via `git pull` or were
created while VS Code was open, they are not loaded yet.

`Ctrl+Shift+P` → **Developer: Reload Window**

### 4. Type `/` into an empty chat input

The slash-command list only appears when `/` is the **first character**. Typing
it mid-sentence does nothing.

### 5. Confirm VS Code actually found them

`Ctrl+Shift+P` → **Chat: Configure Agent Customizations** (or open the Agent
Customizations editor). You should see 8 prompts, 6 agents, 7 instruction
files, and 2 skills.

If that editor lists nothing, discovery is failing — recheck steps 2 and 3.

Alternatively, `Ctrl+Shift+P` → **Chat: Run Prompt** lists every prompt file it
has discovered, independent of the slash-command UI.

### 6. Check the workspace is trusted

Restricted Mode disables workspace-provided customizations. The status bar shows
it. `Ctrl+Shift+P` → **Workspaces: Manage Workspace Trust**.

---

## Is GitHub Spec Kit required?

**No.** They are different, unrelated command sets.

| | `/spec-*` | `/speckit.*` |
|---|---|---|
| Comes from | `.github/prompts/` **in this repo** | `specify-cli`, installed separately |
| Install needed | **none** | `uv tool install specify-cli` |
| Works in | VS Code Chat only | VS Code + Copilot CLI |

This repository implements the spec-driven loop with **prompt files
deliberately**, so it works from a clean clone with nothing installed.

Installing [Spec Kit](https://github.com/github/spec-kit) gives you the
`/speckit.*` family alongside — it will **not** make `/spec-plan` appear, and
`/spec-plan` working does not mean Spec Kit is installed. See
[spec-driven-development.md](spec-driven-development.md#using-github-spec-kit-instead).

---

## I want the spec workflow in the Copilot CLI

**It already works there** — just not as a slash command.

The workflow ships twice: as prompt files for the VS Code slash-command UX, and
as **agent skills** in [`.github/skills/`](../.github/skills/), which the Copilot
CLI, the coding agent, and VS Code all read.

Skills activate from their `description`, so you ask in plain language rather
than typing a command:

```bash
copilot
> write a spec for competitor coverage gaps
> plan spec 003-competitive-intel-feed
> implement the next task in spec 003
> verify spec 001
```

Discovery paths, for reference:

| Scope | Path |
|---|---|
| This repository | `.github/skills/<name>/SKILL.md` |
| Your machine | `~/.copilot/skills/<name>/SKILL.md` |
| Also read | `.claude/skills/`, `.agents/skills/` |

The six custom agents in [`.github/agents/`](../.github/agents/) work in the CLI
too — pick one with `/agent`.

---



1. **Reload the window.** `.vscode/mcp.json` is read at startup.
2. **`slotsight` needs the database up** — `make up` or `make dev`.
3. **`azure` needs `az login`** and downloads on first run via `npx`.
4. **`context7` will prompt for an API key.** It is optional — press Escape and
   it runs rate-limited.
5. Check the MCP output channel for the actual error.

---

## Package installs fail behind a corporate proxy

```
error: Failed to fetch: `https://files.pythonhosted.org/.../asyncpg-...whl.metadata`
  Caused by: received fatal alert: HandshakeFailure
```

Your company runs a TLS-inspecting proxy (Zscaler, Netskope, Palo Alto, and
friends). It re-signs HTTPS with its own root CA. That CA is in the **Windows
certificate store**, but `uv`, `pip`, and `npm` ship their own bundled CA list
and never look there — so the handshake fails.

**The fix is to point each tool at the system trust store.**

```powershell
# uv — load certs from the platform store
$env:UV_SYSTEM_CERTS = "1"
[Environment]::SetEnvironmentVariable("UV_SYSTEM_CERTS", "1", "User")

# npm / Node
$env:NODE_OPTIONS = "--use-openssl-ca"
```

If that is not enough, export the root CA and point everything at the file.
`certmgr.msc` → Trusted Root Certification Authorities → your corporate CA →
Export → **Base-64 encoded X.509** → save as `corp-root-ca.pem`.

```powershell
$env:SSL_CERT_FILE      = "C:\certs\corp-root-ca.pem"   # uv, requests, httpx
$env:REQUESTS_CA_BUNDLE = "C:\certs\corp-root-ca.pem"
$env:NODE_EXTRA_CA_CERTS = "C:\certs\corp-root-ca.pem"  # node, npm
npm config set cafile "C:\certs\corp-root-ca.pem"
```

> [!WARNING]
> **Do not reach for `--allow-insecure-host`, `strict-ssl false`, or
> `PIP_TRUSTED_HOST`.** They work by disabling verification rather than fixing
> trust, which means you are accepting any certificate from anyone — on a
> corporate machine, while installing executable code. Fix the trust store.

### Or skip installing entirely

You do not need any of it for the Copilot portion of this repo. Every
instruction file, agent, prompt, and skill is plain text that VS Code reads off
disk, and **every hook script is pure Python stdlib with zero third-party
imports**. See the setup-path table in
[demo-script.md](demo-script.md#pick-your-setup-path-first) for exactly what
works with nothing installed.

---

## The guardrail hook never fires

The hooks shell out to Python. If no interpreter resolves, they silently do
nothing — and a security control that silently does nothing is worse than none,
because it is still trusted.

`.github/hooks/guardrails.json` tries `python`, then `py -3`, then `python3`.
Confirm at least one works:

```powershell
python --version
py -3 --version
```

If all fail, install Python from python.org (tick **Add python.exe to PATH**) or
adjust the commands in `guardrails.json` to an absolute interpreter path.

To confirm the guard is live, ask Copilot to read `.env`. It should be denied
with an explanation. If it just reads the file, the hook is not running.

---

## MCP servers show as unavailable in VS Code

1. **Reload the window.** `.vscode/mcp.json` is read at startup.
2. **`slotsight` needs the database up** — `make up` or `make dev`.
3. **`azure` downloads on first run** via `npx`. Give it a minute.
4. **`context7` will prompt for an API key.** It is optional — press Escape and
   it runs rate-limited.
5. Check the **MCP output channel** for the actual error.

---

## Copilot refuses to read a file

```
🔒 Blocked: this tool call touches the .env file.
```

**Working as designed.** That is the `PreToolUse` guardrail, layer 3 of the
security model. Do not disable it — read `.env.example` instead, or verify a
credential's *presence and behaviour* rather than its value:

```bash
grep -c '^AZURE_OPENAI_ENDPOINT=' .env    # count, don't print
curl -fsS localhost:8000/api/health
```

---

## The git hooks are not running

They are opt-in — cloning does not enable them:

```bash
git config core.hooksPath .githooks
make verify-hooks
```

---

## Still stuck

```bash
docker compose logs api --tail 50
docker compose logs seed --tail 20
curl -fsS localhost:8000/api/health | python -m json.tool
az account show
```

Then open an issue with the output. Redact anything that looks like a
credential — and if you have already pasted one somewhere, **rotate it first**.
