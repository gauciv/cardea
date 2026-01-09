#!/usr/bin/env python3
"""
Oracle Client for Bridge Service
Handles communication with Oracle cloud service
"""

import asyncio
import logging
import os
import aiohttp
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class OracleClient:
    """Client for communicating with Oracle cloud service"""
    
    def __init__(self, oracle_url: str, api_key: str = None):
        self.oracle_url = oracle_url.rstrip('/')
        self.api_key = api_key or os.getenv("ORACLE_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
        self.connection_attempts = 0
        self.last_successful_ping = None
        
    def update_api_key(self, new_key: str):
        """Update API key dynamically (e.g. after claiming)"""
        self.api_key = new_key
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for standard Oracle API requests"""
        headers = {"Content-Type": "application/json"}
        # Only attach Authorization header if we actually have a key
        # (Registration requests won't have one initially)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            # Also support the legacy header if your backend still checks it
            headers["X-Sentry-API-Key"] = self.api_key
        return headers

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )

    # --- DEVICE MANAGEMENT ENDPOINTS ---

    async def register_device(self, hardware_id: str, version: str = "1.0.0", device_type: str = "sentry_pi") -> Dict[str, Any]:
        """
        Register this device with Oracle on startup.
        Returns the claim_token or status.
        """
        endpoint = f"{self.oracle_url}/api/devices/register"
        payload = {
            "hardware_id": hardware_id,
            "version": version,
            "device_type": device_type
        }
        
        try:
            await self._ensure_session()
            async with self.session.post(endpoint, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info(f"✅ Device registered: Status={data.get('status')}")
                    return data
                else:
                    text = await response.text()
                    logger.error(f"❌ Registration failed ({response.status}): {text}")
                    return {"status": "error", "error": text}
                    
        except Exception as e:
            logger.error(f"Registration connection error: {e}")
            return {"status": "error", "error": str(e)}

    async def send_heartbeat(self, hardware_id: str) -> bool:
        """
        Send periodic heartbeat to Oracle to confirm online status.
        Uses specific X-Sentry headers as defined in the backend.
        """
        if not self.api_key:
            # Cannot heartbeat without an API Key (device must be claimed first)
            return False
            
        endpoint = f"{self.oracle_url}/api/devices/heartbeat"
        
        # Specific headers required by the backend endpoint
        headers = {
            "X-Sentry-ID": hardware_id,
            "X-Sentry-Key": self.api_key
        }
        
        try:
            await self._ensure_session()
            async with self.session.post(endpoint, headers=headers) as response:
                if response.status == 200:
                    self.last_successful_ping = datetime.now()
                    return True
                elif response.status == 403:
                    logger.warning("❌ Heartbeat rejected: Invalid Credentials. Device may have been reset.")
                    return False
                else:
                    logger.warning(f"Heartbeat failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return False

    # --- ALERT ENDPOINTS ---
        
    async def escalate_anomaly(self, alert_data: Dict[str, Any]):
        """Escalate high-score anomaly to Oracle with evidence snapshot"""
        if not self.api_key:
            logger.warning("⚠️ Cannot escalate anomaly: Device not yet claimed/authenticated")
            return

        logger.warning(f"🚨 Escalating anomaly to Oracle: score={alert_data.get('anomaly_score', 0):.4f}")
        
        # Collect evidence snapshot for the IP
        evidence_snapshot = await self._collect_evidence_snapshot(
            alert_data.get('network', {}).get('src_ip')
        )
        
        escalation_data = {
            "source": "bridge",
            "alert_type": "network_anomaly",
            "severity": "high" if alert_data.get('anomaly_score', 0) > 0.8 else "medium",
            "title": f"Anomaly Detected: {alert_data.get('network', {}).get('src_ip', 'Unknown Source')}",
            "description": f"Abnormal traffic pattern detected. Score: {alert_data.get('anomaly_score', 0):.2f}",
            "timestamp": datetime.now().isoformat(),
            "raw_data": alert_data,
            "evidence": evidence_snapshot
        }
        
        await self._send_to_oracle(escalation_data)
    
    async def send_priority_alert(self, alert_data: Dict[str, Any]):
        """Send priority alert from Suricata to Oracle"""
        if not self.api_key:
            return

        logger.warning(f"Sending priority alert to Oracle: {alert_data.get('alert', {}).get('signature', 'Unknown')}")
        
        priority_data = {
            "source": "suricata",
            "alert_type": "intrusion_detection",
            "severity": "critical", # Suricata alerts are usually serious
            "title": alert_data.get('alert', {}).get('signature', 'IDS Alert'),
            "description": f"Signature match on {alert_data.get('dest_ip', 'unknown')}",
            "timestamp": datetime.now().isoformat(),
            "raw_data": alert_data
        }
        
        await self._send_to_oracle(priority_data)
    
    async def _collect_evidence_snapshot(self, target_ip: str) -> Dict[str, Any]:
        """Collect evidence snapshot from Zeek logs for specific IP"""
        evidence = {
            "target_ip": target_ip,
            "zeek_logs": [],
            "collection_timestamp": datetime.now().isoformat(),
            "log_entries_found": 0
        }
        
        if not target_ip:
            return evidence
            
        try:
            zeek_log_path = Path("/opt/zeek/logs/current/conn.log")
            
            if zeek_log_path.exists():
                # Read last 1000 lines and find entries for this IP
                ip_entries = []
                
                with open(zeek_log_path, 'r') as f:
                    # Get last 1000 lines
                    lines = f.readlines()[-1000:] if len(f.readlines()) > 1000 else f.readlines()
                    
                    for line in reversed(lines):  # Start from most recent
                        if target_ip in line and not line.startswith('#'):
                            # Parse Zeek log line for human-readable format
                            parsed_entry = self._parse_zeek_line_for_evidence(line.strip())
                            if parsed_entry:
                                ip_entries.append(parsed_entry)
                                
                            # Limit to last 5 entries
                            if len(ip_entries) >= 5:
                                break
                
                evidence["zeek_logs"] = ip_entries
                evidence["log_entries_found"] = len(ip_entries)
                
        except Exception as e:
            logger.error(f"Error collecting evidence snapshot: {e}")
            evidence["error"] = str(e)
            
        return evidence
    
    def _parse_zeek_line_for_evidence(self, line: str) -> Dict[str, Any]:
        """Parse Zeek conn.log line into human-readable evidence format"""
        try:
            fields = line.split('\t')
            if len(fields) < 10:
                return None
                
            return {
                "timestamp": datetime.fromtimestamp(float(fields[0])).strftime("%Y-%m-%d %H:%M:%S"),
                "connection": f"{fields[2]}:{fields[3]} -> {fields[4]}:{fields[5]}",
                "protocol": fields[6],
                "service": fields[7] if fields[7] != '-' else "unknown",
                "duration": f"{fields[8]}s" if fields[8] != '-' else "N/A",
                "bytes_sent": int(fields[9]) if fields[9] != '-' else 0,
                "bytes_received": int(fields[10]) if len(fields) > 10 and fields[10] != '-' else 0,
                "connection_state": fields[11] if len(fields) > 11 and fields[11] != '-' else "unknown"
            }
        except (ValueError, IndexError):
            return None
    
    async def _send_to_oracle(self, data: Dict[str, Any]):
        """Send data to Oracle service (Alerts endpoint)"""
        endpoint = f"{self.oracle_url}/api/alerts"
        
        try:
            await self._ensure_session()
            
            async with self.session.post(
                endpoint,
                json=data,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    await response.json()
                    self.last_successful_ping = datetime.now()
                    self.connection_attempts = 0
                else:
                    logger.error(f"❌ Oracle rejected alert: {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to Oracle")
            self.connection_attempts += 1
            
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Oracle: {e}")
            self.connection_attempts += 1
            
        except Exception as e:
            logger.error(f"Unexpected error sending to Oracle: {e}")
            self.connection_attempts += 1
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()