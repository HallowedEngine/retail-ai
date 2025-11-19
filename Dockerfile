# Multi-stage Dockerfile for production-ready Retail AI application

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ---  Production stage ---
FROM base as production

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app
COPY ./data /app/data

# Create necessary directories
RUN mkdir -p /app/logs /app/data/uploads

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', auth=('admin', 'retailai2025'))" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- Development stage ---
FROM base as development

# Copy requirements including dev dependencies
COPY requirements.txt requirements-dev.txt ./

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy all code (will be overridden by volume in docker-compose)
COPY . /app

# Create directories
RUN mkdir -p /app/logs /app/data/uploads

EXPOSE 8000

# Run with reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
