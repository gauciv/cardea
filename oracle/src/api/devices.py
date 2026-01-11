"""
Device Management API - Handles Sentry device registration and pairing
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import secrets
import logging
import traceback

logger = logging.getLogger("cardea.oracle.devices")

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
    friendly_name: Optional[str] = "Sentry Device"

class DeviceResponse(BaseModel):
    id: int
    hardware_id: str
    friendly_name: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None
    ip_address: Optional[str] = None
    version: Optional[str] = "1.0.0"

# --- HELPER: Generate readable pairing code ---
def generate_pairing_code() -> str:
    """Generate a 6-char pairing code like 'A3K-9M2'"""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No I,O,0,1 to avoid confusion
    code = ''.join(secrets.choice(chars) for _ in range(6))
    return f"{code[:3]}-{code[3:]}"

# --- ENDPOINTS ---

@router.post("/register")
async def register_device(req: DeviceRegisterRequest):
    """
    Called by Sentry on startup to register and get a pairing code.
    If device exists and is already claimed, returns status only.
    If device is new or unclaimed, returns/generates pairing code.
    """
    logger.info(f"📱 Device registration: {req.hardware_id}")
    conn = await get_db_connection()
    try:
        # Check if device exists
        existing = await conn.fetchrow(
            "SELECT id, status, claim_token, api_key FROM devices WHERE hardware_id = $1", 
            req.hardware_id
        )

        if existing:
            # Update last_seen
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), version = $1 WHERE hardware_id = $2",
                req.version, req.hardware_id
            )
            
            status = existing["status"].lower() if existing["status"] else "unknown"
            
            # If already claimed/online, don't return claim token
            if status in ("online", "offline") and existing["api_key"]:
                logger.info(f"✅ Device {req.hardware_id} already claimed")
                return {
                    "status": status,
                    "claim_token": None,
                    "message": "Device already registered"
                }
            
            # If unclaimed, return existing claim token
            logger.info(f"🔑 Device {req.hardware_id} unclaimed, returning token")
            return {
                "status": "unclaimed",
                "claim_token": existing["claim_token"],
                "message": "Device awaiting claim"
            }
        
        # New device - generate pairing code
        claim_token = generate_pairing_code()
        
        await conn.execute(
            """
            INSERT INTO devices (hardware_id, friendly_name, status, device_type, claim_token, version, last_seen, created_at)
            VALUES ($1, $2, 'UNCLAIMED', 'SENTRY_PI', $3, $4, NOW(), NOW())
            """,
            req.hardware_id, f"Sentry-{req.hardware_id[-4:]}", claim_token, req.version
        )
        
        logger.info(f"✅ New device registered: {req.hardware_id} with code {claim_token}")
        return {
            "status": "unclaimed",
            "claim_token": claim_token,
            "message": "Device registered - use this code in your Oracle dashboard"
        }
    finally:
        await conn.close()

@router.post("/claim")
async def claim_device(req: DeviceClaimRequest, authorization: Optional[str] = Header(None)):
    """
    Called by Dashboard user to claim a device using pairing code.
    Requires user authentication (Bearer token).
    Returns API key for the Sentry to use.
    """
    logger.info(f"📱 Claim request: code='{req.claim_token}'")
    
    # Extract user_id from token (simplified - in production use proper JWT validation)
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        # For now, user_id stays None until proper JWT auth is implemented
        # The user_id column is nullable, so devices can be claimed without a user
        pass
    
    conn = None
    try:
        conn = await get_db_connection()
        input_code = req.claim_token.strip().upper()
        
        # Find device by claim token
        device = await conn.fetchrow(
            "SELECT id, hardware_id, friendly_name FROM devices WHERE claim_token = $1 AND status = 'UNCLAIMED'",
            input_code
        )
        
        if not device:
            logger.warning(f"❌ Invalid claim code: {input_code}")
            raise HTTPException(status_code=404, detail="Invalid or expired pairing code")

        # Generate API key for this device
        api_key = f"sk-{secrets.token_urlsafe(32)}"
        friendly_name = req.friendly_name or device["friendly_name"] or "Sentry Device"
        
        # Update device: set status, API key, clear claim token, assign to user
        await conn.execute(
            """
            UPDATE devices 
            SET status = 'ONLINE', 
                friendly_name = $1, 
                claim_token = NULL, 
                api_key = $2,
                user_id = $3,
                updated_at = NOW()
            WHERE id = $4
            """,
            friendly_name, api_key, user_id, device["id"]
        )
        
        logger.info(f"✅ Device {device['hardware_id']} claimed by user {user_id}")
        return {
            "success": True,
            "device_id": str(device["id"]),
            "hardware_id": device["hardware_id"],
            "api_key": api_key,
            "message": "Device claimed! Enter this API key in your Sentry portal."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Claim failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to claim device: {str(e)}")
    finally:
        if conn:
            await conn.close()

@router.get("/list")
async def list_devices(authorization: Optional[str] = Header(None)) -> List[dict]:
    """
    Returns devices for the authenticated user.
    """
    # Extract user_id from token (simplified)
    user_id = 1  # Default for now
    
    conn = None
    try:
        conn = await get_db_connection()
        
        # Get devices for this user (or all if no user filter for now)
        rows = await conn.fetch("""
            SELECT id, hardware_id, friendly_name, status, last_seen, ip_address, version 
            FROM devices 
            WHERE status != 'UNCLAIMED'
            ORDER BY last_seen DESC NULLS LAST
        """)
        
        devices = []
        for row in rows:
            device_name = row["friendly_name"] or "Unnamed Device"
            status = (row["status"] or "unknown").lower()
            
            # Check if device is stale (no heartbeat in 5 minutes)
            if row["last_seen"]:
                age = (datetime.utcnow() - row["last_seen"].replace(tzinfo=None)).total_seconds()
                if age > 300:  # 5 minutes
                    status = "offline"
            
            devices.append({
                "id": str(row["id"]),
                "hardware_id": row["hardware_id"] or "",
                "friendly_name": device_name,
                "name": device_name,
                "status": status,
                "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
                "ip_address": row["ip_address"],
                "version": row["version"] or "1.0.0"
            })
        
        logger.info(f"✅ Returning {len(devices)} devices")
        return devices
        
    except Exception as e:
        logger.error(f"❌ Device list failed: {e}")
        traceback.print_exc()
        return []
    finally:
        if conn:
            await conn.close()

@router.post("/heartbeat")
async def device_heartbeat(
    x_sentry_id: str = Header(..., alias="X-Sentry-ID"),
    x_sentry_key: str = Header(..., alias="X-Sentry-Key")
):
    """
    Periodic heartbeat from Sentry devices.
    Validates API key and updates device status.
    """
    conn = None
    try:
        conn = await get_db_connection()
        
        device = await conn.fetchrow(
            "SELECT id, api_key, status FROM devices WHERE hardware_id = $1",
            x_sentry_id
        )
        
        if not device:
            logger.warning(f"❌ Heartbeat: Unknown device {x_sentry_id}")
            raise HTTPException(status_code=404, detail="Device not found")
        
        if device["api_key"] != x_sentry_key:
            logger.warning(f"❌ Heartbeat: Invalid key for {x_sentry_id}")
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        await conn.execute(
            """
            UPDATE devices 
            SET status = 'ONLINE', last_seen = NOW(), updated_at = NOW()
            WHERE hardware_id = $1
            """,
            x_sentry_id
        )
        
        logger.info(f"💓 Heartbeat OK: {x_sentry_id}")
        return {"status": "ok", "message": "Heartbeat received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Heartbeat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()

@router.delete("/{device_id}")
async def remove_device(device_id: str, authorization: Optional[str] = Header(None)):
    """
    Remove/unpair a device from the user's account.
    """
    conn = None
    try:
        conn = await get_db_connection()
        
        # Reset device to unclaimed state with new pairing code
        new_code = generate_pairing_code()
        
        result = await conn.execute(
            """
            UPDATE devices 
            SET status = 'UNCLAIMED', 
                api_key = NULL, 
                claim_token = $1,
                user_id = NULL,
                updated_at = NOW()
            WHERE id = $2
            """,
            new_code, int(device_id)
        )
        
        logger.info(f"🗑️ Device {device_id} unpaired")
        return {"success": True, "message": "Device unpaired successfully"}
        
    except Exception as e:
        logger.error(f"❌ Remove device failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            await conn.close()
