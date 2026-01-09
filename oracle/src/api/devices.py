from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import secrets
import logging
import traceback
import os

# Configure logger
logger = logging.getLogger("cardea.oracle.devices")

# ============ DEMO MODE CONFIGURATION ============
# For the demo, we accept a hardcoded claim code instead of requiring pre-registration
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_CLAIM_CODE = "SN7-K2M"  # Must match the Sentry Bridge's code

# Try-except block allows this to run if 'database' is a sibling or in src
try:
    from database import get_db_connection
except ImportError:
    from src.database import get_db_connection

router = APIRouter()

# --- MODELS ---

class DeviceRegisterRequest(BaseModel):
    hardware_id: str
    version: str = "1.0.0"

class DeviceClaimRequest(BaseModel):
    claim_token: str
    friendly_name: str

class DeviceResponse(BaseModel):
    id: str
    hardware_id: str
    friendly_name: str  # FIXED: Matches database column name
    status: str
    last_seen: Optional[datetime]
    ip_address: Optional[str]
    version: str

# --- ENDPOINTS ---

@router.post("/register")
async def register_device(req: DeviceRegisterRequest):
    """
    Called by the Sentry device on startup.
    Generates a Claim Token if the device is new.
    """
    conn = await get_db_connection()
    try:
        # Check if device exists
        existing = await conn.fetchrow(
            "SELECT id, status, claim_token FROM devices WHERE hardware_id = $1", 
            req.hardware_id
        )

        if existing:
            # Update last_seen
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), version = $1 WHERE hardware_id = $2",
                req.version, req.hardware_id
            )
            return {
                "status": existing["status"],
                "claim_token": existing["claim_token"] if existing["status"] == "UNCLAIMED" else None,
                "message": "Device check-in successful"
            }
        
        # Register new device
        # Generate a 6-digit claim token (e.g., "AB3-9K2")
        claim_token = secrets.token_hex(3).upper() 
        claim_token = f"{claim_token[:3]}-{claim_token[3:]}"
        
        # FIXED: Use UPPERCASE enum values + include device_type
        await conn.execute(
            """
            INSERT INTO devices (hardware_id, friendly_name, status, device_type, claim_token, version, last_seen, created_at)
            VALUES ($1, $2, 'UNCLAIMED', 'SENTRY_PI', $3, $4, NOW(), NOW())
            """,
            req.hardware_id, f"Sentry-{req.hardware_id[-4:]}", claim_token, req.version
        )
        
        return {
            "status": "created",
            "claim_token": claim_token,
            "message": "Device registered successfully"
        }
    finally:
        await conn.close()

@router.post("/claim")
async def claim_device(req: DeviceClaimRequest):
    """
    Called by the Dashboard user to link a device to their account.
    
    DEMO MODE: Accepts hardcoded "SN7-K2M" code and auto-creates a device.
    PRODUCTION MODE: Requires device to be pre-registered with matching claim_token.
    """
    logger.info(f"📱 Claim request received: code='{req.claim_token}', name='{req.friendly_name}'")
    logger.info(f"🔧 DEMO_MODE={DEMO_MODE}, expected code='{DEMO_CLAIM_CODE}'")
    
    conn = None
    try:
        conn = await get_db_connection()
        # Normalize input code (strip whitespace, uppercase)
        input_code = req.claim_token.strip().upper()
        
        # ============ DEMO MODE: Auto-create device with hardcoded code ============
        if DEMO_MODE and input_code == DEMO_CLAIM_CODE:
            logger.info(f"🎯 DEMO MODE: Accepting demo claim code '{input_code}'")
            
            # Check if a demo device already exists (use UPPERCASE enum value)
            existing_demo = await conn.fetchrow(
                "SELECT id, api_key FROM devices WHERE hardware_id LIKE 'demo-%' AND status = 'ONLINE' LIMIT 1"
            )
            
            if existing_demo and existing_demo["api_key"]:
                # Return existing demo device's API key
                logger.info(f"🔄 Returning existing demo device: {existing_demo['id']}")
                return {
                    "success": True,
                    "device_id": str(existing_demo["id"]),
                    "api_key": existing_demo["api_key"],
                    "message": "Demo device already configured - returning existing API key"
                }
            
            # Create a new demo device (let PostgreSQL auto-generate the ID)
            hardware_id = f"demo-{secrets.token_hex(6)}"
            api_key = f"sk-demo-{secrets.token_urlsafe(32)}"
            friendly_name = req.friendly_name or "Demo Sentry"
            
            # Insert and return the auto-generated ID
            # Note: Use UPPERCASE enum values to match PostgreSQL enum definition
            result = await conn.fetchrow(
                """
                INSERT INTO devices (hardware_id, friendly_name, status, device_type, api_key, version, last_seen, created_at)
                VALUES ($1, $2, 'ONLINE', 'SENTRY_PI', $3, '1.0.0', NOW(), NOW())
                RETURNING id
                """,
                hardware_id, friendly_name, api_key
            )
            
            new_id = result["id"] if result else "unknown"
            logger.info(f"🎉 DEMO: Created demo device {hardware_id} with id={new_id}")
            return {
                "success": True,
                "device_id": str(new_id),
                "api_key": api_key,
                "message": "Demo device created successfully"
            }
        
        # ============ PRODUCTION MODE: Find device by claim token ============
        device = await conn.fetchrow(
            "SELECT id, hardware_id FROM devices WHERE claim_token = $1 AND status = 'UNCLAIMED'",
            input_code
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Invalid or expired claim token")

        # Generate a permanent API Key for the device
        api_key = f"sk-{secrets.token_urlsafe(32)}"
        
        # Update device status and API key (use UPPERCASE enum value)
        await conn.execute(
            """
            UPDATE devices 
            SET status = 'ONLINE', 
                friendly_name = $1, 
                claim_token = NULL, 
                api_key = $2,
                updated_at = NOW()
            WHERE id = $3
            """,
            req.friendly_name, api_key, device["id"]
        )
        
        return {
            "success": True,
            "device_id": device["id"],
            "api_key": api_key,
            "message": "Device claimed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Claim device failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to claim device: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/list", response_model=List[DeviceResponse])
async def list_devices():
    """
    Called by Dashboard to show user's devices.
    Hardened to handle database drift and prevent 500 errors.
    """
    conn = None
    try:
        conn = await get_db_connection()
        # FIXED: Querying 'friendly_name' instead of 'name'
        # Added NULLS LAST to ensure active devices appear at the top
        rows = await conn.fetch("""
            SELECT id, hardware_id, friendly_name, status, last_seen, ip_address, version 
            FROM devices 
            ORDER BY last_seen DESC NULLS LAST
        """)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Device List Endpoint failed: {e}")
        traceback.print_exc()
        # Return empty list rather than crashing with 500
        return []
    finally:
        if conn:
            await conn.close()