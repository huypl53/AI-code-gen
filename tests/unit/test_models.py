"""Unit tests for data models."""

from datetime import datetime
from uuid import UUID

import pytest

from app.models.project import (
    ClarificationQuestion,
    PhaseInfo,
    PhaseStatus,
    Project,
    ProjectCreate,
    ProjectOptions,
    ProjectResponse,
    ProjectStatus,
)
from app.models.spec import (
    DataModel,
    Feature,
    ModelField,
    StructuredSpec,
)


class TestProjectModels:
    """Tests for project-related models."""

    def test_project_create_validation(self):
        """Test ProjectCreate validation."""
        # Valid project
        project = ProjectCreate(
            name="my-app",
            spec_format="markdown",
            spec_content="# My App\n\nDescription here",
        )
        assert project.name == "my-app"
        assert project.spec_format == "markdown"

    def test_project_create_invalid_name(self):
        """Test ProjectCreate rejects invalid names."""
        with pytest.raises(ValueError):
            ProjectCreate(
                name="My App",  # spaces not allowed
                spec_format="markdown",
                spec_content="# My App",
            )

    def test_project_create_name_too_short(self):
        """Test ProjectCreate rejects empty names."""
        with pytest.raises(ValueError):
            ProjectCreate(
                name="",
                spec_format="markdown",
                spec_content="# My App",
            )

    def test_project_create_content_too_short(self):
        """Test ProjectCreate rejects short content."""
        with pytest.raises(ValueError):
            ProjectCreate(
                name="my-app",
                spec_format="markdown",
                spec_content="short",
            )

    def test_project_defaults(self):
        """Test Project default values."""
        project = Project(
            name="test-app",
            spec_format="markdown",
            spec_content="# Test",
            options=ProjectOptions(),
        )

        assert isinstance(project.id, UUID)
        assert project.status == ProjectStatus.PENDING
        assert project.current_phase is None
        assert project.phases == {}
        assert project.error is None

    def test_project_update_phase(self):
        """Test Project.update_phase method."""
        project = Project(
            name="test-app",
            spec_format="markdown",
            spec_content="# Test",
            options=ProjectOptions(),
        )

        # Start a phase
        project.update_phase("spec_analysis", PhaseStatus.IN_PROGRESS)

        assert project.current_phase == "spec_analysis"
        assert "spec_analysis" in project.phases
        assert project.phases["spec_analysis"].status == PhaseStatus.IN_PROGRESS
        assert project.phases["spec_analysis"].started_at is not None

        # Complete the phase
        project.update_phase(
            "spec_analysis",
            PhaseStatus.COMPLETED,
            metadata={"files_processed": 1},
        )

        assert project.phases["spec_analysis"].status == PhaseStatus.COMPLETED
        assert project.phases["spec_analysis"].completed_at is not None
        assert project.phases["spec_analysis"].duration_ms is not None
        assert project.phases["spec_analysis"].metadata["files_processed"] == 1

    def test_project_update_phase_failure(self):
        """Test Project.update_phase with failure."""
        project = Project(
            name="test-app",
            spec_format="markdown",
            spec_content="# Test",
            options=ProjectOptions(),
        )

        project.update_phase("spec_analysis", PhaseStatus.IN_PROGRESS)
        project.update_phase(
            "spec_analysis",
            PhaseStatus.FAILED,
            error="Parse error on line 42",
        )

        assert project.phases["spec_analysis"].status == PhaseStatus.FAILED
        assert project.phases["spec_analysis"].error == "Parse error on line 42"
        assert project.error == "Parse error on line 42"
        assert project.error_phase == "spec_analysis"

    def test_project_response_from_project(self):
        """Test ProjectResponse.from_project."""
        project = Project(
            name="test-app",
            spec_format="markdown",
            spec_content="# Test",
            options=ProjectOptions(),
            deployment_result={"url": "https://test.vercel.app"},
        )

        response = ProjectResponse.from_project(project)

        assert response.project_id == project.id
        assert response.name == "test-app"
        assert response.result is not None
        assert response.result["url"] == "https://test.vercel.app"

    def test_clarification_question(self):
        """Test ClarificationQuestion model."""
        question = ClarificationQuestion(
            category="feature",
            question="Should tasks have due dates?",
            options=["Yes", "No", "Optional"],
        )

        assert question.id.startswith("q_")
        assert question.required is True
        assert question.answered is False
        assert question.answer is None


class TestSpecModels:
    """Tests for specification models."""

    def test_feature_model(self):
        """Test Feature model."""
        feature = Feature(
            id="f1",
            name="User Authentication",
            description="Users can log in",
            priority="must",
            user_stories=["As a user, I can login"],
            acceptance_criteria=["Login form exists"],
        )

        assert feature.id == "f1"
        assert feature.priority == "must"
        assert len(feature.user_stories) == 1

    def test_data_model(self):
        """Test DataModel model."""
        model = DataModel(
            name="User",
            description="Application user",
            fields=[
                ModelField(name="id", type="uuid", required=True),
                ModelField(name="email", type="string", validation="email"),
                ModelField(name="name", type="string", required=False),
            ],
        )

        assert model.name == "User"
        assert len(model.fields) == 3
        assert model.fields[1].validation == "email"

    def test_structured_spec(self):
        """Test StructuredSpec model."""
        spec = StructuredSpec(
            project_name="my-app",
            description="A test application",
            features=[
                Feature(id="f1", name="Feature 1", description="Desc 1"),
            ],
            estimated_complexity="simple",
        )

        assert spec.project_name == "my-app"
        assert len(spec.features) == 1
        assert spec.estimated_complexity == "simple"
