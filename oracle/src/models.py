"""
Pydantic Models for Oracle Backend
API request/response models and data validation
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(str, Enum):
    NETWORK_ANOMALY = "network_anomaly"
    INTRUSION_DETECTION = "intrusion_detection"
    MALWARE_DETECTION = "malware_detection"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    # Suricata alert types
    IDS_ALERT = "ids_alert"
    SIGNATURE_MATCH = "signature_match"
    # Zeek notice types (prefixed with zeek_)
    ZEEK_SCAN = "zeek_scan"
    ZEEK_RECON = "zeek_recon"
    ZEEK_ATTACK = "zeek_attack"
    ZEEK_EXPLOIT = "zeek_exploit"
    ZEEK_POLICY = "zeek_policy"
    ZEEK_INTEL = "zeek_intel"
    ZEEK_WEIRD = "zeek_weird"
    ZEEK_NOTICE = "zeek_notice"
    # Catch-all for unknown types
    UNKNOWN = "unknown"

# Request Models
class AlertRequest(BaseModel):
    """Alert data received from Sentry services"""
    source: str = Field(..., description="Source service (bridge, zeek, suricata, kitnet)")
    alert_type: AlertType = Field(..., description="Type of security alert")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    title: str = Field(..., min_length=1, max_length=200, description="Alert title")
    description: str = Field(..., min_length=1, description="Detailed alert description")
    timestamp: Optional[datetime] = Field(default=None, description="Alert timestamp")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw alert data")
    network_context: Optional[Dict[str, Any]] = Field(default=None, description="Network context")
    indicators: List[str] = Field(default_factory=list, description="Threat indicators")

class ThreatAnalysisRequest(BaseModel):
    """Request for threat analysis"""
    time_window: int = Field(default=3600, ge=60, le=86400, description="Analysis time window in seconds")
    threat_types: List[AlertType] = Field(default_factory=list, description="Specific threat types to analyze")
    severity_filter: Optional[AlertSeverity] = Field(default=None, description="Filter by severity")
    include_correlations: bool = Field(default=True, description="Include alert correlations")

class AnalyticsRequest(BaseModel):
    """Request for analytics data"""
    time_range: str = Field(default="24h", description="Time range (1h, 6h, 24h, 7d, 30d)")
    metrics: List[str] = Field(default_factory=list, description="Specific metrics to include")

# Response Models
class HealthResponse(BaseModel):
    """Service health check response"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, Dict[str, Any]]
    system: "SystemStatus"

class SystemStatus(BaseModel):
    """System status information"""
    deployment_env: str
    alerts_processed: int
    threat_score_threshold: float
    uptime_seconds: Optional[int] = None

class AlertResponse(BaseModel):
    """Response for alert processing"""
    alert_id: int
    status: str
    threat_score: Optional[float] = None
    correlations: List[Dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: int

class ThreatInfo(BaseModel):
    """Threat information"""
    threat_id: str
    threat_type: AlertType
    severity: AlertSeverity
    confidence_score: float
    first_seen: datetime
    last_seen: datetime
    indicators: List[str]
    affected_assets: List[str]

class ThreatAnalysisResponse(BaseModel):
    """Threat analysis results"""
    analysis_id: str
    threats_detected: List[ThreatInfo]
    risk_score: float = Field(ge=0.0, le=1.0)
    recommendations: List[str]
    correlations: List[Dict[str, Any]]
    processing_time_ms: int

class AIInsight(BaseModel):
    """AI-generated security insight for human-readable display"""
    summary: str = Field(..., description="Brief summary of the security situation")
    what_happened: str = Field(default="", description="Plain language explanation of events")
    why_it_matters: str = Field(default="", description="Business impact explanation")
    recommended_actions: List[str] = Field(default_factory=list, description="Prioritized action items")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="AI confidence in analysis")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_powered: bool = Field(default=False, description="Whether AI was used for this insight")

class AnalyticsResponse(BaseModel):
    """Analytics data response - aligned with Dashboard frontend types"""
    time_range: str
    total_alerts: int
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0, description="Overall risk score")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="List of recent alerts")
    alerts_by_severity: Dict[str, int] = Field(default_factory=dict)
    alerts_by_type: Dict[str, int] = Field(default_factory=dict)
    top_threats: List[ThreatInfo] = Field(default_factory=list)
    trend_data: List[Dict[str, Any]] = Field(default_factory=list)
    ai_insight: Optional[AIInsight] = Field(default=None, description="AI-generated security insight")
    generated_at: datetime

class WebhookAlert(BaseModel):
    """Webhook alert from Sentry Bridge"""
    bridge_id: str
    timestamp: datetime
    alert_data: AlertRequest
    evidence: Optional[Dict[str, Any]] = None
    platform_context: Optional[Dict[str, Any]] = None

# Authentication Models
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)

class User(BaseModel):
    """User information"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    roles: List[str] = Field(default_factory=list)

# Update forward references
HealthResponse.model_rebuild()