// Azure Container Registry.
//
// adminUserEnabled is deliberately FALSE. Container Apps pulls using the
// user-assigned managed identity with AcrPull, so there is no registry password
// to store, rotate, or leak.

param name string
param location string
param tags object

@description('Principal ID of the managed identity that pulls images.')
param principalId string

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// AcrPull
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, principalId, acrPullRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output name string = registry.name
output loginServer string = registry.properties.loginServer
output resourceId string = registry.id
