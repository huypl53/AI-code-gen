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
2. Generate all source code files using the Write tool
3. Create configuration files (package.json, tsconfig, etc.)
4. Add documentation (README, inline comments)

## Code Quality Standards
- Follow framework best practices
- Use TypeScript with strict typing
- Implement proper error handling
- Add input validation
- Use meaningful variable/function names
- Add JSDoc comments for public APIs

## File Generation Order
1. Configuration files (package.json, tsconfig.json, next.config.js, tailwind.config.js, etc.)
2. Type definitions and data models (src/types/)
3. API routes (src/app/api/)
4. UI components - start with atomic, then composite (src/components/)
5. Pages and layouts (src/app/)
6. Utility functions (src/lib/)
7. Documentation (README.md)

## Technology Stack (MUST USE)
### Core Framework
- **Next.js 14** with App Router (use `src/app/` directory structure)
- **TypeScript 5.3+** with strict mode enabled
- **React 18** with Server Components by default

### Styling
- **Tailwind CSS 3.4** for all styling
- **shadcn/ui** components when UI components are needed
- Use CSS variables for theming

### Data & State
- **Zustand** for client-side state management
- **React Query / TanStack Query** for server state and data fetching
- **Zod** for runtime validation and type inference

### API & Database
- Next.js API Routes (Route Handlers) in `src/app/api/`
- Use Server Actions for form submissions when appropriate

### Package Versions (use these exact versions)
```json
{
  "next": "14.2.0",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.3.0",
  "tailwindcss": "^3.4.0",
  "zod": "^3.22.0",
  "zustand": "^4.5.0",
  "@tanstack/react-query": "^5.0.0"
}
```

## CRITICAL: File Creation Rules
1. Always use the Write tool to create files
2. Create files one at a time with complete content
3. Start with package.json, then tsconfig.json, then other config files
4. Ensure all imports reference files that exist or will be created
5. Use relative imports within the project
"""

    @property
    def tools(self) -> list[str]:
        return ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    @property
    def model(self) -> str:
        # return "claude-opus-4-5-20251101"  # Use most capable model for code generation
        return "claude-sonnet-4-5-20250929"  # Use most capable model for code generation

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
            # Use Claude-based generation for intelligent code creation
            # Falls back to templates if Claude SDK is not available
            if settings.anthropic_api_key:
                project = await self._generate_with_claude(
                    spec=input_data.spec,
                    options=input_data.options,
                    output_dir=output_dir,
                )
            else:
                self.logger.warning(
                    "coding_agent.fallback_to_templates",
                    reason="ANTHROPIC_API_KEY not set",
                )
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
        from claude_agent_sdk import (
            query,
            ClaudeAgentOptions,
            AssistantMessage,
            ToolUseBlock,
            ToolResultBlock,
            ResultMessage,
        )

        files: list[GeneratedFile] = []

        # Capture stderr for debugging
        stderr_output: list[str] = []

        def capture_stderr(line: str) -> None:
            stderr_output.append(line)
            self.logger.debug("coding_agent.stderr", line=line)

        agent_options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            allowed_tools=self.tools,
            permission_mode="acceptEdits",
            cwd=str(output_dir),
            model=self.model,
            stderr=capture_stderr,
            # Pass API key as environment variable for authentication
            env={"ANTHROPIC_API_KEY": settings.anthropic_api_key} if settings.anthropic_api_key else {},
        )

        self.logger.info(
            "coding_agent.using_model",
            model=self.model,
            cwd=str(output_dir),
        )

        prompt = self._build_generation_prompt(spec, options)

        # Track tool usage for logging
        tool_uses = 0
        files_written = 0

        # Use the simpler query() function for one-off generation
        async for message in query(prompt=prompt, options=agent_options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        tool_uses += 1
                        if block.name == "Write":
                            files_written += 1
                            file_path = block.input.get("file_path", "unknown")
                            self.logger.info(
                                "coding_agent.writing_file",
                                file_path=file_path,
                            )
                        elif block.name in ["Edit", "Bash"]:
                            self.logger.info(
                                "coding_agent.tool_use",
                                tool=block.name,
                            )
            elif isinstance(message, ResultMessage):
                self.logger.info(
                    "coding_agent.generation_result",
                    is_error=message.is_error,
                    num_turns=message.num_turns,
                    duration_ms=message.duration_ms,
                    tool_uses=tool_uses,
                    files_written=files_written,
                )
                # Log stderr if there was an error
                if message.is_error and stderr_output:
                    self.logger.error(
                        "coding_agent.stderr_output",
                        stderr="\n".join(stderr_output[-20:]),  # Last 20 lines
                    )

        # Detect the actual project directory
        # Sometimes Claude creates a subdirectory with the project name
        actual_project_dir = self._find_project_directory(output_dir)

        self.logger.info(
            "coding_agent.project_directory_detected",
            output_dir=str(output_dir),
            actual_project_dir=str(actual_project_dir),
        )

        # Scan generated files
        files = await self._scan_generated_files(actual_project_dir)

        return GeneratedProject(
            output_directory=str(actual_project_dir),
            files=files,
            dependencies=self._get_default_dependencies(options),
            dev_dependencies=self._get_default_dev_dependencies(options),
        )
    
    def _find_project_directory(self, output_dir: Path) -> Path:
        """Find the actual project directory.
        
        Claude sometimes creates a subdirectory with the project name instead of
        putting files directly in the output directory. This method detects that
        and returns the correct project directory.
        
        Args:
            output_dir: The expected output directory
            
        Returns:
            The actual project directory (may be a subdirectory of output_dir)
        """
        # Check if package.json exists directly in output_dir
        if (output_dir / "package.json").exists():
            return output_dir
        
        # Look for package.json in immediate subdirectories
        for subdir in output_dir.iterdir():
            if subdir.is_dir() and (subdir / "package.json").exists():
                self.logger.info(
                    "coding_agent.found_project_in_subdirectory",
                    subdirectory=subdir.name,
                )
                return subdir
        
        # No package.json found - return original directory
        # The build validation will catch this and try to fix it
        self.logger.warning(
            "coding_agent.no_package_json_found",
            output_dir=str(output_dir),
        )
        return output_dir

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

        return f"""Generate a complete, production-ready {options.framework} application based on this specification.

## CRITICAL: File Paths
**DO NOT create a project subdirectory.** Create all files directly in the current working directory.
- CORRECT: `package.json`, `src/app/page.tsx`
- WRONG: `{spec.project_name}/package.json`, `my-project/src/app/page.tsx`

The current directory IS the project root. Start by creating `package.json` directly (not in a subfolder).

## Project Specification
```json
{spec_json}
```

## Generation Options
- Framework: {options.framework}
- Styling: {options.styling}
- TypeScript: {options.typescript}
- Include Tests: {options.include_tests}

## REQUIRED: File Creation Order
Create files in this EXACT order using the Write tool:

### Step 1: Configuration Files
1. `package.json` - with all dependencies:
   ```json
   {{
     "name": "{spec.project_name.lower().replace(' ', '-')}",
     "version": "0.1.0",
     "private": true,
     "scripts": {{
       "dev": "next dev",
       "build": "next build",
       "start": "next start",
       "lint": "next lint"
     }},
     "dependencies": {{
       "next": "14.2.0",
       "react": "^18.2.0",
       "react-dom": "^18.2.0",
       "zod": "^3.22.0",
       "zustand": "^4.5.0",
       "@tanstack/react-query": "^5.0.0"
     }},
     "devDependencies": {{
       "typescript": "^5.3.0",
       "@types/node": "^20.0.0",
       "@types/react": "^18.2.0",
       "@types/react-dom": "^18.2.0",
       "tailwindcss": "^3.4.0",
       "postcss": "^8.4.0",
       "autoprefixer": "^10.4.0",
       "eslint": "^8.0.0",
       "eslint-config-next": "14.2.0"
     }}
   }}
   ```

2. `tsconfig.json` - TypeScript configuration
3. `next.config.js` - Next.js configuration
4. `tailwind.config.ts` - Tailwind configuration
5. `postcss.config.js` - PostCSS configuration
6. `.eslintrc.json` - ESLint configuration

### Step 2: Source Files Structure
Create the `src/` directory structure:
- `src/app/layout.tsx` - Root layout with providers
- `src/app/page.tsx` - Home page
- `src/app/globals.css` - Global styles with Tailwind directives
- `src/types/` - TypeScript type definitions
- `src/components/` - React components
- `src/lib/` - Utility functions
- `src/app/api/` - API routes (if needed)

### Step 3: Implementation
1. Implement all features from the specification
2. Create all data models/types in `src/types/`
3. Create reusable UI components in `src/components/`
4. Implement API endpoints in `src/app/api/`
5. Create pages in `src/app/`

## CRITICAL Requirements
1. **Every file must be complete and syntactically correct**
2. **All imports must reference files that exist**
3. **Use the exact package versions specified**
4. **Tailwind CSS must be properly configured with the globals.css containing @tailwind directives**
5. **The app must build without errors using `npm run build`**

## Code Quality
- Use TypeScript strict mode
- Implement proper error handling
- Add input validation with Zod
- Use meaningful variable/function names
- Add comments for complex logic

Now create all the necessary files to build this application. Start with package.json.
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

    async def fix_build_errors(
        self,
        project_dir: Path,
        error_output: str,
        spec: StructuredSpec,
    ) -> bool:
        """Use Claude to fix build errors in the generated project.
        
        Args:
            project_dir: Path to the project directory
            error_output: The error output from npm run build
            spec: The original specification for context
            
        Returns:
            True if fixes were applied, False otherwise
        """
        if not settings.anthropic_api_key:
            self.logger.warning("fix_build_errors.skipped", reason="No API key")
            return False

        try:
            from claude_agent_sdk import ClaudeAgentOptions

            self.logger.info(
                "coding_agent.fixing_errors",
                project_dir=str(project_dir),
                error_length=len(error_output),
            )

            agent_options = ClaudeAgentOptions(
                system_prompt="""You are an expert debugger fixing build errors in a Next.js project.

## CRITICAL: File Paths
Create all files directly in the current working directory (cwd).
- CORRECT: `package.json`, `src/app/page.tsx`
- WRONG: `project-name/package.json`, `my-project/src/app/page.tsx`

## Your Task
Analyze the build errors and fix them by editing the necessary files.

## Rules
1. Only modify files that have errors
2. Make minimal changes to fix the issue
3. Ensure imports are correct
4. Check for missing dependencies
5. Verify TypeScript types are correct
6. All file paths should be relative to the current directory (no project subdirectory)

## Common Fixes
- Missing package.json: Create it with all required dependencies
- Missing imports: Add the required import statement
- Type errors: Fix the type annotation or add proper typing
- Missing files: Create the missing file with proper content
- Syntax errors: Fix the syntax issue
- Missing dependencies: They should already be in package.json, but check if imports match

Use the Edit tool to fix existing files or Write tool to create missing files.
""",
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
                permission_mode="acceptEdits",
                cwd=str(project_dir),
                model=self.model,
                # Pass API key as environment variable for authentication
                env={"ANTHROPIC_API_KEY": settings.anthropic_api_key},
            )

            # Truncate error output if too long
            max_error_length = 4000
            truncated_error = error_output
            if len(error_output) > max_error_length:
                truncated_error = error_output[:max_error_length] + "\n\n... (truncated)"

            prompt = f"""The project build failed with the following errors. Please fix them.

## Build Error Output
```
{truncated_error}
```

## Project Context
- Project: {spec.project_name}
- Framework: Next.js 14 with App Router
- Current Directory: {project_dir}

**IMPORTANT**: The current working directory IS the project root. Create/edit files directly here.
- If package.json is missing, create it directly as `package.json` (NOT in a subdirectory)
- Use paths like `src/app/page.tsx` (NOT `{spec.project_name}/src/app/page.tsx`)

First, use `Glob` or `Bash` (with `ls -la`) to see what files exist in the current directory.
Then analyze the errors and fix them using Edit or Write tools.
"""

            from claude_agent_sdk import (
                query,
                AssistantMessage,
                ToolUseBlock,
                ResultMessage,
            )

            # Track fixes applied
            fixes_applied = 0
            files_created = 0

            async for message in query(prompt=prompt, options=agent_options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            if block.name == "Write":
                                files_created += 1
                                file_path = block.input.get("file_path", "unknown")
                                self.logger.info(
                                    "coding_agent.fix_creating_file",
                                    file_path=file_path,
                                )
                            elif block.name == "Edit":
                                fixes_applied += 1
                                file_path = block.input.get("file_path", "unknown")
                                self.logger.info(
                                    "coding_agent.fix_editing_file",
                                    file_path=file_path,
                                )
                elif isinstance(message, ResultMessage):
                    self.logger.info(
                        "coding_agent.fix_result",
                        is_error=message.is_error,
                        num_turns=message.num_turns,
                        fixes_applied=fixes_applied,
                        files_created=files_created,
                    )

            self.logger.info(
                "coding_agent.errors_fixed",
                fixes_applied=fixes_applied,
                files_created=files_created,
            )
            return fixes_applied > 0 or files_created > 0

        except ImportError:
            self.logger.warning("claude-agent-sdk not available for fixing errors")
            return False
        except Exception as e:
            self.logger.error("coding_agent.fix_errors_failed", error=str(e))
            return False
