# ☁️ Deploy to Azure

```bash
azd config set auth.useAzCliAuth true   # or: azd auth login
azd up
```

That is genuinely it. The template provisions everything from nothing —
including its own AI Foundry account and model deployment — so a clean clone
deploys end to end with no pre-existing resources.

---

## What gets created

```mermaid
flowchart LR
    subgraph rg["rg-slotsight-&lt;env&gt;"]
        MI["Managed Identity"]
        ACR["Container Registry<br/><small>Basic</small>"]
        CAE["Container Apps Env"]
        API["ca-api<br/><small>0.5 vCPU · min 1</small>"]
        WEB["ca-web<br/><small>0.25 vCPU · min 1</small>"]
        PG[("PostgreSQL 16<br/><small>B1ms · 32 GB</small>")]
        KV["Key Vault"]
        AIF["AI Foundry<br/><small>disableLocalAuth</small>"]
        LAW["Log Analytics<br/><small>30-day</small>"]
    end

    MI -->|AcrPull| ACR
    MI -->|Secrets User| KV
    MI -->|OpenAI User| AIF
    API --> PG
    API --> AIF
    WEB --> API

    style MI fill:#0B3D2E,stroke:#F5C518,color:#F5F1E8
    style AIF fill:#12563F,stroke:#FF2E88,color:#F5F1E8
```

Roughly **8–12 minutes** on a first provision, most of it PostgreSQL and the
model deployment.

---

## 💰 Cost

Ballpark for an idle demo in a US region. Check
[Azure Pricing](https://azure.microsoft.com/pricing/calculator/) for current
figures, or ask the Azure MCP server.

| Resource | ~Monthly |
|---|---|
| Container Apps (2 apps, `minReplicas: 1`) | **~$15–25** — kept warm, no cold start |
| PostgreSQL Flexible Server B1ms + 32 GB | **~$15–20** ← the bulk of it |
| Container Registry (Basic) | ~$5 |
| Log Analytics (30-day, low volume) | ~$0–3 |
| Key Vault | <$1 |
| AI Foundry | **pay-per-token** — pennies for a demo |
| **Total idle** | **~$25–30/month** |

**PostgreSQL is the only thing that does not scale to zero.** If you are keeping
this around, that is what to stop.

### Tear it down

```bash
azd down --purge
```

> [!IMPORTANT]
> `--purge` matters. Key Vault and AI Foundry soft-delete by default, and a
> soft-deleted resource **blocks a re-deploy under the same name** with an error
> that does not explain itself.

---

## 🔐 The security model

**RBAC, not keys.** Every service-to-service call uses the user-assigned managed
identity:

| Target | Role |
|---|---|
| Container Registry | `AcrPull` |
| AI Foundry | `Cognitive Services OpenAI User` |
| Key Vault | `Key Vault Secrets User` |

**There are no secrets in Bicep and none in `azure.yaml`.** Search for
`listKeys`, `apiKey`, or a connection string — the only one is the Log Analytics
shared key, which the Container Apps environment schema requires.

**AI Foundry sets `disableLocalAuth: true`.** Key-based auth is turned off at the
resource, which means "just use an API key" is not merely discouraged here — it
is impossible.

**One generated secret**, the PostgreSQL admin password: created at provision
time from deployment-scoped entropy, written straight to Key Vault, never an
output, never logged, never in `azd env`.

---

## Before you deploy

```bash
az account show --query "{sub:name, id:id}" -o json
```

Deploying a demo into the wrong subscription happens and is annoying to unwind.

```bash
az bicep build --file infra/main.bicep                 # template compiles?
az bicep build-params --file infra/main.bicepparam --stdout  # params too (build does NOT check these)
azd provision --preview                    # what-if, changes nothing
```

> Compiling is not deploying. A clean `bicep build` proves syntax and nothing
> more.

---

## After you deploy — verify, don't assume

```bash
azd env get-values | grep -i URI

curl -fsS <SERVICE_API_URI>/api/health
curl -fsS <SERVICE_API_URI>/api/floor/summary
curl -fsS <SERVICE_WEB_URI>/api/health     # proves the nginx proxy works too
```

`/api/health` should report `"status": "ok"` with the database `ok`. If the
database reads `degraded — "no machines found"`, the startup seed did not run.

### The database seeds itself on first boot

The Container App sets `SEED_ON_STARTUP=true`, so the API generates the
synthetic floor **if and only if the machines table is empty**. A restart never
re-seeds and never overwrites. First boot therefore takes about a minute longer
while it writes 151,200 rows.

It is **off by default** everywhere else — a service that writes six figures of
rows into a database it did not expect to be empty is a bad surprise, and
locally `make up` runs the seed as its own visible compose service.

If you would rather seed manually, unset that variable and run:

```bash
az containerapp exec -n <api-app> -g <rg> --command "slotsight-seed --reset"
```

### The chat endpoint on Azure

This is the one thing that works **better** in Azure than locally. The
Container App's user-assigned managed identity resolves cleanly through
`DefaultAzureCredential`, so `POST /api/chat` works with no configuration —
whereas locally on Windows or macOS the Entra token cache cannot cross into a
Linux container at all.

```bash
curl -sS -X POST <SERVICE_WEB_URI>/api/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Which penny video slots are underperforming this month?"}'
```

Expect a grounded answer in a few seconds, with the tool calls that produced it.

---

## 🤖 The conversational path

The integration worth demonstrating: **do the whole thing through the Azure MCP
server.**

Switch to the **Azure Deployer** agent in Copilot Chat, or use `/deploy-azure`.

Try, in order:

> *What Azure subscription am I currently logged into?*

> *What will `azd up` create for this repo, and roughly what will it cost per month?*

> *Run a provision preview and summarise what would change.*

> *Provision it.* ← it will ask you to confirm first

> *Is the API healthy? Check the Container App logs.*

> *The database looks empty. How do I run the seed job?*

The agent uses `azure/*` tools for live resources and `microsoft-docs/*` to
check current API versions rather than recalling them. It is configured to
**refuse to change cloud state without confirmation**, and to treat `azd down`
as requiring an explicit, unambiguous instruction.

---

## Configuration

```bash
azd env set AZURE_LOCATION eastus2
azd env set CHAT_MODEL_NAME gpt-4o
azd env set CHAT_MODEL_CAPACITY 30
```

Model availability varies by region. If the deployment fails on model capacity,
either pick another region or lower the capacity — the error names which.

---

## When it fails

| Symptom | Cause |
|---|---|
| `azd` says "You must be logged into Azure" | `azd` has its own auth, separate from `az`. Either `azd auth login`, or `azd config set auth.useAzCliAuth true` to delegate to your existing `az` session. |
| Bicep params error `BCP001: token not recognized "#"` | Parameter files use `//` for comments, not `#`. **`az bicep build --file main.bicep` does not catch this** — it only compiles the template. Use `az bicep build-params --file infra/main.bicepparam --stdout`. |
| `VaultNameNotValid` | Key Vault names are capped at 24 characters. Fails at deploy time, not compile time. |
| Model deployment fails on capacity | The region has no GlobalStandard quota for that model. Check with the command below and pick another model or region. |
| `AuthorizationFailed` right after provisioning | RBAC propagation. Wait 2–5 minutes and retry. **Never** switch to a key. |
| `VaultAlreadyExists` on re-deploy | Soft-deleted from a previous run. You needed `azd down --purge`. |
| API replica fails readiness, "connection refused" | The app could not reach PostgreSQL. Check that `POSTGRES_PASSWORD` is present as a `secretRef` on the container app. |
| Web container won't start, "host not found in upstream" | nginx resolves a literal `proxy_pass` upstream at config-parse time. The upstream must go through a variable, with a `resolver` — see `apps/web/nginx.default.conf.template`. |
| Web starts but `/api/*` hangs or 502s | The `resolver` address is wrong for the environment. `DNS_RESOLVER=auto` discovers it from `/etc/resolv.conf`; neither `127.0.0.11` nor `168.63.129.16` works in both Docker and Container Apps. |
| `/api/health` degraded, "no machines found" | The startup seed did not run. Check `SEED_ON_STARTUP=true` on the container app. |
| `azd deploy` can't find the service | The `azd-service-name` tag must match the key in `azure.yaml`. |

Checking model quota before you deploy:

```bash
az cognitiveservices usage list -l eastus2 \
  --query "[?contains(name.value,'GlobalStandard.gpt')].{model:name.value, used:currentValue, limit:limit}" \
  -o table
```

> [!TIP]
> `gpt-4.1` is offered **Batch-only** in several subscriptions — it has no
> GlobalStandard quota, so a deployment silently fails to find capacity. That is
> why the template defaults to `gpt-4o` / `2024-11-20`, which is far more widely
> available.

More: [troubleshooting](troubleshooting.md)
