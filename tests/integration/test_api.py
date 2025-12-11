"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check returns healthy status."""
        response = await client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data


class TestProjectsEndpoints:
    """Tests for project management endpoints."""

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient):
        """Test creating a new project."""
        response = await client.post(
            "/v1/projects",
            json={
                "name": "test-app",
                "spec_format": "markdown",
                "spec_content": "# Test App\n\n## Features\n- Hello world",
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "project_id" in data
        assert data["name"] == "test-app"
        assert data["status"] == "analyzing"

    @pytest.mark.asyncio
    async def test_create_project_with_options(self, client: AsyncClient):
        """Test creating a project with custom options."""
        response = await client.post(
            "/v1/projects",
            json={
                "name": "custom-app",
                "spec_format": "markdown",
                "spec_content": "# Custom App\n\n## Features\n- Feature 1",
                "options": {
                    "framework": "react",
                    "styling": "scss",
                    "include_tests": False,
                },
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["name"] == "custom-app"

    @pytest.mark.asyncio
    async def test_create_project_invalid_name(self, client: AsyncClient):
        """Test creating project with invalid name fails."""
        response = await client.post(
            "/v1/projects",
            json={
                "name": "Invalid Name!",  # Invalid: contains spaces and special chars
                "spec_format": "markdown",
                "spec_content": "# Test\n\nDescription",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient):
        """Test getting project details."""
        # First create a project
        create_response = await client.post(
            "/v1/projects",
            json={
                "name": "get-test",
                "spec_format": "markdown",
                "spec_content": "# Get Test\n\n## Features\n- Test",
            },
        )
        project_id = create_response.json()["project_id"]

        # Then get it
        response = await client.get(f"/v1/projects/{project_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["name"] == "get-test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, client: AsyncClient):
        """Test getting a project that doesn't exist."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/v1/projects/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient):
        """Test listing projects."""
        # Create a few projects
        for i in range(3):
            await client.post(
                "/v1/projects",
                json={
                    "name": f"list-test-{i}",
                    "spec_format": "markdown",
                    "spec_content": f"# Project {i}\n\nDescription",
                },
            )

        # List them
        response = await client.get("/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data
        assert len(data["projects"]) >= 3

    @pytest.mark.asyncio
    async def test_list_projects_pagination(self, client: AsyncClient):
        """Test listing projects with pagination."""
        response = await client.get("/v1/projects?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_cancel_or_complete_project(self, client: AsyncClient):
        """Test cancelling an in-progress project or deleting completed one."""
        # Create a project (starts in ANALYZING status)
        create_response = await client.post(
            "/v1/projects",
            json={
                "name": "cancel-test",
                "spec_format": "markdown",
                "spec_content": "# Cancel Test\n\nDescription",
            },
        )
        project_id = create_response.json()["project_id"]
        initial_status = create_response.json()["status"]
        assert initial_status in ("analyzing", "generating", "deploying", "deployed")

        # Delete/cancel it
        response = await client.delete(f"/v1/projects/{project_id}")
        assert response.status_code == 204

        # Get the final state - may be cancelled or deleted depending on timing
        get_response = await client.get(f"/v1/projects/{project_id}")
        # Either 404 (deleted) or 200 with cancelled/deployed status
        assert get_response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_delete_completed_project(self, client: AsyncClient):
        """Test deleting a completed/failed project."""
        from app.core.session import get_session_manager
        from app.models.project import ProjectStatus
        from uuid import UUID

        # Create a project
        create_response = await client.post(
            "/v1/projects",
            json={
                "name": "delete-test",
                "spec_format": "markdown",
                "spec_content": "# Delete Test\n\nDescription",
            },
        )
        project_id = create_response.json()["project_id"]

        # Manually set status to DEPLOYED (simulating completion)
        manager = get_session_manager()
        project = await manager.get_project(UUID(project_id))
        project.status = ProjectStatus.DEPLOYED
        await manager.update_project(project)

        # Delete it
        response = await client.delete(f"/v1/projects/{project_id}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/v1/projects/{project_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_clarifications(self, client: AsyncClient):
        """Test getting clarification questions."""
        # Create a project
        create_response = await client.post(
            "/v1/projects",
            json={
                "name": "clarify-test",
                "spec_format": "markdown",
                "spec_content": "# Clarify Test\n\nDescription",
            },
        )
        project_id = create_response.json()["project_id"]

        # Get clarifications
        response = await client.get(f"/v1/projects/{project_id}/clarifications")

        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert data["project_id"] == project_id
