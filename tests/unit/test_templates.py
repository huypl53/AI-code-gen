"""Unit tests for template manager."""

import pytest

from app.core.templates import TemplateManager
from app.models.template import SpecTemplateCreate


class TestTemplateManager:
    """Tests for TemplateManager."""

    @pytest.mark.asyncio
    async def test_create_template_populates_metadata(self):
        manager = TemplateManager()
        template = await manager.create_template(
            SpecTemplateCreate(
                name="sample",
                csv_content="No,Task,Hours\n1,Setup,8\n2,Feature,12",
            )
        )

        assert template.id
        assert template.columns
        assert template.total_rows > 0
        assert template.estimated_hours_baseline is not None

    @pytest.mark.asyncio
    async def test_set_default_template(self):
        manager = TemplateManager()
        t1 = await manager.create_template(
            SpecTemplateCreate(name="one", csv_content="A,B\n1,2")
        )
        t2 = await manager.create_template(
            SpecTemplateCreate(name="two", csv_content="A,B\n3,4", is_default=True)
        )

        assert t2.is_default
        assert manager.get_default().id == t2.id

        updated = await manager.set_default(t1.id)
        assert updated.is_default
        assert manager.get_default().id == t1.id
