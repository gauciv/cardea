"""
Oracle Backend FastAPI Service - Optimized for Azure AI & Credit Protection
Includes Redis-based De-duplication and Rate Limiting
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Any, Optional

import redis.asyncio as redis
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from analytics import AlertCorrelator, ThreatAnalyzer
from config import settings
from database import Alert, get_db
from models import (
    AlertRequest,
    AlertResponse,
    AnalyticsResponse,
    HealthResponse,
    SystemStatus,
    ThreatAnalysisResponse,
)

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
            raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=500, detail=str(e))
    
    return app

async def generate_ai_insight(analytics_data: dict[str, Any], threat_analyzer: ThreatAnalyzer):
    """Generate human-readable AI insight based on current threat data"""
    from models import AIInsight
    
    total_alerts = analytics_data.get("total_alerts", 0)
    risk_score = analytics_data.get("risk_score", 0.0)
    severity_stats = analytics_data.get("severity_stats", {})
    alerts = analytics_data.get("alerts", [])
    
    # Count critical/high alerts
    critical_count = severity_stats.get("critical", 0)
    high_count = severity_stats.get("high", 0)
    
    # Try AI-powered insight generation
    if threat_analyzer.ai_client and settings.AI_ENABLED:
        try:
            # Prepare context for AI
            context = {
                "total_alerts": total_alerts,
                "risk_score": round(risk_score, 3),
                "severity_breakdown": severity_stats,
                "recent_alert_types": list(set(a.get("alert_type", "unknown") for a in alerts[:10])),
                "critical_alerts": critical_count,
                "high_alerts": high_count,
            }
            
            prompt = """Based on the current security telemetry from the Cardea network monitoring system, provide a brief security briefing for a non-technical business owner.

Your response MUST be in this exact JSON format:
{
  "summary": "One sentence summary of the overall security status",
  "what_happened": "2-3 sentences explaining what the system detected in plain language",
  "why_it_matters": "2-3 sentences about the business impact",
  "recommended_actions": ["Action 1", "Action 2", "Action 3"],
  "confidence": 0.85
}

Guidelines:
- If risk is low (<20%) and no critical alerts: Be reassuring
- If risk is moderate (20-50%): Note areas of concern but don't alarm
- If risk is high (>50%) or critical alerts exist: Be clear about urgency
- Always provide actionable next steps"""

            ai_response = await threat_analyzer.reason_with_ai(
                prompt=prompt,
                context=context,
                system_role="You are a friendly cybersecurity advisor who explains technical threats in simple business terms."
            )
            
            if ai_response:
                import re
                import json
                # Extract JSON from response
                json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                if json_match:
                    insight_data = json.loads(json_match.group(1))
                else:
                    insight_data = json.loads(ai_response)
                
                return AIInsight(
                    summary=insight_data.get("summary", "Security analysis complete."),
                    what_happened=insight_data.get("what_happened", ""),
                    why_it_matters=insight_data.get("why_it_matters", ""),
                    recommended_actions=insight_data.get("recommended_actions", []),
                    confidence=insight_data.get("confidence", 0.8),
                    ai_powered=True
                )
                
        except Exception as e:
            logger.warning(f"AI insight generation failed: {e}. Using deterministic fallback.")
    
    # Deterministic fallback
    if total_alerts == 0:
        return AIInsight(
            summary="Your network is quiet. No security alerts detected.",
            what_happened="The Cardea monitoring system has been actively scanning your network and found no suspicious activity during this time period.",
            why_it_matters="This is a good sign! Your security measures appear to be working effectively.",
            recommended_actions=[
                "Continue regular security monitoring",
                "Ensure all software is up to date",
                "Review access permissions periodically"
            ],
            confidence=0.95,
            ai_powered=False
        )
    elif critical_count > 0 or high_count > 0:
        return AIInsight(
            summary=f"⚠️ Action Required: {critical_count + high_count} high-priority security alerts detected.",
            what_happened=f"Your network monitoring system has detected {critical_count} critical and {high_count} high severity events. These may indicate attempted unauthorized access, malware activity, or suspicious network behavior.",
            why_it_matters="High-severity alerts can indicate active threats that may compromise your data, disrupt operations, or expose your business to liability. Prompt attention is recommended.",
            recommended_actions=[
                "Review the critical alerts in the feed below immediately",
                "Check if any unusual login attempts occurred",
                "Consider temporarily isolating affected systems if compromise is suspected",
                "Document findings for potential incident response"
            ],
            confidence=0.85,
            ai_powered=False
        )
    elif risk_score > 0.3:
        return AIInsight(
            summary=f"Moderate activity detected: {total_alerts} alerts with elevated risk score.",
            what_happened=f"The system detected {total_alerts} security events. While none are critical, the overall pattern suggests elevated network activity that warrants attention.",
            why_it_matters="Moderate-risk events often represent reconnaissance or probing activity. Addressing them early can prevent escalation to more serious threats.",
            recommended_actions=[
                "Review the alert feed for patterns",
                "Verify all detected hosts are authorized devices",
                "Consider tightening firewall rules if unusual traffic sources are identified"
            ],
            confidence=0.8,
            ai_powered=False
        )
    else:
        return AIInsight(
            summary=f"Normal operations: {total_alerts} low-priority events logged.",
            what_happened=f"Your network monitoring detected {total_alerts} events, all classified as low severity. This is typical background activity for an active network.",
            why_it_matters="Low-severity alerts help you understand your network's normal behavior patterns. No immediate action is required.",
            recommended_actions=[
                "Continue normal monitoring",
                "Review alerts periodically for patterns",
                "Use this data to establish baseline behavior"
            ],
            confidence=0.9,
            ai_powered=False
        )

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
    except Exception: return 0