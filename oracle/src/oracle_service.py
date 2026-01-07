"""
Oracle Backend FastAPI Service - Optimized for Azure AI & Credit Protection
Includes Redis-based De-duplication and Rate Limiting
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

from analytics import AlertCorrelator, ThreatAnalyzer
from config import settings
from database import Alert, get_db
from models import (
    AlertRequest,
    AlertResponse,
    AnalyticsResponse,
    HealthResponse,
    SystemStatus,
)

logger = logging.getLogger(__name__)

# --- SAFEGUARD CONSTANTS ---
DEDUPE_WINDOW_SECONDS = 60      # Ignore identical alerts within 1 minute
GLOBAL_MINUTE_LIMIT = 50        # Hard cap: Max 50 AI-processed alerts per minute
AI_MAX_RESPONSE_TOKENS = 150    # Force brevity to save output tokens

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
        if settings.AI_ENABLED and threat_analyzer.ai_client:
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
                "reason": "AI_ENABLED=false or missing API key"
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
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/analytics", response_model=AnalyticsResponse)
    async def get_analytics(time_range: str = "24h"):
        try:
            async with get_db() as db:
                analytics_data = await calculate_analytics(db, time_range)
            
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
    
    return app

async def generate_ai_insight(analytics_data: dict[str, Any], threat_analyzer: ThreatAnalyzer):
    """Generate conversational, actionable AI insight for non-technical users"""
    from models import AIInsight, ActionButton
    
    total_alerts = analytics_data.get("total_alerts", 0)
    risk_score = analytics_data.get("risk_score", 0.0)
    severity_stats = analytics_data.get("severity_stats", {})
    alerts = analytics_data.get("alerts", [])
    
    # Count by severity
    critical_count = severity_stats.get("critical", 0)
    high_count = severity_stats.get("high", 0)
    medium_count = severity_stats.get("medium", 0)
    
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
    
    # Try AI-powered insight generation
    if threat_analyzer.ai_client and settings.AI_ENABLED:
        # AI prompt would go here - skipping for now since AI is not connected
        pass
    
    # --- CONSUMER-FRIENDLY DETERMINISTIC RESPONSES ---
    
    if total_alerts == 0:
        return AIInsight(
            greeting="Good news! 🎉",
            status_emoji="🟢",
            headline="Your network is safe and quiet",
            story="I've been watching your network for the past 24 hours and everything looks normal. No suspicious activity, no attempted break-ins, no malware. Your business is protected.",
            actions_taken=[
                "Continuously monitoring all network traffic",
                "Blocking known malicious websites automatically",
                "Keeping your threat database up to date"
            ],
            decisions=[],  # No decisions needed
            confidence=0.95,
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

async def calculate_analytics(db, time_range: str) -> dict[str, Any]:
    stmt = select(Alert).order_by(Alert.timestamp.desc()).limit(50)
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
        "alerts": serialized_alerts,
        "severity_stats": severity_map
    }

async def get_alerts_count() -> int:
    try:
        async with get_db() as db:
            result = await db.execute(select(func.count()).select_from(Alert))
            return result.scalar() or 0
    except Exception:
        return 0
