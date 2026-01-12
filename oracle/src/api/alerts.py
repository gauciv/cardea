"""
Alerts API - Receives alerts from Sentry devices
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, timezone
import logging

try:
    from database import get_db, Alert
except ImportError:
    from src.database import get_db, Alert

router = APIRouter()
logger = logging.getLogger(__name__)

class AlertRequest(BaseModel):
    source: str
    alert_type: str
    severity: str
    title: str
    description: str
    timestamp: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None
    network_context: Optional[dict[str, Any]] = None
    indicators: Optional[list[str]] = None

class AlertResponse(BaseModel):
    success: bool
    alert_id: int
    message: str

@router.post("", response_model=AlertResponse)
async def receive_alert(req: AlertRequest):
    """
    Receive and store an alert from Sentry or external source.
    """
    logger.info(f"📥 Received alert: [{req.severity.upper()}] {req.title}")
    
    try:
        async with get_db() as db:
            alert = Alert(
                source=req.source,
                alert_type=req.alert_type,
                severity=req.severity.lower(),
                title=req.title,
                description=req.description,
                timestamp=datetime.fromisoformat(req.timestamp.replace('Z', '+00:00')) if req.timestamp else datetime.now(timezone.utc),
                raw_data=req.raw_data,
                network_context=req.network_context,
                indicators=req.indicators
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)
            
            logger.info(f"✅ Alert stored with ID: {alert.id}")
            
            return AlertResponse(
                success=True,
                alert_id=alert.id,
                message=f"Alert received and stored"
            )
            
    except Exception as e:
        logger.error(f"❌ Failed to store alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))
