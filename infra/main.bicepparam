// Bicep parameters for `azd`.
//
// Values come from azd environment variables — nothing is hardcoded, and there
// are no secrets here.
//
// Override with:  azd env set AZURE_LOCATION eastus2
//
// NOTE: Bicep parameter files use `//` for comments, not `#`. A `#` produces
// BCP001/BCP337 and — importantly — `az bicep build --file main.bicep` does NOT
// catch it, because that only compiles the template. Validate this file with
// `az bicep build-params --file infra/main.bicepparam` or `azd provision --preview`.

using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'slotsight-dev')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')

// gpt-4o / 2024-11-20 is the default because it has GlobalStandard quota in far
// more subscription+region combinations than gpt-4.1, which in several
// subscriptions is offered only as Batch. Check yours before changing it:
//
//   az cognitiveservices usage list -l <region> \
//     --query "[?contains(name.value,'GlobalStandard.gpt')].{m:name.value,used:currentValue,limit:limit}" -o table
param chatModelName = readEnvironmentVariable('CHAT_MODEL_NAME', 'gpt-4o')
param chatModelVersion = readEnvironmentVariable('CHAT_MODEL_VERSION', '2024-11-20')
param chatModelCapacity = int(readEnvironmentVariable('CHAT_MODEL_CAPACITY', '30'))
