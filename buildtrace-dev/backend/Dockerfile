FROM python:3.11-slim AS base

# Install system dependencies required by OpenCV, PDF processing, and other native libs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        poppler-utils && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Make entrypoint executable
RUN chmod +x entrypoint.py start.sh
# Cloud Run sets PORT env var automatically
ENV PORT=8080
EXPOSE 8080
# Use Python entrypoint for reliable PORT handling
CMD ["python3", "entrypoint.py"]
