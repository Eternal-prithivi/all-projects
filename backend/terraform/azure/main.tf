terraform {
  required_version = ">= 1.10.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "main" {
  count    = var.enable_azure_storage || var.enable_vnet || var.enable_azure_vm || var.enable_cosmos ? 1 : 0
  name     = var.resource_group_name
  location = var.azure_location
  tags     = var.tags
}

# --- Blob storage (static site) ---
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

# --- Virtual network ---
resource "azurerm_virtual_network" "main" {
  count               = var.enable_vnet ? 1 : 0
  name                = "zenith-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main[0].location
  resource_group_name = azurerm_resource_group.main[0].name
  tags                = var.tags
}

resource "azurerm_subnet" "main" {
  count                = var.enable_vnet ? 1 : 0
  name                 = "zenith-subnet"
  resource_group_name  = azurerm_resource_group.main[0].name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = ["10.0.1.0/24"]
}

# --- Linux VM ---
resource "azurerm_network_interface" "main" {
  count               = var.enable_azure_vm ? 1 : 0
  name                = "${var.instance_name}-nic"
  location            = azurerm_resource_group.main[0].location
  resource_group_name = azurerm_resource_group.main[0].name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.enable_vnet ? azurerm_subnet.main[0].id : null
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main[0].id
  }

  tags = var.tags
}

resource "azurerm_public_ip" "main" {
  count               = var.enable_azure_vm ? 1 : 0
  name                = "${var.instance_name}-pip"
  location            = azurerm_resource_group.main[0].location
  resource_group_name = azurerm_resource_group.main[0].name
  allocation_method   = "Static"
  sku                 = "Basic"
  tags                = var.tags
}

resource "azurerm_linux_virtual_machine" "main" {
  count               = var.enable_azure_vm ? 1 : 0
  name                = var.instance_name
  resource_group_name = azurerm_resource_group.main[0].name
  location            = azurerm_resource_group.main[0].location
  size                = var.vm_size
  admin_username      = "zenithadmin"

  network_interface_ids = [
    azurerm_network_interface.main[0].id,
  ]

  admin_ssh_key {
    username   = "zenithadmin"
    public_key = tls_private_key.vm[0].public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = var.disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  tags = var.tags
}

resource "tls_private_key" "vm" {
  count     = var.enable_azure_vm ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# --- Monitor action group (email) ---
resource "azurerm_monitor_action_group" "main" {
  count               = var.enable_azure_monitor && var.alarm_email != "" ? 1 : 0
  name                = "zenith-alerts"
  resource_group_name = azurerm_resource_group.main[0].name
  short_name          = "zenith"

  email_receiver {
    name          = "admin"
    email_address = var.alarm_email
  }

  tags = var.tags
}

# --- Cosmos DB (serverless-style account) ---
resource "azurerm_cosmosdb_account" "main" {
  count                = var.enable_cosmos ? 1 : 0
  name                 = var.cosmos_account_name
  location             = azurerm_resource_group.main[0].location
  resource_group_name  = azurerm_resource_group.main[0].name
  offer_type           = "Standard"
  kind                 = "GlobalDocumentDB"
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    location          = azurerm_resource_group.main[0].location
    failover_priority = 0
  }
  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  count               = var.enable_cosmos ? 1 : 0
  name                = var.cosmos_database_name
  resource_group_name = azurerm_resource_group.main[0].name
  account_name        = azurerm_cosmosdb_account.main[0].name
}

output "storage_account_name" {
  value = length(azurerm_storage_account.main) > 0 ? azurerm_storage_account.main[0].name : ""
}

output "container_name" {
  value = length(azurerm_storage_container.static) > 0 ? azurerm_storage_container.static[0].name : ""
}

output "vm_public_ip" {
  value = length(azurerm_public_ip.main) > 0 ? azurerm_public_ip.main[0].ip_address : ""
}

output "cosmos_endpoint" {
  value = length(azurerm_cosmosdb_account.main) > 0 ? azurerm_cosmosdb_account.main[0].endpoint : ""
}
