# ============================================
# Cardea Infrastructure - Main Configuration
# ============================================
# This is the central Terraform configuration for Project Cardea.
# It provisions all Azure resources needed for the platform.
#
# Architecture:
#   - Dashboard: Azure Static Web App (React frontend)
#   - Oracle: Azure Container Apps (FastAPI backend)
#   - Database: Azure PostgreSQL Flexible Server
#   - Cache: Azure Cache for Redis
#   - AI: Azure OpenAI + Azure AI Search
#
# Usage:
#   terraform init
#   terraform plan -var-file="dev.tfvars"
#   terraform apply -var-file="dev.tfvars"
# ============================================

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Uncomment to use Azure Storage for remote state
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "cardeatfstate"
  #   container_name       = "tfstate"
  #   key                  = "cardea.tfstate"
  # }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}

provider "random" {}

# ============================================
# Resource Group
# ============================================
resource "azurerm_resource_group" "cardea_rg" {
  name     = "rg-${var.project_name}-${var.is_production ? "prod" : "dev"}"
  location = var.location

  tags = var.tags
}

# ============================================
# Azure OpenAI Service
# ============================================
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.project_name}-openai-${var.is_production ? "prod" : "dev"}"
  location            = var.ai_location
  resource_group_name = azurerm_resource_group.cardea_rg.name
  kind                = "OpenAI"
  sku_name            = "S0"

  tags = var.tags
}

# Model Deployment: GPT-4o-mini for cost efficiency
# BUDGET: GPT-4o-mini is 10-20x cheaper than GPT-4o
resource "azurerm_cognitive_deployment" "oracle_brain" {
  name                 = "oracle-brain"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = "gpt-4o-mini"  # Always use mini for budget
    version = "2024-07-18"
  }

  sku {
    name     = "Standard"
    capacity = 10  # Low capacity is fine for demo
  }
}

# ============================================
# Azure AI Search (for RAG)
# ============================================
# BUDGET: Free tier for both dev and prod (3 indexes, 50MB)
resource "azurerm_search_service" "search" {
  name                = "${var.project_name}-search-${var.is_production ? "prod" : "dev"}"
  resource_group_name = azurerm_resource_group.cardea_rg.name
  location            = var.ai_location

  sku = "free"  # Free tier: 3 indexes, 50MB storage

  tags = var.tags
}