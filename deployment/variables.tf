variable "subscription_id" {
  description = "Azure subscription ID to deploy into."
  type        = string
}

variable "location" {
  description = "Azure region for all resources. Must support Azure AI Foundry."
  type        = string
  default     = "westeurope"
}

variable "resource_group_name" {
  description = "Name of the resource group that will contain all Foundry resources."
  type        = string
  default     = "rg-agentic-development"
}

variable "foundry_hub_name" {
  description = "Name of the Azure AI Foundry Hub. Also used to derive supporting resource names."
  type        = string
  default     = "agentic-development-service"
}

variable "foundry_project_name" {
  description = "Name of the Azure AI Foundry Project inside the Hub."
  type        = string
  default     = "agentic-development-project"
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    environment = "development"
    project     = "tj-sales-agents"
    managed_by  = "terraform"
  }
}
