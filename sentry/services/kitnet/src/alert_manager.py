#!/usr/bin/env python3
"""
Alert Manager for KitNET
Manages alert sending to Bridge service with robust type handling
"""

import logging
import aiohttp
from typing import Any, Union

logger = logging.getLogger(__name__)

class AlertManager:
    """Manages alert sending to Bridge service"""
    
    def __init__(self, bridge_url: str):
        # Clean the URL to ensure no trailing slashes mess up the endpoint
        self.bridge_url = bridge_url.rstrip('/')
        self.alert_count = 0
        self.session = None
        
    async def send_alert(self, score_data: Union[float, dict[str, Any]], packet_info: dict[str, Any] = None):
        """
        Send formatted alert to Bridge service.
        Handles cases where score might be wrapped in a dictionary to prevent TypeErrors.
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Extract the actual float value from the data passed by KitNET
            if isinstance(score_data, dict):
                # If it's a dict, try to find 'score' or 'anomaly_score'
                score = float(score_data.get("score", score_data.get("anomaly_score", 0.0)))
            else:
                # If it's already a number or string, convert directly
                score = float(score_data)

            # Align with the endpoint in bridge_service.py
            endpoint = f"{self.bridge_url}/alerts"
            
            # Construct payload to match bridge_service.py AlertRequest schema
            alert_payload = {
                "source": "kitnet",
                "severity": "high" if score > 0.9 else "medium",
                "event_type": "network_anomaly",
                "description": f"AI detected anomaly with score {score:.4f}",
                "raw_data": {
                    "anomaly_score": score,
                    "packet_info": packet_info or {}
                },
                "confidence": 0.95
            }
            
            async with self.session.post(endpoint, json=alert_payload) as response:
                # The bridge_service returns 201 Created for new alerts
                if response.status in [200, 201]:
                    self.alert_count += 1
                    result = await response.json()
                    logger.info(f"✅ Alert accepted by Bridge: {result.get('alert_id')}")
                elif response.status == 422:
                    error_detail = await response.text()
                    logger.error(f"❌ Schema Mismatch (422): {error_detail}")
                else:
                    logger.error(f"❌ Bridge Error {response.status}: {await response.text()}")
                    
        except Exception as e:
            # Captures and logs any remaining logic errors
            logger.error(f"Error sending alert to Bridge: {e}")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()