#!/usr/bin/env python3
"""
Oracle Client for Bridge Service
Handles communication with Oracle cloud service
"""

import asyncio
import logging
import aiohttp
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)

class OracleClient:
    """Client for communicating with Oracle cloud service"""
    
    def __init__(self, oracle_url: str):
        self.oracle_url = oracle_url
        self.session = None
        self.connection_attempts = 0
        self.last_successful_ping = None
        
    async def escalate_anomaly(self, alert_data: Dict[str, Any]):
        """Escalate high-score anomaly to Oracle with evidence snapshot"""
        logger.warning(f"🚨 Escalating anomaly to Oracle: score={alert_data.get('anomaly_score', 0):.4f}")
        
        # Collect evidence snapshot for the IP
        evidence_snapshot = await self._collect_evidence_snapshot(
            alert_data.get('network', {}).get('src_ip')
        )
        
        escalation_data = {
            "type": "anomaly_escalation",
            "timestamp": datetime.now().isoformat(),
            "sentry_data": alert_data,
            "evidence_snapshot": evidence_snapshot,
            "escalation_reason": "anomaly_score_threshold_exceeded",
            "requires_analysis": True
        }
        
        await self._send_to_oracle(escalation_data)
    
    async def send_priority_alert(self, alert_data: Dict[str, Any]):
        """Send priority alert from Suricata to Oracle"""
        logger.warning(f"Sending priority alert to Oracle: {alert_data.get('alert', {}).get('signature', 'Unknown')}")
        
        priority_data = {
            "type": "priority_alert",
            "timestamp": datetime.now().isoformat(),
            "sentry_data": alert_data,
            "priority_reason": "high_severity_signature",
            "requires_immediate_attention": True
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
        """Send data to Oracle service"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(
                self.oracle_url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    self.last_successful_ping = datetime.now()
                    logger.info(f"Data sent to Oracle: {result.get('status', 'unknown')}")
                    self.connection_attempts = 0  # Reset on success
                else:
                    logger.error(f"❌ Oracle responded with error: {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Timeout connecting to Oracle")
            self.connection_attempts += 1
            
        except aiohttp.ClientError as e:
            logger.error(f"Connection error to Oracle: {e}")
            self.connection_attempts += 1
            
        except Exception as e:
            logger.error(f"Unexpected error sending to Oracle: {e}")
            self.connection_attempts += 1
    
    async def ping_oracle(self) -> bool:
        """Ping Oracle to check connectivity"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Try to ping a health endpoint
            ping_url = self.oracle_url.replace("/api/alerts", "/health")
            
            async with self.session.get(
                ping_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    self.last_successful_ping = datetime.now()
                    logger.debug("Oracle connectivity OK")
                    return True
                else:
                    logger.warning(f"Oracle ping failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Oracle ping error: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get Oracle connection status"""
        return {
            "oracle_url": self.oracle_url,
            "connection_attempts": self.connection_attempts,
            "last_successful_ping": self.last_successful_ping.isoformat() if self.last_successful_ping else None,
            "is_healthy": self.connection_attempts < 5 and self.last_successful_ping is not None
        }
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()