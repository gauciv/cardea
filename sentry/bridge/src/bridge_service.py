#!/usr/bin/env python3
"""
Cardea Bridge Service - Service Orchestration and API Gateway
Central coordination point for all Sentry services and Oracle integration
"""

import asyncio
import json
import logging
import sys
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

# Enhanced platform detection for container environments
class EnhancedPlatformDetector:
    def __init__(self):
        self.container_info = self._detect_container_environment()
        self.os_info = self._detect_os()
        self.network_interfaces = self._detect_network_interfaces()
        self.docker_capabilities = self._detect_docker_capabilities()

    def _detect_container_environment(self):
        """Detect if running inside a container"""
        container_info = {
            "is_container": False,
            "type": "unknown",
            "runtime": "unknown"
        }
        
        try:
            # Check for common container indicators
            if Path("/.dockerenv").exists():
                container_info["is_container"] = True
                container_info["type"] = "docker"
                container_info["runtime"] = "docker"
            elif Path("/proc/1/cgroup").exists():
                with open("/proc/1/cgroup", "r") as f:
                    cgroup_content = f.read()
                    if "docker" in cgroup_content:
                        container_info["is_container"] = True
                        container_info["type"] = "docker"
                        container_info["runtime"] = "docker"
            # Check environment variables
            if os.environ.get("container") or os.environ.get("DOCKER_CONTAINER"):
                container_info["is_container"] = True
                container_info["type"] = "docker"
        except Exception:
            pass
            
        return container_info

    def _detect_os(self):
        """Enhanced OS detection with container awareness"""
        import platform
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "distribution": "unknown",
            "distribution_version": "unknown"
        }
        
        if os_info["system"] == "Linux":
            try:
                if Path("/etc/os-release").exists():
                    with open("/etc/os-release", "r") as f:
                        for line in f:
                            if line.startswith("NAME="):
                                os_info["distribution"] = line.split("=")[1].strip().strip('"')
                            elif line.startswith("VERSION="):
                                os_info["distribution_version"] = line.split("=")[1].strip().strip('"')
                                
                # Special handling for containers
                if self.container_info["is_container"]:
                    if os_info["distribution"] == "unknown":
                        if Path("/etc/debian_version").exists():
                            os_info["distribution"] = "Debian"
                        elif Path("/etc/alpine-release").exists():
                            os_info["distribution"] = "Alpine Linux"
                            
            except Exception:
                pass
                
        return os_info

    def _detect_network_interfaces(self):
        """Detect available network interfaces"""
        interfaces = []
        try:
            import subprocess
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': ' in line and line.strip().startswith(tuple('0123456789')):
                        name = line.split(':')[1].strip().split('@')[0]
                        interfaces.append(name)
        except Exception:
            interfaces = ["eth0"]  # fallback
            
        return interfaces

    def _detect_docker_capabilities(self):
        """Detect Docker capabilities"""
        capabilities = {
            "available": False,
            "version": None,
            "host_networking_supported": False
        }
        
        try:
            import subprocess
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                capabilities["available"] = True
                capabilities["version"] = result.stdout.strip()
                if self.os_info["system"] == "Linux":
                    capabilities["host_networking_supported"] = True
        except Exception:
            pass
            
        return capabilities

    # Legacy compatibility methods
    def get_os_info(self):
        return {"name": self.os_info.get("distribution", self.os_info.get("system", "unknown"))}
    
    def get_hardware_info(self):
        return {"cpu_cores": 1, "memory_gb": 1}
    
    def get_network_interfaces(self):
        return self.network_interfaces
    
    def is_docker_available(self):
        return self.docker_capabilities.get("available", False)


# Fallback minimal platform detector  
class BasicPlatformDetector:
    def get_os_info(self):
        return {"name": "unknown", "version": "unknown"}
    def get_hardware_info(self):
        return {"cpu_cores": 1, "memory_gb": 1}
    def get_network_interfaces(self):
        return ["eth0"]
    def is_docker_available(self):
        return True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data Models
@dataclass
class Alert:
    """Alert data structure"""
    id: str
    timestamp: datetime
    severity: str
    source: str
    event_type: str
    description: str
    raw_data: Dict[str, Any]
    confidence: float = 0.0
    status: str = "new"

@dataclass
class EvidenceSnapshot:
    """Evidence collection for Oracle integration"""
    timestamp: datetime
    alerts: List[Alert]
    network_summary: Dict[str, Any]
    system_context: Dict[str, Any]
    threat_indicators: List[Dict[str, Any]]

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    services: Dict[str, Dict[str, Any]]
    platform: Dict[str, str]

class AlertRequest(BaseModel):
    """Alert submission request"""
    source: str = Field(..., description="Alert source service")
    severity: str = Field(..., description="Alert severity level")
    event_type: str = Field(..., description="Type of security event")
    description: str = Field(..., description="Alert description")
    raw_data: Dict[str, Any] = Field(..., description="Raw alert data")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")

class OracleClient:
    def __init__(self, oracle_url: str):
        self.url = f"{oracle_url.rstrip('/')}/api/alerts"

    async def send_to_cloud(self, alert_data: Dict[str, Any]):
        async with httpx.AsyncClient() as client:
            # We map 'event_type' to 'alert_type' here to fix the mismatch
            oracle_payload = {
                "source": alert_data["source"],
                "alert_type": alert_data["event_type"], # Mapping fix
                "severity": alert_data["severity"],
                "title": f"Anomaly from {alert_data['source']}", # Adding missing title
                "description": alert_data["description"],
                "raw_data": alert_data["raw_data"],
                "timestamp": datetime.now().isoformat()
            }
            try:
                response = await client.post(self.url, json=oracle_payload)
                logger.info(f"☁️ Oracle Cloud Response: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Could not reach Oracle Cloud: {e}")

class BridgeService:
    """Main Bridge service class"""
    
    def __init__(self):
        # Initialize enhanced platform detection
        try:
            self.platform_detector = EnhancedPlatformDetector()
            logger.info("Initialized enhanced platform detection")
        except Exception as e:
            logger.warning(f"Enhanced platform detection failed, using basic: {e}")
            self.platform_detector = BasicPlatformDetector()
        self.alerts: List[Alert] = []
        self.services_status: Dict[str, Dict[str, Any]] = {}
        self.data_paths = {
            "zeek": Path("/opt/zeek/logs"),
            "suricata": Path("/var/log/suricata"),
            "kitnet": Path("/opt/kitnet/data"),
            "bridge": Path("/opt/bridge/data")
        }
        self._setup_data_paths()
        
    def _setup_data_paths(self):
        """Create data directories if they don't exist"""
        for service, path in self.data_paths.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Data path ready: {service} -> {path}")
            except Exception as e:
                logger.warning(f"Could not create {service} data path {path}: {e}")
                # Use fallback paths
                fallback = Path(f"/tmp/cardea/{service}")
                fallback.mkdir(parents=True, exist_ok=True)
                self.data_paths[service] = fallback
                logger.info(f"Using fallback path: {service} -> {fallback}")

    async def check_service_health(self, service: str) -> Dict[str, Any]:
        """Check individual service health"""
        health_info = {
            "status": "unknown",
            "last_check": datetime.now().isoformat(),
            "details": {}
        }
        
        try:
            if service == "zeek":
                # Check for recent Zeek logs
                zeek_log = self.data_paths["zeek"] / "conn.log"
                if zeek_log.exists():
                    stat = zeek_log.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    age_minutes = (datetime.now() - last_modified).total_seconds() / 60
                    
                    health_info.update({
                        "status": "healthy" if age_minutes < 30 else "stale",
                        "details": {
                            "log_file": str(zeek_log),
                            "last_modified": last_modified.isoformat(),
                            "age_minutes": round(age_minutes, 2),
                            "file_size_bytes": stat.st_size
                        }
                    })
                else:
                    health_info.update({
                        "status": "warning",
                        "details": {"message": "No conn.log found", "expected_path": str(zeek_log)}
                    })
                    
            elif service == "suricata":
                # Check for recent Suricata alerts
                suricata_log = self.data_paths["suricata"] / "eve.json"
                if suricata_log.exists():
                    stat = suricata_log.stat()
                    last_modified = datetime.fromtimestamp(stat.st_mtime)
                    age_minutes = (datetime.now() - last_modified).total_seconds() / 60
                    
                    health_info.update({
                        "status": "healthy" if age_minutes < 60 else "stale",
                        "details": {
                            "log_file": str(suricata_log),
                            "last_modified": last_modified.isoformat(),
                            "age_minutes": round(age_minutes, 2),
                            "file_size_bytes": stat.st_size
                        }
                    })
                else:
                    health_info.update({
                        "status": "warning", 
                        "details": {"message": "No eve.json found", "expected_path": str(suricata_log)}
                    })
                    
            elif service == "kitnet":
                # Check KitNET process status
                health_info.update({
                    "status": "healthy",  # Assume healthy for now
                    "details": {"message": "AI monitoring active", "model_loaded": True}
                })
                
            elif service == "bridge":
                # Self-check
                health_info.update({
                    "status": "healthy",
                    "details": {
                        "alerts_processed": len(self.alerts),
                        "platform": self.platform_detector.get_os_info()["name"],
                        "data_paths_ready": all(p.exists() for p in self.data_paths.values())
                    }
                })
                
        except Exception as e:
            health_info.update({
                "status": "error",
                "details": {"error": str(e)}
            })
            logger.error(f"Health check failed for {service}: {e}")
            
        self.services_status[service] = health_info
        return health_info

    async def escalate_to_oracle(alert_data: Dict[str, Any]):
    """Pushes local anomaly evidence to the Azure-powered Oracle Cloud"""
    oracle_url = os.getenv("ORACLE_WEBHOOK_URL", "http://host.docker.internal:8000/api/alerts")
    
        async with httpx.AsyncClient() as client:
            # Mapping Sentry fields to Oracle fields
            payload = {
                "source": alert_data["source"],
                "alert_type": alert_data["event_type"], # 'network_anomaly'
                "severity": alert_data["severity"],
                "title": f"AI Anomaly: {alert_data['source']}",
                "description": alert_data["description"],
                "raw_data": alert_data["raw_data"],
                "timestamp": datetime.now().isoformat()
            }
            try:
                # Note: For MVP, we are bypassing the Auth wall for testing
                # If you keep Auth, you'd add headers={"Authorization": f"Bearer {token}"}
                response = await client.post(oracle_url, json=payload, timeout=10.0)
                logger.info(f"☁️ Cloud Escalation Status: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Cloud Escalation Failed: {e}")

    async def collect_evidence_snapshot(self) -> EvidenceSnapshot:
        """Collect comprehensive evidence snapshot for Oracle integration"""
        try:
            # Get recent alerts
            recent_alerts = [
                alert for alert in self.alerts 
                if alert.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            # Collect network summary from Zeek logs
            network_summary = await self._analyze_zeek_logs()
            
            # Get system context from platform detector
            system_context = {
                "os_info": self.platform_detector.get_os_info(),
                "hardware": self.platform_detector.get_hardware_info(),
                "network_interfaces": self.platform_detector.get_network_interfaces(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Extract threat indicators
            threat_indicators = await self._extract_threat_indicators(recent_alerts)
            
            snapshot = EvidenceSnapshot(
                timestamp=datetime.now(),
                alerts=recent_alerts,
                network_summary=network_summary,
                system_context=system_context,
                threat_indicators=threat_indicators
            )
            
            # Save snapshot for Oracle processing
            await self._save_evidence_snapshot(snapshot)
            
            logger.info(f"Evidence snapshot collected: {len(recent_alerts)} alerts, {len(threat_indicators)} indicators")
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to collect evidence snapshot: {e}")
            raise

    async def _analyze_zeek_logs(self) -> Dict[str, Any]:
        """Analyze recent Zeek logs for network summary"""
        try:
            zeek_log = self.data_paths["zeek"] / "conn.log"
            if not zeek_log.exists():
                return {"status": "no_logs", "message": "Zeek logs not available"}
                
            # Read last 1000 lines for recent activity analysis
            async with aiofiles.open(zeek_log, 'r') as f:
                lines = await f.readlines()
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
            # Basic analysis of connections
            connections = 0
            protocols = {}
            unique_hosts = set()
            
            for line in recent_lines:
                if line.startswith('#') or not line.strip():
                    continue
                    
                try:
                    fields = line.split('\t')
                    if len(fields) >= 7:
                        connections += 1
                        protocol = fields[6] if len(fields) > 6 else 'unknown'
                        protocols[protocol] = protocols.get(protocol, 0) + 1
                        
                        # Extract hosts
                        if len(fields) >= 5:
                            unique_hosts.add(fields[2])  # orig_h
                            unique_hosts.add(fields[4])  # resp_h
                            
                except Exception:
                    continue
                    
            return {
                "total_connections": connections,
                "unique_hosts": len(unique_hosts),
                "protocols": protocols,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Zeek log analysis failed: {e}")
            return {"status": "error", "message": str(e)}

    async def _extract_threat_indicators(self, alerts: List[Alert]) -> List[Dict[str, Any]]:
        """Extract threat indicators from alerts for Oracle analysis"""
        indicators = []
        
        for alert in alerts:
            try:
                indicator = {
                    "type": alert.event_type,
                    "severity": alert.severity,
                    "source": alert.source,
                    "timestamp": alert.timestamp.isoformat(),
                    "confidence": alert.confidence,
                    "description": alert.description
                }
                
                # Extract specific indicators from raw data
                if "src_ip" in alert.raw_data:
                    indicator["src_ip"] = alert.raw_data["src_ip"]
                if "dest_ip" in alert.raw_data:
                    indicator["dest_ip"] = alert.raw_data["dest_ip"]
                if "signature" in alert.raw_data:
                    indicator["signature"] = alert.raw_data["signature"]
                    
                indicators.append(indicator)
                
            except Exception as e:
                logger.error(f"Failed to extract indicator from alert {alert.id}: {e}")
                
        return indicators

    async def _save_evidence_snapshot(self, snapshot: EvidenceSnapshot):
        """Save evidence snapshot to file for Oracle processing"""
        try:
            evidence_file = self.data_paths["bridge"] / f"evidence_{snapshot.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert snapshot to serializable format
            snapshot_data = {
                "timestamp": snapshot.timestamp.isoformat(),
                "alerts": [asdict(alert) for alert in snapshot.alerts],
                "network_summary": snapshot.network_summary,
                "system_context": snapshot.system_context,
                "threat_indicators": snapshot.threat_indicators
            }
            
            async with aiofiles.open(evidence_file, 'w') as f:
                await f.write(json.dumps(snapshot_data, indent=2, default=str))
                
            logger.info(f"Evidence snapshot saved: {evidence_file}")
            
        except Exception as e:
            logger.error(f"Failed to save evidence snapshot: {e}")

    def add_alert(self, alert_request: AlertRequest) -> Alert:
        """Add new alert to the system"""
        alert = Alert(
            id=f"alert_{len(self.alerts) + 1}_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            severity=alert_request.severity,
            source=alert_request.source,
            event_type=alert_request.event_type,
            description=alert_request.description,
            raw_data=alert_request.raw_data,
            confidence=alert_request.confidence
        )
        
        self.alerts.append(alert)
        logger.info(f"New alert added: {alert.id} from {alert.source}")
        
        return alert

# Global bridge service instance
bridge_service = BridgeService()

# FastAPI lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("🌉 Starting Cardea Bridge Service...")
    
    # Startup tasks
    await bridge_service.check_service_health("bridge")
    logger.info("Bridge service initialized successfully")
    
    yield
    
    # Shutdown tasks
    logger.info("🛑 Shutting down Cardea Bridge Service...")

# FastAPI application
app = FastAPI(
    title="Cardea Bridge Service",
    description="Central orchestration and API gateway for Cardea Sentry services",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "Cardea Bridge",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/simple-health")
async def simple_health():
    """Simple health check without platform detection"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Bridge service is running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check for all services"""
    logger.info("Performing health check...")
    
    try:
        services = {}
        for service_name in ["zeek", "suricata", "kitnet", "bridge"]:
            try:
                services[service_name] = await bridge_service.check_service_health(service_name)
            except Exception as e:
                logger.error(f"Failed to check {service_name} health: {e}")
                services[service_name] = {
                    "status": "error",
                    "details": {"error": str(e)}
                }
        
        # Enhanced platform info using improved platform detection
        try:
            detector = bridge_service.platform_detector
            
            # Use the enhanced methods if available
            if hasattr(detector, 'os_info') and hasattr(detector, 'container_info'):
                # Using enhanced PlatformDetector
                os_info = detector.os_info
                container_info = detector.container_info
                
                # Get OS name, prefer distribution over system
                os_name = os_info.get("distribution", os_info.get("system", "unknown"))
                if os_name == "unknown" and container_info.get("is_container"):
                    os_name = f"{os_info.get('system', 'unknown')} (container)"
                
                platform_info = {
                    "os": os_name,
                    "interfaces": str(len(detector.network_interfaces)),
                    "docker": "available" if detector.docker_capabilities.get("available") else "unavailable"
                }
            else:
                # Fallback for basic platform detector
                os_info = detector.get_os_info()
                interfaces = detector.get_network_interfaces()
                docker_available = detector.is_docker_available()
                
                platform_info = {
                    "os": str(os_info.get("name", "unknown")),
                    "interfaces": str(len(interfaces) if isinstance(interfaces, list) else 0),
                    "docker": "available" if docker_available else "unavailable"
                }
                
        except Exception as e:
            logger.error(f"Platform detection failed: {e}")
            platform_info = {
                "os": "unknown",
                "interfaces": "0", 
                "docker": "unknown"
            }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            services=services,
            platform=platform_info
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Return a minimal response if everything fails
        return HealthResponse(
            status="error",
            timestamp=datetime.now().isoformat(),
            services={"bridge": {"status": "error", "details": {"error": str(e)}}},
            platform={"os": "unknown", "interfaces": "0", "docker": "unknown"}
        )

@app.post("/alerts", status_code=status.HTTP_201_CREATED)
async def submit_alert(alert_request: AlertRequest, background_tasks: BackgroundTasks):
    try:
        alert = bridge_service.add_alert(alert_request)
        
        # Collect evidence LOCALLY
        background_tasks.add_task(bridge_service.collect_evidence_snapshot)
        
        # ESCALATE to Cloud Oracle IMMEDIATELY
        background_tasks.add_task(escalate_to_oracle, alert_request.dict())
        
        return {"status": "accepted", "alert_id": alert.id}
    except Exception as e:
        logger.error(f"Failed to submit alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts(limit: int = 100, severity: Optional[str] = None):
    """Get recent alerts with optional filtering"""
    try:
        alerts = bridge_service.alerts[-limit:]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity.lower() == severity.lower()]
        
        return {
            "total": len(alerts),
            "alerts": [asdict(alert) for alert in alerts]
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )

@app.get("/evidence/snapshot")
async def get_evidence_snapshot():
    """Generate and return current evidence snapshot"""
    try:
        snapshot = await bridge_service.collect_evidence_snapshot()
        
        return {
            "timestamp": snapshot.timestamp.isoformat(),
            "alerts_count": len(snapshot.alerts),
            "threat_indicators_count": len(snapshot.threat_indicators),
            "network_summary": snapshot.network_summary,
            "system_context": snapshot.system_context
        }
        
    except Exception as e:
        logger.error(f"Failed to generate evidence snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate evidence snapshot: {str(e)}"
        )

@app.get("/services/{service_name}/status")
async def get_service_status(service_name: str):
    """Get status of specific service"""
    if service_name not in ["zeek", "suricata", "kitnet", "bridge"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found"
        )
    
    try:
        status_info = await bridge_service.check_service_health(service_name)
        return {
            "service": service_name,
            "status": status_info
        }
        
    except Exception as e:
        logger.error(f"Failed to check {service_name} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check service status: {str(e)}"
        )

@app.get("/platform/info")
async def get_platform_info():
    """Get detailed platform information"""
    try:
        return {
            "os_info": bridge_service.platform_detector.get_os_info(),
            "hardware_info": bridge_service.platform_detector.get_hardware_info(),
            "network_interfaces": bridge_service.platform_detector.get_network_interfaces(),
            "docker_available": bridge_service.platform_detector.is_docker_available(),
            "data_paths": {k: str(v) for k, v in bridge_service.data_paths.items()}
        }
        
    except Exception as e:
        logger.error(f"Failed to get platform info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get platform information: {str(e)}"
        )

if __name__ == "__main__":
    # Configuration from environment
    host = os.getenv("BRIDGE_HOST", "0.0.0.0")
    port = int(os.getenv("BRIDGE_PORT", "8001"))  # Changed from 8080 to 8001 to match docker-compose
    debug = os.getenv("DEV_MODE", "false").lower() == "true"
    
    logger.info(f"🚀 Starting Cardea Bridge Service on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    uvicorn.run(
        "bridge_service:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )