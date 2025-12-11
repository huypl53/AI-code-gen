# Phase 5: Orchestration - Implementation Notes

## Overview

The PipelineOrchestrator coordinates all agents to transform specs into deployed apps.

## Pipeline Phases

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  spec_analysis  │────▶│ code_generation │────▶│   deployment    │
│                 │     │                 │     │                 │
│ SpecAnalysisAgent     │ CodingAgent     │     │ DevopsAgent     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         ▼                                               ▼
   Clarifications?                                 Vercel URL
```

## Orchestrator (`app/core/orchestrator.py`)

### Key Methods

```python
async def run(project_id: UUID) -> Project:
    """Run complete pipeline."""
    
async def _run_spec_analysis(project: Project) -> Project:
    """Phase 1: Analyze specification."""
    
async def _run_code_generation(project: Project) -> Project:
    """Phase 2: Generate code."""
    
async def _run_deployment(project: Project) -> Project:
    """Phase 3: Deploy to Vercel."""
```

### State Management

Updates project state at each phase:
- `status`: Overall project status
- `current_phase`: Active phase name
- `phases`: Dict of PhaseInfo per phase
- `structured_spec`: Output from spec analysis
- `generated_project`: Output from code generation
- `deployment_result`: Output from deployment

### Event Publishing

Publishes SSE events via EventBus:
- `phase_started` - When a phase begins
- `phase_completed` - When a phase ends
- `agent_message` - Agent log messages
- `file_generated` - Code files created
- `deployment_complete` - Final URL
- `error` - Failure details

## API Integration

Background task execution:

```python
@router.post("/projects")
async def create_project(..., background_tasks: BackgroundTasks):
    project = await session.create_project(data)
    background_tasks.add_task(run_pipeline_background, project.id)
    return ProjectResponse.from_project(project)
```

## Clarification Flow

If spec analysis returns questions:
1. Pipeline pauses
2. Status set to `clarifying`
3. User submits answers via API
4. `resume_after_clarification()` continues pipeline

## Tests

7 tests covering:
- Full pipeline execution
- Individual phase execution
- Minimal spec handling
- Event publishing
- Error handling
