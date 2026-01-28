#!/bin/bash

# Combined startup script for Render free tier
# Runs Django (Gunicorn), Celery Worker, and Celery Beat together

echo "Starting combined Django + Celery service..."

# Start Celery Beat in background (scheduler)
echo "Starting Celery Beat..."
celery -A config beat --loglevel=info &
BEAT_PID=$!

# Start Celery Worker in background (1 worker to save memory)
echo "Starting Celery Worker..."
celery -A config worker --loglevel=info --concurrency=1 &
WORKER_PID=$!

# Give Celery time to start
sleep 3

# Start Gunicorn (Django) in foreground
echo "Starting Gunicorn..."
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120

# If Gunicorn exits, kill Celery processes
kill $BEAT_PID $WORKER_PID 2>/dev/null
