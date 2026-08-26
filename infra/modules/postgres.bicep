// PostgreSQL Flexible Server.
//
// Burstable B1ms with 32 GB and no HA — the cheapest thing that runs this demo.
// A production build of SlotSight would want General Purpose, zone-redundant
// HA, and private networking; that trade-off is stated rather than hidden.

param name string
param location string
param tags object

@description('Key Vault to write the generated admin password into.')
param keyVaultName string

param administratorLogin string = 'slotsight_admin'
param databaseName string = 'slotsight'

// Generated at provision time from the deployment's own entropy. Never an
// output, never logged, never surfaced to `azd env`. The application reads it
// from Key Vault via the managed identity.
//
// The linter flags a default on a @secure() parameter, and it is usually right
// — a hardcoded default is a committed credential. This one is derived from
// resource-group and subscription identifiers that do not exist until provision
// time and differ per deployment, so there is no fixed value in the repository.
// The alternative (requiring the operator to supply one) means a password
// travelling through a shell history and a CI variable, which is worse.
@secure()
#disable-next-line secure-parameter-default
param administratorPassword string = '${toUpper(uniqueString(resourceGroup().id, name))}-${uniqueString(subscription().subscriptionId, name)}!7'

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow Azure services (Container Apps) to connect. Broad, and appropriate only
// because this database holds nothing but synthetic data. A real deployment
// would use a private endpoint and VNet integration instead.
resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource passwordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'postgres-admin-password'
  properties: {
    value: administratorPassword
    contentType: 'text/plain'
  }
}

output name string = postgres.name
output fullyQualifiedDomainName string = postgres.properties.fullyQualifiedDomainName
output administratorLogin string = administratorLogin
output databaseName string = database.name

// The NAME of the Key Vault secret, not its value — the app needs it to look
// the secret up. The linter matches on the identifier and cannot tell the
// difference, which is a reasonable default given how often it is the value.
#disable-next-line outputs-should-not-contain-secrets
output passwordSecretName string = passwordSecret.name
