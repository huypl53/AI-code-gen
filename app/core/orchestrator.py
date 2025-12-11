"""Pipeline Orchestrator.

Coordinates the execution of all agents in sequence to transform
specifications into deployed applications.
"""

import asyncio
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from app.agents.coding_agent import CodingAgent, CodingAgentInput
from app.agents.devops_agent import DevopsAgent, DevopsAgentInput
from app.agents.spec_agent import SpecAnalysisAgent, SpecAnalysisInput
from app.core.events import EventBus, get_event_bus
from app.core.exceptions import AgentExecutionError
from app.core.session import SessionManager, get_session_manager
from app.models.generation import CodeGenOptions
from app.models.project import PhaseStatus, Project, ProjectStatus
from app.utils.logging import get_logger


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
    ):
        self.session = session or get_session_manager()
        self.events = events or get_event_bus()
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
            result = await self.spec_agent.execute(
                SpecAnalysisInput(
                    spec_format=project.spec_format,
                    spec_content=project.spec_content,
                    project_name=project.name,
                )
            )

            # Store structured spec
            project.structured_spec = result.structured_spec.model_dump()

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
            from app.models.spec import StructuredSpec

            spec = StructuredSpec(**project.structured_spec)

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
            project.generated_project = {
                "output_directory": result.project.output_directory,
                "file_count": result.project.file_count,
                "total_lines": result.project.total_lines,
            }

            project.update_phase(
                phase,
                PhaseStatus.COMPLETED,
                metadata={
                    "files_generated": result.project.file_count,
                    "total_lines": result.project.total_lines,
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
