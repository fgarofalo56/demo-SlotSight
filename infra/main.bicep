// ═══════════════════════════════════════════════════════════════════════════
// SlotSight — Azure infrastructure
//
// Provisions everything from nothing, including its own AI Foundry account and
// model deployment, so a clean clone deploys end to end with no pre-existing
// resources.
//
// SECURITY: there are no secrets in this file and none in any module. Every
// service-to-service call uses the user-assigned managed identity, granted by
// RBAC role assignment. The single generated secret is the PostgreSQL admin
// password — created here with a strong random value, written straight to Key
// Vault, and never emitted as an output.
// ═══════════════════════════════════════════════════════════════════════════

targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Environment name. Used to derive resource names and the azd tag.')
param environmentName string

@minLength(1)
@description('Azure region for all resources.')
param location string

@description('Object ID of the user running azd. Granted data-plane access for local debugging. Leave empty in CI.')
param principalId string = ''

@description('Model to deploy. Change with care - the app negotiates parameter shapes but the deployment must exist AND have GlobalStandard quota in your region.')
param chatModelName string = 'gpt-4o'

@description('Model version.')
param chatModelVersion string = '2024-11-20'

@description('Deployment capacity in thousands of TPM. 30 is ample for a demo.')
param chatModelCapacity int = 30

// ── Naming ─────────────────────────────────────────────────────────────────
// uniqueString over the subscription + environment so a second `azd up` in the
// same subscription cannot collide.
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var prefix = 'slotsight'
var tags = {
  'azd-env-name': environmentName
  application: 'slotsight'
  purpose: 'demo'
  'data-classification': 'synthetic'
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${prefix}-${environmentName}'
  location: location
  tags: tags
}

// ── Identity ───────────────────────────────────────────────────────────────
module identity 'modules/identity.bicep' = {
  scope: rg
  name: 'identity'
  params: {
    name: 'id-${prefix}-${resourceToken}'
    location: location
    tags: tags
  }
}

// ── Observability ──────────────────────────────────────────────────────────
module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoring'
  params: {
    logAnalyticsName: 'log-${prefix}-${resourceToken}'
    appInsightsName: 'appi-${prefix}-${resourceToken}'
    location: location
    tags: tags
  }
}

// ── Container registry ─────────────────────────────────────────────────────
module registry 'modules/registry.bicep' = {
  scope: rg
  name: 'registry'
  params: {
    name: 'cr${prefix}${resourceToken}'
    location: location
    tags: tags
    principalId: identity.outputs.principalId
  }
}

// ── Key Vault ──────────────────────────────────────────────────────────────
// Key Vault names are capped at 24 characters, are alphanumeric-plus-hyphen
// only, and must start with a letter. `kv-slotsight-<12 chars of token>` is 25
// — one over — and fails at deploy time with VaultNameNotValid, not at compile
// time. Dropping the hyphens buys the two characters back.
module vault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyvault'
  params: {
    name: 'kvslotsight${take(resourceToken, 13)}'
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.principalId
    userPrincipalId: principalId
  }
}

// ── PostgreSQL ─────────────────────────────────────────────────────────────
module database 'modules/postgres.bicep' = {
  scope: rg
  name: 'postgres'
  params: {
    name: 'psql-${prefix}-${resourceToken}'
    location: location
    tags: tags
    keyVaultName: vault.outputs.name
  }
}

// ── AI Foundry ─────────────────────────────────────────────────────────────
module ai 'modules/foundry.bicep' = {
  scope: rg
  name: 'foundry'
  params: {
    name: 'aif-${prefix}-${resourceToken}'
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.principalId
    userPrincipalId: principalId
    modelName: chatModelName
    modelVersion: chatModelVersion
    modelCapacity: chatModelCapacity
  }
}

// ── Container Apps ─────────────────────────────────────────────────────────
module apps 'modules/containerapps.bicep' = {
  scope: rg
  name: 'containerapps'
  params: {
    environmentNameSuffix: resourceToken
    prefix: prefix
    location: location
    tags: tags
    logAnalyticsCustomerId: monitoring.outputs.customerId
    logAnalyticsSharedKey: monitoring.outputs.sharedKey
    appInsightsConnectionString: monitoring.outputs.connectionString
    registryLoginServer: registry.outputs.loginServer
    identityResourceId: identity.outputs.resourceId
    identityClientId: identity.outputs.clientId
    postgresHost: database.outputs.fullyQualifiedDomainName
    postgresDatabase: database.outputs.databaseName
    postgresUser: database.outputs.administratorLogin
    keyVaultName: vault.outputs.name
    azureOpenAiEndpoint: ai.outputs.endpoint
    azureOpenAiDeployment: ai.outputs.deploymentName
  }
}

// ── Outputs ────────────────────────────────────────────────────────────────
// Note what is NOT here: no connection string, no password, no key. Outputs
// are recorded in deployment history and readable by anyone with reader access.
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name

output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = registry.outputs.name

output AZURE_OPENAI_ENDPOINT string = ai.outputs.endpoint
output AZURE_OPENAI_DEPLOYMENT string = ai.outputs.deploymentName

output SERVICE_API_URI string = apps.outputs.apiUri
output SERVICE_WEB_URI string = apps.outputs.webUri
output SERVICE_API_NAME string = apps.outputs.apiName
output SERVICE_WEB_NAME string = apps.outputs.webName

output AZURE_KEY_VAULT_NAME string = vault.outputs.name
output POSTGRES_HOST string = database.outputs.fullyQualifiedDomainName
