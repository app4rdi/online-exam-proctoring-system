# Multi-stage Dockerfile for Online Exam Proctoring System
# Stage 1: Base image with dependencies
FROM python:3.9-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies for AI libraries
RUN apt-get update && apt-get install -y \
    gcc g++ cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production image
FROM python:3.9-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from base
COPY --from=base /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create directories for runtime data
RUN mkdir -p violation_screenshots && \
    chmod 755 violation_screenshots

# Expose port
EXPOSE 8080

# Environment variables (can be overridden by docker-compose)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run with gunicorn for production
CMD ["python", "app.py"]
