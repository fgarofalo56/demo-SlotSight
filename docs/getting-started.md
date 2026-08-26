# 🚀 Getting started

From clone to a running slot floor in about five minutes.

---

## Prerequisites

| Tool | Why | Check |
|---|---|---|
| **Docker Desktop** | Runs the whole stack | `docker compose version` |
| **Git** | Obviously | `git --version` |
| *(optional)* **uv** | Python deps, for local dev | `uv --version` |
| *(optional)* **Node 22 + pnpm** | Frontend, for local dev | `pnpm --version` |
| *(optional)* **Azure CLI** | Only for the chat feature | `az version` |

Docker alone is enough to run everything except the conversational endpoint.

---

## 1. Clone and start

```bash
git clone https://github.com/<you>/demo-SlotSight.git
cd demo-SlotSight
make up
```

That builds three images, starts PostgreSQL, generates **840 machines × 180
days** of synthetic performance data, and starts the API and web app.

First run takes 2–3 minutes, mostly image builds. Then:

- **Web** → http://localhost:5173
- **API docs** → http://localhost:8000/docs
- **Health** → http://localhost:8000/api/health

> [!TIP]
> Port already taken? All three are configurable:
> `WEB_PORT=5273 API_PORT=8100 DB_PORT=55432 make up`

## 2. Look around

| View | What to notice |
|---|---|
| **Dashboard** | The Zones table. High Limit reads **3.44 floor index** and **1.07 peer index** — same fifty machines. Only the second is meaningful. |
| **Machines** | Hatched rows are machines whose meter data is not trusted. |
| **Recommendations** | Expand the evidence. Every finding shows its numbers, window, and sources. |
| **Market** | The synthetic-data badge. It is on every view that shows generated benchmarks. |
| **Ask SlotSight** | Needs Azure OpenAI — next section. |

---

## 3. Enable the conversational feature *(optional)*

`/api/chat` is the only part that needs a cloud service. Everything else is
deterministic SQL.

You need an **Azure OpenAI or AI Foundry resource** with a chat model
deployment, and the **Cognitive Services OpenAI User** role on it.

```bash
cp .env.example .env
```

Then set two values in `.env`:

```bash
AZURE_OPENAI_ENDPOINT=https://<your-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
```

`AZURE_OPENAI_DEPLOYMENT` is the **deployment name** you chose, not the model
name.

```bash
az login
```

> [!IMPORTANT]
> **There is no API key setting, and you should not add one.** Auth is Entra ID
> via `DefaultAzureCredential` — which is precisely why there is nothing here to
> leak. See [`SECURITY.md`](../SECURITY.md).

### On Windows or macOS, use `make dev` for chat

Entra auth **does not cross from your host into a Linux container**: the token
cache is platform-encrypted and the slim image has no `az` CLI. This is a local
Docker limitation only — in Azure, managed identity works correctly.

```bash
make dev        # postgres in Docker, seeded
make api        # terminal 1 — on the host, uses your az login
make web        # terminal 2
```

Details: [troubleshooting](troubleshooting.md#chat-returns-502-inside-docker).

---

## 4. Wire up Copilot

The point of the repository. Open it in VS Code with the Copilot extension.

```bash
code .
```

Accept the recommended extensions, then **reload the window** so
`.vscode/mcp.json` is read.

**Confirm it worked:**

1. **MCP panel** — five servers connected: `github`, `microsoft-docs`,
   `context7`, `azure`, `slotsight`.
   *(Context7 will prompt for an optional API key. Press Escape to skip.)*
2. **Agents dropdown** — six custom agents.
3. **Type `/`** in Copilot Chat — the `spec-*` commands autocomplete.
4. **Try the guardrail** — ask Copilot to *read the .env file*. It gets denied.
   That is layer 3 of the security model working.

Then ask the **Slot Analyst** agent:

> *Which banks are fading, and is High Limit healthy?*

It queries the live database through our own MCP server.

Full tour: [Copilot configuration](copilot-configuration.md)

---

## 5. Run the gates

```bash
make setup     # installs local deps and wires the git hooks
make gates     # lint + types + tests, both apps
```

```bash
make test-golden
```

Those are the four planted narrative signals. They assert the pipeline reaches
the right *conclusion* about a floor whose truth we control — see
[`seed/scenarios.py`](../apps/api/src/slotsight/seed/scenarios.py).

> [!NOTE]
> `make setup` also runs `git config core.hooksPath .githooks`. Git hooks are
> opt-in — cloning does not enable them.

---

## Everyday commands

```bash
make up            # start everything
make dev           # chat-capable local mode
make down          # stop (keeps the database)
make clean         # stop and delete the database volume
make logs          # tail everything
make reseed        # regenerate the synthetic floor
make gates         # lint + types + tests
make test-golden   # the four planted signals
make scan          # gitleaks, working tree and full history
make help          # all targets
```

---

## What next

- **Presenting this?** → [Demo script](demo-script.md)
- **Understand the analytics?** → [Slot analytics primer](slot-analytics-primer.md)
- **Understand the Copilot setup?** → [Copilot configuration](copilot-configuration.md)
- **Try the spec workflow?** → [Spec-driven development](spec-driven-development.md)
- **Deploy it?** → [Deploy to Azure](deploy-azure.md)
- **Something broke?** → [Troubleshooting](troubleshooting.md)
