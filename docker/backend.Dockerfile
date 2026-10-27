# ==============================================================================
# Nerolac Operations Dashboard - Production Backend Dockerfile
# Multi-Stage Build: Python 3.12-slim | Non-Root User | Minimized Attack Surface
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Dependency Builder
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compilation tools and development libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for deterministic package isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade packaging tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Hardened Runtime Container
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

LABEL maintainer="Nerolac DevOps Engineering <devops@nerolac.bd>"
LABEL description="Production FastAPI ASGI Backend for Nerolac Operations Dashboard"
LABEL security.non-root="true"

WORKDIR /app

# Install minimal runtime system libraries
# - libpq5: PostgreSQL C client
# - libgomp1: OpenMP runtime for LightGBM gradient boosting
# - curl: Container orchestrator health probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system group and user
RUN groupadd --system --gid 10001 nerolac && \
    useradd --system --uid 10001 --gid nerolac --no-create-home --shell /sbin/nologin nerolac

# Copy compiled virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Configure runtime environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app" \
    PORT=8000

# Copy application source code with non-root ownership
COPY --chown=nerolac:nerolac src/ /app/src/
COPY --chown=nerolac:nerolac alembic.ini /app/alembic.ini
COPY --chown=nerolac:nerolac knowledge/ /app/knowledge/

# Enforce non-root execution
USER nerolac

# Expose internal ASGI service port
EXPOSE 8000

# Container liveness and readiness probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production ASGI server
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "65", "--limit-concurrency", "2000"]
