"""Project template models for code generation templates."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TechStack(BaseModel):
    """Technology stack configuration for a template."""

    framework: Literal["nextjs", "react", "vue"] = "nextjs"
    styling: Literal["tailwind", "css", "scss"] = "tailwind"
    typescript: bool = True
    state_management: str | None = "zustand"
    data_fetching: str | None = "tanstack-query"


class ProjectTemplate(BaseModel):
    """A reusable project template for code generation."""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""

    # Filesystem location (relative to templates directory)
    project_path: str

    # Technology configuration
    tech_stack: TechStack = Field(default_factory=TechStack)

    # Features this template implements
    features: list[str] = Field(default_factory=list)

    # Embedding for similarity matching (None = not yet computed)
    embedding: list[float] | None = None

    # Usage statistics
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    source_spec_hash: str | None = None
    file_count: int = 0
    total_lines: int = 0


class TemplateMatch(BaseModel):
    """Result of matching a spec to a template."""

    template: ProjectTemplate
    similarity_score: float  # 0.0 to 1.0
    matched_features: list[str]  # Features in common
    missing_features: list[str]  # Features spec needs but template lacks
    extra_features: list[str]  # Features template has but spec doesn't need


class ProjectTemplateCreate(BaseModel):
    """Request model for creating a new project template."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    tech_stack: TechStack = Field(default_factory=TechStack)
    features: list[str] = Field(default_factory=list)
    # Source can be: existing directory path OR project_id to extract from
    source_path: str | None = None
    source_project_id: UUID | None = None


class ProjectTemplateResponse(BaseModel):
    """Response model for project template."""

    id: UUID
    name: str
    description: str
    project_path: str
    tech_stack: TechStack
    features: list[str]
    usage_count: int
    created_at: datetime
    updated_at: datetime
    file_count: int
    total_lines: int

    @classmethod
    def from_template(cls, template: ProjectTemplate) -> "ProjectTemplateResponse":
        """Create response from ProjectTemplate."""
        return cls(
            id=template.id,
            name=template.name,
            description=template.description,
            project_path=template.project_path,
            tech_stack=template.tech_stack,
            features=template.features,
            usage_count=template.usage_count,
            created_at=template.created_at,
            updated_at=template.updated_at,
            file_count=template.file_count,
            total_lines=template.total_lines,
        )
