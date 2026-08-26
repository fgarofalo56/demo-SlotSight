---
name: deploy-azure
description: Provision and deploy SlotSight to Azure, or check what it would cost
argument-hint: "preview", "provision", "deploy", "cost", or "teardown"
agent: Azure Deployer
tools: ['azure/*', 'microsoft-docs/*', 'runCommands', 'search/codebase', 'vscode/askQuestions']
---

# Azure: **${input:action:What do you want to do? preview / provision / deploy / cost / teardown}**

## Before anything

```bash
az account show --query "{sub:name, id:id, user:user.name}" -o json
azd env get-values 2>/dev/null | grep -v -i "password\|secret\|key" || echo "no azd env yet"
```

Confirm the subscription is the one intended. Deploying a demo into the wrong
subscription is a thing that happens and is annoying to unwind.

> [!IMPORTANT]
> Never print a value that looks like a credential. Filter it out, as above.

## Preview — safe, changes nothing

```bash
az bicep build --file infra/main.bicep
azd provision --preview
```

Show me what would be created. Note that compiling is not deploying — a clean
`bicep build` proves syntax, nothing more.

## Provision / deploy — **ask me first**

State exactly what will be created and roughly what it will cost per month, then
wait for my confirmation.

```bash
azd up
```

Afterwards, **prove it works** rather than assuming:

```bash
azd env get-values | grep -i uri
curl -fsS <api-uri>/api/health
curl -fsS <api-uri>/api/floor/summary
```

If `/api/health` reports the database as degraded, the seed job has not run —
say so and tell me how to run it. Do not report a successful deploy over an
empty database.

## Cost

Use the `azure` pricing tools for real figures rather than estimating. Break it
down by resource. Then tell me how to tear it down.

## Teardown — **destructive, requires explicit instruction**

```bash
azd down --purge
```

Say what will be permanently lost before running it. `--purge` matters:
soft-deleted Key Vault and AI Foundry resources will block a re-deploy under the
same name, and that failure is baffling if you have not hit it before.

## Rules

- **No secrets in Bicep, no secrets in `azure.yaml`.** Access is RBAC to the
  managed identity.
- If a deploy fails on auth, the answer is a role assignment or waiting for RBAC
  propagation — **never** switching to an API key.
- Check current API versions with `#tool:microsoft-docs` instead of copying a
  version from an old sample.
