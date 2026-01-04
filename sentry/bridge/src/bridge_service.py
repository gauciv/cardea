#!/usr/bin/env python3
"""
Cardea Bridge Service - Service Orchestration and API Gateway
Modified to include Tactical UI for Sentry Node X230-ARCH
"""

import asyncio
import json
import logging
import sys
import os
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

import aiofiles
from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel, Field

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
        except Exception: pass
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
            except Exception: pass
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
        except Exception: pass
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
    raw_data: Dict[str, Any]
    confidence: float = 0.0
    status: str = "new"

class AlertRequest(BaseModel):
    source: str
    severity: str
    event_type: str
    description: str
    raw_data: Dict[str, Any]
    confidence: float = 0.0

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Dict[str, Any]]
    platform: Dict[str, str]

# --- CORE SERVICE LOGIC ---

async def escalate_to_oracle(alert_data: Dict[str, Any]):
    """Pushes local anomaly evidence to the Azure-powered Oracle Cloud"""
    oracle_url = os.getenv("ORACLE_WEBHOOK_URL", "http://localhost:8000/api/alerts")
    
    async with httpx.AsyncClient() as client:
        # MAP Sentry 'event_type' to Oracle 'alert_type' to avoid 422 errors
        payload = {
            "source": alert_data["source"],
            "alert_type": alert_data["event_type"],
            "severity": alert_data["severity"],
            "title": f"Sentry Alert: {alert_data['event_type'].upper()}",
            "description": alert_data["description"],
            "raw_data": alert_data["raw_data"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            response = await client.post(oracle_url, json=payload, timeout=5.0)
            logger.info(f"☁️ Oracle Cloud Escalation: {response.status_code}")
            # Update local tactical stats
            bridge_service.local_stats["escalations"] += 1
        except Exception as e:
            logger.error(f"❌ Oracle Cloud Unreachable: {e}")

class BridgeService:
    def __init__(self):
        try:
            self.platform_detector = EnhancedPlatformDetector()
        except Exception:
            self.platform_detector = BasicPlatformDetector()
            
        self.alerts: List[Alert] = []
        self.services_status: Dict[str, Dict[str, Any]] = {}
        
        # Tactical UI Stats
        self.local_stats = {
            "anomaly_score": 0.0,
            "packets_sec": 0,
            "escalations": 0,
            "start_time": datetime.now()
        }

        self.data_paths = {
            "zeek": Path("/opt/zeek/logs"),
            "suricata": Path("/var/log/suricata"),
            "kitnet": Path("/opt/kitnet/data"),
            "bridge": Path("/opt/bridge/data")
        }
        self._setup_data_paths()
        
    def _setup_data_paths(self):
        for service, path in self.data_paths.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception:
                self.data_paths[service] = Path(f"/tmp/cardea/{service}")
                self.data_paths[service].mkdir(parents=True, exist_ok=True)

    async def check_service_health(self, service: str) -> Dict[str, Any]:
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
        # Update UI score if available in raw_data
        if "score" in req.raw_data:
            self.local_stats["anomaly_score"] = req.raw_data["score"]
        return alert

bridge_service = BridgeService()

# --- FASTAPI APP & UI ROUTES ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌉 Bridge Service Online [X230-ARCH]")
    yield

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
    """Serves the Tactical UI for local monitoring"""
    return templates.TemplateResponse("index.html", {
        "request": request, 
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
        # 1. Background task for local storage/analysis
        # 2. ESCALATE to Cloud Oracle
        background_tasks.add_task(escalate_to_oracle, alert_request.model_dump())
        return {"status": "accepted", "alert_id": alert.id}
    except Exception as e:
        logger.error(f"Alert injection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts")
async def get_alerts(limit: int = 100):
    return {"total": len(bridge_service.alerts), "alerts": [asdict(a) for a in bridge_service.alerts[-limit:]]}

@app.get("/api/local-stats")
async def get_local_stats():
    """Endpoint for the UI to poll for real-time updates"""
    return bridge_service.local_stats

if __name__ == "__main__":
    port = int(os.getenv("BRIDGE_PORT", "8001"))
    uvicorn.run("bridge_service:app", host="0.0.0.0", port=port, reload=True)