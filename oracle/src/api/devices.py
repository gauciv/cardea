from fastapi import APIRouter, HTTPException, Header
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
    friendly_name: str

class DeviceResponse(BaseModel):
    id: int
    hardware_id: str
    friendly_name: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None
    ip_address: Optional[str] = None
    version: Optional[str] = "1.0.0"
    
    class Config:
        from_attributes = True

# --- ENDPOINTS ---

@router.post("/register")
async def register_device(req: DeviceRegisterRequest):
    """
    Called by Sentry device on startup.
    Generates a Claim Token if device is new.
    """
    conn = await get_db_connection()
    try:
        existing = await conn.fetchrow(
            "SELECT id, status, claim_token FROM devices WHERE hardware_id = $1", 
            req.hardware_id
        )

        if existing:
            await conn.execute(
                "UPDATE devices SET last_seen = NOW(), version = $1 WHERE hardware_id = $2",
                req.version, req.hardware_id
            )
            return {
                "status": existing["status"],
                "claim_token": existing["claim_token"] if existing["status"] == "UNCLAIMED" else None,
                "message": "Device check-in successful"
            }
        
        # Generate claim token (e.g., "AB3-9K2")
        claim_token = secrets.token_hex(3).upper()
        claim_token = f"{claim_token[:3]}-{claim_token[3:]}"
        
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
    Called by Dashboard user to link a device to their account.
    Validates claim_token from pre-registered device.
    """
    logger.info(f"📱 Claim request: code='{req.claim_token}', name='{req.friendly_name}'")
    
    conn = None
    try:
        conn = await get_db_connection()
        input_code = req.claim_token.strip().upper()
        
        # Find device by claim token
        device = await conn.fetchrow(
            "SELECT id, hardware_id FROM devices WHERE claim_token = $1 AND status = 'UNCLAIMED'",
            input_code
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Invalid or expired claim token")

        # Generate permanent API Key
        api_key = f"sk-{secrets.token_urlsafe(32)}"
        
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
        
        logger.info(f"✅ Device {device['hardware_id']} claimed successfully")
        return {
            "success": True,
            "device_id": str(device["id"]),
            "api_key": api_key,
            "message": "Device claimed successfully"
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
async def list_devices() -> List[dict]:
    """Returns all devices for the Dashboard."""
    conn = None
    try:
        conn = await get_db_connection()
        rows = await conn.fetch("""
            SELECT id, hardware_id, friendly_name, status, last_seen, ip_address, version 
            FROM devices 
            ORDER BY last_seen DESC NULLS LAST
        """)
        
        devices = []
        for row in rows:
            device_name = row["friendly_name"] or "Unnamed Device"
            devices.append({
                "id": str(row["id"]),
                "hardware_id": row["hardware_id"] or "",
                "friendly_name": device_name,
                "name": device_name,
                "status": (row["status"] or "unknown").lower(),
                "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
                "ip_address": row["ip_address"],
                "version": row["version"] or "1.0.0"
            })
        
        logger.info(f"✅ Found {len(devices)} devices")
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
    """Periodic heartbeat from authenticated Sentry devices."""
    conn = None
    try:
        conn = await get_db_connection()
        
        device = await conn.fetchrow(
            "SELECT id, api_key, status FROM devices WHERE hardware_id = $1",
            x_sentry_id
        )
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        if device["api_key"] != x_sentry_key:
            raise HTTPException(status_code=403, detail="Invalid API key")
        
        await conn.execute(
            """
            UPDATE devices 
            SET status = 'ONLINE', last_seen = NOW(), updated_at = NOW()
            WHERE hardware_id = $1
            """,
            x_sentry_id
        )
        
        return {"status": "ok", "message": "Heartbeat received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Heartbeat failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Heartbeat failed: {str(e)}")
    finally:
        if conn:
            await conn.close()
