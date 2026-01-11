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

# Cloud Oracle URL - Azure Container Apps
ORACLE_URL = os.getenv("ORACLE_URL", "https://cardea-oracle.greenbeach-350af183.eastasia.azurecontainerapps.io")
DATA_DIR = Path("/app/data")
CONFIG_FILE = DATA_DIR / "sentry_config.json"

# --- PLATFORM DETECTION LOGIC ---

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
    oracle_url = f"{ORACLE_URL}/api/alerts"
    
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
        self.claim_token = None  # Will be set by Oracle registration
        self.connected_devices_count = 1 if not self.is_setup_mode else 0
        
        if self.is_setup_mode:
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
        """Register with Oracle cloud to get pairing code"""
        if not self.is_setup_mode:
            return

        try:
            logger.info(f"📡 Registering with Oracle: {ORACLE_URL}")
            response = await self.oracle_client.register_device(self.hardware_id)
            
            if response.get("claim_token"):
                self.claim_token = response.get("claim_token")
                logger.info(f"🔑 Pairing Code: {self.claim_token}")
            elif response.get("status") in ("online", "offline") and not response.get("claim_token"):
                # Device exists in Oracle but we're in setup mode - Oracle should give us a new token
                # This happens if device was partially claimed but config was lost
                logger.warning("⚠️ Device exists in Oracle but no claim token returned - may need Oracle fix")
                if not self.claim_token:
                    self.claim_token = self._generate_fallback_code()
                    logger.warning(f"⚠️ Using local fallback code: {self.claim_token}")
            else:
                logger.info(f"📋 Registration response: {response}")
        except Exception as e:
            logger.error(f"❌ Oracle registration failed: {e}")
            # Generate local fallback code if Oracle unreachable
            if not self.claim_token:
                self.claim_token = self._generate_fallback_code()
                logger.warning(f"⚠️ Using local fallback code: {self.claim_token}")

    def _generate_fallback_code(self) -> str:
        """Generate a 6-char fallback pairing code like 'A3K-9M2'"""
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        code = ''.join(random.choice(chars) for _ in range(6))
        return f"{code[:3]}-{code[3:]}"

    async def _poll_registration_status(self):
        """Background loop to register with Oracle and refresh status"""
        # Initial registration
        await self.register_with_oracle()
        
        # Keep polling while in setup mode
        while self.is_setup_mode:
            await asyncio.sleep(30)  # Poll every 30s
            await self.register_with_oracle()

    async def save_configuration(self, api_key: str):
        """Complete setup by saving the API Key and registering with Oracle"""
        try:
            # First, validate the API key by sending a heartbeat BEFORE saving
            self.oracle_client.update_api_key(api_key)
            logger.info(f"📡 Validating API key with Oracle...")
            heartbeat_success = await self.oracle_client.send_heartbeat(self.hardware_id)
            
            if not heartbeat_success:
                logger.error(f"❌ API key validation failed - key may be invalid or device not claimed")
                self.oracle_client.update_api_key(None)  # Reset the key
                return False
            
            # API key is valid, now save configuration
            config = {
                "sentry_id": self.hardware_id,
                "api_key": api_key,
                "configured_at": datetime.now(timezone.utc).isoformat()
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(config, indent=2))
            
            self.api_key = api_key
            self.is_setup_mode = False
            self.claim_token = None
            self.connected_devices_count = 1
            
            # Save account entry with unique nickname
            accounts_file = DATA_DIR / "connected_accounts.json"
            accounts = []
            if accounts_file.exists():
                try:
                    accounts = json.loads(accounts_file.read_text())
                except:
                    pass
            
            existing_nicknames = [a.get("nickname", "") for a in accounts]
            nickname = generate_nickname(existing_nicknames)
            account_number = f"ORC-{self.hardware_id[:4].upper()}-{len(accounts)+1:03d}"
            
            accounts.append({
                "id": str(len(accounts) + 1),
                "nickname": nickname,
                "account_number": account_number,
                "api_key_prefix": api_key[:10] + "...",
                "connected_at": datetime.now(timezone.utc).isoformat()
            })
            accounts_file.write_text(json.dumps(accounts, indent=2))
            
            logger.info(f"✅ Sentry registered with Oracle! Device is now ONLINE")
            return True
        except Exception as e:
            logger.error(f"❌ Config save failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_setup_status(self) -> dict[str, Any]:
        """Return status for the Local UI"""
        if not self.is_setup_mode:
            # Count connected accounts
            accounts_file = DATA_DIR / "connected_accounts.json"
            account_count = 1  # Default
            if accounts_file.exists():
                try:
                    accounts = json.loads(accounts_file.read_text())
                    account_count = len(accounts)
                except:
                    pass
            
            return {
                "configured": True, 
                "sentry_id": self.sentry_id,
                "connected_accounts": account_count
            }
        
        return {
            "configured": False,
            "hardware_id": self.hardware_id,
            "claim_token": self.claim_token or "Registering...",
            "oracle_url": ORACLE_URL
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
    
    # Start Zeek notice monitoring
    notice_task = asyncio.create_task(zeek_notice_monitor.start())
    
    # Start Registration Polling if in setup mode
    reg_task = None
    if bridge_service.is_setup_mode:
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
async def sentry_portal(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "setup_status": bridge_service.get_setup_status()
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

@app.get("/api/setup/status")
async def get_setup_status():
    """Returns the current setup status."""
    return bridge_service.get_setup_status()

@app.post("/api/setup/reset")
async def reset_setup():
    """Resets sentry to setup mode, clearing all connections."""
    try:
        if bridge_service.config_path.exists():
            bridge_service.config_path.unlink()
        
        # Clear accounts file
        accounts_file = DATA_DIR / "connected_accounts.json"
        if accounts_file.exists():
            accounts_file.unlink()
        
        bridge_service.sentry_id = bridge_service.hardware_id
        bridge_service.api_key = None
        bridge_service.is_setup_mode = True
        bridge_service.connected_devices_count = 0
        bridge_service.claim_token = None
        
        bridge_service.oracle_client.update_api_key(None)
        
        # Re-register with Oracle to get a new claim token
        await bridge_service.register_with_oracle()
        
        logger.info("🔄 Sentry reset to setup mode")
        return {
            "status": "reset", 
            "message": "Device unregistered successfully. Ready for new pairing.",
            "claim_token": bridge_service.claim_token or "Registering..."
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
    Registers the device with Oracle immediately after saving the API key.
    """
    api_key = data.get("api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key required")
    
    logger.info(f"🔑 Received API key submission, validating with Oracle...")
    
    try:
        success = await bridge_service.save_configuration(api_key)
        if success:
            logger.info(f"✅ Setup complete! Device registered with Oracle.")
            return {
                "status": "success", 
                "message": "Sentry is now Online and registered!",
                "connected_devices": 1
            }
        else:
            logger.error(f"❌ API key validation failed")
            raise HTTPException(status_code=400, detail="Invalid API key. Please check the key and try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Setup completion failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")

# --- ACCOUNTS MANAGEMENT ---

ACCOUNTS_FILE = DATA_DIR / "connected_accounts.json"

NICKNAME_ADJECTIVES = ["Swift", "Bright", "Silent", "Cosmic", "Noble", "Mystic", "Rapid", "Golden", "Shadow", "Crystal", "Thunder", "Velvet", "Arctic", "Solar", "Lunar"]
NICKNAME_NOUNS = ["Phoenix", "Falcon", "Panther", "Dragon", "Wolf", "Hawk", "Tiger", "Eagle", "Raven", "Viper", "Lynx", "Cobra", "Jaguar", "Orca", "Fox"]

def generate_nickname(existing_nicknames: list[str]) -> str:
    """Generate unique two-word nickname"""
    import random
    for _ in range(100):
        name = f"{random.choice(NICKNAME_ADJECTIVES)} {random.choice(NICKNAME_NOUNS)}"
        if name not in existing_nicknames:
            return name
    return f"Account {random.randint(1000, 9999)}"

def load_accounts() -> list:
    """Load connected accounts from file"""
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except:
            pass
    if bridge_service.api_key:
        return [{"id": "1", "nickname": "Swift Phoenix", "account_number": "ORCxxxx", "connected_at": datetime.now().isoformat()}]
    return []

def save_accounts(accounts: list):
    """Save accounts to file"""
    ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))

@app.get("/api/accounts")
async def get_accounts():
    """Get list of connected Oracle accounts"""
    return load_accounts()

@app.patch("/api/accounts/{account_id}")
async def update_account(account_id: str, request: Request):
    """Update account nickname"""
    data = await request.json()
    accounts = load_accounts()
    for acc in accounts:
        if acc.get("id") == account_id:
            if "nickname" in data:
                acc["nickname"] = data["nickname"][:30]
            break
    save_accounts(accounts)
    return {"status": "updated"}

@app.delete("/api/accounts/{account_id}")
async def remove_account(account_id: str):
    """Remove an Oracle account connection"""
    accounts = load_accounts()
    accounts = [a for a in accounts if a.get("id") != account_id]
    save_accounts(accounts)
    
    if len(accounts) == 0:
        await reset_setup()
    
    return {"status": "removed"}

@app.post("/api/setup/add-account")
async def add_account():
    """Generate new pairing code for additional account"""
    await bridge_service.register_with_oracle()
    return {
        "claim_token": bridge_service.claim_token or "Registering...",
        "message": "Enter this code in your Oracle dashboard"
    }

# --- DEVICE INFO ---

@app.get("/api/device-info")
async def get_device_info():
    """Get device hardware stats"""
    info = {
        "hardware_id": bridge_service.hardware_id,
        "version": "1.0.0",
        "cpu_temp": None,
        "memory_percent": None,
        "disk_percent": None,
        "uptime": None
    }
    
    try:
        # CPU Temperature (Raspberry Pi / Linux)
        temp_file = Path("/sys/class/thermal/thermal_zone0/temp")
        if temp_file.exists():
            temp = int(temp_file.read_text().strip()) / 1000
            info["cpu_temp"] = round(temp, 1)
    except:
        pass
    
    try:
        # Memory usage
        with open("/proc/meminfo") as f:
            lines = f.readlines()
            total = int([l for l in lines if "MemTotal" in l][0].split()[1])
            avail = int([l for l in lines if "MemAvailable" in l][0].split()[1])
            info["memory_percent"] = round((1 - avail/total) * 100, 1)
    except:
        pass
    
    try:
        # Disk usage
        import shutil
        usage = shutil.disk_usage("/")
        info["disk_percent"] = round(usage.used / usage.total * 100, 1)
    except:
        pass
    
    try:
        # Uptime
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            if days > 0:
                info["uptime"] = f"{days}d {hours}h"
            else:
                mins = int((uptime_seconds % 3600) // 60)
                info["uptime"] = f"{hours}h {mins}m"
    except:
        pass
    
    return info

if __name__ == "__main__":
    port = int(os.getenv("BRIDGE_PORT", "8001"))
    uvicorn.run("bridge_service:app", host="0.0.0.0", port=port, reload=True)