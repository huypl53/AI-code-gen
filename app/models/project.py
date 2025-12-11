"""Project-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project processing status."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    CLARIFYING = "clarifying"
    GENERATING = "generating"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseStatus(str, Enum):
    """Individual phase status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PhaseInfo(BaseModel):
    """Information about a processing phase."""

    status: PhaseStatus = PhaseStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ClarificationQuestion(BaseModel):
    """A question requiring user clarification."""

    id: str = Field(default_factory=lambda: f"q_{uuid4().hex[:8]}")
    category: Literal["feature", "design", "technical", "scope"]
    question: str
    options: list[str] | None = None
    required: bool = True
    context: str | None = None

    # Response tracking
    answered: bool = False
    answer: str | None = None


class ProjectOptions(BaseModel):
    """Options for project generation."""

    framework: Literal["nextjs", "react", "vue"] = "nextjs"
    styling: Literal["tailwind", "css", "scss"] = "tailwind"
    auto_deploy: bool = True
    include_tests: bool = True
    typescript: bool = True


class ProjectCreate(BaseModel):
    """Request model for creating a new project."""

    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    spec_format: Literal["markdown", "csv"]
    spec_content: str = Field(..., min_length=10)
    options: ProjectOptions = Field(default_factory=ProjectOptions)


class Project(BaseModel):
    """Complete project model with all state."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    status: ProjectStatus = ProjectStatus.PENDING

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Input
    spec_format: Literal["markdown", "csv"]
    spec_content: str
    options: ProjectOptions

    # Processing state
    current_phase: str | None = None
    phases: dict[str, PhaseInfo] = Field(default_factory=dict)

    # Clarifications
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)

    # Results (stored as dicts to avoid circular imports)
    structured_spec: dict[str, Any] | None = None
    generated_project: dict[str, Any] | None = None
    deployment_result: dict[str, Any] | None = None

    # Error tracking
    error: str | None = None
    error_phase: str | None = None

    def update_phase(
        self,
        phase: str,
        status: PhaseStatus,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Update a phase's status."""
        now = datetime.utcnow()

        if phase not in self.phases:
            self.phases[phase] = PhaseInfo()

        phase_info = self.phases[phase]
        phase_info.status = status

        if status == PhaseStatus.IN_PROGRESS:
            phase_info.started_at = now
            self.current_phase = phase
        elif status in (PhaseStatus.COMPLETED, PhaseStatus.FAILED):
            phase_info.completed_at = now
            if phase_info.started_at:
                phase_info.duration_ms = int(
                    (now - phase_info.started_at).total_seconds() * 1000
                )
            if status == PhaseStatus.FAILED:
                phase_info.error = error
                self.error = error
                self.error_phase = phase

        if metadata:
            phase_info.metadata.update(metadata)

        self.updated_at = now


class ProjectResponse(BaseModel):
    """API response model for project."""

    project_id: UUID
    name: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    current_phase: str | None = None
    phases: dict[str, PhaseInfo] = Field(default_factory=dict)

    # Results
    result: dict[str, Any] | None = None
    error: str | None = None

    # Clarification state
    pending_clarifications: int = 0

    @classmethod
    def from_project(cls, project: Project) -> "ProjectResponse":
        """Create response from project model."""
        result = None
        if project.deployment_result:
            result = {
                "url": project.deployment_result.get("url"),
                "deployment_id": project.deployment_result.get("deployment_id"),
            }

        pending_clarifications = sum(
            1 for q in project.clarification_questions if not q.answered
        )

        return cls(
            project_id=project.id,
            name=project.name,
            status=project.status,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
            current_phase=project.current_phase,
            phases=project.phases,
            result=result,
            error=project.error,
            pending_clarifications=pending_clarifications,
        )
