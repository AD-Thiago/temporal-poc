FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Download Cloud SQL Proxy
RUN wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy \
    && chmod +x /usr/local/bin/cloud_sql_proxy

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
	pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    LOG_LEVEL=INFO \
    ENABLE_CLOUD_LOGGING=true \
    SERVICE_NAME=temporal-worker \
    ENVIRONMENT=production

# Use gunicorn with increased timeout for database operations
CMD gunicorn -w 1 --threads 8 --timeout 120 -b :$PORT src.worker_http:app
