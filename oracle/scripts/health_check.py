#!/usr/bin/env python3
"""
Oracle Health Check Script
Used by Docker and Kubernetes for container health probes
"""

import sys
import httpx

HEALTH_ENDPOINT = "http://localhost:8000/health"
TIMEOUT = 5.0


def check_health() -> bool:
    """Check if the Oracle service is healthy"""
    try:
        response = httpx.get(HEALTH_ENDPOINT, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            # Check overall health status
            if data.get("status") == "healthy":
                print("✅ Oracle is healthy")
                return True
            else:
                print(f"⚠️ Oracle degraded: {data}")
                return True  # Still alive, just degraded
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print("❌ Cannot connect to Oracle service")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


if __name__ == "__main__":
    sys.exit(0 if check_health() else 1)
