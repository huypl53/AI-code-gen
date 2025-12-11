"""Unit tests for devops agent."""

import json
import tempfile
from pathlib import Path

import pytest

from app.agents.devops_agent import DevopsAgent, DevopsAgentInput


class TestDevopsAgent:
    """Tests for DevopsAgent."""

    @pytest.fixture
    def agent(self) -> DevopsAgent:
        return DevopsAgent()

    @pytest.fixture
    def valid_project_dir(self) -> Path:
        """Create a valid project directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # Create package.json
            package_json = {
                "name": "test-project",
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                },
            }
            (project_dir / "package.json").write_text(json.dumps(package_json))

            yield project_dir

    def test_agent_properties(self, agent: DevopsAgent):
        """Test agent has required properties."""
        assert agent.name == "devops"
        assert agent.description
        assert agent.system_prompt
        assert "Bash" in agent.tools

    def test_validate_project_missing_dir(self, agent: DevopsAgent):
        """Test validation fails for missing directory."""
        error = agent._validate_project(Path("/nonexistent/path"))
        assert error is not None
        assert "not found" in error

    def test_validate_project_missing_package_json(self, agent: DevopsAgent):
        """Test validation fails for missing package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error = agent._validate_project(Path(tmpdir))
            assert error is not None
            assert "package.json" in error

    def test_validate_project_missing_build_script(self, agent: DevopsAgent):
        """Test validation fails for missing build script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            package_json = {"name": "test", "scripts": {"dev": "next dev"}}
            (project_dir / "package.json").write_text(json.dumps(package_json))

            error = agent._validate_project(project_dir)
            assert error is not None
            assert "build" in error

    def test_validate_project_valid(self, agent: DevopsAgent, valid_project_dir: Path):
        """Test validation passes for valid project."""
        error = agent._validate_project(valid_project_dir)
        assert error is None

    @pytest.mark.asyncio
    async def test_mock_deployment(self, agent: DevopsAgent, valid_project_dir: Path):
        """Test mock deployment when no Vercel token."""
        input_data = DevopsAgentInput(
            project_directory=str(valid_project_dir),
            project_name="test-project",
        )

        result = await agent.execute(input_data)

        assert result.success is True
        assert result.result.success is True
        assert result.result.url.startswith("https://")
        assert "vercel.app" in result.result.url
        assert result.result.deployment_id.startswith("dpl_")

    def test_extract_url(self, agent: DevopsAgent):
        """Test URL extraction from Vercel output."""
        output = """
Vercel CLI 32.5.0
Deploying...
https://my-app-abc123.vercel.app
"""
        url = agent._extract_url(output)
        assert url == "https://my-app-abc123.vercel.app"

    def test_extract_deployment_id(self, agent: DevopsAgent):
        """Test deployment ID extraction."""
        output = "Deployment dpl_abc123xyz complete"
        deployment_id = agent._extract_deployment_id(output)
        assert deployment_id == "dpl_abc123xyz"

    @pytest.mark.asyncio
    async def test_deployment_fails_invalid_project(self, agent: DevopsAgent):
        """Test deployment fails for invalid project."""
        input_data = DevopsAgentInput(
            project_directory="/nonexistent/path",
            project_name="test-project",
        )

        result = await agent.execute(input_data)

        assert result.success is False
        assert result.result.success is False
        assert result.result.error is not None
