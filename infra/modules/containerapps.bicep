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
      // Note: no `secrets` block. There is nothing to put in it.
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
            { name: 'AZURE_KEY_VAULT_NAME', value: keyVaultName }
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: azureOpenAiDeployment }
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'LOG_LEVEL', value: 'info' }
            { name: 'PROPERTY_NAME', value: 'Neon Palms Casino Resort' }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
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
          ]
        }
      ]
      scale: {
        minReplicas: 0
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
