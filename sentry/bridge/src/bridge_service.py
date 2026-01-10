#!/usr/bin/env python3
"""
Cardea Bridge Service - Service Orchestration and API Gateway
Optimized for X230-ARCH with Dynamic Asset Discovery

Now includes:
- Multi-source alert aggregation (KitNET, Suricata, Zeek notices)
- Zeek notice.log monitoring for behavioral detection
- Real-time network discovery from Zeek logs
"""

import asyncio
import json
import logging
import os
import random
import string
import uuid
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from pydantic import BaseModel

from oracle_client import OracleClient

# Import Zeek Notice Monitor
from zeek_notice_monitor import get_notice_monitor

ORACLE_URL = os.getenv("ORACLE_WEBHOOK_URL", "http://localhost:8000") # Base URL
DATA_DIR = Path("/app/data")
CONFIG_FILE = DATA_DIR / "sentry_config.json"

# ============ DEMO MODE CONFIGURATION ============
# For the demo, we use a hardcoded claim code instead of dynamic Oracle registration
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_CLAIM_CODE = "SN7-K2M"  # Realistic device pairing code format

# --- PLATFORM DETECTION LOGIC (PRESERVED) ---

class EnhancedPlatformDetector:
    def __init__(self):
        self.container_info = self._detect_container_environment()
        self.os_info = self._detect_os()
        self.network_interfaces = self._detect_network_interfaces()
        self.docker_capabilities = self._detect_docker_capabilities()

    def _detect_container_environment(self):
        container_info = {"is_container": False, "type": "unknown", "runtime": "unknown"}
        try:
            if Path("/.dockerenv").exists():
                container_info["is_container"] = True
                container_info["type"] = "docker"
            elif Path("/proc/1/cgroup").exists():
                with open("/proc/1/cgroup", "r") as f:
                    if "docker" in f.read():
                        container_info["is_container"] = True
                        container_info["type"] = "docker"
        except OSError:  # Container detection is best-effort
            pass
        return container_info

    def _detect_os(self):
        import platform
        os_info = {"system": platform.system(), "release": platform.release(), "distribution": "unknown"}
        if os_info["system"] == "Linux":
            try:
                if Path("/etc/os-release").exists():
                    with open("/etc/os-release", "r") as f:
                        for line in f:
                            if line.startswith("NAME="): os_info["distribution"] = line.split("=")[1].strip().strip('"')
            except OSError:  # OS detection is best-effort
                pass
        return os_info

    def _detect_network_interfaces(self):
        interfaces = []
        try:
            import subprocess
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': ' in line and line.strip().startswith(tuple('0123456789')):
                        interfaces.append(line.split(':')[1].strip().split('@')[0])
        except Exception: interfaces = ["eth0"]
        return interfaces

    def _detect_docker_capabilities(self):
        capabilities = {"available": False}
        try:
            import subprocess
            if subprocess.run(["docker", "--version"], capture_output=True).returncode == 0:
                capabilities["available"] = True
        except (OSError, FileNotFoundError):  # Docker detection is best-effort
            pass
        return capabilities

    def get_os_info(self): return {"name": self.os_info.get("distribution", "unknown")}
    def get_hardware_info(self): return {"cpu_cores": os.cpu_count() or 1, "memory_gb": 4}
    def get_network_interfaces(self): return self.network_interfaces
    def is_docker_available(self): return self.docker_capabilities.get("available", False)

class BasicPlatformDetector:
    def get_os_info(self): return {"name": "Arch Linux", "version": "Rolling"}
    def get_hardware_info(self): return {"cpu_cores": 4, "memory_gb": 8}
    def get_network_interfaces(self): return ["wlan0", "eth0"]
    def is_docker_available(self): return True

# --- LOGGING & MODELS ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Alert:
    id: str
    timestamp: datetime
    severity: str
    source: str
    event_type: str
    description: str
    raw_data: dict[str, Any]
    confidence: float = 0.0
    status: str = "new"

class AlertRequest(BaseModel):
    source: str
    severity: str
    event_type: str
    description: str
    raw_data: dict[str, Any]
    confidence: float = 0.0

class SuricataAlertRequest(BaseModel):
    """Suricata-specific alert format from EVE JSON"""
    source: str = "suricata"
    timestamp: Optional[str] = None
    alert: dict[str, Any]  # signature, category, severity, signature_id
    network: dict[str, Any]  # src_ip, dest_ip, src_port, dest_port, protocol
    flow_id: Optional[int] = None
    
    # Optional extended fields
    http: Optional[dict[str, Any]] = None
    dns: Optional[dict[str, Any]] = None
    tls: Optional[dict[str, Any]] = None
    fileinfo: Optional[dict[str, Any]] = None

# MITRE ATT&CK mapping for common Suricata rule categories
SURICATA_CATEGORY_TO_MITRE = {
    "A Network Trojan was detected": "T1071",  # Application Layer Protocol
    "Malware Command and Control Activity Detected": "T1071",
    "Attempted Administrator Privilege Gain": "T1068",  # Exploitation for Privilege Escalation
    "Attempted User Privilege Gain": "T1068",
    "Potential Corporate Privacy Violation": "T1041",  # Exfiltration Over C2 Channel
    "Web Application Attack": "T1190",  # Exploit Public-Facing Application
    "Exploit Kit Activity Detected": "T1189",  # Drive-by Compromise
    "A suspicious filename was detected": "T1204",  # User Execution
    "Potentially Bad Traffic": "T1571",  # Non-Standard Port
    "Misc activity": "T1071",
    "Not Suspicious Traffic": None,  # No MITRE mapping
    "Unknown Traffic": None,
}

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: dict[str, dict[str, Any]]
    platform: dict[str, str]

# --- CORE SERVICE LOGIC ---

async def escalate_to_oracle(alert_data: dict[str, Any]):
    """Pushes local anomaly evidence to the Azure-powered Oracle Cloud"""
    oracle_url = os.getenv("ORACLE_WEBHOOK_URL", "http://localhost:8000/api/alerts")
    
    # Normalize alert_type to match Oracle's AlertType enum
    event_type = alert_data.get("event_type", "unknown")
    alert_type_map = {
        "network_anomaly": "network_anomaly",
        "ids_alert": "ids_alert",
        "signature_match": "signature_match",
        "intrusion_detection": "intrusion_detection",
    }
    # Handle zeek notice types (zeek_scan, zeek_recon, etc.)
    if event_type.startswith("zeek_"):
        alert_type = event_type if event_type in [
            "zeek_scan", "zeek_recon", "zeek_attack", "zeek_exploit",
            "zeek_policy", "zeek_intel", "zeek_weird", "zeek_notice"
        ] else "zeek_notice"
    else:
        alert_type = alert_type_map.get(event_type, "unknown")
    
    # Extract network context if available
    network_context = alert_data.get("network", {})
    if not network_context and "raw_data" in alert_data:
        raw = alert_data["raw_data"]
        network_context = {
            "src_ip": raw.get("src_ip"),
            "dest_ip": raw.get("dest_ip"),
            "src_port": raw.get("src_port"),
            "dest_port": raw.get("dest_port"),
            "protocol": raw.get("protocol"),
        }
    
    # Extract indicators from raw_data
    indicators = []
    if "raw_data" in alert_data:
        raw = alert_data["raw_data"]
        if raw.get("mitre_technique"):
            indicators.append(f"MITRE:{raw['mitre_technique']}")
        if raw.get("signature"):
            indicators.append(f"SIG:{raw['signature'][:50]}")
        if raw.get("src_ip"):
            indicators.append(f"IP:{raw['src_ip']}")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "source": alert_data.get("source", "bridge"),
            "alert_type": alert_type,
            "severity": alert_data.get("severity", "medium"),
            "title": f"Sentry Alert: {event_type.upper().replace('_', ' ')}",
            "description": alert_data.get("description", "Security alert from Sentry"),
            "raw_data": alert_data.get("raw_data", {}),
            "network_context": network_context,
            "indicators": indicators,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            response = await client.post(oracle_url, json=payload, timeout=10.0)
            if response.status_code in (200, 201, 202):
                logger.info(f"☁️ Oracle Cloud Escalation: {response.status_code} ({alert_type})")
                bridge_service.local_stats["escalations"] += 1
            elif response.status_code == 422:
                logger.error(f"❌ Oracle Schema Mismatch: {response.text}")
            else:
                logger.warning(f"⚠️ Oracle responded: {response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"❌ Oracle Cloud Timeout")
        except httpx.ConnectError:
            logger.error(f"❌ Oracle Cloud Unreachable (connection refused)")
        except Exception as e:
            logger.error(f"❌ Oracle Cloud Error: {e}")

class BridgeService:
    def __init__(self):
        try:
            self.platform_detector = EnhancedPlatformDetector()
        except Exception:
            self.platform_detector = BasicPlatformDetector()
        
        # --- IDENTITY & SETUP ---
        # Get unique persistent hardware ID (e.g. "pi-10000000abc")
        self.hardware_id = self._get_hardware_id()
        self.oracle_client = OracleClient(ORACLE_URL)
        
        # Load Configuration
        self.config_path = CONFIG_FILE
        self._config = self._load_configuration()
        
        # Determine Identity: Use config if saved, else hardware ID
        self.sentry_id = self._config.get("sentry_id", self.hardware_id)
        self.api_key = self._config.get("api_key")
        
        # Setup Mode State
        self.is_setup_mode = self.api_key is None
        self.claim_token = DEMO_CLAIM_CODE if DEMO_MODE else None  # Use hardcoded code for demo
        self.connected_devices_count = 1 if not self.is_setup_mode else 0
        
        if self.is_setup_mode:
            if DEMO_MODE:
                logger.warning(f"⚠️ DEMO SETUP MODE: Use code '{DEMO_CLAIM_CODE}' on Dashboard")
            else:
                logger.warning(f"⚠️ SETUP MODE: Sentry {self.hardware_id} waiting for claim...")
        else:
            logger.info(f"✅ Sentry Online: {self.sentry_id}")
            self.oracle_client.update_api_key(self.api_key)
            
        self.alerts: list[Alert] = []
        self.services_status: dict[str, dict[str, Any]] = {}
        
        self.local_stats = {
            "anomaly_score": 0.0,
            "packets_sec": 0,
            "escalations": 0,
            "start_time": datetime.now()
        }
        
        # Initialize stats containers
        self.suricata_stats = {
            "alerts_received": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_category": {},
            "recent_signatures": [],
            "mitre_techniques": {},
        }

        self.data_paths = {
            "zeek": Path("/opt/zeek/logs"),
            "suricata": Path("/var/log/suricata"),
            "kitnet": Path("/opt/kitnet/data"),
            "bridge": Path("/app/data")
        }
        self._setup_data_paths()
    
    def _get_hardware_id(self) -> str:
        """Get persistent unique hardware ID (CPU Serial or UUID)"""
        # 1. Try Raspberry Pi Serial
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("Serial"):
                        serial = line.split(":")[1].strip()
                        if serial != "0000000000000000": return f"pi-{serial}"
        except Exception: pass
            
        # 2. Try Linux Machine ID
        try:
            with open("/etc/machine-id", "r") as f: return f"linux-{f.read().strip()}"
        except Exception: pass
            
        # 3. Fallback: Generated/Stored UUID
        uuid_file = DATA_DIR / "hardware_id"
        if uuid_file.exists(): return uuid_file.read_text().strip()
        
        new_id = f"sentry-{uuid.uuid4().hex[:12]}"
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            uuid_file.write_text(new_id)
        except Exception: pass
        return new_id

    def _load_configuration(self) -> dict[str, Any]:
        """Load saved config from JSON file"""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text())
            except Exception as e:
                logger.warning(f"Config load error: {e}")
        return {}
    
    async def register_with_oracle(self):
        """Poll Oracle to register device and keep Claim Token fresh"""
        if not self.is_setup_mode: return

        try:
            # Register using the method added to OracleClient
            response = await self.oracle_client.register_device(self.hardware_id)
            if response.get("status") in ("created", "registered"):
                self.claim_token = response.get("claim_token")
                logger.info(f"🔑 Claim Token: {self.claim_token}")
        except Exception as e:
            logger.error(f"Registration poll failed: {e}")

    async def _poll_registration_status(self):
        """Background loop for Setup Mode"""
        while self.is_setup_mode:
            await self.register_with_oracle()
            await asyncio.sleep(10)

    def save_configuration(self, api_key: str):
        """Complete setup by saving the API Key"""
        try:
            config = {
                "sentry_id": self.hardware_id,
                "api_key": api_key,
                "configured_at": datetime.now(timezone.utc).isoformat()
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(config, indent=2))
            
            self.api_key = api_key
            self.oracle_client.update_api_key(api_key)
            self.is_setup_mode = False
            self.claim_token = None
            self.connected_devices_count = 1  # Mark as connected for demo
            logger.info(f"🎉 Sentry configured successfully! Connected devices: 1")
            return True
        except Exception as e:
            logger.error(f"Config save failed: {e}")
            return False

    def get_setup_status(self) -> dict[str, Any]:
        """Return status for the Local UI"""
        if not self.is_setup_mode:
            return {
                "configured": True, 
                "sentry_id": self.sentry_id,
                "connected_devices": self.connected_devices_count
            }
        
        return {
            "configured": False,
            "hardware_id": self.hardware_id,
            "claim_token": self.claim_token or (DEMO_CLAIM_CODE if DEMO_MODE else "Connecting..."),
            "oracle_url": ORACLE_URL,
            "demo_mode": DEMO_MODE
        }
        
    def _setup_data_paths(self):
        for service, path in self.data_paths.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                # Fallback to tmp if permissions fail
                self.data_paths[service] = Path(f"/tmp/cardea/{service}")
                self.data_paths[service].mkdir(parents=True, exist_ok=True)

    async def check_service_health(self, service: str) -> dict[str, Any]:
        health_info = {"status": "healthy", "last_check": datetime.now().isoformat(), "details": {}}
        if service == "bridge":
            health_info["details"] = {"alerts_in_buffer": len(self.alerts), "uptime": str(datetime.now() - self.local_stats["start_time"])}
        return health_info

    def add_alert(self, req: AlertRequest) -> Alert:
        alert = Alert(
            id=f"alrt_{int(datetime.now().timestamp())}",
            timestamp=datetime.now(),
            severity=req.severity,
            source=req.source,
            event_type=req.event_type,
            description=req.description,
            raw_data=req.raw_data,
            confidence=req.confidence
        )
        self.alerts.append(alert)
        if "score" in req.raw_data:
            self.local_stats["anomaly_score"] = req.raw_data["score"]
        return alert

    async def get_network_discovery(self) -> dict[str, Any]:
        """Dynamically scans local logs and health to build the map data"""
        devices = []
        links = []
        
        # Sentry Gateway
        sentry_status = "online" 
        devices.append({
            "id": "sentry", "name": f"Sentry [{self.hardware_id[:6]}]", 
            "role": "sentry", "status": sentry_status, "ip": "192.168.1.1"
        })

        # Oracle Link
        oracle_status = "online" if self.oracle_client.last_successful_ping else "offline"
        devices.append({
            "id": "oracle", "name": "ORACLE CLOUD", 
            "role": "cloud", "status": oracle_status, "ip": "Azure Endpoint"
        })
        links.append({"source": "oracle", "target": "sentry", "active": oracle_status == "online"})

        # Discover Assets from Zeek conn.log
        try:
            zeek_log = self.data_paths["zeek"] / "conn.log"
            if zeek_log.exists():
                async with aiofiles.open(zeek_log, mode='r') as f:
                    content = await f.read()
                    lines = content.splitlines()
                    discovered_ips = set()
                    for line in lines[-50:]:
                        if not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) > 4:
                                discovered_ips.add(parts[4])
                    
                    for idx, ip in enumerate(list(discovered_ips)[:5]):
                        dev_id = f"dev-{idx}"
                        devices.append({
                            "id": dev_id, "name": f"Device-{idx}", 
                            "role": "asset", "category": "pc", "status": "online", "ip": ip
                        })
                        links.append({"source": "sentry", "target": dev_id, "active": False})
        except Exception as e:
            logger.error(f"Discovery scan failed: {e}")

        return {"devices": devices, "links": links}

bridge_service = BridgeService()

# --- ZEEK NOTICE INTEGRATION ---

async def handle_zeek_notice_alert(alert_data: dict[str, Any]):
    """Callback for Zeek notice monitor - injects notices as alerts."""
    try:
        req = AlertRequest(
            source=alert_data['source'],
            severity=alert_data['severity'],
            event_type=alert_data['event_type'],
            description=alert_data['description'],
            raw_data=alert_data['raw_data'],
            confidence=alert_data.get('confidence', 0.9),
        )
        alert = bridge_service.add_alert(req)
        
        # Auto-escalate high/critical Zeek notices to Oracle
        if alert_data['severity'] in ('high', 'critical'):
            await escalate_to_oracle(alert_data)
            
        logger.info(f"🔔 Zeek notice ingested: {alert.id} ({alert_data['severity']})")
    except Exception as e:
        logger.error(f"Failed to process Zeek notice: {e}")

# Initialize Zeek notice monitor with callback
zeek_notice_monitor = get_notice_monitor(handle_zeek_notice_alert)

# --- FASTAPI APP & UI ROUTES ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🌉 Bridge Service Online [ID: {bridge_service.hardware_id}]")
    if DEMO_MODE:
        logger.info(f"📋 DEMO MODE: Use pairing code '{DEMO_CLAIM_CODE}' on Dashboard")
    
    # Start Zeek notice monitoring
    notice_task = asyncio.create_task(zeek_notice_monitor.start())
    
    # Start Registration Polling ONLY if in setup mode AND not in demo mode
    reg_task = None
    if bridge_service.is_setup_mode and not DEMO_MODE:
        reg_task = asyncio.create_task(bridge_service._poll_registration_status())
    
    yield
    
    # Cleanup
    await zeek_notice_monitor.stop()
    notice_task.cancel()
    if reg_task: reg_task.cancel()
    await bridge_service.oracle_client.close()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="src/templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def tactical_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "setup_status": bridge_service.get_setup_status(), 
        "stats": bridge_service.local_stats,
        "recent_alerts": bridge_service.alerts[-5:]
    })

@app.get("/health", response_model=HealthResponse)
async def health_check():
    services = {s: await bridge_service.check_service_health(s) for s in ["zeek", "kitnet", "bridge"]}
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        services=services,
        platform={"os": bridge_service.platform_detector.get_os_info()["name"], "interfaces": "2"}
    )

@app.post("/alerts", status_code=status.HTTP_201_CREATED)
async def submit_alert(alert_request: AlertRequest, background_tasks: BackgroundTasks):
    try:
        alert = bridge_service.add_alert(alert_request)
        background_tasks.add_task(escalate_to_oracle, alert_request.model_dump())
        return {"status": "accepted", "alert_id": alert.id}
    except Exception as e:
        logger.error(f"Alert injection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/alerts/suricata", status_code=status.HTTP_201_CREATED)
async def submit_suricata_alert(alert_request: SuricataAlertRequest, background_tasks: BackgroundTasks):
    """
    Dedicated endpoint for Suricata EVE JSON alerts.
    Handles Suricata's native format with MITRE ATT&CK enrichment.
    """
    try:
        alert_info = alert_request.alert
        network_info = alert_request.network
        
        # Map Suricata severity (1=high, 2=medium, 3=low) to our format
        suri_severity = alert_info.get("severity", 3)
        severity_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}
        severity = severity_map.get(suri_severity, "medium")
        
        # Extract MITRE technique from category
        category = alert_info.get("category", "Unknown")
        mitre_technique = SURICATA_CATEGORY_TO_MITRE.get(category)
        
        # Build description with context
        signature = alert_info.get("signature", "Unknown signature")
        src_ip = network_info.get("src_ip", "unknown")
        dest_ip = network_info.get("dest_ip", "unknown")
        dest_port = network_info.get("dest_port", "")
        protocol = network_info.get("protocol", "TCP")
        
        description = f"{signature} | {src_ip} → {dest_ip}:{dest_port} ({protocol})"
        if mitre_technique:
            description += f" [MITRE: {mitre_technique}]"
        
        # Build raw_data with all available context
        raw_data = {
            "signature_id": alert_info.get("signature_id"),
            "signature": signature,
            "category": category,
            "src_ip": src_ip,
            "dest_ip": dest_ip,
            "src_port": network_info.get("src_port"),
            "dest_port": dest_port,
            "protocol": protocol,
            "flow_id": alert_request.flow_id,
            "mitre_technique": mitre_technique,
        }
        
        # Add protocol-specific context if available
        if alert_request.http:
            raw_data["http"] = alert_request.http
        if alert_request.dns:
            raw_data["dns"] = alert_request.dns
        if alert_request.tls:
            raw_data["tls"] = alert_request.tls
        if alert_request.fileinfo:
            raw_data["fileinfo"] = alert_request.fileinfo
        
        # Create normalized alert
        normalized = AlertRequest(
            source="suricata",
            severity=severity,
            event_type="ids_alert",
            description=description,
            raw_data=raw_data,
            confidence=0.95 if suri_severity <= 2 else 0.7
        )
        
        alert = bridge_service.add_alert(normalized)
        
        # Update Suricata stats
        bridge_service.suricata_stats["alerts_received"] += 1
        bridge_service.suricata_stats["by_severity"][severity] = \
            bridge_service.suricata_stats["by_severity"].get(severity, 0) + 1
        bridge_service.suricata_stats["by_category"][category] = \
            bridge_service.suricata_stats["by_category"].get(category, 0) + 1
        
        if mitre_technique:
            bridge_service.suricata_stats["mitre_techniques"][mitre_technique] = \
                bridge_service.suricata_stats["mitre_techniques"].get(mitre_technique, 0) + 1
        
        # Track recent signatures (keep last 20 unique)
        if signature not in bridge_service.suricata_stats["recent_signatures"]:
            bridge_service.suricata_stats["recent_signatures"].append(signature)
            if len(bridge_service.suricata_stats["recent_signatures"]) > 20:
                bridge_service.suricata_stats["recent_signatures"].pop(0)
        
        # Auto-escalate high/critical to Oracle
        if severity in ("critical", "high"):
            background_tasks.add_task(escalate_to_oracle, normalized.model_dump())
        
        # Sanitize log output to prevent log injection
        safe_signature = signature[:50].replace('\n', ' ').replace('\r', ' ')
        safe_severity = severity.replace('\n', ' ').replace('\r', ' ')
        logger.info(f"🛡️ Suricata alert: {safe_signature}... [{safe_severity}]")
        return {"status": "accepted", "alert_id": alert.id, "mitre": mitre_technique}
        
    except Exception as e:
        logger.error(f"Suricata alert processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/suricata-stats")
async def get_suricata_stats():
    """Returns Suricata alert statistics and MITRE coverage"""
    stats = bridge_service.suricata_stats
    return {
        "total_alerts": stats["alerts_received"],
        "by_severity": stats["by_severity"],
        "by_category": stats["by_category"],
        "mitre_techniques": stats["mitre_techniques"],
        "recent_signatures": stats["recent_signatures"],
        "last_check": datetime.now().isoformat()
    }

# --- KITNET STATS ENDPOINT ---

# KitNET statistics storage
kitnet_stats = {
    "last_report": None,
    "phase": "unknown",
    "training_progress": 0.0,
    "total_processed": 0,
    "anomalies_detected": 0,
    "uptime_seconds": 0,
    "num_autoencoders": 0,
    "feature_groups": 0,
    "adaptive_threshold": 0.95,
}

@app.post("/api/kitnet-stats")
async def receive_kitnet_stats(data: dict):
    """Receives periodic stats from KitNET service"""
    global kitnet_stats
    kitnet_stats.update(data)
    kitnet_stats["last_report"] = datetime.now().isoformat()
    # Sanitize log output - only log numeric value to prevent log injection
    total_processed = int(data.get('total_processed', 0)) if isinstance(data.get('total_processed'), (int, float)) else 0
    logger.debug(f"🤖 KitNET stats updated: {total_processed} processed")
    return {"status": "ok"}

@app.get("/api/kitnet-stats")
async def get_kitnet_stats():
    """Returns KitNET AI detection statistics"""
    return {
        **kitnet_stats,
        "detection_rate": (
            kitnet_stats["anomalies_detected"] / kitnet_stats["total_processed"]
            if kitnet_stats["total_processed"] > 0 else 0
        ),
        "status": "training" if kitnet_stats["phase"] != "DETECT" else "active",
    }

@app.get("/api/discovery")
async def discovery_endpoint():
    """Provides dynamic data for the React NetworkMap"""
    return await bridge_service.get_network_discovery()

@app.post("/api/update_score")
async def update_score(data: dict):
    """Fixes KitNET 404 by providing the endpoint it's targeting"""
    score = data.get("score", 0.0)
    bridge_service.local_stats["anomaly_score"] = score
    return {"status": "ok"}

@app.get("/alerts")
async def get_alerts(limit: int = 100):
    return {"total": len(bridge_service.alerts), "alerts": [asdict(a) for a in bridge_service.alerts[-limit:]]}

@app.get("/api/local-stats")
async def get_local_stats():
    return bridge_service.local_stats

@app.get("/api/zeek-notices")
async def get_zeek_notice_stats():
    """Returns Zeek notice monitoring statistics and recent notices"""
    stats = zeek_notice_monitor.get_stats()
    return {
        "status": "active" if zeek_notice_monitor.running else "stopped",
        "total_processed": stats["notices_processed"],
        "by_type": stats["by_type"],
        "by_severity": stats["by_severity"],
        "mitre_coverage": len([k for k, v in stats["by_type"].items() if v > 0]),
        "last_check": datetime.now().isoformat()
    }

# --- SETUP MODE / DEVICE AUTHORIZATION ENDPOINTS ---

class PairingClaimRequest(BaseModel):
    """Request body for claiming/simulating pairing"""
    code: str

@app.get("/api/setup/status")
async def get_setup_status():
    """
    Returns the current setup status.
    Used by the UI to determine if setup overlay should be shown.
    """
    return bridge_service.get_setup_status()

@app.post("/api/setup/simulate_claim")
async def simulate_claim(request: PairingClaimRequest):
    """
    TEMPORARY: Simulates the Oracle claim process for testing.
    In production, this would be handled by the Oracle backend.
    
    Accepts the pairing code and if it matches, generates fake credentials.
    """
    if not bridge_service.is_setup_mode:
        raise HTTPException(
            status_code=400, 
            detail="Sentry is already configured"
        )
    
    # Normalize input code (strip whitespace, uppercase)
    input_code = request.code.strip().upper()
    
    if input_code != bridge_service.pairing_code:
        logger.warning(f"⚠️ Invalid pairing attempt: {input_code}")
        raise HTTPException(
            status_code=401,
            detail="Invalid pairing code"
        )
    
    # Generate simulated credentials (In production, Oracle provides these)
    sentry_id = f"sentry-{uuid.uuid4().hex[:8]}"
    api_key = f"sk-{uuid.uuid4().hex}"
    
    if bridge_service.complete_pairing(sentry_id, api_key):
        logger.info(f"🎉 Simulated pairing successful: {sentry_id}")
        return {
            "status": "success",
            "sentry_id": sentry_id,
            "message": "Sentry is now configured and ready"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to save configuration"
        )

@app.post("/api/setup/reset")
async def reset_setup():
    """
    Resets the sentry to setup mode for demo purposes.
    Deletes the config file and clears API key, allowing re-pairing.
    """
    try:
        # Delete config file if exists
        if bridge_service.config_path.exists():
            bridge_service.config_path.unlink()
            logger.info("🗑️ Deleted config file")
        
        # Reset service state
        bridge_service.sentry_id = bridge_service.hardware_id
        bridge_service.api_key = None
        bridge_service.is_setup_mode = True
        bridge_service.connected_devices_count = 0
        # Set claim token to demo code (or None if not in demo mode)
        bridge_service.claim_token = DEMO_CLAIM_CODE if DEMO_MODE else None
        
        # Clear Oracle client API key
        bridge_service.oracle_client.update_api_key(None)
        
        logger.info("🔄 Sentry reset to setup mode - ready for re-pairing")
        return {
            "status": "reset", 
            "message": "Device unregistered successfully. Ready for new pairing.",
            "claim_token": bridge_service.claim_token or "Connecting..."
        }
    except Exception as e:
        logger.error(f"❌ Reset failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

# --- END SETUP MODE ENDPOINTS ---

@app.post("/api/setup/complete")
async def complete_setup(data: dict):
    """
    Called by local UI when user pastes the API Key generated by the Dashboard.
    """
    api_key = data.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key required")
    
    if bridge_service.save_configuration(api_key):
        return {"status": "success", "message": "Sentry is now Online!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save configuration")

if __name__ == "__main__":
    port = int(os.getenv("BRIDGE_PORT", "8001"))
    uvicorn.run("bridge_service:app", host="0.0.0.0", port=port, reload=True)