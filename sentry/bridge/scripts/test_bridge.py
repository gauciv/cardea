#!/usr/bin/env python3
"""
Test script for Sentry Bridge service
Validates all Bridge components are working correctly
"""

import asyncio
import aiohttp
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_bridge_health():
    """Test Bridge service health endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Bridge health check passed: {data['status']}")
                    return True
                else:
                    logger.error(f"❌ Bridge health check failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Bridge health check error: {e}")
        return False

async def test_kitnet_alert():
    """Test KitNET alert endpoint"""
    try:
        test_alert = {
            "source": "kitnet",
            "timestamp": datetime.now().isoformat(),
            "anomaly_score": 0.97,
            "network": {
                "src_ip": "192.168.1.100",
                "dest_ip": "10.0.0.1",
                "src_port": 12345,
                "dest_port": 443,
                "protocol": "tcp",
                "packet_size": 1200
            },
            "features": {}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/api/v1/alerts/kitnet",
                json=test_alert
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ KitNET alert test passed: {data['alert_id']}")
                    return True
                else:
                    logger.error(f"❌ KitNET alert test failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ KitNET alert test error: {e}")
        return False

async def test_suricata_alert():
    """Test Suricata alert endpoint"""
    try:
        test_alert = {
            "source": "suricata",
            "timestamp": datetime.now().isoformat(),
            "alert": {
                "signature": "TEST: Suspicious activity detected",
                "category": "Trojan",
                "severity": 2,
                "signature_id": 12345
            },
            "network": {
                "src_ip": "192.168.1.200",
                "dest_ip": "10.0.0.2",
                "src_port": 54321,
                "dest_port": 80,
                "protocol": "tcp"
            },
            "flow_id": "test_flow_001"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8001/api/v1/alerts/suricata",
                json=test_alert
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Suricata alert test passed: {data['alert_id']}")
                    return True
                else:
                    logger.error(f"❌ Suricata alert test failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Suricata alert test error: {e}")
        return False

async def test_status_endpoint():
    """Test status endpoint"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/status") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Status endpoint test passed: {data['sentry_id']}")
                    return True
                else:
                    logger.error(f"❌ Status endpoint test failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ Status endpoint test error: {e}")
        return False

async def main():
    """Run all Bridge tests"""
    logger.info("🧪 Starting Bridge service tests...")
    
    tests = [
        ("Health Check", test_bridge_health()),
        ("KitNET Alert", test_kitnet_alert()),
        ("Suricata Alert", test_suricata_alert()),
        ("Status Endpoint", test_status_endpoint())
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"Running {test_name}...")
        result = await test_coro
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        logger.info("🎉 All Bridge service tests passed!")
        return True
    else:
        logger.error("💥 Some Bridge service tests failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)