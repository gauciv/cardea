#!/bin/bash
# Suricata service entrypoint script
# Supports: Live capture, PCAP replay, or offline mode

set -e

echo "🛡️ Starting Suricata intrusion detection service..."
echo "MODE: ${SURICATA_MODE:-live}"
echo "INTERFACE: ${SURICATA_INTERFACE:-auto}"
echo "PCAP_FILE: ${SURICATA_PCAP:-not set}"

# Create necessary directories
mkdir -p /var/log/suricata /var/lib/suricata/rules /etc/suricata

# Determine the running mode
SURICATA_MODE="${SURICATA_MODE:-live}"

# --- SETUP CONFIGURATION ---
# Use our custom config if available, otherwise copy system default
if [ -f "/etc/suricata/custom/suricata.yaml" ]; then
    echo "📋 Using custom Cardea configuration"
    cp /etc/suricata/custom/suricata.yaml /etc/suricata/suricata.yaml
elif [ ! -f "/etc/suricata/suricata.yaml" ]; then
    echo "📋 Using system default configuration"
    # Suricata should have a default config from apt install
fi

# Copy custom rules if available
if [ -d "/etc/suricata/custom/rules" ]; then
    echo "📋 Loading custom rules..."
    cp -r /etc/suricata/custom/rules/* /var/lib/suricata/rules/ 2>/dev/null || true
fi

# Copy threshold config if available
if [ -f "/etc/suricata/custom/threshold.config" ]; then
    echo "📋 Loading threshold configuration..."
    cp /etc/suricata/custom/threshold.config /etc/suricata/threshold.config
fi

# --- UPDATE RULES ---
echo "📡 Updating Suricata rule sets..."
suricata-update --no-test || echo "⚠️ Rule update failed, continuing with existing rules"

# Ensure local.rules is loaded if it exists
if [ -f "/var/lib/suricata/rules/local.rules" ]; then
    echo "📋 Custom local.rules found and will be loaded"
fi

# --- PCAP REPLAY MODE ---
if [ "$SURICATA_MODE" = "pcap" ] && [ -f "$SURICATA_PCAP" ]; then
    echo "📼 PCAP replay mode - processing: $SURICATA_PCAP"
    
    # Start log processor in background
    python3 /app/scripts/log_processor.py &
    LOG_PROCESSOR_PID=$!
    
    # Run Suricata on PCAP
    suricata -c /etc/suricata/suricata.yaml -r "$SURICATA_PCAP" -l /var/log/suricata
    
    echo "✅ PCAP processing complete. Logs generated:"
    ls -la /var/log/suricata/
    
    # Give log processor time to finish
    sleep 5
    
    # Keep container alive for log access
    echo "🔄 PCAP processing done. Container staying alive for log access..."
    tail -f /dev/null

# --- OFFLINE/IDLE MODE ---
elif [ "$SURICATA_MODE" = "offline" ]; then
    echo "💤 Offline mode - Suricata container ready but not capturing"
    echo "   Use SURICATA_MODE=live or SURICATA_MODE=pcap to enable detection"
    
    # Create health status file
    while true; do
        echo "$(date): Suricata idle - ready to start" > /var/log/suricata/status.log
        sleep 30
    done

# --- LIVE CAPTURE MODE (default) ---
else
    echo "🌐 Live capture mode - starting intrusion detection"
    
    # Auto-detect interface if not specified OR if specified interface doesn't exist
    if [ -z "$SURICATA_INTERFACE" ] || [ "$SURICATA_INTERFACE" = "auto" ] || ! ip link show "$SURICATA_INTERFACE" >/dev/null 2>&1; then
        if [ -n "$SURICATA_INTERFACE" ] && [ "$SURICATA_INTERFACE" != "auto" ]; then
            echo "⚠️ Configured interface '$SURICATA_INTERFACE' not found, auto-detecting..."
        fi
        
        # Look for first non-loopback interface that's UP (exclude docker/veth interfaces)
        DETECTED=$(ip -o link show | grep -v 'lo:' | grep -v 'docker' | grep -v 'veth' | grep -v 'br-' | grep 'state UP' | head -1 | awk -F': ' '{print $2}')
        
        if [ -n "$DETECTED" ]; then
            export SURICATA_INTERFACE="$DETECTED"
            echo "✅ Auto-detected interface: $SURICATA_INTERFACE"
        else
            # Fallback: any interface that's not loopback/docker/veth
            DETECTED=$(ip -o link show | grep -v 'lo:' | grep -v 'docker' | grep -v 'veth' | grep -v 'br-' | head -1 | awk -F': ' '{print $2}')
            if [ -n "$DETECTED" ]; then
                export SURICATA_INTERFACE="$DETECTED"
                echo "⚠️ Using first available interface: $SURICATA_INTERFACE"
            else
                echo "❌ No network interfaces found"
                echo "💡 Options:"
                echo "   1. Run container with --network=host"
                echo "   2. Use SURICATA_MODE=pcap with SURICATA_PCAP=/path/to/file.pcap"
                echo "   3. Use SURICATA_MODE=offline for testing"
                
                # Switch to offline mode
                export SURICATA_MODE="offline"
                exec "$0"
            fi
        fi
    else
        echo "✅ Using configured interface: $SURICATA_INTERFACE"
    fi
    
    # Verify interface exists (should always pass now since we check above)
    if ! ip link show "$SURICATA_INTERFACE" >/dev/null 2>&1; then
        echo "❌ Interface $SURICATA_INTERFACE not found"
        echo "   Available interfaces:"
        ip -o link show | awk -F': ' '{print "   - " $2}'
        exit 1
    fi
    
    echo "📡 Interface: $SURICATA_INTERFACE"
    echo "📂 Logs: /var/log/suricata"
    echo "📋 Config: /etc/suricata/suricata.yaml"
    
    # Update config with correct interface
    if [ -f "/etc/suricata/suricata.yaml" ]; then
        sed -i "s/interface: default/interface: $SURICATA_INTERFACE/g" /etc/suricata/suricata.yaml
    fi
    
    # Start log processor in background
    echo "🔄 Starting EVE log processor..."
    python3 /app/scripts/log_processor.py &
    LOG_PROCESSOR_PID=$!
    
    echo "🚀 Starting Suricata..."
    
    # Run Suricata with AF_PACKET (high performance)
    exec suricata -c /etc/suricata/suricata.yaml --af-packet="$SURICATA_INTERFACE" \
        --pidfile /var/run/suricata.pid \
        -D -vvv 2>&1 | tee -a /var/log/suricata/suricata.log &
    
    SURICATA_PID=$!
    
    # Wait for Suricata to start
    sleep 3
    
    if pgrep -f "suricata" > /dev/null; then
        echo "✅ Suricata running (PID: $SURICATA_PID)"
        echo "✅ Log processor running (PID: $LOG_PROCESSOR_PID)"
    else
        echo "❌ Suricata failed to start"
        cat /var/log/suricata/suricata.log
        exit 1
    fi
    
    # Keep container running and monitor
    while true; do
        if ! pgrep -f "suricata" > /dev/null; then
            echo "⚠️ Suricata process died, restarting..."
            exec "$0"
        fi
        sleep 30
    done
fi