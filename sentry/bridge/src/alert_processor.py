#!/usr/bin/env python3
"""
Alert Processor for Bridge Service
Processes and manages alerts from Sentry services
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

class AlertProcessor:
    """Processes alerts from Sentry services"""
    
    def __init__(self, threshold: float, sentry_id: str):
        self.threshold = threshold
        self.sentry_id = sentry_id
        self.alerts_queue = asyncio.Queue()
        self.alerts_history: list[dict[str, Any]] = []
        self.processed_count = 0
        
    async def process_alert(self, alert_data: dict[str, Any]) -> str:
        """Process incoming alert and return alert ID"""
        alert_id = str(uuid.uuid4())
        
        # Add metadata
        processed_alert = {
            "id": alert_id,
            "sentry_id": self.sentry_id,
            "processed_at": datetime.now().isoformat(),
            **alert_data
        }
        
        # Add to queue for processing
        await self.alerts_queue.put(processed_alert)
        
        self.processed_count += 1
        logger.info(f"Alert queued: {alert_id} from {alert_data.get('source', 'unknown')}")
        
        return alert_id
    
    async def start_processing(self):
        """Start background alert processing"""
        logger.info("🔄 Starting alert processing...")
        
        while True:
            try:
                # Get alert from queue
                alert = await self.alerts_queue.get()
                
                # Process the alert
                await self._process_single_alert(alert)
                
                # Mark as done
                self.alerts_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in alert processing: {e}")
                continue
    
    async def _process_single_alert(self, alert: dict[str, Any]):
        """Process a single alert"""
        source = alert.get("source", "unknown")
        
        # Store in history
        self.alerts_history.append(alert)
        
        # Keep only recent alerts (last 1000)
        if len(self.alerts_history) > 1000:
            self.alerts_history = self.alerts_history[-1000:]
        
        # Log based on source
        if source == "kitnet":
            score = alert.get("anomaly_score", 0.0)
            logger.info(f"KitNET alert processed: score={score:.4f}, threshold={self.threshold}")
            
        elif source == "suricata":
            signature = alert.get("alert", {}).get("signature", "Unknown")
            logger.info(f"Suricata alert processed: {signature}")
        
        else:
            logger.info(f"Unknown alert source processed: {source}")
    
    async def get_recent_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent alerts"""
        return self.alerts_history[-limit:] if self.alerts_history else []
    
    async def update_threshold(self, new_threshold: float):
        """Update anomaly detection threshold"""
        old_threshold = self.threshold
        self.threshold = new_threshold
        logger.info(f"Threshold updated: {old_threshold} -> {new_threshold}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get processing statistics"""
        return {
            "processed_count": self.processed_count,
            "queue_size": self.alerts_queue.qsize(),
            "history_size": len(self.alerts_history),
            "threshold": self.threshold
        }