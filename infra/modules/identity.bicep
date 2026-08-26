// User-assigned managed identity.
//
// One identity for every service-to-service call in the deployment. Nothing in
// SlotSight authenticates with a key.

param name string
param location string
param tags object

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output resourceId string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
output name string = identity.name
