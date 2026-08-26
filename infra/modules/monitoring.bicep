// Log Analytics + Application Insights.
//
// 30-day retention: this is a demo people deploy and forget, and log ingestion
// is the line item most likely to surprise them.

param logAnalyticsName string
param appInsightsName string
param location string
param tags object

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    features: { enableLogAccessUsingOnlyResourcePermissions: true }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output customerId string = logAnalytics.properties.customerId
#disable-next-line outputs-should-not-contain-secrets
output sharedKey string = logAnalytics.listKeys().primarySharedKey
output connectionString string = appInsights.properties.ConnectionString
output logAnalyticsId string = logAnalytics.id
