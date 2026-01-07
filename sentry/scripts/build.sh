#!/bin/bash
# Optimized build script for Cardea Sentry
# Uses Docker BuildKit for faster, parallel builds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTRY_DIR="$(dirname "$SCRIPT_DIR")"

cd "$SENTRY_DIR"

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Parse arguments
PARALLEL=true
NO_CACHE=false
SERVICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --sequential)
            PARALLEL=false
            shift
            ;;
        *)
            SERVICE="$1"
            shift
            ;;
    esac
done

echo "🔨 Cardea Sentry Build"
echo "======================"
echo "BuildKit: enabled"
echo "Parallel: $PARALLEL"
echo "No-cache: $NO_CACHE"
echo ""

# Build command
BUILD_CMD="docker compose build"

if [[ "$NO_CACHE" == true ]]; then
    BUILD_CMD="$BUILD_CMD --no-cache"
fi

if [[ "$PARALLEL" == true ]]; then
    BUILD_CMD="$BUILD_CMD --parallel"
fi

if [[ -n "$SERVICE" ]]; then
    BUILD_CMD="$BUILD_CMD $SERVICE"
fi

echo "Command: $BUILD_CMD"
echo ""

# Time the build
START_TIME=$(date +%s)

$BUILD_CMD

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "✅ Build completed in ${DURATION}s"
echo ""

# Show image sizes
echo "📦 Image sizes:"
docker images | grep -E "^cardea|^sentry" | head -10 || \
docker images | grep -E "cardea-|sentry-" | head -10 || \
docker compose images
