"""Template management endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.templates import get_template_manager
from app.models.template import SpecTemplate, SpecTemplateCreate

router = APIRouter()


@router.post(
    "",
    response_model=SpecTemplate,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV estimation template",
)
async def create_template(data: SpecTemplateCreate) -> SpecTemplate:
    """Store a new CSV template for future estimations."""
    manager = get_template_manager()
    template = await manager.create_template(data)
    return template


@router.get(
    "",
    response_model=list[SpecTemplate],
    summary="List all templates",
)
async def list_templates() -> list[SpecTemplate]:
    """Return all stored templates."""
    manager = get_template_manager()
    templates = await manager.list_templates()
    return list(templates)


@router.get(
    "/{template_id}",
    response_model=SpecTemplate,
    summary="Get a single template",
)
async def get_template(template_id: UUID) -> SpecTemplate:
    """Fetch template details."""
    manager = get_template_manager()
    template = await manager.get_template(template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.post(
    "/{template_id}/default",
    response_model=SpecTemplate,
    summary="Mark template as default",
)
async def set_default_template(template_id: UUID) -> SpecTemplate:
    """Set the default template used when no ID is provided."""
    manager = get_template_manager()
    try:
        template = await manager.set_default(template_id)
        return template
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
