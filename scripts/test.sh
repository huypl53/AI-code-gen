#!/bin/bash
# Test runner script

set -e

echo "Running tests..."
uv run pytest tests/ -v --tb=short "$@"
