#!/usr/bin/env python3
"""
KitNET AI Anomaly Detection Service
Main entry point for network anomaly detection using KitNET ensemble autoencoders

Proper KitNET implementation with:
- Feature Mapping (FM) phase for correlated feature grouping
- 10,000+ sample training for stable model
- 60 features from multi-log Zeek data
- Adaptive thresholding based on training distribution
"""

import os
import sys
import asyncio
import logging
import aiohttp
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, '/app/src')

from kitnet_detector import KitNETDetector
from network_monitor import NetworkMonitor
from alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KitNETService:
    """Main KitNET service orchestrator"""
    
    def __init__(self):
        self.threshold = float(os.getenv('KITNET_THRESHOLD', '0.95'))
        self.bridge_url = os.getenv('BRIDGE_URL', 'http://bridge:8001').rstrip('/')
        self.data_dir = Path('/app/data')
        self.config_dir = Path('/app/config')
        self.stats_interval = int(os.getenv('STATS_INTERVAL', '60'))  # seconds
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.detector = KitNETDetector(
            model_path=self.data_dir / 'kitnet_model.pkl',
            threshold=self.threshold
        )
        self.monitor = NetworkMonitor()
        self.alert_manager = AlertManager(self.bridge_url)
        
        # Track service state
        self.is_running = False
        self.start_time = None
        
        logger.info(f"🤖 KitNET service initialized")
        logger.info(f"   Threshold: {self.threshold}")
        logger.info(f"   Training samples: {self.detector.TOTAL_TRAINING}")
        logger.info(f"   Bridge URL: {self.bridge_url}")
    
    async def start(self):
        """Start the KitNET anomaly detection service"""
        logger.info("🧠 Starting KitNET AI anomaly detection service...")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            # Initialize detector (load model or start training)
            await self.detector.initialize()
            
            logger.info(f"📊 Detector phase: {self.detector.phase}")
            
            # Start network monitoring
            packet_queue = asyncio.Queue(maxsize=10000)
            
            tasks = [
                asyncio.create_task(self.monitor.start_monitoring(packet_queue)),
                asyncio.create_task(self.process_packets(packet_queue)),
                asyncio.create_task(self.report_stats()),
            ]
            
            logger.info("✅ KitNET service started successfully")
            
            # Run until shutdown
            await asyncio.gather(*tasks)
            
        except asyncio.CancelledError:
            logger.info("🛑 KitNET service cancelled")
        except Exception as e:
            logger.error(f"❌ KitNET service failed: {e}")
            raise
        finally:
            self.is_running = False
            await self.alert_manager.close()
    
    async def process_packets(self, packet_queue: asyncio.Queue):
        """Process packets and detect anomalies"""
        logger.info("🔍 Starting packet anomaly detection...")
        
        processed = 0

                try:
                    packet_data = await asyncio.wait_for(
                        packet_queue.get(), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Extract features and detect anomaly
                features = self.detector.extract_features(packet_data)
                anomaly_score = self.detector.detect_anomaly(features)
                
                processed += 1
                
                # In detection mode, check for anomalies
                if self.detector.phase == "DETECT":
                    if anomaly_score >= 1.0:  # Normalized score >= threshold
                        await self.handle_anomaly(packet_data, anomaly_score)
                
                # Progress logging during training
                elif processed % log_interval == 0:
                    stats = self.detector.get_stats()
                    logger.info(
                        f"📈 Training: {stats['training_progress']:.1%} "
                        f"({stats['training_samples']}/{self.detector.TOTAL_TRAINING}) "
                        f"Phase: {stats['phase']}"
                    )
                
                packet_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing packet: {e}", exc_info=True)
                continue
    
    async def handle_anomaly(self, packet_data: dict, score: float):
        """Handle detected anomaly by alerting Bridge service"""
        logger.warning(f"🚨 Anomaly detected: score={score:.4f}")
        
        # Get detector context
        stats = self.detector.get_stats()
        
        alert_data = {
            "source": "kitnet",
            "timestamp": packet_data.get("timestamp", datetime.now().isoformat()),
            "anomaly_score": score,
            "threshold": self.detector.adaptive_threshold,
            "network": {
                "src_ip": packet_data.get("src_ip"),
                "dest_ip": packet_data.get("dest_ip"),
                "src_port": packet_data.get("src_port"),
                "dest_port": packet_data.get("dest_port"),
                "protocol": packet_data.get("protocol"),
                "service": packet_data.get("service"),
                "duration": packet_data.get("duration"),
            },
            "context": {
                "has_dns": bool(packet_data.get("dns_queries")),
                "has_http": bool(packet_data.get("http_requests")),
                "has_ssl": bool(packet_data.get("ssl_info")),
                "num_autoencoders": stats.get("num_autoencoders", 0),
                "feature_groups": stats.get("feature_groups", 0),
            }
        }
        
        await self.alert_manager.send_alert(alert_data, packet_data)
    
    async def report_stats(self):
        """Periodically report stats to Bridge"""
        while self.is_running:
            await asyncio.sleep(self.stats_interval)
            
            try:
                stats = self.detector.get_stats()
                uptime = (datetime.now() - self.start_time).total_seconds()
                
                report = {
                    "service": "kitnet",
                    "uptime_seconds": uptime,
                    **stats
                }
                
                # Send stats to Bridge
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.bridge_url}/api/kitnet-stats",
                        json=report,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            logger.debug(f"📊 Stats reported: {stats['total_processed']} processed")
                        
            except Exception as e:
                logger.warning(f"Failed to report stats: {e}")


async def main():
    """Main entry point"""
    service = KitNETService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("🛑 KitNET service stopping...")
    except Exception as e:
        logger.error(f"💥 KitNET service crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())