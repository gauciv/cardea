#!/usr/bin/env python3
"""
Environment Configuration Generator
Generates dynamic environment configuration based on platform detection
"""

import os
import logging
from typing import Any
from pathlib import Path

from platform_detector import platform_detector

logger = logging.getLogger(__name__)

class EnvironmentConfigurator:
    """Generates environment-aware configuration"""
    
    def __init__(self):
        self.platform_config = platform_detector.get_platform_config()
        self.validation = platform_detector.validate_deployment_environment()
        
    def generate_sentry_env(self, output_path: Path = None) -> dict[str, str]:
        """Generate environment variables for Sentry deployment"""
        
        # Base configuration
        env_config = {
            "SENTRY_ID": "sentry_001",
            "LOG_LEVEL": "info",
            "ALERT_THRESHOLD": "0.95",
            "KITNET_THRESHOLD": "0.95",
            "PORT": "8001",
            "NODE_ENV": "production",
            "ORACLE_WEBHOOK_URL": "http://localhost:8000/api/alerts"
        }
        
        # Platform-aware network interface selection
        recommended_interface = self.platform_config["networking"]["recommended_interface"]
        if recommended_interface:
            env_config["ZEEK_INTERFACE"] = recommended_interface
            env_config["SURICATA_INTERFACE"] = recommended_interface
        else:
            # Fallback to common interface names
            env_config["ZEEK_INTERFACE"] = "eth0"
            env_config["SURICATA_INTERFACE"] = "eth0"
            logger.warning("No recommended interface found, using eth0 as fallback")
        
        # Platform optimizations
        optimizations = self.platform_config.get("optimizations", {})
        
        if optimizations.get("performance_mode") == "maximum":
            env_config["ZEEK_PERFORMANCE_MODE"] = "maximum"
            env_config["SURICATA_THREADS"] = str(self.platform_config["hardware"]["cpu_count"])
            env_config["KITNET_BATCH_SIZE"] = "1000"
        elif optimizations.get("performance_mode") == "high":
            env_config["ZEEK_PERFORMANCE_MODE"] = "high"
            env_config["SURICATA_THREADS"] = str(max(2, self.platform_config["hardware"]["cpu_count"] // 2))
            env_config["KITNET_BATCH_SIZE"] = "500"
        else:
            env_config["ZEEK_PERFORMANCE_MODE"] = "balanced"
            env_config["SURICATA_THREADS"] = "2"
            env_config["KITNET_BATCH_SIZE"] = "100"
        
        # Security constraints
        security_constraints = optimizations.get("security_constraints", [])
        if "selinux" in security_constraints:
            env_config["SELINUX_ENABLED"] = "true"
            env_config["DOCKER_SECURITY_OPT"] = "--security-opt label=type:container_runtime_t"
        
        # Docker networking configuration
        if self.platform_config["docker"]["host_networking_supported"]:
            env_config["USE_HOST_NETWORKING"] = "true"
        else:
            env_config["USE_HOST_NETWORKING"] = "false"
            logger.warning("Host networking not supported, using bridge networking")
        
        # Memory optimizations
        memory_info = self.platform_config["hardware"]["memory_info"]
        if memory_info:
            try:
                memory_gb = float(memory_info.split()[0])
                if memory_gb >= 8:
                    env_config["ZEEK_MEMORY_LIMIT"] = "2g"
                    env_config["SURICATA_MEMORY_LIMIT"] = "1g"
                    env_config["KITNET_MEMORY_LIMIT"] = "2g"
                elif memory_gb >= 4:
                    env_config["ZEEK_MEMORY_LIMIT"] = "1g"
                    env_config["SURICATA_MEMORY_LIMIT"] = "512m"
                    env_config["KITNET_MEMORY_LIMIT"] = "1g"
                else:
                    env_config["ZEEK_MEMORY_LIMIT"] = "512m"
                    env_config["SURICATA_MEMORY_LIMIT"] = "256m"
                    env_config["KITNET_MEMORY_LIMIT"] = "512m"
            except (ValueError, IndexError):
                logger.warning("Could not parse memory information")
        
        # Platform-specific paths
        if "arch" in self.platform_config["platform"]["distribution"].lower():
            env_config["ZEEK_CONFIG_PATH"] = "/etc/zeek"
            env_config["SURICATA_CONFIG_PATH"] = "/etc/suricata"
        elif "ubuntu" in self.platform_config["platform"]["distribution"].lower():
            env_config["ZEEK_CONFIG_PATH"] = "/opt/zeek/etc"
            env_config["SURICATA_CONFIG_PATH"] = "/etc/suricata"
        else:
            env_config["ZEEK_CONFIG_PATH"] = "/opt/zeek/etc"
            env_config["SURICATA_CONFIG_PATH"] = "/etc/suricata"
        
        # Write to file if path provided
        if output_path:
            self._write_env_file(env_config, output_path)
        
        return env_config
    
    def generate_docker_compose_config(self) -> dict[str, Any]:
        """Generate Docker Compose configuration based on platform"""
        
        # Base services configuration
        config = {
            "version": "3.8",
            "services": {}
        }
        
        # Networking configuration
        if self.platform_config["docker"]["host_networking_supported"]:
            # Use host networking for packet capture services
            network_config = {"network_mode": "host"}
        else:
            # Fallback to bridge with privileged mode
            network_config = {
                "privileged": True,
                "networks": ["sentry-network"]
            }
            config["networks"] = {
                "sentry-network": {
                    "driver": "bridge",
                    "ipam": {"config": [{"subnet": "172.20.0.0/24"}]}
                }
            }
        
        # Memory limits based on available hardware
        memory_limits = self._get_memory_limits()
        
        # Generate service configurations
        services = {
            "zeek": {
                "build": {"context": "./services/zeek", "dockerfile": "Dockerfile"},
                "container_name": "cardea-zeek",
                "volumes": [
                    "./data/zeek:/opt/zeek/logs",
                    "./config/zeek:/opt/zeek/etc:ro"
                ],
                "environment": [
                    "ZEEK_INTERFACE=${ZEEK_INTERFACE}",
                    "LOG_LEVEL=${LOG_LEVEL}",
                    "ZEEK_PERFORMANCE_MODE=${ZEEK_PERFORMANCE_MODE}"
                ],
                "cap_add": ["NET_ADMIN", "NET_RAW"],
                "restart": "unless-stopped",
                "depends_on": ["bridge"],
                **network_config
            },
            "suricata": {
                "build": {"context": "./services/suricata", "dockerfile": "Dockerfile"},
                "container_name": "cardea-suricata", 
                "volumes": [
                    "./data/suricata:/var/log/suricata",
                    "./config/suricata:/etc/suricata:ro"
                ],
                "environment": [
                    "SURICATA_INTERFACE=${SURICATA_INTERFACE}",
                    "LOG_LEVEL=${LOG_LEVEL}",
                    "SURICATA_THREADS=${SURICATA_THREADS}"
                ],
                "cap_add": ["NET_ADMIN", "NET_RAW"],
                "restart": "unless-stopped",
                "depends_on": ["bridge"],
                **network_config
            }
        }
        
        # Add memory limits if available
        for service_name in services:
            if service_name in memory_limits:
                services[service_name]["mem_limit"] = memory_limits[service_name]
        
        config["services"] = services
        
        return config
    
    def _get_memory_limits(self) -> dict[str, str]:
        """Get memory limits based on available system memory"""
        limits = {}
        
        memory_info = self.platform_config["hardware"]["memory_info"]
        if memory_info:
            try:
                memory_gb = float(memory_info.split()[0])
                if memory_gb >= 8:
                    limits = {
                        "zeek": "2g",
                        "suricata": "1g", 
                        "kitnet": "2g",
                        "bridge": "512m"
                    }
                elif memory_gb >= 4:
                    limits = {
                        "zeek": "1g",
                        "suricata": "512m",
                        "kitnet": "1g", 
                        "bridge": "256m"
                    }
                else:
                    limits = {
                        "zeek": "512m",
                        "suricata": "256m",
                        "kitnet": "512m",
                        "bridge": "128m"
                    }
            except (ValueError, IndexError):  # Fall back to defaults if parsing fails
                pass
        
        return limits
    
    def _write_env_file(self, env_config: dict[str, str], output_path: Path):
        """Write environment configuration to file"""
        try:
            with open(output_path, 'w') as f:
                f.write("# Auto-generated environment configuration for Cardea Sentry\n")
                f.write(f"# Generated for: {self.platform_config['platform']['distribution']} "
                       f"{self.platform_config['platform']['system']}\n")
                f.write(f"# Platform: {self.platform_config['platform']['machine']}\n")
                f.write(f"# Recommended Interface: {self.platform_config['networking']['recommended_interface']}\n\n")
                
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
                    
            logger.info(f"Environment configuration written to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to write environment file: {e}")
    
    def generate_platform_report(self) -> str:
        """Generate human-readable platform report"""
        report = []
        
        report.append("🔍 CARDEA PLATFORM ANALYSIS REPORT")
        report.append("=" * 50)
        
        # Platform info
        platform = self.platform_config["platform"]
        report.append(f"Operating System: {platform['system']} {platform['release']}")
        report.append(f"Distribution: {platform['distribution']} {platform['distribution_version']}")
        report.append(f"Architecture: {platform['machine']}")
        
        # Hardware
        hardware = self.platform_config["hardware"]
        report.append(f"CPU Cores: {hardware['cpu_count']}")
        if hardware["memory_info"]:
            report.append(f"Memory: {hardware['memory_info']}")
        if hardware["disk_info"]:
            report.append(f"Disk: {hardware['disk_info']}")
        
        # Networking
        networking = self.platform_config["networking"]
        report.append(f"\nNetwork Interfaces:")
        for iface in networking["available_interfaces"]:
            status = "✅" if iface["state"] == "up" else "❌"
            report.append(f"  {status} {iface['name']} ({iface['type']}) - {iface['state']}")
        
        if networking["recommended_interface"]:
            report.append(f"Recommended Interface: {networking['recommended_interface']}")
        
        # Docker
        docker = self.platform_config["docker"]
        if docker["available"]:
            report.append(f"\nDocker: ✅ Available ({docker['version']})")
            report.append(f"Runtime: {docker['runtime']}")
            report.append(f"Host Networking: {'✅ Supported' if docker['host_networking_supported'] else '❌ Not Supported'}")
        else:
            report.append(f"\nDocker: ❌ Not Available")
        
        # Validation
        validation = self.validation
        report.append(f"\nDeployment Readiness: {'✅ READY' if validation['ready'] else '❌ NOT READY'}")
        
        if validation["errors"]:
            report.append("Errors:")
            for error in validation["errors"]:
                report.append(f"  ❌ {error}")
        
        if validation["warnings"]:
            report.append("Warnings:")
            for warning in validation["warnings"]:
                report.append(f"  ⚠️  {warning}")
        
        if validation["recommendations"]:
            report.append("Recommendations:")
            for rec in validation["recommendations"]:
                report.append(f"  💡 {rec}")
        
        # Optimizations
        optimizations = self.platform_config["optimizations"]
        report.append(f"\nOptimizations:")
        report.append(f"  Performance Mode: {optimizations['performance_mode']}")
        report.append(f"  Packet Capture: {optimizations['packet_capture_method']}")
        report.append(f"  Parallel Processing: {'✅' if optimizations.get('parallel_processing') else '❌'}")
        
        return "\n".join(report)