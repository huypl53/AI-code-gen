"""Pipeline Orchestrator.

Coordinates the execution of all agents in sequence to transform
specifications into deployed applications.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

from app.agents.coding_agent import CodingAgent, CodingAgentInput
from app.agents.devops_agent import DevopsAgent, DevopsAgentInput
from app.agents.spec_agent import SpecAnalysisAgent, SpecAnalysisInput
from app.config import settings
from app.core.events import EventBus, get_event_bus
from app.core.exceptions import AgentExecutionError
from app.core.session import SessionManager, get_session_manager
from app.core.templates import TemplateManager, get_template_manager
from app.models.generation import CodeGenOptions
from app.models.project import PhaseStatus, Project, ProjectStatus
from app.models.spec import StructuredSpec
from app.utils.debug import save_pre_codegen_debug
from app.utils.logging import get_logger

from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk

# Setup claude_agent_sdk with langsmith tracing
configure_claude_agent_sdk()

# Maximum number of build fix attempts
MAX_BUILD_FIX_ATTEMPTS = 3


class PipelineOrchestrator:
    """Orchestrates the agent pipeline for project generation.
    
    Pipeline phases:
    1. spec_analysis - Parse and analyze specifications
    2. code_generation - Generate application code
    3. deployment - Deploy to Vercel
    """

    def __init__(
        self,
        session: SessionManager | None = None,
        events: EventBus | None = None,
        template_manager: TemplateManager | None = None,
    ):
        self.session = session or get_session_manager()
        self.events = events or get_event_bus()
        self.template_manager = template_manager or get_template_manager()
        self.logger = get_logger("orchestrator")

        # Initialize agents
        self.spec_agent = SpecAnalysisAgent()
        self.coding_agent = CodingAgent()
        self.devops_agent = DevopsAgent()

    async def run(self, project_id: UUID) -> Project:
        """Run the complete pipeline for a project.
        
        Args:
            project_id: The project to process
            
        Returns:
            The updated project with results
            
        Raises:
            AgentExecutionError: If any phase fails
        """
        project = await self.session.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        self.logger.info("orchestrator.pipeline.started", project_id=str(project_id))

        try:
            # Phase 1: Specification Analysis (skip if already completed)
            spec_phase = project.phases.get("spec_analysis")
            if not spec_phase or spec_phase.status != PhaseStatus.COMPLETED:
                project = await self._run_spec_analysis(project)

                # Check if clarifications needed
                if project.status == ProjectStatus.CLARIFYING:
                    self.logger.info(
                        "orchestrator.awaiting_clarifications",
                        project_id=str(project_id),
                    )
                    return project
            else:
                self.logger.info("orchestrator.skipping_spec_analysis", reason="already_completed")

            # Phase 2: Code Generation (skip if already completed)
            code_phase = project.phases.get("code_generation")
            if code_phase and code_phase.status == PhaseStatus.COMPLETED:
                self.logger.info("orchestrator.skipping_code_generation", reason="already_completed")
            else:
                project = await self._run_code_generation(project)

            # Phase 3: Deployment (if auto_deploy is enabled, skip if already completed)
            deploy_phase = project.phases.get("deployment")
            if deploy_phase and deploy_phase.status == PhaseStatus.COMPLETED:
                self.logger.info("orchestrator.skipping_deployment", reason="already_completed")
            elif project.options.auto_deploy:
                project = await self._run_deployment(project)
            else:
                project.status = ProjectStatus.DEPLOYED  # Mark as complete without deploy
                project.completed_at = datetime.utcnow()

            await self.session.update_project(project)

            self.logger.info(
                "orchestrator.pipeline.completed",
                project_id=str(project_id),
                status=project.status.value,
            )

            return project

        except Exception as e:
            self.logger.error(
                "orchestrator.pipeline.failed",
                project_id=str(project_id),
                error=str(e),
            )

            project.status = ProjectStatus.FAILED
            project.error = str(e)
            await self.session.update_project(project)
            await self.events.publish_error(project_id, str(e), project.current_phase)

            raise

    async def _run_spec_analysis(self, project: Project) -> Project:
        """Run the specification analysis phase."""
        phase = "spec_analysis"

        project.update_phase(phase, PhaseStatus.IN_PROGRESS)
        project.status = ProjectStatus.ANALYZING
        await self.session.update_project(project)
        await self.events.publish_phase_started(project.id, phase)

        try:
            template = None
            if project.template_id:
                template = await self.template_manager.get_template(project.template_id)
                if not template:
                    self.logger.warning(
                        "orchestrator.template_missing",
                        template_id=str(project.template_id),
                    )
            else:
                template = self.template_manager.get_default()

            result = await self.spec_agent.execute(
                SpecAnalysisInput(
                    spec_format=project.spec_format,
                    spec_content=project.spec_content,
                    project_name=project.name,
                    template=template,
                )
            )

            # Store structured spec
            project.structured_spec = result.structured_spec.model_dump()
            if result.estimation:
                result.estimation.ensure_csv()
                project.estimation = result.estimation.model_dump()

            # Handle clarification questions (only pause if there are required unanswered questions)
            required_unanswered = [
                q for q in result.clarification_questions
                if q.required and not q.answered
            ]
            
            if required_unanswered:
                project.clarification_questions = result.clarification_questions
                project.status = ProjectStatus.CLARIFYING
                project.update_phase(
                    phase,
                    PhaseStatus.COMPLETED,
                    metadata={"needs_clarification": True},
                )
            else:
                project.update_phase(
                    phase,
                    PhaseStatus.COMPLETED,
                    metadata={
                        "features_count": len(result.structured_spec.features),
                        "models_count": len(result.structured_spec.data_models),
                    },
                )

            await self.session.update_project(project)
            await self.events.publish_phase_completed(
                project.id,
                phase,
                project.phases[phase].duration_ms or 0,
            )

            return project

        except Exception as e:
            project.update_phase(phase, PhaseStatus.FAILED, error=str(e))
            await self.session.update_project(project)
            raise AgentExecutionError("spec_analysis", phase, str(e))

    async def _run_code_generation(self, project: Project) -> Project:
        """Run the code generation phase."""
        phase = "code_generation"

        project.update_phase(phase, PhaseStatus.IN_PROGRESS)
        project.status = ProjectStatus.GENERATING
        await self.session.update_project(project)
        await self.events.publish_phase_started(project.id, phase)

        try:
            # Reconstruct spec from stored dict
            spec = StructuredSpec(**project.structured_spec)

            # Save debug data before code generation
            codegen_options = {
                "framework": project.options.framework,
                "styling": project.options.styling,
                "include_tests": project.options.include_tests,
                "typescript": project.options.typescript,
            }
            
            user_request = {
                "name": project.name,
                "spec_format": project.spec_format,
                "spec_content": project.spec_content,
                "options": project.options.model_dump() if hasattr(project.options, 'model_dump') else dict(project.options),
                "created_at": project.created_at.isoformat() if project.created_at else None,
            }
            
            debug_path = save_pre_codegen_debug(
                project_id=str(project.id),
                user_request=user_request,
                structured_spec=project.structured_spec,
                codegen_options=codegen_options,
            )
            self.logger.info(
                "orchestrator.debug_data_saved",
                project_id=str(project.id),
                debug_path=str(debug_path),
            )

            result = await self.coding_agent.execute(
                CodingAgentInput(
                    spec=spec,
                    options=CodeGenOptions(
                        framework=project.options.framework,
                        styling=project.options.styling,
                        include_tests=project.options.include_tests,
                        typescript=project.options.typescript,
                    ),
                )
            )

            if not result.success:
                raise Exception(result.error or "Code generation failed")

            # Store generated project info
            output_dir = Path(result.project.output_directory)
            project.generated_project = {
                "output_directory": result.project.output_directory,
                "file_count": result.project.file_count,
                "total_lines": result.project.total_lines,
            }

            await self.session.update_project(project)

            # Run local build validation and fix errors if needed
            self.logger.info(
                "orchestrator.validating_build",
                project_id=str(project.id),
                output_dir=str(output_dir),
            )

            build_success = await self._validate_and_fix_build(
                project=project,
                output_dir=output_dir,
                spec=spec,
            )

            if not build_success:
                self.logger.error(
                    "orchestrator.build_validation_failed",
                    project_id=str(project.id),
                )
                raise Exception(
                    "Build validation failed after multiple attempts. "
                    "Please check the generated code for errors."
                )

            project.update_phase(
                phase,
                PhaseStatus.COMPLETED,
                metadata={
                    "files_generated": result.project.file_count,
                    "total_lines": result.project.total_lines,
                    "build_validated": build_success,
                },
            )

            # Publish file generation events
            for file in result.project.files[:10]:  # Limit events
                await self.events.publish_file_generated(
                    project.id,
                    file.path,
                    file.lines,
                )

            await self.session.update_project(project)
            await self.events.publish_phase_completed(
                project.id,
                phase,
                project.phases[phase].duration_ms or 0,
            )

            return project

        except Exception as e:
            project.update_phase(phase, PhaseStatus.FAILED, error=str(e))
            await self.session.update_project(project)
            raise AgentExecutionError("coding", phase, str(e))

    async def _run_deployment(self, project: Project) -> Project:
        """Run the deployment phase."""
        phase = "deployment"

        project.update_phase(phase, PhaseStatus.IN_PROGRESS)
        project.status = ProjectStatus.DEPLOYING
        await self.session.update_project(project)
        await self.events.publish_phase_started(project.id, phase)

        try:
            output_dir = project.generated_project.get("output_directory", "")
            if not output_dir:
                raise Exception("No generated project to deploy")

            result = await self.devops_agent.execute(
                DevopsAgentInput(
                    project_directory=output_dir,
                    project_name=project.name,
                )
            )

            if not result.success:
                raise Exception(result.result.error or "Deployment failed")

            # Store deployment result
            project.deployment_result = result.result.model_dump()
            project.status = ProjectStatus.DEPLOYED
            project.completed_at = datetime.utcnow()

            project.update_phase(
                phase,
                PhaseStatus.COMPLETED,
                metadata={
                    "url": result.result.url,
                    "deployment_id": result.result.deployment_id,
                },
            )

            await self.session.update_project(project)
            await self.events.publish_deployment_complete(project.id, result.result.url)
            await self.events.publish_phase_completed(
                project.id,
                phase,
                project.phases[phase].duration_ms or 0,
            )

            return project

        except Exception as e:
            project.update_phase(phase, PhaseStatus.FAILED, error=str(e))
            await self.session.update_project(project)
            raise AgentExecutionError("devops", phase, str(e))

    async def _validate_and_fix_build(
        self,
        project: Project,
        output_dir: Path,
        spec: StructuredSpec,
    ) -> bool:
        """Validate the build locally and fix errors using the coding agent.
        
        Args:
            project: The project being processed
            output_dir: Path to the generated project
            spec: The structured specification
            
        Returns:
            True if build succeeds, False otherwise
        """
        for attempt in range(MAX_BUILD_FIX_ATTEMPTS):
            self.logger.info(
                "orchestrator.build_attempt",
                project_id=str(project.id),
                attempt=attempt + 1,
                max_attempts=MAX_BUILD_FIX_ATTEMPTS,
            )

            # Step 1: Install dependencies
            install_success, install_error = await self._run_npm_command(
                output_dir, "install"
            )
            if not install_success:
                self.logger.error(
                    "orchestrator.npm_install_failed",
                    error=install_error[:500] if install_error else "Unknown error",
                )
                # Try to fix install errors
                if attempt < MAX_BUILD_FIX_ATTEMPTS - 1:
                    fixed = await self.coding_agent.fix_build_errors(
                        project_dir=output_dir,
                        error_output=install_error or "npm install failed",
                        spec=spec,
                    )
                    if fixed:
                        continue
                return False

            # Step 2: Run build
            build_success, build_error = await self._run_npm_command(
                output_dir, "run build"
            )
            
            if build_success:
                self.logger.info(
                    "orchestrator.build_success",
                    project_id=str(project.id),
                    attempt=attempt + 1,
                )
                return True

            # Build failed - try to fix errors
            self.logger.warning(
                "orchestrator.build_failed",
                project_id=str(project.id),
                attempt=attempt + 1,
                error_preview=build_error[:500] if build_error else "Unknown error",
            )

            # Last attempt - don't try to fix, just fail
            if attempt >= MAX_BUILD_FIX_ATTEMPTS - 1:
                self.logger.error(
                    "orchestrator.max_fix_attempts_reached",
                    project_id=str(project.id),
                )
                break

            # Try to fix the errors with the coding agent
            await self.events.publish_agent_message(
                project.id,
                "coding",
                f"Build failed (attempt {attempt + 1}/{MAX_BUILD_FIX_ATTEMPTS}). Analyzing and fixing errors...",
            )

            fixed = await self.coding_agent.fix_build_errors(
                project_dir=output_dir,
                error_output=build_error or "Build failed with unknown error",
                spec=spec,
            )

            if not fixed:
                self.logger.warning(
                    "orchestrator.fix_attempt_failed",
                    project_id=str(project.id),
                    attempt=attempt + 1,
                )
                # Continue to next attempt anyway - sometimes just retrying helps
                continue

            self.logger.info(
                "orchestrator.fix_applied",
                project_id=str(project.id),
                attempt=attempt + 1,
            )

        return False

    async def _run_npm_command(
        self,
        project_dir: Path,
        command: str,
        timeout: int = 300,
    ) -> tuple[bool, str | None]:
        """Run an npm command in the project directory.
        
        Args:
            project_dir: Path to the project directory
            command: npm command to run (e.g., "install", "run build")
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, error_output)
        """
        try:
            cmd = f"npm {command}"
            self.logger.info(
                "orchestrator.running_npm_command",
                cmd=cmd,
                cwd=str(project_dir),
            )

            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, f"Command timed out after {timeout} seconds"

            stdout_text = stdout.decode() if stdout else ""
            stderr_text = stderr.decode() if stderr else ""

            if process.returncode != 0:
                # Combine stdout and stderr for error output
                error_output = f"Exit code: {process.returncode}\n"
                if stderr_text:
                    error_output += f"STDERR:\n{stderr_text}\n"
                if stdout_text:
                    error_output += f"STDOUT:\n{stdout_text}"
                return False, error_output

            return True, None

        except Exception as e:
            return False, str(e)

    async def resume_after_clarification(self, project_id: UUID) -> Project:
        """Resume pipeline after clarifications are provided.
        
        Continues from specification analysis with the new answers.
        """
        project = await self.session.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        if project.status != ProjectStatus.CLARIFYING:
            raise ValueError("Project is not awaiting clarifications")

        # Re-run spec analysis with clarifications context
        # For now, just continue to code generation since we have the spec
        return await self.run(project_id)


# Convenience function to get orchestrator
def get_orchestrator() -> PipelineOrchestrator:
    """Get a pipeline orchestrator instance."""
    return PipelineOrchestrator()
