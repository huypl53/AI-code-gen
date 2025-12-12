# App-Agent

> AI-driven developer platform that transforms specifications into deployed applications.

[![Tests](https://img.shields.io/badge/tests-86%20passed-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)]()

## Overview

App-Agent is a backend platform that orchestrates AI agents to automatically:
1. **Analyze** user specifications (Markdown or CSV)
2. **Generate** production-ready Next.js applications
3. **Deploy** to Vercel with a live URL

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+ (for generated apps)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/app-agent.git
cd app-agent

# Install dependencies
uv sync --all-extras

# Copy environment file
cp .env.example .env
```

### Configuration

Edit `.env` with your API keys:

```env
# Required for AI-enhanced analysis and generation
ANTHROPIC_API_KEY=your-anthropic-api-key

# Required for deployment (optional for local testing)
VERCEL_TOKEN=your-vercel-token
```

### Run the Server

```bash
# Development mode (uses port from .env or default 8000)
uv run python -m app.main

# Or with explicit port
uv run uvicorn app.main:app --reload --port 8090

# Or use the script
./scripts/dev.sh
```

The API will be available at `http://localhost:{API_PORT}` (default: 8000).

## API Usage

### Create a Project

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-todo-app",
    "spec_format": "markdown",
    "spec_content": "# Todo App\n\n## Features\n- Create tasks\n- Mark complete\n- Delete tasks\n\n## Data Models\n\n### Task\n- id: uuid\n- title: string\n- completed: boolean"
  }'
```

Response:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-todo-app",
  "status": "analyzing",
  "created_at": "2024-12-11T10:00:00Z"
}
```

### Check Project Status

```bash
curl http://localhost:8000/v1/projects/{project_id}
```

Response (when deployed):
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-todo-app",
  "status": "deployed",
  "result": {
    "url": "https://my-todo-app-abc123.vercel.app",
    "deployment_id": "dpl_xyz789"
  }
}
```

### Stream Real-time Events

```bash
curl -N http://localhost:8000/v1/projects/{project_id}/stream
```

Events:
```
event: phase_started
data: {"phase": "spec_analysis", "timestamp": "..."}

event: phase_completed
data: {"phase": "spec_analysis", "duration_ms": 1200}

event: file_generated
data: {"path": "src/app/page.tsx", "lines": 45}

event: deployment_complete
data: {"url": "https://my-todo-app.vercel.app"}
```

## Specification Formats

### Markdown Format

```markdown
# My Application

## Description
A brief description of the application.

## Features
- **Feature Name**: Description of what it does
- Another feature

## Data Models

### User
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Unique identifier |
| email | string | Yes | User email |
| name | string | No | Display name |

## API Endpoints
- GET /api/users - List all users
- POST /api/users - Create a user
- DELETE /api/users/{id} - Delete a user

## UI Components

### Pages
- Home page
- Settings page

### Components
- UserList
- UserForm
```

### CSV Format

```csv
feature_name,description,priority,acceptance_criteria
User Login,Users can authenticate,must,Login form;Validation;Error messages
Dashboard,Main dashboard view,should,Statistics;Recent activity
Settings,User preferences,could,Theme toggle;Notifications
```

## Project Options

```json
{
  "name": "my-app",
  "spec_format": "markdown",
  "spec_content": "...",
  "options": {
    "framework": "nextjs",
    "styling": "tailwind",
    "auto_deploy": true,
    "include_tests": true,
    "typescript": true
  }
}
```

| Option | Default | Description |
|--------|---------|-------------|
| `framework` | `nextjs` | Target framework (nextjs, react, vue) |
| `styling` | `tailwind` | CSS framework (tailwind, css, scss) |
| `auto_deploy` | `true` | Deploy to Vercel automatically |
| `include_tests` | `true` | Generate test files |
| `typescript` | `true` | Use TypeScript |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                       │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ API Layer   │──▶│ Orchestrator │──▶│ Session Mgr │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ SpecAnalysisAgent│ │  CodingAgent   │ │  DevopsAgent   │
│                 │ │                 │ │                 │
│ • Parse specs   │ │ • Generate code │ │ • Deploy Vercel │
│ • Clarify reqs  │ │ • Create tests  │ │ • Return URL    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Development

### Run Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=app --cov-report=html

# Specific test file
uv run pytest tests/unit/test_agents.py -v
```

### Linting

```bash
# Check
uv run ruff check app tests

# Fix
uv run ruff check --fix app tests

# Format
uv run ruff format app tests
```

### Type Checking

```bash
uv run mypy app
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Health check |
| `/v1/projects` | POST | Create a new project |
| `/v1/projects` | GET | List all projects |
| `/v1/projects/{id}` | GET | Get project details |
| `/v1/projects/{id}` | DELETE | Cancel/delete project |
| `/v1/projects/{id}/clarifications` | GET | Get clarification questions |
| `/v1/projects/{id}/clarify` | POST | Submit clarification answers |
| `/v1/projects/{id}/stream` | GET | SSE event stream |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_ENV` | No | Environment (development/staging/production) |
| `APP_DEBUG` | No | Enable debug mode |
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key for Claude |
| `VERCEL_TOKEN` | Yes* | Vercel deployment token |
| `VERCEL_TEAM_ID` | No | Vercel team ID |
| `LOG_LEVEL` | No | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | No | Log format (console/json) |

*Required for full functionality. Without these, the system uses template-based generation and mock deployment.

## Project Structure

```
app-agent/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── agents/          # AI agents
│   ├── core/            # Core functionality
│   ├── generators/      # Code generators
│   ├── models/          # Pydantic models
│   ├── parsers/         # Spec parsers
│   └── utils/           # Utilities
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test fixtures
├── scripts/             # Helper scripts
└── .claude/doc/         # Implementation docs
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

---

Built with ❤️ by App-Agent Team
