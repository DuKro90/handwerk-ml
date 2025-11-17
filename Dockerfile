# Multi-stage build for Django backend

FROM python:3.10-slim as builder

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.10-slim

WORKDIR /app/backend

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=handwerk_ml.settings

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/models

# Create non-root user
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/projects/statistics/ || exit 1

EXPOSE 8000

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "handwerk_ml.wsgi:application"]
