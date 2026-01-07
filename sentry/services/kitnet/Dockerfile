# KitNET AI Anomaly Detection Service
# Optimized for smaller image size and faster builds

FROM python:3.11-slim as builder

# Install build dependencies (needed for numpy/scipy compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy and install requirements
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# --- Final stage: Runtime image ---
FROM python:3.11-slim

# Only install runtime dependencies (no compilers!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Create necessary directories
RUN mkdir -p /app/data /app/config /app/models

# Copy application code (after dependencies for better caching)
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd -r -s /bin/false kitnet \
    && chown -R kitnet:kitnet /app

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=info
ENV KITNET_THRESHOLD=0.95
ENV BRIDGE_URL=http://bridge:8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python scripts/health_check.py || exit 1

USER kitnet

ENTRYPOINT ["python", "src/main.py"]