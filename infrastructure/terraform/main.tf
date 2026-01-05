# 1. Provider & Variable Configuration
terraform {
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

# TOGGLE THIS: Set to true when you're ready for the hackathon/demo
variable "is_production" {
  type    = bool
  default = false 
}

# 2. Resource Group
resource "azurerm_resource_group" "cardea_rg" {
  name     = "rg-cardea-oracle"
  location = "East Asia"
}

# 3. Azure OpenAI (Sweden Central)
resource "azurerm_cognitive_account" "openai" {
  name                = "cardea-openai-service"
  location            = "swedencentral" 
  resource_group_name = azurerm_resource_group.cardea_rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
}

# Logic: Use gpt-4o-mini for Dev, gpt-4o for Prod
resource "azurerm_cognitive_deployment" "oracle_brain" {
  name                 = "oracle-brain" # Static name so your code doesn't have to change
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = var.is_production ? "gpt-4o" : "gpt-4o-mini"
    version = var.is_production ? "2024-05-13" : "2024-07-18" 
  }

  scale {
    type     = "Standard"
    capacity = 10 
  }
}

# 4. Azure AI Search
resource "azurerm_search_service" "search" {
  name                = "cardea-threat-search"
  resource_group_name = azurerm_resource_group.cardea_rg.name
  location            = "swedencentral" 
  
  # Logic: Free tier for Dev ($0), Basic for Prod (~$73/mo)
  sku = var.is_production ? "basic" : "free" 
}

# 5. Outputs
output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "current_mode" {
  value = var.is_production ? "PRODUCTION (GPT-4o)" : "DEVELOPMENT (GPT-4o-mini / Free Search)"
}