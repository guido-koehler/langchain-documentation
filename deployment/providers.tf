terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.2"
    }
    azapi = {
      # azapi is required because azurerm_machine_learning_workspace does not yet
      # expose kind = "Hub" or "Project" for Azure AI Foundry resources.
      source  = "azure/azapi"
      version = ">= 2.0"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azapi" {
  subscription_id = var.subscription_id
}
