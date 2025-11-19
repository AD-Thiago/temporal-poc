FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
	pip install --no-cache-dir -r requirements.txt
COPY src/ src/
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
# Default command runs the HTTP worker (suitable for Cloud Run). Use gunicorn for production on Cloud Run.
CMD gunicorn -w 1 -b :$PORT src.worker_http:app
