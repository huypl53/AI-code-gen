"""Project management endpoints."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api.deps import EventsDep, ProjectDep, SessionDep
from app.core.events import Event
from app.models.project import (
    ClarificationQuestion,
    Project,
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
)

router = APIRouter()


class ProjectListResponse(BaseModel):
    """Response for listing projects."""

    projects: list[ProjectResponse]
    total: int
    limit: int
    offset: int


class ClarificationResponse(BaseModel):
    """Response containing clarification questions."""

    project_id: UUID
    status: ProjectStatus
    questions: list[ClarificationQuestion]


class ClarificationAnswer(BaseModel):
    """An answer to a clarification question."""

    question_id: str
    answer: str


class SubmitClarificationsRequest(BaseModel):
    """Request to submit clarification answers."""

    responses: list[ClarificationAnswer]


async def run_pipeline_background(project_id: UUID) -> None:
    """Background task to run the orchestrator pipeline."""
    from app.core.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    try:
        await orchestrator.run(project_id)
    except Exception as e:
        # Error already handled in orchestrator
        pass


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new project",
    description="Initiate a new project from specifications. Returns immediately while processing continues in background.",
)
async def create_project(
    data: ProjectCreate,
    session: SessionDep,
    events: EventsDep,
    background_tasks: BackgroundTasks,
) -> ProjectResponse:
    """Create a new project and start processing."""
    # Create project
    project = await session.create_project(data)

    # Update status and start background processing
    project.status = ProjectStatus.ANALYZING
    await session.update_project(project)

    # Start the pipeline in background
    background_tasks.add_task(run_pipeline_background, project.id)

    return ProjectResponse.from_project(project)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects",
)
async def list_projects(
    session: SessionDep,
    status_filter: Annotated[ProjectStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectListResponse:
    """List all projects with optional filtering."""
    projects, total = await session.list_projects(
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return ProjectListResponse(
        projects=[ProjectResponse.from_project(p) for p in projects],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
)
async def get_project(project: ProjectDep) -> ProjectResponse:
    """Get detailed information about a project."""
    return ProjectResponse.from_project(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel/delete a project",
)
async def delete_project(
    project: ProjectDep,
    session: SessionDep,
) -> None:
    """Cancel an in-progress project or delete a completed one."""
    # If in progress, mark as cancelled
    if project.status in (
        ProjectStatus.ANALYZING,
        ProjectStatus.GENERATING,
        ProjectStatus.DEPLOYING,
    ):
        project.status = ProjectStatus.CANCELLED
        await session.update_project(project)
    else:
        await session.delete_project(project.id)


@router.get(
    "/{project_id}/clarifications",
    response_model=ClarificationResponse,
    summary="Get pending clarification questions",
)
async def get_clarifications(project: ProjectDep) -> ClarificationResponse:
    """Get any pending clarification questions for a project."""
    pending_questions = [
        q for q in project.clarification_questions if not q.answered
    ]

    return ClarificationResponse(
        project_id=project.id,
        status=project.status,
        questions=pending_questions,
    )


@router.post(
    "/{project_id}/clarify",
    response_model=ProjectResponse,
    summary="Submit clarification answers",
)
async def submit_clarifications(
    project: ProjectDep,
    data: SubmitClarificationsRequest,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> ProjectResponse:
    """Submit answers to clarification questions."""
    if project.status != ProjectStatus.CLARIFYING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is not awaiting clarifications",
        )

    # Map answers to questions
    answer_map = {r.question_id: r.answer for r in data.responses}

    for question in project.clarification_questions:
        if question.id in answer_map:
            question.answered = True
            question.answer = answer_map[question.id]

    # Check if all required questions are answered
    unanswered_required = [
        q
        for q in project.clarification_questions
        if q.required and not q.answered
    ]

    if not unanswered_required:
        # Resume processing
        project.status = ProjectStatus.ANALYZING
        await session.update_project(project)
        
        # Resume the pipeline in background
        background_tasks.add_task(run_pipeline_background, project.id)
    else:
        await session.update_project(project)

    return ProjectResponse.from_project(project)


@router.get(
    "/{project_id}/stream",
    summary="Stream project events (SSE)",
)
async def stream_project_events(
    project: ProjectDep,
    events: EventsDep,
) -> EventSourceResponse:
    """Stream real-time events for a project using Server-Sent Events."""

    async def event_generator():
        queue = events.subscribe(project.id)

        try:
            # Send initial status
            yield {
                "event": "connected",
                "data": {
                    "project_id": str(project.id),
                    "status": project.status.value,
                },
            }

            # Stream events until project completes or client disconnects
            while True:
                try:
                    event: Event = await asyncio.wait_for(
                        queue.get(), timeout=30.0
                    )
                    yield {
                        "event": event.event_type,
                        "data": event.data,
                    }

                    # Stop streaming on terminal events
                    if event.event_type in ("deployment_complete", "error"):
                        break

                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "keepalive", "data": {}}

        finally:
            events.unsubscribe(project.id)

    return EventSourceResponse(event_generator())
