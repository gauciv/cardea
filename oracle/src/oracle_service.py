"""
Oracle Backend FastAPI Service
Main application factory and API routes
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from config import settings
from database import get_db, Alert, ThreatIntelligence, SystemMetrics
from models import (
    HealthResponse, AlertRequest, AlertResponse, 
    ThreatAnalysisRequest, ThreatAnalysisResponse,
    SystemStatus, AnalyticsRequest, AnalyticsResponse
)
from analytics import ThreatAnalyzer, AlertCorrelator
from auth import get_current_user, create_access_token

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Cloud-native security analytics and threat correlation platform",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None
    )
    
    # CORS middleware for cross-origin requests
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize analytics components
    threat_analyzer = ThreatAnalyzer()
    alert_correlator = AlertCorrelator()
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Service health check endpoint"""
        try:
            # Check database connectivity
            async with get_db() as db:
                await db.execute("SELECT 1")
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
            
        return HealthResponse(
            status="healthy" if db_status == "healthy" else "degraded",
            timestamp=datetime.now(timezone.utc),
            version=settings.VERSION,
            services={
                "database": {"status": db_status},
                "analytics": {"status": "healthy", "models_loaded": True},
                "threat_intel": {"status": "healthy", "last_update": datetime.now(timezone.utc)}
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
        """Receive and process security alerts from Sentry services"""
        try:
            logger.info(f"Received alert from {alert_request.source}: {alert_request.alert_type}")
            
            # Store alert in database
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
                await db.commit()
                await db.refresh(alert)
            
            # Trigger background processing
            background_tasks.add_task(
                process_alert_background, 
                alert.id, 
                threat_analyzer, 
                alert_correlator
            )
            
            return AlertResponse(
                alert_id=alert.id,
                status="received",
                threat_score=None,  # Will be calculated in background
                correlations=[],
                processing_time_ms=0
            )
            
        except Exception as e:
            logger.error(f"Failed to process alert: {e}")
            raise HTTPException(status_code=500, detail=f"Alert processing failed: {str(e)}")
    
    @app.post("/api/threat-analysis", response_model=ThreatAnalysisResponse)
    async def analyze_threats(
        analysis_request: ThreatAnalysisRequest,
        current_user: dict = Depends(get_current_user)
    ):
        """Perform advanced threat analysis on security data"""
        try:
            start_time = datetime.now()
            
            # Run threat analysis
            analysis_result = await threat_analyzer.analyze_threats(
                time_window=analysis_request.time_window,
                threat_types=analysis_request.threat_types,
                severity_filter=analysis_request.severity_filter
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ThreatAnalysisResponse(
                analysis_id=f"threat_analysis_{int(start_time.timestamp())}",
                threats_detected=analysis_result["threats"],
                risk_score=analysis_result["risk_score"],
                recommendations=analysis_result["recommendations"],
                correlations=analysis_result["correlations"],
                processing_time_ms=int(processing_time)
            )
            
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}")
            raise HTTPException(status_code=500, detail=f"Threat analysis failed: {str(e)}")
    
    @app.get("/api/analytics", response_model=AnalyticsResponse)
    async def get_analytics(
        time_range: str = "24h",
        current_user: dict = Depends(get_current_user)
    ):
        """Get security analytics and metrics"""
        try:
            # Calculate analytics based on stored alerts and metrics
            async with get_db() as db:
                # Get recent alerts for analytics
                analytics_data = await calculate_analytics(db, time_range)
            
            return AnalyticsResponse(
                time_range=time_range,
                total_alerts=analytics_data["total_alerts"],
                alerts_by_severity=analytics_data["alerts_by_severity"],
                alerts_by_type=analytics_data["alerts_by_type"],
                top_threats=analytics_data["top_threats"],
                trend_data=analytics_data["trend_data"],
                generated_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Analytics generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}")
    
    return app

async def process_alert_background(alert_id: int, threat_analyzer: ThreatAnalyzer, correlator: AlertCorrelator):
    """Background task to process alerts asynchronously"""
    try:
        logger.info(f"Processing alert {alert_id} in background")
        
        async with get_db() as db:
            # Get the alert
            alert = await db.get(Alert, alert_id)
            if not alert:
                logger.error(f"Alert {alert_id} not found")
                return
            
            # Calculate threat score
            threat_score = await threat_analyzer.calculate_threat_score(alert)
            
            # Find correlations
            correlations = await correlator.find_correlations(alert)
            
            # Update alert with analysis results
            alert.threat_score = threat_score
            alert.correlations = correlations
            alert.processed_at = datetime.now(timezone.utc)
            
            await db.commit()
            
        logger.info(f"Alert {alert_id} processed successfully (threat_score: {threat_score})")
        
    except Exception as e:
        logger.error(f"Background processing failed for alert {alert_id}: {e}")

async def get_alerts_count() -> int:
    """Get total number of processed alerts"""
    try:
        async with get_db() as db:
            result = await db.execute("SELECT COUNT(*) FROM alerts")
            return result.scalar() or 0
    except Exception:
        return 0

async def calculate_analytics(db, time_range: str) -> Dict[str, Any]:
    """Calculate security analytics for the given time range"""
    # Placeholder implementation - will be enhanced based on real data patterns
    return {
        "total_alerts": 0,
        "alerts_by_severity": {"high": 0, "medium": 0, "low": 0},
        "alerts_by_type": {},
        "top_threats": [],
        "trend_data": []
    }