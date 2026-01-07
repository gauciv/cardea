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
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw alert data")
    network_context: Optional[dict[str, Any]] = Field(default=None, description="Network context")
    indicators: list[str] = Field(default_factory=list, description="Threat indicators")

class ThreatAnalysisRequest(BaseModel):
    """Request for threat analysis"""
    time_window: int = Field(default=3600, ge=60, le=86400, description="Analysis time window in seconds")
    threat_types: list[AlertType] = Field(default_factory=list, description="Specific threat types to analyze")
    severity_filter: Optional[AlertSeverity] = Field(default=None, description="Filter by severity")
    include_correlations: bool = Field(default=True, description="Include alert correlations")

class AnalyticsRequest(BaseModel):
    """Request for analytics data"""
    time_range: str = Field(default="24h", description="Time range (1h, 6h, 24h, 7d, 30d)")
    metrics: list[str] = Field(default_factory=list, description="Specific metrics to include")

# Response Models
class HealthResponse(BaseModel):
    """Service health check response"""
    status: str
    timestamp: datetime
    version: str
    services: dict[str, dict[str, Any]]
    system: "SystemStatus"

class SystemStatus(BaseModel):
    """System status information"""
    deployment_env: str
    alerts_processed: int
    threat_score_threshold: float
    uptime_seconds: Optional[int] = None
    lockdown_active: bool = False
    lockdown_expires: datetime | None = None
    blocked_ips_count: int = 0
    monitoring_enhanced: bool = False

class AlertResponse(BaseModel):
    """Response for alert processing"""
    alert_id: int
    status: str
    threat_score: Optional[float] = None
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: int

class ThreatInfo(BaseModel):
    """Threat information"""
    threat_id: str
    threat_type: AlertType
    severity: AlertSeverity
    confidence_score: float
    first_seen: datetime
    last_seen: datetime
    indicators: list[str]
    affected_assets: list[str]

class ThreatAnalysisResponse(BaseModel):
    """Threat analysis results"""
    analysis_id: str
    threats_detected: list[ThreatInfo]
    risk_score: float = Field(ge=0.0, le=1.0)
    recommendations: list[str]
    correlations: list[dict[str, Any]]
    processing_time_ms: int

class ActionButton(BaseModel):
    """Actionable button for user to click - the AI will execute the action"""
    id: str = Field(..., description="Unique identifier for the action")
    label: str = Field(..., description="Button text shown to user")
    action_type: str = Field(..., description="Type: block_ip, allow_ip, isolate_device, dismiss, learn_more")
    severity: str = Field(default="info", description="Button color: danger, warning, info, success")
    target: str | None = Field(default=None, description="Target of action (IP, device ID, etc)")
    description: str = Field(default="", description="Tooltip explaining what this does")

class SecurityActionRequest(BaseModel):
    """Request to execute a security action"""
    action_id: str = Field(..., description="Unique action identifier")
    action_type: str = Field(..., description="Type of action: block_ip, lockdown, monitor, dismiss, allow_ip")
    target: str | None = Field(default=None, description="Target (IP addresses, device ID, etc)")
    duration_minutes: int | None = Field(default=60, description="How long the action should last")
    reason: str | None = Field(default=None, description="User-provided reason")

class SecurityActionResponse(BaseModel):
    """Response after executing a security action"""
    success: bool
    action_id: str
    action_type: str
    message: str = Field(..., description="Human-friendly result message")
    details: dict[str, Any] = Field(default_factory=dict, description="Technical details")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = Field(default=None, description="When the action expires (if temporary)")
    can_undo: bool = Field(default=False, description="Whether this action can be reversed")

class BlockedEntity(BaseModel):
    """A blocked IP, domain, or device"""
    id: str
    entity_type: str = Field(..., description="ip, domain, device")
    value: str = Field(..., description="The blocked value (IP address, domain, etc)")
    reason: str
    blocked_at: datetime
    blocked_by: str = Field(default="cardea_ai", description="Who/what blocked it")
    expires_at: datetime | None = None
    is_active: bool = True

class AIInsight(BaseModel):
    """AI-generated security insight - conversational, actionable, human-first"""
    # Conversational greeting - like talking to a security expert friend
    greeting: str = Field(default="Hey there! 👋", description="Friendly opening")
    status_emoji: str = Field(default="🟢", description="Quick visual status: 🟢🟡🟠🔴")
    headline: str = Field(..., description="One-line natural language status")
    
    # The story - what the AI discovered, told naturally
    story: str = Field(default="", description="2-4 sentence narrative of what's happening")
    
    # What we (the AI) already did to protect them
    actions_taken: list[str] = Field(default_factory=list, description="What Cardea already did automatically")
    
    # Decisions for the user - simple buttons, not technical instructions
    decisions: list[ActionButton] = Field(default_factory=list, description="Action buttons for user")
    
    # Optional details (hidden by default, expandable)
    technical_summary: str | None = Field(default=None, description="Technical details for 'show more'")
    
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_powered: bool = Field(default=False)

class AnalyticsResponse(BaseModel):
    """Analytics data response - aligned with Dashboard frontend types"""
    time_range: str
    total_alerts: int
    risk_score: float = Field(ge=0.0, le=1.0, default=0.0, description="Overall risk score")
    alerts: list[dict[str, Any]] = Field(default_factory=list, description="List of recent alerts")
    alerts_by_severity: dict[str, int] = Field(default_factory=dict)
    alerts_by_type: dict[str, int] = Field(default_factory=dict)
    top_threats: list[ThreatInfo] = Field(default_factory=list)
    trend_data: list[dict[str, Any]] = Field(default_factory=list)
    ai_insight: Optional[AIInsight] = Field(default=None, description="AI-generated security insight")
    generated_at: datetime

class WebhookAlert(BaseModel):
    """Webhook alert from Sentry Bridge"""
    bridge_id: str
    timestamp: datetime
    alert_data: AlertRequest
    evidence: Optional[dict[str, Any]] = None
    platform_context: Optional[dict[str, Any]] = None

# Authentication Models
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    """Token payload data"""
    username: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)

class User(BaseModel):
    """User information"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    roles: list[str] = Field(default_factory=list)

# Update forward references
HealthResponse.model_rebuild()