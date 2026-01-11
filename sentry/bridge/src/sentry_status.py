#!/usr/bin/env python3
"""
Sentry Status Monitor
Monitors and reports status of all Sentry services
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
import aiohttp

logger = logging.getLogger(__name__)

class SentryStatus:
    """Monitors status of all Sentry services"""
    
    def __init__(self):
        self.sentry_id = "sentry_001"  # Should be configurable
        self.start_time = datetime.now()
        self.service_status = {
            "zeek": {"healthy": False, "last_check": None},
            "suricata": {"healthy": False, "last_check": None},
            "kitnet": {"healthy": False, "last_check": None},
            "bridge": {"healthy": True, "last_check": datetime.now()},
            "redis": {"healthy": False, "last_check": None}
        }
        
    async def start_monitoring(self):
        """Start background service monitoring"""
        logger.info("📊 Starting Sentry service monitoring...")
        
        while True:
            await self._check_all_services()
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _check_all_services(self):
        """Check health of all services"""
        try:
            # Check each service
            await asyncio.gather(
                self._check_zeek(),
                self._check_suricata(), 
                self._check_kitnet(),
                self._check_redis(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error in service health check: {e}")
    
    async def _check_zeek(self):
        """Check Zeek service health"""
        try:
            # TODO: Check Zeek logs or process status
            self.service_status["zeek"]["healthy"] = True
            self.service_status["zeek"]["last_check"] = datetime.now()
        except Exception as e:
            logger.warning(f"Zeek health check failed: {e}")
            self.service_status["zeek"]["healthy"] = False
    
    async def _check_suricata(self):
        """Check Suricata service health"""
        try:
            # Similar to Zeek, check process or logs
            self.service_status["suricata"]["healthy"] = True  # Placeholder
            self.service_status["suricata"]["last_check"] = datetime.now()
        except Exception as e:
            logger.warning(f"Suricata health check failed: {e}")
            self.service_status["suricata"]["healthy"] = False
    
    async def _check_kitnet(self):
        """Check KitNET service health"""
        try:
            # KitNET should have its own health endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get("http://kitnet:8000/health", timeout=5) as response:
                    if response.status == 200:
                        self.service_status["kitnet"]["healthy"] = True
                    else:
                        self.service_status["kitnet"]["healthy"] = False
            
            self.service_status["kitnet"]["last_check"] = datetime.now()
            
        except Exception as e:
            logger.warning(f"KitNET health check failed: {e}")
            self.service_status["kitnet"]["healthy"] = False
    
    async def _check_redis(self):
        """Check Redis service health"""
        try:
            # Check Redis connectivity
            # This would use aioredis in a real implementation
            self.service_status["redis"]["healthy"] = True  # Placeholder
            self.service_status["redis"]["last_check"] = datetime.now()
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self.service_status["redis"]["healthy"] = False
    
    async def get_service_status(self) -> dict[str, bool]:
        """Get simple service status"""
        return {
            service: status["healthy"] 
            for service, status in self.service_status.items()
        }
    
    async def get_detailed_status(self) -> dict[str, Any]:
        """Get detailed Sentry status"""
        uptime = datetime.now() - self.start_time
        
        return {
            "sentry_id": self.sentry_id,
            "uptime": str(uptime),
            "alerts_processed": 0,  # Would be tracked in alert processor
            "last_alert": "N/A",  # Would be from alert processor
            "services": {
                service: {
                    "healthy": status["healthy"],
                    "last_check": status["last_check"].isoformat() if status["last_check"] else None,
                    "status": "healthy" if status["healthy"] else "unhealthy"
                }
                for service, status in self.service_status.items()
            }
        }
    
    async def get_network_status(self) -> dict[str, Any]:
        """Get network monitoring status"""
        return {
            "monitoring_active": True,  # Would be from actual monitoring
            "interfaces": ["eth0"],  # Would be detected
            "packet_rate": 0,  # Would be from actual monitoring
            "last_packet": datetime.now().isoformat()  # Placeholder
        }