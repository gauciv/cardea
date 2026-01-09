#!/usr/bin/env python3
"""
Oracle Backend Main Entry Point
Cloud-native security analytics and threat correlation platform
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

# Add src to Python path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

from oracle_service import create_app
from database import init_database
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown tasks.
    """
    logger.info("🔮 Initializing Oracle Cloud Brain...")
    
    # 1. Initialize Async Database
    try:
        await init_database()
        logger.info("✅ PostgreSQL Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # In production, for an MVP, a dead DB means a dead service.
        sys.exit(1)
        
    yield  # The application runs while this is paused
    
    logger.info("🛑 Shutting down Oracle Cloud Brain...")

def main():
    """Main entry point"""
    try:
        app = create_app()
        # Attach the lifespan context manager to the app
        app.router.lifespan_context = lifespan
        
        logger.info(f"🌍 Starting Oracle server on port {settings.PORT}")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower()
        )
    except Exception as e:
        logger.error(f"Failed to start Oracle service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()