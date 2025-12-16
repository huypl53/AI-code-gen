"""Unit tests for agents."""

import pytest

from app.agents.spec_agent import SpecAnalysisAgent, SpecAnalysisInput


class TestSpecAnalysisAgent:
    """Tests for SpecAnalysisAgent."""

    @pytest.fixture
    def agent(self) -> SpecAnalysisAgent:
        return SpecAnalysisAgent()

    def test_agent_properties(self, agent: SpecAnalysisAgent):
        """Test agent has required properties."""
        assert agent.name == "spec_analysis"
        assert agent.description
        assert agent.system_prompt
        assert "Read" in agent.tools

    @pytest.mark.asyncio
    async def test_analyze_markdown_spec(
        self, agent: SpecAnalysisAgent, sample_markdown_spec: str
    ):
        """Test analyzing markdown specification."""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=sample_markdown_spec,
            project_name="todo-app",
        )

        result = await agent.execute(input_data)

        assert result.structured_spec is not None
        assert result.structured_spec.project_name == "todo-app"
        assert len(result.structured_spec.features) > 0

    @pytest.mark.asyncio
    async def test_analyze_csv_spec(
        self, agent: SpecAnalysisAgent, sample_csv_spec: str
    ):
        """Test analyzing CSV specification."""
        input_data = SpecAnalysisInput(
            spec_format="csv",
            spec_content=sample_csv_spec,
            project_name="task-manager",
        )

        result = await agent.execute(input_data)

        assert result.structured_spec is not None
        assert result.structured_spec.project_name == "task-manager"
        assert len(result.structured_spec.features) > 0

    @pytest.mark.asyncio
    async def test_generates_clarification_questions(
        self, agent: SpecAnalysisAgent
    ):
        """Test that agent generates clarification questions for incomplete specs."""
        # Minimal spec missing data models
        minimal_spec = """# My App

## Features
- Create items
- Delete items
"""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=minimal_spec,
            project_name="my-app",
        )

        result = await agent.execute(input_data)

        # Should have questions about missing data models
        assert len(result.clarification_questions) > 0
        assert result.needs_clarification is True

    @pytest.mark.asyncio
    async def test_generates_estimation(
        self, agent: SpecAnalysisAgent, sample_markdown_spec: str
    ):
        """Agent should emit estimation breakdown and CSV."""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=sample_markdown_spec,
            project_name="estimate-app",
        )

        result = await agent.execute(input_data)

        assert result.estimation is not None
        assert result.estimation.csv

    @pytest.mark.asyncio
    async def test_estimates_complexity_simple(self, agent: SpecAnalysisAgent):
        """Test complexity estimation for simple spec."""
        simple_spec = """# Simple App

## Features
- Hello world
- About page
"""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=simple_spec,
            project_name="simple-app",
        )

        result = await agent.execute(input_data)

        assert result.structured_spec.estimated_complexity == "simple"

    @pytest.mark.asyncio
    async def test_estimates_complexity_complex(self, agent: SpecAnalysisAgent):
        """Test complexity estimation for complex spec."""
        complex_spec = """# Complex App

## Features
- User authentication with OAuth
- Real-time notifications via WebSocket
- Payment processing
- Analytics dashboard
- Export to PDF
- Multi-user collaboration
- Version history
- API integrations
- Email notifications
- Role-based access control
- Audit logging

## Data Models

### User
- id: uuid
- email: string
- password: string

### Payment
- id: uuid
- amount: number
- status: string

### Notification
- id: uuid
- message: string
- read: boolean

### AuditLog
- id: uuid
- action: string
- timestamp: datetime

### Team
- id: uuid
- name: string

### Role
- id: uuid
- name: string
- permissions: json
"""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=complex_spec,
            project_name="complex-app",
        )

        result = await agent.execute(input_data)

        assert result.structured_spec.estimated_complexity in ("medium", "complex")

    @pytest.mark.asyncio
    async def test_tech_recommendations(self, agent: SpecAnalysisAgent):
        """Test that agent provides tech recommendations."""
        spec = """# App

## Features
- Task management
"""
        input_data = SpecAnalysisInput(
            spec_format="markdown",
            spec_content=spec,
            project_name="app",
        )

        result = await agent.execute(input_data)

        assert result.structured_spec.tech_recommendations is not None
        assert result.structured_spec.tech_recommendations.framework == "nextjs"
        assert result.structured_spec.tech_recommendations.styling == "tailwind"

    def test_identify_gaps_missing_models(self, agent: SpecAnalysisAgent):
        """Test gap identification for missing data models."""
        from app.models.spec import Feature

        features = [Feature(id="f1", name="Create Task", description="Create tasks")]
        data_models = []
        api_endpoints = []
        ui_components = []

        questions = agent._identify_gaps(
            features=features,
            data_models=data_models,
            api_endpoints=api_endpoints,
            ui_components=ui_components,
        )

        # Should ask about data models
        model_questions = [q for q in questions if q.category == "technical"]
        assert len(model_questions) > 0

    def test_identify_gaps_auth_check(self, agent: SpecAnalysisAgent):
        """Test gap identification for authentication."""
        from app.models.spec import Feature

        # Features without auth
        features = [
            Feature(id="f1", name="View Dashboard", description="View the dashboard"),
            Feature(id="f2", name="Create Report", description="Create reports"),
        ]

        questions = agent._identify_gaps(
            features=features,
            data_models=[],
            api_endpoints=[],
            ui_components=[],
        )

        # Should ask about authentication
        auth_questions = [q for q in questions if "authentication" in q.question.lower()]
        assert len(auth_questions) > 0

    def test_estimate_complexity_scoring(self, agent: SpecAnalysisAgent):
        """Test complexity scoring logic."""
        from app.models.spec import Feature, DataModel, APIEndpoint

        # Few items = simple
        complexity = agent._estimate_complexity(
            features=[Feature(id="f1", name="F1", description="")],
            data_models=[],
            api_endpoints=[],
        )
        assert complexity == "simple"

        # Many items = complex
        features = [Feature(id=f"f{i}", name=f"Feature {i}", description="") for i in range(15)]
        models = [DataModel(name=f"Model{i}", description="") for i in range(6)]
        endpoints = [APIEndpoint(method="GET", path=f"/api/{i}", description="") for i in range(20)]

        complexity = agent._estimate_complexity(
            features=features,
            data_models=models,
            api_endpoints=endpoints,
        )
        assert complexity == "complex"
