#!/usr/bin/env python3
"""
Platform Detection and Environment Configuration
Dynamic detection of host OS, network interfaces, and platform capabilities
"""

import os
import platform
import subprocess
import logging
from typing import Optional, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class PlatformDetector:
    """Detects host platform capabilities and configurations"""
    
    def __init__(self):
        self.os_info = self._detect_os()
        self.network_interfaces = self._detect_network_interfaces()
        self.docker_capabilities = self._detect_docker_capabilities()
        self.hardware_info = self._detect_hardware()
        
    def _detect_os(self) -> dict[str, str]:
        """Detect operating system and distribution"""
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "distribution": "unknown",
            "distribution_version": "unknown"
        }
        
        # Detect Linux distribution
        if os_info["system"] == "Linux":
            try:
                # Try /etc/os-release first (modern standard)
                if Path("/etc/os-release").exists():
                    with open("/etc/os-release", "r") as f:
                        for line in f:
                            if line.startswith("NAME="):
                                os_info["distribution"] = line.split("=")[1].strip().strip('"')
                            elif line.startswith("VERSION="):
                                os_info["distribution_version"] = line.split("=")[1].strip().strip('"')
                
                # Fallback to lsb_release
                elif subprocess.run(["which", "lsb_release"], capture_output=True).returncode == 0:
                    result = subprocess.run(["lsb_release", "-d"], capture_output=True, text=True)
                    if result.returncode == 0:
                        os_info["distribution"] = result.stdout.split(":")[1].strip()
                        
            except Exception as e:
                logger.warning(f"Could not detect Linux distribution: {e}")
        
        return os_info
    
    def _detect_network_interfaces(self) -> list[dict[str, Any]]:
        """Detect available network interfaces"""
        interfaces = []
        
        try:
            # Use ip command on Linux
            if self.os_info["system"] == "Linux":
                result = subprocess.run(
                    ["ip", "link", "show"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if result.returncode == 0:
                    interfaces = self._parse_ip_link_output(result.stdout)
            
            # Fallback to ifconfig if available
            if not interfaces:
                result = subprocess.run(
                    ["ifconfig", "-a"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if result.returncode == 0:
                    interfaces = self._parse_ifconfig_output(result.stdout)
            
        except Exception as e:
            logger.error(f"Error detecting network interfaces: {e}")
            
        return interfaces
    
    def _parse_ip_link_output(self, output: str) -> list[dict[str, Any]]:
        """Parse 'ip link show' output"""
        interfaces = []
        
        for line in output.split('\n'):
            if ': ' in line and not line.startswith(' '):
                parts = line.split(': ')
                if len(parts) >= 2:
                    iface_info = parts[1].split('@')[0]  # Remove @bridge info
                    interface = {
                        "name": iface_info,
                        "type": "unknown",
                        "state": "unknown"
                    }
                    
                    # Determine interface type
                    if iface_info.startswith(("eth", "enp", "ens")):
                        interface["type"] = "ethernet"
                    elif iface_info.startswith(("wlan", "wlp", "wifi")):
                        interface["type"] = "wireless"
                    elif iface_info == "lo":
                        interface["type"] = "loopback"
                    elif iface_info.startswith("docker"):
                        interface["type"] = "docker"
                    elif iface_info.startswith("br-"):
                        interface["type"] = "bridge"
                    
                    # Check if interface is up
                    if "UP" in line:
                        interface["state"] = "up"
                    elif "DOWN" in line:
                        interface["state"] = "down"
                    
                    interfaces.append(interface)
        
        return interfaces
    
    def _parse_ifconfig_output(self, output: str) -> list[dict[str, Any]]:
        """Parse ifconfig output as fallback"""
        interfaces = []
        
        for block in output.split('\n\n'):
            lines = block.split('\n')
            if lines and ':' in lines[0]:
                name = lines[0].split(':')[0]
                interface = {
                    "name": name,
                    "type": "unknown",
                    "state": "up" if "UP" in lines[0] else "down"
                }
                interfaces.append(interface)
        
        return interfaces
    
    def _detect_docker_capabilities(self) -> dict[str, Any]:
        """Detect Docker capabilities and configuration"""
        capabilities = {
            "available": False,
            "version": None,
            "host_networking_supported": False,
            "privileged_supported": False,
            "runtime": None
        }
        
        try:
            # Check if Docker is available
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                capabilities["available"] = True
                capabilities["version"] = result.stdout.strip()
                
                # Check Docker info
                result = subprocess.run(
                    ["docker", "info", "--format", "{{json .}}"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if result.returncode == 0:
                    try:
                        docker_info = json.loads(result.stdout)
                        capabilities["runtime"] = docker_info.get("DefaultRuntime", "unknown")
                        
                        # Host networking is typically available on Linux
                        if self.os_info["system"] == "Linux":
                            capabilities["host_networking_supported"] = True
                        
                        # Check if we can run privileged containers
                        capabilities["privileged_supported"] = True  # Assume yes unless we can't
                        
                    except json.JSONDecodeError:
                        logger.warning("Could not parse Docker info JSON")
                        
        except Exception as e:
            logger.warning(f"Docker not available or accessible: {e}")
        
        return capabilities
    
    def _detect_hardware(self) -> dict[str, Any]:
        """Detect hardware information"""
        hardware = {
            "cpu_count": os.cpu_count(),
            "memory_info": None,
            "disk_info": None
        }
        
        try:
            # Get memory info on Linux
            if self.os_info["system"] == "Linux" and Path("/proc/meminfo").exists():
                with open("/proc/meminfo", "r") as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if line.startswith("MemTotal:"):
                            # Convert kB to GB
                            kb = int(line.split()[1])
                            hardware["memory_info"] = f"{kb / 1024 / 1024:.1f} GB"
                            break
            
            # Get disk info
            result = subprocess.run(
                ["df", "-h", "/"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        hardware["disk_info"] = f"Total: {parts[1]}, Available: {parts[3]}"
                        
        except Exception as e:
            logger.warning(f"Could not detect hardware info: {e}")
        
        return hardware
    
    def get_recommended_interface(self) -> Optional[str]:
        """Get recommended network interface for monitoring"""
        # Filter out loopback and Docker interfaces
        suitable_interfaces = [
            iface for iface in self.network_interfaces
            if iface["type"] not in ["loopback", "docker", "bridge"] 
            and iface["state"] == "up"
        ]
        
        # Prefer ethernet over wireless
        ethernet_interfaces = [iface for iface in suitable_interfaces if iface["type"] == "ethernet"]
        if ethernet_interfaces:
            return ethernet_interfaces[0]["name"]
        
        # Fallback to wireless
        wireless_interfaces = [iface for iface in suitable_interfaces if iface["type"] == "wireless"]
        if wireless_interfaces:
            return wireless_interfaces[0]["name"]
        
        # Last resort - any suitable interface
        if suitable_interfaces:
            return suitable_interfaces[0]["name"]
        
        return None
    
    def get_platform_config(self) -> dict[str, Any]:
        """Generate platform-specific configuration"""
        config = {
            "platform": self.os_info,
            "networking": {
                "recommended_interface": self.get_recommended_interface(),
                "available_interfaces": self.network_interfaces,
                "host_networking_supported": self.docker_capabilities["host_networking_supported"]
            },
            "docker": self.docker_capabilities,
            "hardware": self.hardware_info,
            "optimizations": self._get_platform_optimizations()
        }
        
        return config
    
    def _get_platform_optimizations(self) -> dict[str, Any]:
        """Get platform-specific optimizations"""
        optimizations = {
            "packet_capture_method": "standard",
            "performance_mode": "balanced",
            "security_constraints": []
        }
        
        # Platform-specific optimizations
        distribution = self.os_info.get("distribution", "").lower()
        
        if "ubuntu" in distribution or "debian" in distribution:
            optimizations["packet_capture_method"] = "libpcap"
            optimizations["performance_mode"] = "high"
        elif "arch" in distribution:
            optimizations["packet_capture_method"] = "raw_socket"
            optimizations["performance_mode"] = "maximum"
        elif "centos" in distribution or "rhel" in distribution or "fedora" in distribution:
            optimizations["packet_capture_method"] = "libpcap"
            optimizations["performance_mode"] = "balanced"
            optimizations["security_constraints"].append("selinux")
        
        # Memory-based optimizations
        if self.hardware_info.get("cpu_count", 1) >= 4:
            optimizations["parallel_processing"] = True
        else:
            optimizations["parallel_processing"] = False
        
        return optimizations
    
    def validate_environment(self) -> dict[str, Any]:
        """Validate environment for Sentry deployment"""
        validation = {
            "ready": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check operating system
        if self.os_info["system"] != "Linux":
            validation["errors"].append(f"Unsupported OS: {self.os_info['system']}. Linux required for packet capture.")
            validation["ready"] = False
        
        # Check Docker
        if not self.docker_capabilities["available"]:
            validation["errors"].append("Docker not available. Required for Sentry services.")
            validation["ready"] = False
        
        # Check network interfaces
        if not self.get_recommended_interface():
            validation["warnings"].append("No suitable network interface found for monitoring.")
            validation["recommendations"].append("Ensure network interfaces are up and accessible.")
        
        # Check privileges
        if os.geteuid() != 0 and not self._can_capture_packets():
            validation["warnings"].append("May need elevated privileges for packet capture.")
            validation["recommendations"].append("Consider running with CAP_NET_RAW capability or as root.")
        
        # Platform-specific checks
        distribution = self.os_info.get("distribution", "").lower()
        if "centos" in distribution or "rhel" in distribution:
            validation["recommendations"].append("Check SELinux policies for Docker and network access.")
        
        return validation
    
    def _can_capture_packets(self) -> bool:
        """Check if current user can capture packets"""
        try:
            # Check for CAP_NET_RAW capability
            result = subprocess.run(
                ["capsh", "--print"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0 and "cap_net_raw" in result.stdout.lower():
                return True
                
        except OSError:  # Capability check is best-effort
            pass
        
        return False

# Global platform detector instance
platform_detector = PlatformDetector()

def get_platform_config() -> dict[str, Any]:
    """Get current platform configuration"""
    return platform_detector.get_platform_config()

def validate_deployment_environment() -> dict[str, Any]:
    """Validate environment for deployment"""
    return platform_detector.validate_environment()