"""Project template management endpoints."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.project_template import (
    ProjectTemplate,
    ProjectTemplateResponse,
    TechStack,
)
from app.services.template_service import get_template_service

router = APIRouter()


class TemplateListResponse(BaseModel):
    """Response for listing templates."""

    templates: list[ProjectTemplateResponse]
    total: int


class CreateFromProjectRequest(BaseModel):
    """Request to create template from a generated project."""

    project_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    features: list[str] = Field(default_factory=list)


class CreateFromPathRequest(BaseModel):
    """Request to create template from a directory path."""

    name: str = Field(..., min_length=1, max_length=100)
    source_path: str = Field(..., description="Absolute path to the source project")
    description: str = ""
    features: list[str] = Field(default_factory=list)
    tech_stack: TechStack = Field(default_factory=TechStack)


@router.get(
    "",
    response_model=TemplateListResponse,
    summary="List all project templates",
)
async def list_templates() -> TemplateListResponse:
    """List all available project templates ordered by usage count."""
    service = get_template_service()
    templates = await service.list_templates()
    return TemplateListResponse(
        templates=[ProjectTemplateResponse.from_template(t) for t in templates],
        total=len(templates),
    )


@router.get(
    "/{template_id}",
    response_model=ProjectTemplateResponse,
    summary="Get a project template",
)
async def get_template(template_id: UUID) -> ProjectTemplateResponse:
    """Get a project template by ID."""
    service = get_template_service()
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return ProjectTemplateResponse.from_template(template)


@router.post(
    "/from-project",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template from a generated project",
)
async def create_template_from_project(
    data: CreateFromProjectRequest,
) -> ProjectTemplateResponse:
    """Create a new template from a successfully generated project.

    This endpoint takes a project ID from a previously generated project
    and creates a reusable template from its output files.
    """
    from app.core.session import get_session_manager

    session = get_session_manager()
    project = await session.get_project(data.project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.generated_project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no generated code",
        )

    output_dir = project.generated_project.get("output_directory")
    if not output_dir or not Path(output_dir).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Generated project files not found",
        )

    # Determine tech stack from project options
    tech_stack = TechStack(
        framework=project.options.framework,
        styling=project.options.styling,
        typescript=project.options.typescript,
    )

    # Extract features from structured spec if available and not provided
    features = data.features
    if not features and project.structured_spec:
        features = [f["name"] for f in project.structured_spec.get("features", [])]

    service = get_template_service()

    try:
        template = await service.create_template_from_project(
            name=data.name,
            description=data.description,
            source_dir=Path(output_dir),
            features=features,
            tech_stack=tech_stack,
        )
        return ProjectTemplateResponse.from_template(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/from-path",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template from a directory path",
)
async def create_template_from_path(
    data: CreateFromPathRequest,
) -> ProjectTemplateResponse:
    """Create a new template from an existing directory path.

    This endpoint allows creating a template from any directory containing
    a valid project structure.
    """
    source_path = Path(data.source_path)

    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source path does not exist: {data.source_path}",
        )

    if not source_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source path must be a directory",
        )

    service = get_template_service()

    try:
        template = await service.create_template_from_project(
            name=data.name,
            description=data.description,
            source_dir=source_path,
            features=data.features,
            tech_stack=data.tech_stack,
        )
        return ProjectTemplateResponse.from_template(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{template_id}/refresh-embedding",
    response_model=ProjectTemplateResponse,
    summary="Refresh template embedding",
)
async def refresh_template_embedding(template_id: UUID) -> ProjectTemplateResponse:
    """Refresh the embedding vector for a template.

    This is useful if the embedding algorithm has been updated or
    if template metadata has changed.
    """
    service = get_template_service()

    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    success = await service.refresh_template_embedding(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh embedding",
        )

    # Fetch updated template
    updated_template = await service.get_template(template_id)
    if not updated_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found after refresh",
        )

    return ProjectTemplateResponse.from_template(updated_template)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project template",
)
async def delete_template(template_id: UUID) -> None:
    """Delete a project template and its files."""
    service = get_template_service()
    deleted = await service.delete_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
