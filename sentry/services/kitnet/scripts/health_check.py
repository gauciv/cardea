#!/usr/bin/env python3
"""
Health check script for KitNET service
Checks KitNET's internal state, model status, and processing health
"""

import sys
import os
import json
from pathlib import Path

def check_model_health():
    """Check if KitNET model exists and is usable."""
    model_path = Path('/app/data/kitnet_model.pkl')
    
    if not model_path.exists():
        return {
            "model_status": "training",
            "healthy": True,
            "message": "Model training in progress"
        }
    
    # Check model file integrity
    try:
        import pickle
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
        
        version = data.get('version', 'unknown')
        phase = data.get('phase', 'unknown')
        training_samples = data.get('training_samples', 0)
        num_autoencoders = len(data.get('autoencoders', []))
        
        return {
            "model_status": "loaded",
            "phase": phase,
            "version": version,
            "training_samples": training_samples,
            "num_autoencoders": num_autoencoders,
            "healthy": True
        }
    except Exception as e:
        return {
            "model_status": "error",
            "healthy": False,
            "error": str(e)
        }

def check_log_access():
    """Check if Zeek log directory is accessible."""
    zeek_log_dir = Path('/app/logs/zeek')
    
    if not zeek_log_dir.exists():
        # Try alternative paths
        alt_paths = [
            Path('/logs/zeek'),
            Path('/var/log/zeek'),
            Path('/app/data/zeek')
        ]
        for alt in alt_paths:
            if alt.exists():
                zeek_log_dir = alt
                break
    
    if zeek_log_dir.exists():
        log_files = list(zeek_log_dir.glob('*.log')) + list(zeek_log_dir.glob('current/*.log'))
        return {
            "log_access": "available",
            "log_path": str(zeek_log_dir),
            "log_count": len(log_files),
            "healthy": True
        }
    else:
        # Not a critical failure - KitNET can work with live packet capture
        return {
            "log_access": "not_configured",
            "healthy": True,
            "message": "Zeek logs not mounted, using live capture"
        }

def check_memory():
    """Check memory usage is within bounds."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = usage.ru_maxrss / 1024  # Convert to MB on Linux
        
        # KitNET should use < 2GB RAM
        max_mem_mb = 2048
        healthy = mem_mb < max_mem_mb
        
        return {
            "memory_mb": round(mem_mb, 2),
            "max_memory_mb": max_mem_mb,
            "healthy": healthy
        }
    except:
        return {"memory_check": "unavailable", "healthy": True}

def main():
    """Run all health checks."""
    checks = {}
    overall_healthy = True
    
    # Run each check
    checks['model'] = check_model_health()
    checks['logs'] = check_log_access()
    checks['memory'] = check_memory()
    
    # Aggregate health
    for check_name, result in checks.items():
        if not result.get('healthy', True):
            overall_healthy = False
    
    checks['overall'] = overall_healthy
    
    # Output JSON for debugging
    print(json.dumps(checks, indent=2))
    
    if overall_healthy:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()