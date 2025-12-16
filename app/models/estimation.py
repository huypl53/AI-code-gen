"""Estimation data models."""

import csv
import io
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EstimationRow(BaseModel):
    """A single estimation line item."""

    number: int
    area: str
    task: str
    estimated_hours: float
    optional: bool = False
    notes: str | None = None
    feature_id: str | None = None


class EstimationResult(BaseModel):
    """Structured estimation output with CSV rendering."""

    template_id: UUID | None = None
    rows: list[EstimationRow] = Field(default_factory=list)
    total_hours: float = 0.0
    buffer_hours: float = 0.0
    csv: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def ensure_totals(self) -> None:
        """Compute totals if not already set."""
        if not self.total_hours:
            self.total_hours = round(sum(r.estimated_hours for r in self.rows), 2)

    def grand_total(self) -> float:
        """Return total including buffer."""
        return round(self.total_hours + self.buffer_hours, 2)

    def ensure_csv(self) -> None:
        """Ensure CSV string is populated."""
        if self.csv:
            return

        self.ensure_totals()
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(
            ["No", "Area/Module", "Task", "Estimate (hrs)", "Optional", "Notes"]
        )
        for row in self.rows:
            writer.writerow(
                [
                    row.number,
                    row.area,
                    row.task,
                    f"{row.estimated_hours:.1f}",
                    "Y" if row.optional else "",
                    row.notes or "",
                ]
            )

        writer.writerow([])
        writer.writerow(
            [
                "",
                "",
                "Subtotal (hrs)",
                f"{self.total_hours:.1f}",
                "",
                "",
            ]
        )
        writer.writerow(
            [
                "",
                "",
                "Buffer/Overhead (hrs)",
                f"{self.buffer_hours:.1f}",
                "",
                "Contingency for PM/QA/dependencies",
            ]
        )
        writer.writerow(
            [
                "",
                "",
                "Total (hrs)",
                f"{self.grand_total():.1f}",
                "",
                "",
            ]
        )

        self.csv = output.getvalue()
