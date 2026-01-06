#!/usr/bin/env python3
"""
Suricata EVE Log Processor
Processes Suricata EVE JSON logs and sends alerts to Bridge service.

Features:
- Tails eve.json for real-time alert processing
- Extracts protocol-specific context (HTTP, DNS, TLS, SMB)
- Sends to Bridge's dedicated Suricata endpoint
- Handles network connectivity issues gracefully
"""

import json
import time
import os
import requests
from pathlib import Path
from typing import Any
from datetime import datetime
import logging
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SuricataLogProcessor:
    def __init__(self):
        # In host network mode, use localhost; in bridge mode, use container name
        bridge_host = os.getenv("BRIDGE_HOST", "localhost")
        bridge_port = os.getenv("BRIDGE_PORT", "8001")
        self.bridge_url = f"http://{bridge_host}:{bridge_port}"
        
        self.eve_log_path = Path("/var/log/suricata/eve.json")
        self.last_position = 0
        self.retry_queue: deque = deque(maxlen=100)  # Queue failed alerts for retry
        
        # Statistics
        self.stats = {
            "alerts_processed": 0,
            "alerts_forwarded": 0,
            "alerts_failed": 0,
            "events_by_type": {},
            "start_time": datetime.now().isoformat()
        }
        
        logger.info(f"🛡️ Suricata Log Processor initialized")
        logger.info(f"   Bridge URL: {self.bridge_url}")
        logger.info(f"   EVE Log: {self.eve_log_path}")

    def process_alert(self, event: dict[str, Any]) -> bool:
        """Process and forward a Suricata alert event to Bridge"""
        try:
            alert_info = event.get("alert", {})
            
            # Build the request payload matching Bridge's SuricataAlertRequest
            payload = {
                "source": "suricata",
                "timestamp": event.get("timestamp"),
                "alert": {
                    "signature": alert_info.get("signature", "Unknown"),
                    "category": alert_info.get("category", "Unknown"),
                    "severity": alert_info.get("severity", 3),
                    "signature_id": alert_info.get("signature_id"),
                    "rev": alert_info.get("rev"),
                    "gid": alert_info.get("gid", 1),
                    "metadata": alert_info.get("metadata", {})  # Contains MITRE tags
                },
                "network": {
                    "src_ip": event.get("src_ip"),
                    "dest_ip": event.get("dest_ip"),
                    "src_port": event.get("src_port"),
                    "dest_port": event.get("dest_port"),
                    "protocol": event.get("proto", "TCP")
                },
                "flow_id": event.get("flow_id")
            }
            
            # Add protocol-specific context if available
            if "http" in event:
                payload["http"] = {
                    "hostname": event["http"].get("hostname"),
                    "url": event["http"].get("url"),
                    "http_method": event["http"].get("http_method"),
                    "http_user_agent": event["http"].get("http_user_agent"),
                    "http_content_type": event["http"].get("http_content_type"),
                    "status": event["http"].get("status"),
                    "length": event["http"].get("length")
                }
            
            if "dns" in event:
                payload["dns"] = {
                    "type": event["dns"].get("type"),
                    "rrname": event["dns"].get("rrname"),
                    "rrtype": event["dns"].get("rrtype"),
                    "rcode": event["dns"].get("rcode"),
                    "answers": event["dns"].get("answers", [])
                }
            
            if "tls" in event:
                payload["tls"] = {
                    "subject": event["tls"].get("subject"),
                    "issuerdn": event["tls"].get("issuerdn"),
                    "sni": event["tls"].get("sni"),
                    "version": event["tls"].get("version"),
                    "ja3": event["tls"].get("ja3", {}).get("hash"),
                    "ja3s": event["tls"].get("ja3s", {}).get("hash"),
                    "fingerprint": event["tls"].get("fingerprint")
                }
            
            if "fileinfo" in event:
                payload["fileinfo"] = {
                    "filename": event["fileinfo"].get("filename"),
                    "magic": event["fileinfo"].get("magic"),
                    "size": event["fileinfo"].get("size"),
                    "md5": event["fileinfo"].get("md5"),
                    "sha1": event["fileinfo"].get("sha1"),
                    "sha256": event["fileinfo"].get("sha256")
                }
            
            # Send to Bridge's dedicated Suricata endpoint
            response = requests.post(
                f"{self.bridge_url}/api/v1/alerts/suricata",
                json=payload,
                timeout=5
            )
            
            if response.status_code in (200, 201):
                self.stats["alerts_forwarded"] += 1
                result = response.json()
                sig_name = alert_info.get("signature", "Unknown")[:50]
                mitre = result.get("mitre", "")
                logger.info(f"✅ Alert forwarded: {sig_name}... {f'[{mitre}]' if mitre else ''}")
                return True
            else:
                logger.error(f"❌ Bridge rejected alert: {response.status_code}")
                self.stats["alerts_failed"] += 1
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Bridge unreachable, queuing alert for retry")
            self.retry_queue.append(event)
            self.stats["alerts_failed"] += 1
            return False
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            self.stats["alerts_failed"] += 1
            return False

    def process_event(self, event: dict[str, Any]) -> None:
        """Process any EVE event type"""
        event_type = event.get("event_type", "unknown")
        
        # Track event types for stats
        self.stats["events_by_type"][event_type] = \
            self.stats["events_by_type"].get(event_type, 0) + 1
        
        # Only forward alerts to Bridge
        if event_type == "alert":
            self.stats["alerts_processed"] += 1
            self.process_alert(event)
        
        # Log interesting non-alert events at debug level
        elif event_type in ("anomaly", "fileinfo"):
            logger.debug(f"📋 {event_type}: {event.get('src_ip')} → {event.get('dest_ip')}")

    def retry_failed_alerts(self) -> None:
        """Retry sending queued alerts"""
        if not self.retry_queue:
            return
            
        logger.info(f"🔄 Retrying {len(self.retry_queue)} queued alerts...")
        retried = 0
        
        while self.retry_queue and retried < 10:
            event = self.retry_queue.popleft()
            if self.process_alert(event):
                retried += 1
            else:
                # Put back if still failing
                self.retry_queue.appendleft(event)
                break

    def tail_eve_log(self) -> None:
        """Tail Suricata EVE log file and process new entries"""
        logger.info("🛡️ Starting Suricata EVE log processor...")
        logger.info(f"   Watching: {self.eve_log_path}")
        
        # Wait for log file to be created
        wait_count = 0
        while not self.eve_log_path.exists():
            if wait_count % 12 == 0:  # Log every minute
                logger.info(f"⏳ Waiting for {self.eve_log_path} to be created...")
            time.sleep(5)
            wait_count += 1
        
        logger.info(f"✅ EVE log found, starting to tail...")
        
        # Start from end of file
        self.last_position = self.eve_log_path.stat().st_size
        
        retry_timer = 0
        
        while True:
            try:
                current_size = self.eve_log_path.stat().st_size
                
                # Check for log rotation (file got smaller)
                if current_size < self.last_position:
                    logger.info("📁 Log rotation detected, resetting position")
                    self.last_position = 0
                
                if current_size > self.last_position:
                    with open(self.eve_log_path, 'r') as f:
                        f.seek(self.last_position)
                        
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                                
                            try:
                                event = json.loads(line)
                                self.process_event(event)
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON: {line[:100]}...")
                                continue
                        
                        self.last_position = f.tell()
                
                # Periodically retry failed alerts and log stats
                retry_timer += 1
                if retry_timer >= 30:  # Every 30 seconds
                    self.retry_failed_alerts()
                    logger.debug(f"📊 Stats: {self.stats['alerts_forwarded']} forwarded, "
                                f"{self.stats['alerts_failed']} failed, "
                                f"{len(self.retry_queue)} queued")
                    retry_timer = 0
                
                time.sleep(1)
                
            except FileNotFoundError:
                logger.warning("EVE log file not found, waiting...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error tailing log file: {e}")
                time.sleep(5)

    def get_stats(self) -> dict[str, Any]:
        """Return processor statistics"""
        return {
            **self.stats,
            "queue_size": len(self.retry_queue),
            "uptime_seconds": (datetime.now() - datetime.fromisoformat(self.stats["start_time"])).total_seconds()
        }


if __name__ == "__main__":
    processor = SuricataLogProcessor()
    processor.tail_eve_log()