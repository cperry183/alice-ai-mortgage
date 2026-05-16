# ─────────────────────────────────────────────────────────────
#  Mortgage Broker AI Agent — Docker Image
#  Python 3.12 slim base, production-ready
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
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user and systematic working directories (non-root for security)
RUN groupadd -r appuser && useradd -m -r -g appuser appuser

# Establish application context folder structures
WORKDIR /app
RUN mkdir -p /app/data /app/generated_docs && \
    chown -R appuser:appuser /app

# 1. Leverage Docker Layer Caching for Pip Dependencies
# Only rerun pip install if requirements.txt changes
COPY --chown=appuser:appuser requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Copy the Remaining Application Files safely
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