#!/bin/bash
# Zeek service entrypoint script
# Supports: Live capture, PCAP replay, or offline mode

set -e

echo "🔍 Starting Zeek network analysis service..."
echo "MODE: ${ZEEK_MODE:-live}"
echo "INTERFACE: ${ZEEK_INTERFACE:-auto}"
echo "PCAP_FILE: ${ZEEK_PCAP:-not set}"

# Create necessary directories
mkdir -p /opt/zeek/logs/current /opt/zeek/logs/archive /tmp/cardea/zeek

# Determine the running mode
ZEEK_MODE="${ZEEK_MODE:-live}"

# --- PCAP REPLAY MODE ---
# Best for development/testing - replays recorded traffic
if [ "$ZEEK_MODE" = "pcap" ] && [ -f "$ZEEK_PCAP" ]; then
    echo "📼 PCAP replay mode - processing: $ZEEK_PCAP"
    
    cd /opt/zeek/logs/current
    /opt/zeek/bin/zeek -r "$ZEEK_PCAP" /opt/zeek/share/zeek/site/local.zeek
    
    echo "✅ PCAP processing complete. Logs generated:"
    ls -la /opt/zeek/logs/current/
    
    # Keep container alive for log access
    echo "🔄 PCAP processing done. Container staying alive for log access..."
    tail -f /dev/null

# --- OFFLINE/IDLE MODE ---
# Container is up but not processing - for testing container health only
elif [ "$ZEEK_MODE" = "offline" ]; then
    echo "💤 Offline mode - Zeek container ready but not capturing"
    echo "   Use ZEEK_MODE=live or ZEEK_MODE=pcap to enable analysis"
    
    # Create health status file
    while true; do
        echo "$(date): Zeek idle - ready to start" > /tmp/cardea/zeek/status.log
        sleep 30
    done

# --- LIVE CAPTURE MODE (default) ---
else
    echo "🌐 Live capture mode - attempting network monitoring"
    
    # Auto-detect interface if not specified, set to "auto", or if specified interface doesn't exist
    if [ -z "$ZEEK_INTERFACE" ] || [ "$ZEEK_INTERFACE" = "auto" ] || ! ip link show "$ZEEK_INTERFACE" >/dev/null 2>&1; then
        if [ -n "$ZEEK_INTERFACE" ] && [ "$ZEEK_INTERFACE" != "auto" ]; then
            echo "⚠️ Configured interface '$ZEEK_INTERFACE' not found, auto-detecting..."
        fi
        
        # Look for first non-loopback interface (exclude docker/veth interfaces)
        DETECTED=$(ip -o link show | grep -v 'lo:' | grep -v 'docker' | grep -v 'veth' | grep -v 'br-' | grep 'state UP' | head -1 | awk -F': ' '{print $2}')
        
        if [ -n "$DETECTED" ]; then
            export ZEEK_INTERFACE="$DETECTED"
            echo "✅ Auto-detected interface: $ZEEK_INTERFACE"
        else
            # Fallback: any interface that's not loopback/docker/veth
            DETECTED=$(ip -o link show | grep -v 'lo:' | grep -v 'docker' | grep -v 'veth' | grep -v 'br-' | head -1 | awk -F': ' '{print $2}')
            if [ -n "$DETECTED" ]; then
                export ZEEK_INTERFACE="$DETECTED"
                echo "⚠️  Using first available interface: $ZEEK_INTERFACE"
            else
                echo "❌ No network interfaces found"
                echo "💡 Options:"
                echo "   1. Run container with --network=host"
                echo "   2. Use ZEEK_MODE=pcap with ZEEK_PCAP=/path/to/file.pcap"
                echo "   3. Use ZEEK_MODE=offline for testing"
                
                # Switch to offline mode instead of failing
                echo "🔄 Switching to offline mode..."
                export ZEEK_MODE=offline
                exec "$0"  # Re-run in offline mode
            fi
        fi
    else
        echo "✅ Using configured interface: $ZEEK_INTERFACE"
    fi
    
    # Verify interface exists (should always pass now since we check above)
    if ! ip link show "$ZEEK_INTERFACE" >/dev/null 2>&1; then
        echo "❌ Interface $ZEEK_INTERFACE not found"
        exit 1
    fi
    
    echo "📡 Interface: $ZEEK_INTERFACE"
    echo "📂 Logs: /opt/zeek/logs/current"
    
    # Set working directory for log output
    cd /opt/zeek/logs/current
    
    # Start Zeek in standalone mode with full local.zeek config
    echo "🚀 Starting Zeek..."
    exec /opt/zeek/bin/zeek -i "$ZEEK_INTERFACE" /opt/zeek/share/zeek/site/local.zeek
fi