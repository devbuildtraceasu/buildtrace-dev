FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Make start script executable
RUN chmod +x start.sh
# Cloud Run sets PORT env var automatically
ENV PORT=8080
EXPOSE 8080
# Use start script to handle PORT variable
CMD ["./start.sh"]
