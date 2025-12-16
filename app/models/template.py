"""Specification template data models."""

import csv
import io
import statistics
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SpecTemplateCreate(BaseModel):
    """Input model for uploading a new CSV template."""

    name: str = Field(..., min_length=1, max_length=120)
    csv_content: str = Field(..., min_length=5)
    description: str | None = None
    is_default: bool = False


class SpecTemplate(BaseModel):
    """Stored CSV template used for estimations."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    csv_content: str
    description: str | None = None
    is_default: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    columns: list[str] = Field(default_factory=list)
    sample_rows: list[list[str]] = Field(default_factory=list)
    total_rows: int = 0
    estimated_hours_baseline: float | None = None
    stats: dict[str, Any] = Field(default_factory=dict)

    def summarize(self) -> None:
        """Parse CSV and populate metadata."""
        reader = csv.reader(io.StringIO(self.csv_content))

        preview: list[list[str]] = []
        hours: list[float] = []
        columns: list[str] = []
        row_count = 0

        for row in reader:
            # Skip empty rows
            if not any(cell.strip() for cell in row):
                continue

            if not columns:
                columns = [cell.strip() or f"col_{i+1}" for i, cell in enumerate(row)]

            if len(preview) < 5:
                preview.append(row)

            row_count += 1

            for cell in row:
                parsed = self._parse_hours(cell)
                if parsed is not None:
                    hours.append(parsed)

        baseline = None
        filtered_hours = [h for h in hours if 0 < h <= 200]
        if filtered_hours:
            baseline = statistics.median(filtered_hours)

        self.columns = columns
        self.sample_rows = preview
        self.total_rows = row_count
        self.estimated_hours_baseline = baseline
        self.updated_at = datetime.utcnow()
        self.stats = {
            "hours_count": len(hours),
            "hours_min": min(filtered_hours) if filtered_hours else None,
            "hours_max": max(filtered_hours) if filtered_hours else None,
            "hours_median": baseline,
        }

    def _parse_hours(self, cell: str) -> float | None:
        """Attempt to parse a numeric hour value from a cell."""
        cleaned = cell.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
