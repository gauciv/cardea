#!/usr/bin/env python3
"""
Cardea Sentry Runtime Validation
Tests if the application can actually run independently
"""

import sys
from pathlib import Path

def test_platform_detection():
    """Test platform detection capabilities"""
    print("🔍 Testing Platform Detection...")
    
    try:
        sys.path.insert(0, str(Path("/workspaces/cardea").absolute()))
        from shared.utils.platform_detector import PlatformDetector
        
        detector = PlatformDetector()
        print(f"  ✅ OS: {detector.get_os_info()['name']}")
        print(f"  ✅ Network Interfaces: {len(detector.get_network_interfaces())} found")
        print(f"  ✅ Docker Available: {detector.is_docker_available()}")
        return True
        
    except Exception as e:
        print(f"  ❌ Platform detection failed: {e}")
        return False

def test_docker_environment():
    """Test Docker environment setup"""
    print("🐳 Testing Docker Environment...")
    
    try:
        # Check if docker-compose file exists
        compose_file = Path("/workspaces/cardea/sentry/docker-compose.yml")
        if not compose_file.exists():
            print("  ❌ docker-compose.yml not found")
            return False
            
        print("  ✅ Docker Compose configuration found")
        
        # Check if we can validate the compose file
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "config"], 
            capture_output=True, text=True, cwd="/workspaces/cardea/sentry"
        )
        
        if result.returncode == 0:
            print("  ✅ Docker Compose configuration is valid")
        else:
            print(f"  ⚠️  Docker Compose validation warning: {result.stderr}")
            
        return True
        
    except Exception as e:
        print(f"  ❌ Docker environment test failed: {e}")
        return False

def test_service_configurations():
    """Test if service configurations exist"""
    print("⚙️  Testing Service Configurations...")
    
    configs = [
        "/workspaces/cardea/sentry/services/zeek/config/node.cfg",
        "/workspaces/cardea/sentry/services/zeek/config/zeek.cfg", 
        "/workspaces/cardea/sentry/services/suricata/config/suricata.yaml",
        "/workspaces/cardea/sentry/services/kitnet/src/network_monitor.py",
        "/workspaces/cardea/sentry/bridge/src/bridge_service.py"
    ]
    
    all_exist = True
    for config_path in configs:
        if Path(config_path).exists():
            print(f"  ✅ {Path(config_path).name}")
        else:
            print(f"  ❌ {Path(config_path).name} missing")
            all_exist = False
            
    return all_exist

def test_python_dependencies():
    """Test if Python dependencies are importable"""
    print("🐍 Testing Python Dependencies...")
    
    dependencies = [
        ("fastapi", "FastAPI"),
        ("asyncio", "asyncio"),
        ("aiohttp", "aiohttp"),
        ("logging", "logging"),
        ("pathlib", "pathlib"),
        ("json", "json")
    ]
    
    all_available = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} not available")
            all_available = False
            
    return all_available

def test_bridge_service():
    """Test if Bridge service can be imported and initialized"""
    print("🌉 Testing Bridge Service...")
    
    try:
        sys.path.insert(0, str(Path("/workspaces/cardea/sentry/bridge/src").absolute()))
        from bridge_service import BridgeService
        
        # Try to create instance (don't start it) - verifies import works
        BridgeService()
        
    except Exception as e:
        print(f"  ❌ Bridge service test failed: {e}")
        return False

def test_kitnet_service():
    """Test if KitNET service can be imported"""
    print("🔬 Testing KitNET Service...")
    
    try:
        sys.path.insert(0, str(Path("/workspaces/cardea/sentry/services/kitnet/src").absolute()))
        from network_monitor import NetworkMonitor
        
        # NetworkMonitor takes no arguments in __init__ - verifies import works
        NetworkMonitor()
        
    except Exception as e:
        print(f"  ❌ KitNET service test failed: {e}")
        return False

def main():
    """Run all runtime validation tests"""
    print("🧪 CARDEA SENTRY - Runtime Validation Tests")
    print("=" * 50)
    
    tests = [
        ("Platform Detection", test_platform_detection),
        ("Docker Environment", test_docker_environment), 
        ("Service Configurations", test_service_configurations),
        ("Python Dependencies", test_python_dependencies),
        ("Bridge Service", test_bridge_service),
        ("KitNET Service", test_kitnet_service)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  ⚠️  {test_name} needs attention")
    
    print("\n" + "=" * 50)
    print(f"🏁 VALIDATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ Application appears ready to run independently!")
        return True
    elif passed >= total * 0.8:  # 80% pass rate
        print("⚠️  Application mostly ready - minor fixes needed")
        return True  
    else:
        print("❌ Application needs significant work before it can run")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)