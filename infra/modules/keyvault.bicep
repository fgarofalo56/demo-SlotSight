// Key Vault.
//
// Holds exactly one secret: the generated PostgreSQL admin password. Access is
// RBAC (enableRbacAuthorization) rather than access policies, so the managed
// identity is granted Key Vault Secrets User and nothing else.

param name string
param location string
param tags object
@description('Principal ID of the managed identity that reads secrets.')
param identityPrincipalId string

@description('Object ID of the human running azd. Empty in CI.')
param userPrincipalId string = ''

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    // 7 days, the minimum. A demo that gets torn down and redeployed under the
    // same name is blocked by a longer soft-delete window, and that failure is
    // baffling if you have not hit it. `azd down --purge` is still required.
    softDeleteRetentionInDays: 7
    enablePurgeProtection: null
    publicNetworkAccess: 'Enabled'
  }
}

// Key Vault Secrets User
var secretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource identitySecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vault
  name: guid(vault.id, identityPrincipalId, secretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsUserRoleId)
    principalId: identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets Officer, for the human, so `azd up` can write the password.
var secretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'

resource userSecretsOfficer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(userPrincipalId)) {
  scope: vault
  name: guid(vault.id, userPrincipalId, secretsOfficerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', secretsOfficerRoleId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

output name string = vault.name
output uri string = vault.properties.vaultUri
output resourceId string = vault.id
