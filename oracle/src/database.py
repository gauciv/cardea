"""
Database Models and Connection Management
SQLAlchemy models for Oracle backend data persistence (Async PostgreSQL optimized)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)

# Database base
class Base(DeclarativeBase):
    pass

# Database engine and session globals
engine = None
async_session = None

# --- Models ---

class Alert(Base):
    """Alert data model"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Note: using timezone-aware defaults is better for Cloud/Azure deployments
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    threat_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    
    raw_data = Column(JSON, nullable=True)
    network_context = Column(JSON, nullable=True)
    correlations = Column(JSON, nullable=True)
    indicators = Column(JSON, nullable=True)
    
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
    
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    alerts = relationship("Alert", back_populates="threat_intel")

# (SystemMetrics, User, AlertCorrelation remain largely same, 
# just ensure DateTime(timezone=True) is used for consistency)

# --- Connection Management ---

async def init_database():
    """Initialize database connection and create tables"""
    global engine, async_session
    
    try:
        db_url = settings.DATABASE_URL
        
        # 1. ENFORCE ASYNC DRIVER: PostgreSQL requires +asyncpg for async SQLAlchemy
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        logger.info(f"Connecting to database via: {db_url.split('@')[-1]}") # Log endpoint only for security
        
        # 2. CREATE ENGINE
        engine = create_async_engine(
            db_url,
            echo=False, # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        
        # 3. CREATE SESSION FACTORY
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # 4. SYNC TO ASYNC TABLE CREATION
        async with engine.begin() as conn:
            # We must use run_sync for Base.metadata operations
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database schemas synced and connection ready.")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

@asynccontextmanager
async def get_db():
    """FastAPI Dependency - Database session context manager"""
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

async def close_database():
    """Graceful shutdown for database connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection pool closed.")