# Base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies (curl for healthchecks, nodejs for claude-agent-sdk)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential ca-certificates gnupg && \
    # Install Node.js 20.x (LTS) - required for Claude Code CLI
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally (required by claude-agent-sdk)
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && \
    pip install .

# Copy remaining project files
COPY . .

EXPOSE 8000

# Run the API server (port can be overridden with API_PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8000}"]
