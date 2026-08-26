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

## MCP servers show as unavailable in VS Code

1. **Reload the window.** `.vscode/mcp.json` is read at startup.
2. **`slotsight` needs the database up** — `make up` or `make dev`.
3. **`azure` needs `az login`** and downloads on first run via `npx`.
4. **`context7` will prompt for an API key.** It is optional — press Escape and
   it runs rate-limited.
5. Check the MCP output channel for the actual error.

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
