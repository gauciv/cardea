"""
Action Execution API
Handles user decisions and executes commands on Sentry devices
"""

import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

# Safeguarded command whitelist - ONLY these commands can be executed
ALLOWED_COMMANDS = {
    "block_ip": "iptables -A INPUT -s {target} -j DROP",
    "unblock_ip": "iptables -D INPUT -s {target} -j DROP",
    "list_blocked": "iptables -L INPUT -n | grep DROP",
    "restart_monitoring": "systemctl restart zeek suricata",
    "get_status": "systemctl status zeek suricata --no-pager",
}

# Commands that require extra confirmation
DANGEROUS_COMMANDS = {"block_ip", "unblock_ip", "restart_monitoring"}


class ActionType(str, Enum):
    BLOCK_IP = "block_ip"
    ALLOW_IP = "allow_ip"  # Maps to unblock_ip
    DISMISS = "dismiss"
    MONITOR = "monitor"
    LOCKDOWN = "lockdown"


class ActionRequest(BaseModel):
    action_type: ActionType
    target: Optional[str] = None  # IP address, alert ID, etc.
    alert_ids: Optional[list[int]] = None  # Related alerts to update
    reason: Optional[str] = None  # User's reason for the action
    device_id: Optional[str] = None  # Which Sentry to execute on


class ActionResult(BaseModel):
    success: bool
    action_type: str
    message: str
    executed_at: str
    details: Optional[dict] = None


# In-memory store for dismissed alerts (in production, use database)
dismissed_alerts: set[int] = set()
safe_ips: set[str] = set()


async def update_threat_resolution(target: str, action_type: str, reason: str):
    """Update threat resolution in Azure AI Search for future RAG queries"""
    try:
        from api.analytics import analyzer
        if analyzer.search_service and analyzer.search_service.search_client:
            # Search for threats matching this target
            results = await analyzer.search_service.search_similar_threats(
                query=target,
                top=5,
                min_score=0.3
            )
            
            for threat in results:
                if target in str(threat.get("indicators", [])) or target in str(threat.get("network_context", {})):
                    # Update with resolution
                    resolution = f"User marked as {action_type}: {reason}" if reason else f"User action: {action_type}"
                    threat["resolution"] = resolution
                    await analyzer.search_service.index_threat(threat)
                    logger.info(f"📝 Updated threat resolution: {threat.get('threat_id')}")
    except Exception as e:
        logger.warning(f"Could not update threat resolution: {e}")


@router.post("/execute", response_model=ActionResult)
async def execute_action(request: ActionRequest):
    """
    Execute a user-requested action with safety checks
    """
    now = datetime.now(timezone.utc)
    
    # Validate IP format if target is provided
    if request.target and request.action_type in [ActionType.BLOCK_IP, ActionType.ALLOW_IP]:
        if not _is_valid_ip(request.target):
            raise HTTPException(status_code=400, detail=f"Invalid IP address: {request.target}")
        
        # Prevent blocking critical IPs
        if _is_protected_ip(request.target):
            raise HTTPException(status_code=403, detail=f"Cannot block protected IP: {request.target}")
    
    try:
        if request.action_type == ActionType.DISMISS:
            # Mark alerts as safe/dismissed
            if request.alert_ids:
                dismissed_alerts.update(request.alert_ids)
            if request.target:
                safe_ips.add(request.target)
                # Update RAG with resolution
                await update_threat_resolution(request.target, "safe", request.reason or "User confirmed safe")
            
            return ActionResult(
                success=True,
                action_type=request.action_type,
                message="Marked as safe. I won't alert you about this activity again.",
                executed_at=now.isoformat(),
                details={"dismissed_alerts": list(request.alert_ids or []), "safe_ip": request.target}
            )
        
        elif request.action_type == ActionType.MONITOR:
            # Just acknowledge - continue monitoring without action
            return ActionResult(
                success=True,
                action_type=request.action_type,
                message="Got it! I'll keep watching and let you know if anything changes.",
                executed_at=now.isoformat(),
                details={"monitoring": request.target or "general"}
            )
        
        elif request.action_type == ActionType.BLOCK_IP:
            # Execute block command on Sentry
            result = await _execute_on_sentry(
                command_key="block_ip",
                target=request.target,
                device_id=request.device_id
            )
            
            if result["success"]:
                # Update RAG with resolution
                await update_threat_resolution(request.target, "blocked", request.reason or "User blocked IP")
                return ActionResult(
                    success=True,
                    action_type=request.action_type,
                    message=f"Done! I've blocked {request.target} from accessing your network.",
                    executed_at=now.isoformat(),
                    details=result
                )
            else:
                return ActionResult(
                    success=False,
                    action_type=request.action_type,
                    message=f"I couldn't block that IP right now. {result.get('error', 'Please try again.')}",
                    executed_at=now.isoformat(),
                    details=result
                )
        
        elif request.action_type == ActionType.ALLOW_IP:
            # Remove from blocked list
            result = await _execute_on_sentry(
                command_key="unblock_ip",
                target=request.target,
                device_id=request.device_id
            )
            safe_ips.add(request.target)
            
            return ActionResult(
                success=True,
                action_type=request.action_type,
                message=f"Unblocked {request.target} and marked as safe.",
                executed_at=now.isoformat(),
                details=result
            )
        
        elif request.action_type == ActionType.LOCKDOWN:
            # Emergency lockdown - block all external traffic
            raise HTTPException(
                status_code=403, 
                detail="Lockdown requires manual confirmation. Please contact your administrator."
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {request.action_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return ActionResult(
            success=False,
            action_type=request.action_type,
            message="Something went wrong. I'll keep monitoring while you try again.",
            executed_at=now.isoformat(),
            details={"error": str(e)}
        )


@router.get("/dismissed")
async def get_dismissed():
    """Get list of dismissed alerts and safe IPs"""
    return {
        "dismissed_alert_ids": list(dismissed_alerts),
        "safe_ips": list(safe_ips)
    }


@router.delete("/dismissed/{alert_id}")
async def undismiss_alert(alert_id: int):
    """Remove an alert from dismissed list"""
    dismissed_alerts.discard(alert_id)
    return {"success": True, "message": f"Alert {alert_id} will be monitored again"}


async def _execute_on_sentry(command_key: str, target: str = None, device_id: str = None) -> dict:
    """
    Execute a whitelisted command on Sentry device
    Uses HTTP API to send command - Sentry executes with proper permissions
    """
    if command_key not in ALLOWED_COMMANDS:
        return {"success": False, "error": f"Command not allowed: {command_key}"}
    
    # Build the command from template
    command_template = ALLOWED_COMMANDS[command_key]
    command = command_template.format(target=target) if target else command_template
    
    # Get Sentry URL (in production, look up by device_id)
    sentry_url = "http://sentry:8001"  # Default for docker-compose
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{sentry_url}/api/execute",
                json={
                    "command_key": command_key,
                    "target": target,
                    "requested_by": "oracle",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            if response.status_code == 200:
                return {"success": True, "output": response.json()}
            else:
                return {"success": False, "error": response.text}
                
    except httpx.ConnectError:
        logger.warning(f"Could not connect to Sentry at {sentry_url}")
        return {"success": False, "error": "Sentry device not reachable"}
    except Exception as e:
        logger.error(f"Sentry command execution failed: {e}")
        return {"success": False, "error": str(e)}


def _is_valid_ip(ip: str) -> bool:
    """Basic IP validation"""
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(p) <= 255 for p in parts)


def _is_protected_ip(ip: str) -> bool:
    """Check if IP is protected from blocking"""
    protected = {
        "127.0.0.1",  # Localhost
        "0.0.0.0",
        "255.255.255.255",
    }
    # Also protect private network gateways
    if ip.startswith("192.168.") and ip.endswith(".1"):
        return True
    if ip.startswith("10.") and ip.endswith(".1"):
        return True
    return ip in protected
