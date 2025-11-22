#!/bin/sh
set -e

# Get PORT from environment or default to 8080
PORT=${PORT:-8080}

# Start gunicorn with proper configuration
exec gunicorn \
  --bind 0.0.0.0:${PORT} \
  --workers 2 \
  --threads 4 \
  --timeout 3600 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --preload \
  app:app

