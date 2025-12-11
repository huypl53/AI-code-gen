"""DevOps Agent.

Deploys generated projects to Vercel and returns the live URL.
"""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config import settings
from app.models.deployment import DeploymentInput, DeploymentResult


class DevopsAgentInput(BaseModel):
    """Input for the devops agent."""

    project_directory: str
    project_name: str
    environment: str = "production"
    env_vars: dict[str, str] = Field(default_factory=dict)


class DevopsAgentOutput(BaseModel):
    """Output from the devops agent."""

    result: DeploymentResult
    success: bool = True


class DevopsAgent(BaseAgent[DevopsAgentInput, DevopsAgentOutput]):
    """Agent for deploying applications to Vercel.
    
    This agent:
    1. Validates the project structure
    2. Configures Vercel settings
    3. Deploys to Vercel
    4. Returns the deployment URL
    """

    @property
    def name(self) -> str:
        return "devops"

    @property
    def description(self) -> str:
        return "Deploys generated applications to Vercel"

    @property
    def system_prompt(self) -> str:
        return """You are a DevOps engineer specializing in Vercel deployments.

## Your Responsibilities
1. Validate project structure for deployment
2. Configure Vercel project settings
3. Handle environment variables
4. Execute deployment
5. Monitor build process
6. Report deployment status and URL

## Deployment Checklist
- [ ] Verify package.json has build script
- [ ] Check for next.config.js / vite.config.js
- [ ] Validate environment variables
- [ ] Configure build settings
- [ ] Set up domains (if provided)

## Error Handling
- Build failures: Analyze logs, suggest fixes
- Timeout: Increase build timeout or optimize
- Dependencies: Check for missing packages
"""

    @property
    def tools(self) -> list[str]:
        return ["Read", "Bash", "Glob"]

    @property
    def model(self) -> str:
        return "sonnet"

    async def execute(self, input_data: DevopsAgentInput) -> DevopsAgentOutput:
        """Execute deployment to Vercel."""
        import time

        start_time = time.time()

        self.logger.info(
            "devops_agent.started",
            project=input_data.project_name,
            directory=input_data.project_directory,
        )

        project_dir = Path(input_data.project_directory)

        # Validate project structure
        validation_error = self._validate_project(project_dir)
        if validation_error:
            return DevopsAgentOutput(
                result=DeploymentResult(
                    success=False,
                    error=validation_error,
                ),
                success=False,
            )

        # Use mock deployment for demos (real Vercel deployment when vercel_deploy_real=True)
        if settings.vercel_deploy_real and settings.vercel_token:
            # Validate token format (new tokens don't have colons)
            if ":" in settings.vercel_token:
                self.logger.error(
                    "devops_agent.invalid_token_format",
                    reason="Token contains ':' - please regenerate from https://vercel.com/account/tokens",
                )
                return DevopsAgentOutput(
                    result=DeploymentResult(
                        success=False,
                        error="Invalid Vercel token format. Tokens with ':' are legacy format. Please create a new token at https://vercel.com/account/tokens",
                    ),
                    success=False,
                )
            result = await self._deploy_to_vercel(input_data, project_dir)
        else:
            if settings.vercel_token and not settings.vercel_deploy_real:
                self.logger.info("mock_deployment.enabled", reason="set VERCEL_DEPLOY_REAL=true in .env for real deployment")
            result = await self._mock_deployment(input_data, project_dir)

        duration_ms = int((time.time() - start_time) * 1000)
        result.duration_ms = duration_ms

        self.logger.info(
            "devops_agent.completed",
            success=result.success,
            url=result.url if result.success else None,
            duration_ms=duration_ms,
        )

        return DevopsAgentOutput(
            result=result,
            success=result.success,
        )

    def _validate_project(self, project_dir: Path) -> str | None:
        """Validate the project structure for deployment."""
        # Check if directory exists
        if not project_dir.exists():
            return f"Project directory not found: {project_dir}"

        # Check for package.json
        package_json = project_dir / "package.json"
        if not package_json.exists():
            return "Missing package.json - cannot deploy"

        # Parse package.json
        try:
            with open(package_json) as f:
                package = json.load(f)

            # Check for build script
            scripts = package.get("scripts", {})
            if "build" not in scripts:
                return "Missing 'build' script in package.json"

        except json.JSONDecodeError as e:
            return f"Invalid package.json: {e}"

        return None

    async def _deploy_to_vercel(
        self, input_data: DevopsAgentInput, project_dir: Path
    ) -> DeploymentResult:
        """Deploy to Vercel using the Vercel CLI."""
        import os
        
        try:
            token = settings.vercel_token
            
            # Build the vercel deploy command
            cmd = [
                "npx",
                "vercel",
                "deploy",
                "--yes",
                "--token", token,  # Pass token explicitly
            ]

            if input_data.environment == "production":
                cmd.append("--prod")

            # Add team if configured
            if settings.vercel_team_id:
                cmd.extend(["--scope", settings.vercel_team_id])

            # Set environment variables
            for key, value in input_data.env_vars.items():
                cmd.extend(["--env", f"{key}={value}"])

            # Prepare environment (also set token as env var as fallback)
            env = os.environ.copy()
            env["VERCEL_TOKEN"] = token
            
            # Log command (mask token for security)
            cmd_display = " ".join(cmd).replace(token, "***")
            self.logger.info(
                "devops_agent.deploying",
                cmd=cmd_display,
                cwd=str(project_dir),
            )

            # Run deployment
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300,  # 5 minute timeout
            )

            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""
            
            self.logger.info(
                "devops_agent.deploy_output",
                returncode=process.returncode,
                stdout_len=len(stdout_text),
                stderr_len=len(stderr_text),
            )

            if process.returncode != 0:
                # Log first 500 chars of error for debugging
                error_preview = stderr_text[:500] if stderr_text else stdout_text[:500]
                self.logger.error(
                    "devops_agent.deploy_failed",
                    error_preview=error_preview,
                )
                return DeploymentResult(
                    success=False,
                    error=error_preview or "Unknown deployment error",
                    error_details={
                        "stderr": stderr_text[:1000] if stderr_text else None,
                        "stdout": stdout_text[:1000] if stdout_text else None,
                    },
                )

            # Extract deployment URL from output
            output = stdout_text.strip()
            url = self._extract_url(output)
            
            if not url:
                # Try stderr too (sometimes URL is there)
                url = self._extract_url(stderr_text)

            return DeploymentResult(
                success=True,
                url=url,
                deployment_id=self._extract_deployment_id(output),
            )

        except asyncio.TimeoutError:
            return DeploymentResult(
                success=False,
                error="Deployment timed out after 5 minutes",
            )
        except Exception as e:
            self.logger.exception("devops_agent.deploy_exception")
            return DeploymentResult(
                success=False,
                error=str(e),
            )

    def _extract_url(self, output: str) -> str:
        """Extract deployment URL from Vercel CLI output."""
        import re

        # Look for URL pattern in output
        url_pattern = r"https://[a-zA-Z0-9-]+\.vercel\.app"
        match = re.search(url_pattern, output)
        if match:
            return match.group(0)

        # Fall back to last line (usually the URL)
        lines = output.strip().split("\n")
        for line in reversed(lines):
            if line.startswith("https://"):
                return line.strip()

        return ""

    def _extract_deployment_id(self, output: str) -> str:
        """Extract deployment ID from Vercel CLI output."""
        import re

        # Look for deployment ID pattern
        id_pattern = r"dpl_[a-zA-Z0-9]+"
        match = re.search(id_pattern, output)
        if match:
            return match.group(0)

        return ""

    async def _mock_deployment(
        self, input_data: DevopsAgentInput, project_dir: Path
    ) -> DeploymentResult:
        """Mock deployment for testing without Vercel token."""
        import uuid

        # Simulate deployment delay
        await asyncio.sleep(1)

        deployment_id = f"dpl_{uuid.uuid4().hex[:12]}"
        url = f"https://{input_data.project_name}-{uuid.uuid4().hex[:8]}.vercel.app"

        self.logger.info(
            "devops_agent.mock_deployment",
            url=url,
            deployment_id=deployment_id,
        )

        return DeploymentResult(
            success=True,
            url=url,
            deployment_id=deployment_id,
            build_logs_url=f"https://vercel.com/deployments/{deployment_id}",
        )
