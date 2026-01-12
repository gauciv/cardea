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

# --- PATH CONFIGURATION & DEBUGGING ---
# Ensure the directory containing this file is in sys.path
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

# Configure logging early (default to INFO) so we can see import errors
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("cardea.oracle")

# Debug: Print filesystem state (Critical for Azure troubleshooting)
logger.info(f"📂 Current Working Directory: {os.getcwd()}")
logger.info(f"🐍 Python Path: {sys.path}")
try:
    logger.info(f"📂 Directory contents of {current_dir}: {os.listdir(current_dir)}")
    if (current_dir / "api").exists():
        logger.info(f"📂 Directory contents of api: {os.listdir(current_dir / 'api')}")
    else:
        logger.warning(f"⚠️ 'api' directory not found in {current_dir}")
except Exception as e:
    logger.warning(f"Could not list directories: {e}")

# --- ROBUST IMPORTS ---
# Try importing normally, fallback to 'src.' prefix if needed (common in Docker)
try:
    from database import init_database
    from config import settings
    # Import API Routers
    from api import analytics, actions, devices, alerts
except ImportError as e:
    logger.warning(f"⚠️ Standard import failed: {e}. Attempting 'src.' fallback...")
    try:
        from src.database import init_database
        from src.config import settings
        from src.api import analytics, actions, devices, alerts
        logger.info("✅ Recovered using 'src.' prefix imports")
    except ImportError as e2:
        logger.critical(f"❌ FATAL: Could not import modules even with fallback: {e2}")
        sys.exit(1)

# Re-configure logging level if settings loaded successfully
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

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
# Explicitly whitelist allowed domains to fix CORS errors
origins = [
    "http://localhost:5173",  # Local development
    "http://localhost:4173",  # Local preview
    "https://cardea.triji.me", # <--- PRODUCTION FRONTEND (Fixes your error)
    "https://cardea-oracle.greenbeach-350af183.eastasia.azurecontainerapps.io", # Self/Backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Use the explicit list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTER ROUTERS ---
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(actions.router, prefix="/api/actions", tags=["Actions"])
app.include_router(devices.router, prefix="/api/devices", tags=["Devices"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])

@app.get("/health")
async def health_check():
    """Simple health probe for container orchestrators"""
    return {"status": "online", "service": "cardea-oracle"}

def main():
    """Main entry point for local execution"""
    try:
        # Use env var PORT if available (Azure injects this), else config default
        port = int(os.getenv("PORT", settings.PORT))
        logger.info(f"🌍 Starting Oracle server on port {port}")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            log_level=settings.LOG_LEVEL.lower(),
            reload=True # Enable auto-reload for development
        )
    except Exception as e:
        logger.error(f"Failed to start Oracle service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()