# IncidentLens — Production Dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Install security updates and curl for container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy repository application code
COPY . /app/

# Create and switch to non-privileged user for container security
RUN useradd -m -u 1000 sre && \
    chown -R sre:sre /app

USER sre

# Expose standard application port
EXPOSE 8000

# Health check against dedicated production health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Production entrypoint (no --reload flag)
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
