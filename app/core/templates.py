"""In-memory storage for specification templates."""

from functools import lru_cache
from typing import Iterable
from uuid import UUID

from app.models.template import SpecTemplate, SpecTemplateCreate


class TemplateManager:
    """Manages CSV templates uploaded by users."""

    def __init__(self):
        self._templates: dict[UUID, SpecTemplate] = {}
        self._default_template_id: UUID | None = None

    async def create_template(self, data: SpecTemplateCreate) -> SpecTemplate:
        """Store a new template."""
        template = SpecTemplate(
            name=data.name,
            csv_content=data.csv_content,
            description=data.description,
            is_default=data.is_default,
        )
        template.summarize()

        self._templates[template.id] = template

        if data.is_default or not self._default_template_id:
            self._set_default(template.id)

        return template

    async def list_templates(self) -> Iterable[SpecTemplate]:
        """List all templates."""
        return list(self._templates.values())

    async def get_template(self, template_id: UUID) -> SpecTemplate | None:
        """Fetch a template by ID."""
        return self._templates.get(template_id)

    async def set_default(self, template_id: UUID) -> SpecTemplate:
        """Mark a template as the default."""
        if template_id not in self._templates:
            raise KeyError("Template not found")

        self._set_default(template_id)
        return self._templates[template_id]

    def get_default(self) -> SpecTemplate | None:
        """Return the default template if one exists."""
        if self._default_template_id:
            return self._templates.get(self._default_template_id)
        return None

    def clear(self) -> None:
        """Remove all templates (primarily for tests)."""
        self._templates.clear()
        self._default_template_id = None

    def _set_default(self, template_id: UUID) -> None:
        """Internal helper to set default template."""
        # Reset old default flag
        for tid, tmpl in self._templates.items():
            tmpl.is_default = tid == template_id

        self._default_template_id = template_id


_template_manager: TemplateManager | None = None


@lru_cache
def get_template_manager() -> TemplateManager:
    """Get the singleton TemplateManager."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
