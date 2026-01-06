#!/usr/bin/env python3
"""
Oracle Startup Script
Handles database migrations and service initialization
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_migrations():
    """Run Alembic migrations"""
    import subprocess
    
    logger.info("🔄 Running database migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        logger.info("✅ Migrations completed successfully")
        return True
    else:
        logger.error(f"❌ Migration failed: {result.stderr}")
        return False


async def wait_for_postgres(max_retries: int = 30, delay: float = 2.0):
    """Wait for PostgreSQL to be ready"""
    import asyncpg
    from config import settings
    
    # Parse connection string
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    for attempt in range(max_retries):
        try:
            conn = await asyncpg.connect(db_url, timeout=5)
            await conn.close()
            logger.info("✅ PostgreSQL is ready")
            return True
        except Exception as e:
            logger.warning(f"⏳ Waiting for PostgreSQL... (attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(delay)
    
    logger.error("❌ PostgreSQL not available after maximum retries")
    return False


async def main():
    """Main startup sequence"""
    logger.info("🚀 Oracle Startup Script")
    
    # Wait for database
    if not await wait_for_postgres():
        sys.exit(1)
    
    # Run migrations
    if not await run_migrations():
        logger.warning("⚠️ Migrations failed, continuing anyway...")
    
    logger.info("✅ Startup complete - Oracle ready to serve")


if __name__ == "__main__":
    asyncio.run(main())
