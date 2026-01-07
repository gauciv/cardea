#!/bin/bash
# Cardea Sentry Log Cleanup Script
# Run this periodically to prevent disk exhaustion
# Usage: ./cleanup-logs.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTRY_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$SENTRY_DIR/data"

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No files will be deleted"
fi

echo "🧹 Cardea Sentry Log Cleanup"
echo "============================"
echo ""

# Calculate current usage
echo "📊 Current disk usage:"
du -sh "$DATA_DIR"/* 2>/dev/null || echo "No data directories found"
echo ""

# Suricata logs (the biggest offender - can grow to 68GB+!)
SURICATA_DIR="$DATA_DIR/suricata"
if [[ -d "$SURICATA_DIR" ]]; then
    SURICATA_SIZE=$(du -sh "$SURICATA_DIR" 2>/dev/null | cut -f1)
    echo "🛡️  Suricata logs: $SURICATA_SIZE"
    
    # Delete logs older than 1 day
    OLD_FILES=$(find "$SURICATA_DIR" -type f -mtime +1 2>/dev/null | wc -l)
    echo "   Files older than 1 day: $OLD_FILES"
    
    if [[ "$DRY_RUN" == false ]] && [[ $OLD_FILES -gt 0 ]]; then
        find "$SURICATA_DIR" -type f -mtime +1 -delete
        echo "   ✅ Deleted old Suricata logs"
    fi
    
    # Also delete EVE JSON files larger than 1GB
    LARGE_FILES=$(find "$SURICATA_DIR" -type f -size +1G 2>/dev/null | wc -l)
    if [[ $LARGE_FILES -gt 0 ]]; then
        echo "   Large files (>1GB): $LARGE_FILES"
        if [[ "$DRY_RUN" == false ]]; then
            find "$SURICATA_DIR" -type f -size +1G -delete
            echo "   ✅ Deleted large Suricata files"
        fi
    fi
fi

# Zeek logs
ZEEK_DIR="$DATA_DIR/zeek"
if [[ -d "$ZEEK_DIR" ]]; then
    ZEEK_SIZE=$(du -sh "$ZEEK_DIR" 2>/dev/null | cut -f1)
    echo "🔍 Zeek logs: $ZEEK_SIZE"
    
    OLD_FILES=$(find "$ZEEK_DIR" -type f -mtime +1 2>/dev/null | wc -l)
    echo "   Files older than 1 day: $OLD_FILES"
    
    if [[ "$DRY_RUN" == false ]] && [[ $OLD_FILES -gt 0 ]]; then
        find "$ZEEK_DIR" -type f -mtime +1 -delete
        echo "   ✅ Deleted old Zeek logs"
    fi
fi

# KitNET data
KITNET_DIR="$DATA_DIR/kitnet"
if [[ -d "$KITNET_DIR" ]]; then
    KITNET_SIZE=$(du -sh "$KITNET_DIR" 2>/dev/null | cut -f1)
    echo "🧠 KitNET data: $KITNET_SIZE"
fi

# Bridge data
BRIDGE_DIR="$DATA_DIR/bridge"
if [[ -d "$BRIDGE_DIR" ]]; then
    BRIDGE_SIZE=$(du -sh "$BRIDGE_DIR" 2>/dev/null | cut -f1)
    echo "🌉 Bridge data: $BRIDGE_SIZE"
fi

echo ""

# Docker cleanup
echo "🐳 Docker cleanup..."
if [[ "$DRY_RUN" == false ]]; then
    docker system prune -f --volumes 2>/dev/null || echo "   Docker not available or already clean"
else
    echo "   Would run: docker system prune -f --volumes"
fi

echo ""
echo "📊 After cleanup:"
du -sh "$DATA_DIR"/* 2>/dev/null || echo "No data directories"
echo ""
echo "✅ Cleanup complete!"
