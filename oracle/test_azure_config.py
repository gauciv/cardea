#!/usr/bin/env python3
"""
Test Azure Authentication Configuration
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

# Test Azure Auth Service
try:
    from azure_auth import AzureAuthService
    
    print("=" * 60)
    print("AZURE AUTHENTICATION CONFIGURATION TEST")
    print("=" * 60)
    
    service = AzureAuthService()
    
    print(f"\n✓ Service initialized")
    print(f"  - Enabled: {service.enabled}")
    print(f"  - Client ID: {service.client_id[:20]}...")
    print(f"  - Tenant ID: {service.tenant_id[:20]}...")
    print(f"  - Authority: {service.authority}")
    print(f"  - JWKS URI: {service.jwks_uri}")
    print(f"  - Token Issuer: {service.token_issuer}")
    print(f"  - API Scope: {service.api_scope}")
    
    if service.is_enabled():
        print(f"\n✅ Azure authentication is ENABLED and configured")
    else:
        print(f"\n❌ Azure authentication is DISABLED or misconfigured")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
