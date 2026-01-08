# ============================================
# Cardea Authentication - Microsoft Entra External ID
# Provides managed auth with Google/Microsoft federation
# ============================================

# Note: Microsoft Entra External ID (formerly Azure AD B2C) requires manual setup
# for the tenant. This file provisions the application registrations and
# configures the identity providers.
#
# Prerequisites:
# 1. Create an Entra External ID tenant in Azure Portal
# 2. Set the tenant_id variable after creation
#
# Cost: Free tier includes 50,000 MAU (Monthly Active Users)

# ============================================
# Variables for Auth Configuration
# ============================================

variable "entra_tenant_id" {
  description = "Microsoft Entra External ID tenant ID (create tenant first in Azure Portal)"
  type        = string
  default     = null  # Set after creating tenant
}

variable "google_client_id" {
  description = "Google OAuth Client ID for federated login"
  type        = string
  sensitive   = true
  default     = null
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
  default     = null
}

# ============================================
# Azure AD Application Registration (Dashboard)
# ============================================

# This registers the Cardea Dashboard as an application in Entra
# Note: For Entra External ID, you may need to use the azuread provider
# or configure manually in the Azure Portal

resource "azurerm_user_assigned_identity" "cardea_identity" {
  name                = "${var.project_name}-identity"
  resource_group_name = azurerm_resource_group.cardea_rg.name
  location            = azurerm_resource_group.cardea_rg.location

  tags = var.tags
}

# ============================================
# Static Web App Authentication (Built-in)
# ============================================

# Azure Static Web Apps has built-in auth support for:
# - Microsoft (Azure AD)
# - Google
# - GitHub
# - Twitter
#
# This is configured via staticwebapp.config.json in the dashboard

# ============================================
# Outputs for Dashboard Configuration
# ============================================

output "auth_config" {
  description = "Authentication configuration for the dashboard"
  value = {
    # Static Web Apps built-in auth endpoints
    login_microsoft = "/.auth/login/aad"
    login_google    = "/.auth/login/google"
    logout          = "/.auth/logout"
    user_info       = "/.auth/me"
    
    # For custom Entra External ID (if configured)
    entra_tenant_id = var.entra_tenant_id
    
    # Instructions
    setup_notes = <<-EOT
      Azure Static Web Apps provides built-in authentication!
      
      To enable Google login:
      1. Go to Azure Portal > Static Web App > Settings > Identity providers
      2. Add Google and configure OAuth credentials
      
      To enable Microsoft login:
      1. It's enabled by default with Azure AD
      2. Users can sign in with Microsoft accounts
      
      For Entra External ID (advanced):
      1. Create tenant at portal.azure.com > Azure AD B2C
      2. Configure identity providers in the tenant
      3. Update staticwebapp.config.json with custom auth
    EOT
  }
}
