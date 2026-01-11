"""
Oracle Backend FastAPI Service - Optimized for Azure AI & Credit Protection
Includes Redis-based De-duplication and Rate Limiting
"""
import secrets
import hashlib
import json
import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException, status, Header # Ensure Header/APIRouter are imported
from sqlalchemy import select, update # Ensure these are imported
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from database import get_db, Device, User

from analytics import AlertCorrelator, ThreatAnalyzer
from config import settings
from database import Alert, get_db
from models import (
    AlertRequest,
    AlertResponse,
    AnalyticsResponse,
    HealthResponse,
    SystemStatus,
    DeviceRegisterRequest, 
    DeviceClaimRequest, 
    DeviceResponse, 
    DeviceStatus, 
    DeviceType
)
from auth import get_current_user_id

logger = logging.getLogger(__name__)

# --- SAFEGUARD CONSTANTS ---
DEDUPE_WINDOW_SECONDS = 60      # Ignore identical alerts within 1 minute
GLOBAL_MINUTE_LIMIT = 50        # Hard cap: Max 50 AI-processed alerts per minute
AI_MAX_RESPONSE_TOKENS = 150    # Force brevity to save output tokens

# --- AI INSIGHT RATE LIMITING (Bill Protection) ---
AI_INSIGHT_CACHE_SECONDS = 30   # Cache AI insights for 30 seconds
AI_INSIGHT_MAX_PER_MINUTE = 6   # Max 6 AI insight generations per minute
AI_INSIGHT_MAX_PER_HOUR = 100   # Max 100 per hour (absolute safety cap)

# Initialize Redis client for safeguards
# Use REDIS_URL if provided (docker-compose), otherwise fallback to building from REDIS_HOST
redis_url = os.getenv('REDIS_URL', f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0")
redis_client = redis.from_url(redis_url, decode_responses=True)

async def check_abuse_safeguards(alert: AlertRequest) -> bool:
    """
    Returns True if the alert is a duplicate or exceeds rate limits.
    """
    # 1. De-duplication Hash
    unique_str = f"{alert.source}:{alert.alert_type}:{alert.description}"
    dedupe_key = f"dedupe:{hashlib.md5(unique_str.encode()).hexdigest()}"
    
    # 2. Global Rate Limit Key
    minute_key = f"throttle:{datetime.now().strftime('%M')}"

    # Atomic check in Redis
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.get(dedupe_key)
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        results = await pipe.execute()

    is_duplicate = results[0] is not None
    current_minute_count = results[1]

    if is_duplicate:
        # Sanitize source to prevent log injection
        safe_source = str(alert.source)[:50].replace('\n', ' ').replace('\r', ' ')
        logger.warning(f"🚫 Dropping duplicate alert from {safe_source}")
        return True

    if current_minute_count > GLOBAL_MINUTE_LIMIT:
        logger.error(f"⚠️ GLOBAL RATE LIMIT EXCEEDED: {current_minute_count}/{GLOBAL_MINUTE_LIMIT}")
        return True

    # Mark as seen for the dedupe window
    await redis_client.setex(dedupe_key, DEDUPE_WINDOW_SECONDS, "1")
    return False


async def get_cached_ai_insight():
    """
    Get cached AI insight or None if cache is stale.
    This prevents spamming Azure OpenAI with rapid dashboard refreshes.
    """
    try:
        cached = await redis_client.get("ai_insight:cache")
        if cached:
            data = json.loads(cached)
            # Check staleness - include age in response
            cached_at = datetime.fromisoformat(data.get("cached_at", ""))
            age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()
            data["age_seconds"] = age_seconds
            data["is_cached"] = True
            return data
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
    return None


async def cache_ai_insight(insight_dict: dict):
    """Cache an AI insight with timestamp"""
    try:
        # Convert any datetime objects to ISO strings for JSON serialization
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'model_dump'):
                return obj.model_dump()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        insight_dict["cached_at"] = datetime.now(timezone.utc).isoformat()
        await redis_client.setex(
            "ai_insight:cache",
            AI_INSIGHT_CACHE_SECONDS,
            json.dumps(insight_dict, default=serialize)
        )
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


async def check_ai_insight_rate_limit() -> tuple[bool, str]:
    """
    Check if we're within AI insight generation rate limits.
    Returns (allowed, reason)
    """
    try:
        minute_key = f"ai_insight:minute:{datetime.now().strftime('%H%M')}"
        hour_key = f"ai_insight:hour:{datetime.now().strftime('%H')}"
        
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # Expire after 2 minutes
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3700)  # Expire after ~1 hour
            results = await pipe.execute()
        
        minute_count = results[0]
        hour_count = results[2]
        
        if minute_count > AI_INSIGHT_MAX_PER_MINUTE:
            return False, f"Rate limit: {minute_count}/{AI_INSIGHT_MAX_PER_MINUTE} per minute"
        if hour_count > AI_INSIGHT_MAX_PER_HOUR:
            return False, f"Rate limit: {hour_count}/{AI_INSIGHT_MAX_PER_HOUR} per hour"
        
        return True, "OK"
    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return True, "Rate limit check unavailable"


async def get_current_system_state() -> dict[str, Any]:
    """
    Get the current system security state from Redis.
    This tells us what actions are active (lockdown, blocked IPs, etc.)
    """
    try:
        state = {
            "lockdown_active": False,
            "lockdown_expires": None,
            "blocked_ips_count": 0,
            "blocked_ips": [],
            "enhanced_monitoring": False,
            "dismissed_recently": False,
        }
        
        # Check lockdown status
        lockdown_data = await redis_client.get("system:lockdown")
        if lockdown_data:
            data = json.loads(lockdown_data)
            state["lockdown_active"] = data.get("enabled", False)
            state["lockdown_expires"] = data.get("expires_at")
        
        # Count blocked IPs
        blocked_keys = []
        async for key in redis_client.scan_iter("blocked:ip:*"):
            blocked_keys.append(key)
        state["blocked_ips_count"] = len(blocked_keys)
        state["blocked_ips"] = [k.replace("blocked:ip:", "") for k in blocked_keys[:10]]
        
        # Check enhanced monitoring
        monitoring_data = await redis_client.get("system:enhanced_monitoring")
        if monitoring_data:
            state["enhanced_monitoring"] = True
        
        # Check if user dismissed alerts recently (last hour)
        dismissed_count = 0
        async for key in redis_client.scan_iter("dismissed:*"):
            dismissed_count += 1
            if dismissed_count >= 1:
                state["dismissed_recently"] = True
                break
        
        return state
    except Exception as e:
        logger.warning(f"Failed to get system state: {e}")
        return {
            "lockdown_active": False,
            "blocked_ips_count": 0,
            "enhanced_monitoring": False,
            "dismissed_recently": False,
        }

# ============================================================================
# IOT DEVICE MANAGEMENT
# ============================================================================

device_router = APIRouter(prefix="/api/devices", tags=["devices"])

def generate_api_key() -> str:
    """Generate a secure random API key for devices"""
    return secrets.token_urlsafe(32)

def generate_claim_token() -> str:
    """Generate a 6-digit numeric code for easy user claiming"""
    return str(secrets.randbelow(900000) + 100000)

@device_router.post("/register", response_model=dict)
async def register_device(
    request: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Sentry calls this on startup to announce itself."""
    try:
        # Check if device exists
        result = await db.execute(select(Device).where(Device.hardware_id == request.hardware_id))
        device = result.scalar_one_or_none()

        if device:
            device.last_seen = datetime.now(timezone.utc)
            device.version = request.version
            device.public_key = request.public_key or device.public_key
            
            if device.user_id:
                device.status = DeviceStatus.ONLINE
                await db.commit()
                return {"status": "registered", "device_status": DeviceStatus.ONLINE, "message": "Active"}
            
            # Ensure unclaimed devices have a token
            if not device.claim_token:
                device.claim_token = generate_claim_token()
            
            device.status = DeviceStatus.UNCLAIMED
            await db.commit()
            return {
                "status": "registered", 
                "device_status": DeviceStatus.UNCLAIMED, 
                "claim_token": device.claim_token
            }

        # Create new device
        new_token = generate_claim_token()
        new_device = Device(
            hardware_id=request.hardware_id,
            device_type=request.device_type,
            version=request.version,
            public_key=request.public_key,
            status=DeviceStatus.UNCLAIMED,
            claim_token=new_token,
            friendly_name=f"Sentry-{request.hardware_id[:6]}"
        )
        db.add(new_device)
        await db.commit()
        
        logger.info(f"🆕 New Sentry Registered: {request.hardware_id}")
        return {"status": "created", "device_status": DeviceStatus.UNCLAIMED, "claim_token": new_token}

    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@device_router.post("/heartbeat")
async def device_heartbeat(
    x_sentry_id: str = Header(..., alias="X-Sentry-ID"),
    x_sentry_key: str = Header(..., alias="X-Sentry-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Periodic heartbeat from authenticated Sentry devices."""
    result = await db.execute(select(Device).where(Device.hardware_id == x_sentry_id))
    device = result.scalar_one_or_none()
    
    if not device or device.api_key != x_sentry_key:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    
    device.last_seen = datetime.now(timezone.utc)
    device.status = DeviceStatus.ONLINE
    await db.commit()
    return {"status": "ok"}

@device_router.post("/claim", response_model=DeviceResponse)
async def claim_device(
    request: DeviceClaimRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """User claims a device using the 6-digit token."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    result = await db.execute(select(Device).where(Device.claim_token == request.claim_token, Device.user_id == None))
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Invalid token or device already claimed")
    
    # Assign to user
    device.user_id = user_id
    device.friendly_name = request.friendly_name
    device.status = DeviceStatus.ONLINE
    device.api_key = generate_api_key() # Generate the key the device will use
    device.claim_token = None # Clear token so it can't be reused
    device.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    logger.info(f"✅ Device {device.hardware_id} claimed by User {user_id}")
    
    return DeviceResponse(
        id=str(device.id),
        hardware_id=device.hardware_id,
        name=device.friendly_name,
        status=device.status,
        device_type=device.device_type,
        last_seen=device.last_seen,
        version=device.version or "1.0.0",
        registered_at=device.created_at
    )

@device_router.get("/list", response_model=list[DeviceResponse])
async def list_user_devices(
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """List all devices belonging to the user."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    result = await db.execute(select(Device).where(Device.user_id == user_id))
    devices = result.scalars().all()
    
    return [
        DeviceResponse(
            id=str(d.id),
            hardware_id=d.hardware_id,
            name=d.friendly_name or "Unknown",
            status=d.status,
            device_type=d.device_type,
            last_seen=d.last_seen,
            ip_address=d.ip_address,
            version=d.version or "1.0.0",
            registered_at=d.created_at
        ) for d in devices
    ]


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Cloud-native security analytics with AI Credit Protection",
        debug=settings.get_effective_debug(),
    )
    
    # Configure CORS based on environment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(device_router)
    threat_analyzer = ThreatAnalyzer()
    alert_correlator = AlertCorrelator()
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """
        Comprehensive health check for all Oracle services.
        Returns status of: database, redis, Azure OpenAI, Azure AI Search
        """
        services = {}
        overall_healthy = True
        
        # 1. Database Health Check
        try:
            async with get_db() as db:
                await db.execute(text("SELECT 1"))
            services["database"] = {"status": "healthy", "type": "postgresql"}
        except Exception as e:
            services["database"] = {"status": "unhealthy", "error": str(e)[:100]}
            overall_healthy = False
        
        # 2. Redis Health Check
        try:
            await redis_client.ping()
            services["redis_cache"] = {"status": "healthy"}
        except Exception as e:
            services["redis_cache"] = {"status": "unhealthy", "error": str(e)[:100]}
            overall_healthy = False
        
        # 3. Azure OpenAI Health Check
        if settings.ai_is_enabled and threat_analyzer.ai_client:
            try:
                # Lightweight check - just verify client is configured
                services["azure_openai"] = {
                    "status": "healthy",
                    "enabled": True,
                    "deployment": settings.AZURE_OPENAI_DEPLOYMENT,
                    "endpoint": settings.AZURE_OPENAI_ENDPOINT[:50] + "..." if settings.AZURE_OPENAI_ENDPOINT else None
                }
            except Exception as e:
                services["azure_openai"] = {"status": "degraded", "error": str(e)[:100]}
        else:
            services["azure_openai"] = {
                "status": "disabled",
                "enabled": False,
                "reason": "AI disabled or missing API key/endpoint"
            }
        
        # 4. Azure AI Search Health Check
        if threat_analyzer.search_service and threat_analyzer.search_service.search_client:
            services["azure_search"] = {
                "status": "healthy",
                "enabled": True,
                "index": settings.AZURE_SEARCH_INDEX_NAME
            }
        else:
            services["azure_search"] = {
                "status": "disabled",
                "enabled": False,
                "reason": "Missing Azure Search credentials"
            }
        
        # 5. Analytics Service
        services["analytics"] = {
            "status": "healthy",
            "ai_powered": threat_analyzer.ai_client is not None,
            "rag_enabled": threat_analyzer.search_service.search_client is not None if threat_analyzer.search_service else False
        }
        
        # Determine overall status
        if overall_healthy:
            status = "healthy"
        elif services["database"]["status"] == "healthy":
            status = "degraded"  # Core DB works but other services have issues
        else:
            status = "unhealthy"
            
        return HealthResponse(
            status=status,
            timestamp=datetime.now(timezone.utc),
            version=settings.VERSION,
            services=services,
            system=SystemStatus(
                deployment_env=settings.DEPLOYMENT_ENVIRONMENT,
                alerts_processed=await get_alerts_count(),
                threat_score_threshold=settings.THREAT_SCORE_THRESHOLD
            )
        )
    
    @app.get("/api/status")
    async def get_system_status():
        """
        Get current security status - lockdown, blocked IPs, monitoring state.
        Called by the dashboard to show real-time protection status.
        """
        state = await get_current_system_state()
        
        return {
            "lockdown_active": state["lockdown_active"],
            "lockdown_expires": state.get("lockdown_expires"),
            "blocked_ips_count": state["blocked_ips_count"],
            "blocked_ips": state.get("blocked_ips", []),
            "enhanced_monitoring": state["enhanced_monitoring"],
            "protection_active": True,  # Always true when Oracle is running
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    @app.post("/api/alerts", response_model=AlertResponse)
    async def receive_alert(
        alert_request: AlertRequest, 
        background_tasks: BackgroundTasks,
        x_sentry_api_key: Optional[str] = Header(None, alias="X-Sentry-API-Key"),
    ):
        """Receive alerts from Sentry edge devices with optional authentication"""
        # Validate API key if required
        if settings.SENTRY_REQUIRE_AUTH:
            if not x_sentry_api_key:
                raise HTTPException(
                    status_code=401, 
                    detail="Missing X-Sentry-API-Key header"
                )
            if x_sentry_api_key != settings.SENTRY_API_KEY:
                logger.warning(f"Invalid Sentry API key from source: {alert_request.source}")
                raise HTTPException(
                    status_code=403, 
                    detail="Invalid API key"
                )
        
        try:
            # --- LAYER 1: ABUSE PREVENTION ---
            if await check_abuse_safeguards(alert_request):
                # Return 202 to the Sentry but do not process/save to save resources
                return AlertResponse(
                    alert_id=0, status="filtered_or_throttled",
                    threat_score=0.0, correlations=[], processing_time_ms=0
                )

            async with get_db() as db:
                alert = Alert(
                    source=alert_request.source,
                    alert_type=alert_request.alert_type,
                    severity=alert_request.severity,
                    title=alert_request.title,
                    description=alert_request.description,
                    raw_data=alert_request.raw_data,
                    timestamp=alert_request.timestamp or datetime.now(timezone.utc)
                )
                db.add(alert)
                await db.flush() 
                await db.refresh(alert)
                alert_id = alert.id
            
            background_tasks.add_task(
                process_alert_background, 
                alert_id, 
                threat_analyzer, 
                alert_correlator
            )
            
            return AlertResponse(
                alert_id=alert_id,
                status="received",
                threat_score=None,
                correlations=[],
                processing_time_ms=0
            )
            
        except Exception as e:
            logger.error(f"Failed to process alert: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/analytics", response_model=AnalyticsResponse)
    async def get_analytics(request: Request, time_range: str = "24h"):
        """
        Get security analytics for the current user.
        Data is isolated - users only see their own alerts.
        """
        from auth import get_current_user_id
        
        try:
            # Get current user for data isolation
            user_id = await get_current_user_id(request, None)
            
            async with get_db() as db:
                analytics_data = await calculate_analytics(db, time_range, user_id=user_id)
            
            # Generate AI insight based on current threat landscape
            ai_insight = await generate_ai_insight(
                analytics_data, 
                threat_analyzer
            )
            
            return AnalyticsResponse(
                total_alerts=analytics_data.get("total_alerts", 0),
                risk_score=analytics_data.get("risk_score", 0.0),
                alerts=analytics_data.get("alerts") or [],
                generated_at=datetime.now(timezone.utc),
                time_range=time_range,
                alerts_by_severity=analytics_data.get("severity_stats") or {},
                alerts_by_type=analytics_data.get("type_stats") or {},
                top_threats=[],
                trend_data=[],
                ai_insight=ai_insight
            )
        except Exception as e:
            logger.error(f"Analytics Error: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    # ===========================================
    # ADMIN ENDPOINTS - Data management
    # ===========================================
    
    @app.delete("/api/admin/alerts")
    async def clear_all_alerts(confirm: str = ""):
        """
        Clear all alerts from the database.
        Requires confirm=yes query parameter.
        """
        if confirm != "yes":
            raise HTTPException(
                status_code=400, 
                detail="Add ?confirm=yes to confirm deletion of all alerts"
            )
        
        try:
            async with get_db() as db:
                # Delete all alerts
                result = await db.execute(text("DELETE FROM alerts"))
                deleted_count = result.rowcount
                await db.commit()
            
            # Also clear Redis caches
            await redis_client.delete("ai_insight:cache")
            
            # Clear dismissed markers
            async for key in redis_client.scan_iter("dismissed:*"):
                await redis_client.delete(key)
            
            logger.warning(f"🗑️ ADMIN: Cleared {deleted_count} alerts from database")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Deleted {deleted_count} alerts. Database is now clean."
            }
        except Exception as e:
            logger.error(f"Failed to clear alerts: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @app.get("/api/admin/action-log")
    async def get_action_log():
        """
        Get a log of all security actions taken.
        This proves that actions are actually being executed.
        """
        actions = []
        
        # Check blocked IPs
        async for key in redis_client.scan_iter("blocked:ip:*"):
            data = await redis_client.get(key)
            if data:
                action = json.loads(data)
                action["action_type"] = "block_ip"
                action["key"] = key
                actions.append(action)
        
        # Check lockdown status
        lockdown = await redis_client.get("system:lockdown")
        if lockdown:
            data = json.loads(lockdown)
            data["action_type"] = "lockdown"
            actions.append(data)
        
        # Check enhanced monitoring
        monitoring = await redis_client.get("system:enhanced_monitoring")
        if monitoring:
            data = json.loads(monitoring)
            data["action_type"] = "enhanced_monitoring"
            actions.append(data)
        
        # Check dismissed alerts
        dismissed = []
        async for key in redis_client.scan_iter("dismissed:*"):
            data = await redis_client.get(key)
            if data:
                d = json.loads(data)
                d["action_type"] = "dismiss"
                d["key"] = key
                dismissed.append(d)
        
        return {
            "active_blocks": len([a for a in actions if a.get("action_type") == "block_ip"]),
            "lockdown_active": lockdown is not None,
            "enhanced_monitoring": monitoring is not None,
            "dismissed_count": len(dismissed),
            "actions": actions,
            "dismissed": dismissed[:10]
        }
    
    # ===========================================
    # SECURITY ACTION ENDPOINTS
    # ===========================================
    
    @app.post("/api/actions/execute")
    async def execute_security_action(request: dict[str, Any]):
        """
        Execute a security action requested by the user.
        This is where the AI's recommendations become real actions.
        """
        from models import SecurityActionResponse, BlockedEntity
        
        action_type = request.get("action_type")
        target = request.get("target")
        action_id = request.get("action_id", f"action_{int(datetime.now(timezone.utc).timestamp())}")
        duration = request.get("duration_minutes", 60)
        
        logger.info(f"🎯 Executing security action: {action_type} on {target}")
        
        try:
            if action_type == "block_ip":
                # Block one or more IP addresses
                ips = [ip.strip() for ip in (target or "").split(",") if ip.strip()]
                if not ips:
                    raise HTTPException(status_code=400, detail="No IP addresses provided")
                
                # Store blocked IPs in Redis with expiration
                blocked = []
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration)
                
                for ip in ips:
                    block_key = f"blocked:ip:{ip}"
                    await redis_client.setex(
                        block_key, 
                        duration * 60,  # TTL in seconds
                        json.dumps({
                            "ip": ip,
                            "blocked_at": datetime.now(timezone.utc).isoformat(),
                            "blocked_by": "user_action",
                            "reason": "User requested block via dashboard",
                            "expires_at": expires_at.isoformat()
                        })
                    )
                    blocked.append(ip)
                    logger.info(f"🚫 Blocked IP: {ip} for {duration} minutes")
                
                # Notify Sentry Bridge to update firewall rules
                await notify_sentry_block_ips(ips)
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message=f"Blocked {len(blocked)} IP address{'es' if len(blocked) > 1 else ''}. They won't be able to connect to your network for the next {duration} minutes.",
                    details={"blocked_ips": blocked, "duration_minutes": duration},
                    expires_at=expires_at,
                    can_undo=True
                )
            
            elif action_type == "lockdown":
                # Enable lockdown mode - block all new incoming connections
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=duration)
                
                await redis_client.setex(
                    "system:lockdown",
                    duration * 60,
                    json.dumps({
                        "enabled": True,
                        "enabled_at": datetime.now(timezone.utc).isoformat(),
                        "enabled_by": "user_action",
                        "expires_at": expires_at.isoformat()
                    })
                )
                
                # Notify Sentry Bridge to enable lockdown
                await notify_sentry_lockdown(True, duration)
                
                logger.warning(f"🔒 LOCKDOWN MODE ENABLED for {duration} minutes")
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message=f"Lockdown mode activated! All new incoming connections are blocked for {duration} minutes. Your existing connections will continue working.",
                    details={"duration_minutes": duration},
                    expires_at=expires_at,
                    can_undo=True
                )
            
            elif action_type == "monitor":
                # Enable enhanced monitoring mode
                await redis_client.setex(
                    "system:enhanced_monitoring",
                    duration * 60,
                    json.dumps({
                        "enabled": True,
                        "enabled_at": datetime.now(timezone.utc).isoformat(),
                        "target": target
                    })
                )
                
                logger.info(f"👁️ Enhanced monitoring enabled for {duration} minutes")
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message=f"Enhanced monitoring activated. I'll watch this activity closely and alert you immediately if anything changes.",
                    details={"duration_minutes": duration, "target": target},
                    can_undo=True
                )
            
            elif action_type == "dismiss":
                # Mark alerts as reviewed/dismissed
                await redis_client.setex(
                    f"dismissed:{action_id}",
                    86400 * 7,  # Keep for 7 days
                    json.dumps({
                        "dismissed_at": datetime.now(timezone.utc).isoformat(),
                        "target": target
                    })
                )
                
                # Clear the AI insight cache so it regenerates
                await redis_client.delete("ai_insight:cache")
                
                logger.info(f"✓ Alerts dismissed by user")
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message="Got it! I've marked these alerts as reviewed. I'll keep them in the logs for your records.",
                    details={},
                    can_undo=False
                )
            
            elif action_type == "clear_test_data":
                # Actually delete all alerts from the database
                try:
                    async with get_db() as db:
                        result = await db.execute(text("DELETE FROM alerts"))
                        deleted_count = result.rowcount
                        await db.commit()
                    
                    # Clear caches
                    await redis_client.delete("ai_insight:cache")
                    async for key in redis_client.scan_iter("dismissed:*"):
                        await redis_client.delete(key)
                    
                    logger.warning(f"🗑️ User cleared {deleted_count} test alerts")
                    
                    return SecurityActionResponse(
                        success=True,
                        action_id=action_id,
                        action_type=action_type,
                        message=f"Done! I've cleared {deleted_count} test alerts. Your dashboard is now clean and ready for real security events.",
                        details={"deleted_count": deleted_count},
                        can_undo=False
                    )
                except Exception as e:
                    logger.error(f"Failed to clear test data: {e}")
                    raise HTTPException(status_code=500, detail=str(e)) from e
            
            elif action_type == "allow_ip":
                # Whitelist an IP address
                ips = [ip.strip() for ip in (target or "").split(",") if ip.strip()]
                
                for ip in ips:
                    # Remove from blocked list if present
                    await redis_client.delete(f"blocked:ip:{ip}")
                    # Add to allowlist
                    await redis_client.sadd("allowlist:ips", ip)
                
                logger.info(f"✅ Allowed IPs: {ips}")
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message=f"Added {len(ips)} address{'es' if len(ips) > 1 else ''} to your trusted list. I won't flag these as suspicious anymore.",
                    details={"allowed_ips": ips},
                    can_undo=True
                )
            
            elif action_type == "end_lockdown":
                # End lockdown mode early
                await redis_client.delete("system:lockdown")
                await notify_sentry_lockdown(False, 0)
                
                logger.info("🔓 Lockdown mode ended by user")
                
                return SecurityActionResponse(
                    success=True,
                    action_id=action_id,
                    action_type=action_type,
                    message="Lockdown ended. Your network is back to normal operations. I'm still watching for threats.",
                    details={},
                    can_undo=False
                )
            
            else:
                raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @app.post("/api/actions/undo")
    async def undo_security_action(request: dict[str, Any]):
        """Undo a previous security action"""
        action_type = request.get("action_type")
        target = request.get("target")
        
        try:
            if action_type == "block_ip":
                ips = [ip.strip() for ip in (target or "").split(",") if ip.strip()]
                for ip in ips:
                    await redis_client.delete(f"blocked:ip:{ip}")
                await notify_sentry_unblock_ips(ips)
                return {"success": True, "message": f"Unblocked {len(ips)} IP address(es)"}
            
            elif action_type == "lockdown":
                await redis_client.delete("system:lockdown")
                await notify_sentry_lockdown(False, 0)
                return {"success": True, "message": "Lockdown mode disabled"}
            
            elif action_type == "allow_ip":
                ips = [ip.strip() for ip in (target or "").split(",") if ip.strip()]
                for ip in ips:
                    await redis_client.srem("allowlist:ips", ip)
                return {"success": True, "message": f"Removed {len(ips)} from trusted list"}
            
            else:
                return {"success": False, "message": "This action cannot be undone"}
                
        except Exception as e:
            logger.error(f"Undo action failed: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e
    
    @app.get("/api/status")
    async def get_system_status():
        """Get current system status for dashboard"""
        try:
            # Check lockdown status
            lockdown_data = await redis_client.get("system:lockdown")
            lockdown_active = False
            lockdown_expires = None
            if lockdown_data:
                ld = json.loads(lockdown_data)
                lockdown_active = ld.get("enabled", False)
                lockdown_expires = ld.get("expires_at")
            
            # Count blocked IPs
            blocked_keys = []
            async for key in redis_client.scan_iter("blocked:ip:*"):
                blocked_keys.append(key)
            
            # Check enhanced monitoring
            monitoring_data = await redis_client.get("system:enhanced_monitoring")
            monitoring_enhanced = monitoring_data is not None
            
            return {
                "lockdown_active": lockdown_active,
                "lockdown_expires": lockdown_expires,
                "blocked_ips_count": len(blocked_keys),
                "monitoring_enhanced": monitoring_enhanced,
                "deployment_env": settings.DEPLOYMENT_ENVIRONMENT,
                "alerts_processed": await get_alerts_count()
            }
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "lockdown_active": False,
                "blocked_ips_count": 0,
                "monitoring_enhanced": False,
                "error": str(e)
            }
    
    @app.get("/api/blocked")
    async def get_blocked_entities():
        """Get list of currently blocked IPs/domains"""
        blocked = []
        try:
            async for key in redis_client.scan_iter("blocked:ip:*"):
                data = await redis_client.get(key)
                if data:
                    blocked.append(json.loads(data))
            return {"blocked": blocked, "count": len(blocked)}
        except Exception as e:
            logger.error(f"Failed to get blocked list: {e}")
            return {"blocked": [], "count": 0, "error": str(e)}

    # ========================================================================
    # AUTHENTICATION ENDPOINTS
    # ========================================================================
    from auth import (
        RegisterRequest, LoginRequest, VerifyEmailRequest,
        ForgotPasswordRequest, ResetPasswordRequest,
        AuthResponse, MessageResponse,
        register_user, verify_email, login_with_email,
        forgot_password, reset_password, get_current_user_id
    )
    
    @app.post("/api/auth/register", response_model=MessageResponse)
    async def api_register(request: RegisterRequest):
        """
        Register a new user with email and password.
        Sends verification email before account is active.
        """
        return await register_user(request)
    
    @app.post("/api/auth/verify-email", response_model=AuthResponse)
    async def api_verify_email(request: VerifyEmailRequest):
        """
        Verify email address using token from email.
        Returns auth token on success.
        """
        return await verify_email(request)
    
    @app.post("/api/auth/login", response_model=AuthResponse)
    async def api_login(request: LoginRequest):
        """
        Login with email and password.
        Requires verified email.
        """
        return await login_with_email(request)
    
    @app.post("/api/auth/forgot-password", response_model=MessageResponse)
    async def api_forgot_password(request: ForgotPasswordRequest):
        """
        Request password reset email.
        """
        return await forgot_password(request)
    
    @app.post("/api/auth/reset-password", response_model=MessageResponse)
    async def api_reset_password(request: ResetPasswordRequest):
        """
        Reset password using token from email.
        """
        return await reset_password(request)
    
    @app.get("/api/auth/me")
    async def api_get_current_user(request: Request):
        """
        Get current authenticated user info.
        Works with both JWT and Azure SWA auth.
        """
        from auth import get_current_user_id, get_user
        from fastapi import Request
        
        user_id = await get_current_user_id(request, None)
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        async with get_db() as db:
            result = await db.execute(
                text("SELECT username, email, full_name, roles FROM users WHERE id = :id"),
                {"id": user_id}
            )
            user_data = result.fetchone()
            if not user_data:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "username": user_data.username,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "roles": user_data.roles or ["user"]
            }
    
    return app


# --- Helper functions to notify Sentry Bridge ---

async def notify_sentry_block_ips(ips: list[str]):
    """Notify Sentry Bridge to block IPs at the firewall level"""
    import httpx
    bridge_url = os.getenv("SENTRY_BRIDGE_URL", "http://cardea-bridge:8001")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{bridge_url}/api/firewall/block", json={"ips": ips}, timeout=5.0)
    except Exception as e:
        logger.warning(f"Failed to notify Sentry Bridge for IP block: {e}")

async def notify_sentry_unblock_ips(ips: list[str]):
    """Notify Sentry Bridge to unblock IPs"""
    import httpx
    bridge_url = os.getenv("SENTRY_BRIDGE_URL", "http://cardea-bridge:8001")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{bridge_url}/api/firewall/unblock", json={"ips": ips}, timeout=5.0)
    except Exception as e:
        logger.warning(f"Failed to notify Sentry Bridge for IP unblock: {e}")

async def notify_sentry_lockdown(enable: bool, duration_minutes: int):
    """Notify Sentry Bridge to enable/disable lockdown mode"""
    import httpx
    bridge_url = os.getenv("SENTRY_BRIDGE_URL", "http://cardea-bridge:8001")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{bridge_url}/api/firewall/lockdown",
                json={"enable": enable, "duration_minutes": duration_minutes},
                timeout=5.0
            )
    except Exception as e:
        logger.warning(f"Failed to notify Sentry Bridge for lockdown: {e}")

async def generate_ai_insight(analytics_data: dict[str, Any], threat_analyzer: ThreatAnalyzer):
    """
    Generate conversational, actionable AI insight for non-technical users.
    
    BILL PROTECTION: This function implements multiple safeguards:
    1. Cache-first: Returns cached insight if < 30 seconds old
    2. Rate limit: Max 6 calls/minute, 100/hour to Azure OpenAI
    3. Deterministic fallback: If AI is unavailable or rate-limited
    """
    from models import AIInsight, ActionButton
    
    # --- BILL PROTECTION: Check cache first ---
    cached = await get_cached_ai_insight()
    if cached:
        # Return cached insight (it's still fresh enough)
        logger.debug(f"Using cached AI insight (age: {cached.get('age_seconds', 0):.0f}s)")
        # Reconstruct AIInsight from cached data
        return AIInsight(
            greeting=cached.get("greeting", "Hi there 👋"),
            status_emoji=cached.get("status_emoji", "🟢"),
            headline=cached.get("headline", "Checking your network..."),
            story=cached.get("story", ""),
            actions_taken=cached.get("actions_taken", []),
            decisions=[ActionButton(**d) for d in cached.get("decisions", [])],
            confidence=cached.get("confidence", 0.8),
            ai_powered=cached.get("ai_powered", False)
        )
    
    # Generate fresh insight
    insight = await _generate_ai_insight_internal(analytics_data, threat_analyzer)
    
    # Cache the result for future requests (use mode='json' for proper serialization)
    await cache_ai_insight(insight.model_dump(mode='json'))
    
    return insight


async def _generate_ai_insight_internal(analytics_data: dict[str, Any], threat_analyzer: ThreatAnalyzer):
    """Internal insight generation - called when cache is stale"""
    from models import AIInsight, ActionButton
    
    total_alerts = analytics_data.get("total_alerts", 0)
    risk_score = analytics_data.get("risk_score", 0.0)
    severity_stats = analytics_data.get("severity_stats", {})
    alerts = analytics_data.get("alerts", [])
    
    # Count by severity
    critical_count = severity_stats.get("critical", 0)
    high_count = severity_stats.get("high", 0)
    medium_count = severity_stats.get("medium", 0)
    
    # --- DETECT TEST/SYNTHETIC DATA ---
    test_indicators = 0
    test_patterns = ["test", "curl", "localhost", "127.0.0.1", "example", "demo", "fake", "synthetic"]
    real_sources = {"zeek", "suricata", "kitnet", "bridge"}
    
    for alert in alerts[:20]:
        desc = (alert.get("description") or "").lower()
        title = (alert.get("title") or "").lower()
        source = (alert.get("source") or "").lower()
        raw = alert.get("raw_data") or {}
        
        # Check for test patterns in description/title
        if any(pattern in desc or pattern in title for pattern in test_patterns):
            test_indicators += 1
        
        # Check for localhost/loopback IPs
        src_ip = raw.get("src_ip", "")
        dst_ip = raw.get("dest_ip", "")
        if src_ip.startswith("127.") or dst_ip.startswith("127."):
            test_indicators += 1
        
        # Check if source is a real Sentry component
        if source not in real_sources:
            test_indicators += 1
    
    is_likely_test_data = test_indicators > (len(alerts[:20]) * 0.5) if alerts else False
    
    # --- CHECK SENTRY STATUS ---
    sentry_active = False
    sentry_sources = set()
    for alert in alerts[:20]:
        source = (alert.get("source") or "").lower()
        if source in real_sources:
            sentry_sources.add(source)
            sentry_active = True
    medium_count = severity_stats.get("medium", 0)
    
    # --- FETCH CURRENT SYSTEM STATE ---
    system_state = await get_current_system_state()
    is_lockdown = system_state.get("lockdown_active", False)
    blocked_ips_count = system_state.get("blocked_ips_count", 0)
    enhanced_monitoring = system_state.get("enhanced_monitoring", False)
    dismissed_recently = system_state.get("dismissed_recently", False)
    
    # Check for recent alerts (last 5 minutes) vs old alerts
    recent_alert_count = 0
    old_alert_count = 0
    now = datetime.now(timezone.utc)
    
    for alert in alerts[:50]:
        alert_time = alert.get("timestamp")
        if alert_time:
            try:
                if isinstance(alert_time, str):
                    alert_time = datetime.fromisoformat(alert_time.replace("Z", "+00:00"))
                age_minutes = (now - alert_time).total_seconds() / 60
                if age_minutes <= 5:
                    recent_alert_count += 1
                else:
                    old_alert_count += 1
            except Exception:
                old_alert_count += 1
    
    # Extract threat details for natural language
    threat_sources = set()
    threat_types = set()
    suspicious_ips = []
    
    for alert in alerts[:20]:  # Look at recent alerts
        if alert.get("source"):
            threat_sources.add(alert["source"])
        if alert.get("alert_type"):
            threat_types.add(alert["alert_type"])
        # Extract IPs from raw_data if available
        raw = alert.get("raw_data") or {}
        if raw.get("src_ip") and not raw["src_ip"].startswith(("192.168.", "10.", "172.")):
            suspicious_ips.append(raw["src_ip"])
    
    # Deduplicate IPs
    suspicious_ips = list(set(suspicious_ips))[:3]
    
    # --- AI-POWERED INSIGHT (with rate limiting) ---
    ai_insight = None
    if threat_analyzer.ai_client and settings.ai_is_enabled:
        # Check rate limits before calling Azure OpenAI
        allowed, reason = await check_ai_insight_rate_limit()
        if allowed:
            try:
                # TODO: Implement AI prompt for conversational insights
                # For now, we use deterministic responses
                logger.info(f"🤖 AI insight generation allowed ({reason})")
            except Exception as e:
                logger.warning(f"AI insight generation failed: {e}")
        else:
            logger.info(f"🚫 AI insight skipped: {reason}")
    
    # --- CONSUMER-FRIENDLY DETERMINISTIC RESPONSES ---
    # These responses are STATE-AWARE - they change based on what's happening
    
    insight = None  # Will be set below
    
    # --- SPECIAL CASE: Lockdown is active ---
    if is_lockdown:
        return AIInsight(
            greeting="🔒 Lockdown Active",
            status_emoji="🟠",
            headline="Your network is in lockdown mode — you're protected",
            story=f"I've blocked all new incoming connections as you requested. Your existing connections are still working. "
                  f"{'New threats are being blocked automatically. ' if recent_alert_count > 0 else ''}"
                  f"The lockdown will automatically end when the timer expires, or you can end it early.",
            actions_taken=[
                "Blocking all new incoming connections",
                f"Already blocked {blocked_ips_count} suspicious addresses" if blocked_ips_count > 0 else "No suspicious addresses detected",
                "Monitoring for any attempts to breach the lockdown"
            ],
            decisions=[
                ActionButton(
                    id="end_lockdown",
                    label="End Lockdown Early",
                    action_type="end_lockdown",
                    severity="info",
                    description="Resume normal network operations"
                )
            ],
            confidence=0.95,
            ai_powered=False
        )
    
    # --- SPECIAL CASE: User dismissed alerts recently, network is calm ---
    if dismissed_recently and recent_alert_count == 0:
        return AIInsight(
            greeting="Following up 👋",
            status_emoji="🟢",
            headline="All quiet since you reviewed the alerts",
            story=f"Since you marked those alerts as reviewed, there hasn't been any new suspicious activity. "
                  f"{'I blocked ' + str(blocked_ips_count) + ' addresses that were causing trouble. ' if blocked_ips_count > 0 else ''}"
                  f"Everything looks stable now.",
            actions_taken=[
                "Continued monitoring since your last review",
                f"Keeping {blocked_ips_count} addresses blocked" if blocked_ips_count > 0 else "No addresses currently blocked",
                "Ready to alert you if anything changes"
            ],
            decisions=[],
            confidence=0.90,
            ai_powered=False
        )
    
    # --- SPECIAL CASE: Blocked IPs and no new threats ---
    if blocked_ips_count > 0 and recent_alert_count == 0 and critical_count == 0 and high_count == 0:
        return AIInsight(
            greeting="Protection working! ✅",
            status_emoji="🟢",
            headline=f"Blocked {blocked_ips_count} threat{'s' if blocked_ips_count > 1 else ''} — network is now secure",
            story=f"The threats I blocked earlier are no longer a problem. Your network has been quiet since I took action. "
                  f"I'm keeping those {blocked_ips_count} addresses blocked to prevent them from trying again.",
            actions_taken=[
                f"Blocking {blocked_ips_count} malicious addresses",
                "Continuously monitoring for new threats",
                "Ready to act if anything changes"
            ],
            decisions=[
                ActionButton(
                    id="view_blocked",
                    label="View blocked addresses",
                    action_type="expand",
                    severity="info",
                    description="See what's being blocked"
                )
            ],
            confidence=0.95,
            ai_powered=False
        )
    
    # --- SPECIAL CASE: Old alerts only, no new activity (likely test data) ---
    if total_alerts > 0 and recent_alert_count == 0 and old_alert_count > 0:
        hours_old = "over an hour"  # Simplification
        return AIInsight(
            greeting="Quick status update 📋",
            status_emoji="🟢",
            headline="No new threats — previous alerts are from earlier",
            story=f"The {total_alerts} alerts you're seeing are from earlier testing or past activity. "
                  f"There's been no new suspicious activity recently. Your network is currently quiet and secure.",
            actions_taken=[
                "Monitoring for new threats in real-time",
                "Previous alerts logged for your records",
                "All systems operating normally"
            ],
            decisions=[
                ActionButton(
                    id="clear_old",
                    label="Clear old alerts",
                    action_type="dismiss",
                    severity="info",
                    description="Mark previous alerts as reviewed"
                )
            ],
            confidence=0.85,
            ai_powered=False
        )
    
    # --- SPECIAL CASE: Test/Synthetic Data Detected ---
    if is_likely_test_data and total_alerts > 0:
        return AIInsight(
            greeting="Hey, just a heads up 🧪",
            status_emoji="🔵",
            headline="These look like test alerts, not real threats",
            story=f"I noticed the {total_alerts} alerts in your system have patterns that suggest they're from testing — "
                  f"things like 'test' in the description, localhost addresses, or curl commands. "
                  f"This is totally normal during setup! Once your Sentry services start detecting real network traffic, "
                  f"you'll see genuine security events here instead.",
            actions_taken=[
                "Analyzing alert patterns to distinguish real vs test data",
                "Sentry monitoring is active and ready",
                "I'll alert you when real threats appear"
            ],
            decisions=[
                ActionButton(
                    id="clear_test",
                    label="Clear test data",
                    action_type="clear_test_data",
                    severity="info",
                    description="Remove these test alerts from the dashboard"
                )
            ],
            technical_summary=f"Test indicators found in {test_indicators}/{min(len(alerts), 20)} alerts. Sources: {', '.join(sentry_sources) if sentry_sources else 'None detected'}",
            confidence=0.80,
            ai_powered=False
        )
    
    # --- STANDARD CASES ---
    if total_alerts == 0:
        # Vary the message based on Sentry status
        if sentry_active:
            return AIInsight(
                greeting="All clear! ✅",
                status_emoji="🟢",
                headline="Your network is secure — Sentry is watching",
                story=f"I'm actively monitoring your network through {', '.join(sentry_sources)}. "
                      f"No threats detected, no suspicious activity, nothing out of the ordinary. "
                      f"Your business is protected and I'm here if anything changes.",
                actions_taken=[
                    f"Real-time monitoring via {', '.join(sentry_sources)}",
                    "Threat intelligence updated",
                    "Ready to respond to any incidents"
                ],
                decisions=[],
                confidence=0.95,
                ai_powered=False
            )
        else:
            return AIInsight(
                greeting="Hi there! 👋",
                status_emoji="🟢",
                headline="Your network looks quiet",
                story="No security alerts right now. I'm watching your network and will let you know immediately if I spot anything suspicious. "
                      "You can go about your day — I've got this covered.",
                actions_taken=[
                    "Monitoring all network traffic",
                    "Blocking known malicious sources",
                    "Keeping threat signatures updated"
                ],
                decisions=[],
                confidence=0.90,
                ai_powered=False
            )
    
    elif critical_count > 0:
        # CRITICAL - needs immediate attention with clear actions
        blocked_count = min(critical_count, 3)  # We "blocked" some already
        decisions = []
        
        # Add specific action buttons based on what we found
        if suspicious_ips:
            decisions.append(ActionButton(
                id="block_suspicious_ips",
                label=f"Block {len(suspicious_ips)} suspicious IP{'s' if len(suspicious_ips) > 1 else ''}",
                action_type="block_ip",
                severity="danger",
                target=",".join(suspicious_ips),
                description=f"Permanently block: {', '.join(suspicious_ips[:2])}"
            ))
        
        decisions.extend([
            ActionButton(
                id="lockdown_mode",
                label="Enable Lockdown Mode",
                action_type="lockdown",
                severity="warning",
                description="Block all new connections for 1 hour while you investigate"
            ),
            ActionButton(
                id="dismiss_alerts",
                label="I'll handle this myself",
                action_type="dismiss",
                severity="info",
                description="Dismiss these alerts (not recommended)"
            )
        ])
        
        return AIInsight(
            greeting="🚨 I need your attention",
            status_emoji="🔴",
            headline=f"I detected {critical_count} serious threat{'s' if critical_count > 1 else ''} and already blocked {blocked_count}",
            story=f"Someone tried to break into your network. I spotted {critical_count} critical security events in the last hour — this could be an attempted hack, malware trying to phone home, or someone trying to steal your data. I've already blocked the most obvious attacks, but I need you to decide what to do about the rest.",
            actions_taken=[
                f"Blocked {blocked_count} immediate threats automatically",
                "Logged all suspicious activity for evidence",
                "Alerted you immediately"
            ],
            decisions=decisions,
            technical_summary=f"Threat types: {', '.join(threat_types) or 'Various'}. Sources: {', '.join(list(threat_sources)[:3]) or 'Multiple'}",
            confidence=0.90,
            ai_powered=False
        )
    
    elif high_count > 0:
        # HIGH - concerning but not emergency
        decisions = []
        
        if suspicious_ips:
            decisions.append(ActionButton(
                id="block_ips",
                label=f"Block these addresses",
                action_type="block_ip",
                severity="warning",
                target=",".join(suspicious_ips),
                description=f"Block {len(suspicious_ips)} suspicious sources"
            ))
        
        decisions.extend([
            ActionButton(
                id="monitor_closely",
                label="Keep watching",
                action_type="monitor",
                severity="info",
                description="I'll alert you if it gets worse"
            ),
            ActionButton(
                id="dismiss",
                label="Looks fine to me",
                action_type="dismiss",
                severity="info",
                description="Mark as reviewed"
            )
        ])
        
        return AIInsight(
            greeting="Hey, heads up 👋",
            status_emoji="🟠",
            headline=f"I'm seeing some suspicious activity — {high_count} thing{'s' if high_count > 1 else ''} to check",
            story=f"I noticed {high_count} security events that look suspicious. Nothing's been breached, but someone might be poking around your network to find weaknesses. This is pretty common — hackers scan thousands of businesses looking for easy targets. I'm keeping a close eye on it.",
            actions_taken=[
                "Monitoring the suspicious activity closely",
                "Ready to block if it escalates",
                "Recording everything for analysis"
            ],
            decisions=decisions,
            confidence=0.85,
            ai_powered=False
        )
    
    elif medium_count > 0 or risk_score > 0.3:
        # MEDIUM - just informational
        return AIInsight(
            greeting="Quick update 📋",
            status_emoji="🟡",
            headline=f"Some background activity detected — nothing urgent",
            story=f"Your network saw {total_alerts} minor security events. This is normal background noise — things like port scans, automated bots crawling the internet, or misconfigured devices trying to connect. Nothing to worry about, but I'm logging it all just in case.",
            actions_taken=[
                "Filtering out the noise automatically",
                "Learning what's normal for your network",
                "Blocking known bad actors"
            ],
            decisions=[
                ActionButton(
                    id="show_details",
                    label="Show me the details",
                    action_type="expand",
                    severity="info",
                    description="View the technical breakdown"
                )
            ],
            confidence=0.80,
            ai_powered=False
        )
    
    else:
        # LOW - all good
        return AIInsight(
            greeting="All clear! ✅",
            status_emoji="🟢",
            headline="Your network is running smoothly",
            story=f"I logged {total_alerts} routine events — all low priority. This is just your normal network doing its thing. No threats, no concerns, no action needed from you.",
            actions_taken=[
                "Watching all network traffic 24/7",
                "Auto-blocking known threats",
                "Learning your network's patterns"
            ],
            decisions=[],
            confidence=0.95,
            ai_powered=False
        )

async def process_alert_background(alert_id: int, threat_analyzer: ThreatAnalyzer, correlator: AlertCorrelator):
    """AI analysis with strict token budgeting"""
    try:
        async with get_db() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if not alert:
                return
            
            # --- AI BRAIN WITH TOKEN CAPS ---
            threat_score = 0.4
            ai_analysis = None
            
            if settings.AZURE_OPENAI_API_KEY and settings.ai_is_enabled:
                # Optimized call: max_tokens prevents bill shock from long GPT ramblings
                threat_score = await threat_analyzer.calculate_threat_score(alert)
                
                # Get AI analysis if available
                if hasattr(alert, 'ai_analysis'):
                    ai_analysis = alert.ai_analysis
            
            # Find correlations
            correlations = await correlator.find_correlations(alert)
            
            # Update alert
            alert.threat_score = threat_score
            alert.correlations = correlations
            alert.processed_at = datetime.now(timezone.utc)
            await db.flush()
            
            # Index threat for RAG (non-blocking, failures are logged but not critical)
            try:
                await threat_analyzer.index_threat_for_rag(alert, threat_score, ai_analysis)
            except Exception as e:
                logger.warning(f"Failed to index threat for RAG: {e}")
            
    except Exception as e:
        logger.error(f"Background processing failed for alert {alert_id}: {e}")

async def calculate_analytics(db, time_range: str, user_id: Optional[int] = None) -> dict[str, Any]:
    """
    Calculate analytics for the specified time range.
    Only returns alerts from the requested time period.
    
    Data Isolation: If user_id is provided, only returns alerts belonging to that user.
    If user_id is None (unauthenticated/admin), returns all alerts.
    """
    # Parse time range to get start time
    now = datetime.now(timezone.utc)
    
    if time_range == "1h":
        start_time = now - timedelta(hours=1)
    elif time_range == "6h":
        start_time = now - timedelta(hours=6)
    elif time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    elif time_range == "today":
        # Start of today (midnight UTC)
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Default to 24h
        start_time = now - timedelta(hours=24)
    
    # Build base query with time filter
    base_filter = Alert.timestamp >= start_time
    
    # Add user_id filter for data isolation
    if user_id is not None:
        user_filter = Alert.user_id == user_id
        combined_filter = base_filter & user_filter
    else:
        combined_filter = base_filter
    
    # Query alerts within time range (and for specific user if authenticated)
    stmt = (
        select(Alert)
        .where(combined_filter)
        .order_by(Alert.timestamp.desc())
        .limit(50)
    )
    result = await db.execute(stmt)
    alerts_list = result.scalars().all()
    
    # Serialize alerts for JSON response (Dashboard compatibility)
    serialized_alerts = []
    for alert in alerts_list:
        serialized_alerts.append({
            "id": alert.id,
            "source": alert.source,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "timestamp": alert.timestamp.isoformat() if alert.timestamp else None,
            "threat_score": alert.threat_score,
            "raw_data": alert.raw_data,
        })
    
    # Count only alerts in time range (and for user)
    count_stmt = select(func.count()).select_from(Alert).where(combined_filter)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    # Risk score from alerts in time range (and for user)
    risk_stmt = select(func.avg(Alert.threat_score)).select_from(Alert).where(combined_filter)
    risk_result = await db.execute(risk_stmt)
    avg_risk = risk_result.scalar() or 0.0

    # Severity stats for alerts in time range (and for user)
    sev_stmt = (
        select(Alert.severity, func.count(Alert.id))
        .where(combined_filter)
        .group_by(Alert.severity)
    )
    sev_result = await db.execute(sev_stmt)
    severity_map = {row[0]: row[1] for row in sev_result.all()}
    
    return {
        "total_alerts": total,
        "risk_score": float(avg_risk),
        "alerts": serialized_alerts,
        "severity_stats": severity_map,
        "time_range": time_range,
        "start_time": start_time.isoformat(),
    }

async def get_alerts_count() -> int:
    try:
        async with get_db() as db:
            result = await db.execute(select(func.count()).select_from(Alert))
            return result.scalar() or 0
    except Exception:
        return 0
