# Suricata Intrusion Detection Service
# Note: Suricata is inherently large (~500MB+) due to rule databases and dependencies
# This is optimized as much as possible without breaking functionality

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# Install all dependencies in single layer, clean up aggressively
RUN apt-get update && apt-get install -y --no-install-recommends \
    suricata \
    suricata-update \
    curl \
    iproute2 \
    python3-minimal \
    python3-pip \
    python3-yaml \
    python3-requests \
    jq \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Create directories in single layer
RUN mkdir -p /var/log/suricata /var/lib/suricata/rules \
    /etc/suricata/custom /etc/suricata/custom/rules /app/scripts

# Copy configuration files
COPY config/suricata.yaml /etc/suricata/custom/
COPY config/threshold.config /etc/suricata/custom/
COPY config/rules/ /etc/suricata/custom/rules/

# Copy scripts and set permissions in single layer
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py 2>/dev/null || true

# Environment variables
ENV SURICATA_INTERFACE=auto
ENV SURICATA_MODE=live
ENV LOG_LEVEL=info
ENV BRIDGE_HOST=localhost
ENV BRIDGE_PORT=8001
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python3 /app/scripts/health_check.py || exit 1

# Startup script (copy last for better caching)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]