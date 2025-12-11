"""CSV specification parser.

Parses CSV specifications into structured data for further processing.
"""

import csv
import io
from dataclasses import dataclass, field

from app.models.spec import Feature


@dataclass
class ParsedCSV:
    """Result of parsing a CSV specification."""

    features: list[Feature] = field(default_factory=list)
    raw_rows: list[dict[str, str]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)


class CSVParser:
    """Parser for CSV specifications."""

    # Common column name mappings
    COLUMN_MAPPINGS = {
        # Feature name
        "feature_name": "name",
        "feature": "name",
        "name": "name",
        "title": "name",
        # Description
        "description": "description",
        "desc": "description",
        "details": "description",
        # Priority
        "priority": "priority",
        "prio": "priority",
        "importance": "priority",
        # Type
        "type": "type",
        "category": "type",
        "kind": "type",
        # Acceptance criteria
        "acceptance_criteria": "acceptance_criteria",
        "acceptance": "acceptance_criteria",
        "criteria": "acceptance_criteria",
        "ac": "acceptance_criteria",
    }

    def parse(self, content: str) -> ParsedCSV:
        """Parse CSV content into structured data."""
        result = ParsedCSV()

        # Parse CSV
        reader = csv.DictReader(io.StringIO(content))

        if reader.fieldnames:
            result.columns = list(reader.fieldnames)

        # Normalize column names
        column_map = self._build_column_map(result.columns)

        for i, row in enumerate(reader):
            result.raw_rows.append(dict(row))

            # Extract feature data using normalized columns
            feature = self._extract_feature(row, column_map, i + 1)
            if feature:
                result.features.append(feature)

        return result

    def _build_column_map(self, columns: list[str]) -> dict[str, str]:
        """Build a mapping from original columns to normalized names."""
        column_map: dict[str, str] = {}

        for col in columns:
            normalized = col.lower().strip().replace(" ", "_")
            if normalized in self.COLUMN_MAPPINGS:
                column_map[col] = self.COLUMN_MAPPINGS[normalized]
            else:
                column_map[col] = normalized

        return column_map

    def _extract_feature(
        self, row: dict[str, str], column_map: dict[str, str], index: int
    ) -> Feature | None:
        """Extract a Feature from a CSV row."""
        # Create normalized row
        normalized: dict[str, str] = {}
        for orig_col, value in row.items():
            norm_col = column_map.get(orig_col, orig_col.lower())
            normalized[norm_col] = value

        # Feature name is required
        name = normalized.get("name", "").strip()
        if not name:
            return None

        # Description
        description = normalized.get("description", "").strip()

        # Priority
        priority_str = normalized.get("priority", "should").strip().lower()
        priority_map = {
            "must": "must",
            "high": "must",
            "critical": "must",
            "should": "should",
            "medium": "should",
            "normal": "should",
            "could": "could",
            "low": "could",
            "nice": "could",
            "wont": "wont",
            "won't": "wont",
            "no": "wont",
        }
        priority = priority_map.get(priority_str, "should")

        # Acceptance criteria (may be semicolon-separated)
        ac_str = normalized.get("acceptance_criteria", "")
        acceptance_criteria = [
            c.strip() for c in ac_str.split(";") if c.strip()
        ]

        return Feature(
            id=f"f_{index}",
            name=name,
            description=description,
            priority=priority,  # type: ignore
            acceptance_criteria=acceptance_criteria,
        )


def parse_csv_spec(content: str) -> ParsedCSV:
    """Parse a CSV specification string."""
    parser = CSVParser()
    return parser.parse(content)
