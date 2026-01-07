"""
Oracle Backend FastAPI Service - Optimized for Azure AI & Credit Protection
Includes Redis-based De-duplication and Rate Limiting
"""

import os
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import redis.asyncio as redis

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, text

from config import settings
from database import get_db, Alert
from models import (
    HealthResponse, AlertRequest, AlertResponse, 
    ThreatAnalysisResponse, SystemStatus, AnalyticsResponse
)
from analytics import ThreatAnalyzer, AlertCorrelator
from fastapi import Depends, status, Body
from models import User
from auth import authenticate_user, create_access_token
try:
    from azure_auth import azure_auth_service
    from google_auth import google_auth_service
except ImportError:
    logger.warning("OAuth modules not available")
    azure_auth_service = None
    google_auth_service = None
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --- SAFEGUARD CONSTANTS ---
DEDUPE_WINDOW_SECONDS = 60      # Ignore identical alerts within 1 minute
GLOBAL_MINUTE_LIMIT = 50        # Hard cap: Max 50 AI-processed alerts per minute
AI_MAX_RESPONSE_TOKENS = 150    # Force brevity to save output tokens

# Initialize Redis client for safeguards
redis_client = redis.from_url(
    f"redis://{os.getenv('REDIS_HOST', 'localhost')}:6379/0", 
    decode_responses=True
)

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
        logger.warning(f"🚫 Dropping duplicate alert from {alert.source}")
        return True

    if current_minute_count > GLOBAL_MINUTE_LIMIT:
        logger.error(f"⚠️ GLOBAL RATE LIMIT EXCEEDED: {current_minute_count}/{GLOBAL_MINUTE_LIMIT}")
        return True

    # Mark as seen for the dedupe window
    await redis_client.setex(dedupe_key, DEDUPE_WINDOW_SECONDS, "1")
    return False

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Cloud-native security analytics with AI Credit Protection",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    threat_analyzer = ThreatAnalyzer()
    alert_correlator = AlertCorrelator()
    
    # Login request model
    class LoginRequest(BaseModel):
        username: str
        password: str
    
    # OAuth validation request model
    class OAuthValidateRequest(BaseModel):
        provider: str  # 'microsoft' or 'google'
    
    @app.post("/api/auth/login", response_model=dict)
    async def login(login_data: LoginRequest):
        """
        Authenticate user with username/password and return JWT token
        """
        try:
            user = await authenticate_user(login_data.username, login_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create access token
            access_token = create_access_token(
                data={"sub": user.username, "scopes": user.roles}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.roles
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during login"
            )
    
    @app.post("/api/auth/oauth/validate", response_model=dict)
    async def validate_oauth(
        oauth_data: OAuthValidateRequest,
        authorization: str = Depends(lambda x: x.headers.get("authorization", ""))
    ):
        """
        Validate OAuth token from Microsoft or Google and return user info
        Frontend sends the token in Authorization header: Bearer <token>
        """
        try:
            # Extract token from Authorization header
            if not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization header format",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            token = authorization.replace("Bearer ", "")
            provider = oauth_data.provider.lower()
            
            # Validate token based on provider
            user_info = None
            if provider == "microsoft" and azure_auth_service:
                user_info = azure_auth_service.validate_token(token)
            elif provider == "google" and google_auth_service:
                user_info = google_auth_service.validate_token(token)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported or unavailable OAuth provider: {provider}"
                )
            
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token validation failed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Return validated user info
            return {
                "status": "valid",
                "provider": provider,
                "user": {
                    "user_id": user_info.get("user_id"),
                    "email": user_info.get("email"),
                    "name": user_info.get("name"),
                }
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OAuth validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during OAuth validation"
            )
    
    # Azure AD / Microsoft Entra authentication endpoint
    class AzureLoginRequest(BaseModel):
        access_token: str
    
    @app.post("/api/auth/azure/login", response_model=dict)
    async def azure_login(azure_data: AzureLoginRequest):
        """
        Validate Microsoft Azure AD / Entra ID access token and create session
        """
        try:
            if not azure_auth_service or not azure_auth_service.is_enabled():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Azure authentication is not configured or unavailable"
                )
            
            # Validate the Azure token
            user_info = azure_auth_service.validate_token(azure_data.access_token)
            
            # Create JWT token for our API
            access_token = create_access_token(
                data={"sub": user_info.get("email"), "provider": "azure"}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_info.get("user_id"),
                    "email": user_info.get("email"),
                    "full_name": user_info.get("name"),
                    "provider": "azure"
                }
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Azure login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Azure authentication failed: {str(e)}"
            )
    
    # Google OAuth authentication endpoint
    class GoogleLoginRequest(BaseModel):
        credential: str  # ID token from Google Sign-In
    
    @app.post("/api/auth/google/login", response_model=dict)
    async def google_login(google_data: GoogleLoginRequest):
        """
        Validate Google ID token and create session
        """
        try:
            if not google_auth_service or not google_auth_service.is_enabled():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Google authentication is not configured or unavailable"
                )
            
            # Validate the Google ID token
            user_info = google_auth_service.validate_token(google_data.credential)
            
            # Create JWT token for our API
            access_token = create_access_token(
                data={"sub": user_info.get("email"), "provider": "google"}
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user_info.get("user_id"),
                    "email": user_info.get("email"),
                    "full_name": user_info.get("name"),
                    "provider": "google"
                }
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google authentication failed: {str(e)}"
            )
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        try:
            async with get_db() as db:
                await db.execute(text("SELECT 1"))
            db_status = "healthy"
            # Check Redis Health
            await redis_client.ping()
            redis_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
            redis_status = "unreachable"
            
        return HealthResponse(
            status="healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
            timestamp=datetime.now(timezone.utc),
            version=settings.VERSION,
            services={
                "database": {"status": db_status},
                "redis_cache": {"status": redis_status},
                "analytics": {"status": "healthy", "models_loaded": True}
            },
            system=SystemStatus(
                deployment_env=settings.DEPLOYMENT_ENVIRONMENT,
                alerts_processed=await get_alerts_count(),
                threat_score_threshold=settings.THREAT_SCORE_THRESHOLD
            )
        )
    
    @app.post("/api/alerts", response_model=AlertResponse)
    async def receive_alert(
        alert_request: AlertRequest, 
        background_tasks: BackgroundTasks,
    ):
        """Receive alerts with Abuse Prevention layer"""
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
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/analytics", response_model=AnalyticsResponse)
    async def get_analytics(time_range: str = "24h"):
        try:
            async with get_db() as db:
                analytics_data = await calculate_analytics(db, time_range)
            
            return AnalyticsResponse(
                total_alerts=analytics_data.get("total_alerts", 0),
                risk_score=analytics_data.get("risk_score", 0.0),
                alerts=analytics_data.get("alerts") or [], 
                generated_at=datetime.now(timezone.utc),
                time_range=time_range,
                alerts_by_severity=analytics_data.get("severity_stats") or {},
                alerts_by_type={},
                top_threats=[],
                trend_data=[]
            )
        except Exception as e:
            logger.error(f"Analytics Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

async def process_alert_background(alert_id: int, threat_analyzer: ThreatAnalyzer, correlator: AlertCorrelator):
    """AI analysis with strict token budgeting"""
    try:
        async with get_db() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if not alert: return
            
            # --- AI BRAIN WITH TOKEN CAPS ---
            threat_score = 0.4
            ai_analysis = None
            
            if settings.AZURE_OPENAI_API_KEY and settings.AI_ENABLED:
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

async def calculate_analytics(db, time_range: str) -> Dict[str, Any]:
    stmt = select(Alert).order_by(Alert.timestamp.desc()).limit(50)
    result = await db.execute(stmt)
    alerts_list = result.scalars().all()
    
    count_stmt = select(func.count()).select_from(Alert)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    risk_stmt = select(func.avg(Alert.threat_score)).select_from(Alert)
    risk_result = await db.execute(risk_stmt)
    avg_risk = risk_result.scalar() or 0.0

    sev_stmt = select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity)
    sev_result = await db.execute(sev_stmt)
    severity_map = {row[0]: row[1] for row in sev_result.all()}
    
    return {
        "total_alerts": total,
        "risk_score": float(avg_risk),
        "alerts": alerts_list,
        "severity_stats": severity_map
    }

async def get_alerts_count() -> int:
    try:
        async with get_db() as db:
            result = await db.execute(select(func.count()).select_from(Alert))
            return result.scalar() or 0
    except Exception: return 0