"""Unit tests for session management."""

import pytest

from app.core.session import SessionManager
from app.models.project import ProjectCreate, ProjectOptions, ProjectStatus


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.fixture
    def manager(self) -> SessionManager:
        """Create a fresh session manager."""
        return SessionManager()

    @pytest.fixture
    def project_data(self) -> ProjectCreate:
        """Sample project creation data."""
        return ProjectCreate(
            name="test-project",
            spec_format="markdown",
            spec_content="# Test Project\n\nThis is a test.",
            options=ProjectOptions(),
        )

    @pytest.mark.asyncio
    async def test_create_project(self, manager: SessionManager, project_data: ProjectCreate):
        """Test creating a project."""
        project = await manager.create_project(project_data)

        assert project.name == "test-project"
        assert project.spec_format == "markdown"
        assert project.status == ProjectStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_project(self, manager: SessionManager, project_data: ProjectCreate):
        """Test retrieving a project."""
        created = await manager.create_project(project_data)
        retrieved = await manager.get_project(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, manager: SessionManager):
        """Test getting a project that doesn't exist."""
        from uuid import uuid4

        result = await manager.get_project(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_project(self, manager: SessionManager, project_data: ProjectCreate):
        """Test updating a project."""
        project = await manager.create_project(project_data)
        project.status = ProjectStatus.ANALYZING

        updated = await manager.update_project(project)

        assert updated.status == ProjectStatus.ANALYZING

        # Verify persistence
        retrieved = await manager.get_project(project.id)
        assert retrieved is not None
        assert retrieved.status == ProjectStatus.ANALYZING

    @pytest.mark.asyncio
    async def test_delete_project(self, manager: SessionManager, project_data: ProjectCreate):
        """Test deleting a project."""
        project = await manager.create_project(project_data)

        result = await manager.delete_project(project.id)
        assert result is True

        # Verify deletion
        retrieved = await manager.get_project(project.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project(self, manager: SessionManager):
        """Test deleting a project that doesn't exist."""
        from uuid import uuid4

        result = await manager.delete_project(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_list_projects(self, manager: SessionManager, project_data: ProjectCreate):
        """Test listing projects."""
        # Create multiple projects
        for i in range(5):
            data = ProjectCreate(
                name=f"test-project-{i}",
                spec_format="markdown",
                spec_content=f"# Project {i}\n\nDescription",
            )
            await manager.create_project(data)

        projects, total = await manager.list_projects()

        assert total == 5
        assert len(projects) == 5

    @pytest.mark.asyncio
    async def test_list_projects_with_filter(self, manager: SessionManager):
        """Test listing projects with status filter."""
        # Create projects with different statuses
        for status in [ProjectStatus.PENDING, ProjectStatus.ANALYZING, ProjectStatus.DEPLOYED]:
            data = ProjectCreate(
                name=f"project-{status.value}",
                spec_format="markdown",
                spec_content="# Test\n\nDescription",
            )
            project = await manager.create_project(data)
            project.status = status
            await manager.update_project(project)

        # Filter by deployed
        projects, total = await manager.list_projects(status=ProjectStatus.DEPLOYED)

        assert total == 1
        assert projects[0].status == ProjectStatus.DEPLOYED

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, manager: SessionManager):
        """Test listing projects with pagination."""
        # Create 10 projects
        for i in range(10):
            data = ProjectCreate(
                name=f"project-{i}",
                spec_format="markdown",
                spec_content=f"# Project {i}\n\nDescription",
            )
            await manager.create_project(data)

        # Get first page
        projects, total = await manager.list_projects(limit=3, offset=0)
        assert len(projects) == 3
        assert total == 10

        # Get second page
        projects2, _ = await manager.list_projects(limit=3, offset=3)
        assert len(projects2) == 3

        # Verify different projects
        ids1 = {p.id for p in projects}
        ids2 = {p.id for p in projects2}
        assert ids1.isdisjoint(ids2)
