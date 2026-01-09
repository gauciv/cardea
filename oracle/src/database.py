"""
Database Models and Connection Management
SQLAlchemy models for Oracle backend data persistence (Async PostgreSQL optimized)
"""

import logging
import os
import ssl
import asyncpg
from urllib.parse import urlparse, urlunparse
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Boolean,
    Enum as SQLEnum
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from config import settings
from models import DeviceStatus, DeviceType

logger = logging.getLogger(__name__)

# Database base
class Base(DeclarativeBase):
    pass

# Database engine and session globals
engine = None
async_session = None
POOL = None  # Global raw connection pool

# --- Models ---

class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(200), nullable=True)
    
    is_active = Column(Boolean, default=True)
    roles = Column(JSON, default=list)
    
    # Auth & Security
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(100), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    password_reset_token = Column(String(100), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    
    failed_login_attempts = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Azure AD / OAuth mapping
    oauth_provider_id = Column(String(100), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    alerts = relationship("Alert", back_populates="user")
    devices = relationship("Device", back_populates="user")


class Device(Base):
    """IoT Sentry Device model"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    hardware_id = Column(String(100), unique=True, index=True, nullable=False, doc="Immutable Machine ID from Raspberry Pi")
    friendly_name = Column(String(100), nullable=True)
    
    # Status
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.UNCLAIMED, nullable=False)
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.SENTRY_PI, nullable=False)
    version = Column(String(20), default="1.0.0")
    
    # Security & Claiming
    claim_token = Column(String(100), nullable=True, index=True, doc="Token displayed on Sentry local portal for claiming")
    api_key = Column(String(100), unique=True, nullable=True, doc="Generated after claiming for API auth")
    public_key = Column(Text, nullable=True, doc="For E2E encryption")
    
    # Connectivity
    last_seen = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user = relationship("User", back_populates="devices")
    
    # Data
    alerts = relationship("Alert", back_populates="device")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Alert(Base):
    """Alert data model"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    threat_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    
    raw_data = Column(JSON, nullable=True)
    network_context = Column(JSON, nullable=True)
    correlations = Column(JSON, nullable=True)
    indicators = Column(JSON, nullable=True)
    
    # User who owns this alert (Legacy/Direct)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    user = relationship("User", back_populates="alerts")
    
    # Device that generated this alert
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='SET NULL'), nullable=True, index=True)
    device = relationship("Device", back_populates="alerts")
    
    threat_intel_id = Column(Integer, ForeignKey("threat_intelligence.id"), nullable=True)
    threat_intel = relationship("ThreatIntelligence", back_populates="alerts")
    
    __table_args__ = (
        Index('idx_alerts_timestamp_severity', 'timestamp', 'severity'),
        Index('idx_alerts_source_type', 'source', 'alert_type'),
        Index('idx_alerts_threat_score', 'threat_score'),
    )

class ThreatIntelligence(Base):
    """Threat intelligence data model"""
    __tablename__ = "threat_intelligence"
    
    id = Column(Integer, primary_key=True, index=True)
    threat_id = Column(String(100), unique=True, nullable=False, index=True)
    threat_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    indicators = Column(JSON, nullable=True)
    tactics = Column(JSON, nullable=True)
    techniques = Column(JSON, nullable=True)
    
    first_seen = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    alerts = relationship("Alert", back_populates="threat_intel")

# --- Connection Management ---

def create_ssl_context():
    """Create a safe SSL context for Azure PostgreSQL"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # Accept Azure's cert without strictly verifying chain
    return ctx

async def init_database():
    """Initialize database connection (ORM and Raw Pool) and create tables"""
    global engine, async_session, POOL
    
    try:
        db_url = settings.DATABASE_URL
        
        # 1. SETUP RAW POOL (asyncpg)
        logger.info("Initializing raw asyncpg connection pool...")
        
        # Parse URL to strip ALL query parameters (like sslmode=require)
        # This prevents conflict with the manual SSL context we are passing
        parsed = urlparse(db_url)
        # Reconstruct URL with scheme 'postgresql' and NO query params
        # This keeps user:pass@host:port/dbname
        clean_url = urlunparse(("postgresql", parsed.netloc, parsed.path, "", "", ""))
        
        ssl_ctx = create_ssl_context()
        
        POOL = await asyncpg.create_pool(
            clean_url,
            min_size=1,
            max_size=10,
            ssl=ssl_ctx
        )
        
        # --- CRITICAL FIX: SCHEMA PATCHING (AUTO-HEAL) ---
        # This block runs raw SQL to fix the "UndefinedColumnError"
        logger.info("🛠️ Running Schema Patch (Auto-Healing)...")
        async with POOL.acquire() as conn:
            try:
                # Add device_id if missing
                await conn.execute("""
                    ALTER TABLE alerts 
                    ADD COLUMN IF NOT EXISTS device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL;
                """)
                # Add threat_intel_id if missing
                await conn.execute("""
                    ALTER TABLE alerts 
                    ADD COLUMN IF NOT EXISTS threat_intel_id INTEGER REFERENCES threat_intelligence(id);
                """)
                logger.info("✅ Schema patch applied successfully.")
            except Exception as e:
                # Safe to ignore if constraints or columns cause minor issues on retry
                logger.warning(f"⚠️ Schema patch warning: {e}")

        # 2. SETUP ORM ENGINE (SQLAlchemy)
        # Use the original URL but ensure +asyncpg scheme
        orm_url = db_url
        if orm_url.startswith("postgresql://"):
            orm_url = orm_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        logger.info(f"Connecting to ORM via: {orm_url.split('@')[-1]}")
        
        # Pass SSL context via connect_args for SQLAlchemy/asyncpg
        engine = create_async_engine(
            orm_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"ssl": ssl_ctx} 
        )
        
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 3. CREATE TABLES
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database schemas synced and connection ready.")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise

@asynccontextmanager
async def get_db():
    """FastAPI Dependency - ORM Session"""
    if async_session is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db_connection():
    """
    Returns a raw asyncpg connection from the pool.
    Used by high-performance endpoints (e.g. device registration).
    The caller MUST close the connection (release it back to pool).
    """
    global POOL
    if POOL is None:
        # Fallback initialization
        await init_database()
    
    if POOL is None:
        raise RuntimeError("Database pool failed to initialize")
        
    return await POOL.acquire()

async def close_database():
    """Graceful shutdown for database connections"""
    global engine, POOL
    if engine:
        await engine.dispose()
    if POOL:
        await POOL.close()
    logger.info("Database connection pools closed.")