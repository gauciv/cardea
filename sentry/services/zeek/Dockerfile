# Zeek Network Analysis Service
# Note: Zeek is inherently large (~800MB+) due to its analysis framework
# This is optimized as much as possible without breaking functionality

FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies and Zeek in single layer to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    ca-certificates \
    iproute2 \
    && echo 'deb http://download.opensuse.org/repositories/security:/zeek/xUbuntu_22.04/ /' > /etc/apt/sources.list.d/security:zeek.list \
    && wget -qO - https://download.opensuse.org/repositories/security:zeek/xUbuntu_22.04/Release.key | apt-key add - \
    && apt-get update \
    && apt-get install -y --no-install-recommends zeek \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Create directories in single layer
RUN mkdir -p /opt/zeek/logs/current /opt/zeek/logs/archive /opt/zeek/etc /opt/zeek/scripts /tmp/cardea/zeek

# Copy configuration
COPY config/ /opt/zeek/etc/
COPY scripts/ /opt/zeek/scripts/

# Environment variables
ENV PATH=/opt/zeek/bin:$PATH
ENV ZEEK_INTERFACE=auto
ENV ZEEK_MODE=live
ENV LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD pgrep -f zeek || exit 1

# Startup script (copy last for better caching during development)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /opt/zeek

EXPOSE 47760/tcp

ENTRYPOINT ["/entrypoint.sh"]