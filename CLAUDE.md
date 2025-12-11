# AI-Driven Developer Platform

> **Project Codename:** App-Agent  
> **Version:** 0.1.0  
> **Last Updated:** December 2024

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Vision & Goals](#project-vision--goals)
3. [System Architecture](#system-architecture)
4. [Technical Stack](#technical-stack)
5. [Core Components](#core-components)
6. [API Design](#api-design)
7. [Agent Specifications](#agent-specifications)
8. [Data Models](#data-models)
9. [Implementation Phases](#implementation-phases)
10. [File Structure](#file-structure)
11. [Development Guidelines](#development-guidelines)
12. [Testing Strategy](#testing-strategy)
13. [Deployment & DevOps](#deployment--devops)
14. [Error Handling & Logging](#error-handling--logging)
15. [Security Considerations](#security-considerations)

---

## Executive Summary

**App-Agent** is an intelligent backend platform built with Python FastAPI that orchestrates multiple AI agents to transform user specifications into fully deployed web applications. The system receives user requirements (in CSV or Markdown format), analyzes and clarifies specifications, generates production-ready code, and automatically deploys to Vercel—all through a seamless API interface.

### Key Value Proposition

- **Zero-to-Deployed**: Transform ideas into live applications without manual coding
- **Intelligent Clarification**: AI-powered spec analysis ensures complete requirements before generation
- **End-to-End Automation**: From spec to deployment in a single workflow
- **Multi-Agent Architecture**: Specialized agents for each phase of development

---

## Project Vision & Goals

### Vision Statement

Democratize software development by enabling anyone to transform their ideas into production-ready web applications through natural language specifications.

### Primary Goals

| Goal | Description | Success Metric |
|------|-------------|----------------|
| **Spec-to-Code** | Convert user specs into working code | 95% spec coverage in generated code |
| **Autonomous Deployment** | Fully automated deployment pipeline | < 5 min from spec to live URL |
| **Quality Assurance** | Generate maintainable, tested code | 80%+ test coverage in output |
| **User Experience** | Simple, intuitive API interface | < 3 API calls to deploy |

### Non-Goals (Out of Scope for v1)

- Real-time collaborative editing
- Support for mobile native applications
- Self-hosted deployment options (beyond Vercel)
- Multi-language backend generation (Python only initially)

---

## System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER REQUEST                                    │
│                        (CSV / Markdown Specs)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND                                    │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐               │
│  │   API Layer   │───▶│ Orchestrator  │───▶│ Session Mgmt  │               │
│  └───────────────┘    └───────────────┘    └───────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   SPEC AGENT    │      │  CODING AGENT   │      │  DEVOPS AGENT   │
│                 │      │                 │      │                 │
│ • Parse specs   │      │ • Code gen      │      │ • Build app     │
│ • Clarify reqs  │      │ • File struct   │      │ • Deploy Vercel │
│ • Validate data │──────│ • Testing       │──────│ • Return URL    │
│ • Output: JSON  │      │ • Refactoring   │      │                 │
│                 │      │                 │      │                 │
│ claude-agent-sdk│      │ claude-agent-sdk│      │ v0-sdk          │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VERCEL DEPLOYMENT                                  │
│                         (Live Application URL)                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Communication Flow

```
User Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Specification Analysis                            │
│  ─────────────────────────────────────────────────────────  │
│  Input:  Raw specs (CSV/MD)                                 │
│  Agent:  SpecAnalysisAgent                                  │
│  Output: StructuredSpec (JSON)                              │
│                                                              │
│  Actions:                                                    │
│    1. Parse input format (CSV/Markdown)                     │
│    2. Extract features, entities, relationships            │
│    3. Identify ambiguities → Generate clarifying questions  │
│    4. (Optional) Await user clarification                   │
│    5. Produce final structured specification                │
└─────────────────────────────────────────────────────────────┘
     │
     ▼ StructuredSpec
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Code Generation                                   │
│  ─────────────────────────────────────────────────────────  │
│  Input:  StructuredSpec                                     │
│  Agent:  CodingAgent                                        │
│  Output: GeneratedProject (files + metadata)                │
│                                                              │
│  Actions:                                                    │
│    1. Analyze spec requirements                             │
│    2. Design file/folder structure                          │
│    3. Generate source code (components, API, etc.)          │
│    4. Generate configuration files                          │
│    5. Generate tests                                        │
│    6. Validate code quality                                 │
└─────────────────────────────────────────────────────────────┘
     │
     ▼ GeneratedProject
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Deployment                                        │
│  ─────────────────────────────────────────────────────────  │
│  Input:  GeneratedProject                                   │
│  Agent:  DevopsAgent                                        │
│  Output: DeploymentResult (Vercel URL)                      │
│                                                              │
│  Actions:                                                    │
│    1. Prepare build configuration                           │
│    2. Connect to Vercel via v0-sdk                          │
│    3. Deploy project                                        │
│    4. Monitor deployment status                             │
│    5. Return production URL                                 │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
Response: { "url": "https://my-app.vercel.app", ... }
```

---

## Technical Stack

### Core Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Primary language |
| **Framework** | FastAPI | 0.104+ | API backend |
| **AI SDK** | claude-agent-sdk | latest | AI agent orchestration |
| **Deployment SDK** | v0-sdk | latest | Vercel deployment |
| **Async** | asyncio | stdlib | Async operations |
| **Validation** | Pydantic | 2.x | Data validation |
| **HTTP Client** | httpx | 0.25+ | External API calls |

### Development Tools

| Tool | Purpose |
|------|---------|
| **uv** | Package management |
| **pytest** | Testing framework |
| **pytest-asyncio** | Async test support |
| **ruff** | Linting & formatting |
| **mypy** | Type checking |
| **pre-commit** | Git hooks |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Vercel** | Application hosting |
| **Redis** (optional) | Session caching |
| **PostgreSQL** (optional) | Persistent storage |

---

## Core Components

### 1. API Layer (`app/api/`)

Handles HTTP requests, authentication, and response formatting.

```python
# Key responsibilities:
- Request validation (Pydantic models)
- Authentication middleware
- Rate limiting
- Response serialization
- Error handling
- OpenAPI documentation
```

### 2. Orchestrator (`app/core/orchestrator.py`)

Central coordinator that manages the agent pipeline and workflow execution.

```python
# Key responsibilities:
- Agent lifecycle management
- Pipeline execution
- State transitions
- Inter-agent communication
- Timeout handling
- Retry logic
```

### 3. Session Manager (`app/core/session.py`)

Manages user sessions, conversation history, and state persistence.

```python
# Key responsibilities:
- Session creation/retrieval
- Conversation history tracking
- State persistence
- Cleanup & expiration
```

### 4. Agent Registry (`app/agents/registry.py`)

Central registry for agent definitions and configurations.

```python
# Key responsibilities:
- Agent registration
- Configuration management
- Agent instantiation
- Tool authorization
```

### 5. Agents (`app/agents/`)

Specialized AI agents for each phase of the development workflow.

| Agent | Module | Responsibility |
|-------|--------|----------------|
| SpecAnalysisAgent | `spec_agent.py` | Parse and clarify specifications |
| CodingAgent | `coding_agent.py` | Generate application code |
| DevopsAgent | `devops_agent.py` | Deploy to Vercel |

---

## API Design

### Base URL

```
Production: https://api.app-agent.dev/v1
Development: http://localhost:8000/v1
```

### Authentication

All endpoints require API key authentication:

```http
Authorization: Bearer <api_key>
```

### Endpoints

#### 1. Create Project

Initiates a new project from specifications.

```http
POST /v1/projects
Content-Type: application/json

{
  "name": "my-todo-app",
  "spec_format": "markdown",  // "markdown" | "csv"
  "spec_content": "# Todo App\n\n## Features\n- Add tasks\n- Mark complete...",
  "options": {
    "framework": "nextjs",     // "nextjs" | "react" | "vue"
    "styling": "tailwind",      // "tailwind" | "css" | "scss"
    "auto_deploy": true,
    "include_tests": true
  }
}
```

**Response (202 Accepted):**

```json
{
  "project_id": "proj_abc123",
  "status": "analyzing",
  "created_at": "2024-12-11T10:00:00Z",
  "estimated_completion": "2024-12-11T10:05:00Z"
}
```

#### 2. Get Project Status

Check project generation/deployment status.

```http
GET /v1/projects/{project_id}
```

**Response:**

```json
{
  "project_id": "proj_abc123",
  "status": "deployed",  // "analyzing" | "clarifying" | "generating" | "deploying" | "deployed" | "failed"
  "phases": {
    "spec_analysis": {
      "status": "completed",
      "started_at": "2024-12-11T10:00:00Z",
      "completed_at": "2024-12-11T10:01:00Z"
    },
    "code_generation": {
      "status": "completed",
      "started_at": "2024-12-11T10:01:00Z",
      "completed_at": "2024-12-11T10:03:00Z",
      "files_generated": 24
    },
    "deployment": {
      "status": "completed",
      "started_at": "2024-12-11T10:03:00Z",
      "completed_at": "2024-12-11T10:04:30Z"
    }
  },
  "result": {
    "url": "https://my-todo-app.vercel.app",
    "repo_url": null,
    "build_logs": "https://vercel.com/..."
  }
}
```

#### 3. Submit Clarifications

Respond to agent clarification questions.

```http
POST /v1/projects/{project_id}/clarify
Content-Type: application/json

{
  "responses": [
    {
      "question_id": "q_001",
      "answer": "Yes, users should be able to set due dates for tasks"
    },
    {
      "question_id": "q_002", 
      "answer": "Support both light and dark themes"
    }
  ]
}
```

#### 4. Get Clarification Questions

Retrieve pending clarification questions.

```http
GET /v1/projects/{project_id}/clarifications
```

**Response:**

```json
{
  "project_id": "proj_abc123",
  "status": "awaiting_clarification",
  "questions": [
    {
      "id": "q_001",
      "category": "feature",
      "question": "Should tasks have due dates?",
      "options": ["Yes", "No", "Optional for users"],
      "required": true
    },
    {
      "id": "q_002",
      "category": "design",
      "question": "What color theme should the app use?",
      "options": null,
      "required": false
    }
  ]
}
```

#### 5. Stream Project Events (SSE)

Real-time updates via Server-Sent Events.

```http
GET /v1/projects/{project_id}/stream
Accept: text/event-stream
```

**Event Stream:**

```
event: phase_started
data: {"phase": "spec_analysis", "timestamp": "2024-12-11T10:00:00Z"}

event: agent_message
data: {"agent": "spec", "message": "Analyzing markdown specification..."}

event: phase_completed
data: {"phase": "spec_analysis", "duration_ms": 45000}

event: phase_started
data: {"phase": "code_generation", "timestamp": "2024-12-11T10:01:00Z"}

event: file_generated
data: {"path": "src/components/TodoList.tsx", "lines": 45}

event: deployment_complete
data: {"url": "https://my-todo-app.vercel.app"}
```

#### 6. Cancel Project

Cancel an in-progress project.

```http
DELETE /v1/projects/{project_id}
```

#### 7. List Projects

List all projects for the authenticated user.

```http
GET /v1/projects?status=deployed&limit=10&offset=0
```

---

## Agent Specifications

### SpecAnalysisAgent

**Purpose:** Parse user specifications, identify ambiguities, and produce structured output.

#### Configuration

```python
spec_agent_config = AgentDefinition(
    description="Analyzes user specifications in CSV or Markdown format, "
                "identifies missing requirements, and generates clarifying questions",
    prompt="""You are a senior software architect specializing in requirements analysis.

Your task is to analyze user specifications and produce a structured output.

## Input Formats
- **Markdown**: Feature lists, user stories, descriptions
- **CSV**: Structured data with columns for features, requirements, etc.

## Analysis Process
1. Parse the input format correctly
2. Extract all explicit requirements
3. Identify implicit requirements
4. Detect ambiguities or missing information
5. Generate clarifying questions if needed
6. Produce structured specification JSON

## Output Format
Always output valid JSON matching the StructuredSpec schema.

## Quality Standards
- Every feature must have acceptance criteria
- API endpoints must have request/response schemas
- Data models must define all fields and relationships
- UI components must specify layout and interactions
""",
    tools=["Read", "Write", "Grep", "Glob"],
    model="sonnet"
)
```

#### Input Schema

```python
class SpecAnalysisInput(BaseModel):
    format: Literal["markdown", "csv"]
    content: str
    project_name: str
    context: Optional[dict] = None  # Previous clarifications, etc.
```

#### Output Schema

```python
class StructuredSpec(BaseModel):
    project_name: str
    description: str
    
    features: list[Feature]
    data_models: list[DataModel]
    api_endpoints: list[APIEndpoint]
    ui_components: list[UIComponent]
    
    clarifications_needed: list[ClarificationQuestion]
    assumptions: list[str]
    
    tech_recommendations: TechRecommendations
    estimated_complexity: Literal["simple", "medium", "complex"]
```

---

### CodingAgent

**Purpose:** Generate complete, production-ready application code based on structured specifications.

#### Configuration

```python
coding_agent_config = AgentDefinition(
    description="Generates production-ready application code from structured specifications",
    prompt="""You are an expert full-stack developer generating production applications.

## Your Responsibilities
1. Create complete file/folder structure
2. Generate all source code files
3. Write comprehensive tests
4. Create configuration files (package.json, tsconfig, etc.)
5. Add documentation (README, inline comments)

## Code Quality Standards
- Follow framework best practices
- Use TypeScript with strict typing
- Implement proper error handling
- Add input validation
- Write unit and integration tests
- Use meaningful variable/function names
- Add JSDoc comments for public APIs

## File Generation Order
1. Configuration files (package.json, tsconfig.json, etc.)
2. Database schema / data models
3. API routes and controllers
4. UI components (atomic → composite)
5. Pages and layouts
6. Utility functions
7. Tests
8. Documentation

## Technology Defaults
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- State: React Query + Zustand
- Validation: Zod
- Testing: Vitest + Testing Library
""",
    tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    model="opus"  # Use most capable model for code generation
)
```

#### Input Schema

```python
class CodeGenerationInput(BaseModel):
    spec: StructuredSpec
    output_directory: str
    options: CodeGenOptions

class CodeGenOptions(BaseModel):
    framework: Literal["nextjs", "react", "vue"] = "nextjs"
    styling: Literal["tailwind", "css", "scss"] = "tailwind"
    include_tests: bool = True
    include_storybook: bool = False
    typescript: bool = True
```

#### Output Schema

```python
class GeneratedProject(BaseModel):
    output_directory: str
    files: list[GeneratedFile]
    file_count: int
    total_lines: int
    
    entry_point: str  # e.g., "src/app/page.tsx"
    build_command: str  # e.g., "npm run build"
    start_command: str  # e.g., "npm run dev"
    
    dependencies: dict[str, str]
    dev_dependencies: dict[str, str]

class GeneratedFile(BaseModel):
    path: str
    content: str
    file_type: Literal["source", "config", "test", "docs", "asset"]
    lines: int
```

---

### DevopsAgent

**Purpose:** Deploy generated projects to Vercel and return the live URL.

#### Configuration

```python
devops_agent_config = AgentDefinition(
    description="Deploys generated applications to Vercel using v0-sdk",
    prompt="""You are a DevOps engineer specializing in Vercel deployments.

## Your Responsibilities
1. Validate project structure for deployment
2. Configure Vercel project settings
3. Handle environment variables
4. Execute deployment
5. Monitor build process
6. Report deployment status and URL

## Deployment Checklist
- [ ] Verify package.json has build script
- [ ] Check for next.config.js / vite.config.js
- [ ] Validate environment variables
- [ ] Configure build settings
- [ ] Set up domains (if provided)

## Error Handling
- Build failures: Analyze logs, suggest fixes
- Timeout: Increase build timeout or optimize
- Dependencies: Check for missing packages
""",
    tools=["Read", "Bash", "Glob"],  # v0-sdk tools added at runtime
    model="sonnet"
)
```

#### Input Schema

```python
class DeploymentInput(BaseModel):
    project: GeneratedProject
    project_name: str
    
    environment: Literal["production", "preview"] = "production"
    env_vars: Optional[dict[str, str]] = None
    
    domain: Optional[str] = None  # Custom domain
    team_id: Optional[str] = None  # Vercel team
```

#### Output Schema

```python
class DeploymentResult(BaseModel):
    success: bool
    url: str  # Production URL
    deployment_id: str
    
    build_logs_url: Optional[str]
    duration_ms: int
    
    error: Optional[str] = None
    error_details: Optional[dict] = None
```

---

## Data Models

### Core Entities

```python
# app/models/project.py

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class ProjectStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    CLARIFYING = "clarifying"
    GENERATING = "generating"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    status: ProjectStatus = ProjectStatus.PENDING
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Input
    spec_format: str
    spec_content: str
    options: dict
    
    # Processing state
    current_phase: Optional[str] = None
    phases: dict[str, PhaseInfo] = {}
    
    # Results
    structured_spec: Optional[dict] = None
    generated_project: Optional[dict] = None
    deployment_result: Optional[dict] = None
    
    # Error tracking
    error: Optional[str] = None
    error_phase: Optional[str] = None


class PhaseInfo(BaseModel):
    status: PhaseStatus = PhaseStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    metadata: dict = {}


class ClarificationQuestion(BaseModel):
    id: str = Field(default_factory=lambda: f"q_{uuid4().hex[:8]}")
    category: str  # "feature", "design", "technical", "scope"
    question: str
    options: Optional[list[str]] = None
    required: bool = True
    context: Optional[str] = None  # Why this question matters
    
    # Response tracking
    answered: bool = False
    answer: Optional[str] = None
```

### Specification Models

```python
# app/models/spec.py

from pydantic import BaseModel
from typing import Optional


class Feature(BaseModel):
    id: str
    name: str
    description: str
    priority: Literal["must", "should", "could", "wont"] = "should"
    
    user_stories: list[str] = []
    acceptance_criteria: list[str] = []
    
    dependencies: list[str] = []  # Feature IDs this depends on
    estimated_effort: Optional[str] = None  # "small", "medium", "large"


class DataModel(BaseModel):
    name: str
    description: str
    
    fields: list[ModelField]
    relationships: list[Relationship] = []
    
    indexes: list[str] = []
    unique_constraints: list[list[str]] = []


class ModelField(BaseModel):
    name: str
    type: str  # "string", "number", "boolean", "date", "json", etc.
    required: bool = True
    default: Optional[str] = None
    validation: Optional[str] = None  # e.g., "email", "url", "min:1|max:100"


class Relationship(BaseModel):
    type: Literal["one_to_one", "one_to_many", "many_to_many"]
    target_model: str
    field_name: str
    inverse_field: Optional[str] = None


class APIEndpoint(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    description: str
    
    auth_required: bool = True
    rate_limit: Optional[str] = None
    
    request_body: Optional[dict] = None  # JSON Schema
    query_params: Optional[dict] = None
    path_params: Optional[list[str]] = None
    
    response_schema: dict
    error_responses: dict[int, str] = {}  # status_code -> description


class UIComponent(BaseModel):
    name: str
    type: Literal["page", "layout", "component", "modal", "form"]
    description: str
    
    route: Optional[str] = None  # For pages
    props: list[ComponentProp] = []
    
    children: list[str] = []  # Child component names
    state_requirements: list[str] = []
    api_dependencies: list[str] = []  # API endpoints this uses


class ComponentProp(BaseModel):
    name: str
    type: str
    required: bool = True
    default: Optional[str] = None
    description: Optional[str] = None


class TechRecommendations(BaseModel):
    framework: str
    styling: str
    state_management: str
    database: Optional[str] = None
    auth_provider: Optional[str] = None
    
    additional_libraries: list[str] = []
    rationale: str
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Objective:** Set up project structure, core infrastructure, and basic API.

#### Tasks

- [ ] **1.1** Initialize project with FastAPI structure
- [ ] **1.2** Configure dependency management (uv, pyproject.toml)
- [ ] **1.3** Set up configuration management (pydantic-settings)
- [ ] **1.4** Implement core data models (Pydantic)
- [ ] **1.5** Create basic API endpoints (projects CRUD)
- [ ] **1.6** Set up logging and error handling
- [ ] **1.7** Configure testing framework (pytest)
- [ ] **1.8** Add OpenAPI documentation

#### Deliverables

- Working FastAPI server with health check
- Project creation endpoint (without agent integration)
- Unit tests for data models
- API documentation

---

### Phase 2: SpecAnalysisAgent (Week 2-3)

**Objective:** Implement specification parsing and analysis agent.

#### Tasks

- [ ] **2.1** Install and configure claude-agent-sdk
- [ ] **2.2** Create agent base class with common functionality
- [ ] **2.3** Implement SpecAnalysisAgent
- [ ] **2.4** Build Markdown parser (extract features, models, etc.)
- [ ] **2.5** Build CSV parser
- [ ] **2.6** Implement clarification question generation
- [ ] **2.7** Create structured spec output formatter
- [ ] **2.8** Add clarification flow API endpoints
- [ ] **2.9** Write integration tests

#### Deliverables

- SpecAnalysisAgent processing specs → StructuredSpec
- Clarification question/answer flow
- Integration tests with sample specs

---

### Phase 3: CodingAgent (Week 3-5)

**Objective:** Implement code generation agent.

#### Tasks

- [ ] **3.1** Design file generation strategy
- [ ] **3.2** Implement CodingAgent with claude-agent-sdk
- [ ] **3.3** Create code templates for common patterns
- [ ] **3.4** Implement Next.js project generator
- [ ] **3.5** Add Tailwind CSS integration
- [ ] **3.6** Implement component generation
- [ ] **3.7** Add API route generation
- [ ] **3.8** Implement test generation
- [ ] **3.9** Add file validation and linting
- [ ] **3.10** Write integration tests

#### Deliverables

- CodingAgent generating complete projects
- Support for Next.js + Tailwind
- Generated code passes linting
- Integration tests with various specs

---

### Phase 4: DevopsAgent (Week 5-6)

**Objective:** Implement Vercel deployment agent.

#### Tasks

- [ ] **4.1** Integrate v0-sdk for Vercel deployment
- [ ] **4.2** Implement DevopsAgent
- [ ] **4.3** Create deployment configuration generator
- [ ] **4.4** Implement build monitoring
- [ ] **4.5** Add error handling and retry logic
- [ ] **4.6** Create deployment status reporting
- [ ] **4.7** Write integration tests (mock Vercel API)

#### Deliverables

- DevopsAgent deploying to Vercel
- Deployment status streaming
- Error handling with meaningful messages

---

### Phase 5: Orchestration (Week 6-7)

**Objective:** Integrate all agents into a cohesive pipeline.

#### Tasks

- [ ] **5.1** Implement Orchestrator class
- [ ] **5.2** Create agent pipeline execution
- [ ] **5.3** Add state management between phases
- [ ] **5.4** Implement SSE streaming for real-time updates
- [ ] **5.5** Add timeout and cancellation handling
- [ ] **5.6** Implement retry logic for transient failures
- [ ] **5.7** Create end-to-end integration tests

#### Deliverables

- Complete pipeline: spec → code → deploy
- Real-time progress streaming
- Robust error handling

---

### Phase 6: Polish & Production (Week 7-8)

**Objective:** Production readiness and optimization.

#### Tasks

- [ ] **6.1** Add rate limiting
- [ ] **6.2** Implement authentication (API keys)
- [ ] **6.3** Add request validation hardening
- [ ] **6.4** Performance optimization
- [ ] **6.5** Comprehensive logging
- [ ] **6.6** Monitoring and metrics
- [ ] **6.7** Documentation (README, API docs)
- [ ] **6.8** Security audit
- [ ] **6.9** Load testing

#### Deliverables

- Production-ready API
- Complete documentation
- Security compliance

---

## File Structure

```
app-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # Dependency injection
│   │   ├── middleware.py          # Custom middleware
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # Main v1 router
│   │       ├── projects.py        # Project endpoints
│   │       └── health.py          # Health check endpoint
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Agent pipeline orchestration
│   │   ├── session.py             # Session management
│   │   ├── events.py              # Event system for SSE
│   │   └── exceptions.py          # Custom exceptions
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # Base agent class
│   │   ├── registry.py            # Agent registry
│   │   ├── spec_agent.py          # SpecAnalysisAgent
│   │   ├── coding_agent.py        # CodingAgent
│   │   └── devops_agent.py        # DevopsAgent
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py             # Project models
│   │   ├── spec.py                # Specification models
│   │   ├── generation.py          # Code generation models
│   │   └── deployment.py          # Deployment models
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── markdown.py            # Markdown spec parser
│   │   └── csv.py                 # CSV spec parser
│   │
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── nextjs/                # Next.js generators
│   │   │   ├── __init__.py
│   │   │   ├── project.py
│   │   │   ├── components.py
│   │   │   └── api_routes.py
│   │   └── templates/             # Code templates
│   │       ├── component.tsx.j2
│   │       ├── api_route.ts.j2
│   │       └── ...
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py             # Logging configuration
│       ├── validation.py          # Validation utilities
│       └── files.py               # File utilities
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_parsers.py
│   │   └── test_agents.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_pipeline.py
│   │   └── test_deployment.py
│   └── fixtures/
│       ├── sample_spec.md
│       ├── sample_spec.csv
│       └── expected_outputs/
│
├── .claude/
│   └── doc/
│       └── claude-agent-sdk.md    # SDK reference
│
├── scripts/
│   ├── dev.sh                     # Development server
│   ├── test.sh                    # Run tests
│   └── lint.sh                    # Linting
│
├── .env.example                   # Environment template
├── .gitignore
├── .python-version                # Python version (3.11)
├── CLAUDE.md                      # This file
├── README.md                      # Project README
├── pyproject.toml                 # Project configuration
└── uv.lock                        # Dependency lock
```

---

## Development Guidelines

### Code Style

```python
# Use type hints everywhere
def process_spec(spec: str, format: SpecFormat) -> StructuredSpec:
    ...

# Use Pydantic for all data structures
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    spec_content: str = Field(..., min_length=10)

# Async by default for I/O operations
async def create_project(data: ProjectCreate) -> Project:
    ...

# Use dependency injection
async def get_project(
    project_id: UUID,
    session: Session = Depends(get_session)
) -> Project:
    ...
```

### Async Patterns

```python
# Use ClaudeSDKClient for continuous conversations
async def run_agent_pipeline(spec: str) -> GeneratedProject:
    async with ClaudeSDKClient(options=agent_options) as client:
        # Phase 1: Analyze spec
        await client.query(f"Analyze this specification:\n{spec}")
        
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                # Process analysis
                pass
        
        # Phase 2: Follow-up (maintains context)
        await client.query("Now generate the code based on your analysis")
        
        async for message in client.receive_response():
            # Process code generation
            pass
```

### Error Handling

```python
# Custom exceptions hierarchy
class AppAgentError(Exception):
    """Base exception for App-Agent"""
    pass

class SpecParsingError(AppAgentError):
    """Failed to parse specification"""
    pass

class AgentExecutionError(AppAgentError):
    """Agent failed during execution"""
    def __init__(self, agent: str, phase: str, details: str):
        self.agent = agent
        self.phase = phase
        self.details = details
        super().__init__(f"Agent {agent} failed in {phase}: {details}")

class DeploymentError(AppAgentError):
    """Deployment to Vercel failed"""
    pass

# Global exception handler
@app.exception_handler(AppAgentError)
async def app_agent_error_handler(request: Request, exc: AppAgentError):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__}
    )
```

### Logging

```python
import structlog

logger = structlog.get_logger()

async def process_project(project_id: str):
    logger.info("project.processing.started", project_id=project_id)
    
    try:
        result = await orchestrator.run(project_id)
        logger.info(
            "project.processing.completed",
            project_id=project_id,
            duration_ms=result.duration_ms,
            url=result.url
        )
    except Exception as e:
        logger.error(
            "project.processing.failed",
            project_id=project_id,
            error=str(e),
            exc_info=True
        )
        raise
```

---

## Testing Strategy

### Test Pyramid

```
         ╱╲
        ╱  ╲        E2E Tests (10%)
       ╱────╲       - Full pipeline tests
      ╱      ╲      - Actual Vercel deployment (staging)
     ╱────────╲
    ╱          ╲    Integration Tests (30%)
   ╱────────────╲   - API endpoint tests
  ╱              ╲  - Agent + SDK integration
 ╱────────────────╲
╱                  ╲ Unit Tests (60%)
╱────────────────────╲ - Models, parsers, utilities
                       - Agent logic (mocked SDK)
```

### Example Tests

```python
# tests/unit/test_parsers.py
import pytest
from app.parsers.markdown import parse_markdown_spec

def test_parse_features():
    spec = """
    # My App
    
    ## Features
    - User authentication
    - Dashboard view
    """
    
    result = parse_markdown_spec(spec)
    
    assert len(result.features) == 2
    assert result.features[0].name == "User authentication"

# tests/integration/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    response = await client.post(
        "/v1/projects",
        json={
            "name": "test-app",
            "spec_format": "markdown",
            "spec_content": "# Test\n## Features\n- Hello world"
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "project_id" in data
    assert data["status"] == "analyzing"

# tests/integration/test_agents.py
@pytest.mark.asyncio
async def test_spec_agent_with_clarifications(mock_claude_sdk):
    agent = SpecAnalysisAgent()
    
    result = await agent.analyze(
        spec="# App\n\n## Features\n- Todo list",
        format="markdown"
    )
    
    assert result.structured_spec is not None
    # Spec is ambiguous, should have clarification questions
    assert len(result.clarifications_needed) > 0
```

### Test Fixtures

```python
# tests/conftest.py
import pytest
from app.main import create_app

@pytest.fixture
def app():
    return create_app(testing=True)

@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_markdown_spec():
    return """
    # Todo Application
    
    ## Description
    A simple todo list application.
    
    ## Features
    - Create tasks
    - Mark tasks as complete
    - Delete tasks
    
    ## Data Models
    ### Task
    - id: uuid
    - title: string
    - completed: boolean
    - created_at: datetime
    """

@pytest.fixture
def mock_claude_sdk(monkeypatch):
    """Mock claude-agent-sdk for unit tests"""
    # Implementation
    pass
```

---

## Deployment & DevOps

### Environment Variables

```bash
# .env.example

# Application
APP_ENV=development  # development | staging | production
APP_DEBUG=true
APP_SECRET_KEY=your-secret-key-here

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Claude Agent SDK
ANTHROPIC_API_KEY=your-anthropic-key

# Vercel (for deployment)
VERCEL_TOKEN=your-vercel-token
VERCEL_TEAM_ID=optional-team-id

# Storage (optional)
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost:5432/appagent

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # json | console
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application
COPY . .

# Run
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=development
    env_file:
      - .env
    volumes:
      - ./app:/app/app  # Hot reload in dev
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install dependencies
        run: uv sync
      
      - name: Lint
        run: uv run ruff check .
      
      - name: Type check
        run: uv run mypy app
      
      - name: Test
        run: uv run pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Error Handling & Logging

### Structured Logging

```python
# app/utils/logging.py
import structlog
from app.config import settings

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() 
                if settings.LOG_FORMAT == "json" 
                else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### Error Response Format

```python
# Standard error response
{
    "error": {
        "code": "SPEC_PARSING_FAILED",
        "message": "Failed to parse markdown specification",
        "details": {
            "line": 42,
            "expected": "feature definition",
            "found": "empty line"
        },
        "request_id": "req_abc123",
        "documentation_url": "https://docs.app-agent.dev/errors/SPEC_PARSING_FAILED"
    }
}
```

---

## Security Considerations

### API Security

1. **Authentication**: API key in Authorization header
2. **Rate Limiting**: 100 requests/minute per API key
3. **Input Validation**: Strict Pydantic validation on all inputs
4. **Output Sanitization**: No sensitive data in responses

### Agent Security

1. **Tool Restrictions**: Agents only have access to required tools
2. **Sandbox Execution**: Code generation in isolated environment
3. **Permission Mode**: Use `acceptEdits` for controlled file operations
4. **Command Validation**: Block dangerous shell commands

```python
# Dangerous command blocking hook
async def validate_bash_command(
    input_data: dict,
    tool_use_id: str | None,
    context: HookContext
) -> dict:
    if input_data['tool_name'] == 'Bash':
        command = input_data['tool_input'].get('command', '')
        
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'sudo\s+',
            r'chmod\s+777',
            r'curl.*\|\s*bash',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': f'Command blocked: matches dangerous pattern'
                    }
                }
    return {}
```

### Data Security

1. **No Persistent Storage of Specs**: Process and discard
2. **Encryption at Rest**: If caching is enabled
3. **No Logging of Sensitive Data**: Redact API keys, secrets
4. **Secure Environment Variables**: Never commit to git

---

## Quick Start Commands

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run type checker
uv run mypy app

# Format code
uv run ruff format .
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [claude-agent-sdk Reference](/.claude/doc/claude-agent-sdk.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Vercel API Reference](https://vercel.com/docs/rest-api)

---

*This document is a living specification. Update it as the project evolves.*
