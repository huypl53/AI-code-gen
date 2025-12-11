"""Dependency injection for API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.core.events import EventBus, get_event_bus
from app.core.exceptions import ProjectNotFoundError
from app.core.session import SessionManager, get_session_manager
from app.models.project import Project


async def get_session() -> SessionManager:
    """Get the session manager."""
    return get_session_manager()


async def get_events() -> EventBus:
    """Get the event bus."""
    return get_event_bus()


async def get_project_by_id(
    project_id: UUID,
    session: Annotated[SessionManager, Depends(get_session)],
) -> Project:
    """Get a project by ID or raise 404."""
    project = await session.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}",
        )
    return project


# Type aliases for cleaner signatures
SessionDep = Annotated[SessionManager, Depends(get_session)]
EventsDep = Annotated[EventBus, Depends(get_events)]
ProjectDep = Annotated[Project, Depends(get_project_by_id)]
