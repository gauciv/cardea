from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import secrets
import logging
import traceback

# Configure logger
logger = logging.getLogger("cardea.oracle.devices")

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
                "claim_token": existing["claim_token"] if existing["status"] == "unclaimed" else None,
                "message": "Device check-in successful"
            }
        
        # Register new device
        new_id = str(uuid.uuid4())
        # Generate a 6-digit claim token (e.g., "AB3-9K2")
        claim_token = secrets.token_hex(3).upper() 
        claim_token = f"{claim_token[:3]}-{claim_token[3:]}"
        
        # FIXED: Insert into 'friendly_name' instead of 'name'
        await conn.execute(
            """
            INSERT INTO devices (id, hardware_id, friendly_name, status, claim_token, version, last_seen)
            VALUES ($1, $2, $3, 'unclaimed', $4, $5, NOW())
            """,
            new_id, req.hardware_id, f"Sentry-{req.hardware_id[-4:]}", claim_token, req.version
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
    """
    conn = await get_db_connection()
    try:
        # Find device by claim token
        device = await conn.fetchrow(
            "SELECT id, hardware_id FROM devices WHERE claim_token = $1 AND status = 'unclaimed'",
            req.claim_token
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Invalid or expired claim token")

        # Generate a permanent API Key for the device
        api_key = f"sk-{secrets.token_urlsafe(32)}"
        
        # FIXED: Update 'friendly_name' instead of 'name'
        await conn.execute(
            """
            UPDATE devices 
            SET status = 'online', 
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
    finally:
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