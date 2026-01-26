#!/bin/sh
set -e

echo "Starting predict-man..."

# Start services Flask as non-root user
echo "Starting services (WebSocket + FastAPI)..."
exec gosu appuser python startup.py
