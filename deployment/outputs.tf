output "resource_group_name" {
  description = "Name of the deployed resource group."
  value       = azurerm_resource_group.rg.name
}

output "foundry_hub_id" {
  description = "Resource ID of the Azure AI Foundry Hub."
  value       = azapi_resource.foundry_hub.id
}

output "foundry_project_id" {
  description = "Resource ID of the Azure AI Foundry Project."
  value       = azapi_resource.foundry_project.id
}

output "foundry_project_endpoint" {
  description = "Set this as AZURE_AI_PROJECT_ENDPOINT in Agent/.env."
  value       = "https://${var.foundry_hub_name}.services.ai.azure.com/api/projects/${var.foundry_project_name}"
}

output "application_insights_connection_string" {
  description = "Set this as APPLICATION_INSIGHTS_CONNECTION_STRING in Agent/.env for OTel tracing."
  value       = azurerm_application_insights.appi.connection_string
  sensitive   = true
}

output "key_vault_uri" {
  description = "Key Vault URI — store agent secrets (GitHub PAT, Jira token, etc.) here."
  value       = azurerm_key_vault.kv.vault_uri
}

output "azure_portal_link" {
  description = "Direct link to the resource group in the Azure Portal."
  value       = "https://portal.azure.com/#resource/subscriptions/${var.subscription_id}/resourceGroups/${azurerm_resource_group.rg.name}/overview"
}
