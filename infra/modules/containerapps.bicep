// Container Apps environment + the api and web apps.
//
// Consumption plan with minReplicas: 0 — this is a demo people deploy and
// forget, so it should cost nothing while idle.
//
// The azd-service-name tag is load-bearing: `azd deploy` locates apps by it,
// and the value must match the service key in azure.yaml exactly.

param environmentNameSuffix string
param prefix string
param location string
param tags object

param logAnalyticsCustomerId string
@secure()
param logAnalyticsSharedKey string
param appInsightsConnectionString string

param registryLoginServer string
param identityResourceId string
param identityClientId string

param postgresHost string
param postgresDatabase string
param postgresUser string
param keyVaultName string

@description('Key Vault URI, e.g. https://kv.vault.azure.net/')
param keyVaultUri string

@description('Name of the Key Vault secret holding the PostgreSQL admin password.')
param postgresPasswordSecretName string

param azureOpenAiEndpoint string
param azureOpenAiDeployment string

// Placeholder image until `azd deploy` pushes the real one. Without it the
// first provision fails, because a container app cannot be created with no
// image.
param apiImage string = 'mcr.microsoft.com/k8se/quickstart:latest'
param webImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${prefix}-${environmentNameSuffix}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    zoneRedundant: false
  }
}

var identityConfig = {
  type: 'UserAssigned'
  userAssignedIdentities: { '${identityResourceId}': {} }
}

var registryConfig = [
  {
    server: registryLoginServer
    identity: identityResourceId
  }
]

// The PostgreSQL password reaches the container as a Key Vault REFERENCE, not
// a value. Container Apps resolves it at runtime using the managed identity, so
// the secret never appears in the template, in deployment history, or in
// `az containerapp show` output.
//
// This is the piece that was missing on the first deploy: the template passed
// AZURE_KEY_VAULT_NAME and assumed the application would fetch the secret
// itself, but no such code exists — so the app fell back to its local default
// password and could not connect. Wiring it here means zero app code and zero
// secrets in the template.
var kvSecrets = [
  {
    name: 'postgres-password'
    keyVaultUrl: '${keyVaultUri}secrets/${postgresPasswordSecretName}'
    identity: identityResourceId
  }
]

// ── API ────────────────────────────────────────────────────────────────────
resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${prefix}-api-${environmentNameSuffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'api' })
  identity: identityConfig
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      registries: registryConfig
      secrets: kvSecrets
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'POSTGRES_HOST', value: postgresHost }
            { name: 'POSTGRES_PORT', value: '5432' }
            { name: 'POSTGRES_USER', value: postgresUser }
            { name: 'POSTGRES_DB', value: postgresDatabase }
            { name: 'POSTGRES_PASSWORD', secretRef: 'postgres-password' }
            { name: 'AZURE_KEY_VAULT_NAME', value: keyVaultName }
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: azureOpenAiDeployment }
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'LOG_LEVEL', value: 'info' }
            { name: 'PROPERTY_NAME', value: 'Neon Palms Casino Resort' }
            // Makes `azd up` produce a working demo rather than a correctly
            // deployed empty one. Only fires when the machines table is empty.
            { name: 'SEED_ON_STARTUP', value: 'true' }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 15
              periodSeconds: 10
              failureThreshold: 6
            }
          ]
        }
      ]
      scale: {
        // minReplicas 1, not 0. Scale-to-zero saves a few dollars but adds a
        // 20-40s cold start to the first request, which is a poor experience
        // for a demo someone is about to show on a screen.
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ── Web ────────────────────────────────────────────────────────────────────
resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${prefix}-web-${environmentNameSuffix}'
  location: location
  tags: union(tags, { 'azd-service-name': 'web' })
  identity: identityConfig
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'web'
          image: webImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'API_URL', value: 'https://${api.properties.configuration.ingress.fqdn}' }
            // "auto" = discover the platform nameserver from /etc/resolv.conf at
            // container start. Neither Docker's 127.0.0.11 nor Azure's
            // 168.63.129.16 works in both environments — the first refuses here,
            // the second times out. See apps/web/docker-entrypoint.d/.
            { name: 'DNS_RESOLVER', value: 'auto' }
          ]
        }
      ]
      scale: {
        // Warm, for the same reason as the api — see the note there.
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output apiUri string = 'https://${api.properties.configuration.ingress.fqdn}'
output webUri string = 'https://${web.properties.configuration.ingress.fqdn}'
output apiName string = api.name
output webName string = web.name
output environmentId string = env.id
