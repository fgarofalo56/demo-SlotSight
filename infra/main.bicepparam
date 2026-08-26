# Bicep parameters for `azd`.
#
# Values come from azd environment variables — nothing is hardcoded, and there
# are no secrets here.
#
# Override with:  azd env set AZURE_LOCATION eastus2

using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'slotsight-dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')

param chatModelName = readEnvironmentVariable('CHAT_MODEL_NAME', 'gpt-4.1')
param chatModelVersion = readEnvironmentVariable('CHAT_MODEL_VERSION', '2025-04-14')
param chatModelCapacity = int(readEnvironmentVariable('CHAT_MODEL_CAPACITY', '30'))
