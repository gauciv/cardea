# ============================================
# Cardea Oracle - Azure Container Apps
# Hosts the Oracle backend with managed services
# ============================================

# Container Apps Environment (hosts all container apps)
resource "azurerm_container_app_environment" "oracle_env" {
  name                = "${var.project_name}-oracle-env"
  location            = azurerm_resource_group.cardea_rg.location
  resource_group_name = azurerm_resource_group.cardea_rg.name
  
  log_analytics_workspace_id = azurerm_log_analytics_workspace.oracle_logs.id

  tags = var.tags
}

# Log Analytics for monitoring
# BUDGET: Minimal retention to reduce costs
resource "azurerm_log_analytics_workspace" "oracle_logs" {
  name                = "${var.project_name}-oracle-logs"
  location            = azurerm_resource_group.cardea_rg.location
  resource_group_name = azurerm_resource_group.cardea_rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30  # Minimum retention to save costs

  tags = var.tags
}

# Azure Container Registry for Docker images
# BUDGET: Use Basic tier for both dev and prod (~$5/month)
resource "azurerm_container_registry" "acr" {
  name                = "${var.project_name}registry"  # Must be globally unique, alphanumeric only
  resource_group_name = azurerm_resource_group.cardea_rg.name
  location            = azurerm_resource_group.cardea_rg.location
  sku                 = "Basic"  # Basic is sufficient for Imagine Cup
  admin_enabled       = true

  tags = var.tags
}

# Azure Cache for Redis (managed Redis)
# BUDGET: Use Basic C0 for both dev and prod (~$16/month)
resource "azurerm_redis_cache" "oracle_redis" {
  name                          = "${var.project_name}-oracle-redis"
  location                      = azurerm_resource_group.cardea_rg.location
  resource_group_name           = azurerm_resource_group.cardea_rg.name
  capacity                      = 0  # C0 = 250MB, smallest tier
  family                        = "C"
  sku_name                      = "Basic"  # Basic is sufficient for demo
  non_ssl_port_enabled          = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true

  redis_configuration {
    maxmemory_policy = "volatile-lru"
  }

  tags = var.tags
}

# Azure Database for PostgreSQL Flexible Server
# BUDGET OPTIMIZED: Using Burstable tier even in prod for Imagine Cup
resource "azurerm_postgresql_flexible_server" "oracle_db" {
  name                   = "${var.project_name}-oracle-db"
  resource_group_name    = azurerm_resource_group.cardea_rg.name
  location               = azurerm_resource_group.cardea_rg.location
  version                = "15"
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password != null ? var.db_admin_password : random_password.db_password.result
  
  # BUDGET: Use Burstable B1ms for both dev and prod (~$13/month)
  # For enterprise prod, use: GP_Standard_D2s_v3
  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768  # 32GB is plenty for demo

  # BUDGET: Disable HA for Imagine Cup (saves ~$13/month)
  # For enterprise prod, enable zone redundant HA
  # dynamic "high_availability" {
  #   for_each = var.is_production ? [1] : []
  #   content {
  #     mode = "ZoneRedundant"
  #   }
  # }

  # Ignore zone changes - Azure assigns zone and we can't change it without HA
  lifecycle {
    ignore_changes = [zone]
  }

  tags = var.tags
}

# Generate random password if not provided
resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "cardea_db" {
  name      = "cardea_oracle"
  server_id = azurerm_postgresql_flexible_server.oracle_db.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.oracle_db.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Firewall rules for Sentry locations (on-premise)
resource "azurerm_postgresql_flexible_server_firewall_rule" "sentry_access" {
  for_each = { for idx, ip in var.sentry_allowed_ips : idx => ip }
  
  name             = "SentryAccess-${each.key}"
  server_id        = azurerm_postgresql_flexible_server.oracle_db.id
  start_ip_address = each.value
  end_ip_address   = each.value
}

# Oracle Container App
resource "azurerm_container_app" "oracle" {
  name                         = "${var.project_name}-oracle"
  container_app_environment_id = azurerm_container_app_environment.oracle_env.id
  resource_group_name          = azurerm_resource_group.cardea_rg.name
  revision_mode                = "Single"

  # Use system-assigned managed identity for secure resource access
  identity {
    type = "SystemAssigned"
  }

  # Container registry credentials
  registry {
    server               = azurerm_container_registry.acr.login_server
    username             = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  # Secrets (referenced in container env vars)
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }

  secret {
    name  = "db-connection-string"
    value = "postgresql+asyncpg://${var.db_admin_username}:${var.db_admin_password != null ? var.db_admin_password : random_password.db_password.result}@${azurerm_postgresql_flexible_server.oracle_db.fqdn}:5432/cardea_oracle?ssl=require"
  }

  secret {
    name  = "redis-connection-string"
    value = "rediss://:${azurerm_redis_cache.oracle_redis.primary_access_key}@${azurerm_redis_cache.oracle_redis.hostname}:${azurerm_redis_cache.oracle_redis.ssl_port}/0"
  }

  secret {
    name  = "openai-api-key"
    value = azurerm_cognitive_account.openai.primary_access_key
  }

  secret {
    name  = "sentry-api-key"
    value = var.sentry_api_key != null ? var.sentry_api_key : random_password.sentry_api_key.result
  }

  template {
    # BUDGET: Scale to zero when not in use (pay only when active)
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "oracle"
      image  = "${azurerm_container_registry.acr.login_server}/${var.project_name}-oracle:${var.oracle_image_tag}"
      # BUDGET: Minimal resources (0.25 CPU, 0.5Gi RAM)
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "db-connection-string"
      }

      env {
        name        = "REDIS_URL"
        secret_name = "redis-connection-string"
      }

      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = azurerm_cognitive_account.openai.endpoint
      }

      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = azurerm_cognitive_deployment.oracle_brain.name
      }

      env {
        name  = "AZURE_SEARCH_ENDPOINT"
        value = "https://${azurerm_search_service.search.name}.search.windows.net"
      }

      env {
        name  = "AI_ENABLED"
        value = "true"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.is_production ? "WARNING" : "INFO"
      }

      env {
        name        = "SENTRY_API_KEY"
        secret_name = "sentry-api-key"
      }

      # Liveness probe - checks if container is alive
      liveness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8000
        interval_seconds = 30
        timeout          = 5
        failure_count_threshold = 3
      }

      # Readiness probe - checks if container is ready to receive traffic
      readiness_probe {
        transport        = "HTTP"
        path             = "/health"
        port             = 8000
        interval_seconds = 10
        timeout          = 3
        failure_count_threshold = 3
      }
    }
  }

  # Ingress configuration - external access
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    # Allow Sentry IPs if specified
    dynamic "ip_security_restriction" {
      for_each = length(var.sentry_allowed_ips) > 0 ? var.sentry_allowed_ips : []
      content {
        name             = "SentryAccess-${ip_security_restriction.key}"
        ip_address_range = ip_security_restriction.value
        action           = "Allow"
      }
    }
  }

  tags = var.tags
}

# Generate Sentry API key if not provided
resource "random_password" "sentry_api_key" {
  length  = 32
  special = false
}

# Grant Oracle access to Key Vault (if needed later)
# resource "azurerm_role_assignment" "oracle_keyvault" {
#   scope                = azurerm_key_vault.cardea_kv.id
#   role_definition_name = "Key Vault Secrets User"
#   principal_id         = azurerm_container_app.oracle.identity[0].principal_id
# }
