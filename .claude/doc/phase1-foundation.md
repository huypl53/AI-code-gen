# Phase 1: Foundation - Implementation Notes

## Overview

Phase 1 establishes the core infrastructure for the App-Agent platform. This includes the FastAPI application structure, data models, session management, event system, and basic API endpoints.

## Completed Components

### 1. Project Structure

```
app/
├── __init__.py          # Package init with version
├── config.py            # Configuration using pydantic-settings
├── main.py              # FastAPI application entry point
├── api/
│   ├── __init__.py
│   ├── deps.py          # Dependency injection
│   ├── middleware.py    # Request logging middleware
│   └── v1/
│       ├── __init__.py
│       ├── router.py    # Main v1 router
│       ├── health.py    # Health check endpoint
│       └── projects.py  # Project CRUD endpoints
├── core/
│   ├── __init__.py
│   ├── exceptions.py    # Custom exception hierarchy
│   ├── session.py       # In-memory session manager
│   └── events.py        # SSE event bus
├── models/
│   ├── __init__.py
│   ├── project.py       # Project-related models
│   ├── spec.py          # Specification models
│   ├── generation.py    # Code generation models
│   └── deployment.py    # Deployment models
├── agents/
│   ├── __init__.py
│   ├── base.py          # BaseAgent abstract class
│   └── registry.py      # Agent registry singleton
├── parsers/
│   └── __init__.py
├── generators/
│   ├── __init__.py
│   └── nextjs/
│       └── __init__.py
└── utils/
    ├── __init__.py
    └── logging.py       # Structured logging with structlog
```

### 2. Configuration (`app/config.py`)

Uses `pydantic-settings` for environment-based configuration:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: Literal["development", "staging", "production"]
    anthropic_api_key: str
    vercel_token: str
    # ... etc
```

Key settings:
- `APP_ENV` - Environment mode
- `ANTHROPIC_API_KEY` - For claude-agent-sdk
- `VERCEL_TOKEN` - For deployment
- `LOG_LEVEL` / `LOG_FORMAT` - Logging configuration

### 3. Data Models (`app/models/`)

#### Project Models
- `ProjectCreate` - Request model for creating projects
- `Project` - Full project state with phases, results
- `ProjectResponse` - API response model
- `ProjectStatus` - Enum: pending, analyzing, clarifying, generating, deploying, deployed, failed, cancelled
- `PhaseInfo` - Tracks each processing phase
- `ClarificationQuestion` - Questions for user clarification

#### Specification Models
- `Feature` - Feature with priority, user stories, acceptance criteria
- `DataModel` - Entity with fields and relationships
- `APIEndpoint` - API specification
- `UIComponent` - UI component specification
- `StructuredSpec` - Complete parsed specification

### 4. Session Manager (`app/core/session.py`)

In-memory session storage with TTL:

```python
class SessionManager:
    async def create_project(data: ProjectCreate) -> Project
    async def get_project(project_id: UUID) -> Project | None
    async def update_project(project: Project) -> Project
    async def delete_project(project_id: UUID) -> bool
    async def list_projects(status?, limit, offset) -> tuple[list[Project], int]
```

**Note:** For production, replace with Redis or database-backed storage.

### 5. Event Bus (`app/core/events.py`)

SSE event system for real-time updates:

```python
class EventBus:
    def subscribe(project_id: UUID) -> asyncio.Queue[Event]
    async def publish_phase_started(project_id, phase)
    async def publish_agent_message(project_id, agent, message)
    async def publish_file_generated(project_id, path, lines)
    async def publish_deployment_complete(project_id, url)
```

### 6. API Endpoints (`app/api/v1/projects.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/health` | GET | Health check |
| `/v1/projects` | POST | Create project |
| `/v1/projects` | GET | List projects |
| `/v1/projects/{id}` | GET | Get project details |
| `/v1/projects/{id}` | DELETE | Cancel/delete project |
| `/v1/projects/{id}/clarifications` | GET | Get clarification questions |
| `/v1/projects/{id}/clarify` | POST | Submit answers |
| `/v1/projects/{id}/stream` | GET | SSE event stream |

### 7. Base Agent (`app/agents/base.py`)

Abstract base class for all AI agents:

```python
class BaseAgent(ABC, Generic[InputT, OutputT]):
    @property
    @abstractmethod
    def name(self) -> str
    
    @property
    @abstractmethod
    def system_prompt(self) -> str
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT
```

## Testing

32 tests covering:
- Unit tests for all data models
- Unit tests for session manager
- Integration tests for all API endpoints

Run tests: `uv run pytest tests/ -v`

## Key Decisions

1. **In-memory session storage** - Simple for development, designed for easy swap to Redis/DB
2. **Singleton patterns** - Session manager and event bus use `@lru_cache` singletons
3. **Structured logging** - Using `structlog` for JSON-formatted logs in production
4. **SSE for real-time** - Using `sse-starlette` for server-sent events
5. **Generic agents** - BaseAgent uses generics for type-safe input/output

## Next Steps (Phase 2)

1. Implement SpecAnalysisAgent using claude-agent-sdk
2. Build Markdown and CSV parsers
3. Implement clarification flow
4. Create structured spec output

## Dependencies Added

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
claude-agent-sdk>=0.1.0
structlog>=24.1.0
python-multipart>=0.0.6
sse-starlette>=2.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
ruff>=0.2.0
mypy>=1.8.0
```
