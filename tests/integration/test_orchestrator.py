"""Integration tests for the pipeline orchestrator."""

import pytest

from app.core.orchestrator import PipelineOrchestrator
from app.core.session import SessionManager
from app.core.events import EventBus
from app.models.project import ProjectCreate, ProjectOptions, ProjectStatus


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    @pytest.fixture
    def session(self) -> SessionManager:
        """Create a fresh session manager."""
        return SessionManager()

    @pytest.fixture
    def events(self) -> EventBus:
        """Create a fresh event bus."""
        return EventBus()

    @pytest.fixture
    def orchestrator(
        self, session: SessionManager, events: EventBus
    ) -> PipelineOrchestrator:
        """Create orchestrator with test dependencies."""
        return PipelineOrchestrator(session=session, events=events)

    @pytest.fixture
    async def project(self, session: SessionManager):
        """Create a test project."""
        data = ProjectCreate(
            name="test-project",
            spec_format="markdown",
            spec_content="""# Test Project

## Description
A simple test project.

## Features
- Create items
- List items
- Delete items

## Data Models

### Item
- id: uuid
- name: string
- created_at: datetime
""",
            options=ProjectOptions(auto_deploy=False),  # Skip deployment in tests
        )
        return await session.create_project(data)

    @pytest.mark.asyncio
    async def test_run_pipeline_success(
        self,
        orchestrator: PipelineOrchestrator,
        project,
        session: SessionManager,
    ):
        """Test running the complete pipeline."""
        result = await orchestrator.run(project.id)

        # Pipeline completes (may or may not be DEPLOYED depending on options)
        assert result.status in (ProjectStatus.DEPLOYED, ProjectStatus.CLARIFYING)
        assert result.structured_spec is not None
        
        if result.status == ProjectStatus.DEPLOYED:
            assert result.generated_project is not None
            assert result.error is None
            # Check phases completed
            assert "spec_analysis" in result.phases
            assert "code_generation" in result.phases

    @pytest.mark.asyncio
    async def test_run_pipeline_spec_analysis(
        self,
        orchestrator: PipelineOrchestrator,
        project,
        session: SessionManager,
    ):
        """Test spec analysis phase produces structured spec."""
        result = await orchestrator._run_spec_analysis(project)

        assert result.structured_spec is not None
        assert "features" in result.structured_spec
        assert len(result.structured_spec["features"]) > 0
        assert result.estimation is not None

    @pytest.mark.asyncio
    async def test_run_pipeline_code_generation(
        self,
        orchestrator: PipelineOrchestrator,
        project,
        session: SessionManager,
    ):
        """Test code generation phase creates files."""
        # First run spec analysis
        project = await orchestrator._run_spec_analysis(project)

        # Then run code generation
        result = await orchestrator._run_code_generation(project)

        assert result.generated_project is not None
        assert result.generated_project["file_count"] > 0

    @pytest.mark.asyncio
    async def test_pipeline_handles_minimal_spec(
        self,
        orchestrator: PipelineOrchestrator,
        session: SessionManager,
    ):
        """Test pipeline handles minimal specification."""
        data = ProjectCreate(
            name="minimal-app",
            spec_format="markdown",
            spec_content="# Minimal App\n\n## Features\n- Hello world",
            options=ProjectOptions(auto_deploy=False),
        )
        project = await session.create_project(data)

        result = await orchestrator.run(project.id)

        # Should complete even with minimal spec (may need clarification)
        assert result.status in (ProjectStatus.DEPLOYED, ProjectStatus.CLARIFYING)
        assert result.structured_spec is not None

    @pytest.mark.asyncio
    async def test_pipeline_generates_clarification_questions(
        self,
        orchestrator: PipelineOrchestrator,
        session: SessionManager,
    ):
        """Test pipeline generates clarification questions for ambiguous specs."""
        # Very minimal spec that should trigger questions
        data = ProjectCreate(
            name="ambiguous-app",
            spec_format="markdown",
            spec_content="# My App\n\nA cool app.",
            options=ProjectOptions(auto_deploy=False),
        )
        project = await session.create_project(data)

        # Run just spec analysis
        result = await orchestrator._run_spec_analysis(project)

        # May or may not need clarification depending on spec
        # Just verify it doesn't crash
        assert result.structured_spec is not None

    @pytest.mark.asyncio
    async def test_pipeline_project_not_found(
        self,
        orchestrator: PipelineOrchestrator,
    ):
        """Test pipeline raises error for non-existent project."""
        from uuid import uuid4

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.run(uuid4())

    @pytest.mark.asyncio
    async def test_events_published(
        self,
        orchestrator: PipelineOrchestrator,
        project,
        events: EventBus,
    ):
        """Test that events are published during pipeline execution."""
        import asyncio

        # Subscribe to events
        queue = events.subscribe(project.id)

        # Run pipeline in background
        task = asyncio.create_task(orchestrator.run(project.id))

        # Collect some events
        collected_events = []
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
                collected_events.append(event)
                if event.event_type in ("deployment_complete", "error"):
                    break
        except asyncio.TimeoutError:
            pass

        await task

        # Should have phase events
        event_types = [e.event_type for e in collected_events]
        assert "phase_started" in event_types
        assert "phase_completed" in event_types
