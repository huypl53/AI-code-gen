#!/bin/bash
# Development server script
# Uses API_PORT from .env file (default: 8000)

set -e

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

PORT=${API_PORT:-8000}
HOST=${API_HOST:-0.0.0.0}

echo "Starting development server on http://${HOST}:${PORT}..."
uv run uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
