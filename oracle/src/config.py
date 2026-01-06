"""
Oracle Backend Configuration
Updated for Pydantic v2 and environment-based configuration
Supports both development and production environments via DEPLOYMENT_ENVIRONMENT
"""

from typing import Literal, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings with environment variable support (Pydantic v2)
    
    Environment Variables:
        DEPLOYMENT_ENVIRONMENT: 'development' | 'staging' | 'production'
        DATABASE_URL: PostgreSQL connection string
        AZURE_OPENAI_API_KEY: Azure OpenAI API key (required for AI features)
    """
    
    # Service Configuration
    APP_NAME: str = "Cardea Oracle Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=True, description="Enable debug mode (auto-disabled in production)")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    PORT: int = 8000
    
    # Environment Configuration
    DEPLOYMENT_ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment - controls security defaults and logging"
    )
    
    # Database Configuration - PostgreSQL only (no SQLite support)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://oracle:oracle_dev_password@db:5432/cardea_oracle",
        description="PostgreSQL connection URL (must use asyncpg driver)"
    )
    
    # Redis Configuration  
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL for caching and rate limiting"
    )
    REDIS_HOST: str = Field(default="redis", description="Redis host (for backward compatibility)")
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT signing key - MUST be changed in production"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Sentry Integration
    SENTRY_WEBHOOK_TOKEN: str = "sentry-webhook-token"
    
    # Alert Processing
    MAX_ALERTS_PER_BATCH: int = 100
    ALERT_RETENTION_DAYS: int = 90
    
    # Threat Intelligence
    THREAT_SCORE_THRESHOLD: float = 0.7
    CORRELATION_WINDOW_MINUTES: int = 60
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: Optional[str] = Field(
        default=None, 
        description="Azure OpenAI API key"
    )
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(
        default=None, 
        description="Azure OpenAI endpoint URL"
    )
    AZURE_OPENAI_DEPLOYMENT: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment name"
    )
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"
    
    # Azure AI Search Configuration (RAG for threat intelligence)
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_KEY: Optional[str] = None
    AZURE_SEARCH_INDEX_NAME: str = "threat-intelligence"
    
    # AI Agent Configuration
    AI_ENABLED: bool = Field(
        default=False, 
        description="Enable AI-powered analysis (requires Azure OpenAI keys)"
    )
    AI_MODEL_TEMPERATURE: float = Field(default=0.3, ge=0.0, le=2.0)
    AI_MAX_TOKENS: int = Field(default=150, ge=50, le=4096)
    
    # Cloud Configuration
    CLOUD_PROVIDER: Optional[str] = None
    
    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="*",
        description="Comma-separated list of allowed origins (use specific origins in production)"
    )
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure PostgreSQL is used with asyncpg driver"""
        if "sqlite" in v.lower():
            raise ValueError("SQLite is not supported. Use PostgreSQL with asyncpg driver.")
        if v.startswith("postgresql://"):
            # Auto-convert to asyncpg
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg:// driver")
        return v
    
    @field_validator("SECRET_KEY")
    @classmethod  
    def validate_secret_key(cls, v: str, info) -> str:
        """Warn if using default secret key in production"""
        # Get environment from already validated fields
        env = info.data.get("DEPLOYMENT_ENVIRONMENT", "development")
        if env == "production" and v == "your-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production environment!")
        return v
    
    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.DEPLOYMENT_ENVIRONMENT == "production"
    
    @computed_field
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.DEPLOYMENT_ENVIRONMENT == "development"
    
    @computed_field
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    def get_effective_debug(self) -> bool:
        """Get effective debug mode (always False in production)"""
        if self.is_production:
            return False
        return self.DEBUG
    
    def get_effective_log_level(self) -> str:
        """Get effective log level (WARNING minimum in production)"""
        if self.is_production and self.LOG_LEVEL == "DEBUG":
            return "INFO"
        return self.LOG_LEVEL
    
    # Pydantic v2 Model Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Prevents crashes if extra vars exist in .env
    )

# Global settings instance
settings = Settings()