---
name: Bicep & Azure infrastructure
description: IaC conventions for the azd deployment
applyTo: "infra/**/*.bicep,infra/**/*.bicepparam,azure.yaml"
---

# Infrastructure in SlotSight

Deployed with `azd up`. Bicep modules under `infra/`, orchestrated by
`infra/main.bicep` at subscription scope.

## Identity, not keys

Every service-to-service call uses the **user-assigned managed identity**.
Access is granted by RBAC role assignment.

| Target | Role |
|---|---|
| Azure Container Registry | `AcrPull` |
| AI Foundry / Azure OpenAI | `Cognitive Services OpenAI User` |
| Key Vault | `Key Vault Secrets User` |

There must be **zero secrets in Bicep and zero secrets in `azure.yaml`**. The
only generated secret is the PostgreSQL admin password, created at provision
time with `@secure()` and written to Key Vault — never output, never logged,
never surfaced to `azd env`.

Never mark a parameter or output as plain text if it carries a credential.
Outputs are recorded in deployment history and readable by anyone with reader
access.

## Conventions

- **Resource naming** via `uniqueString(subscription().id, environmentName)` so
  a second `azd up` in the same subscription does not collide.
- **`azd` tagging** — every resource carries `azd-env-name`. Container Apps also
  need `azd-service-name` matching the service key in `azure.yaml`, or `azd
  deploy` cannot find them.
- **One module per resource type** under `infra/modules/`. `main.bicep`
  composes; it does not declare resources directly.
- **Target the latest stable API version.** Check with the `microsoft-docs` MCP
  server rather than copying a version from an old sample.
- **Everything is parameterized by `location`.** No hardcoded regions.

## Cost

This is a demo people will deploy and forget. Default to the cheapest thing that
works, and say so in a comment:

- Container Apps: consumption plan, `minReplicas: 0`
- PostgreSQL: `Standard_B1ms`, 32 GB, no HA
- Log Analytics: 30-day retention
- AI Foundry: `GlobalStandard` with a modest capacity

`docs/deploy-azure.md` must state the approximate monthly cost and how to tear
it down (`azd down --purge`). Note that `--purge` matters: soft-deleted Key
Vault and AI Foundry resources will block a re-deploy under the same name.

## Verify before claiming

```bash
az bicep build --file infra/main.bicep    # compiles?
azd provision --preview                   # what-if, no changes
```

Never report an infrastructure change as working on the basis of a successful
`az bicep build`. Compiling is not deploying.
