#!/usr/bin/env python3
"""
Cardea Attack Simulator
Sends realistic attack alerts to test the dashboard and AI response.
Usage: python simulate_attack.py [scenario] [--prod]
Scenarios: recon, intrusion, exfiltration, full, critical
"""

import requests
import time
import sys
import random
from datetime import datetime

# Default to production
ORACLE_URL_LOCAL = "http://localhost:8000"
ORACLE_URL_PROD = "https://cardea-oracle.greenbeach-350af183.eastasia.azurecontainerapps.io"

# Use prod by default, --local for local testing
ORACLE_URL = ORACLE_URL_PROD
if "--local" in sys.argv:
    ORACLE_URL = ORACLE_URL_LOCAL
    sys.argv.remove("--local")

# Realistic external IPs (these are documentation/test IPs, safe to use)
ATTACKER_IPS = [
    "45.33.32.156",    # Scanme.nmap.org
    "185.220.101.42",  # Tor exit node (example)
    "91.121.87.18",    # OVH range
    "23.129.64.100",   # Example
    "198.51.100.50",   # TEST-NET-2
]

def send_alert(alert_data: dict):
    """Send alert to Oracle"""
    try:
        resp = requests.post(f"{ORACLE_URL}/api/alerts", json=alert_data, timeout=5)
        status = "✅" if resp.status_code in (200, 201) else "❌"
        print(f"{status} [{alert_data['severity'].upper()}] {alert_data['title']}")
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"❌ Failed to send alert: {e}")
        return False

def scenario_reconnaissance():
    """Simulate reconnaissance/scanning phase"""
    print("\n🔍 PHASE 1: Reconnaissance")
    print("-" * 40)
    
    attacker = random.choice(ATTACKER_IPS)
    
    alerts = [
        {
            "source": "zeek",
            "alert_type": "network_anomaly",
            "severity": "low",
            "title": f"DNS Enumeration from {attacker}",
            "description": "Multiple DNS queries for internal hostnames detected",
            "raw_data": {"src_ip": attacker, "queries": 47, "type": "dns_enum"}
        },
        {
            "source": "suricata",
            "alert_type": "network_anomaly",
            "severity": "medium",
            "title": f"Port Scan Detected from {attacker}",
            "description": "Sequential port scanning activity targeting multiple hosts",
            "raw_data": {"src_ip": attacker, "dest_ip": "192.168.1.0/24", "ports_scanned": 1000}
        },
        {
            "source": "zeek",
            "alert_type": "suspicious_behavior",
            "severity": "medium",
            "title": f"Service Fingerprinting from {attacker}",
            "description": "Attempts to identify running services and versions",
            "raw_data": {"src_ip": attacker, "services_probed": ["ssh", "http", "mysql", "rdp"]}
        }
    ]
    
    for alert in alerts:
        send_alert(alert)
        time.sleep(2)

def scenario_intrusion():
    """Simulate active intrusion attempt"""
    print("\n⚔️ PHASE 2: Intrusion Attempt")
    print("-" * 40)
    
    attacker = random.choice(ATTACKER_IPS)
    
    alerts = [
        {
            "source": "suricata",
            "alert_type": "intrusion_detection",
            "severity": "high",
            "title": f"Brute Force SSH Attack from {attacker}",
            "description": "Multiple failed SSH authentication attempts detected",
            "raw_data": {"src_ip": attacker, "dest_port": 22, "attempts": 150, "duration": "5m"}
        },
        {
            "source": "suricata",
            "alert_type": "intrusion_detection",
            "severity": "critical",
            "title": f"SQL Injection Attempt from {attacker}",
            "description": "Malicious SQL payload detected in HTTP request",
            "raw_data": {"src_ip": attacker, "dest_ip": "192.168.1.50", "dest_port": 80, 
                        "payload": "' OR '1'='1' --", "signature": "ET WEB_SERVER SQL Injection"}
        },
        {
            "source": "kitnet",
            "alert_type": "network_anomaly",
            "severity": "high",
            "title": f"Anomalous Connection Pattern from {attacker}",
            "description": "Machine learning model detected unusual traffic behavior",
            "raw_data": {"src_ip": attacker, "anomaly_score": 0.94, "baseline_deviation": "3.2σ"}
        }
    ]
    
    for alert in alerts:
        send_alert(alert)
        time.sleep(2)

def scenario_exfiltration():
    """Simulate data exfiltration attempt"""
    print("\n📤 PHASE 3: Data Exfiltration")
    print("-" * 40)
    
    attacker = random.choice(ATTACKER_IPS)
    
    alerts = [
        {
            "source": "zeek",
            "alert_type": "data_exfiltration",
            "severity": "critical",
            "title": "Large Outbound Data Transfer Detected",
            "description": "Unusual volume of data being sent to external IP",
            "raw_data": {"src_ip": "192.168.1.105", "dest_ip": attacker, 
                        "bytes_transferred": 157286400, "duration": "12m"}
        },
        {
            "source": "suricata",
            "alert_type": "suspicious_behavior",
            "severity": "high",
            "title": "Encrypted Channel to Unknown Endpoint",
            "description": "TLS connection to unrecognized external server",
            "raw_data": {"src_ip": "192.168.1.105", "dest_ip": attacker, 
                        "dest_port": 443, "sni": "cdn-update.xyz"}
        },
        {
            "source": "kitnet",
            "alert_type": "data_exfiltration",
            "severity": "critical",
            "title": "Potential C2 Communication Detected",
            "description": "Periodic beaconing pattern matches known C2 behavior",
            "raw_data": {"src_ip": "192.168.1.105", "dest_ip": attacker,
                        "beacon_interval": "60s", "anomaly_score": 0.97}
        }
    ]
    
    for alert in alerts:
        send_alert(alert)
        time.sleep(2)

def scenario_full():
    """Run full attack simulation"""
    print("\n" + "=" * 50)
    print("🚨 CARDEA ATTACK SIMULATION")
    print("=" * 50)
    print(f"Target: {ORACLE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    scenario_reconnaissance()
    time.sleep(3)
    
    scenario_intrusion()
    time.sleep(3)
    
    scenario_exfiltration()
    
    print("\n" + "=" * 50)
    print("✅ Simulation complete! Check your dashboard.")
    print("=" * 50)

def single_critical():
    """Send a single critical alert for quick testing"""
    print("\n🚨 Sending single critical alert...")
    attacker = random.choice(ATTACKER_IPS)
    
    send_alert({
        "source": "suricata",
        "alert_type": "intrusion_detection",
        "severity": "critical",
        "title": f"Active Intrusion Detected from {attacker}",
        "description": "Confirmed malicious activity - immediate action required",
        "raw_data": {
            "src_ip": attacker,
            "dest_ip": "192.168.1.50",
            "attack_type": "exploitation",
            "confidence": 0.95
        }
    })

if __name__ == "__main__":
    scenarios = {
        "recon": scenario_reconnaissance,
        "intrusion": scenario_intrusion,
        "exfiltration": scenario_exfiltration,
        "full": scenario_full,
        "critical": single_critical
    }
    
    if len(sys.argv) < 2:
        print("Usage: python simulate_attack.py [scenario]")
        print(f"Available scenarios: {', '.join(scenarios.keys())}")
        print("\nExample: python simulate_attack.py full")
        sys.exit(1)
    
    scenario = sys.argv[1].lower()
    if scenario not in scenarios:
        print(f"Unknown scenario: {scenario}")
        print(f"Available: {', '.join(scenarios.keys())}")
        sys.exit(1)
    
    scenarios[scenario]()
