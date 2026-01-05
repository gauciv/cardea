"""
Oracle Backend Configuration
Updated for Pydantic v2 and environment-based configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict # FIX: Correct Pydantic v2 imports
from pydantic import Field

class Settings(BaseSettings):
    """Application settings with environment variable support (Pydantic v2)"""
    
    # Service Configuration
    APP_NAME: str = "Cardea Oracle Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    
    # Database Configuration (FIX: Default set to your Docker DB container name)
    DATABASE_URL: str = "postgresql+asyncpg://oracle:oracle_dev_password@db:5432/cardea_oracle"
    
    # Redis Configuration  
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Security Configuration
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Sentry Integration
    SENTRY_WEBHOOK_TOKEN: str = "sentry-webhook-token"
    
    # Alert Processing
    MAX_ALERTS_PER_BATCH: int = 100
    ALERT_RETENTION_DAYS: int = 90
    
    # Threat Intelligence
    THREAT_SCORE_THRESHOLD: float = 0.7
    CORRELATION_WINDOW_MINUTES: int = 60
    
    # Azure OpenAI Configuration (FIX: Defaults to prevent validation crash)
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    
    # Azure AI Search Configuration (RAG for threat intelligence)
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_KEY: Optional[str] = None
    AZURE_SEARCH_INDEX_NAME: str = "threat-intelligence"
    
    # AI Agent Configuration
    AI_ENABLED: bool = False # Disabled by default until keys are provided
    AI_MODEL_TEMPERATURE: float = 0.3
    AI_MAX_TOKENS: int = 1500
    
    # Cloud Configuration
    CLOUD_PROVIDER: Optional[str] = None
    DEPLOYMENT_ENVIRONMENT: str = "development"
    
    # Pydantic v2 Model Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore" # Prevents crashes if extra vars exist in .env
    )

# Global settings instance
settings = Settings()