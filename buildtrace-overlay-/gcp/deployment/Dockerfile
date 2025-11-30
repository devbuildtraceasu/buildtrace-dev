# Multi-stage build for Python Flask application
FROM python:3.11-slim AS builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    # pdf2image dependencies
    poppler-utils \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads results drawings static templates services migrations

# Set environment variables
ENV FLASK_APP=app_with_auth.py
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Cloud Run uses PORT environment variable
EXPOSE 8080

# Run the application on the port specified by Cloud Run
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 0 app_with_auth:app