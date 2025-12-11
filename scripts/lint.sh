#!/bin/bash
# Linting and formatting script

set -e

echo "Running ruff check..."
uv run ruff check app tests

echo "Running ruff format check..."
uv run ruff format --check app tests

echo "Running mypy..."
uv run mypy app

echo "All checks passed!"
