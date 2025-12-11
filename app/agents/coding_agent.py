"""Coding Agent.

Generates complete, production-ready application code from structured specifications.
Uses claude-agent-sdk to leverage Claude's code generation capabilities.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config import settings
from app.models.generation import CodeGenOptions, GeneratedFile, GeneratedProject
from app.models.spec import StructuredSpec


class CodingAgentInput(BaseModel):
    """Input for the coding agent."""

    spec: StructuredSpec
    options: CodeGenOptions = Field(default_factory=CodeGenOptions)
    output_directory: str | None = None  # If None, uses temp directory


class CodingAgentOutput(BaseModel):
    """Output from the coding agent."""

    project: GeneratedProject
    success: bool = True
    error: str | None = None


class CodingAgent(BaseAgent[CodingAgentInput, CodingAgentOutput]):
    """Agent for generating application code from specifications.
    
    This agent:
    1. Analyzes the structured specification
    2. Creates project structure
    3. Generates all source code files
    4. Creates configuration files
    5. Generates tests
    """

    @property
    def name(self) -> str:
        return "coding"

    @property
    def description(self) -> str:
        return "Generates production-ready application code from structured specifications"

    @property
    def system_prompt(self) -> str:
        return """You are an expert full-stack developer generating production applications.

## Your Responsibilities
1. Create complete file/folder structure
2. Generate all source code files
3. Write comprehensive tests
4. Create configuration files (package.json, tsconfig, etc.)
5. Add documentation (README, inline comments)

## Code Quality Standards
- Follow framework best practices
- Use TypeScript with strict typing
- Implement proper error handling
- Add input validation
- Use meaningful variable/function names
- Add JSDoc comments for public APIs

## File Generation Order
1. Configuration files (package.json, tsconfig.json, etc.)
2. Database schema / data models
3. API routes and controllers
4. UI components (atomic → composite)
5. Pages and layouts
6. Utility functions
7. Tests
8. Documentation

## Technology Defaults
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- State: React Query + Zustand
- Validation: Zod
- Testing: Vitest + Testing Library
"""

    @property
    def tools(self) -> list[str]:
        return ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    @property
    def model(self) -> str:
        return "opus"  # Use most capable model for code generation

    async def execute(self, input_data: CodingAgentInput) -> CodingAgentOutput:
        """Execute code generation."""
        self.logger.info(
            "coding_agent.started",
            project=input_data.spec.project_name,
            framework=input_data.options.framework,
        )

        # Create output directory
        if input_data.output_directory:
            output_dir = Path(input_data.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = Path(tempfile.mkdtemp(prefix="appagent_"))

        try:
            # Use template-based generation for reliable, fast results
            # Claude-based generation is available but slower
            # TODO: Add config flag to enable Claude-based generation
            project = await self._generate_from_templates(
                spec=input_data.spec,
                options=input_data.options,
                output_dir=output_dir,
            )

            self.logger.info(
                "coding_agent.completed",
                files_count=project.file_count,
                total_lines=project.total_lines,
            )

            return CodingAgentOutput(project=project, success=True)

        except Exception as e:
            self.logger.error("coding_agent.failed", error=str(e))
            return CodingAgentOutput(
                project=GeneratedProject(output_directory=str(output_dir)),
                success=False,
                error=str(e),
            )

    async def _generate_with_claude(
        self,
        spec: StructuredSpec,
        options: CodeGenOptions,
        output_dir: Path,
    ) -> GeneratedProject:
        """Use Claude to generate the project."""
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

        files: list[GeneratedFile] = []

        agent_options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            allowed_tools=self.tools,
            permission_mode="acceptEdits",
            cwd=str(output_dir),
        )

        prompt = self._build_generation_prompt(spec, options)

        async with ClaudeSDKClient(options=agent_options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                # Claude will create files directly in the output directory
                pass

        # Scan generated files
        files = await self._scan_generated_files(output_dir)

        return GeneratedProject(
            output_directory=str(output_dir),
            files=files,
            dependencies=self._get_default_dependencies(options),
            dev_dependencies=self._get_default_dev_dependencies(options),
        )

    async def _generate_from_templates(
        self,
        spec: StructuredSpec,
        options: CodeGenOptions,
        output_dir: Path,
    ) -> GeneratedProject:
        """Generate project from templates (fallback when Claude not available)."""
        from app.generators.nextjs.project import NextJSProjectGenerator

        generator = NextJSProjectGenerator(
            spec=spec,
            options=options,
            output_dir=output_dir,
        )

        return await generator.generate()

    def _build_generation_prompt(
        self, spec: StructuredSpec, options: CodeGenOptions
    ) -> str:
        """Build the prompt for Claude to generate the project."""
        spec_json = spec.model_dump_json(indent=2)

        return f"""Generate a complete {options.framework} application based on this specification.

## Project Specification
```json
{spec_json}
```

## Generation Options
- Framework: {options.framework}
- Styling: {options.styling}
- TypeScript: {options.typescript}
- Include Tests: {options.include_tests}

## Requirements
1. Create a complete, working project structure
2. Generate all necessary configuration files (package.json, tsconfig.json, etc.)
3. Implement all features from the specification
4. Create all data models/types
5. Implement all API endpoints
6. Create all UI components
7. Add proper error handling
8. {"Generate unit tests for all components" if options.include_tests else ""}

## Important
- Use Next.js 14 with App Router
- Use Tailwind CSS for styling
- Create reusable, well-documented components
- Follow React best practices
- Add TypeScript types for everything

Please create all the necessary files now.
"""

    async def _scan_generated_files(self, output_dir: Path) -> list[GeneratedFile]:
        """Scan the output directory for generated files."""
        files: list[GeneratedFile] = []

        for root, _, filenames in os.walk(output_dir):
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(output_dir)

                # Skip node_modules and hidden files
                if "node_modules" in str(relative_path) or filename.startswith("."):
                    continue

                try:
                    content = file_path.read_text()
                    file_type = self._determine_file_type(str(relative_path))
                    files.append(
                        GeneratedFile(
                            path=str(relative_path),
                            content=content,
                            file_type=file_type,
                        )
                    )
                except Exception:
                    pass  # Skip binary files

        return files

    def _determine_file_type(self, path: str) -> str:
        """Determine the type of a file based on its path."""
        path_lower = path.lower()

        if "test" in path_lower or "spec" in path_lower:
            return "test"
        elif path_lower.endswith((".md", ".txt")):
            return "docs"
        elif path_lower.endswith((".json", ".yaml", ".yml", ".toml")):
            return "config"
        elif path_lower.endswith((".png", ".jpg", ".svg", ".ico")):
            return "asset"
        else:
            return "source"

    def _get_default_dependencies(self, options: CodeGenOptions) -> dict[str, str]:
        """Get default dependencies based on options."""
        deps = {
            "next": "14.0.0",
            "react": "18.2.0",
            "react-dom": "18.2.0",
        }

        if options.styling == "tailwind":
            deps["tailwindcss"] = "3.4.0"

        if options.typescript:
            deps["typescript"] = "5.3.0"

        return deps

    def _get_default_dev_dependencies(self, options: CodeGenOptions) -> dict[str, str]:
        """Get default dev dependencies based on options."""
        deps = {
            "@types/node": "20.10.0",
            "@types/react": "18.2.0",
            "@types/react-dom": "18.2.0",
            "eslint": "8.55.0",
            "eslint-config-next": "14.0.0",
        }

        if options.include_tests:
            deps["vitest"] = "1.0.0"
            deps["@testing-library/react"] = "14.1.0"

        return deps
