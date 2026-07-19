# ─────────────────────────────────────────────────────────────
#  Mortgage Broker AI Agent — Multi-Stage Docker Image
#  Python 3.12 slim base, production-ready, optimized for size
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# STAGE 1: Builder
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────
# STAGE 2: Runtime
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Mortgage Broker Agent"
LABEL description="AI-powered mortgage broker document generation agent"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=5000 \
    FLASK_ENV=production \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user and systematic working directories (non-root for security)
RUN groupadd -r appuser && useradd -m -r -g appuser appuser

# Establish application context folder structures
WORKDIR /app
RUN mkdir -p /app/data /app/generated_docs && \
    chown -R appuser:appuser /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy the application files
COPY --chown=appuser:appuser . .

# Switch to non-root user context
USER appuser

# Expose server interface port
EXPOSE 5000

# Containerside Health Check Verification
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start with production Gunicorn configurations
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "4", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]
