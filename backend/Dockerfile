FROM python:3.11-slim AS base
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
