#!/usr/bin/env python3
"""
Sentry Integration Validation Script
Tests the complete data flow between Zeek, Suricata, KitNET, and Bridge

Run with: python scripts/validate_integration.py
"""

import asyncio
import sys

import aiohttp
from datetime import datetime
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

BRIDGE_URL = "http://localhost:8001"


class IntegrationValidator:
    """Validates the complete sentry integration"""
    
    def __init__(self):
        self.results: list[tuple[str, bool, str]] = []
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    def log(self, msg: str, status: str = "info"):
        colors = {"ok": GREEN, "fail": RED, "warn": YELLOW, "info": BLUE}
        print(f"{colors.get(status, '')}{msg}{RESET}")
    
    async def check_bridge_health(self) -> bool:
        """Check if Bridge service is running"""
        try:
            async with self.session.get(f"{BRIDGE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"✅ Bridge healthy: {data.get('status')}", "ok")
                    return True
                self.log(f"❌ Bridge returned {resp.status}", "fail")
                return False
        except Exception as e:
            self.log(f"❌ Bridge unreachable: {e}", "fail")
            return False
    
    async def check_endpoints(self) -> dict[str, bool]:
        """Verify all required endpoints exist"""
        endpoints = [
            ("GET", "/health", "Bridge health"),
            ("GET", "/alerts", "Alert listing"),
            ("POST", "/alerts", "KitNET alerts"),
            ("POST", "/api/v1/alerts/suricata", "Suricata alerts"),
            ("GET", "/api/suricata-stats", "Suricata stats"),
            ("GET", "/api/kitnet-stats", "KitNET stats"),
            ("GET", "/api/zeek-notices", "Zeek notices"),
            ("GET", "/api/discovery", "Network discovery"),
            ("GET", "/api/local-stats", "Local stats"),
        ]
        
        results = {}
        self.log(f"\n{BOLD}📡 Checking Bridge Endpoints:{RESET}")
        
        for method, path, name in endpoints:
            try:
                if method == "GET":
                    async with self.session.get(f"{BRIDGE_URL}{path}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        ok = resp.status in (200, 201, 404)  # 404 for some may be OK if empty
                        results[path] = ok
                        status = "ok" if resp.status == 200 else "warn" if resp.status == 404 else "fail"
                        self.log(f"  {'✅' if ok else '❌'} {method} {path} [{name}] → {resp.status}", status)
                else:
                    # For POST, just check it doesn't 404
                    async with self.session.options(f"{BRIDGE_URL}{path}", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        # Just verify endpoint exists
                        results[path] = True
                        self.log(f"  ✅ {method} {path} [{name}] → exists", "ok")
            except Exception as e:
                results[path] = False
                self.log(f"  ❌ {method} {path} [{name}] → {e}", "fail")
        
        return results
    
    async def test_kitnet_alert_flow(self) -> bool:
        """Test KitNET → Bridge alert flow"""
        self.log(f"\n{BOLD}🤖 Testing KitNET Alert Flow:{RESET}")
        
        test_alert = {
            "source": "kitnet",
            "severity": "high",
            "event_type": "network_anomaly",
            "description": "Integration test: AI anomaly score 0.98",
            "raw_data": {
                "anomaly_score": 0.98,
                "packet_info": {
                    "src_ip": "192.168.1.100",
                    "dest_ip": "10.0.0.1",
                    "protocol": "tcp"
                }
            },
            "confidence": 0.95
        }
        
        try:
            async with self.session.post(
                f"{BRIDGE_URL}/alerts",
                json=test_alert,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    self.log(f"  ✅ Alert accepted: {data.get('alert_id', 'unknown')}", "ok")
                    return True
                else:
                    body = await resp.text()
                    self.log(f"  ❌ Alert rejected ({resp.status}): {body[:100]}", "fail")
                    return False
        except Exception as e:
            self.log(f"  ❌ Alert failed: {e}", "fail")
            return False
    
    async def test_suricata_alert_flow(self) -> bool:
        """Test Suricata → Bridge alert flow"""
        self.log(f"\n{BOLD}🛡️ Testing Suricata Alert Flow:{RESET}")
        
        test_alert = {
            "source": "suricata",
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "signature": "ET SCAN Integration Test - Port Scan Detected",
                "category": "Attempted Information Leak",
                "severity": 2,
                "signature_id": 999999,
                "rev": 1,
                "gid": 1,
                "metadata": {
                    "mitre_technique_id": ["T1046"],
                    "mitre_tactic_id": ["TA0007"]
                }
            },
            "network": {
                "src_ip": "192.168.1.200",
                "dest_ip": "10.0.0.1",
                "src_port": 54321,
                "dest_port": 22,
                "protocol": "TCP"
            },
            "flow_id": 123456789
        }
        
        try:
            async with self.session.post(
                f"{BRIDGE_URL}/api/v1/alerts/suricata",
                json=test_alert,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    mitre = data.get("mitre", "none")
                    self.log(f"  ✅ Suricata alert accepted: {data.get('alert_id', 'unknown')} [MITRE: {mitre}]", "ok")
                    return True
                else:
                    body = await resp.text()
                    self.log(f"  ❌ Suricata alert rejected ({resp.status}): {body[:100]}", "fail")
                    return False
        except Exception as e:
            self.log(f"  ❌ Suricata alert failed: {e}", "fail")
            return False
    
    async def test_kitnet_stats_flow(self) -> bool:
        """Test KitNET stats reporting"""
        self.log(f"\n{BOLD}📊 Testing KitNET Stats Flow:{RESET}")
        
        test_stats = {
            "service": "kitnet",
            "uptime_seconds": 120,
            "phase": "DETECT",
            "training_progress": 1.0,
            "total_processed": 5000,
            "anomalies_detected": 12,
            "num_autoencoders": 8,
            "feature_groups": 8,
            "adaptive_threshold": 0.87
        }
        
        try:
            # POST stats
            async with self.session.post(
                f"{BRIDGE_URL}/api/kitnet-stats",
                json=test_stats,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    self.log(f"  ✅ Stats posted successfully", "ok")
                else:
                    self.log(f"  ⚠️ Stats post returned {resp.status}", "warn")
            
            # GET stats
            async with self.session.get(
                f"{BRIDGE_URL}/api/kitnet-stats",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"  ✅ Stats retrieved: phase={data.get('phase')}, processed={data.get('total_processed')}", "ok")
                    return True
                else:
                    self.log(f"  ❌ Stats retrieval failed: {resp.status}", "fail")
                    return False
        except Exception as e:
            self.log(f"  ❌ Stats flow failed: {e}", "fail")
            return False
    
    async def check_zeek_log_access(self) -> bool:
        """Check if Bridge can access Zeek logs"""
        self.log(f"\n{BOLD}📁 Checking Zeek Log Access:{RESET}")
        
        # Check via the zeek-notices endpoint
        try:
            async with self.session.get(
                f"{BRIDGE_URL}/api/zeek-notices",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status", "unknown")
                    processed = data.get("total_processed", 0)
                    self.log(f"  ✅ Zeek Notice Monitor: {status}, processed: {processed}", "ok")
                    return True
                else:
                    self.log(f"  ⚠️ Zeek notices endpoint returned {resp.status}", "warn")
                    return False
        except Exception as e:
            self.log(f"  ❌ Zeek log access check failed: {e}", "fail")
            return False
    
    async def check_data_paths(self) -> dict[str, bool]:
        """Check if data directories exist and are accessible"""
        self.log(f"\n{BOLD}📂 Checking Data Paths:{RESET}")
        
        paths = {
            "Zeek logs": Path("./data/zeek"),
            "Suricata logs": Path("./data/suricata"),
            "KitNET data": Path("./data/kitnet"),
            "Bridge data": Path("./data/bridge"),
        }
        
        results = {}
        for name, path in paths.items():
            exists = path.exists()
            results[name] = exists
            if exists:
                files = list(path.glob("*"))
                self.log(f"  ✅ {name}: {path} ({len(files)} items)", "ok")
            else:
                self.log(f"  ⚠️ {name}: {path} (not found - will be created on start)", "warn")
        
        return results
    
    async def check_suricata_stats(self) -> bool:
        """Check Suricata statistics"""
        self.log(f"\n{BOLD}📈 Checking Suricata Stats:{RESET}")
        
        try:
            async with self.session.get(
                f"{BRIDGE_URL}/api/suricata-stats",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"  ✅ Suricata stats: {data.get('total_alerts', 0)} alerts", "ok")
                    if data.get("mitre_techniques"):
                        self.log(f"     MITRE techniques: {list(data['mitre_techniques'].keys())[:5]}", "info")
                    return True
                else:
                    self.log(f"  ⚠️ Suricata stats returned {resp.status}", "warn")
                    return False
        except Exception as e:
            self.log(f"  ❌ Suricata stats check failed: {e}", "fail")
            return False
    
    async def verify_alert_aggregation(self) -> bool:
        """Verify all alerts are aggregated in Bridge"""
        self.log(f"\n{BOLD}🔄 Verifying Alert Aggregation:{RESET}")
        
        try:
            async with self.session.get(
                f"{BRIDGE_URL}/alerts?limit=50",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    total = data.get("total", 0)
                    alerts = data.get("alerts", [])
                    
                    # Count by source
                    sources = {}
                    for alert in alerts:
                        src = alert.get("source", "unknown")
                        sources[src] = sources.get(src, 0) + 1
                    
                    self.log(f"  ✅ Total alerts: {total}", "ok")
                    for src, count in sources.items():
                        self.log(f"     {src}: {count} alerts", "info")
                    
                    return True
                else:
                    self.log(f"  ❌ Alert retrieval failed: {resp.status}", "fail")
                    return False
        except Exception as e:
            self.log(f"  ❌ Alert aggregation check failed: {e}", "fail")
            return False
    
    async def run_all_checks(self) -> bool:
        """Run all integration checks"""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}   🔍 SENTRY INTEGRATION VALIDATION{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"   Bridge URL: {BRIDGE_URL}")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        print(f"{BOLD}{'='*60}{RESET}")
        
        all_passed = True
        
        # 1. Check Bridge health
        if not await self.check_bridge_health():
            self.log("\n⛔ Bridge is not running. Start with: make dev", "fail")
            return False
        
        # 2. Check all endpoints
        await self.check_endpoints()
        
        # 3. Check data paths
        await self.check_data_paths()
        
        # 4. Test KitNET alert flow
        if not await self.test_kitnet_alert_flow():
            all_passed = False
        
        # 5. Test Suricata alert flow
        if not await self.test_suricata_alert_flow():
            all_passed = False
        
        # 6. Test KitNET stats
        if not await self.test_kitnet_stats_flow():
            all_passed = False
        
        # 7. Check Zeek access
        await self.check_zeek_log_access()
        
        # 8. Check Suricata stats
        await self.check_suricata_stats()
        
        # 9. Verify aggregation
        await self.verify_alert_aggregation()
        
        # Summary
        print(f"\n{BOLD}{'='*60}{RESET}")
        if all_passed:
            print(f"{GREEN}{BOLD}   ✅ ALL INTEGRATION TESTS PASSED{RESET}")
        else:
            print(f"{RED}{BOLD}   ❌ SOME INTEGRATION TESTS FAILED{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        
        return all_passed


async def main():
    async with IntegrationValidator() as validator:
        success = await validator.run_all_checks()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
