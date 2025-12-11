"""Unit tests for coding agent."""

import tempfile
from pathlib import Path

import pytest

from app.agents.coding_agent import CodingAgent, CodingAgentInput
from app.generators.nextjs.project import NextJSProjectGenerator
from app.models.generation import CodeGenOptions
from app.models.spec import (
    APIEndpoint,
    DataModel,
    Feature,
    ModelField,
    StructuredSpec,
    UIComponent,
)


@pytest.fixture
def sample_spec() -> StructuredSpec:
    """Create a sample structured specification."""
    return StructuredSpec(
        project_name="test-app",
        description="A test application",
        features=[
            Feature(id="f1", name="Create Items", description="Create new items"),
            Feature(id="f2", name="List Items", description="View all items"),
            Feature(id="f3", name="Delete Items", description="Remove items"),
        ],
        data_models=[
            DataModel(
                name="Item",
                description="An item entity",
                fields=[
                    ModelField(name="id", type="uuid", required=True),
                    ModelField(name="name", type="string", required=True),
                    ModelField(name="description", type="string", required=False),
                    ModelField(name="created_at", type="datetime", required=True),
                ],
            ),
        ],
        api_endpoints=[
            APIEndpoint(method="GET", path="/api/items", description="List all items"),
            APIEndpoint(method="POST", path="/api/items", description="Create an item"),
            APIEndpoint(method="DELETE", path="/api/items/{id}", description="Delete an item"),
        ],
        ui_components=[
            UIComponent(name="ItemList", type="component", description="List of items"),
            UIComponent(name="ItemForm", type="component", description="Form for creating items"),
        ],
    )


class TestCodingAgent:
    """Tests for CodingAgent."""

    @pytest.fixture
    def agent(self) -> CodingAgent:
        return CodingAgent()

    def test_agent_properties(self, agent: CodingAgent):
        """Test agent has required properties."""
        assert agent.name == "coding"
        assert agent.description
        assert agent.system_prompt
        assert "Write" in agent.tools

    @pytest.mark.asyncio
    async def test_generate_project_template_mode(
        self, agent: CodingAgent, sample_spec: StructuredSpec
    ):
        """Test generating project using templates (no API key)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_data = CodingAgentInput(
                spec=sample_spec,
                options=CodeGenOptions(include_tests=False),
                output_directory=tmpdir,
            )

            result = await agent.execute(input_data)

            assert result.success is True
            assert result.project is not None
            assert result.project.file_count > 0

            # Check key files exist
            output_dir = Path(tmpdir)
            assert (output_dir / "package.json").exists()
            assert (output_dir / "src/app/page.tsx").exists()
            assert (output_dir / "src/app/layout.tsx").exists()

    def test_determine_file_type(self, agent: CodingAgent):
        """Test file type determination."""
        assert agent._determine_file_type("src/test/file.test.ts") == "test"
        assert agent._determine_file_type("README.md") == "docs"
        assert agent._determine_file_type("package.json") == "config"
        assert agent._determine_file_type("public/logo.png") == "asset"
        assert agent._determine_file_type("src/app/page.tsx") == "source"


class TestNextJSProjectGenerator:
    """Tests for NextJSProjectGenerator."""

    @pytest.fixture
    def generator(self, sample_spec: StructuredSpec) -> NextJSProjectGenerator:
        with tempfile.TemporaryDirectory() as tmpdir:
            return NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

    @pytest.mark.asyncio
    async def test_generate_creates_files(self, sample_spec: StructuredSpec):
        """Test that generate creates all expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            project = await generator.generate()

            assert project.file_count > 0
            assert project.output_directory == tmpdir

            # Check for essential files
            file_paths = [f.path for f in project.files]
            assert "package.json" in file_paths
            assert "tsconfig.json" in file_paths
            assert "src/app/page.tsx" in file_paths
            assert "src/app/layout.tsx" in file_paths

    @pytest.mark.asyncio
    async def test_generate_creates_types(self, sample_spec: StructuredSpec):
        """Test that types are generated from data models."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            project = await generator.generate()

            # Find types file
            types_file = next(
                (f for f in project.files if f.path == "src/types/index.ts"), None
            )

            assert types_file is not None
            assert "interface Item" in types_file.content
            assert "name: string" in types_file.content

    @pytest.mark.asyncio
    async def test_generate_creates_api_routes(self, sample_spec: StructuredSpec):
        """Test that API routes are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            project = await generator.generate()

            # Find API route files
            api_files = [f for f in project.files if "api/" in f.path]
            assert len(api_files) > 0

    @pytest.mark.asyncio
    async def test_generate_creates_components(self, sample_spec: StructuredSpec):
        """Test that components are generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            project = await generator.generate()

            # Find component files
            component_files = [f for f in project.files if "components/" in f.path]
            assert len(component_files) > 0

            # Check for standard components
            file_paths = [f.path for f in project.files]
            assert "src/components/Button.tsx" in file_paths
            assert "src/components/Input.tsx" in file_paths
            assert "src/components/Card.tsx" in file_paths

    @pytest.mark.asyncio
    async def test_generate_creates_readme(self, sample_spec: StructuredSpec):
        """Test that README is generated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            project = await generator.generate()

            readme = next((f for f in project.files if f.path == "README.md"), None)
            assert readme is not None
            assert sample_spec.project_name in readme.content
            assert sample_spec.description in readme.content

    @pytest.mark.asyncio
    async def test_files_written_to_disk(self, sample_spec: StructuredSpec):
        """Test that files are actually written to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            await generator.generate()

            # Check files exist on disk
            assert (Path(tmpdir) / "package.json").exists()
            assert (Path(tmpdir) / "src" / "app" / "page.tsx").exists()
            assert (Path(tmpdir) / "src" / "components" / "Button.tsx").exists()

    def test_get_ts_type(self, sample_spec: StructuredSpec):
        """Test TypeScript type conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = NextJSProjectGenerator(
                spec=sample_spec,
                options=CodeGenOptions(),
                output_dir=Path(tmpdir),
            )

            assert generator._get_ts_type("string") == "string"
            assert generator._get_ts_type("number") == "number"
            assert generator._get_ts_type("boolean") == "boolean"
            assert generator._get_ts_type("uuid") == "string"
            assert generator._get_ts_type("datetime") == "Date"
            assert generator._get_ts_type("json") == "Record<string, unknown>"
