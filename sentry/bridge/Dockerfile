# Bridge Service - Orchestration Layer
# Optimized for smaller image size and faster builds

FROM python:3.11-slim

# Install system dependencies in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (no build tools needed for these packages)
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories (including bridge subdirectory for config persistence)
RUN mkdir -p /app/data/bridge /app/config

# Copy application code AFTER dependencies
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user and set ownership
RUN useradd -r -s /bin/false bridge \
    && chown -R bridge:bridge /app

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=info
ENV PORT=8001

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

USER bridge

ENTRYPOINT ["python", "src/main.py"]