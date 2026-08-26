// AI Foundry (Azure OpenAI) account + model deployment.
//
// Provisioned rather than referenced, so a clean clone of this repository
// deploys end to end with nothing pre-existing.
//
// disableLocalAuth is TRUE. Key-based auth is turned off at the resource, which
// means the "just use an API key" workaround is not merely discouraged here —
// it is impossible. Access is Entra ID only.

param name string
param location string
param tags object

@description('Principal ID of the managed identity the app runs as.')
param identityPrincipalId string

@description('Object ID of the human running azd, for local debugging. Empty in CI.')
param userPrincipalId string = ''

param modelName string
param modelVersion string
param modelCapacity int

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    // No keys. At all. See the note above.
    disableLocalAuth: true
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: 'chat'
  sku: {
    name: 'GlobalStandard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// Cognitive Services OpenAI User — data-plane inference, no management rights.
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource identityOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, identityPrincipalId, openAiUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource userOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userPrincipalId)) {
  scope: account
  name: guid(account.id, userPrincipalId, openAiUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

output name string = account.name
output endpoint string = account.properties.endpoint
output deploymentName string = deployment.name
output resourceId string = account.id
