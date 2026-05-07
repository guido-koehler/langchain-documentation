data "azurerm_client_config" "current" {}

locals {
  # Storage account: lowercase alphanumeric only, max 24 chars
  storage_account_name = lower(substr(replace("st${var.foundry_hub_name}", "-", ""), 0, 24))

  # Key Vault: 3-24 chars, alphanumeric + hyphens, must not end with hyphen
  key_vault_name = "kv-${trimsuffix(substr(var.foundry_hub_name, 0, 20), "-")}"

  log_analytics_name = "law-${var.foundry_hub_name}"
  app_insights_name  = "appi-${var.foundry_hub_name}"
}

# ── Resource Group ─────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ── Storage Account (required by Foundry Hub) ─────────────────────────────────

resource "azurerm_storage_account" "sa" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.tags
}

# ── Key Vault (required by Foundry Hub) ───────────────────────────────────────

resource "azurerm_key_vault" "kv" {
  name                     = local.key_vault_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  tenant_id                = data.azurerm_client_config.current.tenant_id
  sku_name                 = "standard"
  purge_protection_enabled = true
  tags                     = var.tags
}

# Grant the deploying identity manage permissions so secrets can be stored later
resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  key_permissions    = ["Create", "Get", "Delete", "Purge", "GetRotationPolicy"]
  secret_permissions = ["Set", "Get", "Delete", "List", "Purge"]
}

# ── Log Analytics Workspace (backing Application Insights) ────────────────────

resource "azurerm_log_analytics_workspace" "law" {
  name                = local.log_analytics_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ── Application Insights (Foundry observability + OpenTelemetry traces) ────────

resource "azurerm_application_insights" "appi" {
  name                = local.app_insights_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
  tags                = var.tags
}

# ── Azure AI Foundry Hub ───────────────────────────────────────────────────────
# azapi_resource is used because azurerm_machine_learning_workspace does not yet
# support kind = "Hub". The Hub is the top-level Foundry resource that owns the
# storage, key vault, and app insights connections.

resource "azapi_resource" "foundry_hub" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-10-01"
  name      = var.foundry_hub_name
  location  = azurerm_resource_group.rg.location
  parent_id = azurerm_resource_group.rg.id
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "Hub"
    sku = {
      name = "Basic"
      tier = "Basic"
    }
    properties = {
      friendlyName        = var.foundry_hub_name
      storageAccount      = azurerm_storage_account.sa.id
      keyVault            = azurerm_key_vault.kv.id
      applicationInsights = azurerm_application_insights.appi.id
      publicNetworkAccess = "Enabled"
    }
  }

  response_export_values = ["*"]
}

# ── Azure AI Foundry Project ───────────────────────────────────────────────────
# A Project scoped under the Hub. The AZURE_AI_PROJECT_ENDPOINT env var points
# to this project. Models are deployed and accessed at project scope.

resource "azapi_resource" "foundry_project" {
  type      = "Microsoft.MachineLearningServices/workspaces@2024-10-01"
  name      = var.foundry_project_name
  location  = azurerm_resource_group.rg.location
  parent_id = azurerm_resource_group.rg.id
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "Project"
    sku = {
      name = "Basic"
      tier = "Basic"
    }
    properties = {
      friendlyName  = var.foundry_project_name
      hubResourceId = azapi_resource.foundry_hub.id
    }
  }

  response_export_values = ["*"]

  depends_on = [azapi_resource.foundry_hub]
}
