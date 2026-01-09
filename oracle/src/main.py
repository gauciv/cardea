#!/usr/bin/env python3
"""
Oracle Backend Main Entry Point
Cloud-native security analytics and threat correlation platform
"""

import logging
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to Python path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

# Import Configuration & Database
from database import init_database
from config import settings

# Import API Routers
# We import these directly to ensure the new 'devices' endpoint is registered
from api import analytics, actions, devices

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown tasks.
    Run database migrations and initialize connections.
    """
    logger.info("🔮 Initializing Oracle Cloud Brain...")
    
    # 1. Initialize Async Database (Auto-create tables)
    try:
        await init_database()
        logger.info("✅ PostgreSQL Database initialized successfully")
    except Exception as e:
        logger.critical(f"❌ Database initialization failed: {e}")
        # In production, if DB fails, the service is useless. Fail fast.
        sys.exit(1)
        
    yield  # Application runs here
    
    logger.info("🛑 Shutting down Oracle Cloud Brain...")

# --- APP DEFINITION ---
app = FastAPI(
    title="Cardea Oracle",
    description="AI-Powered Security Backend",
    version="1.0.0",
    lifespan=lifespan
)

# --- CRITICAL FIX: CORS MIDDLEWARE ---
# This allows your Dashboard (frontend) to talk to this Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, strictly restrict this to your Static App URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTER ROUTERS ---
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(actions.router, prefix="/api/actions", tags=["Actions"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"]) # New Devices Endpoint

@app.get("/health")
async def health_check():
    """Simple health probe for container orchestrators"""
    return {"status": "online", "service": "cardea-oracle"}

def main():
    """Main entry point for local execution"""
    try:
        logger.info(f"🌍 Starting Oracle server on port {settings.PORT}")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower(),
            reload=True # Enable auto-reload for development
        )
    except Exception as e:
        logger.error(f"Failed to start Oracle service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()