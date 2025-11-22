#!/bin/bash
set -e

PORT=${PORT:-8080}

exec gunicorn -b 0.0.0.0:$PORT \
  --workers 2 \
  --threads 4 \
  --timeout 3600 \
  --access-logfile - \
  --error-logfile - \
  app:app

