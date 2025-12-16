"""Session management for projects."""

from datetime import datetime, timedelta
from functools import lru_cache
from typing import AsyncIterator
from uuid import UUID

from app.models.project import Project, ProjectCreate, ProjectStatus


class SessionManager:
    """Manages project sessions in memory.
    
    Note: For production, this should be backed by Redis or a database.
    """

    def __init__(self, ttl_hours: int = 24):
        self._projects: dict[UUID, Project] = {}
        self._ttl = timedelta(hours=ttl_hours)

    async def create_project(self, data: ProjectCreate) -> Project:
        """Create a new project."""
        project = Project(
            name=data.name,
            spec_format=data.spec_format,
            spec_content=data.spec_content,
            template_id=data.template_id,
            options=data.options,
        )
        self._projects[project.id] = project
        return project

    async def get_project(self, project_id: UUID) -> Project | None:
        """Get a project by ID."""
        project = self._projects.get(project_id)
        if project:
            # Check if expired
            if datetime.utcnow() - project.created_at > self._ttl:
                del self._projects[project_id]
                return None
        return project

    async def update_project(self, project: Project) -> Project:
        """Update a project."""
        project.updated_at = datetime.utcnow()
        self._projects[project.id] = project
        return project

    async def delete_project(self, project_id: UUID) -> bool:
        """Delete a project."""
        if project_id in self._projects:
            del self._projects[project_id]
            return True
        return False

    async def list_projects(
        self,
        status: ProjectStatus | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Project], int]:
        """List projects with optional filtering."""
        projects = list(self._projects.values())

        # Filter by status
        if status:
            projects = [p for p in projects if p.status == status]

        # Sort by created_at descending
        projects.sort(key=lambda p: p.created_at, reverse=True)

        total = len(projects)
        projects = projects[offset : offset + limit]

        return projects, total

    async def cleanup_expired(self) -> int:
        """Remove expired projects. Returns count of removed projects."""
        now = datetime.utcnow()
        expired = [
            pid
            for pid, project in self._projects.items()
            if now - project.created_at > self._ttl
        ]
        for pid in expired:
            del self._projects[pid]
        return len(expired)


# Singleton instance
_session_manager: SessionManager | None = None


@lru_cache
def get_session_manager() -> SessionManager:
    """Get the session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
