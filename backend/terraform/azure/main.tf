terraform {
  required_version = ">= 1.10.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  count    = var.enable_azure_storage ? 1 : 0
  name     = var.resource_group_name
  location = var.azure_location
  tags     = var.tags
}

resource "azurerm_storage_account" "main" {
  count                    = var.enable_azure_storage ? 1 : 0
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main[0].name
  location                 = azurerm_resource_group.main[0].location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "static" {
  count                 = var.enable_azure_storage ? 1 : 0
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.main[0].name
  container_access_type = "private"
}

output "storage_account_name" {
  value = length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].name : ""
}

output "container_name" {
  value = length(azurerm_storage_container.static) > 0 ? azurerm_storage_container.static[0].name : ""
}
